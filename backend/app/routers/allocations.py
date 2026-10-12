from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, AllocationRule, AllocationRun, AllocationResult, NormalizedFinancialRecord
from ..security import require_permission
from ..services.allocations import execute_configured_allocation, run_allocation, simulate_allocation
from ..services.audit import audit
from ..timeutil import utcnow_naive

router=APIRouter(prefix='/allocations',tags=['allocations'])

COST_POOL_TYPES={'IT','HR','FINANCE','LEGAL','PROCUREMENT','MANAGEMENT','MARKETING','FACILITIES','R&D','SHARED_SERVICES','MANUFACTURING_OVERHEAD','CUSTOM'}
DRIVER_TYPES={'REVENUE','HEADCOUNT','FTE','PAYROLL','USERS','TRANSACTIONS','UNITS','ORDERS','INVOICES','FLOOR_SPACE','ASSETS','DIRECT_COST','USAGE','TICKETS','HOURS','PRODUCTION_VOLUME','CUSTOM','COMPOSITE'}

class AllocationRunIn(BaseModel):
    rule_code:str
    period:str
    source_amount:float
    driver_values:dict[str,float]

class AllocationRuleIn(BaseModel):
    rule_code:str=Field(min_length=2,max_length=80)
    sender_segment:str=Field(min_length=1,max_length=80)
    cost_pool_name:str=Field(min_length=1,max_length=120)
    cost_pool_type:str='CUSTOM'
    sender_entity_code:str|None=None
    period_scope:str='MONTHLY'
    currency:str='EUR'
    source_accounts:list[str]=[]
    source_cost_centers:list[str]=[]
    source_profit_centers:list[str]=[]
    source_transactions:list[str]=[]
    source_amount_source:str='MANUAL_CONTROLLED'
    manual_amount_allowed:bool=True
    driver_type:str='CUSTOM'
    driver_source:str='MANUAL_CONTROLLED'
    driver_weights:dict[str,float]|None=None
    recipients:dict[str,float]={}
    exclusions:list[dict|str]=[]
    stages:list[dict]=[]
    recipient_rules:dict|list|None=None
    markup_treatment:str='NO_MARKUP'
    markup_rate:float|None=None
    fx_methodology:str|None=None
    fx_version:str|None=None
    effective_from:str|None=None
    effective_to:str|None=None

class AllocationExecuteIn(BaseModel):
    period:str
    source_amount:float|None=None
    driver_values:dict[str,float]|None=None
    composite_driver_values:dict[str,dict[str,float]]|None=None
    stage_driver_values:dict[str,dict]|None=None
    exclusion_amounts:dict[str,float]={}

class CopyRuleIn(BaseModel):
    new_rule_code:str


def _validate_rule(body:AllocationRuleIn):
    if body.cost_pool_type.upper() not in COST_POOL_TYPES: raise HTTPException(400,'Unsupported cost_pool_type')
    if body.driver_type.upper() not in DRIVER_TYPES: raise HTTPException(400,'Unsupported driver_type')
    if len(body.currency)!=3: raise HTTPException(400,'Currency must be a three-letter ISO code')
    if body.effective_from and body.effective_to and body.effective_from>body.effective_to: raise HTTPException(400,'effective_from cannot be after effective_to')
    if body.driver_weights:
        total=sum(body.driver_weights.values())
        if abs(total-1)>0.000001 and abs(total-100)>0.0001: raise HTTPException(400,'Composite driver weights must sum to 1.0 or 100')
        if any(v<0 for v in body.driver_weights.values()): raise HTTPException(400,'Driver weights cannot be negative')
    if body.markup_rate is not None and body.markup_rate<0: raise HTTPException(400,'markup_rate cannot be negative')
    if body.stages:
        codes=[]
        for i,stage in enumerate(body.stages,1):
            code=str((stage or {}).get('code') or (stage or {}).get('stage_code') or f'STAGE_{i}').strip().upper()
            if code in codes: raise HTTPException(400,f'Duplicate allocation stage code: {code}')
            codes.append(code)


