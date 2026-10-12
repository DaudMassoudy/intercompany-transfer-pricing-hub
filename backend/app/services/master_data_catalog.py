from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any
import uuid

import pandas as pd
from sqlalchemy.orm import Session

from ..models import (
    Entity, GLAccount, IntercompanyPartner, MasterDataChangeRequest, MasterDataRecord,
    MasterDataVersion, Product, ProfitCenter, User, MappingRule, AllocationRule,
)
from ..timeutil import utcnow_naive


MASTER_DOMAIN_DEFINITIONS: dict[str, dict[str, Any]] = {
    'INTERCOMPANY_PARTNERS': {
        'label': 'Intercompany Partners', 'code_label': 'Partner Code', 'name_label': 'Partner Name',
        'fields': {
            'entity_code': {'type': 'string'}, 'trading_partner_code': {'type': 'string'},
            'vendor_code': {'type': 'string'}, 'customer_code': {'type': 'string'},
            'country': {'type': 'country'}, 'relationship_type': {'type': 'string', 'default': 'RELATED_PARTY'},
        },
    },
    'GL_ACCOUNTS': {
        'label': 'GL Accounts', 'code_label': 'Account Code', 'name_label': 'Description',
        'fields': {
            'classification': {'type': 'choice', 'choices': ['REVENUE','COGS','OPEX','OTHER'], 'required': True},
            'operating': {'type': 'boolean', 'default': True}, 'pli_included': {'type': 'boolean', 'default': True},
            'cost_plus_eligible': {'type': 'boolean', 'default': False}, 'allocation_eligible': {'type': 'boolean', 'default': False},
            'exceptional_item': {'type': 'boolean', 'default': False}, 'pass_through': {'type': 'boolean', 'default': False},
        },
    },
    'COST_CENTERS': {
        'label': 'Cost Centers', 'code_label': 'Cost Center', 'name_label': 'Name',
        'fields': {'entity_code': {'type':'entity','required':True}, 'function': {'type':'string'}, 'business_unit': {'type':'string'}},
    },
    'PROFIT_CENTERS': {
        'label': 'Profit Centers', 'code_label': 'Profit Center', 'name_label': 'Name',
        'fields': {'entity_code': {'type':'entity','required':True}, 'function': {'type':'string'}, 'business_unit': {'type':'string'}, 'geography': {'type':'string'}},
    },
    'PLANTS': {
        'label': 'Plants', 'code_label': 'Plant', 'name_label': 'Plant Name',
        'fields': {'entity_code': {'type':'entity','required':True}, 'country': {'type':'country'}, 'location': {'type':'string'}},
    },
    'BUSINESS_UNITS': {
        'label': 'Business Units', 'code_label': 'Business Unit', 'name_label': 'Name',
        'fields': {'entity_code': {'type':'entity'}, 'description': {'type':'string'}},
    },
    'PRODUCT_GROUPS': {
        'label': 'Product Groups', 'code_label': 'Product Group', 'name_label': 'Name',
        'fields': {'entity_code': {'type':'entity'}, 'description': {'type':'string'}},
    },
    'PRODUCTS': {
        'label': 'Products / SKUs', 'code_label': 'SKU', 'name_label': 'Product Name',
        'fields': {'product_group': {'type':'string'}, 'entity_code': {'type':'entity'}, 'standard_cost': {'type':'number'}, 'currency': {'type':'currency'}},
    },
    'CUSTOMERS': {
        'label': 'Customers', 'code_label': 'Customer', 'name_label': 'Customer Name',
        'fields': {'entity_code': {'type':'entity'}, 'country': {'type':'country'}, 'external': {'type':'boolean','default':True}},
    },
    'VENDORS': {
        'label': 'Vendors', 'code_label': 'Vendor', 'name_label': 'Vendor Name',
        'fields': {'entity_code': {'type':'entity'}, 'country': {'type':'country'}, 'related_party': {'type':'boolean','default':False}},
    },
    'CURRENCIES': {
        'label': 'Currencies', 'code_label': 'ISO Currency', 'name_label': 'Currency Name',
        'fields': {'decimal_places': {'type':'integer','default':2}, 'active_for_posting': {'type':'boolean','default':True}},
    },
    'FX_SOURCES': {
        'label': 'FX Sources', 'code_label': 'FX Source', 'name_label': 'Source Name',
        'fields': {'provider': {'type':'string','required':True}, 'rate_type': {'type':'string','required':True}, 'base_currency': {'type':'currency','default':'EUR'}},
    },
    'TRANSACTION_TYPES': {
        'label': 'Transaction Types', 'code_label': 'Transaction Type', 'name_label': 'Name',
        'fields': {'function': {'type':'string'}, 'description': {'type':'string'}},
    },
    'BENCHMARKS': {
        'label': 'TP Benchmarks', 'code_label': 'Benchmark ID', 'name_label': 'Benchmark Name',
        'fields': {
            'method': {'type':'choice','choices':['TNMM','COST_PLUS','RESALE_PRICE','CUP','PROFIT_SPLIT','ROYALTY','SERVICE_CHARGE'],'required':True},
            'pli': {'type':'string','required':True}, 'minimum': {'type':'number'}, 'q1': {'type':'number'}, 'median': {'type':'number','required':True}, 'q3': {'type':'number'}, 'maximum': {'type':'number'},
            'comparable_count': {'type':'integer'}, 'observation_count': {'type':'integer'}, 'statistics_methodology': {'type':'string'},
            'tested_party': {'type':'string'}, 'geography': {'type':'string'}, 'industry': {'type':'string'},
            'search_period': {'type':'string'}, 'financial_period': {'type':'string'}, 'source': {'type':'string','required':True},
            'database': {'type':'string'}, 'screening_date': {'type':'string'}, 'valid_until': {'type':'string','required':True},
            'refresh_date': {'type':'string'}, 'study_document_code': {'type':'string'},
        },
    },
    'DATA_QUALITY_RULES': {
        'label': 'Data Quality Rules', 'code_label': 'Control Code', 'name_label': 'Control Name',
        'fields': {
            'control_type': {'type':'string','required':True},
            'severity': {'type':'choice','choices':['INFO','WARNING','ERROR','BLOCKING'],'required':True},
            'dimension': {'type':'string'}, 'threshold': {'type':'number'}, 'owner': {'type':'string'},
            'sla_hours': {'type':'integer'}, 'blocking_stage': {'type':'string'}, 'description': {'type':'string'},
        },
    },
    'WORKFLOW_DEFINITIONS': {
        'label': 'Workflow Definitions', 'code_label': 'Workflow Code', 'name_label': 'Workflow Name',
        'fields': {
            'object_type': {'type':'string','required':True}, 'condition_expression': {'type':'string'},
            'min_amount': {'type':'number'}, 'max_amount': {'type':'number'},
            'entities': {'type':'string'}, 'countries': {'type':'string'}, 'methods': {'type':'string'}, 'risk_levels': {'type':'string'},
            'approval_mode': {'type':'choice','choices':['SEQUENTIAL','PARALLEL'],'default':'SEQUENTIAL'},
            'approver_roles': {'type':'role_steps','required':True}, 'sla_hours': {'type':'integer'},
            'escalation_role': {'type':'string'}, 'allow_delegation': {'type':'boolean','default':True},
            'prevent_self_approval': {'type':'boolean','default':True},
        },
    },
    'JOURNAL_TEMPLATES': {
        'label': 'Journal Templates', 'code_label': 'Template Code', 'name_label': 'Template Name',
        'fields': {
            'company_code': {'type':'string'}, 'ledger': {'type':'string','default':'0L'}, 'document_type': {'type':'string','required':True},
            'currency': {'type':'currency'},
            'positive_debit_gl': {'type':'string','required':True}, 'positive_credit_gl': {'type':'string','required':True},
            'negative_debit_gl': {'type':'string','required':True}, 'negative_credit_gl': {'type':'string','required':True},
            'trading_partner': {'type':'string'}, 'profit_center_template': {'type':'string','default':'{entity_code}-CORE'},
            'tax_code': {'type':'string'}, 'positive_text': {'type':'string','default':'Transfer pricing true-up income'},
            'negative_text': {'type':'string','default':'Transfer pricing true-up expense'},
        },
    },
    'TP_SEGMENTS': {
        'label': 'TP Segments', 'code_label': 'Segment Code', 'name_label': 'Segment Name',
        'fields': {
            'entity_code': {'type':'entity'}, 'parent_code': {'type':'string'}, 'hierarchy_level': {'type':'integer','default':1},
            'function': {'type':'string'}, 'partner_code': {'type':'string'}, 'business_unit': {'type':'string'},
            'profit_center': {'type':'string'}, 'product_group': {'type':'string'},
        },
    },
}


