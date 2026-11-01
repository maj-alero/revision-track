# Security and performance notes

## Security

| Area | What is done | Where |
|---|---|---|
| Secrets | The signing key and the database address come only from environment variables (`.env` locally, the host's settings when deployed). `.env` is git-ignored and only `.env.example`, with no real values, is committed. The app refuses to start if `JWT_SECRET_KEY` is missing, shorter than 32 characters, or still the `CHANGE_ME` placeholder. | `app.py`, `.env.example`, `.gitignore` |
| Passwords | Hashed with bcrypt (12 rounds) before saving. Never stored, logged or returned in plain text. Passwords must be 8 to 72 characters (bcrypt ignores anything longer). | `app.py`, `schemas.py` |
| Login | Signed JWT access token, valid for 1 hour. An unknown email and a wrong password give the same 401 message, so emails cannot be probed. | `app.py` |
| Access control | Every route except register and login needs a valid token (401). Each user only sees and changes their own records (403 for someone else's, 404 for a missing one). Lists are filtered by the logged-in user. A project can only be linked to the user's own client. | `app.py` |
| Input validation | Every request body is checked with Pydantic: types, lengths, allowed values, no unknown fields (so nobody can send `user_id` or `is_extra`), strict numbers, and IDs within the database range. | `schemas.py` |
| Input sanitisation | Text is trimmed, emails are lowercased, usernames are limited to letters, digits and `_ . -`, and control characters (null bytes, escape codes) are rejected. HTML is not rewritten on the way in: the API returns plain JSON text, and any client that shows it in a web page must escape it. | `schemas.py` |
| SQL injection | All queries go through SQLAlchemy with bound parameters, so text such as `'; DROP TABLE users; --` is stored as plain data (tested). | `app.py` |
| CORS | Closed by default: no website can call the API from a browser. Allowed websites are listed deliberately in `CORS_ORIGINS`. Tools such as curl and Postman are not affected. | `app.py` |
| Rate limiting | Login: 10 per minute. Register: 10 per hour. Counted per client address, answered with 429 and a `Retry-After` header. Behind the host's proxy, `BEHIND_PROXY=1` makes it read the real client address. | `app.py` |
| Response headers | `X-Content-Type-Options: nosniff` and `Cache-Control: no-store` on every response, so tokens and personal data are not cached. | `app.py` |
| Errors | One JSON format everywhere. Unexpected failures return a generic 500 and the details stay in the server log, so no stack trace, file path or query reaches the client (tested). | `app.py` |
| Transport | HTTPS is provided by the host (Render). The app itself does not redirect HTTP to HTTPS. | host |

### Known gaps (and what I would do next)
- **Tokens cannot be revoked** before they expire, and there is no logout or refresh. Next: short access tokens with refresh tokens and a revocation list.
- **No account lockout or email verification.** The rate limit slows guessing, but a determined attacker could use many addresses.
- **The rate limiter is in memory,** so counters are per process and reset on restart. Next: shared storage such as Redis.
- **A 403 confirms that a record exists.** This follows the work guide. Returning 404 for other users' records would leak less.
- **No security headers beyond the two above** (such as a content security policy), because the API returns JSON, not pages. The Swagger page loads its scripts from a public CDN.
- **No automated dependency scanning.** Next: run `pip-audit` and pin updates regularly.

## Performance

| Area | What is done |
|---|---|
| Pagination | Every list endpoint (`/clients`, `/projects`, `/clients/{id}/projects`, `/projects/{id}/revision-requests`) is paginated with `?page=` and `?per_page=` (default 20, maximum 100). Responses include `total` and `pages`. Invalid values return 400, and a page past the end returns an empty list. |
| Stable ordering | Lists are ordered by `id`, so pages never overlap or skip items. |
| Indexes | Chosen from the filters the queries actually use (table below). Primary keys and unique columns are indexed automatically. |
| Query shape | One query per request for the data, plus one `COUNT` for the page total. No loops that query the database (no N+1 queries), because responses are built from the rows already fetched. |
| Count rule | The `is_extra` check is a single `COUNT` that uses the `(project_id, status)` index. |

| Index | Used by |
|---|---|
| `clients (user_id, email)` unique | Listing a user's clients, and the per-user duplicate check |
| `projects.user_id` | Listing a user's projects |
| `projects.client_id` | Listing a client's projects, and the delete rule |
| `revision_requests (project_id, status)` | Listing a project's requests, the `?status=` filter, and the `is_extra` count |
| `users.email`, `users.username` unique | Login, and duplicate checks at registration |

### Limits and what I would do next
- **SQLite allows one writer at a time.** For this scale I believe it is fine, and the app runs with one worker. At real scale, I would switch to PostgreSQL (only `DATABASE_URL` changes).
- **Offset pagination gets slower on very deep pages** and can shift if rows are added while paging. Next: cursor-based pagination.
- **Free-host cold start:** the first request after idle can take up to a minute.
- **No load testing has been done,** so there are no throughput numbers. I would not claim any.
