from __future__ import annotations
from sqlalchemy.orm import Session
from ..models import Notification, User

ROLE_RECIPIENTS={
    'TP_MANAGER': ['TP_MANAGER','HEAD_OF_TP','GROUP_TAX_DIRECTOR','PLATFORM_ADMIN'],
    'FINANCE_CONTROLLER': ['FINANCE_CONTROLLER','PLATFORM_ADMIN'],
    'GROUP_TAX_DIRECTOR': ['GROUP_TAX_DIRECTOR','PLATFORM_ADMIN'],
    'MASTER_DATA_STEWARD': ['MASTER_DATA_STEWARD','PLATFORM_ADMIN'],
}

def notify_roles(db:Session, workspace_id:int, roles:list[str], subject:str, body:str):
    users=db.query(User).filter(User.workspace_id==workspace_id,User.active.is_(True),User.role.in_(roles)).all()
    created=[]
    for u in users:
        row=Notification(workspace_id=workspace_id,recipient=u.email,channel='IN_APP',subject=subject,body=body,status='UNREAD')
        db.add(row);created.append(row)
    return created

def notify_user(db:Session, workspace_id:int, recipient:str, subject:str, body:str):
    row=Notification(workspace_id=workspace_id,recipient=recipient,channel='IN_APP',subject=subject,body=body,status='UNREAD')
    db.add(row);return row
