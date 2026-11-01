"""Integration tests: clients (create, read, update, delete, and the failure cases)."""
import pytest

from helpers import error_code, make_client, make_project


def test_create_client_trims_and_lowercases(client, alice):
    response = client.post("/clients", headers=alice, json={"name": "  New Client ", "email": "Hello@New.Example.com"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "New Client" and body["email"] == "hello@new.example.com"
    assert "user_id" not in body


@pytest.mark.parametrize(
    "body",
    [
        {"email": "a@example.com"}, {"name": "x"}, {"name": "x", "email": "bad"}, {"name": " ", "email": "a@example.com"},
        {"name": "x" * 151, "email": "a@example.com"}, {"name": 5, "email": "a@example.com"},
        {"name": "x", "email": "a@example.com", "user_id": 2},
    ],
)
def test_create_client_rejects_invalid_input(client, alice, body):
    response = client.post("/clients", headers=alice, json=body)
    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"


def test_same_user_cannot_add_the_same_client_email_twice(client, alice):
    make_client(client, alice)
    response = client.post("/clients", headers=alice, json={"name": "Dup", "email": "hello@acme.example.com"})
    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"


def test_different_users_can_have_a_client_with_the_same_email(client, alice, bob):
    make_client(client, alice)
    response = client.post("/clients", headers=bob, json={"name": "Acme", "email": "hello@acme.example.com"})
    assert response.status_code == 201


def test_get_and_list_clients(client, alice):
    created = make_client(client, alice)
    assert client.get(f"/clients/{created['id']}", headers=alice).get_json()["id"] == created["id"]
    assert client.get("/clients", headers=alice).get_json()["total"] == 1


def test_update_client(client, alice):
    created = make_client(client, alice)
    response = client.patch(f"/clients/{created['id']}", headers=alice, json={"name": "Renamed"})
    assert response.status_code == 200 and response.get_json()["name"] == "Renamed"


def test_update_client_email_to_an_existing_one_returns_409(client, alice):
    make_client(client, alice, email="one@example.com")
    second = make_client(client, alice, name="Two", email="two@example.com")
    response = client.patch(f"/clients/{second['id']}", headers=alice, json={"email": "one@example.com"})
    assert response.status_code == 409


@pytest.mark.parametrize("body", [{}, {"name": None}, {"user_id": 2}, {"email": "bad"}])
def test_update_client_rejects_invalid_bodies(client, alice, body):
    created = make_client(client, alice)
    assert client.patch(f"/clients/{created['id']}", headers=alice, json=body).status_code == 400
    assert client.get(f"/clients/{created['id']}", headers=alice).get_json()["name"] == "Acme"  # unchanged


def test_deleting_a_client_keeps_its_projects(client, alice):
    created = make_client(client, alice)
    project = make_project(client, alice, client_id=created["id"])
    assert client.delete(f"/clients/{created['id']}", headers=alice).status_code == 204
    assert client.get(f"/clients/{created['id']}", headers=alice).status_code == 404
    kept = client.get(f"/projects/{project['id']}", headers=alice).get_json()
    assert kept["client_id"] is None


def test_client_projects_relationship_endpoint(client, alice):
    created = make_client(client, alice)
    make_project(client, alice, title="One", client_id=created["id"])
    make_project(client, alice, title="Not theirs")
    body = client.get(f"/clients/{created['id']}/projects", headers=alice).get_json()
    assert [p["title"] for p in body["items"]] == ["One"]


def test_missing_client_returns_404(client, alice):
    for method in ("get", "patch", "delete"):
        kwargs = {"json": {"name": "x"}} if method == "patch" else {}
        response = getattr(client, method)("/clients/999", headers=alice, **kwargs)
        assert response.status_code == 404 and error_code(response) == "NOT_FOUND"
    assert client.get("/clients/999/projects", headers=alice).status_code == 404


def test_other_users_clients_are_forbidden_and_untouched(client, alice, bob):
    created = make_client(client, alice)
    url = f"/clients/{created['id']}"
    assert client.get(url, headers=bob).status_code == 403
    assert client.patch(url, headers=bob, json={"name": "Hacked"}).status_code == 403
    assert client.delete(url, headers=bob).status_code == 403
    assert client.get(f"{url}/projects", headers=bob).status_code == 403
    assert error_code(client.get(url, headers=bob)) == "FORBIDDEN"
    assert client.get(url, headers=alice).get_json()["name"] == "Acme"


def test_lists_only_show_your_own_clients(client, alice, bob):
    make_client(client, alice)
    assert client.get("/clients", headers=bob).get_json()["items"] == []
