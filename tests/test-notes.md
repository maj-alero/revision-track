# Test notes

## How to run
```bash
pip install -r requirements-dev.txt
pytest                                        # the whole suite (about 10 seconds)
pytest --cov --cov-report=term-missing        # with a coverage report
```
The tests use an in-memory SQLite database that is recreated for every test, a throwaway secret key and fast password hashing. They never touch the real database or `.env`. The environment is set before the app is imported, in `tests/conftest.py`.

## Result
**188 tests, all passing. Coverage: `app.py` 99%, `models.py` 100%, `schemas.py` 100%, overall 99%** (seed script and tests excluded).

## What is tested

| File | Tests | Covers |
|---|---|---|
| `test_schemas.py` | 25 | Unit tests of every validation rule: email cleaning, password and username limits, unknown fields, strict numbers, ID range, status case, control characters, PATCH rules for nulls |
| `test_business_rule.py` | 12 | The `is_extra` rule: boundary cases (limit 0, 1 and 3, rejected and completed requests), the flag flipping over several requests, and flags not being recomputed later |
| `test_auth.py` | 34 | Registering, duplicates (409), invalid input (400), bcrypt storage, login, identical 401 for wrong password and unknown email, 401 on all 16 protected routes, bad and expired tokens |
| `test_clients.py` | 22 | Create, read, update, delete, per-user duplicate email (409), 400 cases, 404, 403 and unchanged data, the delete rule that keeps projects |
| `test_projects.py` | 27 | Same for projects, plus linking only to your own client, detaching a client, and cascade delete of requests |
| `test_revision_requests.py` | 21 | Same for revision requests, plus the status filter and the 500-character limit |
| `test_pagination.py` | 21 | Page shape, page size, ordering, empty pages, invalid values (400) on every list endpoint |
| `test_security.py` | 16 | Rate limits (429), CORS closed by default, security headers, no stack trace on a 500, one error shape, huge or odd IDs, control characters, SQL injection text, HTML text |
| `test_startup.py` | 7 | Refusing to start with a missing, short or placeholder secret, and the proxy setting for rate limits (each run in a separate process) |
| `test_docs.py` | 3 | `openapi.yaml` is valid OpenAPI, every real route is documented and nothing extra is, and `/docs` and `/openapi.yaml` are served |

Every endpoint is tested for the failure cases that apply to it: 400, 401, 403 and 404 (and 409 and 429 where relevant). Tests that expect a failure also check that nothing was changed.

## What is not tested, and why
- **Lines the coverage tool cannot see.** Two lines in `app.py` (the weak-secret check and the proxy setting) are exercised by `test_startup.py`, but in separate processes, which the coverage tool does not measure. One line, the fallback for rare HTTP errors, is not reached because no route can trigger it.
- **Concurrent requests.** Two simultaneous requests can both read the same count in the `is_extra` check. I know about it (see the limitations in the README) but have not written a test for it, because SQLite's single writer makes the race hard to reproduce reliably.
- **A real PostgreSQL database.** All tests run on SQLite, so differences in PostgreSQL (for example how enums and constraints behave) are untested.
- **The live deployment.** Tests do not call the hosted API. I checked it by hand with the sample requests.
- **The Swagger page in a browser.** Tests confirm the page and the spec are served and match the routes, but not how the page renders. It loads its scripts from a public CDN.
- **CORS with an allowed origin.** Only the default (closed) setting is tested, because the setting is read once when the app starts.
- **Load and performance.** There are no load tests, so no speed or capacity claims are made.
- **Token lifetime in real time.** An expired token is tested by creating one that is already expired, not by waiting an hour.
