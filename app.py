# import os

# from dotenv import load_dotenv
# from flask import Flask, jsonify, request
# from flask_bcrypt import Bcrypt

# from models import Project, RevisionRequest, db

# load_dotenv()

# app = Flask(__name__)
# app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///revisiontrack.db")
# app.json.sort_keys = False
# db.init_app(app)

# REVISION_STATUSES = ["Pending", "Completed", "Rejected"]

# #HELPER FUNCTIONS

# def error(status, code, message):
#     """Every error uses the same JSON shape."""
#     return jsonify({"error": {"code": code, "message": message}}), status


# def project_json(project):
#     return {
#         "id": project.id,
#         "title": project.title,
#         "description": project.description,
#         "client_id": project.client_id,
#         "agreed_revisions": project.agreed_revisions,
#         "status": project.status,
#         "created_at": project.created_at.isoformat(),
#     }


# def revision_json(revision):
#     return {
#         "id": revision.id,
#         "project_id": revision.project_id,
#         "description": revision.description,
#         "status": revision.status,
#         "is_extra": revision.is_extra,
#         "created_at": revision.created_at.isoformat(),
#     }


# def validate_body(data, allowed_fields):
#     """Return an error message if the request body is invalid, otherwise None."""
#     if not isinstance(data, dict) or not data:
#         return "Request body must be a non-empty JSON object"
#     unknown = set(data) - set(allowed_fields)
#     if unknown:
#         return "Not allowed: " + ", ".join(sorted(unknown))
#     if "description" in data:
#         text = data["description"]
#         if not isinstance(text, str) or not text.strip() or len(text.strip()) > 500:
#             return "description must be a non-empty string of at most 500 characters"
#     if "status" in data and data["status"] not in REVISION_STATUSES:
#         return "status must be one of: " + ", ".join(REVISION_STATUSES)
#     return None

# #Authentication endpoints

# @app.route("auth/register", methods=["POST"])
# def register():
#     data = request.get_json(silent=True)
#     if not data or "username" not in data or "email" not in data or "password" not in data:
#         return error(400, "VALIDATION_ERROR", "username, email, and password are required")
    
#     username = data["username"].strip()
#     email = data["email"].strip()
#     password = data["password"]

#     if not username or not email or not password:
#         return error(400, "VALIDATION_ERROR", "username, email, and password cannot be empty")

#     # Check if the username or email already exists
#     if User.query.filter((User.username == username) | (User.email == email)).first():
#         return error(400, "VALIDATION_ERROR", "Username or email already exists")

#     # Hash the password
#     hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

#     # Create a new user
#     new_user = User(username=username, email=email, password_hash=hashed_password)
#     db.session.add(new_user)
#     db.session.commit()

#     return jsonify({"message": "User registered successfully"}), 201

# #Projects (read-only endpoints) 

# @app.route("/projects", methods=["GET"])
# def list_projects():
#     projects = Project.query.order_by(Project.id).all()
#     return jsonify([project_json(p) for p in projects])


# @app.route("/projects/<int:project_id>", methods=["GET"])
# def get_project(project_id):
#     project = db.get_or_404(Project, project_id, description=f"Project {project_id} not found")
#     return jsonify(project_json(project))


# #Revision Requests CRUD endpoints

# @app.route("/projects/<int:project_id>/revision-requests", methods=["POST"])
# def create_revision_request(project_id):
#     project = db.get_or_404(Project, project_id, description=f"Project {project_id} not found")

#     data = request.get_json(silent=True)
#     problem = validate_body(data, ["description"])
#     if problem:
#         return error(400, "VALIDATION_ERROR", problem)

    
#     used = RevisionRequest.query.filter(
#         RevisionRequest.project_id == project.id,
#         RevisionRequest.status != "Rejected",
#     ).count()

#     revision = RevisionRequest(
#         project_id=project.id,
#         description=data["description"].strip(),
#         is_extra=used >= project.agreed_revisions,
#     )
#     db.session.add(revision)
#     db.session.commit()
#     return jsonify(revision_json(revision)), 201


# @app.route("/projects/<int:project_id>/revision-requests", methods=["GET"])
# def list_revision_requests(project_id):
#     db.get_or_404(Project, project_id, description=f"Project {project_id} not found")

