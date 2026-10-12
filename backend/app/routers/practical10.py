from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, date
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    User, Entity, Policy, MasterDataRecord, Calculation, FinancialPeriod, Adjustment,
    PnLRun, PnLSnapshot, PnLSegmentResult, NormalizedFinancialRecord, RawFinancialRecord, Reconciliation, ReconciliationStage, ExceptionCase,
    WorkflowInstance, WorkflowTask, UserDelegation, QualificationControl,
    QualificationEvidence, ServiceAccount, Document, AuditEvent
)
from ..security import require_permission, require_entity_access
from ..services.audit import audit
from ..services.finance import D, money, calculate_policy_result
from ..services.workflows import resolve_workflow
from ..timeutil import utcnow_naive
from ..settings import settings

router = APIRouter(tags=['practicality-10'])

METHODS={'TNMM','COST_PLUS','RESALE_PRICE','RESALE_MINUS','CUP','PROFIT_SPLIT','ROYALTY','SERVICE_CHARGE'}
PLIS={'ROS','EBIT_TOTAL_COSTS','EBIT/TC','EBIT_OPEX','EBIT/OPEX','BERRY_RATIO','BERRY','GROSS_MARGIN','ROA','CUSTOM'}
POLICY_STATUSES={'DRAFT','REVIEW','APPROVED','ACTIVE','SUPERSEDED','ARCHIVED'}


def _entity(db:Session, workspace_id:int, code:str)->Entity:
    row=db.query(Entity).filter(Entity.workspace_id==workspace_id,Entity.entity_code==code.upper()).first()
    if not row: raise HTTPException(404,'Entity not found')
    return row


def _policy_dict(db:Session,p:Policy)->dict:
    e=db.get(Entity,p.entity_id)
    return {
        'id':p.id,'policy_code':p.policy_code,'version':p.version,'entity_code':e.entity_code if e else None,
        'tested_party_code':p.tested_party_code,'counterparty_code':p.counterparty_code,'transaction_type':p.transaction_type,
        'method':p.method,'pli':p.pli,'target':float(p.target),'lower_bound':float(p.lower_bound) if p.lower_bound is not None else None,
        'median':float(p.median) if p.median is not None else None,'upper_bound':float(p.upper_bound) if p.upper_bound is not None else None,
        'markup':float(p.markup) if p.markup is not None else None,'benchmark_id':p.benchmark_id,'status':p.status,
        'effective_from':p.effective_from,'effective_to':p.effective_to,'true_up_frequency':p.true_up_frequency,
        'materiality_threshold':float(p.materiality_threshold or 0),'tolerance':float(p.tolerance) if p.tolerance is not None else None,
        'cost_base':p.cost_base,'allocation_treatment':p.allocation_treatment,'currency':p.currency,
        'journal_template_code':p.journal_template_code,'workflow_code':p.workflow_code,'approval_matrix':p.approval_matrix,
        'created_by':p.created_by,'submitted_by':p.submitted_by,'approved_by':p.approved_by,'activated_by':p.activated_by,
        'submitted_at':p.submitted_at.isoformat() if p.submitted_at else None,'approved_at':p.approved_at.isoformat() if p.approved_at else None,
        'activated_at':p.activated_at.isoformat() if p.activated_at else None,'notes':p.notes,
    }


class PolicyIn(BaseModel):
    policy_code:str
    entity_code:str
    transaction_type:str='DISTRIBUTION'
    tested_party_code:str|None=None
    counterparty_code:str|None=None
    method:str='TNMM'
    pli:str='ROS'
    target:float
    lower_bound:float|None=None
    median:float|None=None
    upper_bound:float|None=None
    markup:float|None=None
    benchmark_id:str|None=None
    effective_from:str|None=None
    effective_to:str|None=None
    true_up_frequency:str='QUARTERLY'
    materiality_threshold:float=0
    tolerance:float|None=0.0001
    cost_base:str|None=None
    allocation_treatment:str|None=None
    currency:str|None=None
    journal_template_code:str|None=None
    workflow_code:str|None=None
    notes:str|None=None


def _validate_policy(db:Session,workspace_id:int,body:PolicyIn):
    method=body.method.upper(); pli=body.pli.upper()
    if method not in METHODS: raise HTTPException(422,f'Unsupported TP method: {method}')
    if pli not in PLIS: raise HTTPException(422,f'Unsupported PLI: {pli}')
    if body.effective_from and body.effective_to and body.effective_from>body.effective_to: raise HTTPException(422,'effective_from cannot be after effective_to')
    if body.lower_bound is not None and body.upper_bound is not None and body.lower_bound>body.upper_bound: raise HTTPException(422,'lower_bound cannot exceed upper_bound')
    if body.benchmark_id:
        bm=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==workspace_id,MasterDataRecord.domain=='BENCHMARKS',MasterDataRecord.record_code==body.benchmark_id.upper(),MasterDataRecord.active.is_(True)).first()
        if not bm: raise HTTPException(409,'Approved active benchmark not found')
        valid_until=(bm.attributes or {}).get('valid_until')
        if valid_until and valid_until<date.today().isoformat(): raise HTTPException(409,'Benchmark is expired')


