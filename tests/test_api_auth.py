import uuid
from datetime import timedelta

from schema_extractor.security import create_access_token

CREDENTIALS = {"email": "Jan@Example.com", "password": "correct-horse-battery"}


def register(client, **overrides):
    return client.post("/auth/register", json={**CREDENTIALS, **overrides})


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_register_returns_user_without_password(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jan@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_duplicate_email_is_rejected_case_insensitively(client):
    assert register(client).status_code == 201
    assert register(client, email="JAN@example.com").status_code == 409


def test_short_password_is_rejected(client):
    assert register(client, password="short").status_code == 422


def test_invalid_email_is_rejected(client):
    assert register(client, email="not-an-email").status_code == 422


def test_login_returns_working_token(client):
    register(client)
    response = login(client, "jan@example.com", CREDENTIALS["password"])
    assert response.status_code == 200

    token = response.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "jan@example.com"


def test_wrong_password_and_unknown_email_give_identical_error(client):
    register(client)
    wrong = login(client, "jan@example.com", "wrong-password-123")
    unknown = login(client, "nobody@example.com", "whatever-password")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    garbage = {"Authorization": "Bearer garbage"}
    assert client.get("/auth/me", headers=garbage).status_code == 401


def test_expired_token_is_rejected(client):
    user_id = register(client).json()["id"]
    token = create_access_token(uuid.UUID(user_id), expires_delta=timedelta(minutes=-1))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
