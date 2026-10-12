from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
import hashlib, uuid
from typing import Any

@dataclass
class PostingResponse:
    status: str
    document_number: str
    posted_amount: Decimal
    payload: dict

class ERPConnector(ABC):
    @abstractmethod
    def health_check(self) -> dict: ...
    @abstractmethod
    def submit_journal(self, journal_payload: dict, idempotency_key: str) -> PostingResponse: ...
    @abstractmethod
    def get_posting_status(self, document_number: str) -> dict: ...
    @abstractmethod
    def reverse_posting(self, document_number: str, reason: str) -> dict: ...

class SimulatedSAPConnector(ERPConnector):
    """Deterministic SAP-like sandbox simulator. NEVER presented as a live SAP connector."""
    def health_check(self) -> dict:
        return {'status':'ok','connector':'SAP_S4_SIMULATOR','live':False}
    def submit_journal(self, journal_payload: dict, idempotency_key: str) -> PostingResponse:
        amount=Decimal(str(journal_payload['amount']))
        # deterministic document number from idempotency key for duplicate safety
        digest=hashlib.sha256(idempotency_key.encode()).hexdigest()[:10].upper()
        doc=f'SIM-S4-{digest}'
        if journal_payload.get('simulate_rejection'):
            return PostingResponse('REJECTED',doc,Decimal('0'),{'message':'Synthetic rejection requested'})
        delta=Decimal(str(journal_payload.get('simulate_posting_delta') or 0))
        posted=amount+delta
        return PostingResponse('POSTED',doc,posted,{'company_code':journal_payload.get('company_code'),'currency':journal_payload.get('currency'),'simulated':True,'synthetic_posting_delta':float(delta)})
    def get_posting_status(self, document_number: str) -> dict:
        return {'document_number':document_number,'status':'POSTED' if document_number.startswith('SIM-S4-') else 'UNKNOWN','simulated':True}
    def reverse_posting(self, document_number: str, reason: str) -> dict:
        return {'document_number':document_number,'status':'REVERSED','reason':reason,'simulated':True}

class SAPS4ConnectorContract(ERPConnector):
    """Production contract only. Requires real OData/API credentials and external sandbox qualification."""
    def __init__(self, base_url: str|None=None, credential_ref: str|None=None): self.base_url=base_url; self.credential_ref=credential_ref
    def _pending(self): raise RuntimeError('LIVE ERP SANDBOX QUALIFICATION = PENDING')
    def health_check(self): return {'status':'unqualified','connector':'SAP_S4','live':True,'qualification':'PENDING'}
    def submit_journal(self,journal_payload,idempotency_key): self._pending()
    def get_posting_status(self,document_number): self._pending()
    def reverse_posting(self,document_number,reason): self._pending()
