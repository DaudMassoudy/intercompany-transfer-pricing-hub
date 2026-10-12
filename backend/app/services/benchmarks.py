from __future__ import annotations
from decimal import Decimal
from sqlalchemy.orm import Session

from ..models import BenchmarkComparable, BenchmarkFinancialObservation

ACCEPTED_STATUSES={'ACCEPTED','FINAL'}


def _d(v) -> Decimal:
    return Decimal(str(v))


def _percentile(values:list[Decimal], p:Decimal) -> Decimal:
    if not values:
        raise ValueError('No values available')
    vals=sorted(values)
    if len(vals)==1:
        return vals[0]
    pos=(Decimal(len(vals)-1)*p)
    lo=int(pos)
    hi=min(lo+1,len(vals)-1)
    frac=pos-Decimal(lo)
    return vals[lo] + (vals[hi]-vals[lo])*frac


def benchmark_statistics(db:Session, workspace_id:int, benchmark_code:str) -> dict:
    comps=(db.query(BenchmarkComparable)
           .filter(BenchmarkComparable.workspace_id==workspace_id,
                   BenchmarkComparable.benchmark_code==benchmark_code.upper(),
                   BenchmarkComparable.status.in_(ACCEPTED_STATUSES))
           .order_by(BenchmarkComparable.id).all())
    company_values=[]; company_detail=[]; observations=0
    for comp in comps:
        rows=(db.query(BenchmarkFinancialObservation)
              .filter(BenchmarkFinancialObservation.comparable_id==comp.id)
              .order_by(BenchmarkFinancialObservation.fiscal_year).all())
        if not rows:
            continue
        vals=[_d(x.pli) for x in rows]
        avg=sum(vals,Decimal('0'))/Decimal(len(vals))
        company_values.append(avg);observations+=len(vals)
        company_detail.append({'comparable_id':comp.id,'company_name':comp.company_name,'years':[x.fiscal_year for x in rows],
                               'observation_count':len(vals),'average_pli':float(avg)})
    if not company_values:
        raise ValueError('At least one ACCEPTED/FINAL comparable with financial observations is required')
    q1=_percentile(company_values,Decimal('0.25'));med=_percentile(company_values,Decimal('0.50'));q3=_percentile(company_values,Decimal('0.75'))
    return {
        'benchmark_code':benchmark_code.upper(),'comparable_count':len(company_values),'observation_count':observations,
        'minimum':float(min(company_values)),'q1':float(q1),'median':float(med),'q3':float(q3),'maximum':float(max(company_values)),
        'methodology':'Comparable-level arithmetic mean PLI; inclusive linear percentile interpolation using position (n-1)*p.',
        'comparables':company_detail,
    }
