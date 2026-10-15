# RevisionTrack

A small REST API for freelancers to log client revision requests against projects and flag the ones that go over the agreed limit.

- **Stack:** Python, Flask, Flask-SQLAlchemy, SQLite
- **Docs:** see the `docs/` folder (idea one-pager, work plan, ERD and API spec)
- **All data is dummy data.** Never put real personal data or passwords in this project.

## How to run

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
python seed.py                    # resets the database and loads dummy data
flask run                         # API at http://localhost:5000
```

Running `python seed.py` again wipes the database and reloads the dummy data.

## Endpoints (Week 1)

| Method | Path | Purpose |
|---|---|---|
| GET | `/projects` | List projects (seeded) |
| GET | `/projects/{id}` | Get one project |
| POST | `/projects/{project_id}/revision-requests` | Log a revision request (server sets `is_extra`) |
| GET | `/projects/{project_id}/revision-requests` | List a project's requests, optional `?status=` |
| GET | `/revision-requests/{id}` | Get one request |
| PATCH | `/revision-requests/{id}` | Update `description` and/or `status` |
| DELETE | `/revision-requests/{id}` | Delete a request |

Try them with `requests.http` (VS Code "REST Client" extension) or curl:

```bash
curl http://localhost:5000/projects
curl -X POST http://localhost:5000/projects/1/revision-requests \
  -H "Content-Type: application/json" \
  -d '{"description": "Make the logo bigger"}'
```

Errors always look like `{ "error": { "code": "NOT_FOUND", "message": "..." } }`.
Full details, validation rules and design decisions are in `docs/api-spec.md`.

## Project layout

- `app.py`: Flask app, routes and validation
- `models.py`: database tables
- `seed.py`: resets the database and loads dummy data
- `requests.http`: sample requests