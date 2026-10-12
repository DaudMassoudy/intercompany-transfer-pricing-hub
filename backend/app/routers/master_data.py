from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Entity, EntityChangeRequest, EntityVersion, User
from ..security import require_permission, require_entity_access
from ..services.audit import audit
from ..services.notifications import notify_roles, notify_user
from ..services.entity_master import (
    approve_change_request, create_change_request, entity_snapshot, preview_entity_master,
    reject_change_request, submit_change_request,
)

router=APIRouter(prefix='/master-data',tags=['master-data'])

class EntityPayload(BaseModel):
    entity_code:str
    legal_name:str|None=None
    country:str|None=None
    currency:str|None=None
    group_currency:str|None='EUR'
    characterization:str|None=None
    company_code:str|None=None
    erp_system:str|None=None
    tax_jurisdiction:str|None=None
    tax_rate:float|str|None=None
    customs_territory:str|None=None
    effective_from:str|None=None
    effective_to:str|None=None
    active:bool|None=True

class ChangeIn(BaseModel):
    change_type:str=Field(pattern='^(CREATE|UPDATE|DEACTIVATE|REACTIVATE)$')
    payload:EntityPayload
    reason:str|None=None

class RejectIn(BaseModel):
    reason:str


def _req(row:EntityChangeRequest):
    return {'id':row.id,'request_code':row.request_code,'entity_code':row.entity_code,'change_type':row.change_type,'status':row.status,
        'payload':row.payload,'reason':row.reason,'batch_code':row.batch_code,'created_by':row.created_by,'submitted_by':row.submitted_by,
        'reviewed_by':row.reviewed_by,'submitted_at':row.submitted_at.isoformat() if row.submitted_at else None,
        'reviewed_at':row.reviewed_at.isoformat() if row.reviewed_at else None,'created_at':row.created_at.isoformat() if row.created_at else None}

