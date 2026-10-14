from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    phone = Column(String(32), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    password = Column(String(256), nullable=False)
    two_factor_enabled = Column(Boolean, default=True, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    lockout_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    finance = relationship("FinanceSummary", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    budget_goals = relationship("BudgetGoal", back_populates="user", cascade="all, delete-orphan")


class FinanceSummary(Base):
    __tablename__ = "finance_summaries"

    id = Column(Integer, primary_key=True)
    user_phone = Column(String(32), ForeignKey("users.phone", ondelete="CASCADE"), unique=True, nullable=False)
    bank_balance = Column(Float, default=0.0)
    mutual_funds = Column(Float, default=0.0)
    stocks = Column(Float, default=0.0)
    loan = Column(Float, default=0.0)
    credit_score = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="finance")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_phone = Column(String(32), ForeignKey("users.phone", ondelete="CASCADE"), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    category = Column(String(100))
    merchant = Column(String(200))
    txn_type = Column(String(16))
    description = Column(Text)
    ts = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="transactions")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_phone = Column(String(32), ForeignKey("users.phone", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(200), default="Personal Finance Chat")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_message_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_phone = Column(String(32), ForeignKey("users.phone", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    session = relationship("ChatSession", back_populates="messages")


class BudgetGoal(Base):
    __tablename__ = "budget_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_phone = Column(String(32), ForeignKey("users.phone", ondelete="CASCADE"), index=True, nullable=False)
    period_key = Column(String(7), nullable=False)
    monthly_income = Column(Float, default=0.0)
    savings_goal = Column(Float, default=0.0)
    category_budgets = Column(JSON, default=dict)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="budget_goals")

    __table_args__ = (UniqueConstraint("user_phone", "period_key", name="uq_budget_goal_user_period"),)


Index("idx_tx_user_ts", Transaction.user_phone, Transaction.ts)
Index("idx_chat_session_user_active", ChatSession.user_phone, ChatSession.is_active)
Index("idx_chat_message_session_created", ChatMessage.session_id, ChatMessage.created_at)
