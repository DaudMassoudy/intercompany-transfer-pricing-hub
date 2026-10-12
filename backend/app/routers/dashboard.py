from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Entity, Policy, FinancialPeriod, Calculation, User, ExceptionCase, Adjustment, Reconciliation
from ..security import current_user, entity_accessible, require_entity_access
from ..services.finance import segmented_pnl, status_for, calculate_policy_result, D
from ..services.forecasting import entity_forecast

router=APIRouter(tags=['control-tower'])

def _row(db,e):
    pol=db.query(Policy).filter(Policy.workspace_id==e.workspace_id,Policy.entity_id==e.id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
    fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==e.id).order_by(FinancialPeriod.period.desc()).first()
    calc=db.query(Calculation).filter(Calculation.entity_id==e.id).order_by(Calculation.id.desc()).first()
    if not (pol and fp and calc): return None
    forecast=entity_forecast(db,e,2026)
    forecast_pli=fp.forecast_ros or Decimal('0')
    if forecast.get('available'):
        pp=forecast['pnl']
        fres=calculate_policy_result(pol.method,pol.pli,revenue=pp['revenue'],cogs=pp['cogs'],opex=pp['opex'],target=pol.target,lower=pol.lower_bound or 0,upper=pol.upper_bound or 0,eligible_costs=(D(pp['cogs'])+D(pp['opex']) if pol.method=='COST_PLUS' else None))
        forecast_pli=fres.actual
    return {'entity_code':e.entity_code,'legal_name':e.legal_name,'characterization':e.characterization,'currency':e.currency,'target':float(pol.target),'lower':float(pol.lower_bound or 0),'upper':float(pol.upper_bound or 0),'actual':float(calc.actual_pli),'forecast':float(forecast_pli or 0),'suggested_adjustment':float(calc.suggested_adjustment),'status':status_for(calc.actual_pli,pol.lower_bound or 0,pol.upper_bound or 0),'method':pol.method,'pli':pol.pli,'policy_version':pol.version,'calculation_version':calc.engine_version,'data_source':(calc.manifest or {}).get('source','SEEDED_DEMO')}

@router.get('/dashboard')
def dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.active==True).order_by(Entity.entity_code)
    rows=[]
    for e in q.all():
        if entity_accessible(db,user,e):
            r=_row(db,e)
            if r: rows.append(r)
    open_exceptions=db.query(ExceptionCase).filter(ExceptionCase.workspace_id==user.workspace_id,ExceptionCase.status=='OPEN').count()
    unrec=db.query(Reconciliation).filter(Reconciliation.workspace_id==user.workspace_id,Reconciliation.status!='RECONCILED').count()
    return {'entities':rows,'kpis':{'entities_monitored':len(rows),'outside_target':sum(1 for r in rows if r['status']=='RED'),'forecast_breaches':sum(1 for r in rows if r['forecast']<r['lower'] or r['forecast']>r['upper']),'proposed_adjustment_value':sum(max(0,r['suggested_adjustment']) for r in rows),'open_exceptions':open_exceptions,'unreconciled_postings':unrec}}

@router.get('/entities')
def entities(user:User=Depends(current_user),db:Session=Depends(get_db)):
    out=[]
    for e in db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.active==True).order_by(Entity.entity_code):
        if entity_accessible(db,user,e):
            out.append({'entity_code':e.entity_code,'legal_name':e.legal_name,'country':e.country,'currency':e.currency,'characterization':e.characterization,'company_code':e.company_code,'erp_system':e.erp_system})
    return out

@router.get('/entities/{code}')
def entity_detail(code:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==code).first()
    if not e: raise HTTPException(404,'Entity not found')
    require_entity_access(db,user,e)
    pol=db.query(Policy).filter(Policy.workspace_id==user.workspace_id,Policy.entity_id==e.id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
    fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==e.id).order_by(FinancialPeriod.period.desc()).first()
    calc=db.query(Calculation).filter(Calculation.entity_id==e.id).order_by(Calculation.id.desc()).first()
    pnl=segmented_pnl(fp.revenue,fp.cogs,fp.opex) if fp else None
    forecast=entity_forecast(db,e,2026)
    return {'entity':{'entity_code':e.entity_code,'legal_name':e.legal_name,'country':e.country,'currency':e.currency,'characterization':e.characterization,'company_code':e.company_code,'erp_system':e.erp_system},'policy':{'policy_code':pol.policy_code,'method':pol.method,'pli':pol.pli,'target':float(pol.target),'lower':float(pol.lower_bound or 0),'median':float(pol.median or 0),'upper':float(pol.upper_bound or 0),'benchmark_id':pol.benchmark_id,'version':pol.version,'transaction_type':pol.transaction_type} if pol else None,'period':fp.period if fp else None,'pnl':pnl.to_dict() if pnl else None,'forecast':forecast,'calculation':{'calculation_code':calc.calculation_code,'actual_pli':float(calc.actual_pli),'target_pli':float(calc.target_pli),'suggested_adjustment':float(calc.suggested_adjustment),'engine_version':calc.engine_version,'source_hash':calc.source_hash,'manifest':calc.manifest} if calc else None}
