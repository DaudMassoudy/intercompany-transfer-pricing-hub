from __future__ import annotations

from decimal import Decimal
import io

import pytest

from app.db import SessionLocal
from app.seed import seed_demo
from app.models import (
    Workspace, Entity, AllocationRule, MappingRule, RawFinancialRecord,
    NormalizedFinancialRecord, SourceImport,
)
from app.services.ingestion import validate_and_store, sha256_bytes
from app.services.mapping import choose_rule, detect_conflicts, run_mapping
from app.services.allocations import run_allocation
from app.services.forecasting import entity_forecast
from app.services.erp import SimulatedSAPConnector, SAPS4ConnectorContract
from app.settings import Settings


@pytest.fixture()
def db_session():
    db = SessionLocal()
    seed_demo(db)
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def _ws(db):
    return db.query(Workspace).filter(Workspace.code == 'DEMO').one()


def test_ingestion_validation_and_control_totals(db_session):
    ws = _ws(db_session)
    csv = ("Period,Entity_ID,Company_Code,Document_Number,GL_Account,Cost_Center,Profit_Center,IC_Partner_ID,Currency,Amount,Debit_Credit\n"
           "2026-09,DE01,1000,DOC-1,400100,DE01-OPS,DE01-CORE,TP-NL01,EUR,100.00,CREDIT\n"
           "2026-09,DE01,1000,DOC-2,500100,DE01-OPS,DE01-CORE,TP-UNKNOWN,EUR,-60.00,DEBIT\n"
           "2026-09,DE01,1000,DOC-3,999999,DE01-OPS,DE01-CORE,TP-NL01,EUR,-10.00,DEBIT\n").encode()
    out = validate_and_store(
        db_session, workspace_id=ws.id, actor='tester', source_system='CSV',
        period='2026-09', filename='gl.csv', data=csv
    )
    assert out['status'] == 'PARTIAL'
    assert out['row_count'] == 3
    assert out['accepted_rows'] == 2
    assert out['rejected_rows'] == 1
    assert out['warning_rows'] == 1
    assert Decimal(str(out['source_control_total'])) == Decimal('30.0')
    assert Decimal(str(out['imported_control_total'])) == Decimal('40.0')
    assert out['sha256'] == sha256_bytes(csv)

    mapped = run_mapping(db_session, ws.id, out['import_id'])
    assert mapped['total'] == 2
    assert mapped['mapped'] == 2
    assert mapped['unresolved'] == 0
    assert mapped['coverage'] == 1


def test_ingestion_missing_columns_and_unsupported_type(db_session):
    ws = _ws(db_session)
    bad = b"Entity_ID,Amount\nDE01,1\n"
    out = validate_and_store(db_session, workspace_id=ws.id, actor='tester', source_system='CSV', period='2026-09', filename='bad.csv', data=bad)
    assert out['status'] == 'FAILED'
    assert 'Period' in out['missing_columns']
    out2 = validate_and_store(db_session, workspace_id=ws.id, actor='tester', source_system='TXT', period='2026-09', filename='bad.txt', data=b'x')
    assert out2['status'] == 'FAILED'
    assert 'Only CSV and XLSX' in out2['error']


def test_mapping_priority_and_conflict_detection():
    r = RawFinancialRecord(entity_code='DE01', gl_account='400100', period='2026-09', currency='EUR', amount=Decimal('1'), workspace_id=1, source_import_id=1, row_number=1, validation_status='VALID')
    a = MappingRule(id=1, workspace_id=1, rule_code='A', version=1, priority=20, match_fields={'entity_code':'DE01'}, segment_code='SEG-A', controlled_transaction_code='TX-A', policy_code='POL-A', status='ACTIVE')
    b = MappingRule(id=2, workspace_id=1, rule_code='B', version=1, priority=10, match_fields={'entity_code':'DE01'}, segment_code='SEG-B', controlled_transaction_code='TX-B', policy_code='POL-B', status='ACTIVE')
    assert choose_rule(r, [a,b]).rule_code == 'B'
    c = MappingRule(id=3, workspace_id=1, rule_code='C', version=1, priority=10, match_fields={'entity_code':'DE01'}, segment_code='OTHER', controlled_transaction_code='TX-C', policy_code='POL-C', status='ACTIVE')
    conflicts = detect_conflicts([b,c])
    assert len(conflicts) == 1
    assert conflicts[0]['priority'] == 10


def test_allocation_run_reconciles(db_session):
    ws = _ws(db_session)
    rule = db_session.query(AllocationRule).filter(AllocationRule.workspace_id==ws.id, AllocationRule.rule_code=='ALLOC-HQ-IT-001').one()
    out = run_allocation(db_session, rule, '2026-09', Decimal('9450000'), {'DE01-DIST':450, 'FR01-DIST':300, 'IT01-DIST':250})
    assert out['status'] == 'COMPLETED'
    assert Decimal(str(out['residual'])) == Decimal('0.0')
    assert Decimal(str(out['allocated_amount'])) == Decimal('9450000.0')
    assert len(out['results']) == 3


