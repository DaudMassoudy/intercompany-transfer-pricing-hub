from __future__ import annotations

import io
from app.db import SessionLocal
from app.models import GLAccount, MasterDataRecord


def auth(token): return {'Authorization':f'Bearer {token}'}


def test_catalog_domains_are_exposed(client, analyst_token):
    r=client.get('/api/v1/master-data/catalog/domains',headers=auth(analyst_token))
    assert r.status_code==200
    domains={x['domain'] for x in r.json()}
    assert {'GL_ACCOUNTS','COST_CENTERS','PLANTS','PRODUCTS','CURRENCIES','TP_SEGMENTS'} <= domains


def test_master_data_maker_checker_updates_operational_projection(client, data_steward_token, manager_token):
    payload={
        'change_type':'CREATE','reason':'New controlled allocation account',
        'payload':{'record_code':'699900','name':'Controlled Test Cost','effective_from':'2026-10-01','attributes':{
            'classification':'OPEX','operating':True,'pli_included':True,'cost_plus_eligible':True,'allocation_eligible':True,'exceptional_item':False,'pass_through':False
        }}
    }
    r=client.post('/api/v1/master-data/catalog/GL_ACCOUNTS/changes',headers=auth(data_steward_token),json=payload)
    assert r.status_code==200,r.text
    req=r.json();assert req['status']=='DRAFT'
    r=client.post(f"/api/v1/master-data/catalog-changes/{req['id']}/submit",headers=auth(data_steward_token))
    assert r.status_code==200 and r.json()['status']=='SUBMITTED'
    r=client.post(f"/api/v1/master-data/catalog-changes/{req['id']}/approve",headers=auth(manager_token))
    assert r.status_code==200,r.text
    assert r.json()['record']['version_no']==1

    db=SessionLocal()
    try:
        gl=db.query(GLAccount).filter(GLAccount.account_code=='699900').one()
        assert gl.allocation_eligible is True and gl.description=='Controlled Test Cost'
        md=db.query(MasterDataRecord).filter(MasterDataRecord.domain=='GL_ACCOUNTS',MasterDataRecord.record_code=='699900').one()
        assert md.approved_by=='manager@otp.local'
    finally: db.close()
    hist=client.get('/api/v1/master-data/catalog/GL_ACCOUNTS/699900/history',headers=auth(manager_token))
    assert hist.status_code==200 and hist.json()[0]['version_no']==1


def test_master_data_import_preview_is_non_destructive(client, data_steward_token):
    csv=b"record_code,name,classification,operating,pli_included,cost_plus_eligible,allocation_eligible\n699901,Imported OPEX,OPEX,true,true,true,true\n"
    r=client.post('/api/v1/master-data/catalog/GL_ACCOUNTS/import/preview',headers=auth(data_steward_token),files={'file':('gl.csv',io.BytesIO(csv),'text/csv')})
    assert r.status_code==200,r.text
    body=r.json();assert body['counts']['CREATE']==1
    assert 'never interpreted as deletions' in body['note']


def test_master_deactivation_propagates_to_operational_projection(client, data_steward_token, manager_token):
    create={
        'change_type':'CREATE','reason':'Lifecycle control test',
        'payload':{'record_code':'699902','name':'Lifecycle GL','attributes':{'classification':'OPEX','allocation_eligible':True}}
    }
    r=client.post('/api/v1/master-data/catalog/GL_ACCOUNTS/changes',headers=auth(data_steward_token),json=create); assert r.status_code==200,r.text
    req=r.json(); client.post(f"/api/v1/master-data/catalog-changes/{req['id']}/submit",headers=auth(data_steward_token))
    r=client.post(f"/api/v1/master-data/catalog-changes/{req['id']}/approve",headers=auth(manager_token)); assert r.status_code==200,r.text
    deact={'change_type':'DEACTIVATE','reason':'End of validity','payload':{'record_code':'699902','name':'Lifecycle GL','attributes':{'classification':'OPEX','allocation_eligible':True}}}
    r=client.post('/api/v1/master-data/catalog/GL_ACCOUNTS/changes',headers=auth(data_steward_token),json=deact); assert r.status_code==200,r.text
    req=r.json(); client.post(f"/api/v1/master-data/catalog-changes/{req['id']}/submit",headers=auth(data_steward_token))
    r=client.post(f"/api/v1/master-data/catalog-changes/{req['id']}/approve",headers=auth(manager_token)); assert r.status_code==200,r.text
    db=SessionLocal()
    try:
        gl=db.query(GLAccount).filter(GLAccount.account_code=='699902').one()
        md=db.query(MasterDataRecord).filter(MasterDataRecord.domain=='GL_ACCOUNTS',MasterDataRecord.record_code=='699902').one()
        assert gl.active is False and md.active is False and md.version_no==2
    finally: db.close()