def normalize_domain(domain: str) -> str:
    value=(domain or '').strip().upper().replace('-','_').replace(' ','_')
    if value not in MASTER_DOMAIN_DEFINITIONS:
        raise ValueError(f'Unsupported master-data domain: {domain}')
    return value


def domain_catalog() -> list[dict[str, Any]]:
    out=[]
    for code,definition in MASTER_DOMAIN_DEFINITIONS.items():
        out.append({'domain':code,**definition})
    return out


def _bool(v: Any, default: bool=False) -> bool:
    if v is None or (isinstance(v,float) and pd.isna(v)): return default
    if isinstance(v,bool): return v
    return str(v).strip().lower() in {'1','true','yes','y','ja','x'}


def _clean(v: Any) -> Any:
    if v is None: return None
    if isinstance(v,float) and pd.isna(v): return None
    if hasattr(v,'item'):
        try: return v.item()
        except Exception: pass
    return v


def validate_payload(db: Session, workspace_id: int, domain: str, payload: dict[str, Any], *, change_type: str='CREATE') -> dict[str, Any]:
    domain=normalize_domain(domain)
    definition=MASTER_DOMAIN_DEFINITIONS[domain]
    code=str(payload.get('record_code') or '').strip().upper()
    name=str(payload.get('name') or '').strip()
    if not code: raise ValueError('record_code is required')
    if change_type in {'CREATE','UPDATE'} and not name: raise ValueError('name is required')
    attributes=dict(payload.get('attributes') or {})
    fields=definition['fields']
    unknown=set(attributes)-set(fields)
    if unknown: raise ValueError(f"Unsupported fields for {domain}: {', '.join(sorted(unknown))}")
    for field,spec in fields.items():
        if field not in attributes and 'default' in spec: attributes[field]=spec['default']
        if spec.get('required') and (attributes.get(field) is None or str(attributes.get(field)).strip()==''):
            raise ValueError(f'{field} is required')
        value=attributes.get(field)
        if value is None: continue
        kind=spec.get('type')
        if kind=='boolean': attributes[field]=_bool(value,spec.get('default',False))
        elif kind=='integer': attributes[field]=int(value)
        elif kind=='number':
            try: attributes[field]=str(Decimal(str(value)))
            except (InvalidOperation, ValueError): raise ValueError(f'{field} must be numeric')
        elif kind=='country':
            value=str(value).strip().upper()
            if len(value)!=2: raise ValueError(f'{field} must use a two-letter country code')
            attributes[field]=value
        elif kind=='currency':
            value=str(value).strip().upper()
            if len(value)!=3: raise ValueError(f'{field} must use a three-letter currency code')
            attributes[field]=value
        elif kind=='choice':
            value=str(value).strip().upper()
            if value not in spec['choices']: raise ValueError(f"{field} must be one of {', '.join(spec['choices'])}")
            attributes[field]=value
        elif kind=='entity':
            value=str(value).strip().upper()
            if value and not db.query(Entity).filter(Entity.workspace_id==workspace_id,Entity.entity_code==value).first():
                raise ValueError(f'Unknown entity_code: {value}')
            attributes[field]=value
        else: attributes[field]=str(value).strip()
    ef=payload.get('effective_from'); et=payload.get('effective_to')
    if ef and et and str(ef)>str(et): raise ValueError('effective_from cannot be after effective_to')
    return {'record_code':code,'name':name or code,'attributes':attributes,'active':_bool(payload.get('active'),True),'effective_from':ef,'effective_to':et}