#     query = RevisionRequest.query.filter_by(project_id=project_id)
#     status = request.args.get("status")
#     if status is not None:
#         if status not in REVISION_STATUSES:
#             return error(400, "VALIDATION_ERROR", "status must be one of: " + ", ".join(REVISION_STATUSES))
#         query = query.filter_by(status=status)

#     revisions = query.order_by(RevisionRequest.id).all()
#     return jsonify([revision_json(r) for r in revisions])


# @app.route("/revision-requests/<int:revision_id>", methods=["GET"])
# def get_revision_request(revision_id):
#     revision = db.get_or_404(RevisionRequest, revision_id, description=f"Revision request {revision_id} not found")
#     return jsonify(revision_json(revision))


# @app.route("/revision-requests/<int:revision_id>", methods=["PATCH"])
# def update_revision_request(revision_id):
#     revision = db.get_or_404(RevisionRequest, revision_id, description=f"Revision request {revision_id} not found")

#     data = request.get_json(silent=True)
#     problem = validate_body(data, ["description", "status"])
#     if problem:
#         return error(400, "VALIDATION_ERROR", problem)

#     if "description" in data:
#         revision.description = data["description"].strip()
#     if "status" in data:
#         revision.status = data["status"]
#     db.session.commit()
#     return jsonify(revision_json(revision))


# @app.route("/revision-requests/<int:revision_id>", methods=["DELETE"])
# def delete_revision_request(revision_id):
#     revision = db.get_or_404(RevisionRequest, revision_id, description=f"Revision request {revision_id} not found")
#     db.session.delete(revision)
#     db.session.commit()
#     return "", 204


# @app.errorhandler(404)
# def not_found(err):
#     return error(404, "NOT_FOUND", err.description)

import os
from datetime import timedelta

import bcrypt
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from models import Client, Project, RevisionRequest, User, db
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

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///revisiontrack.db")
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]  # required: set it in .env
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
db.init_app(app)
jwt = JWTManager(app)

REVISION_STATUSES = ["Pending", "Completed", "Rejected"]


# Helper functions

def error(status, code, message):
    """Every error uses the same JSON shape."""
    return jsonify({"error": {"code": code, "message": message}}), status


def me():
    """The id of the logged-in user (from the token)."""
    return int(get_jwt_identity())


def parse(schema, data):
    """Validate a request body. Returns (payload, None) or (None, error_response)."""
    if not isinstance(data, dict):
        return None, error(400, "VALIDATION_ERROR", "Request body must be a JSON object")
    try:
        return schema.model_validate(data), None
    except ValidationError as exc:
        parts = []
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"])
            msg = err["msg"].removeprefix("Value error, ")
            parts.append(f"{field}: {msg}" if field else msg)
        return None, error(400, "VALIDATION_ERROR", "; ".join(parts))


def get_owned_client(client_id):
    """404 if it does not exist, 403 if it belongs to someone else."""
    client = db.session.get(Client, client_id)
    if client is None:
        return None, error(404, "NOT_FOUND", f"Client {client_id} not found")
    if client.user_id != me():
        return None, error(403, "FORBIDDEN", "You do not have access to this client")
    return client, None


def get_owned_project(project_id):
    project = db.session.get(Project, project_id)
    if project is None:
        return None, error(404, "NOT_FOUND", f"Project {project_id} not found")
    if project.user_id != me():
        return None, error(403, "FORBIDDEN", "You do not have access to this project")
    return project, None


def get_owned_revision(revision_id):
    """A revision request belongs to whoever owns its project."""
    revision = db.session.get(RevisionRequest, revision_id)
    if revision is None:
        return None, error(404, "NOT_FOUND", f"Revision request {revision_id} not found")
    project = db.session.get(Project, revision.project_id)
    if project.user_id != me():
        return None, error(403, "FORBIDDEN", "You do not have access to this revision request")
    return revision, None


def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
    }


def client_to_dict(client):
    return {
        "id": client.id,
        "name": client.name,
        "email": client.email,
        "created_at": client.created_at.isoformat(),
    }


def project_to_dict(project):
    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "client_id": project.client_id,
        "agreed_revisions": project.agreed_revisions,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
    }


def revision_to_dict(revision):
    return {
        "id": revision.id,
        "project_id": revision.project_id,
        "description": revision.description,
        "status": revision.status,
        "is_extra": revision.is_extra,
        "created_at": revision.created_at.isoformat(),
    }


