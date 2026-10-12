from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
import hashlib
import os
import uuid
import json
import zipfile
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    BenchmarkComparable, BenchmarkFinancialObservation, Document, Entity, EvidenceChunk, ExceptionCase, IntegrationConnection,
    IntegrationRun, MasterDataRecord, Policy, User, WorkflowRun, MasterDataChangeRequest, Adjustment, Calculation, ApprovalRequest, ApprovalStep, JournalHeader, JournalLine, Posting, Reconciliation, AuditEvent,
)
from ..security import require_entity_access, require_permission
from ..services.audit import audit
from ..services.benchmarks import benchmark_statistics
from ..services.master_data_catalog import create_change_request as create_catalog_change

router = APIRouter(tags=['enterprise-operations'])


def _entity(db: Session, user: User, code: str | None, *, write: bool = False):
    if not code:
        return None
    row = db.query(Entity).filter(Entity.workspace_id == user.workspace_id, Entity.entity_code == code.upper()).first()
    if not row:
        raise HTTPException(404, 'Entity not found')
    require_entity_access(db, user, row, write=write)
    return row


def _exception_dict(db: Session, row: ExceptionCase):
    entity = db.get(Entity, row.entity_id) if row.entity_id else None
    return {
        'id': row.id, 'exception_code': row.exception_code,
        'entity_code': entity.entity_code if entity else None,
        'category': row.category, 'severity': row.severity,
        'amount': float(row.amount) if row.amount is not None else None,
        'currency': entity.currency if entity else None,
        'owner': row.owner, 'due_date': row.due_date, 'status': row.status,'source':row.source,'stored_currency':row.currency,
        'root_cause':row.root_cause,'remediation':row.remediation,'comments':row.comments or [],'attachments':row.attachments or [],
        'sla_hours':row.sla_hours,'escalated_to':row.escalated_to,'waived_by':row.waived_by,'waiver_reason':row.waiver_reason,
        'closed_by':row.closed_by,'closed_at':row.closed_at.isoformat() if row.closed_at else None,
        'evidence': row.evidence or [], 'resolution': row.resolution,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
    }


class ExceptionIn(BaseModel):
    entity_code: str | None = None
    category: str
    severity: str = 'WARNING'
    amount: float | None = None
    owner: str | None = None
    due_date: str | None = None
    evidence: list[dict[str, Any] | str] = Field(default_factory=list)


class ExceptionUpdate(BaseModel):
    owner: str | None = None
    due_date: str | None = None
    status: str | None = None
    severity: str | None = None
    resolution: str | None = None
    evidence: list[dict[str, Any] | str] | None = None


@router.post('/exceptions')
def create_exception(body: ExceptionIn, user: User = Depends(require_permission('write')), db: Session = Depends(get_db)):
    entity = _entity(db, user, body.entity_code, write=True)
    sev = body.severity.upper()
    if sev not in {'INFO', 'WARNING', 'ERROR', 'BLOCKING'}:
        raise HTTPException(422, 'severity must be INFO, WARNING, ERROR or BLOCKING')
    row = ExceptionCase(
        workspace_id=user.workspace_id,
        exception_code=f'EXC-{uuid.uuid4().hex[:10].upper()}',
        entity_id=entity.id if entity else None,
        category=body.category.strip().upper().replace(' ', '_'), severity=sev,
        amount=body.amount, owner=body.owner, due_date=body.due_date,
        status='OPEN', evidence=body.evidence,
    )
    db.add(row); db.flush()
    audit(db,event_type='EXCEPTION_CREATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,
          entity_code=entity.entity_code if entity else None,object_type='exception',object_id=row.exception_code,
          new=_exception_dict(db,row),details='Exception case created')
    db.commit(); db.refresh(row)
    return _exception_dict(db,row)


