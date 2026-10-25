from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials

from src.api.auth import create_access_token, get_current_principal
from src.api.main import app
from src.api.middleware import RequestIDMiddleware
from src.api.schemas import TransactionPayload


def test_local_auth_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("API_AUTH_ENABLED", raising=False)

    assert get_current_principal(None)["auth"] == "disabled"


def test_auth_accepts_configured_static_bearer_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_BEARER_TOKEN", "local-test-token")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="local-test-token")

    assert get_current_principal(credentials)["auth"] == "static-bearer"


def test_auth_creates_and_validates_signed_access_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-signing-secret")
    token = create_access_token("analyst", expires_in_seconds=60)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    assert get_current_principal(credentials)["sub"] == "analyst"


def test_request_id_middleware_echoes_valid_id_and_generates_missing_id():
    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)

    @test_app.get("/")
    def read_root():
        return {"status": "ok"}

    client = TestClient(test_app)
    supplied = client.get("/", headers={"X-Request-ID": "client-request-7"})
    generated = client.get("/")

    assert supplied.headers["X-Request-ID"] == "client-request-7"
    assert generated.headers["X-Request-ID"]


def test_transaction_schema_preserves_extra_custom_fields():
    transaction = TransactionPayload.model_validate(
        {
            "step": 1,
            "type": "TRANSFER",
            "amount": 10,
            "oldbalanceOrg": 10,
            "newbalanceOrig": 0,
            "oldbalanceDest": 0,
            "newbalanceDest": 10,
            "channel": "mobile",
        }
    )

    assert transaction.to_transaction()["channel"] == "mobile"


def test_query_route_returns_supervisor_results_and_request_id(monkeypatch):
    from src.api.routes import investigations

    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    monkeypatch.setattr(
        investigations.supervisor_agent,
        "run",
        lambda request: {"question": request["question"], "findings": []},
    )

    response = TestClient(app).post("/api/query", json={"question": "KYC requirements?"})

    assert response.status_code == 200
    assert response.json()["question"] == "KYC requirements?"
    assert response.headers["X-Request-ID"]