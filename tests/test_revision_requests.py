"""Integration tests: revision requests."""
import pytest

from helpers import error_code, make_project, make_revision


@pytest.fixture
def project(client, alice):
    return make_project(client, alice, agreed_revisions=3)


def test_create_revision_request(client, alice, project):
    response = client.post(f"/projects/{project['id']}/revision-requests", headers=alice, json={"description": "  Bigger logo  "})
    assert response.status_code == 201
    body = response.get_json()
    assert body["description"] == "Bigger logo" and body["status"] == "Pending" and body["is_extra"] is False


@pytest.mark.parametrize(
    "body",
    [
        {}, {"description": ""}, {"description": "   "}, {"description": "a" * 501}, {"description": None},
        {"description": "x", "is_extra": False}, {"description": "x", "status": "Completed"},
    ],
)
def test_create_rejects_invalid_input(client, alice, project, body):
    response = client.post(f"/projects/{project['id']}/revision-requests", headers=alice, json=body)
    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"


def test_create_rejects_a_body_that_is_not_a_json_object(client, alice, project):
    url = f"/projects/{project['id']}/revision-requests"
    assert client.post(url, headers=alice, data="hello").status_code == 400
    assert client.post(url, headers=alice, json=["a"]).status_code == 400


def test_create_accepts_exactly_500_characters(client, alice, project):
    response = client.post(f"/projects/{project['id']}/revision-requests", headers=alice, json={"description": "a" * 500})
    assert response.status_code == 201


def test_list_and_status_filter(client, alice, project):
    first = make_revision(client, alice, project["id"])
    make_revision(client, alice, project["id"])
    client.patch(f"/revision-requests/{first['id']}", headers=alice, json={"status": "Completed"})
    url = f"/projects/{project['id']}/revision-requests"
    assert client.get(url, headers=alice).get_json()["total"] == 2
    assert client.get(url + "?status=Pending", headers=alice).get_json()["total"] == 1
    assert client.get(url + "?status=banana", headers=alice).status_code == 400
    assert client.get(url + "?status=pending", headers=alice).status_code == 400  # case-sensitive


def test_get_one_update_and_delete(client, alice, project):
    revision = make_revision(client, alice, project["id"])
    url = f"/revision-requests/{revision['id']}"
    assert client.get(url, headers=alice).get_json()["project_id"] == project["id"]
    body = client.patch(url, headers=alice, json={"description": "New", "status": "Completed"}).get_json()
    assert body["description"] == "New" and body["status"] == "Completed"
    assert client.delete(url, headers=alice).status_code == 204
    assert client.get(url, headers=alice).status_code == 404
    assert client.delete(url, headers=alice).status_code == 404


@pytest.mark.parametrize(
    "body", [{}, {"status": "Done"}, {"status": "pending"}, {"project_id": 2}, {"is_extra": True}, {"description": None}, {"description": ""}]
)
def test_update_rejects_invalid_bodies(client, alice, project, body):
    revision = make_revision(client, alice, project["id"])
    url = f"/revision-requests/{revision['id']}"
    assert client.patch(url, headers=alice, json=body).status_code == 400
    assert client.get(url, headers=alice).get_json()["description"] == "Make it bigger"  # unchanged


def test_missing_records_return_404(client, alice):
    assert client.get("/revision-requests/999", headers=alice).status_code == 404
    assert client.patch("/revision-requests/999", headers=alice, json={"status": "Completed"}).status_code == 404
    assert client.delete("/revision-requests/999", headers=alice).status_code == 404
    assert client.get("/projects/999/revision-requests", headers=alice).status_code == 404
    assert client.post("/projects/999/revision-requests", headers=alice, json={"description": "x"}).status_code == 404


def test_other_users_requests_are_forbidden_and_untouched(client, alice, bob, project):
    revision = make_revision(client, alice, project["id"])
    url = f"/revision-requests/{revision['id']}"
    assert client.get(url, headers=bob).status_code == 403
    assert client.patch(url, headers=bob, json={"status": "Rejected"}).status_code == 403
    assert client.delete(url, headers=bob).status_code == 403
    assert client.get(f"/projects/{project['id']}/revision-requests", headers=bob).status_code == 403
    assert client.post(f"/projects/{project['id']}/revision-requests", headers=bob, json={"description": "x"}).status_code == 403
    assert client.get(url, headers=alice).get_json()["status"] == "Pending"