def snapshot(record: MasterDataRecord) -> dict[str, Any]:
    return {'record_code':record.record_code,'name':record.name,'attributes':record.attributes or {},'active':bool(record.active),'effective_from':record.effective_from,'effective_to':record.effective_to,'version_no':record.version_no}


def serialize_record(record: MasterDataRecord) -> dict[str, Any]:
    return {'id':record.id,'domain':record.domain,**snapshot(record),'approved_by':record.approved_by,'approval_request_code':record.approval_request_code,'created_at':record.created_at.isoformat() if record.created_at else None,'updated_at':record.updated_at.isoformat() if record.updated_at else None}


def serialize_request(row: MasterDataChangeRequest) -> dict[str, Any]:
    return {'id':row.id,'domain':row.domain,'record_code':row.record_code,'request_code':row.request_code,'change_type':row.change_type,'status':row.status,'payload':row.payload,'reason':row.reason,'batch_code':row.batch_code,'created_by':row.created_by,'submitted_by':row.submitted_by,'reviewed_by':row.reviewed_by,'submitted_at':row.submitted_at.isoformat() if row.submitted_at else None,'reviewed_at':row.reviewed_at.isoformat() if row.reviewed_at else None,'created_at':row.created_at.isoformat() if row.created_at else None}


def create_change_request(db: Session, *, workspace_id: int, user: User, domain: str, change_type: str, payload: dict[str, Any], reason: str|None=None, batch_code: str|None=None) -> MasterDataChangeRequest:
    domain=normalize_domain(domain); change_type=change_type.upper()
    if change_type not in {'CREATE','UPDATE','DEACTIVATE','REACTIVATE'}: raise ValueError('Unsupported change_type')
    normalized=validate_payload(db,workspace_id,domain,payload,change_type=change_type)
    existing=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==workspace_id,MasterDataRecord.domain==domain,MasterDataRecord.record_code==normalized['record_code']).first()
    if change_type=='CREATE' and existing: raise ValueError('Record already exists')
    if change_type!='CREATE' and not existing: raise ValueError('Record not found')
    pending=db.query(MasterDataChangeRequest).filter(MasterDataChangeRequest.workspace_id==workspace_id,MasterDataChangeRequest.domain==domain,MasterDataChangeRequest.record_code==normalized['record_code'],MasterDataChangeRequest.status.in_(['DRAFT','SUBMITTED'])).first()
    if pending: raise ValueError(f'Pending change already exists: {pending.request_code}')
    row=MasterDataChangeRequest(workspace_id=workspace_id,domain=domain,record_code=normalized['record_code'],request_code=f"MDR-{uuid.uuid4().hex[:10].upper()}",change_type=change_type,status='DRAFT',payload=normalized,reason=reason,batch_code=batch_code,created_by=user.email)
    db.add(row);db.flush();return row


