from datetime import timedelta
from app.timeutil import utcnow_naive
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..security import verify_password, issue_token, current_user
from ..settings import settings

router=APIRouter(prefix='/auth',tags=['authentication'])

@router.post('/login')
def login(username:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==username).first()
    now=utcnow_naive()
    if not u or not u.active or (u.locked_until and u.locked_until>now) or not verify_password(password,u.password_hash):
        if u:
            u.failed_login_count=(u.failed_login_count or 0)+1
            if u.failed_login_count>=5: u.locked_until=now+timedelta(minutes=15)
            db.commit()
        raise HTTPException(401,'Invalid credentials or account temporarily locked')
    u.failed_login_count=0;u.locked_until=None;u.last_login_at=now;db.commit()
    return {'access_token':issue_token(u),'token_type':'bearer','role':u.role,'workspace_id':u.workspace_id,'expires_in':settings.access_token_minutes*60}

@router.get('/me')
def me(user:User=Depends(current_user)):
    return {'email':user.email,'role':user.role,'workspace_id':user.workspace_id,'active':user.active,'last_login_at':user.last_login_at}

@router.post('/logout-all')
def logout_all(user:User=Depends(current_user),db:Session=Depends(get_db)):
    user.token_version+=1;db.commit();return {'status':'revoked'}

@router.get('/config')
def auth_config():
    return {'local_login':True,'oidc_enabled':settings.oidc_enabled,'oidc_issuer':settings.oidc_issuer,'saml_ready':True,'mfa_ready':True}