@router.get('/entities')
def master_entities(include_inactive:bool=True,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(Entity).filter(Entity.workspace_id==user.workspace_id)
    if not include_inactive:q=q.filter(Entity.active==True)
    out=[]
    for e in q.order_by(Entity.entity_code):
        try: require_entity_access(db,user,e)
        except HTTPException: continue
        v=db.query(EntityVersion).filter(EntityVersion.entity_id==e.id).order_by(EntityVersion.version_no.desc()).first()
        pending=db.query(EntityChangeRequest).filter(EntityChangeRequest.workspace_id==user.workspace_id,EntityChangeRequest.entity_code==e.entity_code,EntityChangeRequest.status.in_(['DRAFT','SUBMITTED'])).count()
        x=entity_snapshot(e);x.update({'id':e.id,'version':v.version_no if v else 0,'pending_changes':pending});out.append(x)
    return out

@router.get('/entities/{code}/history')
def entity_history(code:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==code.upper()).first()
    if not e: raise HTTPException(404,'Entity not found')
    require_entity_access(db,user,e)
    rows=db.query(EntityVersion).filter(EntityVersion.entity_id==e.id).order_by(EntityVersion.version_no.desc()).all()
    return [{'version':x.version_no,'snapshot':x.snapshot,'effective_from':x.effective_from,'effective_to':x.effective_to,'approved_by':x.approved_by,'approval_request_code':x.approval_request_code,'created_at':x.created_at.isoformat()} for x in rows]

@router.get('/entity-changes')
def changes(status:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(EntityChangeRequest).filter(EntityChangeRequest.workspace_id==user.workspace_id)
    if status:q=q.filter(EntityChangeRequest.status==status.upper())
    return [_req(x) for x in q.order_by(EntityChangeRequest.id.desc()).limit(250)]

@router.post('/entity-changes')
def create_change(body:ChangeIn,user:User=Depends(require_permission('master_data_draft')),db:Session=Depends(get_db)):
    code=body.payload.entity_code.upper()
    if body.change_type!='CREATE':
        e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==code).first()
        if not e: raise HTTPException(404,'Entity not found')
        require_entity_access(db,user,e,write=True)
    try:req=create_change_request(db,workspace_id=user.workspace_id,user=user,change_type=body.change_type,payload=body.payload.model_dump(exclude_none=True),reason=body.reason)
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,event_type='ENTITY_CHANGE_DRAFTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=req.entity_code,object_type='entity_change_request',object_id=req.request_code,new=req.payload,reason=req.reason,details=f'{req.change_type} entity master change drafted')
    db.commit();db.refresh(req);return _req(req)

@router.post('/entity-changes/{request_id}/submit')
def submit_change(request_id:int,user:User=Depends(require_permission('master_data_draft')),db:Session=Depends(get_db)):
    req=db.query(EntityChangeRequest).filter(EntityChangeRequest.id==request_id,EntityChangeRequest.workspace_id==user.workspace_id).first()
    if not req: raise HTTPException(404,'Change request not found')
    try:submit_change_request(db,req,user)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,event_type='ENTITY_CHANGE_SUBMITTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=req.entity_code,object_type='entity_change_request',object_id=req.request_code,new={'status':'SUBMITTED'},reason=req.reason,details='Entity master change submitted for maker-checker review')
    db.commit();return _req(req)

@router.post('/entity-changes/{request_id}/approve')
def approve_change(request_id:int,user:User=Depends(require_permission('master_data_approve')),db:Session=Depends(get_db)):
    req=db.query(EntityChangeRequest).filter(EntityChangeRequest.id==request_id,EntityChangeRequest.workspace_id==user.workspace_id).first()
    if not req: raise HTTPException(404,'Change request not found')
    try:req,entity,previous,current,version=approve_change_request(db,req,user)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,event_type='ENTITY_MASTER_APPROVED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=entity.entity_code,object_type='entity',object_id=entity.entity_code,previous=previous,new=current,reason=req.reason,details=f'{req.change_type} approved; entity master version {version}')
    db.commit();return {'request':_req(req),'entity':current,'version':version}

@router.post('/entity-changes/{request_id}/reject')
def reject_change(request_id:int,body:RejectIn,user:User=Depends(require_permission('master_data_approve')),db:Session=Depends(get_db)):
    req=db.query(EntityChangeRequest).filter(EntityChangeRequest.id==request_id,EntityChangeRequest.workspace_id==user.workspace_id).first()
    if not req: raise HTTPException(404,'Change request not found')
    try:reject_change_request(db,req,user,body.reason)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,event_type='ENTITY_CHANGE_REJECTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=req.entity_code,object_type='entity_change_request',object_id=req.request_code,new={'status':'REJECTED'},reason=body.reason,details='Entity master change rejected')
    db.commit();return _req(req)

@router.post('/entities/import/preview')
async def import_preview(file:UploadFile=File(...),user:User=Depends(require_permission('master_data_import')),db:Session=Depends(get_db)):
    content=await file.read()
    try:return preview_entity_master(db,workspace_id=user.workspace_id,filename=file.filename or 'entity_master.xlsx',content=content)
    except ValueError as exc: raise HTTPException(400,str(exc))

@router.post('/entities/import/requests')
async def import_requests(file:UploadFile=File(...),submit_for_review:bool=Form(False),reason:str=Form('Entity Master bulk import'),user:User=Depends(require_permission('master_data_import')),db:Session=Depends(get_db)):
    content=await file.read()
    try:preview=preview_entity_master(db,workspace_id=user.workspace_id,filename=file.filename or 'entity_master.xlsx',content=content)
    except ValueError as exc: raise HTTPException(400,str(exc))
    if preview['counts']['INVALID']:
        raise HTTPException(409,{'message':'Bulk import contains invalid rows. Resolve all validation errors before creating requests.','preview':preview})
    import uuid
    batch=f"EMB-{uuid.uuid4().hex[:8].upper()}";created=[]
    for item in preview['items']:
        if item['action'] not in {'CREATE','UPDATE'}: continue
        req=create_change_request(db,workspace_id=user.workspace_id,user=user,change_type=item['action'],payload=item['payload'],reason=reason,batch_code=batch)
        if submit_for_review: submit_change_request(db,req,user)
        created.append(req)
    audit(db,event_type='ENTITY_MASTER_BULK_STAGED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='entity_change_batch',object_id=batch,new={'requests':len(created),'submitted':submit_for_review,'filename':file.filename},reason=reason,details='Entity Master workbook staged as governed change requests')
    db.commit();return {'batch_code':batch,'created_requests':len(created),'submitted_for_review':submit_for_review,'requests':[_req(x) for x in created],'preview':preview}

# ---------------------------------------------------------------------------
# Governed enterprise master-data catalog (all non-legal-entity domains)
# ---------------------------------------------------------------------------
from ..models import MasterDataRecord, MasterDataVersion, MasterDataChangeRequest
from ..services.master_data_catalog import (
    approve_change_request as approve_catalog_change,
    create_change_request as create_catalog_change,
    domain_catalog,
    preview_import as preview_catalog_import,
    reject_change_request as reject_catalog_change,
    serialize_record as serialize_catalog_record,
    serialize_request as serialize_catalog_request,
    submit_change_request as submit_catalog_change,
    normalize_domain,
    dependency_impact,
)

class CatalogChangeIn(BaseModel):
    change_type:str=Field(pattern='^(CREATE|UPDATE|DEACTIVATE|REACTIVATE)$')
    payload:dict[str,Any]
    reason:str|None=None

@router.get('/catalog/domains')
def catalog_domains(user:User=Depends(require_permission('read'))):
    return domain_catalog()

@router.get('/catalog/{domain}')
def catalog_records(domain:str,include_inactive:bool=True,search:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    try: domain=normalize_domain(domain)
    except ValueError as exc: raise HTTPException(404,str(exc))
    q=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain==domain)
    if not include_inactive:q=q.filter(MasterDataRecord.active==True)
    rows=q.order_by(MasterDataRecord.record_code).all()
    if search:
        needle=search.lower().strip();rows=[x for x in rows if needle in x.record_code.lower() or needle in x.name.lower()]
    return [serialize_catalog_record(x) for x in rows]

@router.get('/catalog/{domain}/{record_code}/impact')
def catalog_impact(domain:str,record_code:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    try:
        domain=normalize_domain(domain)
        record=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain==domain,MasterDataRecord.record_code==record_code.upper()).first()
        if not record: raise HTTPException(404,'Master-data record not found')
        return dependency_impact(db,user.workspace_id,domain,record_code)
    except ValueError as exc: raise HTTPException(404,str(exc))

@router.get('/catalog/{domain}/{record_code}/history')
def catalog_history(domain:str,record_code:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    try: domain=normalize_domain(domain)
    except ValueError as exc: raise HTTPException(404,str(exc))
    rows=db.query(MasterDataVersion).filter(MasterDataVersion.workspace_id==user.workspace_id,MasterDataVersion.domain==domain,MasterDataVersion.record_code==record_code.upper()).order_by(MasterDataVersion.version_no.desc()).all()
    if not rows: raise HTTPException(404,'Master-data record/history not found')
    return [{'version_no':x.version_no,'snapshot':x.snapshot,'approved_by':x.approved_by,'approval_request_code':x.approval_request_code,'created_at':x.created_at.isoformat() if x.created_at else None} for x in rows]

@router.get('/catalog-changes')
def catalog_changes(domain:str|None=None,status:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(MasterDataChangeRequest).filter(MasterDataChangeRequest.workspace_id==user.workspace_id)
    if domain:
        try: domain=normalize_domain(domain)
        except ValueError as exc: raise HTTPException(404,str(exc))
        q=q.filter(MasterDataChangeRequest.domain==domain)
    if status:q=q.filter(MasterDataChangeRequest.status==status.upper())
    return [serialize_catalog_request(x) for x in q.order_by(MasterDataChangeRequest.id.desc()).limit(500)]

@router.post('/catalog/{domain}/changes')
def create_catalog_request(domain:str,body:CatalogChangeIn,user:User=Depends(require_permission('master_data_draft')),db:Session=Depends(get_db)):
    try:req=create_catalog_change(db,workspace_id=user.workspace_id,user=user,domain=domain,change_type=body.change_type,payload=body.payload,reason=body.reason)
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,event_type='MASTER_DATA_CHANGE_DRAFTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='master_data_change_request',object_id=req.request_code,new={'domain':req.domain,'payload':req.payload},reason=req.reason,details=f'{req.domain} {req.change_type} drafted')
    db.commit();db.refresh(req);return serialize_catalog_request(req)

@router.get('/catalog-changes/{request_id}')
def catalog_change_detail(request_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    req=db.query(MasterDataChangeRequest).filter(MasterDataChangeRequest.id==request_id,MasterDataChangeRequest.workspace_id==user.workspace_id).first()
    if not req: raise HTTPException(404,'Change request not found')
    current=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain==req.domain,MasterDataRecord.record_code==req.record_code).first()
    current_snapshot=serialize_catalog_record(current) if current else None
    proposed=req.payload or {}
    before=current_snapshot or {}
    # flatten governed attributes for a reviewer-friendly field diff
    left={k:v for k,v in before.items() if k!='attributes'}
    left.update((before.get('attributes') or {}) if isinstance(before,dict) else {})
    right={k:v for k,v in proposed.items() if k!='attributes'}
    right.update(proposed.get('attributes') or {})
    keys=sorted(set(left)|set(right))
    diff=[{'field':k,'current':left.get(k),'proposed':right.get(k),'changed':left.get(k)!=right.get(k)} for k in keys if left.get(k)!=right.get(k)]
    impact=dependency_impact(db,user.workspace_id,req.domain,req.record_code) if current else {'dependencies':[],'count':0}
    return {**serialize_catalog_request(req),'current':current_snapshot,'proposed':proposed,'diff':diff,'impact':impact}

class ReturnIn(BaseModel):
    reason:str

@router.post('/catalog-changes/{request_id}/return')
def return_catalog_request(request_id:int,body:ReturnIn,user:User=Depends(require_permission('master_data_approve')),db:Session=Depends(get_db)):
    req=db.query(MasterDataChangeRequest).filter(MasterDataChangeRequest.id==request_id,MasterDataChangeRequest.workspace_id==user.workspace_id).first()
    if not req: raise HTTPException(404,'Change request not found')
    if req.status!='SUBMITTED': raise HTTPException(409,'Only submitted requests can be returned')
    if req.created_by==user.email: raise HTTPException(409,'Maker-checker: maker cannot review own request')
    req.status='DRAFT';req.reason=(req.reason or '') + (' | Returned for rework: '+body.reason)
    notify_user(db,user.workspace_id,req.created_by,'Master-data request returned',f'{req.request_code} ({req.domain}/{req.record_code}) was returned for rework: {body.reason}')
    audit(db,event_type='MASTER_DATA_CHANGE_RETURNED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='master_data_change_request',object_id=req.request_code,new={'status':'DRAFT','domain':req.domain},reason=body.reason,details='Master-data change returned for rework')
    db.commit();return serialize_catalog_request(req)

@router.post('/catalog-changes/{request_id}/submit')
def submit_catalog_request(request_id:int,user:User=Depends(require_permission('master_data_draft')),db:Session=Depends(get_db)):
    req=db.query(MasterDataChangeRequest).filter(MasterDataChangeRequest.id==request_id,MasterDataChangeRequest.workspace_id==user.workspace_id).first()
    if not req: raise HTTPException(404,'Change request not found')
    try:submit_catalog_change(req,user)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    audit(db,event_type='MASTER_DATA_CHANGE_SUBMITTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='master_data_change_request',object_id=req.request_code,new={'status':'SUBMITTED','domain':req.domain},reason=req.reason,details='Master-data change submitted for maker-checker review')
    notify_roles(db,user.workspace_id,['TP_MANAGER','HEAD_OF_TP','GROUP_TAX_DIRECTOR','PLATFORM_ADMIN'],'Master-data approval required',f'{req.request_code}: {req.domain} {req.change_type} for {req.record_code} submitted by {user.email}')
    db.commit();return serialize_catalog_request(req)

@router.post('/catalog-changes/{request_id}/approve')
def approve_catalog_request(request_id:int,user:User=Depends(require_permission('master_data_approve')),db:Session=Depends(get_db)):
    req=db.query(MasterDataChangeRequest).filter(MasterDataChangeRequest.id==request_id,MasterDataChangeRequest.workspace_id==user.workspace_id).first()
    if not req: raise HTTPException(404,'Change request not found')
    try:record,previous,current=approve_catalog_change(db,req,user)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    notify_user(db,user.workspace_id,req.created_by,'Master-data request approved',f'{req.request_code} ({req.domain}/{req.record_code}) was approved by {user.email}')
    audit(db,event_type='MASTER_DATA_APPROVED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type=req.domain.lower(),object_id=req.record_code,previous=previous,new=current,reason=req.reason,details=f'{req.domain} {req.change_type} approved; version {record.version_no}')
    db.commit();return {'request':serialize_catalog_request(req),'record':serialize_catalog_record(record)}

@router.post('/catalog-changes/{request_id}/reject')
def reject_catalog_request(request_id:int,body:RejectIn,user:User=Depends(require_permission('master_data_approve')),db:Session=Depends(get_db)):
    req=db.query(MasterDataChangeRequest).filter(MasterDataChangeRequest.id==request_id,MasterDataChangeRequest.workspace_id==user.workspace_id).first()
    if not req: raise HTTPException(404,'Change request not found')
    try:reject_catalog_change(req,user,body.reason)
    except PermissionError as exc: raise HTTPException(403,str(exc))
    except ValueError as exc: raise HTTPException(409,str(exc))
    notify_user(db,user.workspace_id,req.created_by,'Master-data request rejected',f'{req.request_code} ({req.domain}/{req.record_code}) was rejected by {user.email}: {body.reason}')
    audit(db,event_type='MASTER_DATA_CHANGE_REJECTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='master_data_change_request',object_id=req.request_code,new={'status':'REJECTED','domain':req.domain},reason=body.reason,details='Master-data change rejected')
    db.commit();return serialize_catalog_request(req)

@router.post('/catalog/{domain}/import/preview')
async def catalog_import_preview(domain:str,file:UploadFile=File(...),user:User=Depends(require_permission('master_data_import')),db:Session=Depends(get_db)):
    content=await file.read()
    try:return preview_catalog_import(db,workspace_id=user.workspace_id,domain=domain,filename=file.filename or 'master_data.xlsx',content=content)
    except ValueError as exc: raise HTTPException(400,str(exc))

@router.post('/catalog/{domain}/import/requests')
async def catalog_import_requests(domain:str,file:UploadFile=File(...),submit_for_review:bool=Form(False),reason:str=Form('Master-data bulk import'),user:User=Depends(require_permission('master_data_import')),db:Session=Depends(get_db)):
    content=await file.read()
    try:preview=preview_catalog_import(db,workspace_id=user.workspace_id,domain=domain,filename=file.filename or 'master_data.xlsx',content=content);domain=normalize_domain(domain)
    except ValueError as exc: raise HTTPException(400,str(exc))
    if preview['counts']['INVALID']: raise HTTPException(409,{'message':'Bulk import contains invalid rows. Resolve all validation errors first.','preview':preview})
    import uuid
    batch=f"MDB-{uuid.uuid4().hex[:8].upper()}";created=[]
    for item in preview['items']:
        if item['action'] not in {'CREATE','UPDATE'}: continue
        req=create_catalog_change(db,workspace_id=user.workspace_id,user=user,domain=domain,change_type=item['action'],payload=item['payload'],reason=reason,batch_code=batch)
        if submit_for_review: submit_catalog_change(req,user)
        created.append(req)
    audit(db,event_type='MASTER_DATA_BULK_STAGED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='master_data_change_batch',object_id=batch,new={'domain':domain,'requests':len(created),'submitted':submit_for_review,'filename':file.filename},reason=reason,details='Master-data workbook staged as governed requests')
    db.commit();return {'batch_code':batch,'domain':domain,'created_requests':len(created),'submitted_for_review':submit_for_review,'requests':[serialize_catalog_request(x) for x in created],'preview':preview}