def submit_change_request(row: MasterDataChangeRequest, user: User) -> MasterDataChangeRequest:
    if row.status!='DRAFT': raise ValueError('Only DRAFT requests can be submitted')
    if row.created_by!=user.email and user.role not in {'PLATFORM_ADMIN','MASTER_DATA_STEWARD','GROUP_TAX_DIRECTOR','HEAD_OF_TP'}:
        raise PermissionError('Only the creator or an authorized master-data role can submit this request')
    row.status='SUBMITTED';row.submitted_by=user.email;row.submitted_at=utcnow_naive();return row


def reject_change_request(row: MasterDataChangeRequest, user: User, reason: str) -> MasterDataChangeRequest:
    if row.status!='SUBMITTED': raise ValueError('Only SUBMITTED requests can be rejected')
    if row.created_by==user.email: raise PermissionError('Maker-checker control: creator cannot review own request')
    row.status='REJECTED';row.reviewed_by=user.email;row.reviewed_at=utcnow_naive();row.reason=reason or row.reason;return row


def _resolve_entity_id(db: Session, workspace_id: int, code: str|None) -> int|None:
    if not code: return None
    e=db.query(Entity).filter(Entity.workspace_id==workspace_id,Entity.entity_code==code).first()
    if not e: raise ValueError(f'Unknown entity_code: {code}')
    return e.id


