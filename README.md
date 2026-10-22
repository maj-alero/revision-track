# RevisionTrack

A small REST API for freelancers to log client revision requests against projects and flag the ones that go over the agreed limit. Each freelancer has an account and only sees their own clients, projects and requests.

- **Stack:** Python, Flask, Flask-SQLAlchemy, SQLite, Pydantic, JWT (Flask-JWT-Extended), bcrypt
- **Docs:** see the `docs/` folder (idea one-pager, work plan, ERD, API spec, issue log)
- **All data is dummy data.** Never put real personal data or passwords in this project.

## Live API
`https://revision-track.onrender.com`

Hosted on a free tier: the service sleeps after about 15 minutes of inactivity, so the first request may take up to a minute. The database is reset to the dummy data whenever the service restarts.

## How to run

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
python seed.py                    # resets the database and loads dummy data
flask run                         # API at http://localhost:5000
```

In `.env`, replace `JWT_SECRET_KEY` with your own random value (the app will not start without one):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Running `python seed.py` again wipes the database and reloads the dummy data. Set `FLASK_DEBUG=0` in any deployed environment.

## Demo logins (dummy passwords, for testing only)

| Email | Password |
|---|---|
| demo@example.com | Password123! |
| second@example.com | Password123! |

## Using the API

1. Log in to get a token:
   ```bash
   curl -X POST http://localhost:5000/auth/login -H "Content-Type: application/json" \
     -d '{"email": "demo@example.com", "password": "Password123!"}'
   ```
2. Send the token with every other request: `Authorization: Bearer <access_token>` (tokens last 1 hour).

| Status | Meaning |
|---|---|
| 401 | Not logged in, or the token is missing, invalid or expired |
| 403 | The record exists but belongs to another user |
| 404 | The record does not exist (or the URL is wrong) |
| 400 | Invalid input |
| 409 | Duplicate (username, user email, or the same client email twice for one user) |


## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Log in and get a token |
| GET, POST | `/clients` | List or create your clients |
| GET, PATCH, DELETE | `/clients/{id}` | Get, update or delete a client (its projects are kept) |
| GET | `/clients/{id}/projects` | A client's projects |
| GET, POST | `/projects` | List or create your projects |
| GET, PATCH, DELETE | `/projects/{id}` | Get, update or delete a project (its revision requests are deleted too) |
| POST | `/projects/{project_id}/revision-requests` | Log a revision request (the server sets `is_extra`) |
| GET | `/projects/{project_id}/revision-requests` | List a project's requests, optional `?status=` |
| GET, PATCH, DELETE | `/revision-requests/{id}` | Get, update or delete a request |

Every endpoint except `/auth/register` and `/auth/login` needs a token. Try them with `requests.http` (VS Code "REST Client" extension). Full details, validation rules and design decisions are in `docs/api-spec.md`.

## Project layout

- `app.py`: Flask app, routes, authentication and error handling
- `models.py`: database tables
- `schemas.py`: request validation
- `seed.py`: resets the database and loads dummy data
- `requests.http`: sample requests
- `docs/issue-log.md`: bugs found and how they were fixed

## Issue Logs

- ondelete was passed to db.Column, which crashed; it belongs in ForeignKey.
- SQLite ignores foreign keys by default, so delete rules did nothing until the pragma listener was added.
- A non-integer ID like /projects/abc returned Flask’s default HTML 404, so a handler was added for the standard error format.