@router.get('/exceptions/{exception_id}')
def exception_detail(exception_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    row=db.query(ExceptionCase).filter(ExceptionCase.id==exception_id,ExceptionCase.workspace_id==user.workspace_id).first()
    if not row: raise HTTPException(404,'Exception not found')
    if row.entity_id: require_entity_access(db,user,db.get(Entity,row.entity_id))
    return _exception_dict(db,row)


@router.patch('/exceptions/{exception_id}')
def update_exception(exception_id: int, body: ExceptionUpdate, user: User = Depends(require_permission('write')), db: Session = Depends(get_db)):
    row = db.query(ExceptionCase).filter(ExceptionCase.id == exception_id, ExceptionCase.workspace_id == user.workspace_id).first()
    if not row: raise HTTPException(404, 'Exception not found')
    if row.entity_id:
        require_entity_access(db,user,db.get(Entity,row.entity_id),write=True)
    previous=_exception_dict(db,row)
    data=body.model_dump(exclude_unset=True)
    if 'status' in data:
        status=data['status'].upper()
        allowed={'OPEN','TRIAGED','IN_PROGRESS','AWAITING_INFORMATION','RESOLVED','CLOSED','WAIVED','ESCALATED'}
        if status not in allowed: raise HTTPException(422,'Invalid exception status')
        if status in {'RESOLVED','CLOSED','WAIVED'} and not (data.get('resolution') or row.resolution):
            raise HTTPException(422,'resolution is required before resolving/closing/waiving an exception')
        row.status=status
    if 'severity' in data:
        sev=data['severity'].upper()
        if sev not in {'INFO','WARNING','ERROR','BLOCKING'}: raise HTTPException(422,'Invalid severity')
        row.severity=sev
    for key in ['owner','due_date','resolution','evidence']:
        if key in data: setattr(row,key,data[key])
    audit(db,event_type='EXCEPTION_UPDATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,
          entity_code=db.get(Entity,row.entity_id).entity_code if row.entity_id else None,object_type='exception',object_id=row.exception_code,
          previous=previous,new=_exception_dict(db,row),details='Exception case updated')
    db.commit(); return _exception_dict(db,row)


@router.get('/benchmarks')
def benchmarks(include_inactive: bool = True, user: User = Depends(require_permission('read')), db: Session = Depends(get_db)):
    q=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain=='BENCHMARKS')
    if not include_inactive: q=q.filter(MasterDataRecord.active==True)
    today=date.today().isoformat(); out=[]
    for row in q.order_by(MasterDataRecord.record_code).all():
        a=row.attributes or {}; valid_until=a.get('valid_until')
        out.append({'id':row.id,'benchmark_id':row.record_code,'name':row.name,'version':row.version_no,'active':row.active,
                    'method':a.get('method'),'pli':a.get('pli'),'q1':a.get('q1'),'median':a.get('median'),'q3':a.get('q3'),
                    'tested_party':a.get('tested_party'),'geography':a.get('geography'),'industry':a.get('industry'),
                    'source':a.get('source'),'database':a.get('database'),'search_period':a.get('search_period'),
                    'financial_period':a.get('financial_period'),'valid_until':valid_until,
                    'expiry_status':'EXPIRED' if valid_until and valid_until < today else ('EXPIRING' if valid_until and valid_until <= date(date.today().year+1, date.today().month, min(date.today().day,28)).isoformat() else 'VALID'),
                    'study_document_code':a.get('study_document_code'),'approved_by':row.approved_by})
    return out


class PolicyBenchmarkIn(BaseModel):
    benchmark_id: str

class BenchmarkComparableIn(BaseModel):
    company_name:str
    country:str|None=None
    industry:str|None=None
    status:str='POTENTIAL'
    screening_reason:str|None=None
    notes:str|None=None
    evidence:list[dict[str,Any]|str]=Field(default_factory=list)

class BenchmarkObservationIn(BaseModel):
    fiscal_year:int
    sales:float|None=None
    ebit:float|None=None
    cost_base:float|None=None
    assets:float|None=None
    pli:float
    source_reference:str|None=None

class BenchmarkComparableStatusIn(BaseModel):
    status:str
    screening_reason:str|None=None