# Authentication endpoints (register/login) 

@app.route("/auth/register", methods=["POST"])
def register():
    payload, problem = parse(RegisterBody, request.get_json(silent=True))
    if problem:
        return problem

    password_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(username=payload.username, email=payload.email, password_hash=password_hash)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error(409, "CONFLICT", "That username or email is already registered")
    return jsonify(user_to_dict(user)), 201


@app.route("/auth/login", methods=["POST"])
def login():
    payload, problem = parse(LoginBody, request.get_json(silent=True))
    if problem:
        return problem

    user = db.session.query(User).filter_by(email=payload.email).first()
    # Same message for "no such user" and "wrong password" so emails cannot be probed.
    if user is None or not bcrypt.checkpw(payload.password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return error(401, "UNAUTHORIZED", "Invalid email or password")

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "token_type": "Bearer"}), 200


# Clients endpoints 

@app.route("/clients", methods=["POST"])
@jwt_required()
def create_client():
    payload, problem = parse(ClientCreate, request.get_json(silent=True))
    if problem:
        return problem

    client = Client(user_id=me(), name=payload.name, email=payload.email)
    db.session.add(client)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error(409, "CONFLICT", "You already have a client with this email")
    return jsonify(client_to_dict(client)), 201


@app.route("/clients", methods=["GET"])
@jwt_required()
def get_clients():
    clients = db.session.query(Client).filter_by(user_id=me()).order_by(Client.id).all()
    return jsonify([client_to_dict(c) for c in clients]), 200


@app.route("/clients/<int:client_id>", methods=["GET"])
@jwt_required()
def get_client(client_id):
    client, problem = get_owned_client(client_id)
    if problem:
        return problem
    return jsonify(client_to_dict(client)), 200


@app.route("/clients/<int:client_id>", methods=["PATCH"])
@jwt_required()
def update_client(client_id):
    client, problem = get_owned_client(client_id)
    if problem:
        return problem
    payload, problem = parse(ClientUpdate, request.get_json(silent=True))
    if problem:
        return problem

    for field in payload.model_fields_set:
        setattr(client, field, getattr(payload, field))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error(409, "CONFLICT", "You already have a client with this email")
    return jsonify(client_to_dict(client)), 200


@app.route("/clients/<int:client_id>", methods=["DELETE"])
@jwt_required()
def delete_client(client_id):
    client, problem = get_owned_client(client_id)
    if problem:
        return problem
    # The database keeps this client's projects and sets their client_id to NULL.
    db.session.delete(client)
    db.session.commit()
    return "", 204


@app.route("/clients/<int:client_id>/projects", methods=["GET"])
@jwt_required()
def get_client_projects(client_id):
    client, problem = get_owned_client(client_id)
    if problem:
        return problem
    projects = db.session.query(Project).filter_by(client_id=client.id).order_by(Project.id).all()
    return jsonify([project_to_dict(p) for p in projects]), 200


# ---------- Projects ----------

