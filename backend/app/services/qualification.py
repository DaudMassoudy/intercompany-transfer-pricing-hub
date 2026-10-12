from __future__ import annotations
from sqlalchemy.orm import Session
from ..models import QualificationControl

INTERNAL_TYPES={'INTERNAL','AUTOMATED'}
PASS='PASS'


def qualification_summary(db: Session, workspace_id: int) -> dict:
    rows=db.query(QualificationControl).filter(QualificationControl.workspace_id==workspace_id).order_by(QualificationControl.domain,QualificationControl.control_code).all()
    internal=[x for x in rows if x.control_type in INTERNAL_TYPES]
    external=[x for x in rows if x.control_type=='EXTERNAL']
    internal_pass=sum(1 for x in internal if x.status==PASS)
    blocking_external=sum(1 for x in external if x.blocking and x.status!=PASS)
    score=0 if not internal else round(100*internal_pass/len(internal),1)
    classification='PRODUCTION_QUALIFIED' if score==100 and blocking_external==0 else 'ENTERPRISE_PRODUCTION_RELEASE_CANDIDATE'
    return {'classification':classification,'internal_score_pct':score,'internal_pass':internal_pass,'internal_total':len(internal),'external_blocking_remaining':blocking_external,'controls':[{'control_code':x.control_code,'domain':x.domain,'title':x.title,'control_type':x.control_type,'requirement':x.requirement,'status':x.status,'evidence':x.evidence,'reviewer':x.reviewer,'reviewed_at':x.reviewed_at.isoformat() if x.reviewed_at else None,'expires_at':x.expires_at.isoformat() if x.expires_at else None,'blocking':x.blocking} for x in rows]}
