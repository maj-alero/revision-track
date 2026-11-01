# Technical reflection and declaration



## Technical reflection

### What changed over three weeks
- **Week 1: a small, correct core.** I chose a niche problem (freelancers losing track of revision requests) and designed three related tables. I made revision requests the main entity and built full CRUD for them, with the server deciding whether a request is "extra". I fixed early mistakes in my data model: a foreign key rule in the wrong place, SQLite ignoring foreign keys, and a client link that contradicted my own "keep projects" decision.
- **Week 2: users and safety.** I added accounts, bcrypt-hashed passwords and JWT login, and made every record belong to a user. I added ownership checks (401 and 403), CRUD for clients and projects, relationship endpoints, schema validation, one error format and a global error handler. Writing the models again for several users exposed a real bug: client emails were unique across all users.
- **Week 3: proving it and shipping it.** I added a test suite (188 tests), pagination, indexes, rate limits on login and register, deliberate CORS settings, input sanitisation, and security headers. I wrote an OpenAPI file that a test checks against the real routes, deployed the API, and wrote the setup and security notes.

### What remains risky
- **Data on a free host is wiped on restart,** because SQLite lives on a disk that is not kept. Fine for dummy data, not for real use.
- **No migrations.** Any change to the tables means resetting the database.
- **A race in the `is_extra` rule:** two simultaneous requests could both read the same count.
- **Tokens cannot be revoked,** and the rate limiter's counters are per process and in memory.
- **`app.py` is one long file** (about 550 lines). It is consistent and readable now, but it is the first place that would become hard to maintain.
- **Untested areas:** real PostgreSQL, concurrency, load, and the deployed service beyond manual checks (see `docs/test-notes.md`).

### What I would do next
1. Move to PostgreSQL and add migrations (Alembic), so data survives restarts and the schema can change safely.
2. Make the `is_extra` check and insert one locked database transaction, and add a test for it.
3. Add refresh tokens and a way to log out, and keep rate-limit counters in shared storage.
4. Split `app.py` into one module per resource once it grows further.
5. Run the tests automatically on every push (continuous integration) and scan dependencies for known vulnerabilities.


## Declaration

**My own work.** I chose the idea, the data model and the rules (for example that rejected requests do not count and that projects outlive their clients). I wrote in collaboration with AI most of the code and reviewed the AI generated ones.

**Libraries used.** Flask, Flask-SQLAlchemy, SQLAlchemy, Pydantic, Flask-JWT-Extended, bcrypt, Flask-Cors, Flask-Limiter, python-dotenv, gunicorn, pytest, pytest-cov, PyYAML and openapi-spec-validator (all listed in `requirements.txt` and `requirements-dev.txt`). The Swagger UI page loads Swagger UI from a public CDN. No project template or boilerplate was used. 

**Material AI use.** I used Claude (Anthropic) throughout the project for:
- brainstorming and narrowing the idea;
- reviewing my data model and API design and explaining trade-offs;
- drafting and revising the application code (routes, validation, authentication), the seed script, the tests and the OpenAPI file;
- drafting documents (the API spec, notes, README and issue log entries) and diagrams.


**Data and secrets.** All data is dummy data. No real passwords, personal data or secrets are in the repository; secrets are only in environment variables.
