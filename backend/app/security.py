from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable
import secrets
import hashlib
from types import SimpleNamespace

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, UserEntityAccess, Entity, ServiceAccount
from .settings import settings

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
oauth2 = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')

ROLE_PERMISSIONS = {
    'PLATFORM_ADMIN': {'*'},
    'GROUP_TAX_DIRECTOR': {'read','write','approve','export','admin_policy','policy_admin','workflow_admin','security_admin','service_account_admin','integration_admin','reconciliation_certify','journal_post','master_data_draft','master_data_approve','master_data_import'},
    'HEAD_OF_TP': {'read','write','approve','export','admin_policy','policy_admin','workflow_admin','security_admin','service_account_admin','integration_admin','reconciliation_certify','journal_post','master_data_draft','master_data_approve','master_data_import'},
    'TP_MANAGER': {'read','write','approve','export','master_data_approve','reconciliation_certify'},
    'TP_ANALYST': {'read','write','export'},
    'FINANCE_CONTROLLER': {'read','approve','journal','journal_post','reconciliation_certify','export'},
    'LOCAL_FINANCE': {'read','write','export'},
    'MASTER_DATA_STEWARD': {'read','export','master_data_draft','master_data_import'},
    'REVIEWER': {'read','approve'},
    'AUDITOR': {'read','export'},
    'EXECUTIVE_VIEWER': {'read'},
    'INTEGRATION_SERVICE': {'integration'},
    # legacy role alias
    'GROUP_TP_MANAGER': {'read','write','approve','export','admin_policy','policy_admin','workflow_admin','security_admin','service_account_admin','integration_admin','reconciliation_certify','journal_post','master_data_draft','master_data_approve','master_data_import'},
}

def hash_password(value: str) -> str:
    return ph.hash(value)

def verify_password(raw: str, encoded: str) -> bool:
    try:
        return ph.verify(encoded, raw)
    except (VerifyMismatchError, Exception):
        return False

def issue_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user.email,
        'uid': user.id,
        'role': user.role,
        'workspace_id': user.workspace_id,
        'ver': user.token_version,
        'iss': settings.jwt_issuer,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        'jti': secrets.token_hex(12),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm='HS256')

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=['HS256'], issuer=settings.jwt_issuer)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, 'Session expired')
    except jwt.PyJWTError:
        raise HTTPException(401, 'Invalid token')

def current_user(token: str=Depends(oauth2), db: Session=Depends(get_db)) -> User:
    if token.startswith('otp_sa_'):
        digest=hashlib.sha256(token.encode()).hexdigest()
        row=db.query(ServiceAccount).filter(ServiceAccount.token_hash==digest,ServiceAccount.active.is_(True)).first()
        now=datetime.now(timezone.utc).replace(tzinfo=None)
        if not row or (row.expires_at and row.expires_at<now): raise HTTPException(401,'Inactive or expired service account')
        return SimpleNamespace(id=-row.id,email=f'service:{row.account_code}',role='INTEGRATION_SERVICE',workspace_id=row.workspace_id,active=True,last_login_at=None,token_version=1,service_permissions=set(row.permissions or []),service_entity_codes=set(row.entity_codes or []),service_account_id=row.id)
    payload = decode_token(token)
    user = db.query(User).filter(User.id==payload.get('uid'), User.active==True).first()
    if not user or user.email != payload.get('sub') or user.token_version != payload.get('ver'):
        raise HTTPException(401, 'Inactive or revoked session')
    return user

def has_permission(user: User, permission: str) -> bool:
    service_perms=getattr(user,'service_permissions',None)
    if service_perms is not None: return '*' in service_perms or permission in service_perms
    perms = ROLE_PERMISSIONS.get(user.role, set())
    return '*' in perms or permission in perms

def require_permission(permission: str):
    def _dep(user: User=Depends(current_user)):
        if not has_permission(user, permission):
            raise HTTPException(403, f'Missing permission: {permission}')
        return user
    return _dep

def require_roles(*roles: str):
    allowed=set(roles)
    def _dep(user: User=Depends(current_user)):
        if user.role not in allowed and user.role != 'PLATFORM_ADMIN':
            raise HTTPException(403, 'Role not permitted')
        return user
    return _dep

def entity_accessible(db: Session, user: User, entity: Entity, write: bool=False, approve: bool=False) -> bool:
    if user.workspace_id is not None and entity.workspace_id != user.workspace_id:
        return False
    if getattr(user,'role',None)=='INTEGRATION_SERVICE':
        allowed=getattr(user,'service_entity_codes',set())
        return entity.entity_code in allowed and not approve
    if user.role in {'PLATFORM_ADMIN','GROUP_TAX_DIRECTOR','HEAD_OF_TP','TP_MANAGER','TP_ANALYST','FINANCE_CONTROLLER','REVIEWER','AUDITOR','EXECUTIVE_VIEWER','GROUP_TP_MANAGER','MASTER_DATA_STEWARD'}:
        return True
    grant = db.query(UserEntityAccess).filter(UserEntityAccess.user_id==user.id, UserEntityAccess.entity_id==entity.id).first()
    if not grant: return False
    if approve: return bool(grant.can_approve)
    if write: return bool(grant.can_write)
    return bool(grant.can_read)

def require_entity_access(db: Session, user: User, entity: Entity, write: bool=False, approve: bool=False):
    if not entity_accessible(db,user,entity,write=write,approve=approve):
        raise HTTPException(403,'Entity access denied')
