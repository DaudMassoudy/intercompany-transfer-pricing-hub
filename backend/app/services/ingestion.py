from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import hashlib, io, uuid
from typing import Iterable

import pandas as pd
from sqlalchemy.orm import Session

from ..models import SourceImport, RawFinancialRecord, Entity, GLAccount, IntercompanyPartner
from .finance import D, money

REQUIRED_COLUMNS={'Period','Entity_ID','GL_Account','Currency','Amount'}
COLUMN_MAP={
    'Period':'period','Entity_ID':'entity_code','Company_Code':'company_code','Document_Number':'document_number',
    'GL_Account':'gl_account','Cost_Center':'cost_center','Profit_Center':'profit_center','IC_Partner_ID':'counterparty_code',
    'Product_SKU':'product_sku','Product_Group':'product_group','Currency':'currency','Amount':'amount','Debit_Credit':'debit_credit'
}

def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

def _read_table(filename: str, data: bytes) -> pd.DataFrame:
    lower=filename.lower()
    if lower.endswith('.csv'):
        return pd.read_csv(io.BytesIO(data),dtype=str,keep_default_na=False)
    if lower.endswith('.xlsx') or lower.endswith('.xlsm'):
        return pd.read_excel(io.BytesIO(data),dtype=str,keep_default_na=False)
    raise ValueError('Only CSV and XLSX imports are supported')

def validate_and_store(db: Session, *, workspace_id: int, actor: str, source_system: str, period: str, filename: str, data: bytes, entity_id: int|None=None, original_path: str|None=None) -> dict:
    digest=sha256_bytes(data)
    imp=SourceImport(import_code=f'IMP-{uuid.uuid4().hex[:12].upper()}',workspace_id=workspace_id,entity_id=entity_id,source_system=source_system,period=period,filename=filename,sha256=digest,status='VALIDATING',actor=actor,original_path=original_path)
    db.add(imp); db.flush()
    try:
        df=_read_table(filename,data)
    except Exception as e:
        imp.status='FAILED'; imp.rejected_rows=0; db.flush(); return {'import_id':imp.id,'import_code':imp.import_code,'status':'FAILED','error':str(e)}
    missing=sorted(REQUIRED_COLUMNS-set(df.columns))
    if missing:
        imp.status='FAILED';imp.row_count=len(df);imp.rejected_rows=len(df);db.flush();return {'import_id':imp.id,'import_code':imp.import_code,'status':'FAILED','missing_columns':missing}
    imp.row_count=len(df)
    accepted=rejected=warning=0
    src_total=Decimal('0');accepted_total=Decimal('0')
    entity_codes={x.entity_code for x in db.query(Entity).filter(Entity.workspace_id==workspace_id).all()}
    gl_codes={x.account_code for x in db.query(GLAccount).filter(GLAccount.workspace_id==workspace_id,GLAccount.active.is_(True)).all()}
    partner_codes={x.partner_code for x in db.query(IntercompanyPartner).filter(IntercompanyPartner.workspace_id==workspace_id,IntercompanyPartner.active.is_(True)).all()}
    seen_docs=set()
    for idx,row in df.iterrows():
        payload={str(k): (None if pd.isna(v) else str(v)) for k,v in row.to_dict().items()}
        messages=[];status='VALID'
        try: amount=money(payload.get('Amount','0'))
        except Exception: amount=Decimal('0');messages.append('INVALID_AMOUNT');status='REJECTED'
        src_total+=amount
        entity_code=payload.get('Entity_ID','').strip()
        gl=payload.get('GL_Account','').strip()
        ccy=payload.get('Currency','').strip().upper()
        period_value=payload.get('Period','').strip()
        cp=(payload.get('IC_Partner_ID') or '').strip() or None
        if entity_code not in entity_codes: messages.append('UNKNOWN_ENTITY');status='REJECTED'
        if gl not in gl_codes: messages.append('UNKNOWN_GL');status='REJECTED'
        if len(ccy)!=3: messages.append('INVALID_CURRENCY');status='REJECTED'
        if len(period_value)<7: messages.append('INVALID_PERIOD');status='REJECTED'
        if cp and cp not in partner_codes: messages.append('UNKNOWN_COUNTERPARTY');status='WARNING' if status!='REJECTED' else status
        doc=(payload.get('Document_Number') or '').strip()
        if doc:
            key=(entity_code,doc,gl,str(amount))
            if key in seen_docs: messages.append('POSSIBLE_DUPLICATE');status='WARNING' if status!='REJECTED' else status
            seen_docs.add(key)
        rec=RawFinancialRecord(workspace_id=workspace_id,source_import_id=imp.id,row_number=int(idx)+2,period=period_value or period,entity_code=entity_code,company_code=(payload.get('Company_Code') or None),document_number=doc or None,gl_account=gl,cost_center=(payload.get('Cost_Center') or None),profit_center=(payload.get('Profit_Center') or None),counterparty_code=cp,product_sku=(payload.get('Product_SKU') or None),product_group=(payload.get('Product_Group') or None),currency=ccy,amount=amount,debit_credit=(payload.get('Debit_Credit') or None),validation_status=status,validation_messages=messages or None,raw_payload=payload)
        db.add(rec)
        if status=='REJECTED': rejected+=1
        else:
            accepted+=1;accepted_total+=amount
            if status=='WARNING': warning+=1
    imp.accepted_rows=accepted;imp.rejected_rows=rejected;imp.warning_rows=warning;imp.source_control_total=money(src_total);imp.imported_control_total=money(accepted_total);imp.status='VALIDATED' if rejected==0 else ('PARTIAL' if accepted>0 else 'FAILED')
    db.flush()
    return {'import_id':imp.id,'import_code':imp.import_code,'status':imp.status,'row_count':imp.row_count,'accepted_rows':accepted,'rejected_rows':rejected,'warning_rows':warning,'source_control_total':float(imp.source_control_total),'imported_control_total':float(imp.imported_control_total),'sha256':digest}
