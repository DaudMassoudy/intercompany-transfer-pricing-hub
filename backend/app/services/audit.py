from __future__ import annotations
import uuid
from sqlalchemy.orm import Session
from ..models import AuditEvent, User

def audit(db: Session, *, event_type: str, actor: str, workspace_id: int|None=None, actor_role: str|None=None, entity_code: str|None=None, object_type: str|None=None, object_id: str|None=None, previous=None, new=None, reason: str|None=None, details: str='', correlation_id: str|None=None, source_system: str|None=None):
    cid=correlation_id or str(uuid.uuid4())
    row=AuditEvent(workspace_id=workspace_id,event_type=event_type,actor=actor,actor_role=actor_role,entity_code=entity_code,object_type=object_type,object_id=object_id,previous_value=previous,new_value=new,reason=reason,correlation_id=cid,source_system=source_system,details=details or event_type)
    db.add(row)
    return row
