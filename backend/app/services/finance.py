from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Iterable, Mapping

MONEY_Q = Decimal('0.01')
RATIO_Q = Decimal('0.00000001')
DEFAULT_ROUNDING = ROUND_HALF_UP

def D(value) -> Decimal:
    if isinstance(value, Decimal): return value
    if value is None: return Decimal('0')
    return Decimal(str(value))

def money(value) -> Decimal:
    return D(value).quantize(MONEY_Q, rounding=DEFAULT_ROUNDING)

def ratio(value) -> Decimal:
    return D(value).quantize(RATIO_Q, rounding=DEFAULT_ROUNDING)

@dataclass(frozen=True)
class PnLResult:
    revenue: Decimal
    cogs: Decimal
    opex: Decimal
    gross_profit: Decimal
    ebit: Decimal
    ros: Decimal
    def to_dict(self): return {k: float(v) for k,v in asdict(self).items()}

@dataclass(frozen=True)
class TPResult:
    method: str
    pli: str
    actual: Decimal
    target: Decimal
    adjustment: Decimal
    status: str
    metadata: dict
    def to_dict(self):
        return {'method':self.method,'pli':self.pli,'actual':float(self.actual),'target':float(self.target),'adjustment':float(self.adjustment),'status':self.status,'metadata':self.metadata}

@dataclass(frozen=True)
class AllocationLine:
    recipient: str
    driver_value: Decimal
    share: Decimal
    amount: Decimal
    def to_dict(self): return {'recipient':self.recipient,'driver_value':float(self.driver_value),'share':float(self.share),'amount':float(self.amount)}

def segmented_pnl(revenue, cogs, opex) -> PnLResult:
    revenue=money(revenue); cogs=money(cogs); opex=money(opex)
    gross=money(revenue-cogs)
    ebit=money(gross-opex)
    ros=Decimal('0') if revenue == 0 else ratio(ebit/revenue)
    return PnLResult(revenue,cogs,opex,gross,ebit,ros)

def target_ebit(revenue, target_ros) -> Decimal:
    return money(D(revenue)*D(target_ros))

def true_up_to_target(revenue, actual_ebit, target_ros) -> Decimal:
    return money(target_ebit(revenue,target_ros)-D(actual_ebit))

def status_for(actual, lower, upper, amber_buffer=Decimal('0.0025')) -> str:
    actual=D(actual); lower=D(lower); upper=D(upper); amber_buffer=D(amber_buffer)
    if actual < lower or actual > upper: return 'RED'
    if actual < lower + amber_buffer or actual > upper - amber_buffer: return 'AMBER'
    return 'GREEN'

def simulate_price_effect(revenue, cogs, opex, ic_purchase_delta) -> PnLResult:
    return segmented_pnl(revenue, D(cogs)+D(ic_purchase_delta), opex)

def goal_seek_cogs_for_ros(revenue, opex, target_ros) -> Decimal:
    # EBIT = Revenue * target; EBIT = Revenue - COGS - OPEX
    return money(D(revenue)-D(opex)-target_ebit(revenue,target_ros))

def goal_seek_unit_ic_price(revenue, opex, target_ros, non_ic_cogs, units) -> Decimal:
    units=D(units)
    if units <= 0: raise ValueError('units must be positive')
    total_cogs=goal_seek_cogs_for_ros(revenue,opex,target_ros)
    ic_cogs=total_cogs-D(non_ic_cogs)
    return money(ic_cogs/units)

def ebit_total_costs(ebit, total_costs) -> Decimal:
    total_costs=D(total_costs)
    if total_costs == 0: return Decimal('0')
    return ratio(D(ebit)/total_costs)

def ebit_operating_costs(ebit, operating_costs) -> Decimal:
    return ebit_total_costs(ebit,operating_costs)

def berry_ratio(gross_profit, operating_expenses) -> Decimal:
    operating_expenses=D(operating_expenses)
    if operating_expenses == 0: return Decimal('0')
    return ratio(D(gross_profit)/operating_expenses)

def cost_plus(cost_base, markup) -> tuple[Decimal, Decimal]:
    base=money(cost_base); m=D(markup)
    profit=money(base*m)
    charge=money(base+profit)
    return profit,charge

def cost_plus_markup(revenue, eligible_costs) -> Decimal:
    eligible_costs=D(eligible_costs)
    if eligible_costs == 0: return Decimal('0')
    return ratio((D(revenue)-eligible_costs)/eligible_costs)

def resale_margin(resale_revenue, purchase_cost) -> Decimal:
    rev=D(resale_revenue)
    if rev == 0: return Decimal('0')
    return ratio((rev-D(purchase_cost))/rev)

def resale_target_purchase_cost(resale_revenue, target_margin) -> Decimal:
    return money(D(resale_revenue)*(Decimal('1')-D(target_margin)))

