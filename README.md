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

## Issue Log

Issue 1: `ondelete` passed to `db.Column` crashed the app
- **Problem:** I wrote `db.Column(..., ondelete='SET NULL')` on `Project.client_id`. `Column` does not accept `ondelete`, so the app crashed when the models loaded.
- **Options considered:** put the rule on the column (not supported); define a separate table-level foreign key constraint; pass `ondelete` to `db.ForeignKey`.
- **Fix:** moved the rule into `db.ForeignKey('clients.id', ondelete='SET NULL')`. The same applies to the `CASCADE` rule on `revision_requests.project_id`.
- **Verified:** the models load, and deleting a client leaves its projects with `client_id` set to `NULL`.

Issue 2: SQLite ignored foreign keys, so delete rules did nothing
- **Problem:** SQLite does not enforce foreign keys unless they are switched on for every connection. Without that, `SET NULL` and `CASCADE` silently did nothing, and a revision request could point at a project that did not exist.
- **Options considered:** handle every delete in application code; move to PostgreSQL straight away; switch foreign keys on for each SQLite connection.
- **Fix:** added a connection listener in `models.py` that runs `PRAGMA foreign_keys=ON` for every SQLite connection. This keeps SQLite for easy local running, and the database enforces the rules.
- **Verified:** a revision request with a missing `project_id` is rejected, deleting a client keeps its projects, and deleting a project removes its revision requests.

Issue 3: Unknown or non-integer URLs returned Flask's default HTML 404
- **Problem:** a request such as `/projects/abc` returned Flask's HTML error page, which broke the rule that every error uses the same JSON format.
- **Options considered:** leave the default page; return JSON errors only from inside each route (this misses URLs that match no route); add one global error handler.
- **Fix:** added a global handler, later extended to every HTTP error and to unexpected errors, so every response uses `{ "error": { "code", "message" } }`.
- **Verified:** `/projects/abc`, unknown URLs, and wrong methods (405) all return the standard JSON error.

Issue 4: Client emails were unique across all users
- **Problem:** `clients.email` was `unique=True`, which was written when the app had a single freelancer. After adding users, a second freelancer could not save a client whose email another freelancer already had. The rejection also revealed that someone else had that client.
- **Options considered:** keep the global rule (blocks legitimate use and leaks information); remove uniqueness (the same user could add duplicates); make it unique per user.
- **Fix:** replaced `unique=True` with `UniqueConstraint('user_id', 'email', name='uq_clients_user_id_email')`. Adding the same client email twice as one user returns 409. Emails are trimmed and lowercased on input.
- **Verified:** two users can save the same client email, and the same user saving it twice is rejected (both covered by automated checks).

Issue 5: Very large IDs returned a 500 error instead of a 404
- **Problem:** a request such as `/clients/99999999999999999999` made SQLite raise an `OverflowError`, and the API answered with a 500 error. The same happened for a huge `client_id` in a request body.
- **Options considered:** limit the ID range in the URL converter (tried this, but Flask's router then returned a wrong 405 for some methods, so I dropped it); check the range inside every route (repeated code); add one `OverflowError` handler for URLs and a maximum value for body IDs.
- **Fix:** an `OverflowError` handler returns the normal 404 (no record can have an ID that large), and `IntId` in `schemas.py` caps body IDs at 2,147,483,647, so those return 400.
- **Verified:** huge, zero, negative and decimal IDs all return 404, and a huge `client_id` in a body returns 400. All 151 automated checks pass.