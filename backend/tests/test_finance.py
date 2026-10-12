from decimal import Decimal
import pytest
from app.services.finance import *

def test_germany_golden_case():
    pnl=segmented_pnl(111_900_000,80_000_000,29_315_110)
    assert pnl.ros==Decimal('0.02310000')
    assert true_up_to_target(pnl.revenue,pnl.ebit,0.04)==Decimal('1891110.00')
    assert status_for(pnl.ros,0.03,0.05)=='RED'

@pytest.mark.parametrize('revenue,cogs,opex,target,expected',[
    (1000,700,250,.04,-10),(1000,700,260,.04,0),(2000,1300,620,.05,20),(5000,3500,1200,.06,0),
    (10000,7000,2500,.04,-100),(10000,8000,2500,.03,800),(25000,15000,9000,.05,250),(100000,60000,35000,.04,-1000),
    (100000,65000,33000,.04,2000),(100000,70000,28000,.04,2000),(40000,30000,7000,.05,-1000),(40000,30000,9000,.05,1000),
    (1_000_000,750_000,220_000,.04,10000),(1_000_000,750_000,230_000,.04,20000),(1_000_000,750_000,210_000,.04,0),
    (15_000_000,10_000_000,4_400_000,.05,150000),(15_000_000,10_000_000,4_100_000,.05,-150000),
    (77_000_000,55_000_000,18_000_000,.04,-920000),(77_000_000,55_000_000,20_000_000,.04,1080000),
    (111_900_000,80_000_000,29_315_110,.04,1891110),
])
def test_true_up_cases(revenue,cogs,opex,target,expected):
    p=segmented_pnl(revenue,cogs,opex)
    assert true_up_to_target(revenue,p.ebit,target)==Decimal(str(expected)).quantize(Decimal('0.01'))

@pytest.mark.parametrize('actual,lower,upper,expected',[
    (.02,.03,.05,'RED'),(.06,.03,.05,'RED'),(.04,.03,.05,'GREEN'),(.031,.03,.05,'AMBER'),(.049,.03,.05,'AMBER'),(.035,.03,.05,'GREEN'),(.045,.03,.05,'GREEN'),(.03,.03,.05,'AMBER'),(.05,.03,.05,'AMBER')
])
def test_status_cases(actual,lower,upper,expected): assert status_for(actual,lower,upper)==expected

@pytest.mark.parametrize('ebit,costs,expected',[(10,100,'0.10000000'),(-5,100,'-0.05000000'),(0,100,'0E-8'),(10,0,'0')])
def test_ebit_total_costs(ebit,costs,expected): assert ebit_total_costs(ebit,costs)==Decimal(expected)

def test_zero_revenue_ros(): assert segmented_pnl(0,10,5).ros==0

def test_goal_seek():
    assert goal_seek_cogs_for_ros(100,20,.04)==Decimal('76.00')
    assert goal_seek_unit_ic_price(100,20,.04,16,10)==Decimal('6.00')

def test_simulation_lower_purchase_cost_increases_ros():
    base=segmented_pnl(100,70,25);sim=simulate_price_effect(100,70,25,-2);assert sim.ros>base.ros
