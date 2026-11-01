"""The core rule: a request is extra once the project's agreed revisions are used up.
Rejected requests do not count."""
import pytest

from app import is_extra
from helpers import make_project, make_revision
from models import Project, RevisionRequest, User, db


def build_project(limit, statuses):
    """Create a project directly in the database with one existing request per status."""
    user = User(username="rule_user", email="rule@example.com", password_hash="x")
    db.session.add(user)
    db.session.commit()
    project = Project(user_id=user.id, title="Rule test", agreed_revisions=limit)
    db.session.add(project)
    db.session.commit()
    for status in statuses:
        db.session.add(RevisionRequest(project_id=project.id, description="x", status=status))
    db.session.commit()
    return project


@pytest.mark.parametrize(
    "limit, existing, expected",
    [
        (3, [], False),
        (3, ["Pending", "Pending"], False),                    # 2 used of 3
        (3, ["Pending", "Completed", "Pending"], True),        # limit used up
        (3, ["Pending", "Completed", "Pending", "Pending"], True),
        (3, ["Pending", "Rejected", "Pending"], False),        # the rejected one does not count
        (3, ["Rejected", "Rejected", "Rejected"], False),
        (1, ["Rejected"], False),
        (1, ["Completed"], True),                              # completed requests still count
        (0, [], True),                                         # a limit of zero: everything is extra
    ],
)
def test_is_extra_boundaries(app, limit, existing, expected):
    assert is_extra(build_project(limit, existing)) is expected


def test_flag_flips_when_the_limit_is_used_up(client, alice):
    project = make_project(client, alice, agreed_revisions=2)
    flags = [make_revision(client, alice, project["id"])["is_extra"] for _ in range(4)]
    assert flags == [False, False, True, True]


def test_rejecting_requests_frees_up_the_limit(client, alice):
    project = make_project(client, alice, agreed_revisions=1)
    first = make_revision(client, alice, project["id"])
    assert make_revision(client, alice, project["id"])["is_extra"] is True
    client.patch(f"/revision-requests/{first['id']}", headers=alice, json={"status": "Rejected"})
    # one request is rejected and one counts, so the limit of 1 is still used up
    assert make_revision(client, alice, project["id"])["is_extra"] is True


def test_saved_flags_are_not_recomputed_later(client, alice):
    project = make_project(client, alice, agreed_revisions=1)
    make_revision(client, alice, project["id"])
    extra = make_revision(client, alice, project["id"])
    client.patch(f"/projects/{project['id']}", headers=alice, json={"agreed_revisions": 10})
    assert client.get(f"/revision-requests/{extra['id']}", headers=alice).get_json()["is_extra"] is True
