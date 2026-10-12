from collections import defaultdict
from decimal import Decimal
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import get_db
from ..models import User, Entity, Policy, FinancialPeriod, Calculation, NormalizedFinancialRecord, Simulation, ExceptionCase, ForecastVersion, PnLRun, PnLSegmentResult, VarianceRun, VarianceComponent
from ..security import require_permission, require_entity_access
from ..services.finance import segmented_pnl, goal_seek_cogs_for_ros, goal_seek_unit_ic_price, simulate_price_effect, D, money, status_for, calculate_policy_result
from ..services.forecasting import entity_forecast
from ..services.audit import audit
from ..services.pnl_builder import build_authoritative_pnl, pnl_drilldown
from ..services.variance import run_variance

router=APIRouter(tags=['operational-tp'])

@router.get('/pnl/segmented')
def segmented(entity_code:str|None=None,period:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(NormalizedFinancialRecord).filter(NormalizedFinancialRecord.workspace_id==user.workspace_id)
    if entity_code:
        e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==entity_code).first()
        if not e: raise HTTPException(404,'Entity not found')
        require_entity_access(db,user,e);q=q.filter(NormalizedFinancialRecord.entity_id==e.id)
    if period: q=q.filter(NormalizedFinancialRecord.period==period)
    buckets=defaultdict(lambda:{'revenue':Decimal('0'),'cogs':Decimal('0'),'opex':Decimal('0')})
    for r in q.all():
        b=buckets[(r.entity_id,r.segment_code,r.controlled_transaction_code,r.currency)]
        if r.financial_classification=='REVENUE': b['revenue']+=D(r.amount)
        elif r.financial_classification=='COGS': b['cogs']+=abs(D(r.amount))
        elif r.financial_classification=='OPEX': b['opex']+=abs(D(r.amount))
    out=[]
    for (entity_id,seg,txn,ccy),b in buckets.items():
        e=db.get(Entity,entity_id); pnl=segmented_pnl(b['revenue'],b['cogs'],b['opex'])
        out.append({'entity_code':e.entity_code,'segment_code':seg,'controlled_transaction_code':txn,'currency':ccy,**pnl.to_dict()})
    # Fallback seeded aggregate view until user imports real GL.
    if not out:
        fq=db.query(FinancialPeriod).join(Entity).filter(Entity.workspace_id==user.workspace_id)
        if entity_code: fq=fq.filter(Entity.entity_code==entity_code)
        if period: fq=fq.filter(FinancialPeriod.period==period)
        for fp in fq.all():
            e=db.get(Entity,fp.entity_id); pnl=segmented_pnl(fp.revenue,fp.cogs,fp.opex)
            out.append({'entity_code':e.entity_code,'segment_code':f'{e.entity_code}-CORE','controlled_transaction_code':'SEEDED-DEMO','currency':e.currency,**pnl.to_dict(),'source':'seeded_aggregate'})
    return out

