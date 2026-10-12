from __future__ import annotations


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def test_hotfix7_master_data_change_is_reviewable(client, data_steward_token, manager_token):
    body={
        'change_type':'CREATE',
        'payload':{
            'record_code':'HF7-GL-TEST',
            'name':'Hotfix 7 governed test account',
            'active':True,
            'effective_from':'2026-09-26',
            'attributes':{'classification':'OPEX','operating':True,'pli_included':True,'allocation_eligible':False,'exceptional_item':False,'pass_through':False},
        },
        'reason':'Hotfix 7 reviewability regression test',
    }
    r=client.post('/api/v1/master-data/catalog/GL_ACCOUNTS/changes',headers=auth(data_steward_token),json=body)
    assert r.status_code==200,r.text
    req=r.json();rid=req['id']
    assert client.post(f'/api/v1/master-data/catalog-changes/{rid}/submit',headers=auth(data_steward_token)).status_code==200
    detail=client.get(f'/api/v1/master-data/catalog-changes/{rid}',headers=auth(manager_token))
    assert detail.status_code==200,detail.text
    d=detail.json();assert d['request_code']==req['request_code'] and d['diff']
    assert any(x['field'] in {'name','effective_from','attributes'} for x in d['diff'])
    ret=client.post(f'/api/v1/master-data/catalog-changes/{rid}/return',headers=auth(manager_token),json={'reason':'Please confirm classification'})
    assert ret.status_code==200,ret.text and ret.json()['status']=='DRAFT'


def test_hotfix7_true_up_preview_pins_applicable_policy(client, analyst_token):
    calcs=client.get('/api/v1/calculations',headers=auth(analyst_token));assert calcs.status_code==200,calcs.text
    calc=next(x for x in calcs.json() if x['calculation_code']=='CALC-DE01-2026-09')
    r=client.post('/api/v1/true-ups/preview',headers=auth(analyst_token),json={'calculation_id':calc['id'],'target_type':'POLICY_TARGET'})
    assert r.status_code==200,r.text
    d=r.json();assert d['calculation_code']=='CALC-DE01-2026-09'
    assert d['policy'] and d['policy']['version'] is not None
    assert 'policy_consistent' in d and 'source_hash' in d and 'formula' in d


def test_hotfix7_data_quality_is_multidimensional(client, analyst_token):
    r=client.get('/api/v1/data-quality',headers=auth(analyst_token));assert r.status_code==200,r.text
    d=r.json();assert d['readiness'] in {'READY','CONDITIONAL','BLOCKED'}
    dims=d['dimensions']
    for key in ['technical_schema_validity','completeness','uniqueness','referential_integrity','consistency','timeliness','business_rule_validity','downstream_control_readiness']:
        assert key in dims


def test_hotfix7_integration_test_history_and_dedicated_admin(client, admin_token, analyst_token):
    # Read remains available to analysts; administration remains privileged.
    assert client.get('/api/v1/integrations',headers=auth(analyst_token)).status_code==200
    denied=client.post('/api/v1/integrations',headers=auth(analyst_token),json={'connection_code':'HF7-DENIED','connector_type':'REST','config':{}})
    assert denied.status_code==403
    created=client.post('/api/v1/integrations',headers=auth(admin_token),json={'connection_code':'HF7-CONTRACT','connector_type':'REST','config':{'mode':'contract'}})
    assert created.status_code==200,created.text
    cid=created.json()['id']
    test=client.post(f'/api/v1/integrations/{cid}/test',headers=auth(admin_token));assert test.status_code==200,test.text
    runs=client.get(f'/api/v1/integrations/{cid}/runs',headers=auth(analyst_token));assert runs.status_code==200,runs.text
    assert runs.json() and runs.json()[0]['run_code']==test.json()['run_code']


def test_hotfix7_system_health_separates_runtime_and_external_gates(client, analyst_token):
    r=client.get('/api/v1/system-health',headers=auth(analyst_token));assert r.status_code==200,r.text
    d=r.json();assert 'services' in d and 'external_qualification' in d
    assert 'checked_at' in d and d['production_readiness']=='BLOCKED_EXTERNAL_QUALIFICATION'
    names={x['service'] for x in d['services']}
    assert {'FastAPI','PostgreSQL','Redis','MinIO','n8n'} <= names
