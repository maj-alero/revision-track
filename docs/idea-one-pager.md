# RevisionTrack
Track: Backend Development   Stack: Python, Flask, SQLAlchemy, SQLite 

**Target user:** An independent freelancer (designer, developer, writer) who agrees a fixed number of revisions with each client.

**Problem:** Clients keep asking for "one small change" and the freelancer loses track of how many revisions were agreed, how many were used, and which ones should have been billed as extra. RevisionTrack records every revision request against a project and flags the ones that go over the agreed limit.

**Entities:** clients, projects, revision_requests

**Core flow:** `GET /projects` (find the project) -> `POST /projects/1/revision-requests` (log a request; server flags it extra if over the limit) -> `GET /projects/1/revision-requests` (see all requests and which are extra)

**In scope**
- Full CRUD for revision requests (main entity)
- Automatic `is_extra` flag when a project's agreed revisions are exceeded
- Read-only endpoints for projects
- Seeded dummy clients, projects and requests
- Consistent validation and status codes

**Out of scope**
- Payments or invoicing
- Authentication (Week 2)
- Client and project write endpoints (clients/projects are seeded in Week 1)
- File uploads or client-facing portals
- Email or notification features

**Top 3 risks**
1. SQLite does not enforce foreign keys by default, so integrity bugs could hide. Mitigation: enable `PRAGMA foreign_keys=ON` and test it.
2. The `is_extra` counting rule is easy to get wrong (what counts toward the limit). Mitigation: write the rule down in the spec and test boundary cases.
3. Time: three weeks part-time. Mitigation: keep Week 1 to one main entity and defer extras.