def test_forecast_is_computed_from_ytd_and_remaining_months(db_session):
    de = db_session.query(Entity).filter(Entity.entity_code=='DE01').one()
    out = entity_forecast(db_session, de, 2026)
    assert out['available'] is True
    assert out['version_code'] == 'LE2-2026'
    assert out['pnl']['revenue'] > 111_900_000
    assert len(out['months']) == 3


def test_simulated_erp_connector_is_deterministic_and_explicitly_not_live():
    c = SimulatedSAPConnector()
    assert c.health_check()['live'] is False
    a = c.submit_journal({'amount':'123.45','company_code':'1000','currency':'EUR'}, 'same-key')
    b = c.submit_journal({'amount':'123.45','company_code':'1000','currency':'EUR'}, 'same-key')
    assert a.document_number == b.document_number
    assert a.posted_amount == Decimal('123.45')
    reject = c.submit_journal({'amount':'123.45','simulate_rejection':True}, 'reject-key')
    assert reject.status == 'REJECTED'
    assert c.get_posting_status(a.document_number)['status'] == 'POSTED'
    assert c.reverse_posting(a.document_number, 'test')['status'] == 'REVERSED'


def test_live_sap_contract_cannot_masquerade_as_qualified():
    c = SAPS4ConnectorContract(base_url='https://example.invalid')
    health = c.health_check()
    assert health['qualification'] == 'PENDING'
    with pytest.raises(RuntimeError, match='LIVE ERP SANDBOX QUALIFICATION = PENDING'):
        c.submit_journal({}, 'x')


def test_production_settings_reject_placeholder_secrets():
    with pytest.raises(Exception):
        Settings(environment='production', demo_mode=False, jwt_secret='SET_IN_SECRET_MANAGER', n8n_integration_key='SET_IN_SECRET_MANAGER', cors_origins='https://otp.example.com')
    s = Settings(environment='production', demo_mode=False, jwt_secret='a'*40, n8n_integration_key='b'*40, cors_origins='https://otp.example.com')
    assert s.environment == 'production'

from app.services.pnl_builder import build_authoritative_pnl
from app.services.variance import run_variance
from app.services.qualification import qualification_summary


def test_imported_data_builds_authoritative_pnl_and_lineage(db_session):
    ws=_ws(db_session)
    csv=("Period,Entity_ID,Company_Code,Document_Number,GL_Account,Cost_Center,Profit_Center,IC_Partner_ID,Currency,Amount,Debit_Credit\n"
         "2026-09,DE01,1000,PNL-REV,400100,DE01-OPS,DE01-CORE,TP-NL01,EUR,100.00,CREDIT\n"
         "2026-09,DE01,1000,PNL-COGS,500100,DE01-OPS,DE01-CORE,TP-NL01,EUR,-60.00,DEBIT\n"
         "2026-09,DE01,1000,PNL-OPEX,610100,DE01-OPS,DE01-CORE,TP-NL01,EUR,-30.00,DEBIT\n").encode()
    imp=validate_and_store(db_session,workspace_id=ws.id,actor='tester',source_system='CSV',period='2026-09',filename='authoritative.csv',data=csv)
    assert imp['accepted_rows']==3 and imp['rejected_rows']==0
    mapped=run_mapping(db_session,ws.id,imp['import_id']);assert mapped['coverage']==1
    ar=db_session.query(AllocationRule).filter(AllocationRule.workspace_id==ws.id,AllocationRule.rule_code=='ALLOC-HQ-IT-001').one()
    run_allocation(db_session,ar,'2026-09',Decimal('0'),{'DE01-DIST':450,'FR01-DIST':300,'IT01-DIST':250})
    result=build_authoritative_pnl(db_session,workspace_id=ws.id,as_of_period='2026-09',created_by='tester',source_import_ids=[imp['import_id']],publish=True)
    assert result['source_rows']==3
    assert result['mapped_rows']==3
    assert result['control_difference']==0
    de=result['entities'][0]
    assert de['entity_code']=='DE01'
    assert de['revenue']==100.0
    assert de['cogs']==60.0
    assert de['opex']==30.0
    assert de['ebit']==10.0
    assert round(de['pli'],4)==0.1
    assert result['segments'][0]['rows']==3
    assert len(result['source_hash'])==64


def test_variance_bridge_reconciles_exactly(db_session):
    ws=_ws(db_session)
    result=run_variance(db_session,workspace_id=ws.id,entity_code='DE01',actual_period='2026-09',baseline_type='BUDGET',created_by='tester')
    assert result['status']=='CONTROLLED'
    assert Decimal(str(result['residual']))==Decimal('0.0')
    assert Decimal(str(result['component_total']))==Decimal(str(result['ebit_variance']))
    assert {x['code'] for x in result['components']}=={'REVENUE','COGS','DIRECT_OPEX','ALLOCATIONS'}


def test_qualification_center_separates_internal_and_external_evidence(db_session):
    ws=_ws(db_session)
    q=qualification_summary(db_session,ws.id)
    assert q['classification']=='ENTERPRISE_PRODUCTION_RELEASE_CANDIDATE'
    assert q['internal_score_pct']==100.0
    assert q['external_blocking_remaining']>=1
    assert any(x['control_code']=='Q-LIVE-SAP' and x['control_type']=='EXTERNAL' for x in q['controls'])
