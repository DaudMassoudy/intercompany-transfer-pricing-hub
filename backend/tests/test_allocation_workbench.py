from __future__ import annotations


def auth(token): return {'Authorization':f'Bearer {token}'}


def test_configurable_allocation_lifecycle_and_execution(client, analyst_token, manager_token):
    body={
      'rule_code':'ALLOC-TEST-HR-001','sender_segment':'NL02-SVC','cost_pool_name':'Global HR','cost_pool_type':'HR','sender_entity_code':'NL02',
      'period_scope':'MONTHLY','currency':'EUR','source_accounts':['610100'],'source_cost_centers':[],'source_profit_centers':[],'source_transactions':[],
      'source_amount_source':'MANUAL_CONTROLLED','manual_amount_allowed':True,'driver_type':'HEADCOUNT','driver_source':'MANUAL_CONTROLLED',
      'recipients':{'DE01-DIST':60,'FR01-DIST':40},'exclusions':[{'category':'SHAREHOLDER_ACTIVITY'}],'stages':[],
      'markup_treatment':'MARKUP_ELIGIBLE','markup_rate':0.05,'effective_from':'2026-01-01'
    }
    r=client.post('/api/v1/allocations/rules',headers=auth(analyst_token),json=body)
    assert r.status_code==200,r.text
    rule=r.json();assert rule['status']=='DRAFT'
    r=client.post(f"/api/v1/allocations/rules/{rule['id']}/submit",headers=auth(analyst_token));assert r.status_code==200 and r.json()['status']=='REVIEW'
    r=client.post(f"/api/v1/allocations/rules/{rule['id']}/approve",headers=auth(manager_token));assert r.status_code==200 and r.json()['status']=='APPROVED'
    r=client.post(f"/api/v1/allocations/rules/{rule['id']}/activate",headers=auth(manager_token));assert r.status_code==200 and r.json()['status']=='ACTIVE'
    sim=client.post(f"/api/v1/allocations/rules/{rule['id']}/simulate",headers=auth(analyst_token),json={'period':'2026-08','source_amount':100000,'driver_values':{'DE01-DIST':60,'FR01-DIST':40},'exclusion_amounts':{'SHAREHOLDER_ACTIVITY':10000}})
    assert sim.status_code==200,sim.text
    s=sim.json();assert s['eligible_pool']==90000.0 and s['allocated_amount']==90000.0 and s['residual']==0.0 and s['markup_amount']==4500.0
    run=client.post(f"/api/v1/allocations/rules/{rule['id']}/execute",headers=auth(analyst_token),json={'period':'2026-08','source_amount':100000,'driver_values':{'DE01-DIST':60,'FR01-DIST':40},'exclusion_amounts':{'SHAREHOLDER_ACTIVITY':10000}})
    assert run.status_code==200,run.text
    assert run.json()['status']=='COMPLETED' and run.json()['reconciled'] is True
    d=client.post(f"/api/v1/allocations/rules/{rule['id']}/deactivate",headers=auth(manager_token));assert d.status_code==200


def test_composite_driver_weights_reconcile(client, analyst_token, manager_token):
    body={
      'rule_code':'ALLOC-TEST-COMP-001','sender_segment':'NL02-SVC','cost_pool_name':'Composite Shared Service','cost_pool_type':'SHARED_SERVICES',
      'currency':'EUR','source_amount_source':'MANUAL_CONTROLLED','manual_amount_allowed':True,'driver_type':'COMPOSITE','driver_source':'MANUAL_CONTROLLED',
      'driver_weights':{'HEADCOUNT':60,'PAYROLL':40},'recipients':{},'markup_treatment':'NO_MARKUP'
    }
    r=client.post('/api/v1/allocations/rules',headers=auth(analyst_token),json=body);assert r.status_code==200,r.text;rid=r.json()['id']
    client.post(f'/api/v1/allocations/rules/{rid}/submit',headers=auth(analyst_token));client.post(f'/api/v1/allocations/rules/{rid}/approve',headers=auth(manager_token));client.post(f'/api/v1/allocations/rules/{rid}/activate',headers=auth(manager_token))
    sim=client.post(f'/api/v1/allocations/rules/{rid}/simulate',headers=auth(analyst_token),json={'period':'2026-08','source_amount':1000,'composite_driver_values':{'HEADCOUNT':{'DE':3,'FR':1},'PAYROLL':{'DE':1,'FR':1}}})
    assert sim.status_code==200,sim.text
    body=sim.json();assert body['reconciled'] is True and body['allocated_amount']==1000.0
    shares={x['recipient']:round(x['share'],2) for x in body['results']}
    assert shares=={'DE':0.65,'FR':0.35}
    d=client.post(f'/api/v1/allocations/rules/{rid}/deactivate',headers=auth(manager_token));assert d.status_code==200
