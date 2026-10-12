from pathlib import Path
import os
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, SourceImport, RawFinancialRecord, Entity
from ..security import require_permission, require_entity_access
from ..services.ingestion import validate_and_store, sha256_bytes
from ..services.audit import audit

router=APIRouter(prefix='/imports',tags=['data-imports'])
UPLOAD_DIR=Path(os.getenv('UPLOAD_DIR','/data/uploads'))

@router.post('')
async def create_import(source_system:str=Form(...),period:str=Form(...),entity_code:str|None=Form(None),allow_duplicate:bool=Form(False),file:UploadFile=File(...),user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    data=await file.read()
    if len(data)>100*1024*1024: raise HTTPException(413,'File exceeds 100 MB demo/API limit; use SFTP/warehouse adapter for larger batches')
    e=None
    if entity_code:
        e=db.query(Entity).filter(Entity.workspace_id==user.workspace_id,Entity.entity_code==entity_code).first()
        if not e: raise HTTPException(404,'Entity not found')
        require_entity_access(db,user,e,write=True)
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    safe_name=Path(file.filename or 'upload.dat').name
    digest=sha256_bytes(data)
    duplicate=db.query(SourceImport).filter(SourceImport.workspace_id==user.workspace_id,SourceImport.sha256==digest,SourceImport.source_system==source_system,SourceImport.period==period,SourceImport.entity_id==(e.id if e else None),SourceImport.status.in_(['VALIDATED','PARTIAL','ACCEPTED'])).order_by(SourceImport.id.desc()).first()
    if duplicate and not allow_duplicate:
        raise HTTPException(409,{'message':'Duplicate import blocked','existing_import_code':duplicate.import_code,'sha256':digest,'source_system':source_system,'period':period})
    path=UPLOAD_DIR/f'{digest[:12]}_{safe_name}'
    path.write_bytes(data)
    result=validate_and_store(db,workspace_id=user.workspace_id,actor=user.email,source_system=source_system,period=period,filename=safe_name,data=data,entity_id=e.id if e else None,original_path=str(path))
    audit(db,event_type='IMPORT_VALIDATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=entity_code,object_type='source_import',object_id=result.get('import_code'),new=result,details=f'Validated {safe_name}')
    db.commit();return result

@router.get('')
def list_imports(limit:int=Query(100,ge=1,le=500),user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(SourceImport).filter(SourceImport.workspace_id==user.workspace_id).order_by(SourceImport.id.desc()).limit(limit).all()
    return [{'id':x.id,'import_code':x.import_code,'source_system':x.source_system,'period':x.period,'filename':x.filename,'sha256':x.sha256,'row_count':x.row_count,'accepted_rows':x.accepted_rows,'rejected_rows':x.rejected_rows,'warning_rows':x.warning_rows,'source_control_total':float(x.source_control_total),'imported_control_total':float(x.imported_control_total),'status':x.status,'created_at':x.created_at.isoformat()} for x in rows]

@router.get('/{import_id}/issues')
def import_issues(import_id:int,status:str|None=None,limit:int=Query(200,ge=1,le=2000),user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    imp=db.query(SourceImport).filter(SourceImport.id==import_id,SourceImport.workspace_id==user.workspace_id).first()
    if not imp: raise HTTPException(404,'Import not found')
    q=db.query(RawFinancialRecord).filter(RawFinancialRecord.source_import_id==imp.id)
    if status: q=q.filter(RawFinancialRecord.validation_status==status.upper())
    else: q=q.filter(RawFinancialRecord.validation_status!='VALID')
    return [{'id':x.id,'row_number':x.row_number,'entity_code':x.entity_code,'document_number':x.document_number,'gl_account':x.gl_account,'amount':float(x.amount),'currency':x.currency,'status':x.validation_status,'messages':x.validation_messages} for x in q.limit(limit).all()]

@router.get('/{import_id}/control')
def import_control(import_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    imp=db.query(SourceImport).filter(SourceImport.id==import_id,SourceImport.workspace_id==user.workspace_id).first()
    if not imp: raise HTTPException(404,'Import not found')
    difference=imp.source_control_total-imp.imported_control_total
    return {'source_control_total':float(imp.source_control_total),'accepted_control_total':float(imp.imported_control_total),'difference':float(difference),'rejected_rows':imp.rejected_rows,'explained':imp.rejected_rows>0,'status':'RECONCILED_WITH_REJECTIONS' if imp.rejected_rows>0 else 'RECONCILED'}
