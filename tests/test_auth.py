"""Integration tests: registration, login, and the 401 rule for protected routes."""
import datetime

import pytest
from flask_jwt_extended import create_access_token

from helpers import PASSWORD, error_code
from models import User

PROTECTED = [
    ("get", "/clients"), ("post", "/clients"), ("get", "/clients/1"), ("patch", "/clients/1"),
    ("delete", "/clients/1"), ("get", "/clients/1/projects"),
    ("get", "/projects"), ("post", "/projects"), ("get", "/projects/1"), ("patch", "/projects/1"),
    ("delete", "/projects/1"), ("get", "/projects/1/revision-requests"),
    ("post", "/projects/1/revision-requests"),
    ("get", "/revision-requests/1"), ("patch", "/revision-requests/1"), ("delete", "/revision-requests/1"),
]


def register(client, **overrides):
    body = {"username": "newbie", "email": "newbie@example.com", "password": PASSWORD, **overrides}
    return client.post("/auth/register", json=body)


def test_register_returns_the_user_without_any_password(client):
    response = register(client, email="  NewBie@Example.com ")
    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "newbie@example.com"
    assert "password" not in body and "password_hash" not in body


def test_password_is_stored_as_a_bcrypt_hash(client, app):
    register(client)
    user = User.query.filter_by(email="newbie@example.com").one()
    assert user.password_hash.startswith("$2b$")
    assert PASSWORD not in user.password_hash


def test_duplicate_email_or_username_returns_409(client):
    register(client)
    assert register(client, username="other").status_code == 409
    assert register(client, email="other@example.com").status_code == 409
    assert error_code(register(client)) == "CONFLICT"


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "not-an-email"}, {"password": "short"}, {"username": "ab"}, {"username": "has space"},
        {"role": "admin"},  # unknown field
    ],
)
def test_register_rejects_invalid_input(client, overrides):
    response = register(client, **overrides)
    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"


def test_register_rejects_missing_fields_and_non_json(client):
    assert client.post("/auth/register", json={}).status_code == 400
    assert client.post("/auth/register", data="hello").status_code == 400


@pytest.mark.parametrize("body", [{}, {"email": "a@example.com"}, {"email": "bad", "password": PASSWORD}, {"email": "a@example.com", "password": "x"}])
def test_login_rejects_invalid_input(client, body):
    response = client.post("/auth/login", json=body)
    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"


def test_login_returns_a_bearer_token(client):
    register(client)
    response = client.post("/auth/login", json={"email": "newbie@example.com", "password": PASSWORD})
    assert response.status_code == 200
    assert response.get_json()["token_type"] == "Bearer"
    assert len(response.get_json()["access_token"]) > 50


def test_login_email_is_case_insensitive(client):
    register(client)
    response = client.post("/auth/login", json={"email": "NEWBIE@example.com", "password": PASSWORD})
    assert response.status_code == 200


def test_wrong_password_and_unknown_email_give_the_same_401(client):
    register(client)
    wrong_password = client.post("/auth/login", json={"email": "newbie@example.com", "password": "WrongPass123"})
    unknown_email = client.post("/auth/login", json={"email": "ghost@example.com", "password": "WrongPass123"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.get_json() == unknown_email.get_json()


@pytest.mark.parametrize("method, path", PROTECTED)
def test_every_protected_route_needs_a_token(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401
    assert error_code(response) == "UNAUTHORIZED"


def test_invalid_tokens_are_rejected(client):
    assert client.get("/projects", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/projects", headers={"Authorization": "Token abc"}).status_code == 401


def test_expired_token_is_rejected_with_its_own_code(client, app):
    expired = create_access_token(identity="1", expires_delta=datetime.timedelta(seconds=-5))
    response = client.get("/projects", headers={"Authorization": "Bearer " + expired})
    assert response.status_code == 401
    assert error_code(response) == "TOKEN_EXPIRED"
