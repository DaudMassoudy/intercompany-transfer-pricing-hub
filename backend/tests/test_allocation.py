from decimal import Decimal
import pytest
from app.services.finance import allocate_amount,service_charge

@pytest.mark.parametrize('source,drivers',[(100,{'A':1,'B':1}),(100,{'A':1,'B':2,'C':3}),(999.99,{'DE':450,'FR':300,'IT':250}),(1,{'A':1,'B':1,'C':1}),(1000000,{'A':40,'B':25,'C':20,'D':15})])
def test_allocations_reconcile(source,drivers):
    rows=allocate_amount(source,drivers);assert sum(x.amount for x in rows)==Decimal(str(source)).quantize(Decimal('0.01'))

def test_allocation_negative_driver_rejected():
    with pytest.raises(ValueError): allocate_amount(100,{'A':1,'B':-1})

def test_allocation_zero_rejected():
    with pytest.raises(ValueError): allocate_amount(100,{'A':0,'B':0})

def test_service_charge():
    x=service_charge(10_000_000,[700_000],.05,{'DE':450,'FR':300,'IT':250})
    assert x['eligible_cost_pool']==Decimal('9300000.00');assert x['chargeable_amount']==Decimal('9765000.00');assert sum(a.amount for a in x['allocations'])==Decimal('9765000.00')
