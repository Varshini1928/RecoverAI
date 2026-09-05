from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class LoginRequest(BaseModel): username: str; password: str
class Token(BaseModel): access_token: str; token_type: str = "bearer"
class CaseCreate(BaseModel):
    merchant_id: str = Field(min_length=2, max_length=64)
    payment_id: str = Field(min_length=2, max_length=64)
    customer_reference: str = Field(min_length=2, max_length=64)
    failure_reason: str
    amount: float = Field(gt=0, le=10_000_000)
    previous_attempts: int = Field(ge=0, le=20)
    customer_history_score: float = Field(ge=0, le=1, default=.5)
    customer_opted_out: bool = False
    idempotency_key: str = Field(min_length=4, max_length=100)
class CaseOut(CaseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int; status: str; priority_score: float | None; recommended_action: str | None
    confidence: float | None; recovered_amount: float; created_at: datetime; updated_at: datetime
class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; case_id: int; agent_name: str; action: str; reasoning: str
    input_summary: str; output_summary: str; safety_rule: str | None; timestamp: datetime
class Page(BaseModel): items: list[CaseOut]; total: int; page: int; page_size: int
class DecisionOut(BaseModel): case: CaseOut; message: str

