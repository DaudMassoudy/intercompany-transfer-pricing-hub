def auth(token): return {'Authorization':f'Bearer {token}'}

def test_health(client): assert client.get('/api/v1/health/live').status_code==200

def test_dashboard(client,analyst_token):
    r=client.get('/api/v1/dashboard',headers=auth(analyst_token));assert r.status_code==200;data=r.json();assert data['kpis']['entities_monitored']>=5;de=next(x for x in data['entities'] if x['entity_code']=='DE01');assert round(de['actual'],4)==0.0231

def test_goal_seek_simulation(client,analyst_token):
    r=client.post('/api/v1/simulations',headers=auth(analyst_token),json={'entity_code':'DE01','ic_purchase_delta':-1000000,'target_ros':.04});assert r.status_code==200;assert r.json()['required_total_cogs']>0

def test_sod_and_multilevel_approval_and_accounting(client,analyst_token,manager_token,finance_token,director_token):
    rows=client.get('/api/v1/adjustments',headers=auth(analyst_token)).json();a=next(x for x in rows if x['adjustment_code']=='ADJ-DE01-2026-001')
    if a['status'] in ('PROPOSED','RETURNED','REJECTED'):
        r=client.post(f"/api/v1/adjustments/{a['id']}/submit",headers=auth(analyst_token));assert r.status_code==200
    r=client.post(f"/api/v1/adjustments/{a['id']}/approve",headers=auth(analyst_token),json={'comments':'self approval attempt'});assert r.status_code in (403,409)
    r=client.post(f"/api/v1/adjustments/{a['id']}/approve",headers=auth(manager_token),json={'comments':'TP review'});assert r.status_code==200
    r=client.post(f"/api/v1/adjustments/{a['id']}/approve",headers=auth(finance_token),json={'comments':'Finance review'});assert r.status_code==200
    r=client.post(f"/api/v1/adjustments/{a['id']}/approve",headers=auth(director_token),json={'comments':'Tax director approval'});assert r.status_code==200;assert r.json()['status']=='APPROVED'
    j=client.post(f"/api/v1/journals/from-adjustment/{a['id']}",headers=auth(finance_token));assert j.status_code==200;assert j.json()['balanced'] is True
    jid=j.json()['journal_id']
    post=client.post(f"/api/v1/postings/simulate/{jid}",headers=auth(finance_token));assert post.status_code==200;assert post.json()['status']=='RECONCILED';assert post.json()['reconciliation']['difference']==0
    replay=client.post(f"/api/v1/postings/simulate/{jid}",headers=auth(finance_token));assert replay.status_code==200,replay.text;assert replay.json().get('idempotent_replay') is True

def test_german_localized_ai_explanation(client,analyst_token):
    r=client.get('/api/v1/ai/explain/DE01?lang=de',headers=auth(analyst_token))
    assert r.status_code==200
    data=r.json()
    assert data['language']=='de'
    assert 'tatsächliche' in data['answer']
    assert 'Zielanpassung' in data['answer']
    assert 'Provider-Abstraktion' in data['note']

def test_variance_and_qualification_api(client,analyst_token):
    q=client.get('/api/v1/qualification',headers=auth(analyst_token));assert q.status_code==200
    body=q.json();assert body['classification']=='ENTERPRISE_PRODUCTION_RELEASE_CANDIDATE';assert body['internal_score_pct']==100.0
    v=client.post('/api/v1/variance/run',headers=auth(analyst_token),json={'entity_code':'DE01','actual_period':'2026-09','baseline_type':'BUDGET'});assert v.status_code==200
    data=v.json();assert data['status']=='CONTROLLED';assert data['residual']==0;assert len(data['components'])==4
