from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, MappingRule, SourceImport
from ..security import require_permission
from ..services.mapping import run_mapping, detect_conflicts
from ..services.audit import audit

router=APIRouter(prefix='/mappings',tags=['tp-mapping'])

class MappingRuleIn(BaseModel):
    rule_code:str
    priority:int=100
    match_fields:dict
    segment_code:str
    controlled_transaction_code:str
    policy_code:str
    effective_from:str|None=None
    effective_to:str|None=None

@router.get('')
def list_rules(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rules=db.query(MappingRule).filter(MappingRule.workspace_id==user.workspace_id).order_by(MappingRule.priority,MappingRule.rule_code).all()
    return [{'id':r.id,'rule_code':r.rule_code,'version':r.version,'priority':r.priority,'match_fields':r.match_fields,'segment_code':r.segment_code,'controlled_transaction_code':r.controlled_transaction_code,'policy_code':r.policy_code,'status':r.status,'approved_by':r.approved_by} for r in rules]

@router.post('')
def create_rule(body:MappingRuleIn,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    prior=db.query(MappingRule).filter(MappingRule.workspace_id==user.workspace_id,MappingRule.rule_code==body.rule_code).order_by(MappingRule.version.desc()).first()
    version=(prior.version+1) if prior else 1
    r=MappingRule(workspace_id=user.workspace_id,rule_code=body.rule_code,version=version,priority=body.priority,match_fields=body.match_fields,segment_code=body.segment_code,controlled_transaction_code=body.controlled_transaction_code,policy_code=body.policy_code,effective_from=body.effective_from,effective_to=body.effective_to,status='ACTIVE',approved_by=user.email)
    db.add(r);audit(db,event_type='MAPPING_RULE_CREATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='mapping_rule',object_id=body.rule_code,new=body.model_dump(),details=f'Mapping rule {body.rule_code} v{version}')
    db.commit();return {'id':r.id,'version':version,'status':r.status}

@router.post('/run')
def map_records(import_id:int|None=None,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    if import_id:
        imp=db.query(SourceImport).filter(SourceImport.id==import_id,SourceImport.workspace_id==user.workspace_id).first()
        if not imp: raise HTTPException(404,'Import not found')
    result=run_mapping(db,user.workspace_id,import_id)
    audit(db,event_type='MAPPING_RUN',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='mapping_run',new=result,details=f"Mapped {result['mapped']} of {result['total']} records")
    db.commit();return result

@router.get('/coverage')
def coverage(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    result=run_mapping(db,user.workspace_id,None);db.rollback() # dry-ish: existing mapped rows are counted; unflushed additions rolled back
    return result

@router.get('/conflicts')
def conflicts(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rules=db.query(MappingRule).filter(MappingRule.workspace_id==user.workspace_id).all()
    return detect_conflicts(rules)
