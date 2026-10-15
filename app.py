import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from models import Project, RevisionRequest, db

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///revisiontrack.db")
app.json.sort_keys = False
db.init_app(app)

REVISION_STATUSES = ["Pending", "Completed", "Rejected"]

#HELPER FUNCTIONS

def error(status, code, message):
    """Every error uses the same JSON shape."""
    return jsonify({"error": {"code": code, "message": message}}), status


def project_json(project):
    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "client_id": project.client_id,
        "agreed_revisions": project.agreed_revisions,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
    }


def revision_json(revision):
    return {
        "id": revision.id,
        "project_id": revision.project_id,
        "description": revision.description,
        "status": revision.status,
        "is_extra": revision.is_extra,
        "created_at": revision.created_at.isoformat(),
    }


def validate_body(data, allowed_fields):
    """Return an error message if the request body is invalid, otherwise None."""
    if not isinstance(data, dict) or not data:
        return "Request body must be a non-empty JSON object"
    unknown = set(data) - set(allowed_fields)
    if unknown:
        return "Not allowed: " + ", ".join(sorted(unknown))
    if "description" in data:
        text = data["description"]
        if not isinstance(text, str) or not text.strip() or len(text.strip()) > 500:
            return "description must be a non-empty string of at most 500 characters"
    if "status" in data and data["status"] not in REVISION_STATUSES:
        return "status must be one of: " + ", ".join(REVISION_STATUSES)
    return None


#Projects (read-only endpoints) 

@app.route("/projects", methods=["GET"])
def list_projects():
    projects = Project.query.order_by(Project.id).all()
    return jsonify([project_json(p) for p in projects])


@app.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    project = db.get_or_404(Project, project_id, description=f"Project {project_id} not found")
    return jsonify(project_json(project))


#Revision Requests CRUD endpoints

@app.route("/projects/<int:project_id>/revision-requests", methods=["POST"])
def create_revision_request(project_id):
    project = db.get_or_404(Project, project_id, description=f"Project {project_id} not found")

    data = request.get_json(silent=True)
    problem = validate_body(data, ["description"])
    if problem:
        return error(400, "VALIDATION_ERROR", problem)

    
    used = RevisionRequest.query.filter(
        RevisionRequest.project_id == project.id,
        RevisionRequest.status != "Rejected",
    ).count()

    revision = RevisionRequest(
        project_id=project.id,
        description=data["description"].strip(),
        is_extra=used >= project.agreed_revisions,
    )
    db.session.add(revision)
    db.session.commit()
    return jsonify(revision_json(revision)), 201


@app.route("/projects/<int:project_id>/revision-requests", methods=["GET"])
def list_revision_requests(project_id):
    db.get_or_404(Project, project_id, description=f"Project {project_id} not found")

    query = RevisionRequest.query.filter_by(project_id=project_id)
    status = request.args.get("status")
    if status is not None:
        if status not in REVISION_STATUSES:
            return error(400, "VALIDATION_ERROR", "status must be one of: " + ", ".join(REVISION_STATUSES))
        query = query.filter_by(status=status)

    revisions = query.order_by(RevisionRequest.id).all()
    return jsonify([revision_json(r) for r in revisions])


@app.route("/revision-requests/<int:revision_id>", methods=["GET"])
def get_revision_request(revision_id):
    revision = db.get_or_404(RevisionRequest, revision_id, description=f"Revision request {revision_id} not found")
    return jsonify(revision_json(revision))


@app.route("/revision-requests/<int:revision_id>", methods=["PATCH"])
def update_revision_request(revision_id):
    revision = db.get_or_404(RevisionRequest, revision_id, description=f"Revision request {revision_id} not found")

    data = request.get_json(silent=True)
    problem = validate_body(data, ["description", "status"])
    if problem:
        return error(400, "VALIDATION_ERROR", problem)

    if "description" in data:
        revision.description = data["description"].strip()
    if "status" in data:
        revision.status = data["status"]
    db.session.commit()
    return jsonify(revision_json(revision))


@app.route("/revision-requests/<int:revision_id>", methods=["DELETE"])
def delete_revision_request(revision_id):
    revision = db.get_or_404(RevisionRequest, revision_id, description=f"Revision request {revision_id} not found")
    db.session.delete(revision)
    db.session.commit()
    return "", 204


@app.errorhandler(404)
def not_found(err):
    return error(404, "NOT_FOUND", err.description)