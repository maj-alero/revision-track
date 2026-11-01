"""Small helpers that create data through the real API."""
PASSWORD = "Password123!"


def sign_up_and_log_in(client, username, email, password=PASSWORD):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": "Bearer " + response.get_json()["access_token"]}


def make_client(client, headers, name="Acme", email="hello@acme.example.com"):
    return client.post("/clients", headers=headers, json={"name": name, "email": email}).get_json()


def make_project(client, headers, title="Logo", agreed_revisions=2, **extra):
    body = {"title": title, "agreed_revisions": agreed_revisions, **extra}
    return client.post("/projects", headers=headers, json=body).get_json()


def make_revision(client, headers, project_id, description="Make it bigger"):
    return client.post(
        f"/projects/{project_id}/revision-requests", headers=headers, json={"description": description}
    ).get_json()


def error_code(response):
    body = response.get_json(silent=True) or {}
    return body.get("error", {}).get("code")
