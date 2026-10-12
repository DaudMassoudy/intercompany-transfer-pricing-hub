from io import BytesIO
from openpyxl import Workbook

def auth(token): return {'Authorization':f'Bearer {token}'}

def test_governed_entity_create_edit_history(client,data_steward_token,manager_token):
    payload={'entity_code':'ES01','legal_name':'Spain Distribution SL','country':'ES','currency':'EUR','group_currency':'EUR','characterization':'Limited-Risk Distributor','company_code':'1300','erp_system':'SAP S/4HANA','tax_jurisdiction':'ES','tax_rate':0.25,'customs_territory':'EU','effective_from':'2027-01-01','active':True}
    r=client.post('/api/v1/master-data/entity-changes',headers=auth(data_steward_token),json={'change_type':'CREATE','payload':payload,'reason':'Spain market onboarding'})
    assert r.status_code==200;r0=r.json();assert r0['status']=='DRAFT'
    r=client.post(f"/api/v1/master-data/entity-changes/{r0['id']}/submit",headers=auth(data_steward_token));assert r.status_code==200;assert r.json()['status']=='SUBMITTED'
    # maker-checker: creator cannot approve; Local Finance also lacks approval permission
    r=client.post(f"/api/v1/master-data/entity-changes/{r0['id']}/approve",headers=auth(data_steward_token));assert r.status_code==403
    r=client.post(f"/api/v1/master-data/entity-changes/{r0['id']}/approve",headers=auth(manager_token));assert r.status_code==200;assert r.json()['entity']['legal_name']=='Spain Distribution SL';assert r.json()['version']==1
    rows=client.get('/api/v1/master-data/entities?include_inactive=true',headers=auth(data_steward_token)).json();assert any(x['entity_code']=='ES01' for x in rows)
    # edit through a second governed request
    edit=dict(payload);edit['legal_name']='Spain Distribution S.L.'
    r=client.post('/api/v1/master-data/entity-changes',headers=auth(data_steward_token),json={'change_type':'UPDATE','payload':edit,'reason':'Legal name formatting'});assert r.status_code==200;rid=r.json()['id']
    assert client.post(f'/api/v1/master-data/entity-changes/{rid}/submit',headers=auth(data_steward_token)).status_code==200
    r=client.post(f'/api/v1/master-data/entity-changes/{rid}/approve',headers=auth(manager_token));assert r.status_code==200;assert r.json()['version']==2
    hist=client.get('/api/v1/master-data/entities/ES01/history',headers=auth(data_steward_token));assert hist.status_code==200;assert [x['version'] for x in hist.json()][:2]==[2,1]

def test_entity_master_bulk_preview_does_not_delete_missing_rows(client,data_steward_token,manager_token):
    wb=Workbook();ws=wb.active
    ws.append(['Entity_ID','Company_Code','Legal_Name','Country','Currency','TP_Characterization','ERP_System'])
    ws.append(['PT01','1400','Portugal Distribution Lda','PT','EUR','Limited-Risk Distributor','SAP S/4HANA'])
    bio=BytesIO();wb.save(bio)
    files={'file':('01_Entity_Master.xlsx',bio.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    r=client.post('/api/v1/master-data/entities/import/preview',headers=auth(data_steward_token),files=files)
    assert r.status_code==200;d=r.json();assert d['counts']['CREATE']==1;assert d['counts']['INVALID']==0
    assert 'never interpreted as deletions' in d['note']
    # Stage the workbook as governed requests and approve with a separate reviewer.
    bio2=BytesIO();wb.save(bio2);files2={'file':('01_Entity_Master.xlsx',bio2.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    r=client.post('/api/v1/master-data/entities/import/requests',headers=auth(data_steward_token),files=files2,data={'submit_for_review':'true','reason':'Portugal onboarding'});assert r.status_code==200
    body=r.json();assert body['created_requests']==1;rid=body['requests'][0]['id'];assert body['requests'][0]['status']=='SUBMITTED'
    r=client.post(f'/api/v1/master-data/entity-changes/{rid}/approve',headers=auth(manager_token));assert r.status_code==200;assert r.json()['entity']['entity_code']=='PT01'

def test_seeded_entity_master_workbook_matches_system_of_record(client,data_steward_token):
    from pathlib import Path
    sample=Path(__file__).resolve().parents[2]/'sample_data'/'01_Entity_Master.xlsx'
    files={'file':('01_Entity_Master.xlsx',sample.read_bytes(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    r=client.post('/api/v1/master-data/entities/import/preview',headers=auth(data_steward_token),files=files)
    assert r.status_code==200
    d=r.json();assert d['rows']==6;assert d['counts']['NO_CHANGE']==6;assert d['counts']['INVALID']==0
