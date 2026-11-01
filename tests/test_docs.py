"""The API documentation (docs/openapi.yaml) must stay in step with the real routes."""
import re
from pathlib import Path

import yaml
from openapi_spec_validator import validate

from app import app as flask_app

SPEC_FILE = Path(__file__).resolve().parent.parent / "docs" / "openapi.yaml"
DOC_ROUTES = {"static", "api_docs", "openapi_spec"}  # served by the app but not part of the API
METHODS = {"get", "post", "patch", "delete"}


def real_routes():
    found = set()
    for rule in flask_app.url_map.iter_rules():
        if rule.endpoint in DOC_ROUTES:
            continue
        path = re.sub(r"<(?:int:)?(\w+)>", r"{\1}", rule.rule)
        for method in rule.methods & {m.upper() for m in METHODS}:
            found.add((path, method.lower()))
    return found


def documented_routes():
    spec = yaml.safe_load(SPEC_FILE.read_text())
    return {(path, method) for path, item in spec["paths"].items() for method in item if method in METHODS}


def test_the_spec_is_valid_openapi():
    validate(yaml.safe_load(SPEC_FILE.read_text()))


def test_every_route_is_documented_and_nothing_extra_is():
    assert real_routes() == documented_routes()


def test_swagger_page_and_spec_are_served(client):
    page = client.get("/docs")
    assert page.status_code == 200 and "swagger-ui" in page.get_data(as_text=True)
    spec = client.get("/openapi.yaml")
    assert spec.status_code == 200
    assert yaml.safe_load(spec.get_data(as_text=True))["info"]["title"] == "RevisionTrack API"