@router.get('/forecasts/{entity_code}')
def forecast(entity_code:str,fiscal_year:int=2026,version_code:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==entity_code).first()
    if not e: raise HTTPException(404,'Entity not found')
    require_entity_access(db,user,e)
    result=entity_forecast(db,e,fiscal_year,version_code)
    result['currency']=e.currency
    if result.get('available'):
        pol=db.query(Policy).filter(Policy.workspace_id==user.workspace_id,Policy.entity_id==e.id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
        if pol:
            pp=result['pnl']
            pres=calculate_policy_result(pol.method,pol.pli,revenue=pp['revenue'],cogs=pp['cogs'],opex=pp['opex'],target=pol.target,lower=pol.lower_bound or 0,upper=pol.upper_bound or 0,eligible_costs=(D(pp['cogs'])+D(pp['opex']) if pol.method=='COST_PLUS' else None))
            result['status']=pres.status
            result['target']=float(pol.target)
            result['forecast_pli']=float(pres.actual)
            result['pli_name']=pol.pli
            result['method']=pol.method
            result['anticipated_adjustment']=float(pres.adjustment)
    return result

class SimIn(BaseModel):
    entity_code:str
    ic_purchase_delta:float=0
    target_ros:float|None=None
    units:float|None=None
    non_ic_cogs:float|None=None

@router.post('/simulations')
def simulation(body:SimIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==body.entity_code).first()
    if not e: raise HTTPException(404,'Entity not found')
    require_entity_access(db,user,e,write=True)
    fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==e.id).order_by(FinancialPeriod.period.desc()).first()
    pol=db.query(Policy).filter(Policy.workspace_id==user.workspace_id,Policy.entity_id==e.id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
    if not fp or not pol: raise HTTPException(404,'Financial period or policy missing')
    result=simulate_price_effect(fp.revenue,fp.cogs,fp.opex,body.ic_purchase_delta)
    target=D(body.target_ros) if body.target_ros is not None else D(pol.target)
    outputs={'simulated_pnl':result.to_dict(),'target_ros':float(target),'required_total_cogs':float(goal_seek_cogs_for_ros(fp.revenue,fp.opex,target))}
    if body.units and body.non_ic_cogs is not None:
        outputs['required_unit_ic_price']=float(goal_seek_unit_ic_price(fp.revenue,fp.opex,target,body.non_ic_cogs,body.units))
    sim=Simulation(workspace_id=user.workspace_id,simulation_code=f'SIM-{uuid.uuid4().hex[:10].upper()}',entity_id=e.id,period=fp.period,inputs=body.model_dump(),outputs=outputs,created_by=user.email)
    db.add(sim);audit(db,event_type='SIMULATION_RUN',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='simulation',object_id=sim.simulation_code,new=outputs,details='Immutable TP price-setting simulation');db.commit()
    return {'simulation_code':sim.simulation_code,'currency':e.currency,**outputs}

# Backward compatible query-param simulation from v0.x frontend
@router.post('/simulations-legacy')
def simulation_legacy(entity_code:str,ic_purchase_delta:float,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    return simulation(SimIn(entity_code=entity_code,ic_purchase_delta=ic_purchase_delta),user,db)

@router.get('/policies')
def policies(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    out=[]
    for p in db.query(Policy).filter(Policy.workspace_id==user.workspace_id).order_by(Policy.policy_code,Policy.version.desc()):
        e=db.get(Entity,p.entity_id)
        out.append({'id':p.id,'policy_code':p.policy_code,'version':p.version,'entity_code':e.entity_code,'transaction_type':p.transaction_type,'tested_party_code':p.tested_party_code,'method':p.method,'pli':p.pli,'target':float(p.target),'lower':float(p.lower_bound or 0),'median':float(p.median or 0),'upper':float(p.upper_bound or 0),'markup':float(p.markup) if p.markup is not None else None,'status':p.status,'benchmark_id':p.benchmark_id,'true_up_frequency':p.true_up_frequency,'materiality_threshold':float(p.materiality_threshold or 0),'tolerance':float(p.tolerance) if p.tolerance is not None else None,'cost_base':p.cost_base,'allocation_treatment':p.allocation_treatment,'currency':p.currency,'journal_template_code':p.journal_template_code,'workflow_code':p.workflow_code,'created_by':p.created_by,'approved_by':p.approved_by,'approval_matrix':p.approval_matrix})
    return out

@router.get('/exceptions')
def exceptions(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(ExceptionCase).filter(ExceptionCase.workspace_id==user.workspace_id).order_by(ExceptionCase.id.desc()).all()
    return [{'id':x.id,'exception_code':x.exception_code,'entity_code':db.get(Entity,x.entity_id).entity_code if x.entity_id else None,'category':x.category,'severity':x.severity,'amount':float(x.amount) if x.amount is not None else None,'currency':x.currency or (db.get(Entity,x.entity_id).currency if x.entity_id else None),'owner':x.owner,'due_date':x.due_date,'status':x.status,'source':x.source,'root_cause':x.root_cause,'remediation':x.remediation,'comments':x.comments or [],'evidence':x.evidence,'resolution':x.resolution,'waived_by':x.waived_by,'waiver_reason':x.waiver_reason,'created_at':x.created_at.isoformat() if x.created_at else None} for x in rows]


class PnLBuildIn(BaseModel):
    as_of_period:str='2026-09'
    import_ids:list[int]|None=None
    publish:bool=True

@router.post('/pnl/build')
def build_pnl(body:PnLBuildIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    try:
        result=build_authoritative_pnl(db,workspace_id=user.workspace_id,as_of_period=body.as_of_period,created_by=user.email,source_import_ids=body.import_ids,publish=body.publish)
    except ValueError as exc:
        raise HTTPException(409,str(exc))
    audit(db,event_type='AUTHORITATIVE_PNL_BUILT',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='pnl_run',object_id=result['run_code'],new={'source_rows':result['source_rows'],'mapped_rows':result['mapped_rows'],'entities':len(result['entities']),'source_hash':result['source_hash']},details=f"Imported-data P&L published for {body.as_of_period}")
    db.commit();return result

@router.get('/pnl/runs')
def pnl_runs(limit:int=50,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(PnLRun).filter(PnLRun.workspace_id==user.workspace_id).order_by(PnLRun.id.desc()).limit(min(limit,200)).all()
    return [{'id':x.id,'run_code':x.run_code,'as_of_period':x.as_of_period,'status':x.status,'published':x.published,'source_rows':x.source_rows,'mapped_rows':x.mapped_rows,'unresolved_rows':x.unresolved_rows,'mapping_coverage':float(x.mapping_coverage),'source_control_total':float(x.source_control_total),'normalized_control_total':float(x.normalized_control_total),'allocation_residual':float(x.allocation_residual),'source_hash':x.source_hash,'engine_version':x.engine_version,'created_by':x.created_by,'created_at':x.created_at.isoformat()} for x in rows]

@router.get('/pnl/runs/{run_id}')
def pnl_run_detail(run_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    run=db.query(PnLRun).filter(PnLRun.id==run_id,PnLRun.workspace_id==user.workspace_id).first()
    if not run: raise HTTPException(404,'P&L run not found')
    rows=db.query(PnLSegmentResult).filter(PnLSegmentResult.pnl_run_id==run.id).all()
    return {'run':{'id':run.id,'run_code':run.run_code,'as_of_period':run.as_of_period,'status':run.status,'published':run.published,'source_import_ids':run.source_import_ids,'allocation_run_ids':run.allocation_run_ids,'mapping_coverage':float(run.mapping_coverage),'source_rows':run.source_rows,'mapped_rows':run.mapped_rows,'unresolved_rows':run.unresolved_rows,'source_control_total':float(run.source_control_total),'normalized_control_total':float(run.normalized_control_total),'allocation_residual':float(run.allocation_residual),'source_hash':run.source_hash,'engine_version':run.engine_version},'segments':[{'entity_code':db.get(Entity,x.entity_id).entity_code,'segment_code':x.segment_code,'controlled_transaction_code':x.controlled_transaction_code,'policy_code':x.policy_code,'currency':x.currency,'source_row_count':x.source_row_count,'direct_revenue':float(x.direct_revenue),'direct_cogs':float(x.direct_cogs),'direct_opex':float(x.direct_opex),'allocated_opex':float(x.allocated_opex),'revenue':float(x.revenue),'cogs':float(x.cogs),'opex':float(x.opex),'gross_profit':float(x.gross_profit),'ebit':float(x.ebit),'pli':float(x.pli),'pli_name':x.pli_name,'target':float(x.target),'status':x.status,'suggested_adjustment':float(x.suggested_adjustment)} for x in rows]}

@router.get('/pnl/runs/{run_id}/drilldown')
def pnl_run_drilldown(run_id:int,entity_code:str|None=None,segment_code:str|None=None,limit:int=500,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    try: return pnl_drilldown(db,workspace_id=user.workspace_id,pnl_run_id=run_id,entity_code=entity_code,segment_code=segment_code,limit=min(limit,2000))
    except ValueError as exc: raise HTTPException(404,str(exc))

class VarianceIn(BaseModel):
    entity_code:str
    actual_period:str='2026-09'
    baseline_type:str='BUDGET'

@router.post('/variance/run')
def variance(body:VarianceIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==body.entity_code).first()
    if not e: raise HTTPException(404,'Entity not found')
    require_entity_access(db,user,e,write=True)
    try: result=run_variance(db,workspace_id=user.workspace_id,entity_code=body.entity_code,actual_period=body.actual_period,baseline_type=body.baseline_type,created_by=user.email)
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,event_type='VARIANCE_RUN',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='variance_run',object_id=result['run_code'],new={'baseline_type':body.baseline_type,'ebit_variance':result['ebit_variance'],'residual':result['residual']},details='Deterministic profitability variance decomposition')
    db.commit();return result

@router.get('/variance/runs')
def variance_runs(entity_code:str|None=None,limit:int=50,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(VarianceRun).filter(VarianceRun.workspace_id==user.workspace_id)
    if entity_code:
        e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==entity_code).first()
        if not e: raise HTTPException(404,'Entity not found')
        q=q.filter(VarianceRun.entity_id==e.id)
    out=[]
    for r in q.order_by(VarianceRun.id.desc()).limit(min(limit,200)):
        comps=db.query(VarianceComponent).filter(VarianceComponent.variance_run_id==r.id).order_by(VarianceComponent.component_order).all()
        out.append({'id':r.id,'run_code':r.run_code,'entity_code':db.get(Entity,r.entity_id).entity_code,'actual_period':r.actual_period,'baseline_type':r.baseline_type,'baseline_reference':r.baseline_reference,'currency':r.currency,'baseline_ebit':float(r.baseline_ebit),'actual_ebit':float(r.actual_ebit),'ebit_variance':float(r.ebit_variance),'component_total':float(r.component_total),'residual':float(r.residual),'status':r.status,'components':[{'code':x.component_code,'label':x.label,'amount':float(x.amount),'direction':x.direction,'source':x.source} for x in comps]})
    return out
