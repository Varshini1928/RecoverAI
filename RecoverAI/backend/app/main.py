import csv, io, logging, sys
from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .agents import RecoveryWorkflow, VALID_REASONS
from .auth import create_token, require_admin, verify_login
from .config import get_settings
from .database import Base, engine, get_db
from .models import AuditLog, RecoveryCase
from .schemas import AuditOut, CaseCreate, CaseOut, DecisionOut, LoginRequest, Page, Token

logging.basicConfig(stream=sys.stdout,level=logging.INFO,format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}')
settings=get_settings(); Base.metadata.create_all(engine)
app=FastAPI(title="RecoverAI API",version="1.0.0",description="Synthetic test data and simulated/test-mode payments only.")
app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=True,allow_methods=["GET","POST"],allow_headers=["Authorization","Content-Type"])

@app.exception_handler(Exception)
async def unhandled(_,exc):
    logging.exception("Unhandled error",exc_info=exc); return __import__('fastapi').responses.JSONResponse(status_code=500,content={"detail":"Unexpected server error"})
@app.get("/api/health")
def health(): return {"status":"ok","mode":"synthetic-test-data","payments":"simulated/test-mode"}
@app.post("/api/auth/login",response_model=Token)
def login(body:LoginRequest):
    if not verify_login(body.username,body.password): raise HTTPException(401,"Invalid credentials")
    return Token(access_token=create_token(body.username))
@app.post("/api/cases",response_model=CaseOut,status_code=201,dependencies=[Depends(require_admin)])
def create_case(body:CaseCreate,db:Session=Depends(get_db)):
    if body.failure_reason not in VALID_REASONS: raise HTTPException(422,"Unsupported failure_reason")
    existing=db.query(RecoveryCase).filter_by(idempotency_key=body.idempotency_key).first()
    if existing:
        existing.duplicate_prevented+=1; db.add(AuditLog(case_id=existing.id,agent_name="Safety Gate",action="DUPLICATE_BLOCKED",reasoning="Idempotency key already processed.",input_summary='{"redacted":true}',output_summary='{"duplicate":true}',safety_rule="IDEMPOTENCY_DUPLICATE")); db.commit()
        raise HTTPException(409,"Duplicate event prevented by idempotency key")
    c=RecoveryCase(**body.model_dump(),status="pending"); db.add(c)
    try: db.commit(); db.refresh(c); return c
    except IntegrityError: db.rollback(); raise HTTPException(409,"Duplicate idempotency key")
@app.get("/api/cases",response_model=Page,dependencies=[Depends(require_admin)])
def cases(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),status:str|None=None,failure_reason:str|None=None,search:str|None=None,db:Session=Depends(get_db)):
    q=db.query(RecoveryCase)
    if status: q=q.filter(RecoveryCase.status==status)
    if failure_reason: q=q.filter(RecoveryCase.failure_reason==failure_reason)
    if search: q=q.filter((RecoveryCase.payment_id.contains(search))|(RecoveryCase.customer_reference.contains(search))|(RecoveryCase.merchant_id.contains(search)))
    total=q.count(); items=q.order_by(RecoveryCase.created_at.desc()).offset((page-1)*page_size).limit(page_size).all(); return Page(items=items,total=total,page=page,page_size=page_size)
@app.get("/api/cases/{case_id}",response_model=CaseOut,dependencies=[Depends(require_admin)])
def case(case_id:int,db:Session=Depends(get_db)):
    c=db.get(RecoveryCase,case_id)
    if not c: raise HTTPException(404,"Case not found")
    return c
@app.post("/api/cases/{case_id}/process",response_model=DecisionOut,dependencies=[Depends(require_admin)])
def process(case_id:int,db:Session=Depends(get_db)):
    c=db.get(RecoveryCase,case_id)
    if not c: raise HTTPException(404,"Case not found")
    if c.status not in {"pending","failed"}: c.duplicate_prevented+=1; db.commit(); raise HTTPException(409,"Case already processed")
    c.status="processing"; db.commit(); RecoveryWorkflow(db).run(c.id); db.refresh(c); return DecisionOut(case=c,message="Processed using simulated/test-mode payment adapter")
@app.post("/api/cases/process-all",dependencies=[Depends(require_admin)])
def process_all(db:Session=Depends(get_db)):
    ids=[x[0] for x in db.query(RecoveryCase.id).filter_by(status="pending").all()]; processed=0; errors=0
    for cid in ids:
        try: RecoveryWorkflow(db).run(cid); processed+=1
        except Exception: db.rollback(); errors+=1; logging.exception("Batch case failed",extra={"case_id":cid})
    return {"queued":len(ids),"processed":processed,"errors":errors}
