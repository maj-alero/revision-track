"""Start-up behaviour that depends on environment variables. Each case runs the app in a fresh
Python process, because the settings are read when the app is first imported."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GOOD_SECRET = "a" * 40


def run(code, **env):
    full_env = {**os.environ, "DATABASE_URL": "sqlite:///:memory:", "BCRYPT_ROUNDS": "4", **env}
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=full_env, capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("secret", ["short", "CHANGE_ME" + "x" * 40, ""])
def test_the_app_refuses_to_start_with_a_weak_or_placeholder_secret(secret):
    result = run("import app", JWT_SECRET_KEY=secret)
    assert result.returncode != 0
    assert "JWT_SECRET_KEY" in result.stderr


def test_the_app_refuses_to_start_without_a_secret():
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"}
    result = subprocess.run([sys.executable, "-c", "import app"], cwd=ROOT, env={**env, "DATABASE_URL": "sqlite:///:memory:"},
                            capture_output=True, text=True, timeout=60)
    assert result.returncode != 0


def test_the_app_starts_with_a_good_secret():
    assert run("import app", JWT_SECRET_KEY=GOOD_SECRET).returncode == 0


CODE_FOR_PROXY_TEST = """
from app import app
from models import db
with app.app_context():
    db.create_all()
client = app.test_client()
body = {"email": "nobody@example.com", "password": "Password123!"}
def attempt(address):
    return client.post("/auth/login", json=body, headers={"X-Forwarded-For": address}).status_code
first = [attempt("1.1.1.1") for _ in range(11)]
print(first[-1], attempt("2.2.2.2"))
"""


def test_behind_a_proxy_each_real_client_address_gets_its_own_rate_limit():
    result = run(CODE_FOR_PROXY_TEST, JWT_SECRET_KEY=GOOD_SECRET, BEHIND_PROXY="1")
    assert result.stdout.split() == ["429", "401"]   # address 1 is blocked, address 2 is not


def test_without_the_proxy_setting_forwarded_addresses_are_ignored():
    result = run(CODE_FOR_PROXY_TEST, JWT_SECRET_KEY=GOOD_SECRET)
    assert result.stdout.split() == ["429", "429"]   # spoofing the header gains nothing
