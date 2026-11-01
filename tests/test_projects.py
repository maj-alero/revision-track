"""Integration tests: projects."""
import pytest

from helpers import error_code, make_client, make_project, make_revision


def test_create_project_defaults(client, alice):
    response = client.post("/projects", headers=alice, json={"title": " Brand kit ", "agreed_revisions": 0})
    assert response.status_code == 201
    body = response.get_json()
    assert body["title"] == "Brand kit" and body["status"] == "Active"
    assert body["client_id"] is None and body["description"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"agreed_revisions": 1}, {"title": "x"}, {"title": "", "agreed_revisions": 1},
        {"title": "x", "agreed_revisions": -1}, {"title": "x", "agreed_revisions": "3"},
        {"title": "x", "agreed_revisions": True}, {"title": "x", "agreed_revisions": 1.5},
        {"title": "x", "agreed_revisions": 5000}, {"title": "x", "agreed_revisions": 1, "status": "Done"},
        {"title": "x", "agreed_revisions": 1, "status": "active"}, {"title": "x", "agreed_revisions": 1, "user_id": 2},
        {"title": "x", "agreed_revisions": 1, "client_id": "1"},
    ],
)
def test_create_project_rejects_invalid_input(client, alice, body):
    response = client.post("/projects", headers=alice, json=body)
    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"


def test_project_needs_one_of_your_own_clients(client, alice, bob):
    others = make_client(client, bob)
    for client_id in (others["id"], 999):
        response = client.post("/projects", headers=alice, json={"title": "x", "agreed_revisions": 1, "client_id": client_id})
        assert response.status_code == 400


def test_update_project_and_detach_client(client, alice):
    owner = make_client(client, alice)
    project = make_project(client, alice, client_id=owner["id"])
    url = f"/projects/{project['id']}"
    body = client.patch(url, headers=alice, json={"status": "Completed", "agreed_revisions": 4}).get_json()
    assert body["status"] == "Completed" and body["agreed_revisions"] == 4
    assert client.patch(url, headers=alice, json={"client_id": None}).get_json()["client_id"] is None
    assert client.patch(url, headers=alice, json={"client_id": owner["id"]}).get_json()["client_id"] == owner["id"]
    assert client.patch(url, headers=alice, json={"description": None}).status_code == 200


@pytest.mark.parametrize(
    "body", [{}, {"title": None}, {"agreed_revisions": None}, {"status": None}, {"status": "x"}, {"agreed_revisions": -2}, {"user_id": 2}]
)
def test_update_project_rejects_invalid_bodies(client, alice, body):
    project = make_project(client, alice)
    assert client.patch(f"/projects/{project['id']}", headers=alice, json=body).status_code == 400


def test_cannot_move_a_project_to_someone_elses_client(client, alice, bob):
    project = make_project(client, alice)
    others = make_client(client, bob)
    response = client.patch(f"/projects/{project['id']}", headers=alice, json={"client_id": others["id"]})
    assert response.status_code == 400


def test_deleting_a_project_deletes_its_revision_requests(client, alice):
    project = make_project(client, alice)
    revision = make_revision(client, alice, project["id"])
    assert client.delete(f"/projects/{project['id']}", headers=alice).status_code == 204
    assert client.get(f"/revision-requests/{revision['id']}", headers=alice).status_code == 404


def test_missing_project_returns_404(client, alice):
    assert client.get("/projects/999", headers=alice).status_code == 404
    assert client.patch("/projects/999", headers=alice, json={"title": "x"}).status_code == 404
    assert client.delete("/projects/999", headers=alice).status_code == 404


def test_other_users_projects_are_forbidden_and_untouched(client, alice, bob):
    project = make_project(client, alice)
    url = f"/projects/{project['id']}"
    assert client.get(url, headers=bob).status_code == 403
    assert client.patch(url, headers=bob, json={"title": "Hacked"}).status_code == 403
    assert client.delete(url, headers=bob).status_code == 403
    assert client.get(url, headers=alice).get_json()["title"] == "Logo"


def test_lists_only_show_your_own_projects(client, alice, bob):
    make_project(client, alice)
    make_project(client, bob, title="Bob's")
    titles = [p["title"] for p in client.get("/projects", headers=bob).get_json()["items"]]
    assert titles == ["Bob's"]
