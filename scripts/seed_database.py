"""Initialize the local PostgreSQL schema and optionally add synthetic demo rows."""
import argparse
import os
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, JSON, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
Base = declarative_base()
CUSTOMER_FOREIGN_KEY = "customers.id"
class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(64), primary_key=True)
    name = Column(String(160), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), ForeignKey(CUSTOMER_FOREIGN_KEY), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    transaction_type = Column(String(48), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    attributes = Column(JSON, nullable=False, default=dict)
class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), ForeignKey(CUSTOMER_FOREIGN_KEY), nullable=True, index=True)
    transaction_id = Column(String(64), ForeignKey("transactions.id"), nullable=True, index=True)
    task = Column(String(48), nullable=False, index=True)
    model_version = Column(String(120), nullable=False)
    probability = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    explanation = Column(JSON, nullable=False, default=dict)
class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), ForeignKey(CUSTOMER_FOREIGN_KEY), nullable=True, index=True)
    transaction_id = Column(String(64), ForeignKey("transactions.id"), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="open")
    severity = Column(String(32), nullable=False)
    summary = Column(Text, nullable=False)
    is_synthetic = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(64), primary_key=True)
    event_type = Column(String(80), nullable=False, index=True)
    actor = Column(String(120), nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False)
def seed_demo(session):
    now = datetime.now(timezone.utc)
    customer_id = "demo_customer_001"
    transaction_id = "demo_transaction_001"
    session.merge(Customer(id=customer_id, name="Synthetic Demo Customer", created_at=now))
    session.merge(Transaction(
        id=transaction_id,
        customer_id=customer_id,
        amount=1250.00,
        currency="USD",
        transaction_type="DEMO_TRANSFER",
        occurred_at=now,
        attributes={"synthetic": True, "purpose": "local development seed"},
    ))
    session.merge(Prediction(
        id="demo_prediction_001",
        customer_id=customer_id,
        transaction_id=transaction_id,
        task="fraud_demo",
        model_version="synthetic-seed-no-model",
        probability=0.0,
        threshold=0.5,
        created_at=now,
        explanation={"synthetic": True, "not_a_model_output": True},
    ))
    session.merge(InvestigationCase(
        id="demo_case_001",
        customer_id=customer_id,
        transaction_id=transaction_id,
        status="open",
        severity="informational",
        summary="Synthetic development record; not a real alert or customer.",
        is_synthetic=True,
        created_at=now,
    ))
    session.merge(AuditLog(
        id="demo_seed_event_001",
        event_type="demo_seeded",
        actor="scripts.seed_database",
        details={"synthetic": True, "customer_id": customer_id},
        created_at=now,
    ))
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Insert clearly marked synthetic development re
cords")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="Defaults to DATABASE_U
RL")
    args = parser.parse_args()
    if not args.database_url:
        parser.error("Set DATABASE_URL or pass --database-url")
    if args.database_url.startswith("postgresql://"):
        args.database_url = args.database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(args.database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    if args.demo:
        session_factory = sessionmaker(bind=engine)
        with session_factory.begin() as session:
            seed_demo(session)
    print("Database schema initialized%s." % (" with synthetic demo records" if args.demo else ""))
if __name__ == "__main__":
    main()
