from __future__ import annotations
import os, hashlib
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from .models import (
    Organization, Workspace, Client, User, Entity, IntercompanyPartner, GLAccount, ProfitCenter, Product,
    Policy, FinancialPeriod, ForecastVersion, ForecastLine, Calculation, Adjustment, ApprovalRequest, ApprovalStep,
    MappingRule, AllocationRule, ExceptionCase, AuditEvent, IntegrationConnection, QualificationControl, EntityVersion, MasterDataRecord, MasterDataVersion
)
from .security import hash_password
from .services.finance import segmented_pnl, true_up_to_target, calculate_policy_result, D
from .services.master_data_catalog import sync_seeded_operational_masters

DEMO_USERS=[
    ('demo.admin@otp.local','Demo-OTP-2026!','PLATFORM_ADMIN'),
    ('analyst@otp.local','Demo-Analyst-2026!','TP_ANALYST'),
    ('manager@otp.local','Demo-Manager-2026!','TP_MANAGER'),
    ('finance@otp.local','Demo-Finance-2026!','FINANCE_CONTROLLER'),
    ('tax.director@otp.local','Demo-Director-2026!','GROUP_TAX_DIRECTOR'),
    ('auditor@otp.local','Demo-Auditor-2026!','AUDITOR'),
    ('local.finance@otp.local','Demo-LocalFinance-2026!','LOCAL_FINANCE'),
    ('data.steward@otp.local','Demo-DataSteward-2026!','MASTER_DATA_STEWARD'),
]

def _get_or_create(db, model, defaults=None, **kwargs):
    obj=db.query(model).filter_by(**kwargs).first()
    if obj: return obj
    data={**kwargs,**(defaults or {})};obj=model(**data);db.add(obj);db.flush();return obj