def _sync_projection(db: Session, record: MasterDataRecord) -> None:
    """Synchronize master domains already consumed by operational services.
    The governed catalog remains the approval/version history; structured tables
    remain optimized operational projections for existing engines.
    """
    a=record.attributes or {}; ws=record.workspace_id
    if record.domain=='GL_ACCOUNTS':
        row=db.query(GLAccount).filter(GLAccount.workspace_id==ws,GLAccount.account_code==record.record_code).first()
        if not row:
            row=GLAccount(workspace_id=ws,account_code=record.record_code,description=record.name,classification=a.get('classification','OTHER'))
            db.add(row)
        row.description=record.name;row.classification=a.get('classification','OTHER');row.operating=_bool(a.get('operating'),True);row.pli_included=_bool(a.get('pli_included'),True);row.cost_plus_eligible=_bool(a.get('cost_plus_eligible'));row.allocation_eligible=_bool(a.get('allocation_eligible'));row.exceptional_item=_bool(a.get('exceptional_item'));row.pass_through=_bool(a.get('pass_through'));row.effective_from=record.effective_from;row.effective_to=record.effective_to;row.active=record.active
    elif record.domain=='INTERCOMPANY_PARTNERS':
        row=db.query(IntercompanyPartner).filter(IntercompanyPartner.workspace_id==ws,IntercompanyPartner.partner_code==record.record_code).first()
        if not row:
            row=IntercompanyPartner(workspace_id=ws,partner_code=record.record_code);db.add(row)
        row.entity_id=_resolve_entity_id(db,ws,a.get('entity_code'));row.trading_partner_code=a.get('trading_partner_code');row.vendor_code=a.get('vendor_code');row.customer_code=a.get('customer_code');row.country=a.get('country');row.relationship_type=a.get('relationship_type','RELATED_PARTY');row.effective_from=record.effective_from;row.effective_to=record.effective_to;row.active=record.active
    elif record.domain=='PROFIT_CENTERS':
        row=db.query(ProfitCenter).filter(ProfitCenter.workspace_id==ws,ProfitCenter.code==record.record_code).first()
        if not row:
            row=ProfitCenter(workspace_id=ws,code=record.record_code,entity_id=_resolve_entity_id(db,ws,a.get('entity_code')));db.add(row)
        row.entity_id=_resolve_entity_id(db,ws,a.get('entity_code'));row.function=a.get('function');row.business_unit=a.get('business_unit');row.geography=a.get('geography');row.active=record.active
    elif record.domain=='PRODUCTS':
        row=db.query(Product).filter(Product.workspace_id==ws,Product.sku==record.record_code).first()
        if not row:
            row=Product(workspace_id=ws,sku=record.record_code);db.add(row)
        row.product_group=a.get('product_group');row.entity_id=_resolve_entity_id(db,ws,a.get('entity_code'));row.standard_cost=Decimal(str(a['standard_cost'])) if a.get('standard_cost') not in {None,''} else None;row.currency=a.get('currency');row.active=record.active



