"""List endpoints are paginated: ?page= and ?per_page=, with a total in every response."""
import pytest

from helpers import make_client, make_project, make_revision


@pytest.fixture
def twenty_five_clients(client, alice):
    for number in range(25):
        make_client(client, alice, name=f"Client {number}", email=f"c{number}@example.com")


def test_default_page_shape_and_size(client, alice, twenty_five_clients):
    body = client.get("/clients", headers=alice).get_json()
    assert len(body["items"]) == 20
    assert (body["page"], body["per_page"], body["total"], body["pages"]) == (1, 20, 25, 2)


def test_second_page_holds_the_rest_in_order(client, alice, twenty_five_clients):
    first = client.get("/clients", headers=alice).get_json()["items"]
    second = client.get("/clients?page=2", headers=alice).get_json()["items"]
    assert len(second) == 5
    ids = [c["id"] for c in first + second]
    assert ids == sorted(ids) and len(set(ids)) == 25


def test_custom_page_size(client, alice, twenty_five_clients):
    body = client.get("/clients?per_page=10&page=3", headers=alice).get_json()
    assert len(body["items"]) == 5 and body["pages"] == 3


def test_a_page_past_the_end_is_empty_not_an_error(client, alice, twenty_five_clients):
    body = client.get("/clients?page=99", headers=alice).get_json()
    assert body["items"] == [] and body["total"] == 25


def test_maximum_page_size_is_allowed(client, alice, twenty_five_clients):
    assert len(client.get("/clients?per_page=100", headers=alice).get_json()["items"]) == 25


@pytest.mark.parametrize(
    "query", ["page=0", "page=-1", "page=abc", "page=1.5", "per_page=0", "per_page=101", "per_page=abc", "page=99999999", "per_page=1000"]
)
def test_invalid_paging_values_return_400(client, alice, query):
    response = client.get(f"/clients?{query}", headers=alice)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_an_empty_list_still_has_the_page_shape(client, alice):
    assert client.get("/clients", headers=alice).get_json() == {"items": [], "page": 1, "per_page": 20, "total": 0, "pages": 0}


def test_every_list_endpoint_is_paginated(client, alice):
    owner = make_client(client, alice)
    project = make_project(client, alice, client_id=owner["id"])
    for _ in range(3):
        make_revision(client, alice, project["id"])
    for url in ("/clients", "/projects", f"/clients/{owner['id']}/projects", f"/projects/{project['id']}/revision-requests"):
        body = client.get(url + "?per_page=1", headers=alice).get_json()
        assert len(body["items"]) == 1 and body["per_page"] == 1
    assert client.get(f"/projects/{project['id']}/revision-requests?per_page=2", headers=alice).get_json()["pages"] == 2


def test_total_respects_the_status_filter(client, alice):
    project = make_project(client, alice)
    make_revision(client, alice, project["id"])
    body = client.get(f"/projects/{project['id']}/revision-requests?status=Completed", headers=alice).get_json()
    assert body["total"] == 0 and body["pages"] == 0


@pytest.mark.parametrize("path", ["/clients", "/projects", "/clients/{client}/projects", "/projects/{project}/revision-requests"])
def test_invalid_paging_values_are_rejected_on_every_list_endpoint(client, alice, path):
    owner = make_client(client, alice)
    project = make_project(client, alice, client_id=owner["id"])
    url = path.format(client=owner["id"], project=project["id"])
    assert client.get(url + "?page=0", headers=alice).status_code == 400
    assert client.get(url + "?per_page=101", headers=alice).status_code == 400
