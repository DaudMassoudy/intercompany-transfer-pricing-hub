from __future__ import annotations
from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from ..models import AllocationRule, AllocationRun, AllocationResult
from .finance import allocate_amount, money


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _normalized_composite(weights: dict[str, object], values: dict[str, dict[str, object]]) -> dict[str, Decimal]:
    if not weights: raise ValueError('Composite driver weights are required')
    parsed={k:_d(v) for k,v in weights.items()}
    total=sum(parsed.values(),Decimal('0'))
    if total==Decimal('100'): parsed={k:v/Decimal('100') for k,v in parsed.items()};total=Decimal('1')
    if abs(total-Decimal('1'))>Decimal('0.000001'): raise ValueError('Composite driver weights must sum to 1.0 or 100')
    recipients=set()
    for driver in parsed:
        recipients.update((values.get(driver) or {}).keys())
    if not recipients: raise ValueError('Composite driver values are required')
    score={r:Decimal('0') for r in recipients}
    for driver,weight in parsed.items():
        rows={r:_d(v) for r,v in (values.get(driver) or {}).items()}
        if any(v<0 for v in rows.values()): raise ValueError('Negative driver values are not allowed')
        subtotal=sum(rows.values(),Decimal('0'))
        if subtotal<=0: raise ValueError(f'Composite driver {driver} has no positive values')
        for recipient in recipients:
            score[recipient]+=weight*(rows.get(recipient,Decimal('0'))/subtotal)
    return score



def _multi_stage_allocate(eligible:Decimal, stages:list[dict], stage_driver_values:dict[str,dict]) -> list[dict]:
    if not stages:
        return []
    codes=[]
    for i,stage in enumerate(stages,1):
        code=str((stage or {}).get('code') or (stage or {}).get('stage_code') or f'STAGE_{i}').strip().upper()
        if code in codes: raise ValueError(f'Duplicate allocation stage code: {code}')
        codes.append(code)
    buckets=[{'node':'SOURCE','path':['SOURCE'],'amount':eligible}]
    for idx,code in enumerate(codes):
        raw=(stage_driver_values or {}).get(code) or (stage_driver_values or {}).get(code.lower())
        if raw is None: raise ValueError(f'Driver values are required for allocation stage {code}')
        # Convenience for the first stage: {recipient: value} is treated as SOURCE -> recipients.
        if idx==0 and raw and all(not isinstance(v,dict) for v in raw.values()):
            raw={'SOURCE':raw}
        next_buckets=[]
        for bucket in buckets:
            drivers=raw.get(bucket['node']) if isinstance(raw,dict) else None
            if drivers is None and isinstance(raw,dict): drivers=raw.get('*')
            if not isinstance(drivers,dict) or not drivers:
                raise ValueError(f'No driver values configured for stage {code} parent {bucket["node"]}')
            if any(_d(v)<0 for v in drivers.values()): raise ValueError('Negative driver values are not allowed')
            lines=allocate_amount(bucket['amount'],drivers)
            for line in lines:
                child=str(line.recipient)
                if child in bucket['path']:
                    raise ValueError(f'Circular allocation detected at stage {code}: {" -> ".join(bucket["path"]+[child])}')
                next_buckets.append({'node':child,'path':bucket['path']+[child],'amount':line.amount,'driver_value':line.driver_value,'local_share':line.share,'stage_code':code})
        buckets=next_buckets
    out=[]
    for b in buckets:
        global_share=(b['amount']/eligible) if eligible else Decimal('0')
        out.append({'recipient':b['node'],'driver_value':float(b.get('driver_value',0)),'share':float(global_share),'base_allocated_amount':float(money(b['amount'])),'path':b['path'][1:],'stage_code':b.get('stage_code')})
    return out