def dependency_impact(db:Session, workspace_id:int, domain:str, record_code:str) -> dict[str,Any]:
    domain=normalize_domain(domain);code=record_code.upper();uses=[]
    if domain=='GL_ACCOUNTS':
        for r in db.query(MappingRule).filter(MappingRule.workspace_id==workspace_id,MappingRule.status=='ACTIVE'):
            mf=r.match_fields or {};value=mf.get('gl_account') or mf.get('gl')
            hit=(str(value).upper()==code) if not isinstance(value,list) else code in {str(x).upper() for x in value}
            if hit: uses.append({'type':'MAPPING_RULE','code':r.rule_code,'version':r.version,'blocking':True})
        for r in db.query(AllocationRule).filter(AllocationRule.workspace_id==workspace_id,AllocationRule.status.in_(['APPROVED','ACTIVE'])):
            if code in {str(x).upper() for x in (r.source_accounts or [])}: uses.append({'type':'ALLOCATION_RULE','code':r.rule_code,'version':r.version,'blocking':True})
        for r in db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==workspace_id,MasterDataRecord.domain=='JOURNAL_TEMPLATES',MasterDataRecord.active.is_(True)):
            vals={str(v).upper() for k,v in (r.attributes or {}).items() if k.endswith('_gl') and v}
            if code in vals: uses.append({'type':'JOURNAL_TEMPLATE','code':r.record_code,'version':r.version_no,'blocking':True})
    elif domain=='TP_SEGMENTS':
        for r in db.query(MappingRule).filter(MappingRule.workspace_id==workspace_id,MappingRule.status=='ACTIVE',MappingRule.segment_code==code):
            uses.append({'type':'MAPPING_RULE','code':r.rule_code,'version':r.version,'blocking':True})
        for r in db.query(AllocationRule).filter(AllocationRule.workspace_id==workspace_id,AllocationRule.status.in_(['APPROVED','ACTIVE'])):
            recips={str(x).upper() for x in (r.recipients or {}).keys()}
            if str(r.sender_segment).upper()==code or code in recips: uses.append({'type':'ALLOCATION_RULE','code':r.rule_code,'version':r.version,'blocking':True})
    elif domain in {'PRODUCTS','PROFIT_CENTERS','INTERCOMPANY_PARTNERS'}:
        field_aliases={
            'PRODUCTS':{'product_sku','product','sku'},
            'PROFIT_CENTERS':{'profit_center','profitcentre'},
            'INTERCOMPANY_PARTNERS':{'counterparty_code','counterparty','partner_code','partner'},
        }[domain]
        for r in db.query(MappingRule).filter(MappingRule.workspace_id==workspace_id,MappingRule.status=='ACTIVE'):
            mf=r.match_fields or {}
            for key in field_aliases:
                value=mf.get(key)
                hit=(str(value).upper()==code) if value is not None and not isinstance(value,list) else (code in {str(x).upper() for x in value} if isinstance(value,list) else False)
                if hit:
                    uses.append({'type':'MAPPING_RULE','code':r.rule_code,'version':r.version,'blocking':True,'field':key});break
        if domain=='INTERCOMPANY_PARTNERS':
            for r in db.query(AllocationRule).filter(AllocationRule.workspace_id==workspace_id,AllocationRule.status.in_(['APPROVED','ACTIVE'])):
                rules=r.recipient_rules or {}
                if any(str((cfg or {}).get('partner_code','')).upper()==code for cfg in rules.values() if isinstance(cfg,dict)):
                    uses.append({'type':'ALLOCATION_RULE','code':r.rule_code,'version':r.version,'blocking':True})
        # Historic financial lineage remains visible but never causes destructive deletion.
        uses.append({'type':'HISTORIC_FINANCIAL_LINEAGE','code':code,'blocking':False})
    return {'domain':domain,'record_code':code,'dependencies':uses,'blocking_count':sum(1 for x in uses if x.get('blocking')),'safe_to_deactivate':not any(x.get('blocking') for x in uses)}

def approve_change_request(db: Session, row: MasterDataChangeRequest, user: User) -> tuple[MasterDataRecord, dict[str, Any]|None, dict[str, Any]]:
    if row.status!='SUBMITTED': raise ValueError('Only SUBMITTED requests can be approved')
    if row.created_by==user.email: raise PermissionError('Maker-checker control: creator cannot approve own request')
    if row.change_type=='DEACTIVATE':
        impact=dependency_impact(db,row.workspace_id,row.domain,row.record_code)
        if impact['blocking_count']:
            refs=', '.join(f"{x['type']}:{x['code']}" for x in impact['dependencies'] if x.get('blocking'))
            raise ValueError(f'Cannot deactivate {row.record_code}; active dependencies exist: {refs}')
    record=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==row.workspace_id,MasterDataRecord.domain==row.domain,MasterDataRecord.record_code==row.record_code).first()
    previous=snapshot(record) if record else None
    if row.change_type=='CREATE':
        if record: raise ValueError('Record already exists')
        p=row.payload;record=MasterDataRecord(workspace_id=row.workspace_id,domain=row.domain,record_code=row.record_code,name=p['name'],attributes=p.get('attributes') or {},active=True,effective_from=p.get('effective_from'),effective_to=p.get('effective_to'),version_no=1,approved_by=user.email,approval_request_code=row.request_code);db.add(record);db.flush()
    else:
        if not record: raise ValueError('Record no longer exists')
        p=row.payload
        if row.change_type=='UPDATE':
            record.name=p['name'];record.attributes=p.get('attributes') or {};record.effective_from=p.get('effective_from');record.effective_to=p.get('effective_to');record.active=_bool(p.get('active'),record.active)
        elif row.change_type=='DEACTIVATE': record.active=False
        elif row.change_type=='REACTIVATE': record.active=True
        record.version_no+=1;record.approved_by=user.email;record.approval_request_code=row.request_code
    _sync_projection(db,record)
    current=snapshot(record)
    db.add(MasterDataVersion(workspace_id=row.workspace_id,domain=row.domain,record_code=row.record_code,version_no=record.version_no,snapshot=current,approved_by=user.email,approval_request_code=row.request_code))
    row.status='APPROVED';row.reviewed_by=user.email;row.reviewed_at=utcnow_naive();db.flush();return record,previous,current


