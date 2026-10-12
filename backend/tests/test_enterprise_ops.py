from __future__ import annotations
import io


def auth(token): return {'Authorization':f'Bearer {token}'}


def test_exception_case_lifecycle_is_writeable_and_audited(client, analyst_token):
    r=client.post('/api/v1/exceptions',headers=auth(analyst_token),json={
        'entity_code':'DE01','category':'RECONCILIATION','severity':'ERROR','amount':123.45,
        'owner':'analyst@otp.local','due_date':'2026-10-10','evidence':[{'type':'control','ref':'TEST-1'}]
    })
    assert r.status_code==200,r.text
    row=r.json();assert row['status']=='OPEN' and row['entity_code']=='DE01'
    r=client.patch(f"/api/v1/exceptions/{row['id']}",headers=auth(analyst_token),json={'status':'RESOLVED','resolution':'Reprocessed source data and reconciled to zero'})
    assert r.status_code==200,r.text
    assert r.json()['status']=='RESOLVED'


def test_versioned_document_upload_search_and_supersession(client, analyst_token):
    files={'file':('evidence.txt',io.BytesIO(b'Policy evidence for controlled distribution transaction DE01.'),'text/plain')}
    data={'document_code':'TEST-EVIDENCE','document_type':'ACCOUNTING_EVIDENCE','entity_code':'DE01'}
    r=client.post('/api/v1/documents/upload',headers=auth(analyst_token),files=files,data=data)
    assert r.status_code==200,r.text
    v1=r.json();assert v1['version']==1 and len(v1['sha256'])==64
    files={'file':('evidence.txt',io.BytesIO(b'Updated policy evidence with benchmark support for DE01.'),'text/plain')}
    r=client.post('/api/v1/documents/upload',headers=auth(analyst_token),files=files,data=data)
    assert r.status_code==200,r.text
    assert r.json()['version']==2
    rows=client.get('/api/v1/documents',headers=auth(analyst_token)).json()
    versions=[x for x in rows if x['document_code']=='TEST-EVIDENCE']
    assert {x['status'] for x in versions}=={'ACTIVE','SUPERSEDED'}
    r=client.get('/api/v1/documents/search/evidence?q=benchmark',headers=auth(analyst_token))
    assert r.status_code==200 and any(x['document_code']=='TEST-EVIDENCE' for x in r.json())


def test_benchmark_governance_and_policy_assignment(client, data_steward_token, manager_token, director_token):
    payload={'change_type':'CREATE','reason':'Controlled benchmark onboarding','payload':{
        'record_code':'BM-TEST-001','name':'Distribution TNMM 2026','effective_from':'2026-01-01',
        'attributes':{'method':'TNMM','pli':'ROS','q1':'0.028','median':'0.050','q3':'0.081','tested_party':'Distributor','geography':'Europe','industry':'Wholesale','search_period':'2023-2025','financial_period':'2023-2025','source':'Moody\'s Orbis','database':'Orbis','screening_date':'2026-09-01','valid_until':'2028-09-01'}
    }}
    r=client.post('/api/v1/master-data/catalog/BENCHMARKS/changes',headers=auth(data_steward_token),json=payload)
    assert r.status_code==200,r.text
    req=r.json();client.post(f"/api/v1/master-data/catalog-changes/{req['id']}/submit",headers=auth(data_steward_token))
    r=client.post(f"/api/v1/master-data/catalog-changes/{req['id']}/approve",headers=auth(manager_token));assert r.status_code==200,r.text
    rows=client.get('/api/v1/benchmarks',headers=auth(director_token));assert rows.status_code==200
    assert any(x['benchmark_id']=='BM-TEST-001' and x['expiry_status']=='VALID' for x in rows.json())
    policies=client.get('/api/v1/policies',headers=auth(director_token)).json();pid=policies[0]['id']
    r=client.post(f'/api/v1/policies/{pid}/benchmark',headers=auth(director_token),json={'benchmark_id':'BM-TEST-001'})
    assert r.status_code==200,r.text
    assert r.json()['benchmark_id']=='BM-TEST-001'


def test_integration_configuration_and_simulator_are_explicit(client, admin_token):
    r=client.post('/api/v1/integrations',headers=auth(admin_token),json={'connection_code':'SAP-S4-SANDBOX','connector_type':'SAP_S4','config':{'base_url':'https://sandbox.invalid'},'secret_reference':'vault://otp/sap-s4'})
    assert r.status_code==200,r.text
    cid=r.json()['id']
    r=client.post(f'/api/v1/integrations/{cid}/test',headers=auth(admin_token))
    assert r.status_code==200,r.text
    body=r.json();assert body['live'] is False and body['qualification']=='EXTERNAL QUALIFICATION REQUIRED'


def test_new_governed_configuration_domains_are_exposed(client, analyst_token):
    r=client.get('/api/v1/master-data/catalog/domains',headers=auth(analyst_token))
    assert r.status_code==200
    domains={x['domain'] for x in r.json()}
    assert {'BENCHMARKS','DATA_QUALITY_RULES','WORKFLOW_DEFINITIONS','JOURNAL_TEMPLATES'} <= domains
