"""Unit tests: request validation rules, with no database or HTTP involved."""
import pytest
from pydantic import ValidationError

from schemas import (
    ClientCreate,
    ClientUpdate,
    LoginBody,
    ProjectCreate,
    ProjectUpdate,
    RegisterBody,
    RevisionRequestCreate,
    RevisionRequestUpdate,
)


def test_email_is_trimmed_and_lowercased():
    body = RegisterBody(username="amy", email="  Amy@Example.COM ", password="Password123!")
    assert body.email == "amy@example.com"


@pytest.mark.parametrize("email", ["nope", "a@b", "@example.com", "a b@example.com", ""])
def test_bad_emails_are_rejected(email):
    with pytest.raises(ValidationError):
        LoginBody(email=email, password="Password123!")


@pytest.mark.parametrize("password", ["short", "a" * 73, "é" * 40])  # 40 characters but 80 bytes
def test_password_length_limits(password):
    with pytest.raises(ValidationError):
        RegisterBody(username="amy", email="amy@example.com", password=password)


@pytest.mark.parametrize("username", ["ab", "has space", "semi;colon", "<script>"])
def test_bad_usernames_are_rejected(username):
    with pytest.raises(ValidationError):
        RegisterBody(username=username, email="amy@example.com", password="Password123!")


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        RevisionRequestCreate(description="ok", is_extra=True)
    with pytest.raises(ValidationError):
        ClientCreate(name="x", email="a@example.com", user_id=2)


def test_revision_description_is_trimmed_and_limited():
    assert RevisionRequestCreate(description="  hello  ").description == "hello"
    assert RevisionRequestCreate(description="a" * 500).description == "a" * 500
    for bad in ["", "   ", "a" * 501, "bad\x00text", "esc\x1b[31m"]:
        with pytest.raises(ValidationError):
            RevisionRequestCreate(description=bad)


def test_status_values_are_case_sensitive():
    assert RevisionRequestUpdate(status="Rejected").status == "Rejected"
    with pytest.raises(ValidationError):
        RevisionRequestUpdate(status="rejected")
    with pytest.raises(ValidationError):
        ProjectCreate(title="x", agreed_revisions=1, status="active")


@pytest.mark.parametrize("value", ["3", True, 1.5, -1, 1001, None])
def test_agreed_revisions_must_be_a_real_whole_number_in_range(value):
    with pytest.raises(ValidationError):
        ProjectCreate(title="x", agreed_revisions=value)


def test_ids_must_be_real_positive_numbers_within_database_range():
    assert ProjectCreate(title="x", agreed_revisions=1, client_id=5).client_id == 5
    for bad in ["1", True, 0, -3, 2147483648]:
        with pytest.raises(ValidationError):
            ProjectCreate(title="x", agreed_revisions=1, client_id=bad)


def test_patch_bodies_need_at_least_one_field():
    for schema in (ClientUpdate, ProjectUpdate, RevisionRequestUpdate):
        with pytest.raises(ValidationError):
            schema()


def test_only_some_project_fields_may_be_cleared_with_null():
    assert ProjectUpdate(client_id=None).client_id is None
    assert ProjectUpdate(description=None).description is None
    for field in ("title", "agreed_revisions", "status"):
        with pytest.raises(ValidationError):
            ProjectUpdate(**{field: None})
    with pytest.raises(ValidationError):
        ClientUpdate(name=None)
