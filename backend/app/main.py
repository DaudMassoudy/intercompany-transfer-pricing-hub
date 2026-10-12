from __future__ import annotations
import os, uuid, time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .db import SessionLocal
from .seed import seed_demo
from .routers import health, auth, dashboard, imports, mapping, allocations, operational, approvals, accounting, governance, internal, master_data, enterprise_ops, practical10

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.demo_mode and settings.jwt_secret in {'dev-only-change-me','demo_jwt_secret_change_me',''}:
        raise RuntimeError('Refusing non-demo startup with default JWT_SECRET')
    if settings.demo_mode:
        db=SessionLocal()
        try: seed_demo(db)
        finally: db.close()
    yield

app=FastAPI(title='Enterprise Operational Transfer Pricing Platform API',version=settings.app_version,docs_url='/api/docs',openapi_url='/api/openapi.json',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()],allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type','X-Correlation-ID','X-Integration-Key'],allow_credentials=True)

@app.middleware('http')
async def request_context(request:Request,call_next):
    cid=request.headers.get('X-Correlation-ID') or str(uuid.uuid4());request.state.correlation_id=cid
    start=time.perf_counter();response=await call_next(request);response.headers['X-Correlation-ID']=cid
    response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Referrer-Policy']='no-referrer';response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    if settings.environment=='production': response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    response.headers['Server-Timing']=f'app;dur={(time.perf_counter()-start)*1000:.1f}'
    return response

PREFIX='/api/v1'
for router in [health.router,auth.router,dashboard.router,imports.router,mapping.router,allocations.router,operational.router,approvals.router,accounting.router,governance.router,internal.router,master_data.router,enterprise_ops.router,practical10.router]:
    app.include_router(router,prefix=PREFIX)