@app.post("/api/cases/{case_id}/approve",response_model=DecisionOut,dependencies=[Depends(require_admin)])
def approve(case_id:int,db:Session=Depends(get_db)):
    c=db.get(RecoveryCase,case_id)
    if not c: raise HTTPException(404,"Case not found")
    if c.status!="escalated": raise HTTPException(409,"Only escalated cases can be approved")
    c.status="processing"; db.commit(); RecoveryWorkflow(db,human_approved=True).run(c.id); db.refresh(c); return DecisionOut(case=c,message="Human approval recorded and workflow rerun")
@app.post("/api/cases/{case_id}/reject",response_model=DecisionOut,dependencies=[Depends(require_admin)])
def reject(case_id:int,db:Session=Depends(get_db)):
    c=db.get(RecoveryCase,case_id)
    if not c: raise HTTPException(404,"Case not found")
    if c.status!="escalated": raise HTTPException(409,"Only escalated cases can be rejected")
    c.status="stopped"; db.add(AuditLog(case_id=c.id,agent_name="Human Review",action="REJECT",reasoning="Admin rejected recovery action.",input_summary='{}',output_summary='{"status":"stopped"}',safety_rule="HUMAN_REJECTED")); db.commit(); db.refresh(c); return DecisionOut(case=c,message="Recovery rejected and stopped")
@app.get("/api/cases/{case_id}/audit",response_model=list[AuditOut],dependencies=[Depends(require_admin)])
def case_audit(case_id:int,db:Session=Depends(get_db)):
    if not db.get(RecoveryCase,case_id): raise HTTPException(404,"Case not found")
    return db.query(AuditLog).filter_by(case_id=case_id).order_by(AuditLog.timestamp).all()
@app.get("/api/audit",response_model=list[AuditOut],dependencies=[Depends(require_admin)])
def audits(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=200),agent_name:str|None=None,db:Session=Depends(get_db)):
    q=db.query(AuditLog)
    if agent_name:q=q.filter_by(agent_name=agent_name)
    return q.order_by(AuditLog.timestamp.desc()).offset((page-1)*page_size).limit(page_size).all()
@app.get("/api/metrics",dependencies=[Depends(require_admin)])
def metrics(db:Session=Depends(get_db)):
    cs=db.query(RecoveryCase).all(); total=len(cs); at_risk=sum(c.amount for c in cs); recovered=sum(c.recovered_amount for c in cs); completed=sum(c.status in {"recovered","failed"} for c in cs); escalated=sum(c.status=="escalated" for c in cs)
    times=[(c.recovered_at-c.recovery_started_at).total_seconds() for c in cs if c.recovered_at and c.recovery_started_at]
    strategies={}
    for name in ["RETRY","REMIND","ESCALATE","STOP"]:
        group=[c for c in cs if c.recommended_action==name]; strategies[name]={"total":len(group),"recovered":sum(c.status=="recovered" for c in group),"rate":round(100*sum(c.status=="recovered" for c in group)/len(group),1) if group else 0}
    reasons={r:sum(c.failure_reason==r for c in cs) for r in VALID_REASONS}; trend={}
    for c in cs:
        d=c.updated_at.strftime("%Y-%m-%d"); trend.setdefault(d,{"date":d,"processed":0,"recovered":0}); trend[d]["processed"]+=int(c.status!="pending"); trend[d]["recovered"]+=c.recovered_amount
    return {"synthetic":True,"total_cases":total,"total_revenue_at_risk":round(at_risk,2),"revenue_recovered":round(recovered,2),"recovery_success_rate":round(100*sum(c.status=="recovered" for c in cs)/completed,1) if completed else 0,"average_recovery_time_seconds":round(sum(times)/len(times),2) if times else 0,"pending_cases":sum(c.status=="pending" for c in cs),"human_escalations":escalated,"escalation_rate":round(100*escalated/total,1) if total else 0,"unsafe_actions_blocked":sum(c.unsafe_blocked for c in cs),"duplicate_events_prevented":sum(c.duplicate_prevented for c in cs),"unresolved_exceptions":sum(c.status=="failed" for c in cs),"false_or_inappropriate_retry_count":sum(c.inappropriate_retry for c in cs),"strategy_performance":strategies,"failure_reasons":reasons,"trend":list(trend.values())[-14:]}
@app.get("/api/reports/csv",dependencies=[Depends(require_admin)])
def report(db:Session=Depends(get_db)):
    buf=io.StringIO(); w=csv.writer(buf); w.writerow(["case_id","payment_id","failure_reason","amount","status","priority_score","strategy","confidence","recovered_amount","synthetic_data"])
    for c in db.query(RecoveryCase).order_by(RecoveryCase.id): w.writerow([c.id,c.payment_id,c.failure_reason,c.amount,c.status,c.priority_score,c.recommended_action,c.confidence,c.recovered_amount,True])
    return StreamingResponse(iter([buf.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=recoverai-synthetic-report.csv"})

