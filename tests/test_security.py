"""Security basics: rate limiting, CORS, headers, safe errors, and hostile input."""
from unittest import mock

import pytest

from app import limiter
from helpers import PASSWORD, error_code, make_client, sign_up_and_log_in


def test_login_is_rate_limited(client):
    limiter.enabled = True
    limiter.reset()
    body = {"email": "nobody@example.com", "password": PASSWORD}
    statuses = [client.post("/auth/login", json=body).status_code for _ in range(11)]
    assert statuses[:10] == [401] * 10          # the first 10 attempts are answered normally
    assert statuses[10] == 429                   # the 11th is blocked
    blocked = client.post("/auth/login", json=body)
    assert error_code(blocked) == "TOO_MANY_REQUESTS"
    assert "Retry-After" in blocked.headers


def test_register_is_rate_limited(client):
    limiter.enabled = True
    limiter.reset()
    statuses = [
        client.post("/auth/register", json={"username": f"user{n}", "email": f"u{n}@example.com", "password": PASSWORD}).status_code
        for n in range(11)
    ]
    assert statuses[:10] == [201] * 10 and statuses[10] == 429


def test_other_routes_are_not_rate_limited(client, alice):
    limiter.enabled = True
    limiter.reset()
    assert all(client.get("/projects", headers=alice).status_code == 200 for _ in range(30))


def test_cors_is_closed_by_default(client, alice):
    response = client.get("/projects", headers={**alice, "Origin": "https://evil.example.com"})
    assert "Access-Control-Allow-Origin" not in response.headers
    preflight = client.options("/projects", headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"})
    assert "Access-Control-Allow-Origin" not in preflight.headers


def test_security_headers_are_set(client, alice):
    response = client.get("/projects", headers=alice)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"


def test_unexpected_errors_hide_internal_details(client, alice):
    with mock.patch("app.db.session.query", side_effect=RuntimeError("secret detail /etc/passwd")):
        response = client.get("/projects", headers=alice)
    text = response.get_data(as_text=True)
    assert response.status_code == 500 and error_code(response) == "INTERNAL_ERROR"
    assert "secret" not in text and "Traceback" not in text and "/etc/passwd" not in text
    assert client.get("/projects", headers=alice).status_code == 200  # the app keeps working


def test_every_error_uses_the_same_json_shape(client, alice):
    responses = [
        client.get("/nope"),                                  # 404 unknown URL
        client.get("/projects/abc", headers=alice),           # 404 bad id
        client.delete("/auth/login"),                         # 405
        client.get("/projects"),                              # 401
        client.post("/projects", headers=alice, json={}),     # 400
    ]
    for response in responses:
        assert response.is_json
        assert set(response.get_json()["error"]) == {"code", "message"}


@pytest.mark.parametrize("path", ["/clients/99999999999999999999", "/projects/99999999999999999999/revision-requests", "/clients/0", "/clients/-1", "/clients/1.5"])
def test_invalid_or_huge_ids_return_404_not_500(client, alice, path):
    response = client.get(path, headers=alice)
    assert response.status_code == 404 and error_code(response) == "NOT_FOUND"


def test_huge_ids_in_a_body_return_400_not_500(client, alice):
    response = client.post("/projects", headers=alice, json={"title": "x", "agreed_revisions": 1, "client_id": 99999999999999999999})
    assert response.status_code == 400


def test_control_characters_are_rejected(client, alice):
    response = client.post("/clients", headers=alice, json={"name": "bad\u0000name", "email": "a@example.com"})
    assert response.status_code == 400


def test_sql_injection_text_is_stored_as_plain_data(client, alice):
    attack = "'; DROP TABLE users; --"
    created = make_client(client, alice, name=attack, email="x@example.com")
    assert created["name"] == attack
    assert client.get("/clients", headers=alice).get_json()["items"][0]["name"] == attack
    assert sign_up_and_log_in(client, "carol", "carol@example.com")  # the users table still exists


def test_html_in_text_is_returned_as_plain_json_text(client, alice):
    created = make_client(client, alice, name="<script>alert(1)</script>", email="y@example.com")
    response = client.get(f"/clients/{created['id']}", headers=alice)
    assert response.content_type.startswith("application/json")
    assert response.get_json()["name"] == "<script>alert(1)</script>"