@router.post('/policies/workbench')
def create_policy(body:PolicyIn,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    _validate_policy(db,user.workspace_id,body); e=_entity(db,user.workspace_id,body.entity_code);require_entity_access(db,user,e,write=True)
    code=body.policy_code.upper().strip()
    if db.query(Policy).filter(Policy.workspace_id==user.workspace_id,Policy.policy_code==code).first(): raise HTTPException(409,'Policy code already exists; create a new version instead')
    p=Policy(workspace_id=user.workspace_id,policy_code=code,version='1',entity_id=e.id,counterparty_code=body.counterparty_code,transaction_type=body.transaction_type.upper(),method=body.method.upper(),pli=body.pli.upper(),target=body.target,lower_bound=body.lower_bound,median=body.median,upper_bound=body.upper_bound,markup=body.markup,benchmark_id=body.benchmark_id.upper() if body.benchmark_id else None,status='DRAFT',effective_from=body.effective_from,effective_to=body.effective_to,true_up_frequency=body.true_up_frequency.upper(),materiality_threshold=body.materiality_threshold,tested_party_code=body.tested_party_code,tolerance=body.tolerance,cost_base=body.cost_base,allocation_treatment=body.allocation_treatment,currency=(body.currency or e.currency).upper(),journal_template_code=body.journal_template_code,workflow_code=body.workflow_code,created_by=user.email,notes=body.notes)
    db.add(p);db.flush();audit(db,event_type='POLICY_CREATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='policy',object_id=code,new=_policy_dict(db,p),details='TP policy draft created from Policy Workbench');db.commit();return _policy_dict(db,p)


@router.post('/policies/{policy_id}/new-version')
def new_policy_version(policy_id:int,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    old=db.query(Policy).filter(Policy.id==policy_id,Policy.workspace_id==user.workspace_id).first()
    if not old: raise HTTPException(404,'Policy not found')
    e=db.get(Entity,old.entity_id);require_entity_access(db,user,e,write=True)
    versions=db.query(Policy).filter(Policy.workspace_id==user.workspace_id,Policy.policy_code==old.policy_code).all()
    nums=[]
    for v in versions:
        try: nums.append(int(str(v.version).split('.')[0]))
        except Exception: pass
    version=str((max(nums) if nums else 0)+1)
    p=Policy(workspace_id=old.workspace_id,policy_code=old.policy_code,version=version,entity_id=old.entity_id,counterparty_code=old.counterparty_code,transaction_type=old.transaction_type,method=old.method,pli=old.pli,target=old.target,lower_bound=old.lower_bound,median=old.median,upper_bound=old.upper_bound,markup=old.markup,benchmark_id=old.benchmark_id,status='DRAFT',effective_from=old.effective_from,effective_to=old.effective_to,true_up_frequency=old.true_up_frequency,materiality_threshold=old.materiality_threshold,approval_matrix=old.approval_matrix,document_references=old.document_references,tested_party_code=old.tested_party_code,tolerance=old.tolerance,cost_base=old.cost_base,allocation_treatment=old.allocation_treatment,currency=old.currency,journal_template_code=old.journal_template_code,workflow_code=old.workflow_code,created_by=user.email,notes=old.notes)
    db.add(p);db.flush();audit(db,event_type='POLICY_VERSION_CREATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='policy',object_id=old.policy_code,new={'version':version},details='New governed policy version created');db.commit();return _policy_dict(db,p)


class PolicyPatch(BaseModel):
    target:float|None=None;lower_bound:float|None=None;median:float|None=None;upper_bound:float|None=None;markup:float|None=None
    benchmark_id:str|None=None;effective_from:str|None=None;effective_to:str|None=None;true_up_frequency:str|None=None
    materiality_threshold:float|None=None;tolerance:float|None=None;cost_base:str|None=None;allocation_treatment:str|None=None
    currency:str|None=None;journal_template_code:str|None=None;workflow_code:str|None=None;notes:str|None=None


@router.patch('/policies/{policy_id}/workbench')
def edit_policy(policy_id:int,body:PolicyPatch,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    p=db.query(Policy).filter(Policy.id==policy_id,Policy.workspace_id==user.workspace_id).first()
    if not p: raise HTTPException(404,'Policy not found')
    if p.status!='DRAFT': raise HTTPException(409,'Only DRAFT policy versions are editable')
    e=db.get(Entity,p.entity_id);require_entity_access(db,user,e,write=True);previous=_policy_dict(db,p)
    for k,v in body.model_dump(exclude_unset=True).items():
        if k=='benchmark_id' and v:
            bm=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain=='BENCHMARKS',MasterDataRecord.record_code==str(v).upper(),MasterDataRecord.active.is_(True)).first()
            if not bm: raise HTTPException(409,'Approved active benchmark not found')
            v=str(v).upper()
        setattr(p,k,v)
    if p.effective_from and p.effective_to and p.effective_from>p.effective_to: raise HTTPException(422,'effective_from cannot be after effective_to')
    audit(db,event_type='POLICY_EDITED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='policy',object_id=p.policy_code,previous=previous,new=_policy_dict(db,p),details='Draft policy edited');db.commit();return _policy_dict(db,p)


@router.post('/policies/{policy_id}/submit')
def submit_policy(policy_id:int,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    p=db.query(Policy).filter(Policy.id==policy_id,Policy.workspace_id==user.workspace_id).first()
    if not p: raise HTTPException(404,'Policy not found')
    if p.status!='DRAFT': raise HTTPException(409,'Only DRAFT policies can be submitted')
    p.status='REVIEW';p.submitted_by=user.email;p.submitted_at=utcnow_naive();db.commit();return _policy_dict(db,p)


@router.post('/policies/{policy_id}/approve')
def approve_policy(policy_id:int,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    p=db.query(Policy).filter(Policy.id==policy_id,Policy.workspace_id==user.workspace_id).with_for_update().first()
    if not p: raise HTTPException(404,'Policy not found')
    if p.status!='REVIEW': raise HTTPException(409,'Only REVIEW policies can be approved')
    if p.created_by and p.created_by==user.email: raise HTTPException(409,'Maker-checker: policy creator cannot approve own version')
    e=db.get(Entity,p.entity_id);require_entity_access(db,user,e,approve=True)
    p.status='APPROVED';p.approved_by=user.email;p.approved_at=utcnow_naive();db.commit();return _policy_dict(db,p)


@router.post('/policies/{policy_id}/activate')
def activate_policy(policy_id:int,user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    p=db.query(Policy).filter(Policy.id==policy_id,Policy.workspace_id==user.workspace_id).with_for_update().first()
    if not p: raise HTTPException(404,'Policy not found')
    if p.status!='APPROVED': raise HTTPException(409,'Only APPROVED policies can be activated')
    e=db.get(Entity,p.entity_id);require_entity_access(db,user,e,approve=True)
    active=db.query(Policy).filter(Policy.workspace_id==user.workspace_id,Policy.policy_code==p.policy_code,Policy.status=='ACTIVE').all()
    for old in active: old.status='SUPERSEDED'
    p.status='ACTIVE';p.activated_by=user.email;p.activated_at=utcnow_naive();db.commit();return _policy_dict(db,p)


@router.get('/policies/{policy_code}/history')
def policy_history(policy_code:str,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(Policy).filter(Policy.workspace_id==user.workspace_id,Policy.policy_code==policy_code.upper()).order_by(Policy.id).all()
    return [_policy_dict(db,x) for x in rows]


@router.get('/policies/{policy_id}/impact')
def policy_impact(policy_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    p=db.query(Policy).filter(Policy.id==policy_id,Policy.workspace_id==user.workspace_id).first()
    if not p: raise HTTPException(404,'Policy not found')
    calcs=db.query(Calculation).filter(Calculation.policy_id==p.id).all()
    return {'policy_id':p.id,'policy_code':p.policy_code,'version':p.version,'calculation_count':len(calcs),'calculation_codes':[c.calculation_code for c in calcs[:100]],'historic_integrity':'Existing calculations retain policy_id and manifest policy version; activation never rewrites them.'}




@router.get('/pnl/runs/{run_id}/cube')
def pnl_cube(run_id:int,dimensions:str='entity,segment,transaction,currency',user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    run=db.query(PnLRun).filter(PnLRun.id==run_id,PnLRun.workspace_id==user.workspace_id).first()
    if not run: raise HTTPException(404,'P&L run not found')
    allowed={'entity','segment','transaction','partner','profit_center','product_group','sku','currency','gl_account'}
    dims=[x.strip().lower() for x in dimensions.split(',') if x.strip()]
    if not dims or any(x not in allowed for x in dims): raise HTTPException(422,f'Dimensions must be drawn from {sorted(allowed)}')
    import_ids=set(run.source_import_ids or [])
    q=(db.query(NormalizedFinancialRecord,RawFinancialRecord)
       .join(RawFinancialRecord,RawFinancialRecord.id==NormalizedFinancialRecord.raw_record_id)
       .filter(NormalizedFinancialRecord.workspace_id==user.workspace_id))
    if import_ids:q=q.filter(RawFinancialRecord.source_import_id.in_(import_ids))
    buckets={}
    entity_cache={}
    def entity_code(eid):
        if eid not in entity_cache:
            e=db.get(Entity,eid);entity_cache[eid]=e.entity_code if e else str(eid)
        return entity_cache[eid]
    for n,r in q.all():
        vals={'entity':entity_code(n.entity_id),'segment':n.segment_code,'transaction':n.controlled_transaction_code,
              'partner':n.counterparty_code,'profit_center':n.profit_center,'product_group':n.product_group,'sku':n.product_sku,
              'currency':n.currency,'gl_account':n.gl_account}
        key=tuple(vals[d] for d in dims);b=buckets.setdefault(key,{'revenue':Decimal('0'),'cogs':Decimal('0'),'direct_opex':Decimal('0'),'allocated_opex':Decimal('0'),'rows':0})
        b['rows']+=1
        if n.financial_classification=='REVENUE':b['revenue']+=D(n.amount)
        elif n.financial_classification=='COGS':b['cogs']+=abs(D(n.amount))
        elif n.financial_classification=='OPEX':b['direct_opex']+=abs(D(n.amount))
    allocation_precise=set(dims).issubset({'entity','segment','transaction','currency'}) and 'segment' in dims
    if allocation_precise:
        for seg in db.query(PnLSegmentResult).filter(PnLSegmentResult.pnl_run_id==run.id).all():
            vals={'entity':entity_code(seg.entity_id),'segment':seg.segment_code,'transaction':seg.controlled_transaction_code,'currency':seg.currency}
            key=tuple(vals[d] for d in dims);b=buckets.setdefault(key,{'revenue':Decimal('0'),'cogs':Decimal('0'),'direct_opex':Decimal('0'),'allocated_opex':Decimal('0'),'rows':0})
            b['allocated_opex']+=D(seg.allocated_opex)
    out=[]
    for key,b in buckets.items():
        row={d:key[i] for i,d in enumerate(dims)};revenue=money(b['revenue']);cogs=money(b['cogs']);direct=money(b['direct_opex']);alloc=money(b['allocated_opex']);gross=money(revenue-cogs);ebit=money(gross-direct-alloc);pli=Decimal('0') if revenue==0 else (ebit/revenue)
        row.update({'source_rows':b['rows'],'revenue':float(revenue),'cogs':float(cogs),'direct_opex':float(direct),'allocated_opex':float(alloc),'gross_profit':float(gross),'ebit':float(ebit),'ros':float(pli)})
        out.append(row)
    return {'run_id':run.id,'run_code':run.run_code,'dimensions':dims,'allocation_precision':'FULL' if allocation_precise else 'SEGMENT_ONLY_NOT_DISTRIBUTED_BELOW_SEGMENT','rows':out,'source_hash':run.source_hash}


class SnapshotIn(BaseModel):
    scenario:str='ACTUAL';label:str|None=None;comment:str|None=None;dimensions:dict[str,Any]=Field(default_factory=dict)


@router.post('/pnl/runs/{run_id}/snapshots')
def create_snapshot(run_id:int,body:SnapshotIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    run=db.query(PnLRun).filter(PnLRun.id==run_id,PnLRun.workspace_id==user.workspace_id).first()
    if not run: raise HTTPException(404,'P&L run not found')
    row=PnLSnapshot(workspace_id=user.workspace_id,snapshot_code=f'SNAP-{uuid.uuid4().hex[:10].upper()}',pnl_run_id=run.id,scenario=body.scenario.upper(),label=body.label,status='OPEN',dimensions=body.dimensions,comment=body.comment)
    db.add(row);db.flush();audit(db,event_type='PNL_SNAPSHOT_CREATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,object_type='pnl_snapshot',object_id=row.snapshot_code,new={'run_code':run.run_code,'scenario':row.scenario},details='Immutable-addressable P&L snapshot created');db.commit();return {'id':row.id,'snapshot_code':row.snapshot_code,'status':row.status,'scenario':row.scenario,'pnl_run_id':run.id}


@router.post('/pnl/snapshots/{snapshot_id}/lock')
def lock_snapshot(snapshot_id:int,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    row=db.query(PnLSnapshot).filter(PnLSnapshot.id==snapshot_id,PnLSnapshot.workspace_id==user.workspace_id).with_for_update().first()
    if not row: raise HTTPException(404,'Snapshot not found')
    if row.status=='LOCKED': return {'id':row.id,'status':row.status,'locked_by':row.locked_by}
    row.status='LOCKED';row.locked_by=user.email;row.locked_at=utcnow_naive();db.commit();return {'id':row.id,'status':row.status,'locked_by':row.locked_by,'locked_at':row.locked_at.isoformat()}


@router.get('/pnl/snapshots')
def list_snapshots(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(PnLSnapshot).filter(PnLSnapshot.workspace_id==user.workspace_id).order_by(PnLSnapshot.id.desc()).all()
    return [{'id':x.id,'snapshot_code':x.snapshot_code,'pnl_run_id':x.pnl_run_id,'scenario':x.scenario,'label':x.label,'status':x.status,'dimensions':x.dimensions,'locked_by':x.locked_by,'locked_at':x.locked_at.isoformat() if x.locked_at else None} for x in rows]



@router.get('/calculations')
def calculations(entity_code:str|None=None,limit:int=200,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(Calculation).filter(Calculation.workspace_id==user.workspace_id)
    if entity_code:
        e=_entity(db,user.workspace_id,entity_code);require_entity_access(db,user,e);q=q.filter(Calculation.entity_id==e.id)
    out=[]
    for c in q.order_by(Calculation.id.desc()).limit(min(limit,500)).all():
        e=db.get(Entity,c.entity_id);p=db.get(Policy,c.policy_id)
        try:require_entity_access(db,user,e)
        except HTTPException:continue
        out.append({'id':c.id,'calculation_code':c.calculation_code,'entity_code':e.entity_code,'period':c.period,'policy_code':p.policy_code if p else None,'policy_version':p.version if p else None,'revenue':float(c.revenue),'ebit':float(c.ebit),'actual_pli':float(c.actual_pli),'target_pli':float(c.target_pli),'suggested_adjustment':float(c.suggested_adjustment),'engine_version':c.engine_version,'source_hash':c.source_hash,'finalized':c.finalized})
    return out


class TrueUpIn(BaseModel):
    calculation_id:int
    target_type:str='POLICY_TARGET'
    custom_target:float|None=None
    frequency:str='QUARTERLY'
    batch_code:str|None=None
    reason:str|None=None


def _resolve_target(db:Session,p:Policy,target_type:str,custom:float|None)->Decimal:
    t=target_type.upper()
    if t=='POLICY_TARGET': return D(p.target)
    if t=='CUSTOM':
        if custom is None: raise HTTPException(422,'custom_target is required')
        return D(custom)
    if t in {'Q1','MEDIAN','Q3'}:
        if not p.benchmark_id: raise HTTPException(409,'Policy has no benchmark')
        bm=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==p.workspace_id,MasterDataRecord.domain=='BENCHMARKS',MasterDataRecord.record_code==p.benchmark_id).first()
        if not bm: raise HTTPException(409,'Benchmark not found')
        v=(bm.attributes or {}).get(t.lower())
        if v is None: raise HTTPException(409,f'Benchmark does not contain {t}')
        return D(v)
    raise HTTPException(422,'target_type must be POLICY_TARGET, Q1, MEDIAN, Q3 or CUSTOM')


def _compute_adjustment(db:Session,calc:Calculation,p:Policy,target:Decimal)->Decimal:
    fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==calc.entity_id,FinancialPeriod.period==calc.period).first()
    if p.method.upper()=='TNMM' and p.pli.upper()=='ROS': return money(target*D(calc.revenue)-D(calc.ebit))
    if not fp: return money(calc.suggested_adjustment)
    res=calculate_policy_result(p.method,p.pli,revenue=fp.revenue,cogs=fp.cogs,opex=fp.opex,target=target,lower=p.lower_bound or 0,upper=p.upper_bound or 0,eligible_costs=(D(fp.cogs)+D(fp.opex) if p.method.upper()=='COST_PLUS' else None))
    return money(res.adjustment)



def _active_policy_for_calc(db:Session,calc:Calculation):
    linked=db.get(Policy,calc.policy_id)
    q=db.query(Policy).filter(Policy.workspace_id==calc.workspace_id,Policy.entity_id==calc.entity_id,Policy.status=='ACTIVE')
    if linked: q=q.filter(Policy.policy_code==linked.policy_code,Policy.method==linked.method,Policy.pli==linked.pli)
    rows=q.order_by(Policy.id.desc()).all()
    for p in rows:
        if p.effective_from and calc.period < p.effective_from[:7]: continue
        if p.effective_to and calc.period > p.effective_to[:7]: continue
        return p
    return rows[0] if rows else None

def _true_up_preview(db:Session,calc:Calculation,target_type:str,custom_target:float|None):
    linked=db.get(Policy,calc.policy_id)
    if not linked: raise HTTPException(409,'Calculation policy not found')
    active=_active_policy_for_calc(db,calc) or linked
    target=_resolve_target(db,active,target_type,custom_target)
    amount=_compute_adjustment(db,calc,active,target)
    e=db.get(Entity,calc.entity_id)
    consistency=True
    if target_type.upper()=='POLICY_TARGET' and linked.id!=active.id:
        consistency=abs(float(linked.target)-float(active.target))<1e-9
    return {'calculation_id':calc.id,'calculation_code':calc.calculation_code,'entity_code':e.entity_code if e else None,'period':calc.period,'actual_pli':float(calc.actual_pli),'revenue':float(calc.revenue),'ebit':float(calc.ebit),'target_type':target_type.upper(),'target_value':float(target),'adjustment_amount':float(amount),'currency':active.currency or (e.currency if e else 'EUR'),'policy':{'id':active.id,'policy_code':active.policy_code,'version':active.version,'status':active.status,'method':active.method,'pli':active.pli,'target':float(active.target),'benchmark_id':active.benchmark_id,'effective_from':active.effective_from,'effective_to':active.effective_to},'calculation_policy':{'id':linked.id,'policy_code':linked.policy_code,'version':linked.version,'target':float(linked.target)},'policy_consistent':consistency,'source_hash':calc.source_hash,'formula':'target × revenue − EBIT' if active.method.upper()=='TNMM' and active.pli.upper()=='ROS' else 'governed policy engine'}

class TrueUpPreviewIn(BaseModel):
    calculation_id:int
    target_type:str='POLICY_TARGET'
    custom_target:float|None=None

@router.post('/true-ups/preview')
def preview_true_up(body:TrueUpPreviewIn,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    calc=db.query(Calculation).filter(Calculation.id==body.calculation_id,Calculation.workspace_id==user.workspace_id).first()
    if not calc: raise HTTPException(404,'Calculation not found')
    e=db.get(Entity,calc.entity_id);require_entity_access(db,user,e)
    return _true_up_preview(db,calc,body.target_type,body.custom_target)

@router.post('/true-ups')
def create_true_up(body:TrueUpIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    calc=db.query(Calculation).filter(Calculation.id==body.calculation_id,Calculation.workspace_id==user.workspace_id).first()
    if not calc: raise HTTPException(404,'Calculation not found')
    e=db.get(Entity,calc.entity_id);require_entity_access(db,user,e,write=True)
    preview=_true_up_preview(db,calc,body.target_type,body.custom_target)
    if not preview['policy_consistent']:
        raise HTTPException(409,f"Policy mismatch: calculation is pinned to {preview['calculation_policy']['policy_code']} v{preview['calculation_policy']['version']} target {preview['calculation_policy']['target']}, while applicable active policy is {preview['policy']['policy_code']} v{preview['policy']['version']} target {preview['policy']['target']}")
    p=db.get(Policy,preview['policy']['id']);target=D(preview['target_value']);amount=money(D(preview['adjustment_amount']))
    duplicate=db.query(Adjustment).filter(Adjustment.workspace_id==user.workspace_id,Adjustment.calculation_id==calc.id,Adjustment.entity_id==e.id,Adjustment.target_type==body.target_type.upper(),Adjustment.target_value==target,Adjustment.frequency==body.frequency.upper(),Adjustment.amount==amount,Adjustment.status.in_(['PROPOSED','SUBMITTED','IN_REVIEW','APPROVED'])).first()
    if duplicate: raise HTTPException(409,f'Duplicate true-up proposal exists: {duplicate.adjustment_code} ({duplicate.status})')
    row=Adjustment(workspace_id=user.workspace_id,adjustment_code=f'TU-{e.entity_code}-{calc.period}-{uuid.uuid4().hex[:7].upper()}',calculation_id=calc.id,entity_id=e.id,amount=amount,currency=p.currency or e.currency,status='PROPOSED',version=1,materiality=p.materiality_threshold or 0,adjustment_type='TRUE_UP',batch_code=body.batch_code,target_type=body.target_type.upper(),target_value=target,frequency=body.frequency.upper(),rounding_mode='ROUND_HALF_UP',reason=body.reason)
    db.add(row);db.flush();audit(db,event_type='TRUE_UP_CREATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='adjustment',object_id=row.adjustment_code,new={'target_type':row.target_type,'target_value':float(target),'amount':float(amount),'frequency':row.frequency,'policy_version':p.version},details='Deterministic true-up proposal created');db.commit();return {'id':row.id,'adjustment_code':row.adjustment_code,'amount':float(row.amount),'currency':row.currency,'status':row.status,'target_type':row.target_type,'target_value':float(row.target_value),'frequency':row.frequency,'batch_code':row.batch_code}


class TrueUpBatchIn(BaseModel):
    calculation_ids:list[int]
    target_type:str='POLICY_TARGET'
    custom_target:float|None=None
    frequency:str='QUARTERLY'


@router.post('/true-ups/batch')
def create_true_up_batch(body:TrueUpBatchIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    code=f'TUB-{uuid.uuid4().hex[:10].upper()}';out=[]
    for cid in body.calculation_ids:
        out.append(create_true_up(TrueUpIn(calculation_id=cid,target_type=body.target_type,custom_target=body.custom_target,frequency=body.frequency,batch_code=code),user,db))
    return {'batch_code':code,'count':len(out),'items':out}


class ReversalIn(BaseModel): reason:str


@router.post('/true-ups/{adjustment_id}/reverse')
def reverse_true_up(adjustment_id:int,body:ReversalIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    old=db.query(Adjustment).filter(Adjustment.id==adjustment_id,Adjustment.workspace_id==user.workspace_id).first()
    if not old: raise HTTPException(404,'True-up not found')
    if old.status not in {'APPROVED','LOCKED'}: raise HTTPException(409,'Only approved/locked true-ups can be reversed')
    if db.query(Adjustment).filter(Adjustment.original_adjustment_id==old.id,Adjustment.adjustment_type=='REVERSAL').first(): raise HTTPException(409,'True-up already has a reversal')
    e=db.get(Entity,old.entity_id);require_entity_access(db,user,e,write=True)
    row=Adjustment(workspace_id=user.workspace_id,adjustment_code=f'REV-{old.adjustment_code}-{uuid.uuid4().hex[:5].upper()}',calculation_id=old.calculation_id,entity_id=old.entity_id,amount=money(-D(old.amount)),currency=old.currency,status='PROPOSED',version=1,materiality=old.materiality,adjustment_type='REVERSAL',original_adjustment_id=old.id,batch_code=old.batch_code,target_type=old.target_type,target_value=old.target_value,frequency=old.frequency,rounding_mode=old.rounding_mode,reason=body.reason)
    db.add(row);old.status='REVERSED';db.commit();return {'id':row.id,'adjustment_code':row.adjustment_code,'amount':float(row.amount),'status':row.status,'reverses':old.adjustment_code}


class WorkflowStartIn(BaseModel):
    workflow_code:str
    object_type:str
    object_id:str
    amount:float=0
    materiality:float=0
    entity_code:str|None=None
    country:str|None=None
    method:str|None=None
    risk:str|None=None


@router.post('/workflow-engine/instances')
def start_workflow(body:WorkflowStartIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    wf=resolve_workflow(db,user.workspace_id,workflow_code=body.workflow_code,object_type=body.object_type,amount=body.amount,materiality=body.materiality,entity_code=body.entity_code,country=body.country,method=body.method,risk=body.risk)
    if not wf: raise HTTPException(409,'No active workflow definition matches the supplied context')
    row=WorkflowInstance(workspace_id=user.workspace_id,instance_code=f'WFI-{uuid.uuid4().hex[:10].upper()}',workflow_code=wf['code'],workflow_version=wf['version'],object_type=body.object_type.upper(),object_id=body.object_id,approval_mode=wf['approval_mode'],status='PENDING',created_by=user.email,context=body.model_dump())
    db.add(row);db.flush();sla=int(wf.get('sla_hours') or 72);due=utcnow_naive()+timedelta(hours=sla)
    for idx,group in enumerate(wf['groups'],1):
        for role in group:
            db.add(WorkflowTask(workflow_instance_id=row.id,step_order=idx,group_no=idx,required_role=role,status='PENDING',due_at=due))
    db.commit();return _workflow_instance(db,row)


def _workflow_instance(db:Session,row:WorkflowInstance)->dict:
    tasks=db.query(WorkflowTask).filter(WorkflowTask.workflow_instance_id==row.id).order_by(WorkflowTask.step_order,WorkflowTask.id).all()
    return {'id':row.id,'instance_code':row.instance_code,'workflow_code':row.workflow_code,'workflow_version':row.workflow_version,'object_type':row.object_type,'object_id':row.object_id,'approval_mode':row.approval_mode,'status':row.status,'created_by':row.created_by,'context':row.context,'tasks':[{'id':t.id,'step_order':t.step_order,'required_role':t.required_role,'status':t.status,'actor':t.actor,'delegated_from':t.delegated_from,'due_at':t.due_at.isoformat() if t.due_at else None,'comments':t.comments} for t in tasks]}


@router.get('/workflow-engine/instances')
def workflow_instances(status:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    q=db.query(WorkflowInstance).filter(WorkflowInstance.workspace_id==user.workspace_id)
    if status:q=q.filter(WorkflowInstance.status==status.upper())
    return [_workflow_instance(db,x) for x in q.order_by(WorkflowInstance.id.desc()).limit(200).all()]


@router.get('/workflow-engine/inbox')
def workflow_inbox(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    now=utcnow_naive();delegated_roles=[]
    dels=db.query(UserDelegation).filter(UserDelegation.workspace_id==user.workspace_id,UserDelegation.to_user==user.email,UserDelegation.active.is_(True),UserDelegation.effective_from<=now,UserDelegation.effective_to>=now).all()
    delegated_roles=[x.role for x in dels if x.role]
    tasks=db.query(WorkflowTask,WorkflowInstance).join(WorkflowInstance,WorkflowInstance.id==WorkflowTask.workflow_instance_id).filter(WorkflowInstance.workspace_id==user.workspace_id,WorkflowInstance.status=='PENDING',WorkflowTask.status=='PENDING').all()
    out=[]
    for t,i in tasks:
        if user.role not in {'PLATFORM_ADMIN',t.required_role} and t.required_role not in delegated_roles: continue
        out.append({'task_id':t.id,'instance_code':i.instance_code,'object_type':i.object_type,'object_id':i.object_id,'step_order':t.step_order,'required_role':t.required_role,'due_at':t.due_at.isoformat() if t.due_at else None,'overdue':bool(t.due_at and t.due_at<now)})
    return out


class WorkflowDecisionIn(BaseModel): comments:str|None=None


def _current_step(db:Session,row:WorkflowInstance)->int|None:
    pending=db.query(WorkflowTask).filter(WorkflowTask.workflow_instance_id==row.id,WorkflowTask.status=='PENDING').order_by(WorkflowTask.step_order).first()
    return pending.step_order if pending else None


@router.post('/workflow-engine/tasks/{task_id}/approve')
def approve_workflow_task(task_id:int,body:WorkflowDecisionIn|None=None,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    task=db.get(WorkflowTask,task_id)
    if not task: raise HTTPException(404,'Workflow task not found')
    inst=db.query(WorkflowInstance).filter(WorkflowInstance.id==task.workflow_instance_id,WorkflowInstance.workspace_id==user.workspace_id).with_for_update().first()
    if not inst or inst.status!='PENDING': raise HTTPException(409,'Workflow is not pending')
    if inst.created_by==user.email: raise HTTPException(409,'Maker-checker: workflow creator cannot approve own object')
    current=_current_step(db,inst)
    if current is None or task.step_order!=current: raise HTTPException(409,'Task is not in the current approval step')
    if user.role not in {'PLATFORM_ADMIN',task.required_role}:
        now=utcnow_naive();deleg=db.query(UserDelegation).filter(UserDelegation.workspace_id==user.workspace_id,UserDelegation.to_user==user.email,UserDelegation.role==task.required_role,UserDelegation.active.is_(True),UserDelegation.effective_from<=now,UserDelegation.effective_to>=now).first()
        if not deleg: raise HTTPException(403,f'Task requires role {task.required_role}')
        task.delegated_from=deleg.from_user
    task.status='APPROVED';task.actor=user.email;task.comments=body.comments if body else None;task.decided_at=utcnow_naive();db.flush()
    group_remaining=db.query(WorkflowTask).filter(WorkflowTask.workflow_instance_id==inst.id,WorkflowTask.step_order==current,WorkflowTask.status=='PENDING').count()
    if group_remaining==0:
        next_task=db.query(WorkflowTask).filter(WorkflowTask.workflow_instance_id==inst.id,WorkflowTask.status=='PENDING').order_by(WorkflowTask.step_order).first()
        if not next_task: inst.status='APPROVED';inst.completed_at=utcnow_naive()
    db.commit();return _workflow_instance(db,inst)


@router.post('/workflow-engine/tasks/{task_id}/reject')
def reject_workflow_task(task_id:int,body:WorkflowDecisionIn,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    task=db.get(WorkflowTask,task_id)
    if not task: raise HTTPException(404,'Workflow task not found')
    inst=db.query(WorkflowInstance).filter(WorkflowInstance.id==task.workflow_instance_id,WorkflowInstance.workspace_id==user.workspace_id).with_for_update().first()
    if not inst or inst.status!='PENDING': raise HTTPException(409,'Workflow is not pending')
    if user.role not in {'PLATFORM_ADMIN',task.required_role}: raise HTTPException(403,f'Task requires role {task.required_role}')
    task.status='REJECTED';task.actor=user.email;task.comments=body.comments;task.decided_at=utcnow_naive();inst.status='REJECTED';inst.completed_at=utcnow_naive();db.commit();return _workflow_instance(db,inst)


@router.post('/workflow-engine/tasks/{task_id}/return')
def return_workflow_task(task_id:int,body:WorkflowDecisionIn,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    task=db.get(WorkflowTask,task_id)
    if not task: raise HTTPException(404,'Workflow task not found')
    inst=db.query(WorkflowInstance).filter(WorkflowInstance.id==task.workflow_instance_id,WorkflowInstance.workspace_id==user.workspace_id).with_for_update().first()
    if not inst or inst.status!='PENDING': raise HTTPException(409,'Workflow is not pending')
    if user.role not in {'PLATFORM_ADMIN',task.required_role}: raise HTTPException(403,f'Task requires role {task.required_role}')
    if not body.comments: raise HTTPException(422,'Return comments are required')
    task.status='RETURNED';task.actor=user.email;task.comments=body.comments;task.decided_at=utcnow_naive();inst.status='RETURNED';inst.completed_at=None
    db.commit();return _workflow_instance(db,inst)


@router.post('/workflow-engine/instances/{instance_id}/withdraw')
def withdraw_workflow_instance(instance_id:int,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    inst=db.query(WorkflowInstance).filter(WorkflowInstance.id==instance_id,WorkflowInstance.workspace_id==user.workspace_id).with_for_update().first()
    if not inst: raise HTTPException(404,'Workflow instance not found')
    if inst.created_by!=user.email and user.role!='PLATFORM_ADMIN': raise HTTPException(403,'Only the workflow creator or platform administrator may withdraw it')
    if inst.status not in {'PENDING','RETURNED'}: raise HTTPException(409,'Only pending/returned workflows may be withdrawn')
    inst.status='WITHDRAWN';inst.completed_at=utcnow_naive()
    db.query(WorkflowTask).filter(WorkflowTask.workflow_instance_id==inst.id,WorkflowTask.status=='PENDING').update({'status':'CANCELLED'},synchronize_session=False)
    db.commit();return _workflow_instance(db,inst)


@router.post('/workflow-engine/instances/{instance_id}/resubmit')
def resubmit_workflow_instance(instance_id:int,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    inst=db.query(WorkflowInstance).filter(WorkflowInstance.id==instance_id,WorkflowInstance.workspace_id==user.workspace_id).with_for_update().first()
    if not inst: raise HTTPException(404,'Workflow instance not found')
    if inst.created_by!=user.email and user.role!='PLATFORM_ADMIN': raise HTTPException(403,'Only the workflow creator or platform administrator may resubmit it')
    if inst.status not in {'RETURNED','REJECTED','WITHDRAWN'}: raise HTTPException(409,'Workflow is not in a resubmittable state')
    wf=resolve_workflow(db,user.workspace_id,workflow_code=inst.workflow_code,object_type=inst.object_type,amount=float((inst.context or {}).get('amount') or 0),materiality=float((inst.context or {}).get('materiality') or 0),entity_code=(inst.context or {}).get('entity_code'),country=(inst.context or {}).get('country'),method=(inst.context or {}).get('method'),risk=(inst.context or {}).get('risk'))
    if not wf or int(wf['version'])!=int(inst.workflow_version):
        # In-flight/resubmitted instances retain their pinned definition. Existing tasks are reset rather than silently switching versions.
        tasks=db.query(WorkflowTask).filter(WorkflowTask.workflow_instance_id==inst.id).all()
        if not tasks: raise HTTPException(409,'Pinned workflow definition/tasks are unavailable')
    now=utcnow_naive();sla=int((wf or {}).get('sla_hours') or 72)
    for t in db.query(WorkflowTask).filter(WorkflowTask.workflow_instance_id==inst.id).all():
        t.status='PENDING';t.actor=None;t.delegated_from=None;t.comments=None;t.decided_at=None;t.due_at=now+timedelta(hours=sla)
    inst.status='PENDING';inst.completed_at=None
    db.commit();return _workflow_instance(db,inst)


@router.post('/workflow-engine/escalate-overdue')
def escalate_overdue_workflows(user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    now=utcnow_naive();rows=db.query(WorkflowTask,WorkflowInstance).join(WorkflowInstance,WorkflowInstance.id==WorkflowTask.workflow_instance_id).filter(WorkflowInstance.workspace_id==user.workspace_id,WorkflowInstance.status=='PENDING',WorkflowTask.status=='PENDING',WorkflowTask.due_at.is_not(None),WorkflowTask.due_at<now).all();out=[]
    for task,inst in rows:
        wf=resolve_workflow(db,user.workspace_id,workflow_code=inst.workflow_code,object_type=inst.object_type,amount=float((inst.context or {}).get('amount') or 0),materiality=float((inst.context or {}).get('materiality') or 0),entity_code=(inst.context or {}).get('entity_code'),country=(inst.context or {}).get('country'),method=(inst.context or {}).get('method'),risk=(inst.context or {}).get('risk'))
        escalation=(wf or {}).get('escalation_role')
        if escalation and task.required_role!=escalation:
            previous=task.required_role;task.required_role=escalation;task.comments=((task.comments+'\n') if task.comments else '')+f'Auto-escalated from {previous} at {now.isoformat()}'
            out.append({'task_id':task.id,'instance_code':inst.instance_code,'from_role':previous,'to_role':escalation})
    db.commit();return {'escalated':len(out),'tasks':out}


class DelegationIn(BaseModel):
    to_user:str;role:str|None=None;effective_from:datetime;effective_to:datetime


@router.post('/workflow-engine/delegations')
def create_delegation(body:DelegationIn,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    if body.effective_to<=body.effective_from: raise HTTPException(422,'effective_to must be after effective_from')
    row=UserDelegation(workspace_id=user.workspace_id,from_user=user.email,to_user=body.to_user.lower(),role=body.role.upper() if body.role else user.role,effective_from=body.effective_from,effective_to=body.effective_to,active=True)
    db.add(row);db.commit();return {'id':row.id,'from_user':row.from_user,'to_user':row.to_user,'role':row.role,'active':row.active}


@router.post('/reconciliations/{reconciliation_id}/stages/rebuild')
def rebuild_reconciliation_stages(reconciliation_id:int,user:User=Depends(require_permission('journal')),db:Session=Depends(get_db)):
    r=db.query(Reconciliation).filter(Reconciliation.id==reconciliation_id,Reconciliation.workspace_id==user.workspace_id).first()
    if not r: raise HTTPException(404,'Reconciliation not found')
    db.query(ReconciliationStage).filter(ReconciliationStage.reconciliation_id==r.id).delete()
    tol=D(r.tolerance);vals=[
        ('APPROVED_TO_JOURNAL',D(r.approved_amount or r.expected_amount),D(r.journal_amount or 0)),
        ('JOURNAL_TO_POSTING',D(r.journal_amount or 0),D(r.posted_amount)),
        ('POSTING_TO_FINAL_PNL',D(r.posted_amount),D(r.final_pnl_impact if r.final_pnl_impact is not None else r.posted_amount)),
    ]
    out=[]
    for i,(code,src,tgt) in enumerate(vals,1):
        diff=money(tgt-src);status='RECONCILED' if abs(diff)<=tol else 'DIFFERENCE'
        s=ReconciliationStage(reconciliation_id=r.id,stage_order=i,stage_code=code,source_amount=src,target_amount=tgt,difference=diff,tolerance=tol,status=status,linked_records={'adjustment_id':r.adjustment_id});db.add(s);out.append({'stage':code,'source_amount':float(src),'target_amount':float(tgt),'difference':float(diff),'status':status})
    db.flush()
    bad=[x for x in out if x['status']=='DIFFERENCE']
    r.status='RECONCILED' if not bad else 'DIFFERENCE'
    if bad and not r.exception_code:
        a=db.get(Adjustment,r.adjustment_id);e=db.get(Entity,a.entity_id) if a else None;code=f'EXC-REC-{r.id}-{uuid.uuid4().hex[:5].upper()}'
        exc=ExceptionCase(workspace_id=user.workspace_id,exception_code=code,entity_id=e.id if e else None,category='RECONCILIATION',severity='HIGH',amount=max(abs(D(x['difference'])) for x in bad),owner='finance@otp.local',status='OPEN',source='RECONCILIATION',currency=r.currency or (e.currency if e else None),evidence={'reconciliation_id':r.id,'stages':bad});db.add(exc);r.exception_code=code
    db.commit();return {'reconciliation_id':r.id,'status':r.status,'tolerance':float(tol),'stages':out,'exception_code':r.exception_code}


@router.get('/reconciliations/{reconciliation_id}/stages')
def reconciliation_stages(reconciliation_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    r=db.query(Reconciliation).filter(Reconciliation.id==reconciliation_id,Reconciliation.workspace_id==user.workspace_id).first()
    if not r: raise HTTPException(404,'Reconciliation not found')
    rows=db.query(ReconciliationStage).filter(ReconciliationStage.reconciliation_id==r.id).order_by(ReconciliationStage.stage_order).all()
    return [{'stage_order':x.stage_order,'stage_code':x.stage_code,'source_amount':float(x.source_amount),'target_amount':float(x.target_amount),'difference':float(x.difference),'tolerance':float(x.tolerance),'status':x.status,'reason':x.reason,'linked_records':x.linked_records} for x in rows]


class ExceptionActionIn(BaseModel):
    root_cause:str|None=None;remediation:str|None=None;comment:str|None=None;attachment:str|None=None;waiver_reason:str|None=None


@router.post('/exceptions/{exception_id}/triage')
def triage_exception(exception_id:int,body:ExceptionActionIn,user:User=Depends(require_permission('write')),db:Session=Depends(get_db)):
    x=db.query(ExceptionCase).filter(ExceptionCase.id==exception_id,ExceptionCase.workspace_id==user.workspace_id).first()
    if not x: raise HTTPException(404,'Exception not found')
    x.status='IN_PROGRESS';x.root_cause=body.root_cause or x.root_cause;x.remediation=body.remediation or x.remediation
    comments=list(x.comments or []);
    if body.comment:comments.append({'at':utcnow_naive().isoformat(),'user':user.email,'text':body.comment})
    x.comments=comments;atts=list(x.attachments or []);
    if body.attachment:atts.append(body.attachment)
    x.attachments=atts;db.commit();return {'id':x.id,'status':x.status,'root_cause':x.root_cause,'remediation':x.remediation,'comments':x.comments,'attachments':x.attachments}


@router.post('/exceptions/{exception_id}/waive')
def waive_exception(exception_id:int,body:ExceptionActionIn,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    x=db.query(ExceptionCase).filter(ExceptionCase.id==exception_id,ExceptionCase.workspace_id==user.workspace_id).first()
    if not x: raise HTTPException(404,'Exception not found')
    if not body.waiver_reason: raise HTTPException(422,'waiver_reason is required')
    x.status='WAIVED';x.waived_by=user.email;x.waiver_reason=body.waiver_reason;x.closed_at=utcnow_naive();db.commit();return {'id':x.id,'status':x.status,'waived_by':x.waived_by,'waiver_reason':x.waiver_reason}


class ServiceAccountIn(BaseModel):
    account_code:str;permissions:list[str];entity_codes:list[str]=Field(default_factory=list);expires_at:datetime|None=None


@router.post('/security/service-accounts')
def create_service_account(body:ServiceAccountIn,user:User=Depends(require_permission('service_account_admin')),db:Session=Depends(get_db)):
    code=body.account_code.upper()
    if db.query(ServiceAccount).filter(ServiceAccount.workspace_id==user.workspace_id,ServiceAccount.account_code==code).first(): raise HTTPException(409,'Service account already exists')
    raw='otp_sa_'+secrets.token_urlsafe(32);digest=hashlib.sha256(raw.encode()).hexdigest()
    row=ServiceAccount(workspace_id=user.workspace_id,account_code=code,token_hash=digest,permissions=body.permissions,entity_codes=[x.upper() for x in body.entity_codes],active=True,expires_at=body.expires_at,created_by=user.email);db.add(row);db.commit()
    return {'id':row.id,'account_code':row.account_code,'token':raw,'permissions':row.permissions,'entity_codes':row.entity_codes,'expires_at':row.expires_at.isoformat() if row.expires_at else None,'warning':'Token is shown once. Store it in a secure external secret manager.'}


@router.get('/security/service-accounts')
def list_service_accounts(user:User=Depends(require_permission('service_account_admin')),db:Session=Depends(get_db)):
    rows=db.query(ServiceAccount).filter(ServiceAccount.workspace_id==user.workspace_id).order_by(ServiceAccount.account_code).all()
    return [{'id':x.id,'account_code':x.account_code,'permissions':x.permissions,'entity_codes':x.entity_codes,'active':x.active,'expires_at':x.expires_at.isoformat() if x.expires_at else None,'created_by':x.created_by} for x in rows]


@router.post('/security/service-accounts/{account_id}/revoke')
def revoke_service_account(account_id:int,user:User=Depends(require_permission('service_account_admin')),db:Session=Depends(get_db)):
    row=db.query(ServiceAccount).filter(ServiceAccount.id==account_id,ServiceAccount.workspace_id==user.workspace_id).first()
    if not row: raise HTTPException(404,'Service account not found')
    row.active=False;db.commit();return {'id':row.id,'active':row.active}


_REPORT_CONTROLS={
    'BACKEND_TESTS':('TESTING','TEST_REPORT.md'),
    'CODE_COVERAGE':('TESTING','COVERAGE_REPORT.md'),
    'FRONTEND_TESTS':('TESTING','FRONTEND_TEST_REPORT.md'),
    'MIGRATION_VALIDATION':('RELEASE','VALIDATION_REPORT.md'),
    'SECURITY_VALIDATION':('SECURITY','SECURITY_REPORT.md'),
    'RELEASE_INTEGRITY':('RELEASE','VALIDATION_REPORT.md'),
    'UAT':('UAT','UAT_RESULTS.md'),
    'LOCAL_10_10':('UAT','LOCAL_10_10_QUALIFICATION_RESULT.md'),
}


def _report_status(content:str, exists:bool)->str:
    if not exists:
        return 'NOT RUN'
    # Prefer a machine-readable marker generated by the validation harness.
    match=re.search(r'(?im)^\s*QUALIFICATION_STATUS\s*:\s*(PASS|FAIL|WARNING|NOT RUN)\s*$',content)
    if match:
        return match.group(1).upper()
    lowered=content.lower()
    # Conservative fallback: an explicitly unexecuted gate is never converted to PASS.
    if 'not run' in lowered or 'not executed' in lowered:
        return 'NOT RUN'
    if re.search(r'\b(fail|failed|failure)\b',lowered) and not re.search(r'\b0\s+failed\b',lowered):
        return 'FAIL'
    return 'PASS'


@router.post('/qualification/sync-release-evidence')
def sync_qualification_evidence(user:User=Depends(require_permission('admin_policy')),db:Session=Depends(get_db)):
    version=settings.app_version;base=Path('/release-docs')
    if not base.exists():
        # Developer/local fallback from backend working directory.
        candidate=Path(__file__).resolve().parents[3]/'docs';base=candidate if candidate.exists() else base
    results=[]
    for code,(category,filename) in _REPORT_CONTROLS.items():
        path=base/filename;exists=path.exists();content=path.read_text(errors='ignore')[:20000] if exists else ''
        status=_report_status(content,exists)
        row=db.query(QualificationEvidence).filter(QualificationEvidence.workspace_id==user.workspace_id,QualificationEvidence.release_version==version,QualificationEvidence.control_code==code).first()
        result={'exists':exists,'filename':filename,'sha256':hashlib.sha256(content.encode()).hexdigest() if exists else None}
        if not row:
            row=QualificationEvidence(workspace_id=user.workspace_id,release_version=version,control_code=code,category=category,status=status,environment=settings.environment,result=result,evidence_path=str(path) if exists else None,executed_by=user.email);db.add(row)
        else:
            row.status=status;row.result=result;row.evidence_path=str(path) if exists else None;row.executed_by=user.email
        control=db.query(QualificationControl).filter(QualificationControl.workspace_id==user.workspace_id,QualificationControl.control_code==code).first()
        if control and control.control_type in {'INTERNAL','AUTOMATED'}:
            control.status=status;control.evidence=result;control.reviewer=user.email;control.reviewed_at=utcnow_naive()
        results.append({'control_code':code,'status':status,'evidence':result})
    db.commit();return {'release_version':version,'evidence_root':str(base),'controls':results}


@router.get('/qualification/evidence')
def qualification_evidence(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    rows=db.query(QualificationEvidence).filter(QualificationEvidence.workspace_id==user.workspace_id).order_by(QualificationEvidence.release_version.desc(),QualificationEvidence.control_code).all()
    return [{'id':x.id,'release_version':x.release_version,'control_code':x.control_code,'category':x.category,'status':x.status,'environment':x.environment,'result':x.result,'evidence_path':x.evidence_path,'executed_by':x.executed_by,'created_at':x.created_at.isoformat()} for x in rows]



@router.get('/qualification/evidence/{evidence_id}/download')
def qualification_evidence_download(evidence_id:int,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    row=db.query(QualificationEvidence).filter(QualificationEvidence.id==evidence_id,QualificationEvidence.workspace_id==user.workspace_id).first()
    if not row or not row.evidence_path: raise HTTPException(404,'Qualification evidence not found')
    path=Path(row.evidence_path).resolve()
    allowed=[Path('/release-docs').resolve(),(Path(__file__).resolve().parents[3]/'docs').resolve()]
    if not any(path==a or a in path.parents for a in allowed): raise HTTPException(403,'Evidence path outside approved release roots')
    if not path.exists(): raise HTTPException(404,'Evidence artifact is not available in this runtime')
    return FileResponse(path,filename=f'{row.release_version}_{row.control_code}_{path.name}')

@router.get('/audit/transaction-chain/{entity_code}')
def audit_transaction_chain(entity_code:str,object_id:str|None=None,user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    e=_entity(db,user.workspace_id,entity_code);require_entity_access(db,user,e)
    q=db.query(AuditEvent).filter(AuditEvent.workspace_id==user.workspace_id,AuditEvent.entity_code==e.entity_code)
    if object_id:q=q.filter(AuditEvent.object_id==object_id)
    rows=q.order_by(AuditEvent.id).all()
    return {'entity_code':e.entity_code,'object_id':object_id,'event_count':len(rows),'events':[{'id':x.id,'event_type':x.event_type,'actor':x.actor,'actor_role':x.actor_role,'object_type':x.object_type,'object_id':x.object_id,'previous_value':x.previous_value,'new_value':x.new_value,'reason':x.reason,'request_id':x.request_id,'correlation_id':x.correlation_id,'created_at':x.created_at.isoformat()} for x in rows]}
