from app.timeutil import utcnow_naive
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Adjustment, Entity, Calculation, Policy, ApprovalRequest, ApprovalStep, FinancialPeriod
from ..security import require_permission, current_user, require_entity_access, entity_accessible
from ..services.audit import audit
from ..services.notifications import notify_roles, notify_user
from ..services.workflows import resolve_adjustment_workflow

router=APIRouter(tags=['adjustments-approvals'])

@router.get('/adjustments')
def adjustments(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    out=[]
    for a in db.query(Adjustment).filter(Adjustment.workspace_id==user.workspace_id).order_by(Adjustment.id.desc()):
        e=db.get(Entity,a.entity_id)
        if not e or not entity_accessible(db,user,e): continue
        req=db.query(ApprovalRequest).filter(ApprovalRequest.adjustment_id==a.id).first()
        steps=[]
        if req:
            steps=[{'step_order':s.step_order,'required_role':s.required_role,'status':s.status,'actor':s.actor,'comments':s.comments} for s in db.query(ApprovalStep).filter(ApprovalStep.approval_request_id==req.id).order_by(ApprovalStep.step_order)]
        out.append({'id':a.id,'adjustment_code':a.adjustment_code,'entity_code':e.entity_code,'amount':float(a.amount),'currency':a.currency,'status':a.status,'version':a.version,'adjustment_type':a.adjustment_type,'original_adjustment_id':a.original_adjustment_id,'batch_code':a.batch_code,'target_type':a.target_type,'target_value':float(a.target_value) if a.target_value is not None else None,'frequency':a.frequency,'reason':a.reason,'submitted_by':a.submitted_by,'approved_by':a.approved_by,'approval_status':req.status if req else None,'current_step':req.current_step if req else None,'workflow_code':req.workflow_code if req else None,'workflow_version':req.workflow_version if req else None,'steps':steps})
    return out


def _applicable_active_policy(db:Session,a:Adjustment):
    calc=db.get(Calculation,a.calculation_id)
    if not calc: return None
    linked=db.get(Policy,calc.policy_id)
    q=db.query(Policy).filter(Policy.workspace_id==a.workspace_id,Policy.entity_id==a.entity_id,Policy.status=='ACTIVE')
    if linked: q=q.filter(Policy.policy_code==linked.policy_code,Policy.method==linked.method,Policy.pli==linked.pli)
    candidates=q.order_by(Policy.id.desc()).all()
    for p in candidates:
        if p.effective_from and calc.period < p.effective_from[:7]:
            continue
        if p.effective_to and calc.period > p.effective_to[:7]:
            continue
        return p
    return candidates[0] if candidates else None

def _policy_consistency(db:Session,a:Adjustment):
    calc=db.get(Calculation,a.calculation_id)
    linked=db.get(Policy,calc.policy_id) if calc else None
    active=_applicable_active_policy(db,a)
    expected=float(active.target) if active and a.target_type=='POLICY_TARGET' else None
    actual=float(a.target_value) if a.target_value is not None else None
    consistent=(expected is None or actual is None or abs(expected-actual) < 1e-9)
    return {'consistent':consistent,'linked_policy_id':linked.id if linked else None,'linked_policy_code':linked.policy_code if linked else None,'linked_policy_version':linked.version if linked else None,'active_policy_id':active.id if active else None,'active_policy_code':active.policy_code if active else None,'active_policy_version':active.version if active else None,'active_policy_target':expected,'adjustment_target':actual}

def _adjustment_detail(db:Session,a:Adjustment):
    e=db.get(Entity,a.entity_id);calc=db.get(Calculation,a.calculation_id);pol=db.get(Policy,calc.policy_id) if calc else None
    fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==a.entity_id,FinancialPeriod.period==calc.period).first() if calc else None
    req=db.query(ApprovalRequest).filter(ApprovalRequest.adjustment_id==a.id).first()
    steps=[]
    if req:
        steps=[{'step_order':x.step_order,'required_role':x.required_role,'status':x.status,'actor':x.actor,'comments':x.comments,'decided_at':x.decided_at.isoformat() if x.decided_at else None} for x in db.query(ApprovalStep).filter(ApprovalStep.approval_request_id==req.id).order_by(ApprovalStep.step_order)]
    return {'id':a.id,'adjustment_code':a.adjustment_code,'entity_code':e.entity_code if e else None,'amount':float(a.amount),'currency':a.currency,'status':a.status,'version':a.version,'adjustment_type':a.adjustment_type,'target_type':a.target_type,'target_value':float(a.target_value) if a.target_value is not None else None,'frequency':a.frequency,'reason':a.reason,'submitted_by':a.submitted_by,'approved_by':a.approved_by,'created_at':a.created_at.isoformat() if a.created_at else None,'calculation':({'id':calc.id,'calculation_code':calc.calculation_code,'period':calc.period,'revenue':float(calc.revenue),'ebit':float(calc.ebit),'actual_pli':float(calc.actual_pli),'target_pli':float(calc.target_pli),'source_hash':calc.source_hash,'manifest':calc.manifest} if calc else None),'policy':({'id':pol.id,'policy_code':pol.policy_code,'version':pol.version,'status':pol.status,'method':pol.method,'pli':pol.pli,'target':float(pol.target),'benchmark_id':pol.benchmark_id,'effective_from':pol.effective_from,'effective_to':pol.effective_to} if pol else None),'financial_period':({'revenue':float(fp.revenue),'cogs':float(fp.cogs),'opex':float(fp.opex),'source_import_id':fp.source_import_id} if fp else None),'policy_consistency':_policy_consistency(db,a),'approval':({'id':req.id,'status':req.status,'current_step':req.current_step,'workflow_code':req.workflow_code,'workflow_version':req.workflow_version,'created_by':req.created_by,'steps':steps} if req else None)}

