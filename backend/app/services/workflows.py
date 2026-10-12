from __future__ import annotations
import re
from decimal import Decimal
from sqlalchemy.orm import Session

from ..models import MasterDataRecord

_CONDITION_RE=re.compile(r'^\s*(amount|materiality)\s*(>=|<=|>|<|==)\s*([0-9]+(?:\.[0-9]+)?)\s*$',re.I)


def _condition_matches(expr:str|None, *, amount=0, materiality=0) -> bool:
    if not expr or not expr.strip():
        return True
    m=_CONDITION_RE.match(expr)
    if not m:
        return False
    field,op,raw=m.groups();left=Decimal(str(amount if field.lower()=='amount' else materiality or 0));right=Decimal(raw)
    return {'>':left>right,'>=':left>=right,'<':left<right,'<=':left<=right,'==':left==right}[op]


def _csv(value) -> set[str]:
    if value is None:return set()
    if isinstance(value,list):return {str(x).strip().upper() for x in value if str(x).strip()}
    return {x.strip().upper() for x in str(value).replace(';',',').split(',') if x.strip()}


def _groups(attrs:dict) -> list[list[str]]:
    """Structured, no-code approval grammar.

    approver_roles accepts sequential groups separated by '>' and parallel roles
    inside a group separated by '+'. Example:
      TP_MANAGER > FINANCE_CONTROLLER+GROUP_TAX_DIRECTOR
    The older comma-separated form remains sequential for backwards compatibility.
    """
    raw=str(attrs.get('approver_roles') or '').strip()
    if not raw:return []
    if '>' in raw:
        return [[r.strip().upper() for r in part.split('+') if r.strip()] for part in raw.split('>') if part.strip()]
    if '+' in raw and str(attrs.get('approval_mode','')).upper()=='PARALLEL':
        return [[r.strip().upper() for r in raw.split('+') if r.strip()]]
    roles=[x.strip().upper() for x in raw.replace(';',',').split(',') if x.strip()]
    if str(attrs.get('approval_mode','SEQUENTIAL')).upper()=='PARALLEL':return [roles]
    return [[r] for r in roles]


def resolve_workflow(db:Session, workspace_id:int, *, workflow_code:str|None=None, object_type:str, amount=0, materiality=0,
                     entity_code:str|None=None,country:str|None=None,method:str|None=None,risk:str|None=None) -> dict|None:
    q=(db.query(MasterDataRecord)
       .filter(MasterDataRecord.workspace_id==workspace_id,
               MasterDataRecord.domain=='WORKFLOW_DEFINITIONS',
               MasterDataRecord.active.is_(True)))
    if workflow_code:q=q.filter(MasterDataRecord.record_code==workflow_code.upper())
    rows=q.order_by(MasterDataRecord.version_no.desc(),MasterDataRecord.record_code).all()
    obj=object_type.upper()
    for row in rows:
        a=row.attributes or {}
        accepted=_csv(a.get('object_type'))
        if accepted and obj not in accepted and not ({'ADJUSTMENT','TRUE_UP','TRUE-UP'} & accepted and obj in {'ADJUSTMENT','TRUE_UP','TRUE-UP'}):continue
        if not _condition_matches(a.get('condition_expression'),amount=abs(Decimal(str(amount))),materiality=materiality):continue
        min_amount=a.get('min_amount');max_amount=a.get('max_amount')
        if min_amount not in (None,'') and abs(Decimal(str(amount)))<Decimal(str(min_amount)):continue
        if max_amount not in (None,'') and abs(Decimal(str(amount)))>Decimal(str(max_amount)):continue
        checks=[('entities',entity_code),('countries',country),('methods',method),('risk_levels',risk)]
        failed=False
        for field,value in checks:
            allowed=_csv(a.get(field))
            if allowed and (not value or str(value).upper() not in allowed):failed=True;break
        if failed:continue
        groups=_groups(a)
        if not groups or any(not g for g in groups):continue
        return {'code':row.record_code,'version':row.version_no,'groups':groups,'roles':[r for g in groups for r in g],
                'approval_mode':str(a.get('approval_mode') or ('PARALLEL' if len(groups)==1 and len(groups[0])>1 else 'SEQUENTIAL')).upper(),
                'prevent_self_approval':bool(a.get('prevent_self_approval',True)),'condition_expression':a.get('condition_expression'),
                'sla_hours':int(a.get('sla_hours') or 72),'escalation_role':a.get('escalation_role'),'allow_delegation':bool(a.get('allow_delegation',True))}
    return None


def resolve_adjustment_workflow(db:Session, workspace_id:int, *, amount, materiality=0) -> dict|None:
    wf=resolve_workflow(db,workspace_id,object_type='ADJUSTMENT',amount=amount,materiality=materiality)
    if not wf:return None
    # Legacy approval request uses a sequential role list. Preserve compatibility;
    # the generic workflow engine handles genuine parallel groups.
    return {**wf,'roles':[r for g in wf['groups'] for r in g]}
