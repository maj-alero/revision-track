"""Test setup. The environment is set BEFORE the app is imported, so the tests always use an
in-memory database and a throwaway secret, never your real .env values."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-for-the-test-suite-0123456789"
os.environ["BCRYPT_ROUNDS"] = "4"  # the minimum: hashing is slow on purpose, which only slows the tests
os.environ.pop("CORS_ORIGINS", None)

import pytest  # noqa: E402

from app import app as flask_app  # noqa: E402
from app import limiter  # noqa: E402
from helpers import sign_up_and_log_in  # noqa: E402
from models import db  # noqa: E402


@pytest.fixture
def app():
    """A fresh empty database for every test."""
    limiter.enabled = False  # the rate limit has its own test
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def alice(client):
    """Auth headers for a registered, logged-in user."""
    return sign_up_and_log_in(client, "alice", "alice@example.com")


@pytest.fixture
def bob(client):
    """A second user, used to test that users cannot reach each other's data."""
    return sign_up_and_log_in(client, "bob", "bob@example.com")