@router.get('/benchmarks/{benchmark_code}/comparables')
def benchmark_comparables(benchmark_code:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    bm=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain=='BENCHMARKS',MasterDataRecord.record_code==benchmark_code.upper()).first()
    if not bm: raise HTTPException(404,'Benchmark not found')
    rows=db.query(BenchmarkComparable).filter(BenchmarkComparable.workspace_id==user.workspace_id,BenchmarkComparable.benchmark_code==benchmark_code.upper()).order_by(BenchmarkComparable.id).all()
    out=[]
    for row in rows:
        obs=db.query(BenchmarkFinancialObservation).filter(BenchmarkFinancialObservation.comparable_id==row.id).order_by(BenchmarkFinancialObservation.fiscal_year).all()
        out.append({'id':row.id,'company_name':row.company_name,'country':row.country,'industry':row.industry,'status':row.status,'screening_reason':row.screening_reason,'notes':row.notes,'evidence':row.evidence or [],'created_by':row.created_by,
                    'observations':[{'id':x.id,'fiscal_year':x.fiscal_year,'sales':float(x.sales) if x.sales is not None else None,'ebit':float(x.ebit) if x.ebit is not None else None,'cost_base':float(x.cost_base) if x.cost_base is not None else None,'assets':float(x.assets) if x.assets is not None else None,'pli':float(x.pli),'source_reference':x.source_reference} for x in obs]})
    return out

