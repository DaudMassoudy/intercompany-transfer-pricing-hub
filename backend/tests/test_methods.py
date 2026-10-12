from decimal import Decimal
import pytest
from app.services.finance import cost_plus,cost_plus_markup,resale_margin,resale_target_purchase_cost,berry_ratio,cup_variance,profit_split,fx_convert,calculate_policy_result

@pytest.mark.parametrize('base,markup,profit,charge',[(100,.05,'5.00','105.00'),(1000,.1,'100.00','1100.00'),(999.99,.075,'75.00','1074.99'),(0,.05,'0.00','0.00'),(250000,.05,'12500.00','262500.00'),(1000000,.03,'30000.00','1030000.00')])
def test_cost_plus(base,markup,profit,charge):
    p,c=cost_plus(base,markup);assert p==Decimal(profit);assert c==Decimal(charge)

@pytest.mark.parametrize('revenue,costs,expected',[(105,100,'0.05000000'),(110,100,'0.10000000'),(95,100,'-0.05000000'),(0,0,'0')])
def test_cost_plus_markup(revenue,costs,expected): assert cost_plus_markup(revenue,costs)==Decimal(expected)

@pytest.mark.parametrize('revenue,purchase,expected',[(100,70,'0.30000000'),(100,80,'0.20000000'),(200,150,'0.25000000'),(0,10,'0')])
def test_resale_margin(revenue,purchase,expected): assert resale_margin(revenue,purchase)==Decimal(expected)

@pytest.mark.parametrize('revenue,target,expected',[(100,.3,'70.00'),(100,.25,'75.00'),(200,.2,'160.00')])
def test_resale_target_cost(revenue,target,expected): assert resale_target_purchase_cost(revenue,target)==Decimal(expected)

def test_berry_and_cup():
    assert berry_ratio(30,20)==Decimal('1.50000000')
    assert cup_variance(105,100)==Decimal('0.05000000')

def test_profit_split_rounding_reconciles():
    x=profit_split(100,{'A':1,'B':2,'C':3});assert sum(x.values())==Decimal('100.00');assert x['C']==Decimal('50.00')

@pytest.mark.parametrize('amount,rate,expected',[(100,1.1,'110.00'),(100,.9,'90.00'),(1234.56,1.0,'1234.56'),(-100,1.2,'-120.00')])
def test_fx(amount,rate,expected): assert fx_convert(amount,rate)==Decimal(expected)

def test_policy_methods():
    r=calculate_policy_result('TNMM','ROS',revenue=100,cogs=70,opex=25,target=.04,lower=.03,upper=.05);assert r.adjustment==Decimal('-1.00')
    c=calculate_policy_result('COST_PLUS','COST_PLUS',revenue=105,eligible_costs=100,target=.05,lower=.04,upper=.07);assert c.actual==Decimal('0.05000000')
    rp=calculate_policy_result('RESALE_PRICE','RESALE_MARGIN',revenue=100,resale_purchase_cost=75,target=.3,lower=.25,upper=.35);assert rp.adjustment==Decimal('-5.00')
