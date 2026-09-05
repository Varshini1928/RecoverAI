import hashlib, json, logging
from datetime import datetime, timezone
from typing import TypedDict
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session
from .models import AuditLog, RecoveryCase
from .llm import gemini_strategy

log = logging.getLogger("recoverai.agents")
VALID_REASONS = {"insufficient_balance","card_declined","expired_card","technical_error","authentication_failed"}

class AgentState(TypedDict, total=False):
    case_id:int; score:float; expected_value:float; strategy:str; confidence:float
    strategy_reason:str; allowed:bool; safety_rule:str; final_action:str; result:str; recovered_amount:float

def calculate_score(amount, reason, attempts, history):
    amount_score = min(amount / 500, 35)
    reason_weight = {"technical_error":28,"insufficient_balance":23,"authentication_failed":18,"card_declined":12,"expired_card":4}.get(reason,5)
    score = amount_score + reason_weight + history*32 - attempts*10
    return round(max(0, min(100, score)), 2)

def choose_strategy(reason, attempts, history):
    if reason == "expired_card": return "REMIND", .96, "Payment method is expired; request an update instead of retrying."
    if attempts >= 3: return "STOP", .99, "Retry limit reached."
    if reason == "technical_error": return "RETRY", .94, "A transient technical failure is suitable for a safe retry."
    if reason == "insufficient_balance": return ("RETRY", .82, "A later retry may succeed after funds are available.") if history >= .45 else ("REMIND", .76, "Low payment history suggests a reminder before retrying.")
    if reason == "authentication_failed": return "REMIND", .84, "Customer authentication is required before another attempt."
    if reason == "card_declined": return ("ESCALATE", .68, "Decline cause is uncertain and needs review.") if history < .35 else ("REMIND", .78, "Ask the customer to confirm or replace the card.")
    return "ESCALATE", .5, "Unknown failure reason requires review."

def safety_decision(case, action, confidence, approved=False):
    if case.customer_opted_out: return False,"STOP","CUSTOMER_OPT_OUT","Customer opted out; contact and retries are blocked."
    if action == "RETRY" and case.failure_reason == "expired_card": return False,"ESCALATE","EXPIRED_CARD_NO_RETRY","Expired cards can never be retried."
    if action == "RETRY" and case.previous_attempts >= 3: return False,"STOP","MAX_THREE_RETRIES","Maximum retry count reached."
    if confidence < .70: return False,"ESCALATE","LOW_CONFIDENCE","Confidence is below 0.70."
    if case.amount > 25000 and not approved: return False,"ESCALATE","HIGH_VALUE_APPROVAL_REQUIRED","Cases above ₹25,000 require human approval."
    return True,action,"POLICY_ALLOWED","All mandatory safety checks passed."

def simulated_outcome(case, action):
    if action == "ESCALATE": return "escalated",0.0
    if action == "STOP": return "stopped",0.0
    if action == "REMIND": return "reminded",0.0
    bucket = int(hashlib.sha256(case.idempotency_key.encode()).hexdigest()[:8],16) % 100
    threshold = {"technical_error":82,"insufficient_balance":46,"card_declined":25,"authentication_failed":20,"expired_card":0}.get(case.failure_reason,10)
    return ("recovered",case.amount) if bucket < threshold else ("failed",0.0)

class RecoveryWorkflow:
    def __init__(self, db:Session, human_approved=False):
        self.db=db; self.human_approved=human_approved
        g=StateGraph(AgentState)
        for name,fn in [("scorer",self.scorer),("strategist",self.strategist),("safety",self.safety),("sender",self.sender),("audit",self.audit)]: g.add_node(name,fn)
        g.set_entry_point("scorer"); g.add_edge("scorer","strategist"); g.add_edge("strategist","safety"); g.add_edge("safety","sender"); g.add_edge("sender","audit"); g.add_edge("audit",END)
        self.graph=g.compile()
    def case(self,s): return self.db.get(RecoveryCase,s["case_id"])
    def note(self,c,agent,action,reason,inp,out,rule=None):
        self.db.add(AuditLog(case_id=c.id,agent_name=agent,action=action,reasoning=reason,input_summary=json.dumps(inp),output_summary=json.dumps(out),safety_rule=rule))
    def scorer(self,s):
        c=self.case(s); score=calculate_score(c.amount,c.failure_reason,c.previous_attempts,c.customer_history_score); ev=round(c.amount*score/100,2)
        self.note(c,"Scorer Agent","SCORE","Weighted amount, failure recoverability, attempts and customer history.",{"amount":c.amount,"reason":c.failure_reason,"attempts":c.previous_attempts},{"priority_score":score,"expected_recoverable_value":ev})
        return {**s,"score":score,"expected_value":ev}
    def strategist(self,s):
        c=self.case(s); fallback=choose_strategy(c.failure_reason,c.previous_attempts,c.customer_history_score); action,conf,reason=gemini_strategy(c,fallback)
        self.note(c,"Strategist Agent",action,reason,{"priority_score":s["score"],"failure_reason":c.failure_reason},{"action":action,"confidence":conf})
        return {**s,"strategy":action,"confidence":conf,"strategy_reason":reason}
    def safety(self,s):
        c=self.case(s); allowed,final,rule,reason=safety_decision(c,s["strategy"],s["confidence"],self.human_approved)
        if not allowed and final in {"ESCALATE","STOP"}: c.unsafe_blocked += 1
        self.note(c,"Safety Gate",final,reason,{"proposed_action":s["strategy"],"confidence":s["confidence"]},{"allowed":allowed,"final_action":final},rule)
        return {**s,"allowed":allowed,"safety_rule":rule,"final_action":final}
    def sender(self,s):
        c=self.case(s); result,recovered=simulated_outcome(c,s["final_action"])
        self.note(c,"Sender Agent",s["final_action"],"Deterministic Razorpay test-mode simulator; no real charge was made.",{"action":s["final_action"]},{"result":result,"recovered_amount":recovered})
        return {**s,"result":result,"recovered_amount":recovered}
    def audit(self,s):
        c=self.case(s); now=datetime.now(timezone.utc); c.priority_score=s["score"]; c.recommended_action=s["final_action"]; c.confidence=s["confidence"]; c.status=s["result"]; c.recovered_amount=s["recovered_amount"]; c.updated_at=now
        if c.recovery_started_at is None: c.recovery_started_at=now
        if c.status=="recovered": c.recovered_at=now
        self.note(c,"Audit Agent","COMMIT","Complete decision trace persisted without secrets or payment credentials.",{"case_id":c.id},{"status":c.status,"recovered_amount":c.recovered_amount},s["safety_rule"])
        self.db.commit(); return s
    def run(self,case_id): return self.graph.invoke({"case_id":case_id})