def cup_variance(controlled_price, uncontrolled_price) -> Decimal:
    ref=D(uncontrolled_price)
    if ref == 0: return Decimal('0')
    return ratio((D(controlled_price)-ref)/ref)

def profit_split(combined_profit, weights: Mapping[str, object]) -> dict[str, Decimal]:
    combined=money(combined_profit)
    vals={k:D(v) for k,v in weights.items()}
    total=sum(vals.values(),Decimal('0'))
    if total <= 0: raise ValueError('profit split weights must sum to positive value')
    out={}; allocated=Decimal('0')
    keys=list(vals)
    for i,k in enumerate(keys):
        if i == len(keys)-1:
            amt=money(combined-allocated)
        else:
            amt=money(combined*vals[k]/total); allocated += amt
        out[k]=amt
    return out

def allocate_amount(source_amount, drivers: Mapping[str, object]) -> list[AllocationLine]:
    source=money(source_amount)
    d={k:D(v) for k,v in drivers.items()}
    if any(v < 0 for v in d.values()): raise ValueError('allocation drivers cannot be negative')
    total=sum(d.values(),Decimal('0'))
    if total <= 0: raise ValueError('allocation drivers must sum to positive value')
    result=[]; allocated=Decimal('0'); keys=list(d)
    for i,k in enumerate(keys):
        share=ratio(d[k]/total)
        if i == len(keys)-1:
            amt=money(source-allocated)
        else:
            amt=money(source*share); allocated += amt
        result.append(AllocationLine(k,money(d[k]),share,amt))
    return result

def service_charge(gross_cost_pool, exclusions, markup, allocation_drivers: Mapping[str, object]):
    eligible=money(D(gross_cost_pool)-sum((D(x) for x in exclusions),Decimal('0')))
    if eligible < 0: raise ValueError('exclusions exceed gross cost pool')
    profit,chargeable=cost_plus(eligible,markup)
    alloc=allocate_amount(chargeable,allocation_drivers)
    return {'gross_cost_pool':gross_cost_pool,'eligible_cost_pool':eligible,'markup_profit':profit,'chargeable_amount':chargeable,'allocations':alloc}

def forecast_full_year(actual_months: Iterable[Mapping[str, object]], remaining_months: Iterable[Mapping[str, object]]) -> PnLResult:
    rows=list(actual_months)+list(remaining_months)
    return segmented_pnl(sum((D(x.get('revenue',0)) for x in rows),Decimal('0')), sum((D(x.get('cogs',0)) for x in rows),Decimal('0')), sum((D(x.get('opex',0)) for x in rows),Decimal('0')))

def calculate_policy_result(method: str, pli: str, *, revenue=0, cogs=0, opex=0, target=0, lower=0, upper=0, eligible_costs=None, resale_purchase_cost=None) -> TPResult:
    method=method.upper(); pli=pli.upper()
    lower=D(lower); upper=D(upper); target=D(target)
    if method == 'TNMM':
        pnl=segmented_pnl(revenue,cogs,opex)
        if pli == 'ROS': actual=pnl.ros; adjustment=true_up_to_target(pnl.revenue,pnl.ebit,target)
        elif pli in {'EBIT_TOTAL_COSTS','EBIT/TC'}:
            costs=pnl.cogs+pnl.opex; actual=ebit_total_costs(pnl.ebit,costs); adjustment=money((target*costs)-pnl.ebit)
        elif pli in {'BERRY_RATIO','BERRY'}:
            actual=berry_ratio(pnl.gross_profit,pnl.opex); adjustment=money((target*pnl.opex)-pnl.gross_profit)
        else: raise ValueError(f'Unsupported TNMM PLI {pli}')
    elif method == 'COST_PLUS':
        base=D(eligible_costs if eligible_costs is not None else cogs)+D(opex if eligible_costs is None else 0)
        actual=cost_plus_markup(revenue,base); adjustment=money((base*(Decimal('1')+target))-D(revenue))
    elif method in {'RESALE_PRICE','RESALE_MINUS'}:
        pc=D(resale_purchase_cost if resale_purchase_cost is not None else cogs)
        actual=resale_margin(revenue,pc); adjustment=money(resale_target_purchase_cost(revenue,target)-pc)
    else:
        raise ValueError(f'Unsupported method {method}')
    status=status_for(actual,lower,upper) if upper != 0 or lower != 0 else ('GREEN' if actual==target else 'AMBER')
    return TPResult(method,pli,actual,target,adjustment,status,{})

def fx_convert(amount, rate, *, source_currency: str='LOCAL', target_currency: str='GROUP', rate_type: str='AVERAGE') -> Decimal:
    rate=D(rate)
    if rate <= 0: raise ValueError('FX rate must be positive')
    return money(D(amount)*rate)