def preview_import(db: Session, *, workspace_id: int, domain: str, filename: str, content: bytes) -> dict[str, Any]:
    domain=normalize_domain(domain)
    lower=filename.lower()
    if lower.endswith('.xlsx'):
        frame=pd.read_excel(BytesIO(content))
    elif lower.endswith('.csv'):
        frame=pd.read_csv(BytesIO(content))
    else: raise ValueError('Only CSV and XLSX master-data files are supported')
    frame.columns=[str(c).strip() for c in frame.columns]
    if 'record_code' not in frame.columns or 'name' not in frame.columns: raise ValueError('Columns record_code and name are required')
    field_names=list(MASTER_DOMAIN_DEFINITIONS[domain]['fields'])
    items=[];counts={'CREATE':0,'UPDATE':0,'NO_CHANGE':0,'INVALID':0}
    for idx,row in frame.iterrows():
        raw={k:_clean(row.get(k)) for k in frame.columns}
        attributes={k:_clean(raw.get(k)) for k in field_names if k in raw and _clean(raw.get(k)) is not None}
        payload={'record_code':raw.get('record_code'),'name':raw.get('name'),'attributes':attributes,'active':raw.get('active',True),'effective_from':raw.get('effective_from'),'effective_to':raw.get('effective_to')}
        try:
            normalized=validate_payload(db,workspace_id,domain,payload)
            existing=db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==workspace_id,MasterDataRecord.domain==domain,MasterDataRecord.record_code==normalized['record_code']).first()
            if not existing: action='CREATE'
            else:
                comparable=snapshot(existing); candidate={**normalized,'version_no':existing.version_no}
                action='NO_CHANGE' if all(comparable.get(k)==candidate.get(k) for k in ['record_code','name','attributes','active','effective_from','effective_to']) else 'UPDATE'
            item={'row':int(idx)+2,'action':action,'payload':normalized,'errors':[]}
        except Exception as exc:
            action='INVALID';item={'row':int(idx)+2,'action':action,'payload':payload,'errors':[str(exc)]}
        counts[action]+=1;items.append(item)
    return {'domain':domain,'filename':filename,'counts':counts,'items':items,'note':'Missing rows are never interpreted as deletions or deactivations.'}


