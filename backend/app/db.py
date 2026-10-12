import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .base import Base

DATABASE_URL = os.getenv('DATABASE_URL','sqlite:///./otp.db')
kwargs={'pool_pre_ping':True,'future':True}
if DATABASE_URL.startswith('sqlite'):
    kwargs['connect_args']={'check_same_thread':False}
engine=create_engine(DATABASE_URL,**kwargs)
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False,expire_on_commit=False)

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()
