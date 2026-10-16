# Work plan: RevisionTrack

## Week 1: Design and build
- Idea one-pager, work plan, public repo with README and `.env.example`
- 1.1 ERD and API spec (this /docs folder)
- 1.2 Flask project, SQLite schema, seed data, full CRUD for revision requests, read-only project endpoints, sample requests
- Tag `week-1`, submit, prepare 5-minute presentation

## Week 2: Auth and robustness
- Respond to Week 1 feedback; start the issue log (aim for 5+ entries)
- 2.1 Sign-up/login with JWT, bcrypt/argon2 password hashing, protected routes, ownership checks, 401/403
- 2.2 Write endpoints for clients and projects, relationship endpoints, schema validation, one error format, global error handler
- Edge cases: duplicates, deleting a client (projects are kept; their client link becomes empty), invalid IDs
- Tag `week-2`

## Week 3: Quality and delivery
- 3.1 Unit and integration tests (400/401/403/404 cases), one-command test run, coverage note
- 3.2 API docs, security basics (env secrets, CORS, rate limit on auth), pagination and indexes, deploy or run guide
- Final package: README/case study, walkthrough video, technical reflection, declaration
- Tag `week-3`

## Top 3 risks
1. SQLite foreign keys off by default (enable and test).
2. `is_extra` counting rule errors (document and test boundaries).
3. Scope creep within three weeks (defer anything not in the current week's tasks).
