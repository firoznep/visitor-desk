# Visitor Desk — backend

FastAPI + PostgreSQL 18 + Argon2, tested end-to-end (see "What's already verified" below).

## Layout
```
backend/          FastAPI app, Alembic migrations, tests, seed scripts
db/init/          Runs once when the Postgres container starts fresh
nginx/            TLS termination, rate limiting, reverse proxy to api + frontend
scripts/          backup.sh (encrypted daily backup) and decrypt_export.py (standalone reader)
docker-compose.yml
```

## First-time setup

1. **Generate secrets** (do this once per environment, store the output in a password manager,
   never commit it):
   ```
   cd backend
   pip install -r requirements.txt
   python -m scripts.generate_keys
   ```
   Copy `.env.example` to `.env` and fill in the four generated values plus `DATABASE_URL`,
   `ALLOWED_ORIGINS`, etc.

2. **Database passwords**: copy `.env.db.example` to `.env.db` at the project root and set
   `POSTGRES_PASSWORD` (superuser) and `APP_DB_PASSWORD` (the app's own least-privilege role).

3. **Start Postgres**, then run migrations as the *schema owner* (not the app role — see
   "Two database roles" below):
   ```
   docker compose --env-file .env.db up -d db
   docker compose --env-file .env.db --profile tools run --rm migrate
   ```

4. **Create the first admin user**:
   ```
   docker compose run --rm api python -m scripts.seed_admin --username admin --full-name "Front Office Admin" --role admin
   ```
   This prints a one-time temporary password. Hand it to that person over a secure channel;
   they'll be forced to change it on first login.

5. **Start everything**:
   ```
   docker compose --env-file .env.db up -d
   ```

## What's already verified

This isn't just written — it's been run:
- 16 unit tests (encryption round-trip, wrong-key/wrong-row rejection, ID parsing, password
  strength) — `cd backend && pytest`
- A live Postgres migration end-to-end, including the least-privilege role and grants
- A full HTTP flow through the real API: login, failed-login lockout, scan → auto-fill,
  duplicate-visit rejection, expired-ID flagging (not blocking), role-based access (403 for
  receptionist on admin routes), check-out, admin soft-delete, and the audit trail recording
  every step
- The database column holding the ID number was confirmed to contain ciphertext
  (`k1.c7sVtRc...`), never the plaintext number
- `scripts/decrypt_export.py` was run against a real CSV export of that encrypted column and
  correctly recovered the original ID number and date of birth, using only the key

## Two database roles (why migrations and the API use different connections)

- **Schema owner** (`postgres`, via `MIGRATION_DATABASE_URL`): can create/alter tables. Used
  only for `alembic upgrade`, never by the running API.
- **`visitor_app`** (via `DATABASE_URL`, what the API uses): can only `SELECT`/`INSERT`/`UPDATE`
  on the tables it needs, and cannot `DELETE` anything, anywhere. Even a bug in the API, or a
  fully compromised API container, cannot drop a table or hard-delete a row — the worst it can
  do is set `deleted_at` (soft delete), which admins can see and restore.

## Encryption at rest, and reading your backups

Visitor ID numbers and dates of birth are encrypted with AES-256-GCM before they reach the
database (see `backend/app/crypto.py`). Duplicate-visit checks use a separate HMAC "blind
index" column, so the app can check "has this ID number been seen today" without ever
decrypting anything for that check.

**Reading an encrypted backup, with no app running:** `scripts/decrypt_export.py` is a small,
dependency-light script (just `cryptography`, optionally `psycopg2`) that decrypts straight
from a CSV export or a restored database. It does not import anything from `backend/`, so it
will keep working even if this codebase changes completely later. See the script's own
docstring for exact commands — the short version:

```
gunzip -c visitors_2026-09-29.sql.gz | psql visitors_restore
psql visitors_restore -c "\copy (select id, id_number_enc, id_number_hash, dob_enc from visits) to 'visits_enc.csv' with csv header"
python3 scripts/decrypt_export.py --csv visits_enc.csv --keys "k1:<your-key>" --out visits_decrypted.csv
```

**Key rotation:** `ID_ENCRYPTION_KEYS` accepts multiple keys (`k1:...,k0:...`). Set
`ID_ACTIVE_KEY_ID` to the newest one; old keys stay listed so existing rows (and old backups)
still decrypt. Never remove a key while any backup you might need to read still uses it.

**Daily/weekly backups:** `scripts/backup.sh` runs `pg_dump`, compresses it, and encrypts the
dump itself with GPG before it ever touches disk unencrypted — so a stolen backup file is
useless without the GPG private key, on top of the column-level encryption inside it. Point
your cron at it; the script's header comment has the restore steps.

## Production checklist

- [ ] Real TLS certificate in `nginx/certs/` (not the self-signed one)
- [ ] `.env` has `APP_ENV=production`, `COOKIE_SECURE=true`, real `ALLOWED_ORIGINS`
- [ ] `ID_ENCRYPTION_KEYS`, `ID_INDEX_KEY`, `SCAN_TOKEN_SECRET` generated fresh for this
      environment (never reuse the ones from this test run) and stored in a secrets manager
- [ ] `POSTGRES_PASSWORD` / `APP_DB_PASSWORD` are strong and not the same as any example value
- [ ] `scripts/backup.sh` scheduled via cron, `GPG_RECIPIENT` set to a key you control offline
- [ ] First admin created via `seed_admin.py`, temporary password changed on first login
- [ ] Timezone set correctly in `.env` (`TIMEZONE=Asia/Qatar` by default — this defines what
      "today" means for the receptionist's visitor list)

## Frontend status

The React frontend is wired to the API for login, visitor desk workflows, and admin user
management. The desk dashboard summarizes today's, this week's, this month's, and last month's
visitor counts, and the visitor list displays up to 200 records in a scrollable table. Admins
can create, disable, and re-enable accounts, and reset another user's password to a temporary
password that must be changed on next login. Password resets revoke that user's active
sessions. Visit records allow floors Ground through 99, optional meeting contact details, and
admin-managed department and company options. Run `alembic upgrade head` to apply the
department/company tables and optional-field migrations to an existing database. Manual browser
testing and production Docker image wiring are still pending.

## Frontend (React + Vite + Tailwind v4)

```
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to http://localhost:8000 by default
                      # (set VITE_PROXY_TARGET to point elsewhere)
npm run build         # production build -> frontend/dist, served by nginx (see ../nginx)
```

Login sessions use an HttpOnly cookie plus a CSRF token read from the login response header
and attached to every state-changing request (`src/lib/api.js`). There's no token stored in
`localStorage` — a page refresh requires signing in again, which is a deliberate simplicity
tradeoff; see the comment in `src/context/AuthContext.jsx` if you want to change that later.

**Scanning or manually entering an ID:** `src/components/ScanPanel.jsx` accepts the 3-line
(or 90-character) MRZ text from a compatible USB reader, and also provides a manual ID-details
form for cards without an MRZ. Manual entries are marked as such in the UI and must be checked
against the physical ID by staff. Both paths produce the same short-lived server-signed token;
the existing visit flow encrypts ID numbers and dates of birth at rest. Camera/barcode capture
is not included. A barcode that contains only an ID number cannot provide the other personal
details, so those must still be entered manually.

### Verified so far
`npm run build` succeeds, and the full login → scan → create-visit → list flow was run
end-to-end through axios (the same library and cookie/CSRF pattern `src/lib/api.js` uses)
against the real API and a real Qatar ID MRZ test vector — see the backend section above for
how that MRZ vector was constructed and validated.

### Still to do
- Manual browser click-through testing of MRZ scan and manual ID entry
- Manual browser click-through testing of the admin user-management page
- Wiring the production Docker build (a `frontend/Dockerfile` + nginx static serving — the
  `docker-compose.yml` already has a `frontend` service expecting this)

## Windows development setup (test before production)

This covers running everything natively on Windows for development/testing, without Docker.
(Docker Desktop also works and is simpler if you have it — see the note at the end.)

### 1. Install PostgreSQL 18
Download from https://www.postgresql.org/download/windows/ and run the installer. Remember
the password you set for the `postgres` superuser — you'll need it below. The installer adds
`psql` to your PATH if you tick that option; if not, add
`C:\Program Files\PostgreSQL\18\bin` to PATH yourself.

### 2. Create the database and the app role
Open **SQL Shell (psql)** from the Start menu (or `psql -U postgres` in a terminal) and run:
```sql
CREATE DATABASE visitors;
CREATE ROLE visitor_app LOGIN PASSWORD 'pick-a-strong-password-here';
```
This step is done automatically inside Docker (by `db/init/000_create_role.sh`), but on a
native Windows install there's no such init hook, so you create the role yourself, once.

### 3. Set up Python
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 4. Create `backend\.env`
Copy `backend\.env.example` to `backend\.env`, then generate the encryption keys:
```powershell
python -m scripts.generate_keys
```
Paste those four lines into `.env`, replacing the placeholders. Then set:
```
DATABASE_URL=postgresql+asyncpg://visitor_app:pick-a-strong-password-here@localhost:5432/visitors
MIGRATION_DATABASE_URL=postgresql+asyncpg://postgres:your-postgres-superuser-password@localhost:5432/visitors
ALLOWED_ORIGINS=http://localhost:5173
COOKIE_SECURE=false
APP_ENV=development
```
**Both `DATABASE_URL` and `MIGRATION_DATABASE_URL` matter and are different on purpose:**
migrations need the `postgres` superuser (to create tables and grant permissions), while the
running API uses the restricted `visitor_app` role and can never do schema changes or hard
deletes, even if it's compromised. See "Two database roles" above.

### 5. Run the migration, then seed your first admin
```powershell
alembic upgrade head
python -m scripts.seed_admin --username admin --full-name "Your Name" --role admin
```
Both commands now read `backend\.env` automatically — no manual environment exporting needed
(earlier builds of this project required that; it's fixed as of this version).

### 6. Start the backend
```powershell
uvicorn app.main:app --reload --port 8000
```
Check http://localhost:8000/api/health → should return `{"status":"ok"}`.

### 7. Start the frontend, in a second terminal
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173, log in with the admin account `seed_admin.py` printed.

### Common errors and what they mean
- **`Role "visitor_app" does not exist`** — you skipped step 2, or `MIGRATION_DATABASE_URL`
  isn't set so Alembic tried to use the restricted role instead of the superuser. Fix: run
  step 2, and double-check `MIGRATION_DATABASE_URL` is in `.env`.
- **`password authentication failed`** — the password in `DATABASE_URL` /
  `MIGRATION_DATABASE_URL` doesn't match what you set in step 2 or your Postgres install.
- **`KeyError: 'DATABASE_URL'` or similar** — you're running a command from the wrong folder
  (`.env` is looked for relative to `backend\`), or `.env` wasn't created from `.env.example`.
- **`ModuleNotFoundError`** — the virtual environment isn't activated; re-run
  `venv\Scripts\activate` in that terminal.

### Prefer Docker Desktop instead?
If you have Docker Desktop for Windows, `docker-compose.yml` already automates steps 1–2
(role creation) and 5 (migration via the `migrate` service) for you — see the
"First-time setup" section above. That path avoids the native-install gotchas entirely.
