"""SQLAlchemy ORM models for the structured operational data described in architecture.md."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()
CUSTOMER_FK = "customers.id"



def _uuid() -> str:
        return str(uuid.uuid4())



def _now() -> datetime:
        return datetime.now(timezone.utc)



class User(Base):
        __tablename__ = "users"
        id = Column(String(64), primary_key=True, default=_uuid)
        email = Column(String(255), nullable=False, unique=True)
        hashed_password = Column(String(255), nullable=False)
        role = Column(String(32), nullable=False, default="analyst")
        is_active = Column(Boolean, nullable=False, default=True)
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)



class Customer(Base):
        __tablename__ = "customers"
        id = Column(String(64), primary_key=True)
        name = Column(String(160), nullable=False)
        segment = Column(String(64), nullable=True)
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

        accounts = relationship("Account", back_populates="customer")
        loans = relationship("Loan", back_populates="customer")



class Account(Base):
        __tablename__ = "accounts"
        id = Column(String(64), primary_key=True)
        customer_id = Column(String(64), ForeignKey(CUSTOMER_FK), nullable=False, index=True)
        account_type = Column(String(48), nullable=False)
        balance = Column(Float, nullable=False, default=0.0)
        currency = Column(String(3), nullable=False, default="USD")
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

        customer = relationship("Customer", back_populates="accounts")



class Loan(Base):
        __tablename__ = "loans"
        id = Column(String(64), primary_key=True)
        customer_id = Column(String(64), ForeignKey(CUSTOMER_FK), nullable=False, index=True)
        principal_amount = Column(Float, nullable=False)
        status = Column(String(32), nullable=False, default="active")
        dataset_source = Column(String(32), nullable=True)
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

        customer = relationship("Customer", back_populates="loans")



class Transaction(Base):
        __tablename__ = "transactions"

        id = Column(String(64), primary_key=True)
        customer_id = Column(String(64), ForeignKey(CUSTOMER_FK), nullable=True, index=True)
        from_account_id = Column(String(64), ForeignKey("accounts.id"), nullable=True, index=True)
        to_account_id = Column(String(64), ForeignKey("accounts.id"), nullable=True, index=True)
        amount = Column(Float, nullable=False)
        currency = Column(String(3), nullable=False, default="USD")
        transaction_type = Column(String(48), nullable=False)
        occurred_at = Column(DateTime(timezone=True), nullable=False)
        attributes = Column(JSON, nullable=False, default=dict)



class Document(Base):
        __tablename__ = "documents"
        id = Column(String(64), primary_key=True, default=_uuid)
        customer_id = Column(String(64), ForeignKey(CUSTOMER_FK), nullable=True, index=True)
        file_name = Column(String(255), nullable=False)
        document_type = Column(String(64), nullable=True)
        status = Column(String(32), nullable=False, default="queued")
        chunks_indexed = Column(Integer, nullable=False, default=0)
        vector_indexed = Column(Boolean, nullable=False, default=False)
        graph_indexed = Column(Boolean, nullable=False, default=False)
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)



class Prediction(Base):
        __tablename__ = "predictions"
        id = Column(String(64), primary_key=True, default=_uuid)
        customer_id = Column(String(64), ForeignKey(CUSTOMER_FK), nullable=True, index=True)
        transaction_id = Column(String(64), ForeignKey("transactions.id"), nullable=True, index=True)
        task = Column(String(48), nullable=False, index=True)
        model_version = Column(String(120), nullable=False)
        probability = Column(Float, nullable=False)
        threshold = Column(Float, nullable=False)
        explanation = Column(JSON, nullable=False, default=dict)
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)



class InvestigationCase(Base):
        __tablename__ = "investigation_cases"
        id = Column(String(64), primary_key=True, default=_uuid)
        customer_id = Column(String(64), ForeignKey(CUSTOMER_FK), nullable=True, index=True)
        transaction_id = Column(String(64), ForeignKey("transactions.id"), nullable=True, index=True)
        case_type = Column(String(48), nullable=False)
        status = Column(String(32), nullable=False, default="open")
        severity = Column(String(32), nullable=False)
        summary = Column(Text, nullable=False)
        owner = Column(String(120), nullable=True)
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
        updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)



class Report(Base):
        __tablename__ = "reports"
        id = Column(String(64), primary_key=True, default=_uuid)
        case_id = Column(String(64), ForeignKey("investigation_cases.id"), nullable=True, index=True)
        report_type = Column(String(48), nullable=False)
        content = Column(Text, nullable=False)
        generated_by = Column(String(64), nullable=True)
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)



class ChatMessage(Base):
        __tablename__ = "chat_messages"
        id = Column(String(64), primary_key=True, default=_uuid)
        session_id = Column(String(64), nullable=False, index=True)
        user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
        role = Column(String(16), nullable=False)
        content = Column(Text, nullable=False)
        sources = Column(JSON, nullable=False, default=list)
        created_at = Column(DateTime(timezone=True), nullable=False, default=_now)



class AuditLog(Base):
        __tablename__ = "audit_logs"
        id = Column(String(64), primary_key=True, default=_uuid)

event_type = Column(String(80), nullable=False, index=True)
actor = Column(String(120), nullable=False)
details = Column(JSON, nullable=False, default=dict)
created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
