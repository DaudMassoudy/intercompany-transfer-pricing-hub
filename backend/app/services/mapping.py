from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from sqlalchemy.orm import Session
from ..models import MappingRule, RawFinancialRecord, NormalizedFinancialRecord, Entity, GLAccount

SUPPORTED_FIELDS={'entity_code','counterparty_code','gl_account','cost_center','profit_center','product_sku','product_group','currency'}

def _matches(record: RawFinancialRecord, criteria: dict[str, Any]) -> bool:
    for key, expected in (criteria or {}).items():
        if key not in SUPPORTED_FIELDS: return False
        actual=getattr(record,key,None)
        if expected in (None,'','*'): continue
        if isinstance(expected,list):
            if actual not in expected: return False
        elif str(actual) != str(expected): return False
    return True

def choose_rule(record: RawFinancialRecord, rules: list[MappingRule]) -> MappingRule|None:
    matches=[r for r in rules if r.status=='ACTIVE' and _matches(record,r.match_fields)]
    if not matches: return None
    return sorted(matches,key=lambda r:(r.priority,-r.version,r.id))[0]

def detect_conflicts(rules: list[MappingRule]) -> list[dict]:
    conflicts=[]
    for i,a in enumerate(rules):
        for b in rules[i+1:]:
            if a.status!='ACTIVE' or b.status!='ACTIVE': continue
            if a.priority==b.priority and a.match_fields==b.match_fields and (a.segment_code!=b.segment_code or a.policy_code!=b.policy_code):
                conflicts.append({'rule_a':a.rule_code,'rule_b':b.rule_code,'priority':a.priority,'match_fields':a.match_fields})
    return conflicts

def run_mapping(db: Session, workspace_id: int, source_import_id: int|None=None) -> dict:
    q=db.query(RawFinancialRecord).filter(RawFinancialRecord.workspace_id==workspace_id, RawFinancialRecord.validation_status.in_(['VALID','WARNING']))
    if source_import_id: q=q.filter(RawFinancialRecord.source_import_id==source_import_id)
    records=q.all()
    rules=db.query(MappingRule).filter(MappingRule.workspace_id==workspace_id, MappingRule.status=='ACTIVE').order_by(MappingRule.priority).all()
    conflicts=detect_conflicts(rules)
    mapped=0; unresolved=[]
    for rec in records:
        if db.query(NormalizedFinancialRecord).filter(NormalizedFinancialRecord.raw_record_id==rec.id).first():
            mapped+=1; continue
        rule=choose_rule(rec,rules)
        if not rule:
            unresolved.append(rec.id); continue
        ent=db.query(Entity).filter(Entity.workspace_id==workspace_id,Entity.entity_code==rec.entity_code).first()
        gl=db.query(GLAccount).filter(GLAccount.workspace_id==workspace_id,GLAccount.account_code==rec.gl_account).first()
        if not ent or not gl:
            unresolved.append(rec.id); continue
        db.add(NormalizedFinancialRecord(workspace_id=workspace_id,raw_record_id=rec.id,entity_id=ent.id,period=rec.period,gl_account=rec.gl_account,counterparty_code=rec.counterparty_code,profit_center=rec.profit_center,product_sku=rec.product_sku,product_group=rec.product_group,currency=rec.currency,amount=rec.amount,financial_classification=gl.classification,segment_code=rule.segment_code,controlled_transaction_code=rule.controlled_transaction_code,policy_code=rule.policy_code,mapping_rule_id=rule.id))
        mapped+=1
    db.flush()
    total=len(records)
    return {'total':total,'mapped':mapped,'unresolved':len(unresolved),'coverage':0 if total==0 else mapped/total,'unresolved_ids':unresolved[:1000],'conflicts':conflicts}