@router.get('/adjustments/{adjustment_id}')
def adjustment_detail(adjustment_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    a=db.query(Adjustment).filter(Adjustment.id==adjustment_id,Adjustment.workspace_id==user.workspace_id).first()
    if not a: raise HTTPException(404,'Adjustment not found')
    e=db.get(Entity,a.entity_id);require_entity_access(db,user,e)
    return _adjustment_detail(db,a)

@router.post('/adjustments/{adjustment_id}/submit')
def submit(adjustment_id:int,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    a=db.query(Adjustment).filter(Adjustment.id==adjustment_id,Adjustment.workspace_id==user.workspace_id).first()
    if not a: raise HTTPException(404,'Adjustment not found')
    e=db.get(Entity,a.entity_id);require_entity_access(db,user,e,write=True)
    if a.status not in ('PROPOSED','RETURNED','REJECTED'): raise HTTPException(409,'Adjustment not submittable')
    consistency=_policy_consistency(db,a)
    if not consistency['consistent']: raise HTTPException(409,f"Policy target mismatch: adjustment target {consistency['adjustment_target']} vs active policy {consistency['active_policy_code']} v{consistency['active_policy_version']} target {consistency['active_policy_target']}")
    if db.query(ApprovalRequest).filter(ApprovalRequest.adjustment_id==a.id,ApprovalRequest.status=='PENDING').first(): raise HTTPException(409,'Approval request already pending')
    calc=db.get(Calculation,a.calculation_id);pol=db.get(Policy,calc.policy_id)
    workflow=resolve_adjustment_workflow(db,user.workspace_id,amount=a.amount,materiality=a.materiality)
    matrix=(workflow or {}).get('roles') or (pol.approval_matrix or {}).get('steps') or ['TP_MANAGER','FINANCE_CONTROLLER']
    req=ApprovalRequest(workspace_id=user.workspace_id,adjustment_id=a.id,current_step=1,status='PENDING',created_by=user.email,
                        workflow_code=(workflow or {}).get('code'),workflow_version=(workflow or {}).get('version'))
    db.add(req);db.flush()
    for idx,role in enumerate(matrix,1): db.add(ApprovalStep(approval_request_id=req.id,step_order=idx,required_role=role,status='PENDING'))
    prev=a.status;a.status='SUBMITTED';a.submitted_by=user.email
    notify_roles(db,user.workspace_id,['TP_MANAGER','HEAD_OF_TP','GROUP_TAX_DIRECTOR','PLATFORM_ADMIN'],'True-up approval required',f'{a.adjustment_code} · {e.entity_code} · {a.currency} {float(a.amount):,.2f} submitted by {user.email}')
    audit(db,event_type='ADJUSTMENT_SUBMITTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='adjustment',object_id=a.adjustment_code,previous={'status':prev},new={'status':a.status,'approval_steps':matrix,'workflow_code':req.workflow_code,'workflow_version':req.workflow_version},details='Adjustment submitted to version-pinned approval workflow')
    db.commit();return {'status':a.status,'approval_request_id':req.id,'steps':matrix,'workflow_code':req.workflow_code,'workflow_version':req.workflow_version}

class DecisionIn(BaseModel): comments:str|None=None

@router.post('/adjustments/{adjustment_id}/approve')
def approve(adjustment_id:int,body:DecisionIn|None=None,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    a=db.query(Adjustment).filter(Adjustment.id==adjustment_id,Adjustment.workspace_id==user.workspace_id).with_for_update().first()
    if not a: raise HTTPException(404,'Adjustment not found')
    e=db.get(Entity,a.entity_id);require_entity_access(db,user,e,approve=True)
    req=db.query(ApprovalRequest).filter(ApprovalRequest.adjustment_id==a.id,ApprovalRequest.status=='PENDING').with_for_update().first()
    if not req: raise HTTPException(409,'No pending approval request')
    consistency=_policy_consistency(db,a)
    if not consistency['consistent']: raise HTTPException(409,f"Approval blocked by policy target mismatch: {consistency}")
    if req.created_by==user.email: raise HTTPException(409,'Segregation of duties: preparer cannot approve own adjustment')
    step=db.query(ApprovalStep).filter(ApprovalStep.approval_request_id==req.id,ApprovalStep.step_order==req.current_step).with_for_update().first()
    if not step: raise HTTPException(409,'Approval step not found')
    if user.role!='PLATFORM_ADMIN' and user.role!=step.required_role and not (user.role=='GROUP_TAX_DIRECTOR' and step.required_role=='HEAD_OF_TP'):
        raise HTTPException(403,f'Current step requires role {step.required_role}')
    step.status='APPROVED';step.actor=user.email;step.comments=(body.comments if body else None);step.decided_at=utcnow_naive()
    remaining=db.query(ApprovalStep).filter(ApprovalStep.approval_request_id==req.id,ApprovalStep.step_order>req.current_step).order_by(ApprovalStep.step_order).first()
    if remaining:
        req.current_step=remaining.step_order;a.status='IN_REVIEW'
    else:
        req.status='APPROVED';a.status='APPROVED';a.approved_by=user.email;a.locked_at=utcnow_naive()
    if a.status=='APPROVED': notify_user(db,user.workspace_id,req.created_by,'True-up approved',f'{a.adjustment_code} was fully approved by {user.email}')
    audit(db,event_type='APPROVAL_STEP_APPROVED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='adjustment',object_id=a.adjustment_code,new={'step':step.step_order,'required_role':step.required_role,'adjustment_status':a.status},details=f'Approved step {step.step_order}')
    db.commit();return {'status':a.status,'approval_status':req.status,'next_step':req.current_step if req.status=='PENDING' else None}

@router.post('/adjustments/{adjustment_id}/reject')
def reject(adjustment_id:int,body:DecisionIn,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    a=db.query(Adjustment).filter(Adjustment.id==adjustment_id,Adjustment.workspace_id==user.workspace_id).with_for_update().first()
    if not a: raise HTTPException(404,'Adjustment not found')
    req=db.query(ApprovalRequest).filter(ApprovalRequest.adjustment_id==a.id,ApprovalRequest.status=='PENDING').with_for_update().first()
    if not req: raise HTTPException(409,'No pending approval request')
    if req.created_by==user.email: raise HTTPException(409,'Segregation of duties: preparer cannot reject own adjustment')
    step=db.query(ApprovalStep).filter(ApprovalStep.approval_request_id==req.id,ApprovalStep.step_order==req.current_step).first()
    if user.role!='PLATFORM_ADMIN' and user.role!=step.required_role: raise HTTPException(403,f'Current step requires role {step.required_role}')
    step.status='REJECTED';step.actor=user.email;step.comments=body.comments;step.decided_at=utcnow_naive();req.status='REJECTED';a.status='REJECTED'
    notify_user(db,user.workspace_id,req.created_by,'True-up rejected',f'{a.adjustment_code} was rejected by {user.email}: {body.comments or "No comment"}')
    audit(db,event_type='ADJUSTMENT_REJECTED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=db.get(Entity,a.entity_id).entity_code,object_type='adjustment',object_id=a.adjustment_code,reason=body.comments,new={'status':'REJECTED'},details='Adjustment rejected')
    db.commit();return {'status':a.status}


@router.post('/adjustments/{adjustment_id}/return')
def return_adjustment(adjustment_id:int,body:DecisionIn,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    a=db.query(Adjustment).filter(Adjustment.id==adjustment_id,Adjustment.workspace_id==user.workspace_id).with_for_update().first()
    if not a: raise HTTPException(404,'Adjustment not found')
    req=db.query(ApprovalRequest).filter(ApprovalRequest.adjustment_id==a.id,ApprovalRequest.status=='PENDING').with_for_update().first()
    if not req: raise HTTPException(409,'No pending approval request')
    if req.created_by==user.email: raise HTTPException(409,'Segregation of duties: preparer cannot return own adjustment')
    step=db.query(ApprovalStep).filter(ApprovalStep.approval_request_id==req.id,ApprovalStep.step_order==req.current_step).first()
    if user.role!='PLATFORM_ADMIN' and user.role!=step.required_role: raise HTTPException(403,f'Current step requires role {step.required_role}')
    if not body.comments: raise HTTPException(422,'Return-for-rework comments are required')
    step.status='RETURNED';step.actor=user.email;step.comments=body.comments;step.decided_at=utcnow_naive();req.status='RETURNED';a.status='RETURNED'
    notify_user(db,user.workspace_id,req.created_by,'True-up returned for rework',f'{a.adjustment_code} was returned by {user.email}: {body.comments}')
    audit(db,event_type='ADJUSTMENT_RETURNED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=db.get(Entity,a.entity_id).entity_code,object_type='adjustment',object_id=a.adjustment_code,reason=body.comments,new={'status':'RETURNED'},details='Adjustment returned for rework')
    db.commit();return {'status':a.status,'approval_status':req.status}
