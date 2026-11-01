# Issue log

Bugs found, options considered, and how each was fixed. Newest last.

| # | Issue | Found | Status |
|---|---|---|---|
| 1 | `ondelete` passed to `db.Column` crashed the app | Week 1 | Fixed |
| 2 | SQLite ignored foreign keys, so delete rules did nothing | Week 1 | Fixed |
| 3 | Unknown or non-integer URLs returned Flask's default HTML 404 | Week 1 | Fixed |
| 4 | Client emails were unique across all users | Week 2 (2026-10-19) | Fixed |
| 5 | Very large IDs returned a 500 error instead of a 404 | Week 2 (2026-10-19) | Fixed |
| 6 | The test suite took 80 seconds because of password hashing | Week 3 (2026-11-01) | Fixed |
| 7 | Rate limiting would have shared one limit between all users on the host | Week 3 (2026-11-01) | Fixed |

---

## Issue 1: `ondelete` passed to `db.Column` crashed the app
- **Problem:** I wrote `db.Column(..., ondelete='SET NULL')` on `Project.client_id`. `Column` does not accept `ondelete`, so the app crashed when the models loaded.
- **Options considered:** put the rule on the column (not supported); define a separate table-level foreign key constraint; pass `ondelete` to `db.ForeignKey`.
- **Fix:** moved the rule into `db.ForeignKey('clients.id', ondelete='SET NULL')`. The same applies to the `CASCADE` rule on `revision_requests.project_id`.
- **Verified:** the models load, and deleting a client leaves its projects with `client_id` set to `NULL`.

## Issue 2: SQLite ignored foreign keys, so delete rules did nothing
- **Problem:** SQLite does not enforce foreign keys unless they are switched on for every connection. Without that, `SET NULL` and `CASCADE` silently did nothing, and a revision request could point at a project that did not exist.
- **Options considered:** handle every delete in application code; move to PostgreSQL straight away; switch foreign keys on for each SQLite connection.
- **Fix:** added a connection listener in `models.py` that runs `PRAGMA foreign_keys=ON` for every SQLite connection. This keeps SQLite for easy local running, and the database enforces the rules.
- **Verified:** a revision request with a missing `project_id` is rejected, deleting a client keeps its projects, and deleting a project removes its revision requests.

## Issue 3: Unknown or non-integer URLs returned Flask's default HTML 404
- **Problem:** a request such as `/projects/abc` returned Flask's HTML error page, which broke the rule that every error uses the same JSON format.
- **Options considered:** leave the default page; return JSON errors only from inside each route (this misses URLs that match no route); add one global error handler.
- **Fix:** added a global handler, later extended to every HTTP error and to unexpected errors, so every response uses `{ "error": { "code", "message" } }`.
- **Verified:** `/projects/abc`, unknown URLs, and wrong methods (405) all return the standard JSON error.

## Issue 4: Client emails were unique across all users
- **Problem:** `clients.email` was `unique=True`, which was written when the app had a single freelancer. After adding users, a second freelancer could not save a client whose email another freelancer already had. The rejection also revealed that someone else had that client.
- **Options considered:** keep the global rule (blocks legitimate use and leaks information); remove uniqueness (the same user could add duplicates); make it unique per user.
- **Fix:** replaced `unique=True` with `UniqueConstraint('user_id', 'email', name='uq_clients_user_id_email')`. Adding the same client email twice as one user returns 409. Emails are trimmed and lowercased on input.
- **Verified:** two users can save the same client email, and the same user saving it twice is rejected (both covered by automated checks).

## Issue 5: Very large IDs returned a 500 error instead of a 404
- **Problem:** a request such as `/clients/99999999999999999999` made SQLite raise an `OverflowError`, and the API answered with a 500 error. The same happened for a huge `client_id` in a request body.
- **Options considered:** limit the ID range in the URL converter (tried this, but Flask's router then returned a wrong 405 for some methods, so I dropped it); check the range inside every route (repeated code); add one `OverflowError` handler for URLs and a maximum value for body IDs.
- **Fix:** an `OverflowError` handler returns the normal 404 (no record can have an ID that large), and `IntId` in `schemas.py` caps body IDs at 2,147,483,647, so those return 400.
- **Verified:** huge, zero, negative and decimal IDs all return 404, and a huge `client_id` in a body returns 400. All 151 automated checks pass.

## Issue 6: The test suite took 80 seconds because of password hashing
- **Problem:** every test that registers a user hashes a password with bcrypt, which is deliberately slow (12 rounds). With about 170 tests the suite took 80 seconds, which is too slow to run often and works against the "tests run with one command" goal.
- **Options considered:** reuse one logged-in user across tests (tests would share state and break each other); mock the hashing (then the real hashing is not tested); make the number of rounds a setting and lower it only in tests.
- **Fix:** added a `BCRYPT_ROUNDS` setting (default 12) that `conftest.py` sets to 4 before the app loads. Production behaviour is unchanged, and the hashing code is still the real bcrypt.
- **Verified:** the full suite now runs in about 5 to 10 seconds, and a test still checks that stored passwords are bcrypt hashes.

## Issue 7: Rate limiting would have shared one limit between all users on the host
- **Problem:** the login and register limits are counted per client address. On Render the app sits behind a proxy, so every request appears to come from the proxy's address. One person's failed logins could then lock out everyone.
- **Options considered:** always trust the `X-Forwarded-For` header (anyone could spoof it when the app is not behind a proxy, to dodge the limit); skip rate limiting on the live host; trust the header only when told the app is behind a proxy.
- **Fix:** added a `BEHIND_PROXY` setting. When it is `1`, Flask reads the real client address from the proxy's header (Werkzeug `ProxyFix`, trusting one proxy). It is `0` by default and set to `1` in `render.yaml`.
- **Verified:** two tests run the app in a fresh process: with the setting on, one address gets blocked after 10 attempts while a second address is not; with it off, the forwarded header is ignored.