def _rule_dict(r:AllocationRule):
    return {
        'id':r.id,'rule_code':r.rule_code,'version':r.version,'sender_segment':r.sender_segment,'cost_pool_name':r.cost_pool_name,
        'cost_pool_type':r.cost_pool_type,'sender_entity_code':r.sender_entity_code,'period_scope':r.period_scope,'currency':r.currency,
        'source_accounts':r.source_accounts or [],'source_cost_centers':r.source_cost_centers or [],'source_profit_centers':r.source_profit_centers or [],
        'source_transactions':r.source_transactions or [],'source_amount_source':r.source_amount_source,'manual_amount_allowed':r.manual_amount_allowed,
        'driver_type':r.driver_type,'driver_source':r.driver_source,'driver_weights':r.driver_weights,'recipients':r.recipients or {},
        'exclusions':r.exclusions or [],'stages':r.stages or [],'recipient_rules':r.recipient_rules,'markup_eligible':r.markup_eligible,
        'markup_treatment':r.markup_treatment,'markup_rate':float(r.markup_rate) if r.markup_rate is not None else None,
        'fx_methodology':r.fx_methodology,'fx_version':r.fx_version,'effective_from':r.effective_from,'effective_to':r.effective_to,
        'status':r.status,'created_by':r.created_by,'approved_by':r.approved_by,'approved_at':r.approved_at.isoformat() if r.approved_at else None,
        'created_at':r.created_at.isoformat() if r.created_at else None,'updated_at':r.updated_at.isoformat() if r.updated_at else None,
    }


def _apply_rule(r:AllocationRule,body:AllocationRuleIn):
    r.sender_segment=body.sender_segment;r.cost_pool_name=body.cost_pool_name;r.cost_pool_type=body.cost_pool_type.upper();r.sender_entity_code=body.sender_entity_code.upper() if body.sender_entity_code else None
    r.period_scope=body.period_scope.upper();r.currency=body.currency.upper();r.source_accounts=body.source_accounts;r.source_cost_centers=body.source_cost_centers;r.source_profit_centers=body.source_profit_centers;r.source_transactions=body.source_transactions
    r.source_amount_source=body.source_amount_source.upper();r.manual_amount_allowed=body.manual_amount_allowed;r.driver_type=body.driver_type.upper();r.driver_source=body.driver_source.upper();r.driver_weights=body.driver_weights;r.recipients=body.recipients
    r.exclusions=body.exclusions;r.stages=body.stages;r.recipient_rules=body.recipient_rules;r.markup_treatment=body.markup_treatment.upper();r.markup_rate=body.markup_rate;r.markup_eligible=body.markup_treatment.upper() in {'MARKUP_ELIGIBLE','CUSTOM_MARKUP'}
    r.fx_methodology=body.fx_methodology;r.fx_version=body.fx_version;r.effective_from=body.effective_from;r.effective_to=body.effective_to


def _source_amount(db:Session,user:User,rule:AllocationRule,body:AllocationExecuteIn)->float:
    if body.source_amount is not None:
        if not rule.manual_amount_allowed and rule.source_amount_source!='MANUAL_CONTROLLED': raise HTTPException(409,'Manual source amount is disabled for this rule')
        return body.source_amount
    if rule.source_amount_source!='NORMALIZED_FINANCIALS': raise HTTPException(400,'source_amount is required unless source_amount_source=NORMALIZED_FINANCIALS')
    q=db.query(NormalizedFinancialRecord).filter(NormalizedFinancialRecord.workspace_id==user.workspace_id,NormalizedFinancialRecord.period==body.period)
    if rule.sender_segment:q=q.filter(NormalizedFinancialRecord.segment_code==rule.sender_segment)
    if rule.source_accounts:q=q.filter(NormalizedFinancialRecord.gl_account.in_(rule.source_accounts))
    rows=q.all()
    if not rows: raise HTTPException(409,'No normalized financial rows match the configured cost-pool source')
    # Financial source rows may use debit-negative sign conventions. Cost-pool
    # derivation is therefore an absolute cost basis; source lineage remains in P&L/import records.
    return float(sum(abs(x.amount) for x in rows))

@router.get('/rules')
def rules(status:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id)
    if status:q=q.filter(AllocationRule.status==status.upper())
    return [_rule_dict(r) for r in q.order_by(AllocationRule.rule_code,AllocationRule.version.desc()).all()]