def simulate_allocation(rule: AllocationRule, source_amount, driver_values: dict[str, object]|None=None, *, composite_driver_values: dict[str,dict[str,object]]|None=None, stage_driver_values:dict[str,dict]|None=None, exclusion_amounts: dict[str,object]|None=None) -> dict:
    source=money(source_amount)
    if source<0: raise ValueError('Source amount cannot be negative')
    exclusions={k:money(v) for k,v in (exclusion_amounts or {}).items()}
    if any(v<0 for v in exclusions.values()): raise ValueError('Exclusion amounts cannot be negative')
    excluded_total=money(sum(exclusions.values(),Decimal('0')))
    if excluded_total>source: raise ValueError('Exclusions cannot exceed original pool')
    eligible=money(source-excluded_total)

    multistage=bool(rule.stages)
    if multistage:
        raw_lines=_multi_stage_allocate(eligible,rule.stages or [],stage_driver_values or {}) if eligible else []
        allocated=money(sum((_d(x['base_allocated_amount']) for x in raw_lines),Decimal('0')))
        driver_mode='MULTI_STAGE'
    elif rule.driver_weights:
        normalized=_normalized_composite(rule.driver_weights,composite_driver_values or {})
        base_lines=allocate_amount(eligible,normalized) if eligible else []
        raw_lines=[{**x.to_dict(),'base_allocated_amount':float(x.amount)} for x in base_lines]
        allocated=money(sum((x.amount for x in base_lines),Decimal('0')))
        driver_mode='COMPOSITE'
    else:
        values=driver_values or rule.recipients or {}
        if eligible and not values: raise ValueError('Driver values are required')
        base_lines=allocate_amount(eligible,values) if eligible else []
        raw_lines=[{**x.to_dict(),'base_allocated_amount':float(x.amount)} for x in base_lines]
        allocated=money(sum((x.amount for x in base_lines),Decimal('0')))
        driver_mode=rule.driver_type

    residual=money(eligible-allocated)
    rate=_d(rule.markup_rate or 0)
    if rule.markup_treatment in {'MARKUP_ELIGIBLE','CUSTOM_MARKUP'} and rate<0: raise ValueError('Markup rate cannot be negative')
    apply_markup=rule.markup_treatment in {'MARKUP_ELIGIBLE','CUSTOM_MARKUP'} or (rule.markup_eligible and rate>0)
    lines=[];markup_total=Decimal('0');recipient_rules=rule.recipient_rules or {}
    for x in raw_lines:
        recipient=str(x['recipient']);cfg=recipient_rules.get(recipient) or recipient_rules.get(recipient.upper()) or {}
        if cfg.get('eligible') is False or cfg.get('include') is False:
            raise ValueError(f'Recipient {recipient} is not eligible under the active recipient rule')
        if cfg.get('benefit_test_required') and not cfg.get('benefit_test_passed'):
            raise ValueError(f'Recipient {recipient} failed the required benefit test')
        base=money(x['base_allocated_amount'])
        min_threshold=_d(cfg.get('minimum_threshold') or 0);max_cap=_d(cfg.get('maximum_cap') or 0)
        if min_threshold and base<min_threshold: raise ValueError(f'Recipient {recipient} allocation is below minimum threshold')
        if max_cap and base>max_cap: raise ValueError(f'Recipient {recipient} allocation exceeds maximum cap')
        markup=money(base*rate) if apply_markup else Decimal('0.00')
        markup_total+=markup;charge=money(base+markup)
        recipient_currency=str(cfg.get('currency') or rule.currency).upper();fx_rate=_d(cfg.get('fx_rate') or 1)
        if recipient_currency!=rule.currency and fx_rate<=0: raise ValueError(f'Positive FX rate is required for recipient {recipient}')
        recipient_charge=money(charge*fx_rate)
        lines.append({**x,'base_allocated_amount':float(base),'markup_amount':float(markup),'charge_amount':float(charge),
                      'recipient_currency':recipient_currency,'fx_rate':float(fx_rate),'recipient_charge_amount':float(recipient_charge),
                      'benefit_test_passed':cfg.get('benefit_test_passed') if cfg.get('benefit_test_required') else None})
    markup_total=money(markup_total)
    return {
        'rule_code':rule.rule_code,'version':rule.version,'source_amount':float(source),'exclusions':{k:float(v) for k,v in exclusions.items()},
        'excluded_amount':float(excluded_total),'eligible_pool':float(eligible),'allocated_amount':float(allocated),'residual':float(residual),
        'driver_mode':driver_mode,'stages':rule.stages or [],'markup_treatment':rule.markup_treatment,'markup_rate':float(rate),'markup_amount':float(markup_total),
        'total_recipient_charge':float(money(allocated+markup_total)),'currency':rule.currency,'results':lines,
        'reconciled':abs(residual)<=Decimal('0.01')
    }


def run_allocation(db: Session, rule: AllocationRule, period: str, source_amount, driver_values: dict[str, object]) -> dict:
    """Backward-compatible deterministic allocation execution used by RC.10 APIs/tests."""
    lines=allocate_amount(source_amount,driver_values)
    allocated=money(sum((x.amount for x in lines),Decimal('0')))
    source=money(source_amount); residual=money(source-allocated)
    run=AllocationRun(workspace_id=rule.workspace_id,run_code=f'ALRUN-{uuid.uuid4().hex[:10].upper()}',rule_id=rule.id,period=period,source_amount=source,allocated_amount=allocated,residual=residual,status='COMPLETED' if abs(residual)<=Decimal('0.01') else 'EXCEPTION')
    db.add(run);db.flush()
    for x in lines:
        db.add(AllocationResult(allocation_run_id=run.id,recipient_segment=x.recipient,driver_value=x.driver_value,driver_share=x.share,allocated_amount=x.amount))
    db.flush()
    return {'run_id':run.id,'run_code':run.run_code,'source_amount':float(source),'allocated_amount':float(allocated),'residual':float(residual),'status':run.status,'results':[x.to_dict() for x in lines]}


def execute_configured_allocation(db: Session, rule: AllocationRule, period: str, source_amount, driver_values: dict[str, object]|None=None, *, composite_driver_values: dict[str,dict[str,object]]|None=None, stage_driver_values:dict[str,dict]|None=None, exclusion_amounts: dict[str,object]|None=None) -> dict:
    sim=simulate_allocation(rule,source_amount,driver_values,composite_driver_values=composite_driver_values,stage_driver_values=stage_driver_values,exclusion_amounts=exclusion_amounts)
    source=money(sim['source_amount']); allocated=money(sim['allocated_amount']); residual=money(sim['residual'])
    run=AllocationRun(workspace_id=rule.workspace_id,run_code=f'ALRUN-{uuid.uuid4().hex[:10].upper()}',rule_id=rule.id,period=period,source_amount=source,allocated_amount=allocated,residual=residual,status='COMPLETED' if sim['reconciled'] else 'EXCEPTION')
    db.add(run);db.flush()
    for line in sim['results']:
        db.add(AllocationResult(allocation_run_id=run.id,recipient_segment=line['recipient'],driver_value=_d(line['driver_value']),driver_share=_d(line['share']),allocated_amount=_d(line['base_allocated_amount'])))
    db.flush()
    return {'run_id':run.id,'run_code':run.run_code,'period':period,'status':run.status,**sim}
