from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from decimal import Decimal
from sqlalchemy.orm import Session

from ..models import (
    AllocationResult, AllocationRun, AllocationRule, Calculation, Entity, ExceptionCase,
    FinancialPeriod, MappingRule, NormalizedFinancialRecord, PnLRun,
    PnLSegmentResult, Policy, RawFinancialRecord, SourceImport,
)
from .finance import D, money, segmented_pnl, calculate_policy_result

ENGINE_VERSION='otp-engine-2.4.0-rc.3'


def _period_in_scope(period: str, fiscal_year: int, as_of_period: str) -> bool:
    return period.startswith(f'{fiscal_year}-') and period <= as_of_period


def _latest_allocation_runs(db: Session, workspace_id: int, period: str) -> list[AllocationRun]:
    runs=db.query(AllocationRun).filter(AllocationRun.workspace_id==workspace_id,AllocationRun.period==period,AllocationRun.status=='COMPLETED').order_by(AllocationRun.id.desc()).all()
    latest_by_rule={}
    for r in runs:
        latest_by_rule.setdefault(r.rule_id,r)
    return list(latest_by_rule.values())


def build_authoritative_pnl(
    db: Session,
    *,
    workspace_id: int,
    as_of_period: str,
    created_by: str,
    source_import_ids: list[int] | None = None,
    publish: bool = True,
) -> dict:
    try:
        fiscal_year=int(as_of_period[:4])
    except Exception as exc:
        raise ValueError('as_of_period must be YYYY-MM') from exc

    iq=db.query(SourceImport).filter(SourceImport.workspace_id==workspace_id,SourceImport.status.in_(['VALIDATED','PARTIAL','ACCEPTED']))
    if source_import_ids:
        iq=iq.filter(SourceImport.id.in_(source_import_ids))
    imports=iq.order_by(SourceImport.id).all()
    if not imports:
        raise ValueError('No validated source imports are available for P&L generation')
    import_ids=[x.id for x in imports]

    rq=db.query(RawFinancialRecord).filter(
        RawFinancialRecord.workspace_id==workspace_id,
        RawFinancialRecord.source_import_id.in_(import_ids),
        RawFinancialRecord.validation_status.in_(['VALID','WARNING'])
    )
    raw=[r for r in rq.all() if _period_in_scope(r.period,fiscal_year,as_of_period)]
    raw_ids=[r.id for r in raw]
    nq=db.query(NormalizedFinancialRecord).filter(
        NormalizedFinancialRecord.workspace_id==workspace_id,
        NormalizedFinancialRecord.raw_record_id.in_(raw_ids or [-1])
    )
    norm=nq.all()

    source_rows=len(raw)
    mapped_rows=len(norm)
    unresolved=max(0,source_rows-mapped_rows)
    coverage=Decimal('0') if source_rows==0 else D(mapped_rows)/D(source_rows)
    if source_rows==0:
        raise ValueError('No accepted rows fall within the requested fiscal-year/as-of period')
    if unresolved:
        raise ValueError(f'Cannot publish authoritative P&L: {unresolved} accepted rows are unresolved')

    source_total=money(sum((D(r.amount) for r in raw),Decimal('0')))
    normalized_total=money(sum((D(r.amount) for r in norm),Decimal('0')))
    if abs(source_total-normalized_total) > Decimal('0.01'):
        raise ValueError(f'Normalized control total does not reconcile: {source_total} vs {normalized_total}')

    allocations=_latest_allocation_runs(db,workspace_id,as_of_period)
    active_allocation_rules=db.query(AllocationRule).filter(AllocationRule.workspace_id==workspace_id,AllocationRule.status=='ACTIVE').count()
    if active_allocation_rules and len(allocations) < active_allocation_rules:
        raise ValueError(f'Cannot publish authoritative P&L: {active_allocation_rules} active allocation rule(s) require completed runs for {as_of_period}; found {len(allocations)}')
    alloc_by_segment=defaultdict(lambda:Decimal('0'))
    alloc_residual=Decimal('0')
    for ar in allocations:
        alloc_residual+=D(ar.residual)
        for res in db.query(AllocationResult).filter(AllocationResult.allocation_run_id==ar.id).all():
            alloc_by_segment[res.recipient_segment]+=D(res.allocated_amount)

    source_fingerprint='|'.join(f'{x.import_code}:{x.sha256}' for x in imports)
    mapping_versions='|'.join(sorted({f'{r.mapping_rule_id}' for r in norm}))
    allocation_versions='|'.join(str(x.id) for x in allocations)
    source_hash=hashlib.sha256(f'{source_fingerprint}|{mapping_versions}|{allocation_versions}|{as_of_period}|{ENGINE_VERSION}'.encode()).hexdigest()
    run=PnLRun(
        workspace_id=workspace_id,
        run_code=f'PNL-{as_of_period}-{uuid.uuid4().hex[:8].upper()}',
        as_of_period=as_of_period,
        fiscal_year=fiscal_year,
        source_import_ids=import_ids,
        allocation_run_ids=[x.id for x in allocations],
        mapping_coverage=coverage,
        source_rows=source_rows,
        mapped_rows=mapped_rows,
        unresolved_rows=unresolved,
        source_control_total=source_total,
        normalized_control_total=normalized_total,
        allocation_residual=money(alloc_residual),
        source_hash=source_hash,
        engine_version=ENGINE_VERSION,
        status='CONTROLLED' if abs(alloc_residual) <= Decimal('0.01') else 'CONTROL_EXCEPTION',
        published=publish,
        created_by=created_by,
    )
    db.add(run);db.flush()

    buckets=defaultdict(lambda:{'revenue':Decimal('0'),'cogs':Decimal('0'),'opex':Decimal('0'),'rows':0,'raw_ids':[]})
    for r in norm:
        key=(r.entity_id,r.segment_code,r.controlled_transaction_code,r.policy_code,r.currency)
        b=buckets[key];b['rows']+=1;b['raw_ids'].append(r.raw_record_id)
        if r.financial_classification=='REVENUE': b['revenue']+=D(r.amount)
        elif r.financial_classification=='COGS': b['cogs']+=abs(D(r.amount))
        elif r.financial_classification=='OPEX': b['opex']+=abs(D(r.amount))

    entity_agg=defaultdict(lambda:{'revenue':Decimal('0'),'cogs':Decimal('0'),'opex':Decimal('0'),'segments':0})
    segment_outputs=[]
    for (entity_id,segment,txn,policy_code,currency),b in buckets.items():
        entity=db.get(Entity,entity_id)
        policy=db.query(Policy).filter(Policy.workspace_id==workspace_id,Policy.policy_code==policy_code,Policy.entity_id==entity_id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
        if not policy:
            raise ValueError(f'Active policy {policy_code} not found for {entity.entity_code}')
        allocated=money(alloc_by_segment.get(segment,Decimal('0')))
        direct_opex=money(b['opex'])
        pnl=segmented_pnl(b['revenue'],b['cogs'],direct_opex+allocated)
        tp=calculate_policy_result(policy.method,policy.pli,revenue=pnl.revenue,cogs=pnl.cogs,opex=pnl.opex,target=policy.target,lower=policy.lower_bound or 0,upper=policy.upper_bound or 0,eligible_costs=(pnl.cogs+pnl.opex if policy.method=='COST_PLUS' else None))
        line=PnLSegmentResult(
            pnl_run_id=run.id,entity_id=entity_id,segment_code=segment,controlled_transaction_code=txn,policy_code=policy.policy_code,currency=currency,
            direct_revenue=money(b['revenue']),direct_cogs=money(b['cogs']),direct_opex=direct_opex,allocated_opex=allocated,
            revenue=pnl.revenue,cogs=pnl.cogs,opex=pnl.opex,gross_profit=pnl.gross_profit,ebit=pnl.ebit,pli=tp.actual,
            method=policy.method,pli_name=policy.pli,target=policy.target,status=tp.status,suggested_adjustment=tp.adjustment if tp.status=='RED' else Decimal('0'),
            source_row_count=b['rows'],lineage={'raw_record_ids':b['raw_ids'][:5000],'mapping_rule_ids':sorted({r.mapping_rule_id for r in norm if r.raw_record_id in set(b['raw_ids'])}),'source_import_ids':import_ids,'allocation_run_ids':[x.id for x in allocations],'source_hash':source_hash}
        )
        db.add(line);db.flush()
        segment_outputs.append({'entity_code':entity.entity_code,'segment_code':segment,'transaction_code':txn,'policy_code':policy.policy_code,'currency':currency,'rows':b['rows'],'revenue':float(pnl.revenue),'cogs':float(pnl.cogs),'direct_opex':float(direct_opex),'allocated_opex':float(allocated),'opex':float(pnl.opex),'ebit':float(pnl.ebit),'pli':float(tp.actual),'pli_name':policy.pli,'status':tp.status,'suggested_adjustment':float(line.suggested_adjustment)})
        ea=entity_agg[entity_id];ea['revenue']+=pnl.revenue;ea['cogs']+=pnl.cogs;ea['opex']+=pnl.opex;ea['segments']+=1

    entity_outputs=[]
    if publish:
        for entity_id,b in entity_agg.items():
            entity=db.get(Entity,entity_id)
            policy=db.query(Policy).filter(Policy.workspace_id==workspace_id,Policy.entity_id==entity_id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
            pnl=segmented_pnl(b['revenue'],b['cogs'],b['opex'])
            tp=calculate_policy_result(policy.method,policy.pli,revenue=pnl.revenue,cogs=pnl.cogs,opex=pnl.opex,target=policy.target,lower=policy.lower_bound or 0,upper=policy.upper_bound or 0,eligible_costs=(pnl.cogs+pnl.opex if policy.method=='COST_PLUS' else None))
            fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==entity_id,FinancialPeriod.period==as_of_period).first()
            if not fp:
                fp=FinancialPeriod(workspace_id=workspace_id,entity_id=entity_id,period=as_of_period,revenue=pnl.revenue,cogs=pnl.cogs,opex=pnl.opex,source_import_id=run.run_code)
                db.add(fp)
            else:
                fp.workspace_id=workspace_id;fp.revenue=pnl.revenue;fp.cogs=pnl.cogs;fp.opex=pnl.opex;fp.source_import_id=run.run_code
            calc=Calculation(workspace_id=workspace_id,calculation_code=f'CALC-{entity.entity_code}-{as_of_period}-{run.id}',entity_id=entity_id,policy_id=policy.id,period=as_of_period,revenue=pnl.revenue,ebit=pnl.ebit,actual_pli=tp.actual,target_pli=policy.target,suggested_adjustment=tp.adjustment if tp.status=='RED' else Decimal('0'),engine_version=ENGINE_VERSION,source_hash=source_hash,manifest={'pnl_run_code':run.run_code,'source_import_ids':import_ids,'source_hash':source_hash,'mapping_coverage':float(coverage),'allocation_run_ids':[x.id for x in allocations],'policy_code':policy.policy_code,'policy_version':policy.version,'benchmark_id':policy.benchmark_id,'rounding':'ROUND_HALF_UP','money_precision':'0.01','ratio_precision':'0.00000001','source':'IMPORTED_ERP_DATA'},finalized=True)
            db.add(calc);db.flush()
            if tp.status=='RED':
                exc_code=f'EXC-{entity.entity_code}-{as_of_period}-{run.id}'
                if not db.query(ExceptionCase).filter(ExceptionCase.exception_code==exc_code).first():
                    db.add(ExceptionCase(workspace_id=workspace_id,exception_code=exc_code,entity_id=entity_id,category='PROFITABILITY_BREACH',severity='HIGH',amount=abs(tp.adjustment),owner='manager@otp.local',due_date=None,status='OPEN',evidence={'pnl_run':run.run_code,'calculation':calc.calculation_code,'policy':policy.policy_code,'source_hash':source_hash}))
            entity_outputs.append({'entity_code':entity.entity_code,'segments':b['segments'],'revenue':float(pnl.revenue),'cogs':float(pnl.cogs),'opex':float(pnl.opex),'ebit':float(pnl.ebit),'pli':float(tp.actual),'pli_name':policy.pli,'status':tp.status,'suggested_adjustment':float(tp.adjustment if tp.status=='RED' else Decimal('0')),'financial_period_source':run.run_code,'calculation_code':calc.calculation_code})

    db.flush()
    return {'run_id':run.id,'run_code':run.run_code,'status':run.status,'published':publish,'as_of_period':as_of_period,'source_import_ids':import_ids,'source_rows':source_rows,'mapped_rows':mapped_rows,'unresolved_rows':unresolved,'mapping_coverage':float(coverage),'source_control_total':float(source_total),'normalized_control_total':float(normalized_total),'control_difference':float(money(source_total-normalized_total)),'allocation_run_ids':[x.id for x in allocations],'allocation_residual':float(money(alloc_residual)),'source_hash':source_hash,'segments':segment_outputs,'entities':entity_outputs}


def pnl_drilldown(db: Session, *, workspace_id: int, pnl_run_id: int, entity_code: str | None=None, segment_code: str | None=None, limit: int=500) -> dict:
    run=db.query(PnLRun).filter(PnLRun.id==pnl_run_id,PnLRun.workspace_id==workspace_id).first()
    if not run: raise ValueError('P&L run not found')
    q=db.query(PnLSegmentResult).filter(PnLSegmentResult.pnl_run_id==run.id)
    if entity_code:
        e=db.query(Entity).filter(Entity.workspace_id==workspace_id,Entity.entity_code==entity_code).first()
        if not e: raise ValueError('Entity not found')
        q=q.filter(PnLSegmentResult.entity_id==e.id)
    if segment_code: q=q.filter(PnLSegmentResult.segment_code==segment_code)
    segments=q.all();raw_ids=[]
    for s in segments: raw_ids.extend((s.lineage or {}).get('raw_record_ids',[]))
    raw=db.query(RawFinancialRecord).filter(RawFinancialRecord.id.in_(raw_ids or [-1])).order_by(RawFinancialRecord.id).limit(limit).all()
    return {'run_code':run.run_code,'source_hash':run.source_hash,'segments':[{'entity_code':db.get(Entity,s.entity_id).entity_code,'segment_code':s.segment_code,'transaction_code':s.controlled_transaction_code,'policy_code':s.policy_code,'rows':s.source_row_count,'revenue':float(s.revenue),'cogs':float(s.cogs),'direct_opex':float(s.direct_opex),'allocated_opex':float(s.allocated_opex),'opex':float(s.opex),'ebit':float(s.ebit),'pli':float(s.pli),'status':s.status} for s in segments],'source_rows':[{'id':r.id,'row_number':r.row_number,'period':r.period,'entity_code':r.entity_code,'document_number':r.document_number,'gl_account':r.gl_account,'cost_center':r.cost_center,'profit_center':r.profit_center,'counterparty_code':r.counterparty_code,'currency':r.currency,'amount':float(r.amount),'validation_status':r.validation_status} for r in raw]}