@router.get('/rules/{rule_id}')
def rule_detail(rule_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    return _rule_dict(r)

@router.get('/rules/{rule_code}/history')
def rule_history(rule_code:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.rule_code==rule_code.upper()).order_by(AllocationRule.version.desc()).all()
    if not rows: raise HTTPException(404,'Allocation rule not found')
    return [_rule_dict(x) for x in rows]

@router.post('/rules')
def create_rule(body:AllocationRuleIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    _validate_rule(body);code=body.rule_code.upper()
    latest=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.rule_code==code).order_by(AllocationRule.version.desc()).first()
    if latest and latest.status in {'DRAFT','REVIEW'}: raise HTTPException(409,'A draft/review version already exists for this rule code')
    version=(latest.version+1) if latest else 1
    r=AllocationRule(workspace_id=user.workspace_id,rule_code=code,version=version,sender_segment=body.sender_segment,cost_pool_name=body.cost_pool_name,driver_type=body.driver_type.upper(),recipients={},status='DRAFT',created_by=user.email)
    _apply_rule(r,body);db.add(r);db.flush()
    audit(db,event_type='ALLOCATION_RULE_DRAFTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='allocation_rule',object_id=f'{code}:v{version}',new=_rule_dict(r),details='Configurable allocation rule drafted')
    db.commit();return _rule_dict(r)

@router.put('/rules/{rule_id}')
def update_rule(rule_id:int,body:AllocationRuleIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    _validate_rule(body);r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    if r.status!='DRAFT': raise HTTPException(409,'Only DRAFT allocation rules can be edited')
    if body.rule_code.upper()!=r.rule_code: raise HTTPException(409,'rule_code cannot be changed; use Copy for a new rule code')
    previous=_rule_dict(r);_apply_rule(r,body)
    audit(db,event_type='ALLOCATION_RULE_EDITED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='allocation_rule',object_id=f'{r.rule_code}:v{r.version}',previous=previous,new=_rule_dict(r),details='Allocation rule draft edited')
    db.commit();return _rule_dict(r)

@router.post('/rules/{rule_id}/copy')
def copy_rule(rule_id:int,body:CopyRuleIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    source=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not source: raise HTTPException(404,'Allocation rule not found')
    code=body.new_rule_code.upper()
    if db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.rule_code==code).first(): raise HTTPException(409,'Target rule code already exists')
    fields={k:v for k,v in _rule_dict(source).items() if k not in {'id','rule_code','version','status','created_by','approved_by','approved_at','created_at','updated_at'}}
    r=AllocationRule(workspace_id=user.workspace_id,rule_code=code,version=1,status='DRAFT',created_by=user.email,sender_segment=source.sender_segment,cost_pool_name=source.cost_pool_name,driver_type=source.driver_type,recipients=source.recipients or {})
    for field in ['cost_pool_type','sender_entity_code','period_scope','currency','source_accounts','source_cost_centers','source_profit_centers','source_transactions','source_amount_source','manual_amount_allowed','driver_source','driver_weights','exclusions','stages','recipient_rules','markup_eligible','markup_treatment','markup_rate','fx_methodology','fx_version','effective_from','effective_to']:
        setattr(r,field,getattr(source,field))
    db.add(r);db.commit();db.refresh(r);return _rule_dict(r)

@router.post('/rules/{rule_id}/submit')
def submit_rule(rule_id:int,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    if r.status!='DRAFT': raise HTTPException(409,'Only DRAFT rules can be submitted')
    r.status='REVIEW';audit(db,event_type='ALLOCATION_RULE_SUBMITTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='allocation_rule',object_id=f'{r.rule_code}:v{r.version}',new={'status':'REVIEW'},details='Allocation methodology submitted for approval');db.commit();return _rule_dict(r)

@router.post('/rules/{rule_id}/approve')
def approve_rule(rule_id:int,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    if r.status!='REVIEW': raise HTTPException(409,'Only REVIEW rules can be approved')
    if r.created_by==user.email: raise HTTPException(403,'Maker-checker control: creator cannot approve own allocation rule')
    r.status='APPROVED';r.approved_by=user.email;r.approved_at=utcnow_naive();audit(db,event_type='ALLOCATION_RULE_APPROVED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='allocation_rule',object_id=f'{r.rule_code}:v{r.version}',new={'status':'APPROVED'},details='Allocation methodology approved');db.commit();return _rule_dict(r)

@router.post('/rules/{rule_id}/activate')
def activate_rule(rule_id:int,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    if r.status!='APPROVED': raise HTTPException(409,'Only APPROVED rules can be activated')
    db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.rule_code==r.rule_code,AllocationRule.status=='ACTIVE').update({'status':'SUPERSEDED'},synchronize_session=False)
    r.status='ACTIVE';audit(db,event_type='ALLOCATION_RULE_ACTIVATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='allocation_rule',object_id=f'{r.rule_code}:v{r.version}',new={'status':'ACTIVE'},details='Approved allocation rule activated');db.commit();return _rule_dict(r)

@router.post('/rules/{rule_id}/deactivate')
def deactivate_rule(rule_id:int,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    if r.status not in {'ACTIVE','APPROVED'}: raise HTTPException(409,'Only ACTIVE/APPROVED rules can be deactivated')
    r.status='INACTIVE';audit(db,event_type='ALLOCATION_RULE_DEACTIVATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='allocation_rule',object_id=f'{r.rule_code}:v{r.version}',new={'status':'INACTIVE'},details='Allocation rule deactivated');db.commit();return _rule_dict(r)

@router.post('/rules/{rule_id}/simulate')
def simulate_rule(rule_id:int,body:AllocationExecuteIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    try:source=_source_amount(db,user,r,body);result=simulate_allocation(r,source,body.driver_values,composite_driver_values=body.composite_driver_values,stage_driver_values=body.stage_driver_values,exclusion_amounts=body.exclusion_amounts)
    except ValueError as exc: raise HTTPException(400,str(exc))
    return {'simulation':True,'period':body.period,**result}

@router.post('/rules/{rule_id}/execute')
def execute_rule(rule_id:int,body:AllocationExecuteIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.id==rule_id).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    if r.status!='ACTIVE': raise HTTPException(409,'Only ACTIVE allocation rules can execute')
    try:source=_source_amount(db,user,r,body);result=execute_configured_allocation(db,r,body.period,source,body.driver_values,composite_driver_values=body.composite_driver_values,stage_driver_values=body.stage_driver_values,exclusion_amounts=body.exclusion_amounts)
    except ValueError as exc: raise HTTPException(400,str(exc))
    audit(db,event_type='ALLOCATION_RUN',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='allocation_run',object_id=result['run_code'],new=result,details=f"Allocation {r.rule_code}: residual {result['residual']}")
    db.commit();return result

# Backward-compatible RC.10 execution endpoint. It remains API-compatible but the
# primary business UI no longer uses a fixed amount, recipients or period.
@router.post('/run')
def run(body:AllocationRunIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    r=db.query(AllocationRule).filter(AllocationRule.workspace_id==user.workspace_id,AllocationRule.rule_code==body.rule_code,AllocationRule.status=='ACTIVE').order_by(AllocationRule.version.desc()).first()
    if not r: raise HTTPException(404,'Allocation rule not found')
    result=run_allocation(db,r,body.period,body.source_amount,body.driver_values)
    audit(db,event_type='ALLOCATION_RUN',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='allocation_run',object_id=result['run_code'],new=result,details=f"Allocation {body.rule_code}: residual {result['residual']}")
    db.commit();return result

@router.get('/runs')
def runs(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    out=[]
    for x in db.query(AllocationRun).filter(AllocationRun.workspace_id==user.workspace_id).order_by(AllocationRun.id.desc()).limit(250):
        results=db.query(AllocationResult).filter(AllocationResult.allocation_run_id==x.id).all()
        rule=db.query(AllocationRule).filter(AllocationRule.id==x.rule_id).first()
        out.append({'run_code':x.run_code,'rule_code':rule.rule_code if rule else None,'rule_version':rule.version if rule else None,'period':x.period,'source_amount':float(x.source_amount),'allocated_amount':float(x.allocated_amount),'residual':float(x.residual),'status':x.status,'results':[{'recipient_segment':r.recipient_segment,'share':float(r.driver_share),'allocated_amount':float(r.allocated_amount)} for r in results]})
    return out
