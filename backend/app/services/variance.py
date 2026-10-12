from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from sqlalchemy.orm import Session

from ..models import (
    Entity, FinancialPeriod, ForecastLine, ForecastVersion, NormalizedFinancialRecord,
    PnLRun, PnLSegmentResult, RawFinancialRecord, VarianceComponent, VarianceRun, Policy
)
from .finance import D, money, segmented_pnl


def _actual_components(db: Session, workspace_id: int, entity: Entity, period: str) -> dict:
    run=db.query(PnLRun).filter(PnLRun.workspace_id==workspace_id,PnLRun.as_of_period==period,PnLRun.published==True).order_by(PnLRun.id.desc()).first()
    if run:
        segs=db.query(PnLSegmentResult).filter(PnLSegmentResult.pnl_run_id==run.id,PnLSegmentResult.entity_id==entity.id).all()
        if segs:
            return {'revenue':sum((D(s.direct_revenue) for s in segs),Decimal('0')),'cogs':sum((D(s.direct_cogs) for s in segs),Decimal('0')),'direct_opex':sum((D(s.direct_opex) for s in segs),Decimal('0')),'allocated_opex':sum((D(s.allocated_opex) for s in segs),Decimal('0')),'source':run.run_code}
    fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==entity.id,FinancialPeriod.period==period).first()
    if not fp: raise ValueError('Actual financial period not found')
    return {'revenue':D(fp.revenue),'cogs':D(fp.cogs),'direct_opex':D(fp.opex),'allocated_opex':Decimal('0'),'source':fp.source_import_id}


def _budget_baseline(db: Session, workspace_id: int, entity: Entity, period: str) -> dict:
    year=int(period[:4]);month=int(period[5:7])
    ver=db.query(ForecastVersion).filter(ForecastVersion.workspace_id==workspace_id,ForecastVersion.fiscal_year==year,ForecastVersion.scenario=='BUDGET',ForecastVersion.status=='APPROVED').order_by(ForecastVersion.id.desc()).first()
    if not ver: raise ValueError('No approved BUDGET forecast version available')
    lines=db.query(ForecastLine).filter(ForecastLine.forecast_version_id==ver.id,ForecastLine.entity_id==entity.id,ForecastLine.month<=month).all()
    if not lines: raise ValueError('No budget lines available for entity/period')
    return {'revenue':sum((D(x.revenue) for x in lines),Decimal('0')),'cogs':sum((D(x.cogs) for x in lines),Decimal('0')),'direct_opex':sum((D(x.opex) for x in lines),Decimal('0')),'allocated_opex':Decimal('0'),'source':ver.version_code}


def _previous_period(period: str) -> str:
    y=int(period[:4]);m=int(period[5:7]);m-=1
    if m==0:y-=1;m=12
    return f'{y:04d}-{m:02d}'



def _prior_year_period(period: str) -> str:
    y=int(period[:4])-1;m=int(period[5:7]);return f'{y:04d}-{m:02d}'


def _forecast_baseline(db: Session, workspace_id: int, entity: Entity, period: str) -> dict:
    year=int(period[:4]);month=int(period[5:7])
    versions=(db.query(ForecastVersion).filter(ForecastVersion.workspace_id==workspace_id,ForecastVersion.fiscal_year==year,ForecastVersion.status=='APPROVED').order_by(ForecastVersion.id.desc()).all())
    ver=next((v for v in versions if str(v.scenario).upper() in {'BASE','LE1','LE2','LE3','MANAGEMENT'}),None)
    if not ver: raise ValueError('No approved forecast version available')
    lines=db.query(ForecastLine).filter(ForecastLine.forecast_version_id==ver.id,ForecastLine.entity_id==entity.id,ForecastLine.month<=month).all()
    if not lines: raise ValueError('No forecast lines available for entity/period')
    return {'revenue':sum((D(x.revenue) for x in lines),Decimal('0')),'cogs':sum((D(x.cogs) for x in lines),Decimal('0')),'direct_opex':sum((D(x.opex) for x in lines),Decimal('0')),'allocated_opex':Decimal('0'),'source':ver.version_code}


