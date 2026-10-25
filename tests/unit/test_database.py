import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.database.models import Account, AuditLog, Base, Customer, Transaction, User
from src.database.postgres import check_database, create_database_engine, init_db
from src.database.redis import cache_delete, cache_get, cache_set, check_redis


class FakeRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, ex=None):
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)

    def ping(self):
        return True


@pytest.fixture
def database_session():
    test_engine = create_database_engine("sqlite:///:memory:")
    init_db(test_engine)
    session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def test_database_models_persist_customer_account_transaction_and_audit(database_session):
    database_session.add_all(
        [
            Customer(customer_id="customer-1", full_name="Analyst Test"),
            User(email="analyst@example.test", password_hash="hashed-value"),
        ]
    )
    database_session.flush()
    database_session.add_all(
        [
            Account(account_id="account-1", customer_id="customer-1", account_type="checking"),
            Transaction(
                transaction_id="transaction-1",
                customer_id="customer-1",
                step=4,
                transaction_type="TRANSFER",
                amount=120.50,
            ),
            AuditLog(action="created", resource_type="customer", resource_id="customer-1"),
        ]
    )
    database_session.commit()

    assert database_session.scalar(select(Account).where(Account.account_id == "account-1"))
    transaction = database_session.get(Transaction, "transaction-1")
    assert float(transaction.amount) == pytest.approx(120.50)
    assert database_session.scalar(select(AuditLog).where(AuditLog.resource_id == "customer-1"))


def test_user_email_is_unique(database_session):
    database_session.add_all(
        [
            User(email="same@example.test", password_hash="one"),
            User(email="same@example.test", password_hash="two"),
        ]
    )
    with pytest.raises(IntegrityError):
        database_session.commit()


def test_sqlite_engine_can_initialize_and_be_checked():
    test_engine = create_database_engine("sqlite:///:memory:")
    init_db(test_engine)

    assert check_database(test_engine)

    test_engine.dispose()


def test_redis_json_cache_round_trip_with_injected_client():
    client = FakeRedis()
    value = {"risk": 0.82, "sources": ["RBI"]}

    assert cache_set("case:1", value, ttl_seconds=30, client=client)
    assert cache_get("case:1", client=client) == value
    assert check_redis(client)
    assert cache_delete("case:1", client=client)
    assert cache_get("case:1", client=client) is None