@app.route("/projects", methods=["POST"])
@jwt_required()
def create_project():
    payload, problem = parse(ProjectCreate, request.get_json(silent=True))
    if problem:
        return problem

    if payload.client_id is not None:
        client = db.session.get(Client, payload.client_id)
        if client is None or client.user_id != me():
            return error(400, "VALIDATION_ERROR", "client_id must be one of your clients")

    project = Project(
        user_id=me(),
        client_id=payload.client_id,
        title=payload.title,
        description=payload.description,
        agreed_revisions=payload.agreed_revisions,
        status=payload.status,
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(project_to_dict(project)), 201


@app.route("/projects", methods=["GET"])
@jwt_required()
def get_projects():
    projects = db.session.query(Project).filter_by(user_id=me()).order_by(Project.id).all()
    return jsonify([project_to_dict(p) for p in projects]), 200


@app.route("/projects/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id):
    project, problem = get_owned_project(project_id)
    if problem:
        return problem
    return jsonify(project_to_dict(project)), 200


@app.route("/projects/<int:project_id>", methods=["PATCH"])
@jwt_required()
def update_project(project_id):
    project, problem = get_owned_project(project_id)
    if problem:
        return problem
    payload, problem = parse(ProjectUpdate, request.get_json(silent=True))
    if problem:
        return problem

    if payload.client_id is not None:
        client = db.session.get(Client, payload.client_id)
        if client is None or client.user_id != me():
            return error(400, "VALIDATION_ERROR", "client_id must be one of your clients")

    for field in payload.model_fields_set:
        setattr(project, field, getattr(payload, field))
    db.session.commit()
    return jsonify(project_to_dict(project)), 200


@app.route("/projects/<int:project_id>", methods=["DELETE"])
@jwt_required()
def delete_project(project_id):
    project, problem = get_owned_project(project_id)
    if problem:
        return problem
    # The database deletes this project's revision requests with it.
    db.session.delete(project)
    db.session.commit()
    return "", 204


# ---------- Revision requests ----------

@app.route("/projects/<int:project_id>/revision-requests", methods=["POST"])
@jwt_required()
def create_revision_request(project_id):
    project, problem = get_owned_project(project_id)
    if problem:
        return problem
    payload, problem = parse(RevisionRequestCreate, request.get_json(silent=True))
    if problem:
        return problem

    # Core rule: if the project has already used up its agreed revisions
    # (not counting rejected ones), this new request is flagged as extra.
    used = db.session.query(RevisionRequest).filter(
        RevisionRequest.project_id == project.id,
        RevisionRequest.status != "Rejected",
    ).count()

    revision = RevisionRequest(
        project_id=project.id,
        description=payload.description,
        is_extra=used >= project.agreed_revisions,
    )
    db.session.add(revision)
    db.session.commit()
    return jsonify(revision_to_dict(revision)), 201


@app.route("/projects/<int:project_id>/revision-requests", methods=["GET"])
@jwt_required()
def get_revision_requests(project_id):
    project, problem = get_owned_project(project_id)
    if problem:
        return problem

    query = db.session.query(RevisionRequest).filter_by(project_id=project.id)
    status = request.args.get("status")
    if status is not None:
        if status not in REVISION_STATUSES:
            return error(400, "VALIDATION_ERROR", "status must be one of: " + ", ".join(REVISION_STATUSES))
        query = query.filter_by(status=status)

    revisions = query.order_by(RevisionRequest.id).all()
    return jsonify([revision_to_dict(r) for r in revisions]), 200


@app.route("/revision-requests/<int:revision_id>", methods=["GET"])
@jwt_required()
def get_revision_request(revision_id):
    revision, problem = get_owned_revision(revision_id)
    if problem:
        return problem
    return jsonify(revision_to_dict(revision)), 200


@app.route("/revision-requests/<int:revision_id>", methods=["PATCH"])
@jwt_required()
def update_revision_request(revision_id):
    revision, problem = get_owned_revision(revision_id)
    if problem:
        return problem
    payload, problem = parse(RevisionRequestUpdate, request.get_json(silent=True))
    if problem:
        return problem

    for field in payload.model_fields_set:
        setattr(revision, field, getattr(payload, field))
    db.session.commit()
    return jsonify(revision_to_dict(revision)), 200


@app.route("/revision-requests/<int:revision_id>", methods=["DELETE"])
@jwt_required()
def delete_revision_request(revision_id):
    revision, problem = get_owned_revision(revision_id)
    if problem:
        return problem
    db.session.delete(revision)
    db.session.commit()
    return "", 204


# ---------- Errors: clients never see a stack trace ----------

@jwt.unauthorized_loader
def missing_token(reason):
    return error(401, "UNAUTHORIZED", "Log in and send the header: Authorization: Bearer <token>")


@jwt.invalid_token_loader
def invalid_token(reason):
    return error(401, "UNAUTHORIZED", "Invalid token")


@jwt.expired_token_loader
def expired_token(jwt_header, jwt_payload):
    return error(401, "TOKEN_EXPIRED", "Token has expired, please log in again")


@app.errorhandler(HTTPException)
def handle_http_error(err):
    if err.code == 404:
        return error(404, "NOT_FOUND", "Resource not found")
    if err.code == 405:
        return error(405, "METHOD_NOT_ALLOWED", "Method not allowed for this URL")
    return error(err.code, err.name.upper().replace(" ", "_"), err.description)


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    db.session.rollback()
    app.logger.exception("Unhandled error")  # the details stay in the server log only
    return error(500, "INTERNAL_ERROR", "Something went wrong on the server")
