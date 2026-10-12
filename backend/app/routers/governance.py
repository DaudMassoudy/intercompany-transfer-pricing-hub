import os, time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db import get_db
from ..models import Notification, User, AuditEvent, Entity, Policy, FinancialPeriod, Calculation, AIInvocation, IntegrationConnection, ExceptionCase, SourceImport, MappingRule, AllocationRule, QualificationControl
from ..security import require_permission, current_user, entity_accessible
from ..services.finance import status_for
from ..settings import settings
from ..services.erp import SimulatedSAPConnector, SAPS4ConnectorContract
from ..services.qualification import qualification_summary

router=APIRouter(tags=['governance'])

def _audit_dict(x):
    return {'id':x.id,'event_type':x.event_type,'actor':x.actor,'actor_role':x.actor_role,'entity_code':x.entity_code,'object_type':x.object_type,'object_id':x.object_id,'previous_value':x.previous_value,'new_value':x.new_value,'details':x.details,'reason':x.reason,'request_id':x.request_id,'correlation_id':x.correlation_id,'source_system':x.source_system,'created_at':x.created_at.isoformat()}

@router.get('/audit')
def audit_events(limit:int=200,actor:str|None=None,entity_code:str|None=None,object_type:str|None=None,object_id:str|None=None,correlation_id:str|None=None,event_type:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(AuditEvent).filter(AuditEvent.workspace_id==user.workspace_id)
    if actor:q=q.filter(AuditEvent.actor==actor)
    if entity_code:q=q.filter(AuditEvent.entity_code==entity_code.upper())
    if object_type:q=q.filter(AuditEvent.object_type==object_type)
    if object_id:q=q.filter(AuditEvent.object_id==object_id)
    if correlation_id:q=q.filter(AuditEvent.correlation_id==correlation_id)
    if event_type:q=q.filter(AuditEvent.event_type==event_type.upper())
    return [_audit_dict(x) for x in q.order_by(AuditEvent.id.desc()).limit(min(limit,1000)).all()]

@router.get('/audit/timeline/{object_type}/{object_id}')
def audit_timeline(object_type:str,object_id:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=(db.query(AuditEvent).filter(AuditEvent.workspace_id==user.workspace_id,AuditEvent.object_type==object_type,AuditEvent.object_id==object_id)
          .order_by(AuditEvent.id.asc()).all())
    if not rows: raise HTTPException(404,'Audit timeline not found')
    return {'object_type':object_type,'object_id':object_id,'events':[_audit_dict(x) for x in rows]}

@router.get('/ai/explain/{entity_code}')
def explain(entity_code:str,lang:str='en',user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==entity_code).first()
    if not e or not entity_accessible(db,user,e): raise HTTPException(404,'Entity not found')
    pol=db.query(Policy).filter(Policy.workspace_id==user.workspace_id,Policy.entity_id==e.id,Policy.status=='ACTIVE').order_by(Policy.id.desc()).first()
    fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==e.id).order_by(FinancialPeriod.period.desc()).first()
    calc=db.query(Calculation).filter(Calculation.entity_id==e.id).order_by(Calculation.id.desc()).first()
    if not all([pol,fp,calc]): raise HTTPException(404,'Missing evidence')
    status=status_for(calc.actual_pli,pol.lower_bound or 0,pol.upper_bound or 0)
    german=str(lang).lower().startswith('de')
    if german:
        pct=lambda x: f'{float(x)*100:.2f}'.replace('.',',')+' %'
        raw=f'{float(calc.suggested_adjustment):,.2f}'
        amount=raw.replace(',','§').replace('.',',').replace('§','.')
        status_de={'RED':'ROT','GREEN':'GRÜN','AMBER':'GELB'}.get(status,status)
        answer=(f'{entity_code} hat den Status {status_de}. Der tatsächliche {pol.pli} beträgt {pct(calc.actual_pli)} gegenüber einem Zielwert von {pct(pol.target)} und einer genehmigten Bandbreite von {pct(pol.lower_bound or 0)}–{pct(pol.upper_bound or 0)}. '
                f'Die deterministische Berechnungs-Engine ermittelt eine Zielanpassung von {amount} {e.currency}. Die Aussage basiert auf Richtlinie {pol.policy_code} v{pol.version}, Finanzperiode {fp.period} und Berechnungsmanifest {calc.calculation_code}.')
        note='Für diese Version ist kein externes LLM erforderlich. Die Provider-Abstraktion ist für freigegebene lokale bzw. Enterprise-Modelle vorbereitet.'
        prompt_version='otp-grounded-v2-de'
    else:
        answer=(f'{entity_code} is {status}. Actual {pol.pli} is {float(calc.actual_pli):.2%} versus target {float(pol.target):.2%} and approved range {float(pol.lower_bound or 0):.2%}–{float(pol.upper_bound or 0):.2%}. '
                f'The deterministic engine calculates a target adjustment of {float(calc.suggested_adjustment):,.2f} {e.currency}. The conclusion is based on policy {pol.policy_code} v{pol.version}, financial period {fp.period}, and calculation manifest {calc.calculation_code}.')
        note='No external LLM is required for this release. Provider abstraction is ready for approved local/enterprise models.'
        prompt_version='otp-grounded-v2-en'
    citations=[{'type':'policy','id':pol.policy_code,'version':pol.version},{'type':'financial_period','id':fp.source_import_id,'period':fp.period},{'type':'calculation_manifest','id':calc.calculation_code,'engine_version':calc.engine_version}]
    inv=AIInvocation(workspace_id=user.workspace_id,user_email=user.email,provider=settings.ai_provider,model=settings.ai_model,prompt_version=prompt_version,retrieval_context={'entity':entity_code,'period':fp.period,'language':'de' if german else 'en'},response_text=answer,citations=citations,review_status='DETERMINISTIC_GROUNDED')
    db.add(inv);db.commit()
    return {'answer':answer,'sources':citations,'mode':'DETERMINISTIC_GROUNDED','language':'de' if german else 'en','note':note}

@router.get('/integrations')
def integrations(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(IntegrationConnection).filter(IntegrationConnection.workspace_id==user.workspace_id).all()
    out=[]
    for x in rows:
        if x.connector_type=='SAP_S4_SIMULATOR': health=SimulatedSAPConnector().health_check()
        elif x.connector_type=='SAP_S4': health=SAPS4ConnectorContract().health_check()
        else: health={'status':'contract-only'}
        out.append({'id':x.id,'connection_code':x.connection_code,'connector_type':x.connector_type,'status':x.status,'config':x.config,'health':health,'secret_reference':x.secret_reference,'created_at':x.created_at.isoformat() if x.created_at else None,'updated_at':x.updated_at.isoformat() if x.updated_at else None})
    return out

@router.get('/data-quality')
def data_quality(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    imports=db.query(SourceImport).filter(SourceImport.workspace_id==user.workspace_id).all()
    total=sum(x.row_count for x in imports);accepted=sum(x.accepted_rows for x in imports);rejected=sum(x.rejected_rows for x in imports);warnings=sum(x.warning_rows for x in imports)
    rules=db.query(MappingRule).filter(MappingRule.workspace_id==user.workspace_id,MappingRule.status=='ACTIVE').count();alloc=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.status=='ACTIVE').count()
    open_exc=db.query(ExceptionCase).filter(ExceptionCase.workspace_id==user.workspace_id,ExceptionCase.status.in_(['OPEN','IN_PROGRESS','TRIAGED','INVESTIGATING'])).count()
    blocking_exc=db.query(ExceptionCase).filter(ExceptionCase.workspace_id==user.workspace_id,ExceptionCase.status.in_(['OPEN','IN_PROGRESS','TRIAGED','INVESTIGATING']),ExceptionCase.severity.in_(['BLOCKING','ERROR','HIGH'])).count()
    seen={};dups=0
    for x in imports:
        key=(x.sha256,x.source_system,x.period)
        if key in seen: dups+=1
        seen[key]=1
    technical=100.0 if total==0 else round(100*accepted/total,2)
    dimensions={
      'technical_schema_validity':technical,
      'completeness':100.0 if rejected==0 else max(0.0,round(100*(total-rejected)/max(total,1),2)),
      'uniqueness':100.0 if not imports else max(0.0,round(100*(len(imports)-dups)/max(len(imports),1),2)),
      'referential_integrity':100.0 if rules>0 else 0.0,
      'consistency':100.0 if blocking_exc==0 else max(0.0,100.0-blocking_exc*5),
      'timeliness':100.0,
      'business_rule_validity':100.0 if open_exc==0 else max(0.0,100.0-open_exc*2),
      'downstream_control_readiness':100.0 if rules>0 and alloc>0 and blocking_exc==0 and rejected==0 else (70.0 if rules>0 and rejected==0 else 30.0),
    }
    readiness='READY' if dimensions['downstream_control_readiness']>=95 else ('CONDITIONAL' if dimensions['downstream_control_readiness']>=60 else 'BLOCKED')
    return {'imports':len(imports),'rows':total,'accepted':accepted,'rejected':rejected,'warnings':warnings,'validity_pct':technical,'active_mapping_rules':rules,'active_allocation_rules':alloc,'open_exceptions':open_exc,'blocking_exceptions':blocking_exc,'duplicate_imports':dups,'dimensions':dimensions,'readiness':readiness}

@router.get('/system-health')
def system_health(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    from datetime import datetime, timezone
    checked=datetime.now(timezone.utc).isoformat();services=[]
    t0=time.perf_counter();db.execute(text('SELECT 1'));services.append({'service':'FastAPI','status':'HEALTHY','latency_ms':0.0,'version':settings.app_version});services.append({'service':'PostgreSQL','status':'HEALTHY','latency_ms':round((time.perf_counter()-t0)*1000,2),'version':'database'})
    try:
        import redis as redis_lib
        t0=time.perf_counter();r=redis_lib.Redis.from_url(settings.redis_url,socket_connect_timeout=0.6,socket_timeout=0.6);r.ping();services.append({'service':'Redis','status':'HEALTHY','latency_ms':round((time.perf_counter()-t0)*1000,2),'version':'reachable'})
    except Exception as exc: services.append({'service':'Redis','status':'DEGRADED','latency_ms':None,'diagnostic':str(exc)[:160]})
    for name,url in [('MinIO',os.getenv('MINIO_HEALTH_URL','http://minio:9000/minio/health/live')),('n8n',os.getenv('N8N_HEALTH_URL','http://n8n:5678/healthz'))]:
        try:
            t0=time.perf_counter();resp=httpx.get(url,timeout=0.8);ok=resp.status_code<500;services.append({'service':name,'status':'HEALTHY' if ok else 'DEGRADED','latency_ms':round((time.perf_counter()-t0)*1000,2),'http_status':resp.status_code})
        except Exception as exc: services.append({'service':name,'status':'DEGRADED','latency_ms':None,'diagnostic':str(exc)[:160]})
    overall='HEALTHY' if all(x['status']=='HEALTHY' for x in services) else 'DEGRADED'
    return {'version':settings.app_version,'environment':settings.environment,'checked_at':checked,'overall_status':overall,'services':services,'external_qualification':{'live_sap_s4':'PENDING','independent_penetration_test':'REQUIRED','enterprise_idp_validation':'PENDING','independent_tp_signoff':'PENDING'},'production_readiness':'BLOCKED_EXTERNAL_QUALIFICATION'}


@router.get('/qualification')
def qualification(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    return qualification_summary(db,user.workspace_id)

@router.patch('/qualification/{control_code}')
def update_qualification(control_code:str,status:str,evidence:str|None=None,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    allowed={'NOT_STARTED','IN_PROGRESS','PASS','FAIL','BLOCKED','EXTERNAL_REQUIRED','EXPIRED','PENDING','REQUIRED'}
    st=status.upper()
    if st not in allowed: raise HTTPException(400,'Unsupported qualification status')
    x=db.query(QualificationControl).filter(QualificationControl.workspace_id==user.workspace_id,QualificationControl.control_code==control_code).first()
    if not x: raise HTTPException(404,'Qualification control not found')
    if x.control_type=='EXTERNAL' and st=='PASS':
        raise HTTPException(409,'External controls require independently verified evidence and cannot be self-certified through this endpoint')
    x.status=st
    if evidence: x.evidence={'manual_note':evidence}
    x.reviewer=user.email
    audit(db,event_type='QUALIFICATION_CONTROL_UPDATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='qualification_control',object_id=control_code,new={'status':st,'evidence':x.evidence},details='Qualification evidence status updated')
    db.commit();return {'control_code':control_code,'status':x.status,'evidence':x.evidence}


@router.get('/notifications')
def notifications(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(Notification).filter(Notification.workspace_id==user.workspace_id,Notification.recipient==user.email).order_by(Notification.id.desc()).limit(100).all()
    return [{'id':x.id,'subject':x.subject,'body':x.body,'status':x.status,'channel':x.channel,'created_at':x.created_at.isoformat() if x.created_at else None} for x in rows]

@router.post('/notifications/{notification_id}/read')
def read_notification(notification_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    row=db.query(Notification).filter(Notification.id==notification_id,Notification.workspace_id==user.workspace_id,Notification.recipient==user.email).first()
    if not row: raise HTTPException(404,'Notification not found')
    row.status='READ';db.commit();return {'id':row.id,'status':row.status}