def sync_seeded_operational_masters(db: Session, workspace_id: int) -> None:
    """Create governed catalog snapshots from existing operational demo masters.
    This is idempotent and only used to bootstrap sample data.
    """
    specs=[]
    for x in db.query(IntercompanyPartner).filter(IntercompanyPartner.workspace_id==workspace_id):
        entity=db.query(Entity).filter(Entity.id==x.entity_id).first() if x.entity_id else None
        specs.append(('INTERCOMPANY_PARTNERS',x.partner_code,x.partner_code,{'entity_code':entity.entity_code if entity else None,'trading_partner_code':x.trading_partner_code,'vendor_code':x.vendor_code,'customer_code':x.customer_code,'country':x.country,'relationship_type':x.relationship_type},x.effective_from,x.effective_to))
    for x in db.query(GLAccount).filter(GLAccount.workspace_id==workspace_id):
        specs.append(('GL_ACCOUNTS',x.account_code,x.description,{'classification':x.classification,'operating':x.operating,'pli_included':x.pli_included,'cost_plus_eligible':x.cost_plus_eligible,'allocation_eligible':x.allocation_eligible,'exceptional_item':x.exceptional_item,'pass_through':x.pass_through},x.effective_from,x.effective_to))
    for x in db.query(ProfitCenter).filter(ProfitCenter.workspace_id==workspace_id):
        entity=db.query(Entity).filter(Entity.id==x.entity_id).first()
        specs.append(('PROFIT_CENTERS',x.code,x.code,{'entity_code':entity.entity_code if entity else None,'function':x.function,'business_unit':x.business_unit,'geography':x.geography},None,None))
    for x in db.query(Product).filter(Product.workspace_id==workspace_id):
        entity=db.query(Entity).filter(Entity.id==x.entity_id).first() if x.entity_id else None
        specs.append(('PRODUCTS',x.sku,x.sku,{'product_group':x.product_group,'entity_code':entity.entity_code if entity else None,'standard_cost':str(x.standard_cost) if x.standard_cost is not None else None,'currency':x.currency},None,None))
    for domain,code,name,attributes,ef,et in specs:
        if db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==workspace_id,MasterDataRecord.domain==domain,MasterDataRecord.record_code==code).first(): continue
        attrs={k:v for k,v in attributes.items() if v is not None}
        r=MasterDataRecord(workspace_id=workspace_id,domain=domain,record_code=code,name=name,attributes=attrs,active=True,effective_from=ef,effective_to=et,version_no=1,approved_by='system@otp.local',approval_request_code='DEMO-SEED')
        db.add(r);db.flush();db.add(MasterDataVersion(workspace_id=workspace_id,domain=domain,record_code=code,version_no=1,snapshot=snapshot(r),approved_by='system@otp.local',approval_request_code='DEMO-SEED'))

    # Representative sample records for master domains that did not exist in RC.10.
    demo=[
        ('COST_CENTERS','DE01-OPS','DE Operations',{'entity_code':'DE01','function':'Distribution','business_unit':'Core'}),
        ('PLANTS','PL01-01','Poland Manufacturing Plant',{'entity_code':'PL01','country':'PL','location':'Poland'}),
        ('BUSINESS_UNITS','CORE','Core Business',{'description':'Core operating business'}),
        ('PRODUCT_GROUPS','FINISHED-GOODS','Finished Goods',{'description':'Finished products'}),
        ('CUSTOMERS','EXT-DE-001','German External Customers',{'entity_code':'DE01','country':'DE','external':True}),
        ('VENDORS','IC-NL01','Netherlands Principal Vendor',{'entity_code':'DE01','country':'NL','related_party':True}),
        ('CURRENCIES','EUR','Euro',{'decimal_places':2,'active_for_posting':True}),
        ('CURRENCIES','PLN','Polish Zloty',{'decimal_places':2,'active_for_posting':True}),
        ('FX_SOURCES','ECB-SPOT','ECB Reference Rates',{'provider':'ECB','rate_type':'SPOT','base_currency':'EUR'}),
        ('TRANSACTION_TYPES','DISTRIBUTION','Distribution',{'function':'Distribution','description':'Controlled distribution transaction'}),
        ('TP_SEGMENTS','DE01-DIST','DE01 Distribution',{'entity_code':'DE01','hierarchy_level':5,'function':'Distribution','business_unit':'Core','profit_center':'DE01-CORE'}),
    ]
    for domain,code,name,attrs in demo:
        if db.query(MasterDataRecord).filter(MasterDataRecord.workspace_id==workspace_id,MasterDataRecord.domain==domain,MasterDataRecord.record_code==code).first(): continue
        r=MasterDataRecord(workspace_id=workspace_id,domain=domain,record_code=code,name=name,attributes=attrs,active=True,effective_from='2025-01-01',version_no=1,approved_by='system@otp.local',approval_request_code='DEMO-SEED')
        db.add(r);db.flush();db.add(MasterDataVersion(workspace_id=workspace_id,domain=domain,record_code=code,version_no=1,snapshot=snapshot(r),approved_by='system@otp.local',approval_request_code='DEMO-SEED'))
