from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends
from ..db import get_db
from ..settings import settings

router=APIRouter(tags=['health'])

@router.get('/health/live')
def live(): return {'status':'ok','version':settings.app_version}

@router.get('/health/ready')
def ready(db:Session=Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status':'ready','version':settings.app_version,'environment':settings.environment}

@router.get('/health/version')
def version(): return {'version':settings.app_version,'environment':settings.environment,'demo_mode':settings.demo_mode}

# v0.x compatibility endpoint
@router.get('/health')
def health(db:Session=Depends(get_db)): return ready(db)
