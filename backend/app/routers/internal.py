from __future__ import annotations
from decimal import Decimal
import os, uuid
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Entity, Policy, FinancialPeriod, Calculation, ExceptionCase, WorkflowRun, Notification, AllocationRule, SourceImport
from ..services.finance import calculate_policy_result, segmented_pnl, status_for
from ..services.forecasting import entity_forecast
from ..services.mapping import run_mapping
from ..services.allocations import run_allocation
from ..services.audit import audit
from ..services.pnl_builder import build_authoritative_pnl
from ..services.variance import run_variance
from ..settings import settings

router=APIRouter(prefix='/internal',tags=['n8n-internal'])

def integration_guard(x_integration_key:str=Header(default='')):
    if not x_integration_key or x_integration_key != settings.n8n_integration_key: raise HTTPException(401,'Invalid integration key')
    return True

def _workspace(db):
    e=db.query(Entity).filter(Entity.workspace_id.isnot(None)).first()
    return e.workspace_id if e else None

def _run(db,name,payload=None,status='RUNNING'):
    ws=_workspace(db);cid=str(uuid.uuid4());r=WorkflowRun(workspace_id=ws,workflow_name=name,correlation_id=cid,status=status,payload=payload or {});db.add(r);db.flush();return r

@router.post('/source-availability')
def source_availability(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    run=_run(db,'MONTHLY_OTP_CLOSE',{'step':'source_availability'});run.status='SUCCESS';db.commit();return {'correlation_id':run.correlation_id,'available':True,'source':'DEMO_ERP'}

@router.post('/data-quality')
def data_quality(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);red=db.query(Entity).filter(Entity.workspace_id==ws).count()==0
    return {'ok':not red,'critical_errors':0 if not red else 1,'mapping_threshold':0.98}

@router.post('/mapping-run')
def mapping_run(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);result=run_mapping(db,ws,None);db.commit();return result

@router.post('/allocation-run')
def allocation_run(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);rule=db.query(AllocationRule).filter(AllocationRule.workspace_id==ws,AllocationRule.status=='ACTIVE').first()
    if not rule: return {'status':'SKIPPED','reason':'No active allocation rule'}
    result=run_allocation(db,rule,'2026-09',1_000_000,rule.recipients);db.commit();return result

@router.post('/calculation-run')
def calculation_run(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db)
    imports=db.query(SourceImport).filter(SourceImport.workspace_id==ws,SourceImport.status.in_(['VALIDATED','PARTIAL','ACCEPTED'])).count()
    if imports:
        try:
            result=build_authoritative_pnl(db,workspace_id=ws,as_of_period='2026-09',created_by='n8n-service',publish=True)
            db.commit();return {'mode':'IMPORTED_ERP_AUTHORITATIVE','processed':len(result['entities']),'pnl_run':result['run_code'],'results':result['entities']}
        except ValueError as exc:
            db.rollback();return {'mode':'IMPORTED_ERP_BLOCKED','processed':0,'error':str(exc)}
    out=[]
    for e in db.query(Entity).filter(Entity.workspace_id==ws).all():
        p=db.query(Policy).filter(Policy.entity_id==e.id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first();fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==e.id).order_by(FinancialPeriod.period.desc()).first()
        if not p or not fp: continue
        res=calculate_policy_result(p.method,p.pli,revenue=fp.revenue,cogs=fp.cogs,opex=fp.opex,target=p.target,lower=p.lower_bound or 0,upper=p.upper_bound or 0,eligible_costs=(fp.cogs+fp.opex if p.method=='COST_PLUS' else None));out.append({'entity_code':e.entity_code,'actual':float(res.actual),'target':float(res.target),'status':res.status,'adjustment':float(res.adjustment)})
    return {'mode':'SEEDED_FALLBACK','processed':len(out),'results':out}

@router.post('/variance-run')
def variance_run(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);out=[]
    for e in db.query(Entity).filter(Entity.workspace_id==ws).all():
        if not db.query(Policy).filter(Policy.entity_id==e.id,Policy.status=='ACTIVE').first(): continue
        try: out.append(run_variance(db,workspace_id=ws,entity_code=e.entity_code,actual_period='2026-09',baseline_type='BUDGET',created_by='n8n-service'))
        except ValueError: continue
    db.commit();return {'processed':len(out),'results':[{'entity_code':x['entity_code'],'ebit_variance':x['ebit_variance'],'residual':x['residual'],'status':x['status']} for x in out]}

@router.post('/forecast-run')
def forecast_run(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);out=[]
    for e in db.query(Entity).filter(Entity.workspace_id==ws).all():
        f=entity_forecast(db,e,2026);out.append({'entity_code':e.entity_code,'available':f.get('available'),'ros':f.get('pnl',{}).get('ros')})
    return {'processed':len(out),'results':out}

@router.post('/exception-detection')
def exception_detection(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);exceptions=[]
    for e in db.query(Entity).filter(Entity.workspace_id==ws).all():
        p=db.query(Policy).filter(Policy.entity_id==e.id,Policy.status=='ACTIVE').first();c=db.query(Calculation).filter(Calculation.entity_id==e.id).order_by(Calculation.id.desc()).first()
        if p and c and status_for(c.actual_pli,p.lower_bound or 0,p.upper_bound or 0)=='RED': exceptions.append(e.entity_code)
    return {'exceptions':exceptions,'count':len(exceptions)}

@router.post('/notify')
def notify(subject:str='OTP workflow notification',recipient:str='manager@otp.local',_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);n=Notification(workspace_id=ws,recipient=recipient,channel='IN_APP',subject=subject,body='Generated by n8n orchestration workflow',status='SENT');db.add(n);db.commit();return {'status':'SENT','recipient':recipient}

@router.post('/monthly-close')
def monthly_close(_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);run=_run(db,'MONTHLY_OTP_CLOSE',{'period':'2026-09'})
    rows=[]
    for e in db.query(Entity).filter(Entity.workspace_id==ws).all():
        p=db.query(Policy).filter(Policy.entity_id==e.id,Policy.status=='ACTIVE').first();c=db.query(Calculation).filter(Calculation.entity_id==e.id).order_by(Calculation.id.desc()).first()
        if p and c: rows.append({'entity_code':e.entity_code,'actual':float(c.actual_pli),'target':float(p.target),'status':status_for(c.actual_pli,p.lower_bound or 0,p.upper_bound or 0)})
    run.status='SUCCESS';run.payload={'period':'2026-09','processed_entities':len(rows),'exceptions':[r for r in rows if r['status']=='RED']};audit(db,event_type='N8N_MONTHLY_CLOSE',actor='n8n-service',actor_role='INTEGRATION_SERVICE',workspace_id=ws,correlation_id=run.correlation_id,details=f'Processed {len(rows)} entities',source_system='n8n');db.commit();return {'correlation_id':run.correlation_id,**run.payload}

@router.post('/workflow-event')
def workflow_event(event_name:str,entity_code:str|None=None,_:bool=Depends(integration_guard),db:Session=Depends(get_db)):
    ws=_workspace(db);run=_run(db,event_name,{'entity_code':entity_code});run.status='SUCCESS';audit(db,event_type=f'N8N_{event_name.upper()}',actor='n8n-service',actor_role='INTEGRATION_SERVICE',workspace_id=ws,entity_code=entity_code,correlation_id=run.correlation_id,details=f'n8n workflow event: {event_name}',source_system='n8n');db.commit();return {'status':'accepted','correlation_id':run.correlation_id,'event_name':event_name}
