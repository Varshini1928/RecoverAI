from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow(): return datetime.now(timezone.utc)

class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True)
    payment_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_reference: Mapped[str] = mapped_column(String(64))
    failure_reason: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[float] = mapped_column(Float)
    previous_attempts: Mapped[int] = mapped_column(Integer, default=0)
    customer_history_score: Mapped[float] = mapped_column(Float, default=0.5)
    customer_opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    recovered_amount: Mapped[float] = mapped_column(Float, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    duplicate_prevented: Mapped[int] = mapped_column(Integer, default=0)
    unsafe_blocked: Mapped[int] = mapped_column(Integer, default=0)
    inappropriate_retry: Mapped[int] = mapped_column(Integer, default=0)
    recovery_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    audits: Mapped[list["AuditLog"]] = relationship(back_populates="case", cascade="all,delete")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("recovery_cases.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(40))
    reasoning: Mapped[str] = mapped_column(Text)
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str] = mapped_column(Text)
    safety_rule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    case: Mapped[RecoveryCase] = relationship(back_populates="audits")

