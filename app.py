import math
import os
from datetime import timedelta

import bcrypt
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

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

jwt_secret = os.environ["JWT_SECRET_KEY"]
if len(jwt_secret) < 32 or jwt_secret.startswith("CHANGE_ME"):
    raise RuntimeError(
        "JWT_SECRET_KEY must be a random value of at least 32 characters. "
        'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
    )

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///revisiontrack.db")
app.config["JWT_SECRET_KEY"] = jwt_secret
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["RATELIMIT_HEADERS_ENABLED"] = True
app.config["BCRYPT_ROUNDS"] = int(os.getenv("BCRYPT_ROUNDS", "12"))  # tests lower this for speed
db.init_app(app)
jwt = JWTManager(app)

# Behind the host's proxy (Render) every request seems to come from the proxy, which would make
# one shared rate limit for everyone. BEHIND_PROXY=1 makes Flask read the real client address instead.
if os.getenv("BEHIND_PROXY") == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
CORS(app, origins=cors_origins, allow_headers=["Content-Type", "Authorization"])

# Rate limiting applies to the login and register routes only (limits are per client address).
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")
LOGIN_LIMIT = "10 per minute"
REGISTER_LIMIT = "10 per hour"

REVISION_STATUSES = ["Pending", "Completed", "Rejected"]
MAX_PER_PAGE = 100


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


def paginate(query, to_dict):
    """Apply ?page= and ?per_page= to an ordered query.
    Returns (body, None) or (None, error_response)."""
    page = request.args.get("page", "1")
    per_page = request.args.get("per_page", "20")
    if not (page.isdecimal() and per_page.isdecimal() and len(page) <= 7 and len(per_page) <= 3):
        return None, error(400, "VALIDATION_ERROR", "page and per_page must be positive whole numbers")
    page, per_page = int(page), int(per_page)
    if page < 1 or not 1 <= per_page <= MAX_PER_PAGE:
        return None, error(400, "VALIDATION_ERROR", f"page must be 1 or more and per_page must be 1 to {MAX_PER_PAGE}")

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    body = {
        "items": [to_dict(item) for item in items],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": math.ceil(total / per_page),
    }
    return body, None


def is_extra(project):
    """Core rule: True if the project has already used up its agreed revisions.
    Rejected requests do not count, because they were never carried out."""
    used = db.session.query(RevisionRequest).filter(
        RevisionRequest.project_id == project.id,
        RevisionRequest.status != "Rejected",
    ).count()
    return used >= project.agreed_revisions


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
@limiter.limit(REGISTER_LIMIT)
def register():
    payload, problem = parse(RegisterBody, request.get_json(silent=True))
    if problem:
        return problem

    password_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt(rounds=app.config["BCRYPT_ROUNDS"])).decode("utf-8")
    user = User(username=payload.username, email=payload.email, password_hash=password_hash)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error(409, "CONFLICT", "That username or email is already registered")
    return jsonify(user_to_dict(user)), 201


@app.route("/auth/login", methods=["POST"])
@limiter.limit(LOGIN_LIMIT)
def login():
    payload, problem = parse(LoginBody, request.get_json(silent=True))
    if problem:
        return problem

    user = db.session.query(User).filter_by(email=payload.email).first()

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
    query = db.session.query(Client).filter_by(user_id=me()).order_by(Client.id)
    body, problem = paginate(query, client_to_dict)
    if problem:
        return problem
    return jsonify(body), 200


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
    query = db.session.query(Project).filter_by(client_id=client.id).order_by(Project.id)
    body, problem = paginate(query, project_to_dict)
    if problem:
        return problem
    return jsonify(body), 200


# Projects endpoints

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
    query = db.session.query(Project).filter_by(user_id=me()).order_by(Project.id)
    body, problem = paginate(query, project_to_dict)
    if problem:
        return problem
    return jsonify(body), 200


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


# Revision requests

@app.route("/projects/<int:project_id>/revision-requests", methods=["POST"])
@jwt_required()
def create_revision_request(project_id):
    project, problem = get_owned_project(project_id)
    if problem:
        return problem
    payload, problem = parse(RevisionRequestCreate, request.get_json(silent=True))
    if problem:
        return problem

    revision = RevisionRequest(
        project_id=project.id,
        description=payload.description,
        is_extra=is_extra(project),
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

    body, problem = paginate(query.order_by(RevisionRequest.id), revision_to_dict)
    if problem:
        return problem
    return jsonify(body), 200


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


# ---------- API documentation (Swagger UI reads docs/openapi.yaml) ----------

SWAGGER_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>RevisionTrack API docs</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({ url: "/openapi.yaml", dom_id: "#swagger-ui" });</script>
</body>
</html>"""


@app.route("/docs", methods=["GET"])
def api_docs():
    return SWAGGER_PAGE


@app.route("/openapi.yaml", methods=["GET"])
def openapi_spec():
    return send_from_directory( os.path.join(app.root_path, "docs"), "openapi.yaml", mimetype="application/yaml")


# ---------- Errors: clients never see a stack trace ----------

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"  # browsers must trust the declared type
    response.headers["Cache-Control"] = "no-store"  # tokens and personal data are not cached
    return response


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
    if err.code == 429:
        return error(429, "TOO_MANY_REQUESTS", "Too many attempts, please wait a moment and try again")
    return error(err.code, err.name.upper().replace(" ", "_"), err.description)


@app.errorhandler(OverflowError)
def handle_id_too_large(err):
    # An id too big for the database can only come from the URL (request bodies are limited
    # by their schemas), and no record can have it, so it is simply not found.
    return error(404, "NOT_FOUND", "Resource not found")


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    db.session.rollback()
    app.logger.exception("Unhandled error")  # the details stay in the server log only
    return error(500, "INTERNAL_ERROR", "Something went wrong on the server")