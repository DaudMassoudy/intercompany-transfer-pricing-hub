from app.timeutil import utcnow_naive
from datetime import date
from decimal import Decimal
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Adjustment, Calculation, Policy, Entity, JournalHeader, JournalLine, Posting, PostingAttempt, Reconciliation, MasterDataRecord, ExceptionCase
from ..security import require_permission, require_entity_access
from ..services.finance import money, D
from ..services.erp import SimulatedSAPConnector
from ..services.audit import audit

router=APIRouter(tags=['accounting-execution'])

@router.post('/journals/from-adjustment/{adjustment_id}')
def create_journal(adjustment_id:int,template_code:str|None=None,user:User=Depends(require_permission('journal')),db:Session=Depends(get_db)):
    a=db.query(Adjustment).filter(Adjustment.id==adjustment_id,Adjustment.workspace_id==user.workspace_id).with_for_update().first()
    if not a or a.status!='APPROVED': raise HTTPException(409,'Fully approved adjustment required')
    e=db.get(Entity,a.entity_id);require_entity_access(db,user,e)
    existing=db.query(JournalHeader).filter(JournalHeader.adjustment_id==a.id).first()
    if existing: return _journal_dict(db,existing)
    amount=money(abs(D(a.amount)))
    today=date.today().isoformat()
    tq=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==user.workspace_id,MasterDataRecord.domain=='JOURNAL_TEMPLATES',MasterDataRecord.active.is_(True))
    if template_code:
        tq=tq.filter(MasterDataRecord.record_code==template_code.upper())
    templates=tq.order_by(MasterDataRecord.version_no.desc()).all()
    template=None
    for candidate in templates:
        ca=candidate.attributes or {}
        if ca.get('company_code') and str(ca.get('company_code')).upper()!=e.company_code.upper():
            continue
        if ca.get('currency') and str(ca.get('currency')).upper()!=a.currency.upper():
            continue
        template=candidate;break
    if template_code and template is None: raise HTTPException(404,'Active journal template not found for company/currency')
    ta=template.attributes if template else {}
    ledger=str(ta.get('ledger') or '0L');document_type=str(ta.get('document_type') or 'TP')
    h=JournalHeader(workspace_id=user.workspace_id,journal_code=f'JRN-{a.adjustment_code}',adjustment_id=a.id,company_code=e.company_code,ledger=ledger,document_type=document_type,posting_date=today,document_date=today,currency=a.currency,reference=a.adjustment_code,status='PREPARED',template_code=template.record_code if template else None,template_version=template.version_no if template else None)
    db.add(h);db.flush()
    # Template-driven GL determination is primary. Legacy defaults remain only as a compatibility fallback when no governed template exists.
    if D(a.amount)>=0:
        debit_gl=str(ta.get('positive_debit_gl') or '140900');credit_gl=str(ta.get('positive_credit_gl') or '499900')
        debit_text='Intercompany TP receivable';credit_text=str(ta.get('positive_text') or 'Transfer pricing true-up income')
    else:
        debit_gl=str(ta.get('negative_debit_gl') or '699900');credit_gl=str(ta.get('negative_credit_gl') or '240900')
        debit_text=str(ta.get('negative_text') or 'Transfer pricing true-up expense');credit_text='Intercompany TP payable'
    partner=str(ta.get('trading_partner') or 'TP-NL01');pc=str(ta.get('profit_center_template') or '{entity_code}-CORE').replace('{entity_code}',e.entity_code)
    specs=[(1,debit_gl,'DEBIT',amount,debit_text),(2,credit_gl,'CREDIT',amount,credit_text)]
    for line_no,gl,dc,amt,line_text in specs:
        db.add(JournalLine(journal_id=h.id,line_no=line_no,gl_account=gl,debit_credit=dc,amount=amt,currency=a.currency,profit_center=pc,trading_partner=partner,assignment=a.adjustment_code,text=line_text,tax_code=ta.get('tax_code')))
    audit(db,event_type='JOURNAL_CREATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code,object_type='journal',object_id=h.journal_code,new={'amount':float(amount),'status':'PREPARED','template_code':h.template_code,'template_version':h.template_version},details='Balanced TP journal created from approved adjustment using governed template when available')
    db.commit();return _journal_dict(db,h)

def _journal_dict(db,h):
    lines=db.query(JournalLine).filter(JournalLine.journal_id==h.id).order_by(JournalLine.line_no).all()
    debit=sum((D(x.amount) for x in lines if x.debit_credit=='DEBIT'),Decimal('0'));credit=sum((D(x.amount) for x in lines if x.debit_credit=='CREDIT'),Decimal('0'))
    a=db.get(Adjustment,h.adjustment_id);calc=db.get(Calculation,a.calculation_id) if a else None;pol=db.get(Policy,calc.policy_id) if calc else None
    return {'journal_id':h.id,'journal_code':h.journal_code,'adjustment_id':h.adjustment_id,'adjustment_code':a.adjustment_code if a else None,'approval_actor':a.approved_by if a else None,'policy_code':pol.policy_code if pol else None,'policy_version':pol.version if pol else None,'company_code':h.company_code,'ledger':h.ledger,'document_type':h.document_type,'posting_date':h.posting_date,'document_date':h.document_date,'currency':h.currency,'status':h.status,'template_code':h.template_code,'template_version':h.template_version,'created_at':h.created_at.isoformat() if h.created_at else None,'debit_total':float(debit),'credit_total':float(credit),'balanced':money(debit-credit)==0,'lines':[{'line_no':x.line_no,'gl_account':x.gl_account,'debit_credit':x.debit_credit,'amount':float(x.amount),'currency':x.currency,'profit_center':x.profit_center,'trading_partner':x.trading_partner,'text':x.text} for x in lines]}

@router.get('/journals')
def list_journals(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    return [_journal_dict(db,h) for h in db.query(JournalHeader).filter(JournalHeader.workspace_id==user.workspace_id).order_by(JournalHeader.id.desc()).all()]

@router.post('/postings/simulate/{journal_id}')
def simulate_posting(journal_id:int,simulate_rejection:bool=False,simulate_posting_delta:float=0,user:User=Depends(require_permission('journal')),db:Session=Depends(get_db)):
    h=db.query(JournalHeader).filter(JournalHeader.id==journal_id,JournalHeader.workspace_id==user.workspace_id).with_for_update().first()
    if not h: raise HTTPException(404,'Journal not found')
    # Idempotency must be checked before the mutable journal-status gate. A caller may
    # legitimately retry the same request after the first submission already moved the
    # journal to POSTED/RECONCILED. Return the original posting instead of a 409.
    existing_by_journal=db.query(Posting).filter(Posting.workspace_id==user.workspace_id,Posting.journal_header_id==h.id).order_by(Posting.id.desc()).first()
    if existing_by_journal:
        rec=db.query(Reconciliation).filter(Reconciliation.adjustment_id==h.adjustment_id).order_by(Reconciliation.id.desc()).first()
        return {'posting_id':existing_by_journal.id,'erp_document_number':existing_by_journal.erp_document_number,'status':existing_by_journal.status,'idempotent_replay':True,'reconciliation':_rec_dict(rec) if rec else None}
    if h.status not in ('PREPARED','REJECTED','FAILED'): raise HTTPException(409,f'Journal status {h.status} cannot be posted')
    a=db.get(Adjustment,h.adjustment_id)
    if not a or a.status!='APPROVED': raise HTTPException(409,'Underlying adjustment is not approved')
    lines=db.query(JournalLine).filter(JournalLine.journal_id==h.id).all()
    debit=money(sum((D(x.amount) for x in lines if x.debit_credit=='DEBIT'),Decimal('0')));credit=money(sum((D(x.amount) for x in lines if x.debit_credit=='CREDIT'),Decimal('0')))
    if debit!=credit: raise HTTPException(409,'Journal is not balanced')
    if debit!=money(abs(D(a.amount))): raise HTTPException(409,'Journal amount does not equal approved adjustment')
    idem=hashlib.sha256(f'{h.journal_code}:{h.adjustment_id}:{debit}'.encode()).hexdigest()
    existing=db.query(Posting).filter(Posting.idempotency_key==idem).first()
    if existing:
        rec=db.query(Reconciliation).filter(Reconciliation.adjustment_id==a.id).order_by(Reconciliation.id.desc()).first()
        return {'posting_id':existing.id,'erp_document_number':existing.erp_document_number,'status':existing.status,'idempotent_replay':True,'reconciliation':_rec_dict(rec) if rec else None}
    connector=SimulatedSAPConnector()
    h.status='SUBMITTED'
    response=connector.submit_journal({'amount':float(debit),'company_code':h.company_code,'currency':h.currency,'lines':len(lines),'simulate_rejection':simulate_rejection,'simulate_posting_delta':simulate_posting_delta},idem)
    p=Posting(workspace_id=user.workspace_id,journal_header_id=h.id,idempotency_key=idem,erp_system='SAP_S4_SIMULATOR',erp_document_number=response.document_number,posted_amount=response.posted_amount,status=response.status,posted_at=utcnow_naive())
    db.add(p);db.flush();db.add(PostingAttempt(posting_id=p.id,attempt_no=1,request_payload={'journal_code':h.journal_code,'amount':float(debit)},response_payload=response.payload,status=response.status,error_message=response.payload.get('message') if isinstance(response.payload,dict) else None))
    if response.status=='POSTED':
        h.status='POSTED';diff=money(D(response.posted_amount)-abs(D(a.amount)));rec=Reconciliation(workspace_id=user.workspace_id,adjustment_id=a.id,expected_amount=abs(D(a.amount)),approved_amount=abs(D(a.amount)),journal_amount=debit,posted_amount=response.posted_amount,final_pnl_impact=response.posted_amount,difference=diff,status='RECONCILED' if abs(diff)<=Decimal('0.01') else 'DIFFERENCE',tolerance=Decimal('0.01'),currency=a.currency);db.add(rec);db.flush()
        if rec.status=='DIFFERENCE':
            exc=ExceptionCase(workspace_id=user.workspace_id,exception_code=f'EXC-REC-{rec.id}',entity_id=a.entity_id,category='RECONCILIATION',severity='ERROR',amount=abs(diff),owner='finance@otp.local',status='OPEN',evidence=[{'type':'reconciliation','id':rec.id},{'type':'journal','id':h.id},{'type':'posting','id':p.id}])
            db.add(exc);db.flush();rec.exception_code=exc.exception_code
        p.status='RECONCILED' if rec.status=='RECONCILED' else 'POSTED';h.status=p.status
    else:
        h.status='REJECTED';rec=None
    audit(db,event_type='ERP_POSTING_SIMULATED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code if (e:=db.get(Entity,a.entity_id)) else None,object_type='posting',object_id=p.erp_document_number,new={'status':p.status,'amount':float(p.posted_amount),'simulated':True},details='SAP S/4 connector contract executed against deterministic simulator',source_system='SAP_S4_SIMULATOR')
    db.commit();return {'posting_id':p.id,'erp_document_number':p.erp_document_number,'status':p.status,'simulated':True,'reconciliation':_rec_dict(rec) if rec else None}

def _rec_dict(r):
    return {'id':r.id,'adjustment_id':r.adjustment_id,'expected_amount':float(r.expected_amount),'approved_amount':float(r.approved_amount or 0),'journal_amount':float(r.journal_amount or 0),'posted_amount':float(r.posted_amount),'final_pnl_impact':float(r.final_pnl_impact or 0),'difference':float(r.difference),'tolerance':float(r.tolerance),'currency':r.currency,'status':r.status,'exception_code':r.exception_code,'certified_by':r.certified_by,'certified_at':r.certified_at.isoformat() if r.certified_at else None,'certification_comment':r.certification_comment}

@router.get('/postings')
def postings(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    out=[]
    for p in db.query(Posting).filter(Posting.workspace_id==user.workspace_id).order_by(Posting.id.desc()):
        h=db.get(JournalHeader,p.journal_header_id) if p.journal_header_id else None
        a=db.get(Adjustment,h.adjustment_id) if h else None
        attempts=db.query(PostingAttempt).filter(PostingAttempt.posting_id==p.id).order_by(PostingAttempt.attempt_no).all()
        rec=db.query(Reconciliation).filter(Reconciliation.adjustment_id==h.adjustment_id).order_by(Reconciliation.id.desc()).first() if h else None
        out.append({'id':p.id,'journal_header_id':p.journal_header_id,'journal_code':h.journal_code if h else None,'adjustment_id':h.adjustment_id if h else None,'adjustment_code':a.adjustment_code if a else None,'company_code':h.company_code if h else None,'period':(h.posting_date[:7] if h and h.posting_date else None),'posting_date':h.posting_date if h else None,'currency':h.currency if h else None,'erp_system':p.erp_system,'erp_document_number':p.erp_document_number,'posted_amount':float(p.posted_amount),'status':p.status,'posted_at':p.posted_at.isoformat() if p.posted_at else None,'idempotency_key':p.idempotency_key,'attempts':[{'attempt_no':x.attempt_no,'status':x.status,'request_payload':x.request_payload,'response_payload':x.response_payload,'error_message':x.error_message,'created_at':x.created_at.isoformat() if x.created_at else None} for x in attempts],'reconciliation':_rec_dict(rec) if rec else None})
    return out

@router.get('/reconciliations')
def reconciliations(user:User=Depends(require_permission('read')),db:Session=Depends(get_db)):
    return [_rec_dict(r) for r in db.query(Reconciliation).filter(Reconciliation.workspace_id==user.workspace_id).order_by(Reconciliation.id.desc()).all()]


class ReconciliationCertificationIn(BaseModel):
    comment:str|None=None

@router.post('/reconciliations/{reconciliation_id}/certify')
def certify_reconciliation(reconciliation_id:int,body:ReconciliationCertificationIn|None=None,user:User=Depends(require_permission('approve')),db:Session=Depends(get_db)):
    r=db.query(Reconciliation).filter(Reconciliation.id==reconciliation_id,Reconciliation.workspace_id==user.workspace_id).with_for_update().first()
    if not r: raise HTTPException(404,'Reconciliation not found')
    a=db.get(Adjustment,r.adjustment_id);e=db.get(Entity,a.entity_id) if a else None
    if e: require_entity_access(db,user,e,approve=True)
    if r.status not in {'RECONCILED','WITHIN_TOLERANCE'}: raise HTTPException(409,'Only reconciled/within-tolerance records can be certified')
    r.certified_by=user.email;r.certified_at=utcnow_naive();r.certification_comment=body.comment if body else None;r.status='CERTIFIED'
    audit(db,event_type='RECONCILIATION_CERTIFIED',actor=user.email,actor_role=user.role,workspace_id=user.workspace_id,entity_code=e.entity_code if e else None,object_type='reconciliation',object_id=str(r.id),new={'status':'CERTIFIED','comment':r.certification_comment},details='Finance/TP reconciliation certified')
    db.commit();return _rec_dict(r)
