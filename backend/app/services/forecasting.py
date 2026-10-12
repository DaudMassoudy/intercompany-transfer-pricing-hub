from __future__ import annotations
from sqlalchemy.orm import Session
from ..models import ForecastVersion, ForecastLine, FinancialPeriod, Entity
from .finance import forecast_full_year, segmented_pnl

def entity_forecast(db: Session, entity: Entity, fiscal_year: int, version_code: str|None=None) -> dict:
    q=db.query(ForecastVersion).filter(ForecastVersion.workspace_id==entity.workspace_id,ForecastVersion.fiscal_year==fiscal_year,ForecastVersion.status=='APPROVED')
    if version_code:
        q=q.filter(ForecastVersion.version_code==version_code)
    else:
        q=q.filter(ForecastVersion.scenario!='BUDGET')
    ver=q.order_by(ForecastVersion.id.desc()).first()
    if not ver: return {'available':False,'reason':'No approved forecast version'}
    lines=db.query(ForecastLine).filter(ForecastLine.forecast_version_id==ver.id,ForecastLine.entity_id==entity.id).order_by(ForecastLine.month).all()
    if not lines: return {'available':False,'reason':'No forecast lines'}
    # Demo convention: months 1..9 are actualized in FinancialPeriod aggregate and 10..12 remain forecast.
    fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==entity.id,FinancialPeriod.period.like(f'{fiscal_year}-%')).order_by(FinancialPeriod.period.desc()).first()
    if fp and fp.period.endswith('-09'):
        # Aggregate YTD FinancialPeriod is treated as 9-month actual; only remaining lines are forecast.
        actual=[{'revenue':fp.revenue,'cogs':fp.cogs,'opex':fp.opex}]
        remaining=[{'revenue':l.revenue,'cogs':l.cogs,'opex':l.opex} for l in lines if l.month>=10]
    else:
        actual=[]; remaining=[{'revenue':l.revenue,'cogs':l.cogs,'opex':l.opex} for l in lines]
    pnl=forecast_full_year(actual,remaining)
    return {'available':True,'version_code':ver.version_code,'scenario':ver.scenario,'fiscal_year':fiscal_year,'pnl':pnl.to_dict(),'months':[{'month':l.month,'revenue':float(l.revenue),'cogs':float(l.cogs),'opex':float(l.opex)} for l in lines]}