def seed_demo(db: Session):
    org=_get_or_create(db,Organization,code='DEMO-GROUP',defaults={'name':'OTP Demo Multinational','active':True})
    ws=_get_or_create(db,Workspace,organization_id=org.id,code='DEMO',defaults={'name':'Demo Workspace','active':True})
    client=_get_or_create(db,Client,workspace_id=ws.id,code='DEMO-CLIENT',defaults={'name':'Demo Group','active':True})

    # Backfill any legacy entities before adding missing ones.
    for e in db.query(Entity).all():
        if e.workspace_id is None: e.workspace_id=ws.id
        if e.client_id is None: e.client_id=client.id
    for p in db.query(Policy).all():
        if p.workspace_id is None: p.workspace_id=ws.id
    for f in db.query(FinancialPeriod).all():
        if f.workspace_id is None: f.workspace_id=ws.id
    for c in db.query(Calculation).all():
        if c.workspace_id is None: c.workspace_id=ws.id
    for a in db.query(Adjustment).all():
        if a.workspace_id is None: a.workspace_id=ws.id
    db.flush()

    for email,pw,role in DEMO_USERS:
        u=db.query(User).filter(User.email==email).first()
        if not u:
            db.add(User(workspace_id=ws.id,email=email,password_hash=hash_password(pw),role=role,active=True))
        else:
            u.workspace_id=ws.id
            if u.role=='GROUP_TP_MANAGER' and email=='demo.admin@otp.local': u.role='PLATFORM_ADMIN'
    db.flush()

    ent_specs=[
      ('NL01','Netherlands Principal BV','NL','EUR','Principal','2000','SAP S/4HANA',Decimal('0.258')),
      ('DE01','Germany Distribution GmbH','DE','EUR','Limited-Risk Distributor','1000','SAP S/4HANA',Decimal('0.300')),
      ('FR01','France Distribution SAS','FR','EUR','Limited-Risk Distributor','1100','SAP S/4HANA',Decimal('0.250')),
      ('IT01','Italy Distribution SRL','IT','EUR','Limited-Risk Distributor','1200','Oracle',Decimal('0.240')),
      ('PL01','Poland Manufacturing Sp.z.o.o','PL','PLN','Contract Manufacturer','3000','SAP S/4HANA',Decimal('0.190')),
      ('NL02','Netherlands Shared Services BV','NL','EUR','Shared Services','2100','Dynamics 365',Decimal('0.258')),
    ]
    entities={}
    for code,name,country,ccy,char,co,erp,tax in ent_specs:
        e=db.query(Entity).filter(Entity.workspace_id==ws.id,Entity.entity_code==code).first()
        if not e:
            e=Entity(workspace_id=ws.id,client_id=client.id,entity_code=code,legal_name=name,country=country,tax_jurisdiction=country,currency=ccy,group_currency='EUR',characterization=char,company_code=co,erp_system=erp,tax_rate=tax,customs_territory='EU',active=True,effective_from='2025-01-01')
            db.add(e);db.flush()
        else:
            e.workspace_id=ws.id;e.client_id=client.id;e.erp_system=erp;e.tax_rate=tax
        entities[code]=e
    db.flush()

    # Seed an initial governed Entity Master snapshot. Later changes are applied only
    # through maker-checker EntityChangeRequest approvals.
    for code,e in entities.items():
        if not db.query(EntityVersion).filter(EntityVersion.entity_id==e.id).first():
            snap={'entity_code':e.entity_code,'legal_name':e.legal_name,'country':e.country,'currency':e.currency,'group_currency':e.group_currency,'characterization':e.characterization,'company_code':e.company_code,'erp_system':e.erp_system,'tax_jurisdiction':e.tax_jurisdiction,'tax_rate':float(e.tax_rate) if e.tax_rate is not None else None,'customs_territory':e.customs_territory,'effective_from':e.effective_from,'effective_to':e.effective_to,'active':bool(e.active)}
            db.add(EntityVersion(workspace_id=ws.id,entity_id=e.id,version_no=1,snapshot=snap,effective_from=e.effective_from,effective_to=e.effective_to,approved_by='system@otp.local',approval_request_code='DEMO-SEED'))
    db.flush()

    for code,e in entities.items():
        _get_or_create(db,IntercompanyPartner,workspace_id=ws.id,partner_code=f'TP-{code}',defaults={'entity_id':e.id,'trading_partner_code':code,'country':e.country,'relationship_type':'RELATED_PARTY','effective_from':'2025-01-01'})

    gls=[
        ('400100','External Product Revenue','REVENUE',True,False,False),
        ('410100','Service Revenue','REVENUE',True,False,False),
        ('500100','Intercompany Product Purchases','COGS',True,False,False),
        ('510100','Direct Manufacturing Costs','COGS',True,True,True),
        ('610100','Personnel','OPEX',True,True,True),
        ('620100','Marketing','OPEX',True,True,True),
        ('630100','IT','OPEX',True,True,True),
        ('640100','Professional Fees','OPEX',True,True,True),
        ('650100','Depreciation','OPEX',True,True,True),
        ('680500','Shareholder Activities','OPEX',False,False,False),
    ]
    for code,desc,cls,op,cp,alloc in gls:
        _get_or_create(db,GLAccount,workspace_id=ws.id,account_code=code,defaults={'description':desc,'classification':cls,'operating':op,'pli_included':op,'cost_plus_eligible':cp,'allocation_eligible':alloc,'exceptional_item':False,'pass_through':False,'effective_from':'2025-01-01'})

    for code,e in entities.items():
        _get_or_create(db,ProfitCenter,workspace_id=ws.id,code=f'{code}-CORE',defaults={'entity_id':e.id,'function':e.characterization,'business_unit':'Core','geography':e.country})
    for i in range(1,21):
        _get_or_create(db,Product,workspace_id=ws.id,sku=f'SKU-{i:04d}',defaults={'product_group':'Finished Goods' if i<=15 else 'Services','entity_id':entities['NL01'].id,'standard_cost':Decimal('70')+i,'currency':'EUR'})
    # RC.1 extends maker-checker/versioned governance beyond legal entities.
    # Existing operational masters are mirrored into the governed catalog and
    # remain synchronized only when an approved change is applied.
    sync_seeded_operational_masters(db,ws.id)

    # Governed workflow and journal-template defaults use the same master-data records as user-created configuration.
    governed_defaults=[
        ('WORKFLOW_DEFINITIONS','WF-TRUEUP-HIGH','High-value True-Up Approval',{'object_type':'TRUE_UP','condition_expression':'amount > 500000','approval_mode':'SEQUENTIAL','approver_roles':'TP_MANAGER,FINANCE_CONTROLLER,GROUP_TAX_DIRECTOR','sla_hours':48,'escalation_role':'GROUP_TAX_DIRECTOR','allow_delegation':True,'prevent_self_approval':True}),
        ('JOURNAL_TEMPLATES','JT-TP-DEFAULT','Default TP True-Up Journal',{'company_code':'','ledger':'0L','document_type':'TP','currency':'','positive_debit_gl':'140900','positive_credit_gl':'499900','negative_debit_gl':'699900','negative_credit_gl':'240900','trading_partner':'TP-NL01','profit_center_template':'{entity_code}-CORE','tax_code':'','positive_text':'Transfer pricing true-up income','negative_text':'Transfer pricing true-up expense'}),
    ]
    for domain,code,name,attrs in governed_defaults:
        row=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==ws.id,MasterDataRecord.domain==domain,MasterDataRecord.record_code==code).first()
        if not row:
            row=MasterDataRecord(workspace_id=ws.id,domain=domain,record_code=code,name=name,attributes=attrs,active=True,effective_from='2026-01-01',version_no=1,approved_by='system@otp.local',approval_request_code='DEMO-SEED')
            db.add(row);db.flush();db.add(MasterDataVersion(workspace_id=ws.id,domain=domain,record_code=code,version_no=1,snapshot={'record_code':code,'name':name,'attributes':attrs,'active':True,'effective_from':'2026-01-01'},approved_by='system@otp.local',approval_request_code='DEMO-SEED'))

    policy_specs={
      'DE01':('TNMM','ROS',Decimal('0.04'),Decimal('0.03'),Decimal('0.04'),Decimal('0.05'),None,'TP-NL01','DISTRIBUTION'),
      'FR01':('TNMM','ROS',Decimal('0.04'),Decimal('0.03'),Decimal('0.04'),Decimal('0.05'),None,'TP-NL01','DISTRIBUTION'),
      'IT01':('TNMM','ROS',Decimal('0.04'),Decimal('0.03'),Decimal('0.04'),Decimal('0.05'),None,'TP-NL01','DISTRIBUTION'),
      'PL01':('TNMM','EBIT/TC',Decimal('0.07'),Decimal('0.05'),Decimal('0.07'),Decimal('0.09'),None,'TP-NL01','CONTRACT_MANUFACTURING'),
      'NL02':('COST_PLUS','COST_PLUS',Decimal('0.05'),Decimal('0.04'),Decimal('0.05'),Decimal('0.07'),Decimal('0.05'),'TP-DE01','SHARED_SERVICES'),
    }
    policies={}
    for code,s in policy_specs.items():
        method,pli,target,low,median,high,markup,cp,tt=s
        pol=db.query(Policy).filter(Policy.workspace_id==ws.id,Policy.policy_code==f'POL-{code}-001').order_by(Policy.id.desc()).first()
        if not pol:
            pol=Policy(workspace_id=ws.id,policy_code=f'POL-{code}-001',entity_id=entities[code].id,counterparty_code=cp,transaction_type=tt,method=method,pli=pli,target=target,lower_bound=low,median=median,upper_bound=high,markup=markup,benchmark_id=f'BENCH-{code}-2026',version='2.0',status='ACTIVE',effective_from='2026-01-01',true_up_frequency='QUARTERLY',materiality_threshold=Decimal('50000'),approval_matrix={'steps':['TP_MANAGER','FINANCE_CONTROLLER','GROUP_TAX_DIRECTOR'] if code=='DE01' else ['TP_MANAGER','FINANCE_CONTROLLER']},document_references=[f'{code}_Local_File_Extract.pdf','Global_TP_Policy.pdf'])
            db.add(pol);db.flush()
        else:
            pol.workspace_id=ws.id;pol.median=median;pol.markup=markup;pol.counterparty_code=cp;pol.transaction_type=tt;pol.approval_matrix={'steps':['TP_MANAGER','FINANCE_CONTROLLER','GROUP_TAX_DIRECTOR'] if code=='DE01' else ['TP_MANAGER','FINANCE_CONTROLLER']}
        policies[code]=pol

    # YTD values through September 2026. DE01 gives exact 2.31% ROS and EUR 1,891,110 target true-up.
    cfg={
      'DE01':(Decimal('111900000'),Decimal('80000000'),Decimal('29315110')),
      'FR01':(Decimal('90000000'),Decimal('63000000'),Decimal('23400000')),
      'IT01':(Decimal('76000000'),Decimal('55000000'),Decimal('18710000')),
      'PL01':(Decimal('62000000'),Decimal('40000000'),Decimal('17700000')),
      'NL02':(Decimal('30000000'),Decimal('8000000'),Decimal('20500000')),
    }
    for code,(rev,cogs,opex) in cfg.items():
        fp=db.query(FinancialPeriod).filter(FinancialPeriod.entity_id==entities[code].id,FinancialPeriod.period=='2026-09').first()
        if not fp:
            fp=FinancialPeriod(workspace_id=ws.id,entity_id=entities[code].id,period='2026-09',revenue=rev,cogs=cogs,opex=opex,source_import_id='DEMO-ERP-2026-09')
            db.add(fp);db.flush()
        else:
            fp.workspace_id=ws.id;fp.revenue=rev;fp.cogs=cogs;fp.opex=opex
        pol=policies[code]
        res=calculate_policy_result(pol.method,pol.pli,revenue=rev,cogs=cogs,opex=opex,target=pol.target,lower=pol.lower_bound,upper=pol.upper_bound,eligible_costs=(cogs+opex if pol.method=='COST_PLUS' else None))
        calc=db.query(Calculation).filter(Calculation.calculation_code==f'CALC-{code}-2026-09').first()
        source_hash=hashlib.sha256(f'{code}-{rev}-{cogs}-{opex}-v2'.encode()).hexdigest()
        manifest={'workspace_id':ws.id,'policy_code':pol.policy_code,'policy_version':pol.version,'benchmark_id':pol.benchmark_id,'source_import':'DEMO-ERP-2026-09','rounding':'ROUND_HALF_UP','money_precision':'0.01','ratio_precision':'0.00000001','engine_version':'otp-engine-2.4.0-rc.3'}
        if not calc:
            calc=Calculation(workspace_id=ws.id,calculation_code=f'CALC-{code}-2026-09',entity_id=entities[code].id,policy_id=pol.id,period='2026-09',revenue=rev,ebit=segmented_pnl(rev,cogs,opex).ebit,actual_pli=res.actual,target_pli=res.target,suggested_adjustment=res.adjustment if res.status=='RED' else Decimal('0'),engine_version='otp-engine-2.4.0-rc.3',source_hash=source_hash,manifest=manifest,finalized=True)
            db.add(calc);db.flush()
        else:
            calc.workspace_id=ws.id;calc.revenue=rev;calc.ebit=segmented_pnl(rev,cogs,opex).ebit;calc.actual_pli=res.actual;calc.target_pli=res.target;calc.suggested_adjustment=res.adjustment if res.status=='RED' else Decimal('0');calc.engine_version='otp-engine-2.4.0-rc.3';calc.source_hash=source_hash;calc.manifest=manifest
        if code=='DE01':
            adj=db.query(Adjustment).filter(Adjustment.adjustment_code=='ADJ-DE01-2026-001').first()
            amount=true_up_to_target(rev,segmented_pnl(rev,cogs,opex).ebit,Decimal('0.04'))
            if not adj:
                adj=Adjustment(workspace_id=ws.id,adjustment_code='ADJ-DE01-2026-001',calculation_id=calc.id,entity_id=entities[code].id,amount=amount,currency='EUR',status='PROPOSED',version=1,materiality=Decimal('50000'))
                db.add(adj);db.flush()
            else:
                adj.workspace_id=ws.id;adj.currency='EUR';adj.amount=amount

    fv=_get_or_create(db,ForecastVersion,workspace_id=ws.id,version_code='LE2-2026',defaults={'scenario':'LATEST_ESTIMATE','fiscal_year':2026,'status':'APPROVED','approved_by':'manager@otp.local'})
    # Oct-Dec forecast monthly data. Combined with YTD aggregate creates full-year forecast.
    forecast_monthly={
        'DE01':[(10,Decimal('13500000'),Decimal('9700000'),Decimal('3500000')),(11,Decimal('13700000'),Decimal('9850000'),Decimal('3560000')),(12,Decimal('14800000'),Decimal('10600000'),Decimal('3850000'))],
        'FR01':[(10,Decimal('10500000'),Decimal('7350000'),Decimal('2700000')),(11,Decimal('11000000'),Decimal('7700000'),Decimal('2800000')),(12,Decimal('12000000'),Decimal('8400000'),Decimal('3000000'))],
        'IT01':[(10,Decimal('9000000'),Decimal('6500000'),Decimal('2200000')),(11,Decimal('9200000'),Decimal('6650000'),Decimal('2250000')),(12,Decimal('9800000'),Decimal('7100000'),Decimal('2350000'))],
        'PL01':[(10,Decimal('7200000'),Decimal('4600000'),Decimal('2050000')),(11,Decimal('7300000'),Decimal('4650000'),Decimal('2080000')),(12,Decimal('7600000'),Decimal('4850000'),Decimal('2150000'))],
        'NL02':[(10,Decimal('3500000'),Decimal('900000'),Decimal('2400000')),(11,Decimal('3500000'),Decimal('900000'),Decimal('2400000')),(12,Decimal('4000000'),Decimal('1000000'),Decimal('2700000'))],
    }
    for code,lines in forecast_monthly.items():
        for m,rev,cogs,opex in lines:
            if not db.query(ForecastLine).filter(ForecastLine.forecast_version_id==fv.id,ForecastLine.entity_id==entities[code].id,ForecastLine.month==m).first():
                db.add(ForecastLine(forecast_version_id=fv.id,entity_id=entities[code].id,month=m,revenue=rev,cogs=cogs,opex=opex,currency=entities[code].currency))

    # Approved YTD budget baseline used for deterministic variance decomposition.
    budget=_get_or_create(db,ForecastVersion,workspace_id=ws.id,version_code='BUDGET-2026',defaults={'scenario':'BUDGET','fiscal_year':2026,'status':'APPROVED','approved_by':'finance@otp.local'})
    budget_ytd={
        'DE01':(Decimal('110000000'),Decimal('78000000'),Decimal('27600000')),
        'FR01':(Decimal('88000000'),Decimal('61600000'),Decimal('22880000')),
        'IT01':(Decimal('75000000'),Decimal('54000000'),Decimal('18000000')),
        'PL01':(Decimal('61000000'),Decimal('39000000'),Decimal('18000000')),
        'NL02':(Decimal('29400000'),Decimal('8000000'),Decimal('20000000')),
    }
    def split9(total):
        base=(total/Decimal('9')).quantize(Decimal('0.01'))
        return [base]*8+[total-base*8]
    for code,(trev,tcogs,topex) in budget_ytd.items():
        revs,cogss,opexs=split9(trev),split9(tcogs),split9(topex)
        for m in range(1,10):
            if not db.query(ForecastLine).filter(ForecastLine.forecast_version_id==budget.id,ForecastLine.entity_id==entities[code].id,ForecastLine.month==m).first():
                db.add(ForecastLine(forecast_version_id=budget.id,entity_id=entities[code].id,month=m,revenue=revs[m-1],cogs=cogss[m-1],opex=opexs[m-1],currency=entities[code].currency))

    # Evidence-based qualification center. Internal controls may be proven by automated evidence; external controls are never self-certified.
    qualification_specs=[
        ('Q-TP-DECIMAL','TP Calculation','Fixed-precision monetary arithmetic','AUTOMATED','All authoritative monetary calculations use Decimal/fixed precision.','PASS',{'evidence':'backend/app/services/finance.py'}),
        ('Q-TP-GOLDEN','TP Calculation','Golden TP regression suite','AUTOMATED','Critical TP methods and edge cases must pass deterministic golden tests.','PASS',{'evidence':'backend/tests + docs/TEST_REPORT.md'}),
        ('Q-DATA-INGEST','Data','Controlled ERP/file ingestion','AUTOMATED','Source hashes, row validation and control totals must reconcile.','PASS',{'evidence':'backend/app/services/ingestion.py'}),
        ('Q-DATA-PNL','Data','Imported-data authoritative P&L','AUTOMATED','Mapped imported records must rebuild controlled P&L and publish calculation lineage.','PASS',{'evidence':'backend/app/services/pnl_builder.py'}),
        ('Q-MD-ENTITY','Master Data','Governed Legal Entity Master','AUTOMATED','Entity create/edit/deactivate/reactivate changes require versioned maker-checker approval and retain immutable history.','PASS',{'evidence':'backend/app/services/entity_master.py + backend/tests/test_entity_master.py'}),
        ('Q-MD-CATALOG','Master Data','Governed Enterprise Master Catalog','AUTOMATED','Partner, GL, cost/profit center, plant, BU, product, customer/vendor, currency, FX, transaction and TP segment changes require maker-checker approval and immutable versions.','PASS',{'evidence':'backend/app/services/master_data_catalog.py + backend/tests/test_master_data_catalog.py'}),
        ('Q-AN-VARIANCE','Analytics','Deterministic EBIT variance bridge','AUTOMATED','Variance components must reconcile to total EBIT variance within tolerance.','PASS',{'evidence':'backend/app/services/variance.py'}),
        ('Q-GOV-SOD','Governance','Segregation of duties','AUTOMATED','Material adjustment approval must prevent self-approval and enforce configured roles.','PASS',{'evidence':'backend/tests/test_api.py'}),
        ('Q-ERP-IDEMP','ERP','Posting idempotency','AUTOMATED','Repeated posting requests must not create duplicate ERP documents.','PASS',{'evidence':'backend/app/services/erp.py'}),
        ('Q-SEC-AUTH','Security','Role and entity authorization','AUTOMATED','Protected actions require role permission and entity scope.','PASS',{'evidence':'backend/app/security.py'}),
        ('Q-LIVE-SAP','ERP','Live SAP S/4 sandbox qualification','EXTERNAL','Connector must be certified against an authorized live SAP sandbox.','PENDING',{'required':'Real SAP S/4 credentials and sandbox'}),
        ('Q-PENTEST','Security','Independent penetration test','EXTERNAL','Independent penetration test must have zero unresolved Critical/High findings.','EXTERNAL_REQUIRED',{'required':'Independent security provider'}),
        ('Q-IDP','Security','Enterprise IdP validation','EXTERNAL','Validate OIDC/SAML with customer Microsoft Entra ID or Okta tenant.','PENDING',{'required':'Customer IdP tenant'}),
        ('Q-TP-SIGNOFF','TP Governance','Independent TP professional sign-off','EXTERNAL','Supported methods, policies and golden cases require independent professional review.','PENDING',{'required':'Qualified TP reviewer'}),
        ('Q-FIN-UAT','Finance','Finance user acceptance testing','EXTERNAL','Finance users must approve journals, reconciliations and accounting controls.','PENDING',{'required':'Customer Finance UAT'}),
        ('Q-PARALLEL','Operations','Parallel close validation','EXTERNAL','Run at least two controlled parallel closes against the trusted process.','PENDING',{'required':'Customer close cycles'}),
        ('Q-DR','Operations','Production disaster recovery exercise','EXTERNAL','RPO/RTO targets require restore/failover exercise on target infrastructure.','PENDING',{'required':'Production-like infrastructure'}),
    ]
    for code,domain,title,ctype,requirement,status,evidence in qualification_specs:
        q=db.query(QualificationControl).filter(QualificationControl.workspace_id==ws.id,QualificationControl.control_code==code).first()
        if not q:
            db.add(QualificationControl(workspace_id=ws.id,control_code=code,domain=domain,title=title,control_type=ctype,requirement=requirement,status=status,evidence=evidence,reviewer='system' if ctype!='EXTERNAL' else None,blocking=True))
        else:
            q.domain=domain;q.title=title;q.control_type=ctype;q.requirement=requirement;q.status=status;q.evidence=evidence

    # Mapping rules used by imported demo GL records.
    mapping_specs=[
        ('MAP-DE-DIST',10,{'entity_code':'DE01'},'DE01-DIST','DE01-NL01-DIST','POL-DE01-001'),
        ('MAP-FR-DIST',10,{'entity_code':'FR01'},'FR01-DIST','FR01-NL01-DIST','POL-FR01-001'),
        ('MAP-IT-DIST',10,{'entity_code':'IT01'},'IT01-DIST','IT01-NL01-DIST','POL-IT01-001'),
        ('MAP-PL-MFG',10,{'entity_code':'PL01'},'PL01-MFG','PL01-NL01-MFG','POL-PL01-001'),
        ('MAP-NL-SVC',10,{'entity_code':'NL02'},'NL02-SVC','NL02-GROUP-SVC','POL-NL02-001'),
    ]
    for code,priority,match,segment,txn,policy in mapping_specs:
        if not db.query(MappingRule).filter(MappingRule.workspace_id==ws.id,MappingRule.rule_code==code,MappingRule.version==1).first():
            db.add(MappingRule(workspace_id=ws.id,rule_code=code,version=1,priority=priority,match_fields=match,segment_code=segment,controlled_transaction_code=txn,policy_code=policy,status='ACTIVE',approved_by='manager@otp.local'))

    if not db.query(AllocationRule).filter(AllocationRule.workspace_id==ws.id,AllocationRule.rule_code=='ALLOC-HQ-IT-001').first():
        db.add(AllocationRule(workspace_id=ws.id,rule_code='ALLOC-HQ-IT-001',version=1,sender_segment='NL02-SVC',cost_pool_name='Group IT',cost_pool_type='IT',sender_entity_code='NL02',period_scope='MONTHLY',currency='EUR',source_accounts=['630100'],source_amount_source='MANUAL_CONTROLLED',manual_amount_allowed=True,driver_type='USERS',driver_source='MANUAL_CONTROLLED',recipients={'DE01-DIST':450,'FR01-DIST':300,'IT01-DIST':250},recipient_rules={'DE01-DIST':{'included':True},'FR01-DIST':{'included':True},'IT01-DIST':{'included':True}},exclusions=[{'category':'SHAREHOLDER_ACTIVITY','reason':'Non-beneficial shareholder cost','approval_required':True}],markup_eligible=True,markup_treatment='MARKUP_ELIGIBLE',markup_rate=Decimal('0.05'),fx_methodology='GROUP_MONTHLY_AVERAGE',fx_version='DEMO-2026-09',effective_from='2026-01-01',status='ACTIVE',created_by='analyst@otp.local',approved_by='manager@otp.local'))

    _get_or_create(db,IntegrationConnection,workspace_id=ws.id,connection_code='SAP-S4-SIM',defaults={'connector_type':'SAP_S4_SIMULATOR','config':{'live':False,'purpose':'contract testing and demo'},'secret_reference':None,'status':'CONFIGURED'})
    _get_or_create(db,IntegrationConnection,workspace_id=ws.id,connection_code='SAP-S4-PROD-CONTRACT',defaults={'connector_type':'SAP_S4','config':{'live':True,'qualification':'PENDING'},'secret_reference':'vault://sap-s4/credentials','status':'UNQUALIFIED'})

    if not db.query(ExceptionCase).filter(ExceptionCase.exception_code=='EXC-DE01-FORECAST-001').first():
        db.add(ExceptionCase(workspace_id=ws.id,exception_code='EXC-DE01-FORECAST-001',entity_id=entities['DE01'].id,category='FORECAST_BREACH',severity='HIGH',amount=Decimal('1891110'),owner='manager@otp.local',due_date='2026-09-30',status='OPEN',evidence={'calculation':'CALC-DE01-2026-09','policy':'POL-DE01-001'}))

    if not db.query(AuditEvent).filter(AuditEvent.event_type=='DEMO_ENTERPRISE_SEEDED').first():
        db.add(AuditEvent(workspace_id=ws.id,event_type='DEMO_ENTERPRISE_SEEDED',actor='system',actor_role='SYSTEM',details='Enterprise RC synthetic multinational demo initialized',source_system='SEEDER'))
    db.commit()
