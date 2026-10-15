# RevisionTrack: Data model and API spec (Week 1)

## 1. Entities

Table and column definitions match `models.py`.

**clients** (table `clients`)
| Field | Type | Notes |
|---|---|---|
| id | integer | PK |
| name | string (max 150) | required |
| email | string (max 150) | required, **unique** |
| created_at | datetime | set by server |

**projects** (table `projects`)
| Field | Type | Notes |
|---|---|---|
| id | integer | PK |
| title | string (max 150) | required |
| description | text | optional |
| client_id | integer | FK to clients.id, **nullable**, `ON DELETE SET NULL` |
| agreed_revisions | integer | required, default 0, must be >= 0 (database check constraint) |
| status | string | `Active` (default), `Completed`, `On-hold` |
| created_at | datetime | set by server |

**revision_requests** (table `revision_requests`, main entity; model class `RevisionRequest`)
| Field | Type | Notes |
|---|---|---|
| id | integer | PK |
| project_id | integer | FK to projects.id, required, `ON DELETE CASCADE`, not editable after creation |
| description | text | required, non-empty (API limits it to 500 characters) |
| status | string | `Pending` (default), `Completed`, `Rejected` |
| is_extra | boolean | default false |
| created_at | datetime | set by server |

## 2. ERD

![RevisionTrack ERD](erd.svg)

Relationships
- One client has many projects. A project has zero or one client (the link becomes empty if the client is deleted).
- One project has many revision requests. A revision request belongs to exactly one project.
- A revision request reaches its client only through its project (no `client_id` on revision requests).

Delete rules (enforced by the database, with SQLite foreign keys switched on)
- Deleting a client keeps its projects; their `client_id` becomes NULL.
- Deleting a project deletes its revision requests.

## 3. API spec

Base path: `/`. All bodies are JSON. Errors use one format:

```json
{ "error": { "code": "NOT_FOUND", "message": "Project 99 not found" } }
```

### Revision requests (full CRUD)

| Method | Path | Purpose | Request body | Success response | Status codes |
|---|---|---|---|---|---|
| POST | `/projects/{project_id}/revision-requests` | Log a new request under a project; server sets `is_extra` | `{ "description": "string" }` | The created request | 201, 400 (invalid body), 404 (project not found) |
| GET | `/projects/{project_id}/revision-requests` | List a project's requests; optional `?status=Pending\|Completed\|Rejected` | none | Array of requests | 200, 400 (invalid status filter), 404 (project not found) |
| GET | `/revision-requests/{id}` | Get one request | none | One request | 200, 404 |
| PATCH | `/revision-requests/{id}` | Update `description` and/or `status` | `{ "description"?: "string", "status"?: "Pending\|Completed\|Rejected" }` | The updated request | 200, 400 (invalid or empty body, unknown field), 404 |
| DELETE | `/revision-requests/{id}` | Delete a request | none | empty body | 204, 404 |

Example revision request response:

```json
{
  "id": 4,
  "project_id": 1,
  "description": "Make the logo bigger",
  "status": "Pending",
  "is_extra": false,
  "created_at": "2026-10-13T10:15:00Z"
}
```

### Projects (read-only in Week 1, seeded)

| Method | Path | Purpose | Success response | Status codes |
|---|---|---|---|---|
| GET | `/projects` | List projects (so testers can find valid IDs) | Array of projects | 200 |
| GET | `/projects/{id}` | Get one project | One project | 200, 404 |

Example project response:

```json
{
  "id": 1,
  "title": "Bakery logo redesign",
  "description": "New logo and colour palette",
  "client_id": 1,
  "agreed_revisions": 3,
  "status": "Active",
  "created_at": "2026-10-01T09:00:00Z"
}
```

`client_id` is `null` for a project whose client was deleted.

IDs that are not integers (e.g. `/revision-requests/abc`) return 404 in the standard error format.

## 4. Business rule: `is_extra`

When a revision request is created, the server counts the project's existing requests whose status is not `Rejected`. If that count is already **greater than or equal to** `agreed_revisions`, the new request is saved with `is_extra = true`; otherwise `false`.

Examples with `agreed_revisions = 3`:
- 0, 1 or 2 existing requests -> new request is not extra
- 3 or more existing requests -> new request is extra

`is_extra` cannot be set or changed through the API (documented limitation).

## 5. Validation rules

- `description` (revision request): required on create, string, not empty or whitespace only, max 500 characters
- `status`: must be exactly one of the listed values (case-sensitive); anything else returns 400
- PATCH accepts only `description` and `status`; any other field (including `project_id` and `is_extra`) returns 400, and an empty body returns 400
- The database does not enforce enum values in SQLite, so API validation is the guard

## 6. Seed data

Dummy data only: a few clients (each with a different email, since `email` is unique), projects with different `agreed_revisions` values and statuses, and revision requests including one project that is already over its limit and one `Rejected` request. Run the seed on a fresh database.

## 7. Design decisions

- **Main entity is revision_requests.** It holds the app's core value (the extra-revision flag), so full CRUD there demonstrates the real purpose. Clients and projects are seeded.
- **Rejected requests do not count toward the limit.** A rejected request was never carried out, so it should not use up the client's agreed revisions.
- **Server-side `is_extra`.** Computing it on the server prevents clients from faking or hiding extra work.
- **A relational (SQL) database instead of NoSQL.** The data is naturally relational: a client has many projects, and a project has many revision requests, with a fixed set of fields on each. A relational database lets the database itself enforce the rules the app depends on: foreign keys stop a request pointing at a missing project, `ON DELETE SET NULL` and `CASCADE` define what happens on deletes, `UNIQUE` prevents duplicate client emails, and a check constraint blocks a negative revision limit. The core feature, deciding `is_extra`, is a simple count of a project's non-rejected requests, which SQL does directly. A document database such as MongoDB suits data whose shape varies between records or that must scale across many servers, and neither applies here. In NoSQL, the links between clients, projects and requests, and the delete rules, would have to be enforced in application code. The trade-off is that changing the schema needs migrations. 
- **SQLite for Week 1.** Anyone can clone and run the project with no database install. The database location comes from `DATABASE_URL`, so switching to PostgreSQL for deployment is a configuration change. Foreign keys are switched on explicitly for every connection because SQLite ignores them by default.
- **Projects outlive clients.** `projects.client_id` is nullable with `ON DELETE SET NULL`, so work history is preserved when a client is deleted. Client deletion endpoints arrive in Week 2.
- **A project's revision requests are deleted with it.** A request has no meaning without its project, so `project_id` is required and uses `ON DELETE CASCADE`.
- **Database-level safety nets.** `agreed_revisions >= 0` is a check constraint, and `clients.email` is unique, so bad data is rejected even if it bypasses the API.
- **No ORM relationships in Week 1.** Foreign keys alone link the tables; queries filter by `project_id` directly.