def _target_baseline(db: Session, workspace_id: int, entity: Entity, period: str, actual: dict) -> dict:
    policy=db.query(Policy).filter(Policy.workspace_id==workspace_id,Policy.entity_id==entity.id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
    if not policy: raise ValueError('No active policy available for target variance')
    if policy.pli.upper()!='ROS': raise ValueError('TARGET baseline currently requires ROS policy because revenue/EBIT target must be deterministic')
    revenue=D(actual['revenue']);cogs=D(actual['cogs']);target_ebit=revenue*D(policy.target);opex=revenue-cogs-target_ebit
    return {'revenue':revenue,'cogs':cogs,'direct_opex':opex,'allocated_opex':Decimal('0'),'source':f'{policy.policy_code}:v{policy.version}:TARGET'}


def _driver_data(db:Session, workspace_id:int, entity:Entity, period:str) -> dict[str,dict[str,Decimal]]:
    rows=(db.query(NormalizedFinancialRecord,RawFinancialRecord).join(RawFinancialRecord,RawFinancialRecord.id==NormalizedFinancialRecord.raw_record_id)
          .filter(NormalizedFinancialRecord.workspace_id==workspace_id,NormalizedFinancialRecord.entity_id==entity.id,NormalizedFinancialRecord.period==period).all())
    out={}
    for n,r in rows:
        raw=r.raw_payload or {};product=str(n.product_sku or n.product_group or raw.get('product') or raw.get('sku') or 'UNSPECIFIED')
        q=raw.get('quantity');price=raw.get('unit_price');fx=raw.get('fx_rate')
        if q is None or price is None: continue
        try:q=D(q);price=D(price);fx=D(fx or 1)
        except Exception:continue
        cur=out.setdefault(product,{'quantity':Decimal('0'),'value':Decimal('0'),'fx_weighted':Decimal('0')})
        cur['quantity']+=q;cur['value']+=q*price*fx;cur['fx_weighted']+=q*price*(fx-Decimal('1'))
    return out


def _source_driver_components(db:Session,workspace_id:int,entity:Entity,actual_period:str,baseline_period:str|None) -> list[tuple[str,str,Decimal,str]]:
    if not baseline_period:return []
    a=_driver_data(db,workspace_id,entity,actual_period);b=_driver_data(db,workspace_id,entity,baseline_period)
    if not a or not b:return []
    products=set(a)|set(b);volume=price=mix=fx=Decimal('0')
    total_bq=sum((b.get(p,{}).get('quantity',Decimal('0')) for p in products),Decimal('0'));total_aq=sum((a.get(p,{}).get('quantity',Decimal('0')) for p in products),Decimal('0'))
    avg_b=(sum((b.get(p,{}).get('value',Decimal('0')) for p in products),Decimal('0'))/total_bq) if total_bq else Decimal('0')
    for p in products:
        bq=b.get(p,{}).get('quantity',Decimal('0'));aq=a.get(p,{}).get('quantity',Decimal('0'));bv=b.get(p,{}).get('value',Decimal('0'));av=a.get(p,{}).get('value',Decimal('0'))
        bp=(bv/bq) if bq else avg_b;ap=(av/aq) if aq else bp
        volume+=(aq-bq)*bp;price+=aq*(ap-bp)
        if total_bq and total_aq: mix+=(aq/total_aq-bq/total_bq)*total_aq*bp
        fx+=a.get(p,{}).get('fx_weighted',Decimal('0'))-b.get(p,{}).get('fx_weighted',Decimal('0'))
    return [('VOLUME','Volume effect',money(volume),'source quantity/unit-price fields'),('PRICE','External price effect',money(price),'source quantity/unit-price fields'),('MIX','Product mix effect',money(mix),'source product/quantity fields'),('FX','FX effect',money(fx),'source fx_rate fields')]


def _period_from_imported_rows(db: Session, workspace_id: int, entity: Entity, period: str) -> dict:
    rows=db.query(NormalizedFinancialRecord).filter(NormalizedFinancialRecord.workspace_id==workspace_id,NormalizedFinancialRecord.entity_id==entity.id,NormalizedFinancialRecord.period==period).all()
    if not rows: raise ValueError(f'No normalized imported records for {period}')
    rev=cogs=opex=Decimal('0')
    for r in rows:
        if r.financial_classification=='REVENUE': rev+=D(r.amount)
        elif r.financial_classification=='COGS': cogs+=abs(D(r.amount))
        elif r.financial_classification=='OPEX': opex+=abs(D(r.amount))
    return {'revenue':rev,'cogs':cogs,'direct_opex':opex,'allocated_opex':Decimal('0'),'source':f'IMPORTED-{period}'}


def run_variance(db: Session, *, workspace_id: int, entity_code: str, actual_period: str, baseline_type: str, created_by: str) -> dict:
    entity=db.query(Entity).filter(Entity.workspace_id==workspace_id,Entity.entity_code==entity_code).first()
    if not entity: raise ValueError('Entity not found')
    actual=_actual_components(db,workspace_id,entity,actual_period)
    baseline_type=baseline_type.upper()
    baseline_period=None
    if baseline_type=='BUDGET': baseline=_budget_baseline(db,workspace_id,entity,actual_period);baseline_ref=baseline['source']
    elif baseline_type=='FORECAST': baseline=_forecast_baseline(db,workspace_id,entity,actual_period);baseline_ref=baseline['source']
    elif baseline_type=='TARGET': baseline=_target_baseline(db,workspace_id,entity,actual_period,actual);baseline_ref=baseline['source']
    elif baseline_type=='PRIOR_PERIOD':
        pp=_previous_period(actual_period);baseline_period=pp;baseline=_period_from_imported_rows(db,workspace_id,entity,pp);baseline_ref=pp
        try: actual=_period_from_imported_rows(db,workspace_id,entity,actual_period)
        except ValueError: pass
    elif baseline_type=='PRIOR_YEAR':
        pp=_prior_year_period(actual_period);baseline_period=pp;baseline=_period_from_imported_rows(db,workspace_id,entity,pp);baseline_ref=pp
        try: actual=_period_from_imported_rows(db,workspace_id,entity,actual_period)
        except ValueError: pass
    else: raise ValueError('baseline_type must be BUDGET, FORECAST, TARGET, PRIOR_PERIOD or PRIOR_YEAR')

    base_pnl=segmented_pnl(baseline['revenue'],baseline['cogs'],baseline['direct_opex']+baseline['allocated_opex'])
    act_pnl=segmented_pnl(actual['revenue'],actual['cogs'],actual['direct_opex']+actual['allocated_opex'])
    advanced=_source_driver_components(db,workspace_id,entity,actual_period,baseline_period)
    revenue_delta=D(actual['revenue'])-D(baseline['revenue'])
    if advanced:
        advanced_total=sum((x[2] for x in advanced),Decimal('0'))
        components=advanced+[('REVENUE_RESIDUAL','Revenue residual not attributable to available source drivers',money(revenue_delta-advanced_total),'deterministic residual from source revenue control')]
    else:
        components=[('REVENUE','Revenue / Umsatzerlöse',revenue_delta,'source financial records')]
    components += [
        ('COGS','COGS / Umsatzkosten',-(D(actual['cogs'])-D(baseline['cogs'])),'source financial records'),
        ('DIRECT_OPEX','Direct OPEX / Direkte OPEX',-(D(actual['direct_opex'])-D(baseline['direct_opex'])),'source financial records'),
        ('ALLOCATIONS','Allocations / Umlagen',-(D(actual['allocated_opex'])-D(baseline['allocated_opex'])),'allocation engine'),
    ]
    comp_total=money(sum((x[2] for x in components),Decimal('0')))
    ebit_variance=money(act_pnl.ebit-base_pnl.ebit)
    residual=money(ebit_variance-comp_total)
    status='CONTROLLED' if abs(residual)<=Decimal('0.01') else 'CONTROL_EXCEPTION'
    vr=VarianceRun(workspace_id=workspace_id,run_code=f'VAR-{entity_code}-{actual_period}-{uuid.uuid4().hex[:8].upper()}',entity_id=entity.id,actual_period=actual_period,baseline_type=baseline_type,baseline_reference=baseline_ref,currency=entity.currency,baseline_revenue=money(baseline['revenue']),baseline_cogs=money(baseline['cogs']),baseline_direct_opex=money(baseline['direct_opex']),baseline_allocated_opex=money(baseline['allocated_opex']),actual_revenue=money(actual['revenue']),actual_cogs=money(actual['cogs']),actual_direct_opex=money(actual['direct_opex']),actual_allocated_opex=money(actual['allocated_opex']),baseline_ebit=base_pnl.ebit,actual_ebit=act_pnl.ebit,ebit_variance=ebit_variance,component_total=comp_total,residual=residual,status=status,created_by=created_by)
    db.add(vr);db.flush()
    out=[]
    for i,(code,label,amount,source) in enumerate(components,1):
        amount=money(amount);vc=VarianceComponent(variance_run_id=vr.id,component_order=i,component_code=code,label=label,amount=amount,direction='FAVORABLE' if amount>0 else ('UNFAVORABLE' if amount<0 else 'NEUTRAL'),source=source,evidence={'baseline':baseline_ref,'actual_source':actual['source']});db.add(vc)
        out.append({'code':code,'label':label,'amount':float(amount),'direction':vc.direction,'source':source})
    policy=db.query(Policy).filter(Policy.workspace_id==workspace_id,Policy.entity_id==entity.id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
    db.flush()
    return {'run_id':vr.id,'run_code':vr.run_code,'entity_code':entity_code,'currency':entity.currency,'actual_period':actual_period,'baseline_type':baseline_type,'baseline_reference':baseline_ref,'baseline':{'revenue':float(base_pnl.revenue),'cogs':float(base_pnl.cogs),'opex':float(base_pnl.opex),'ebit':float(base_pnl.ebit),'ros':float(base_pnl.ros)},'actual':{'revenue':float(act_pnl.revenue),'cogs':float(act_pnl.cogs),'opex':float(act_pnl.opex),'ebit':float(act_pnl.ebit),'ros':float(act_pnl.ros)},'ebit_variance':float(ebit_variance),'component_total':float(comp_total),'residual':float(residual),'status':status,'components':out,'policy':{'policy_code':policy.policy_code,'pli':policy.pli,'target':float(policy.target),'lower':float(policy.lower_bound or 0),'upper':float(policy.upper_bound or 0)} if policy else None,'methodology_note':'EBIT bridge is fully additive and reconciled. Volume/price/mix/FX drivers are calculated only when source quantity, unit-price, product and FX fields exist; any remaining revenue difference is explicitly shown as a deterministic residual rather than silently balanced.'}
