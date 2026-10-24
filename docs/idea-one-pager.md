# RevisionTrack
Track: Backend Development   Stack: Python, Flask, SQLAlchemy, SQLite 

**Target user:** An independent freelancer (designer, developer, writer) who agrees a fixed number of revisions with each client.

**Problem:** Clients keep asking for "one small change" and the freelancer loses track of how many revisions were agreed, how many were used, and which ones should have been billed as extra. RevisionTrack records every revision request against a project and flags the ones that go over the agreed limit.

**Entities:** users, clients, projects, revision_requests

**Core flow:**  Register and log in to get a token -> `GET /projects` (find the project) -> `POST /projects/1/revision-requests` (log a request; server flags it extra if over the limit) -> `GET /projects/1/revision-requests` (see all requests and which are extra)

## In scope
- Sign-up and login with JWT and bcrypt-hashed passwords
- Ownership checks: users only see and change their own data (401 when not logged in, 403 when a record belongs to someone else)
- Full CRUD for clients, projects and revision requests, plus endpoints for related data
- Automatic is_extra flag when a project's agreed revisions are used up
- Input validation on every request body, one error format, and a global error handler
- Seeded dummy users, clients, projects and requests

## Out of scope
- Payments or invoicing, email or notifications, file uploads, client-facing portals
- Admin roles, password reset, token refresh and logout
- Pagination, rate limiting and the automated test suite (Week 3)

## Top 3 risks
1. **Access control mistakes.** One missed ownership check would let a user see another user's data. Mitigation: one ownership helper per entity used by every route, a user filter on every list, and automated tests that try each route as the wrong user.
2. **Data integrity.** SQLite ignores foreign keys by default. Mitigation: switch foreign keys on for every connection and test the delete rules.
3. **The is_extra rule.** It is easy to get the counting rule wrong (rejected requests do not count). Mitigation: write the rule in the spec and test the boundary cases.