@router.post('/benchmarks/{benchmark_code}/comparables')
def create_benchmark_comparable(benchmark_code:str,body:BenchmarkComparableIn,user:User=Depends(require_permission('integration_admin')),db:Session=Depends(get_db)):
    bm=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain=='BENCHMARKS',MasterDataRecord.record_code==benchmark_code.upper(),MasterDataRecord.active==True).first()
    if not bm: raise HTTPException(404,'Active benchmark not found')
    status=body.status.upper();allowed={'POTENTIAL','REVIEWED','ACCEPTED','REJECTED','FINAL'}
    if status not in allowed: raise HTTPException(422,'Unsupported comparable status')
    row=BenchmarkComparable(workspace_id=user.workspace_id,benchmark_code=bm.record_code,company_name=body.company_name.strip(),country=body.country.upper() if body.country else None,industry=body.industry,status=status,screening_reason=body.screening_reason,notes=body.notes,evidence=body.evidence,created_by=user.email)
    db.add(row);db.flush();audit(db,event_type='BENCHMARK_COMPARABLE_CREATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='benchmark_comparable',object_id=str(row.id),new={'benchmark':bm.record_code,'company':row.company_name,'status':row.status},details='Benchmark comparable added to governed screening set');db.commit()
    return {'id':row.id,'benchmark_code':bm.record_code,'company_name':row.company_name,'status':row.status}

@router.patch('/benchmarks/comparables/{comparable_id}')
def update_benchmark_comparable(comparable_id:int,body:BenchmarkComparableStatusIn,user:User=Depends(require_permission('integration_admin')),db:Session=Depends(get_db)):
    row=db.query(BenchmarkComparable).filter(BenchmarkComparable.id==comparable_id,BenchmarkComparable.workspace_id==user.workspace_id).first()
    if not row: raise HTTPException(404,'Comparable not found')
    status=body.status.upper();allowed={'POTENTIAL','REVIEWED','ACCEPTED','REJECTED','FINAL'}
    if status not in allowed: raise HTTPException(422,'Unsupported comparable status')
    if status=='REJECTED' and not (body.screening_reason or row.screening_reason): raise HTTPException(422,'screening_reason is required when rejecting a comparable')
    previous=row.status;row.status=status
    if body.screening_reason is not None: row.screening_reason=body.screening_reason
    audit(db,event_type='BENCHMARK_SCREENING_DECISION',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='benchmark_comparable',object_id=str(row.id),previous={'status':previous},new={'status':row.status,'reason':row.screening_reason},details='Comparable screening status changed');db.commit()
    return {'id':row.id,'status':row.status,'screening_reason':row.screening_reason}

@router.post('/benchmarks/comparables/{comparable_id}/observations')
def add_benchmark_observation(comparable_id:int,body:BenchmarkObservationIn,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    comp=db.query(BenchmarkComparable).filter(BenchmarkComparable.id==comparable_id,BenchmarkComparable.workspace_id==user.workspace_id).first()
    if not comp: raise HTTPException(404,'Comparable not found')
    if body.fiscal_year<1900 or body.fiscal_year>2100: raise HTTPException(422,'Invalid fiscal_year')
    existing=db.query(BenchmarkFinancialObservation).filter(BenchmarkFinancialObservation.comparable_id==comp.id,BenchmarkFinancialObservation.fiscal_year==body.fiscal_year).first()
    if existing: raise HTTPException(409,'Observation already exists for this comparable/year')
    row=BenchmarkFinancialObservation(comparable_id=comp.id,fiscal_year=body.fiscal_year,sales=body.sales,ebit=body.ebit,cost_base=body.cost_base,assets=body.assets,pli=body.pli,source_reference=body.source_reference)
    db.add(row);db.flush();audit(db,event_type='BENCHMARK_FINANCIAL_ADDED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='benchmark_comparable',object_id=str(comp.id),new={'year':body.fiscal_year,'pli':body.pli},details='Comparable financial observation added');db.commit()
    return {'id':row.id,'comparable_id':comp.id,'fiscal_year':row.fiscal_year,'pli':float(row.pli)}

@router.get('/benchmarks/{benchmark_code}/statistics')
def benchmark_stats(benchmark_code:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    try:return benchmark_statistics(db,user.workspace_id,benchmark_code)
    except ValueError as exc: raise HTTPException(409,str(exc))

@router.post('/benchmarks/{benchmark_code}/statistics/stage')
def stage_benchmark_statistics(benchmark_code:str,user:User=Depends(require_permission('master_data_draft')),db:Session=Depends(get_db)):
    bm=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain=='BENCHMARKS',MasterDataRecord.record_code==benchmark_code.upper(),MasterDataRecord.active==True).first()
    if not bm: raise HTTPException(404,'Active benchmark not found')
    try:stats=benchmark_statistics(db,user.workspace_id,benchmark_code)
    except ValueError as exc: raise HTTPException(409,str(exc))
    attrs=dict(bm.attributes or {});attrs.update({'minimum':str(stats['minimum']),'q1':str(stats['q1']),'median':str(stats['median']),'q3':str(stats['q3']),'maximum':str(stats['maximum']),'comparable_count':stats['comparable_count'],'observation_count':stats['observation_count'],'statistics_methodology':stats['methodology']})
    payload={'record_code':bm.record_code,'name':bm.name,'effective_from':bm.effective_from,'effective_to':bm.effective_to,'attributes':attrs}
    try:req=create_catalog_change(db,workspace_id=user.workspace_id,user=user,domain='BENCHMARKS',change_type='UPDATE',payload=payload,reason='Recalculate benchmark statistics from accepted comparable set')
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,event_type='BENCHMARK_STATISTICS_STAGED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='benchmark',object_id=bm.record_code,new={'request_code':req.request_code,'statistics':stats},details='Deterministic benchmark statistics staged for maker-checker approval');db.commit()
    return {'request_id':req.id,'request_code':req.request_code,'statistics':stats}


@router.post('/policies/{policy_id}/benchmark')
def assign_policy_benchmark(policy_id:int, body:PolicyBenchmarkIn, user:User=Depends(require_permission('admin_policy')), db:Session=Depends(get_db)):
    policy=db.query(Policy).filter(Policy.id==policy_id,Policy.workspace_id==user.workspace_id).first()
    if not policy: raise HTTPException(404,'Policy not found')
    bm=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain=='BENCHMARKS',MasterDataRecord.record_code==body.benchmark_id.upper(),MasterDataRecord.active==True).first()
    if not bm: raise HTTPException(404,'Approved active benchmark not found')
    valid_until=(bm.attributes or {}).get('valid_until')
    if valid_until and valid_until < date.today().isoformat(): raise HTTPException(409,'Benchmark is expired')
    previous=policy.benchmark_id;policy.benchmark_id=bm.record_code
    audit(db,event_type='POLICY_BENCHMARK_ASSIGNED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,
          entity_code=db.get(Entity,policy.entity_id).entity_code,object_type='policy',object_id=policy.policy_code,
          previous={'benchmark_id':previous},new={'benchmark_id':bm.record_code,'benchmark_version':bm.version_no},details='Approved benchmark linked to TP policy')
    db.commit();return {'policy_id':policy.id,'policy_code':policy.policy_code,'benchmark_id':bm.record_code,'benchmark_version':bm.version_no}


def _storage_root() -> Path:
    path=Path(os.getenv('DOCUMENT_STORAGE_PATH','/data/documents'))
    try:
        path.mkdir(parents=True,exist_ok=True)
    except PermissionError:
        path=Path('/tmp/otp-documents');path.mkdir(parents=True,exist_ok=True)
    return path


def _document_dict(db: Session,row:Document):
    e=db.get(Entity,row.entity_id) if row.entity_id else None
    return {'id':row.id,'document_code':row.document_code,'version':row.version,'entity_code':e.entity_code if e else None,
            'country':row.country,'period':row.period,'document_type':row.document_type,'effective_date':row.effective_date,'expires_at':row.expires_at,
            'status':row.status,'sha256':row.sha256,'uploader':row.uploader,'access_classification':row.access_classification,
            'tags':row.tags or [],'linked_object_type':row.linked_object_type,'linked_object_id':row.linked_object_id,'metadata':row.metadata_json or {},
            'storage_key':row.storage_key,'created_at':row.created_at.isoformat() if row.created_at else None}


@router.get('/documents')
def documents(document_type:str|None=None,entity_code:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(Document).filter(Document.workspace_id==user.workspace_id)
    if document_type: q=q.filter(Document.document_type==document_type.upper())
    if entity_code:
        e=_entity(db,user,entity_code);q=q.filter(Document.entity_id==e.id)
    return [_document_dict(db,x) for x in q.order_by(Document.document_code,Document.version.desc()).all()]


@router.post('/documents/upload')
async def upload_document(
    file:UploadFile=File(...), document_code:str=Form(...), document_type:str=Form(...),
    entity_code:str|None=Form(None), country:str|None=Form(None), period:str|None=Form(None),
    effective_date:str|None=Form(None), expires_at:str|None=Form(None), access_classification:str=Form('CONFIDENTIAL'),
    tags:str|None=Form(None), linked_object_type:str|None=Form(None), linked_object_id:str|None=Form(None),
    user:User=Depends(require_permission('write')), db:Session=Depends(get_db)
):
    entity=_entity(db,user,entity_code,write=True) if entity_code else None
    content=await file.read()
    if not content: raise HTTPException(422,'File is empty')
    if len(content)>25*1024*1024: raise HTTPException(413,'Document exceeds 25 MB limit')
    digest=hashlib.sha256(content).hexdigest();code=document_code.strip().upper()
    previous=db.query(Document).filter(Document.workspace_id==user.workspace_id,Document.document_code==code).order_by(Document.version.desc()).first()
    version=(previous.version+1) if previous else 1
    safe_name=''.join(c if c.isalnum() or c in '._-' else '_' for c in (file.filename or 'document.bin'))
    rel=f'{user.workspace_id}/{code}/v{version}_{safe_name}';path=_storage_root()/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    if previous and previous.status=='ACTIVE': previous.status='SUPERSEDED'
    row=Document(workspace_id=user.workspace_id,document_code=code,version=version,entity_id=entity.id if entity else None,
                 country=(country.upper() if country else None),period=period,document_type=document_type.strip().upper(),effective_date=effective_date,expires_at=expires_at,
                 status='ACTIVE',sha256=digest,uploader=user.email,access_classification=access_classification.upper(),storage_key=str(path),
                 tags=[x.strip() for x in (tags or '').split(',') if x.strip()],linked_object_type=linked_object_type.upper() if linked_object_type else None,
                 linked_object_id=linked_object_id,metadata_json={'filename':safe_name,'size_bytes':len(content)})
    db.add(row);db.flush()
    # Text-like files are indexed deterministically for evidence retrieval. PDFs remain metadata-only until an extraction provider is configured.
    if safe_name.lower().endswith(('.txt','.md','.csv','.json')):
        text=content.decode('utf-8',errors='replace')
        for idx,start in enumerate(range(0,len(text),1800),1):
            db.add(EvidenceChunk(document_id=row.id,chunk_no=idx,content=text[start:start+1800],metadata_json={'filename':safe_name,'sha256':digest}))
    audit(db,event_type='DOCUMENT_UPLOADED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,
          entity_code=entity.entity_code if entity else None,object_type='document',object_id=f'{code}:v{version}',new={'sha256':digest,'document_type':row.document_type},details='Versioned evidence document uploaded')
    db.commit();return _document_dict(db,row)


@router.get('/documents/{document_id}/download')
def download_document(document_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    row=db.query(Document).filter(Document.id==document_id,Document.workspace_id==user.workspace_id).first()
    if not row: raise HTTPException(404,'Document not found')
    if row.entity_id: require_entity_access(db,user,db.get(Entity,row.entity_id))
    path=Path(row.storage_key)
    if not path.exists(): raise HTTPException(404,'Document content is not available in this runtime')
    return FileResponse(path,filename=path.name.split('_',1)[-1])


@router.get('/documents/search/evidence')
def search_evidence(q:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    if len(q.strip())<2: raise HTTPException(422,'Search query is too short')
    rows=(db.query(EvidenceChunk,Document).join(Document,Document.id==EvidenceChunk.document_id)
          .filter(Document.workspace_id==user.workspace_id,EvidenceChunk.content.ilike(f'%{q.strip()}%')).limit(50).all())
    out=[]
    for chunk,doc in rows:
        if doc.entity_id:
            try: require_entity_access(db,user,db.get(Entity,doc.entity_id))
            except HTTPException: continue
        out.append({'document_id':doc.id,'document_code':doc.document_code,'version':doc.version,'chunk_no':chunk.chunk_no,'content':chunk.content[:700],'sha256':doc.sha256})
    return out


class IntegrationIn(BaseModel):
    connection_code:str
    connector_type:str
    config:dict[str,Any]=Field(default_factory=dict)
    secret_reference:str|None=None


@router.post('/integrations')
def create_integration(body:IntegrationIn,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    code=body.connection_code.strip().upper()
    if db.query(IntegrationConnection).filter(IntegrationConnection.workspace_id==user.workspace_id,IntegrationConnection.connection_code==code).first():
        raise HTTPException(409,'Connection code already exists')
    row=IntegrationConnection(workspace_id=user.workspace_id,connection_code=code,connector_type=body.connector_type.upper(),config=body.config,secret_reference=body.secret_reference,status='CONFIGURED')
    db.add(row);db.flush();audit(db,event_type='INTEGRATION_CONFIGURED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='integration',object_id=code,new={'connector_type':row.connector_type,'config':body.config,'secret_reference':body.secret_reference},details='Integration connection configured; secrets remain references only');db.commit()
    return {'id':row.id,'connection_code':row.connection_code,'connector_type':row.connector_type,'status':row.status,'config':row.config,'secret_reference':row.secret_reference}


@router.post('/integrations/{connection_id}/test')
def test_integration(connection_id:int,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    row=db.query(IntegrationConnection).filter(IntegrationConnection.id==connection_id,IntegrationConnection.workspace_id==user.workspace_id).first()
    if not row: raise HTTPException(404,'Integration not found')
    run=IntegrationRun(connection_id=row.id,run_code=f'INT-{uuid.uuid4().hex[:10].upper()}',correlation_id=str(uuid.uuid4()),status='SIMULATED_OK',records_processed=0)
    db.add(run);row.status='SIMULATED'
    audit(db,event_type='INTEGRATION_TEST',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='integration',object_id=row.connection_code,new={'status':'SIMULATED_OK','live':False},details='Connector contract/simulator test executed; this is not live external qualification');db.commit()
    return {'run_code':run.run_code,'status':run.status,'connector_type':row.connector_type,'live':False,'qualification':'EXTERNAL QUALIFICATION REQUIRED'}


@router.get('/integrations/{connection_id}/runs')
def integration_runs(connection_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    row=db.query(IntegrationConnection).filter(IntegrationConnection.id==connection_id,IntegrationConnection.workspace_id==user.workspace_id).first()
    if not row: raise HTTPException(404,'Integration not found')
    runs=db.query(IntegrationRun).filter(IntegrationRun.connection_id==row.id).order_by(IntegrationRun.id.desc()).limit(100).all()
    return [{'id':x.id,'run_code':x.run_code,'correlation_id':x.correlation_id,'status':x.status,'records_processed':x.records_processed,'error_message':x.error_message,'created_at':x.created_at.isoformat() if x.created_at else None} for x in runs]


@router.get('/workflow-runs')
def workflow_runs(limit:int=100,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(WorkflowRun).filter(WorkflowRun.workspace_id==user.workspace_id).order_by(WorkflowRun.id.desc()).limit(min(limit,500)).all()
    return [{'id':x.id,'workflow_name':x.workflow_name,'correlation_id':x.correlation_id,'status':x.status,'payload':x.payload,'created_at':x.created_at.isoformat() if x.created_at else None} for x in rows]


@router.get('/evidence-packs/adjustments/{adjustment_id}')
def adjustment_evidence_pack(adjustment_id:int,user:User=Depends(require_permission('export')),db:Session=Depends(get_db)):
    adj=db.query(Adjustment).filter(Adjustment.id==adjustment_id,Adjustment.workspace_id==user.workspace_id).first()
    if not adj: raise HTTPException(404,'Adjustment not found')
    entity=db.get(Entity,adj.entity_id);require_entity_access(db,user,entity)
    calc=db.get(Calculation,adj.calculation_id);policy=db.get(Policy,calc.policy_id) if calc else None
    req=db.query(ApprovalRequest).filter(ApprovalRequest.adjustment_id==adj.id).first()
    steps=db.query(ApprovalStep).filter(ApprovalStep.approval_request_id==req.id).order_by(ApprovalStep.step_order).all() if req else []
    journal=db.query(JournalHeader).filter(JournalHeader.adjustment_id==adj.id).first()
    jlines=db.query(JournalLine).filter(JournalLine.journal_id==journal.id).order_by(JournalLine.line_no).all() if journal else []
    posting=db.query(Posting).filter(Posting.journal_header_id==journal.id).order_by(Posting.id.desc()).first() if journal else None
    rec=db.query(Reconciliation).filter(Reconciliation.adjustment_id==adj.id).order_by(Reconciliation.id.desc()).first()
    audit_rows=(db.query(AuditEvent).filter(AuditEvent.workspace_id==user.workspace_id)
                .filter((AuditEvent.entity_code==entity.entity_code) | (AuditEvent.object_id==adj.adjustment_code)).order_by(AuditEvent.id).all())
    docs=db.query(Document).filter(Document.workspace_id==user.workspace_id,Document.entity_id==entity.id).order_by(Document.document_code,Document.version).all()
    benchmark=None
    if policy and policy.benchmark_id:
        benchmark=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain=='BENCHMARKS',MasterDataRecord.record_code==policy.benchmark_id).first()
    data={
      'entity':{'entity_code':entity.entity_code,'legal_name':entity.legal_name,'country':entity.country,'currency':entity.currency},
      'adjustment':{'id':adj.id,'adjustment_code':adj.adjustment_code,'amount':float(adj.amount),'currency':adj.currency,'status':adj.status,'version':adj.version,'materiality':float(adj.materiality)},
      'calculation':({'calculation_code':calc.calculation_code,'period':calc.period,'revenue':float(calc.revenue),'ebit':float(calc.ebit),'actual_pli':float(calc.actual_pli),'target_pli':float(calc.target_pli),'suggested_adjustment':float(calc.suggested_adjustment),'engine_version':calc.engine_version,'source_hash':calc.source_hash,'manifest':calc.manifest} if calc else None),
      'policy':({'policy_code':policy.policy_code,'version':policy.version,'method':policy.method,'pli':policy.pli,'target':float(policy.target),'benchmark_id':policy.benchmark_id,'status':policy.status} if policy else None),
      'benchmark':({'benchmark_id':benchmark.record_code,'version':benchmark.version_no,'attributes':benchmark.attributes,'approved_by':benchmark.approved_by} if benchmark else None),
      'approval':({'request_id':req.id,'status':req.status,'workflow_code':req.workflow_code,'workflow_version':req.workflow_version,'steps':[{'step_order':s.step_order,'required_role':s.required_role,'status':s.status,'actor':s.actor,'comments':s.comments,'decided_at':s.decided_at.isoformat() if s.decided_at else None} for s in steps]} if req else None),
      'journal':({'journal_code':journal.journal_code,'status':journal.status,'company_code':journal.company_code,'currency':journal.currency,'template_code':journal.template_code,'template_version':journal.template_version,'lines':[{'line_no':x.line_no,'gl_account':x.gl_account,'debit_credit':x.debit_credit,'amount':float(x.amount),'currency':x.currency,'profit_center':x.profit_center,'trading_partner':x.trading_partner,'assignment':x.assignment,'text':x.text,'tax_code':x.tax_code} for x in jlines]} if journal else None),
      'posting':({'erp_system':posting.erp_system,'erp_document_number':posting.erp_document_number,'posted_amount':float(posting.posted_amount),'status':posting.status,'posted_at':posting.posted_at.isoformat() if posting.posted_at else None} if posting else None),
      'reconciliation':({'id':rec.id,'expected_amount':float(rec.expected_amount),'journal_amount':float(rec.journal_amount or 0),'posted_amount':float(rec.posted_amount),'difference':float(rec.difference),'tolerance':float(rec.tolerance),'status':rec.status,'exception_code':rec.exception_code,'certified_by':rec.certified_by} if rec else None),
      'documents':[{'document_code':d.document_code,'version':d.version,'document_type':d.document_type,'sha256':d.sha256,'status':d.status} for d in docs],
      'audit_events':[{'id':x.id,'event_type':x.event_type,'actor':x.actor,'actor_role':x.actor_role,'entity_code':x.entity_code,'object_type':x.object_type,'object_id':x.object_id,'previous_value':x.previous_value,'new_value':x.new_value,'reason':x.reason,'correlation_id':x.correlation_id,'details':x.details,'created_at':x.created_at.isoformat()} for x in audit_rows],
    }
    tmp=Path(tempfile.mkdtemp(prefix='otp-evidence-'));zip_path=tmp/f'Evidence_{adj.adjustment_code}.zip'
    manifest={'release_object':'ADJUSTMENT_EVIDENCE_PACK','adjustment_code':adj.adjustment_code,'entity_code':entity.entity_code,'generated_by':user.email,'files':['manifest.json','evidence.json']}
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(manifest,indent=2,default=str))
        z.writestr('evidence.json',json.dumps(data,indent=2,default=str))
        for d in docs:
            path=Path(d.storage_key)
            if path.exists():
                arc=f'documents/{d.document_code}/v{d.version}_{path.name.split("_",1)[-1]}'
                z.write(path,arc);manifest['files'].append(arc)
        z.writestr('manifest_final.json',json.dumps(manifest,indent=2,default=str))
    audit(db,event_type='EVIDENCE_PACK_GENERATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=entity.entity_code,object_type='adjustment',object_id=adj.adjustment_code,new={'files':len(manifest['files'])},details='Auditor evidence pack generated from governed transaction chain');db.commit()
    return FileResponse(zip_path,media_type='application/zip',filename=zip_path.name)
