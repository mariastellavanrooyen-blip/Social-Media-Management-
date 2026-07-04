# Solo CRM + Bulk Cold Email Tool

Lightweight CRM and bulk cold-email tool for a single user. Python/FastAPI backend,
plain HTML/JS frontend (no build step). SQLite locally by default; Postgres (e.g. a free
Neon or Supabase database) in production, via `DATABASE_URL`.

## Status

- ✅ Phase 1: Project scaffold, database models, client tracker (list/search/filter/add/edit/delete)
- ✅ Phase 2: Excel/CSV upload + column mapping, email template with merge-field preview,
  Gmail OAuth2 send queue (throttled, daily-cap safe), suppression list + unsubscribe links

## Project structure

```
backend/
  app/
    main.py          FastAPI app + all API routes, serves the frontend
    database.py      SQLAlchemy engine/session setup (DATABASE_URL env var; sqlite locally,
                     postgres in production — normalizes postgres:// -> postgresql://)
    models.py        Client, EmailSend, SuppressionEntry, EmailTemplate tables
    schemas.py       Pydantic request/response models
    crud.py          DB access functions
    upload_store.py  Parses .csv/.xlsx uploads (pandas), persists them (UPLOADS_DIR env var)
    merge.py         {{merge field}} rendering for the email template
    security.py      Signed unsubscribe tokens (itsdangerous)
    gmail_client.py  Gmail API OAuth2 client (GOOGLE_TOKEN_JSON env var or local token.json)
    send_queue.py    Throttled background bulk-send job runner
  scripts/
    gmail_auth.py         One-time interactive OAuth consent — run locally, not by the server
    gmail_manual_token.py Caches a manually-obtained refresh token (see Option B below)
  tests/             pytest suite (client API, upload/merge, template, suppression, send queue)
  requirements.txt
frontend/
  index.html         Client list: search, filter by status, add
  client.html        Client detail: view/edit notes & fields, delete
  send.html          Bulk email: upload sheet -> map columns -> edit template -> preview -> send
  suppression.html   View/add/remove suppressed addresses
  static/            CSS + vanilla JS
Dockerfile           Image for deployment
render.yaml          Render Blueprint (free web service, no persistent disk needed)
```

## Database models

- **clients** — id, name, email (unique), company, phone, status
  (`lead`/`contacted`/`active`/`closed`), notes, last_contact_date, created_at
- **sends** — log of every bulk-email attempt (recipient, subject, status `sent`/`failed`,
  error_message, timestamp)
- **suppression_list** — emails always skipped on bulk sends, even if present in an uploaded
  sheet (populated manually or via unsubscribe links)
- **email_templates** — the single reusable cold-email subject/body with `{{merge fields}}`

Locally, the SQLite file is created automatically at `backend/crm.db` on first run. In
production, set `DATABASE_URL` to a Postgres connection string (see "Deploy to Render" below)
— `create_all()` creates the tables there the same way, no migration framework needed for
an app this size.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Gmail setup (one-time)

Either path below ends the same way: a `backend/token.json` refresh token that the web app
reads for every send (it never runs either flow itself — both are one-time, manual steps).

### Option A — you have a browser on the same machine you run the server on

1. In Google Cloud Console, create an OAuth client (type "Desktop app"), enable the Gmail API,
   and download its credentials as `backend/credentials.json` (never committed — it's gitignored).
2. Run:
   ```bash
   cd backend
   source .venv/bin/activate
   python scripts/gmail_auth.py
   ```
   This opens a local browser for the Google consent screen and caches the resulting token.

### Option B — no local browser to run scripts/gmail_auth.py on (e.g. driving this from a tablet)

Google's Device Authorization flow (short code + `google.com/device`) looks like the obvious
fit here, but Google rejects restricted/sensitive scopes — including `gmail.send` — on that
flow entirely, so it can't be used for this app. Instead, use Google's own **OAuth Playground**
as the redirect target — it completes the whole consent flow in-browser (works fine on a
tablet) and hands you the resulting refresh token to paste in yourself, with nothing on our
side needing to receive a redirect.

1. In Google Cloud Console, create a **separate** OAuth client of type **"Web application"**,
   with `https://developers.google.com/oauthplayground` added under **Authorized redirect
   URIs**. Note its client ID and client secret.
2. On any device's browser, go to https://developers.google.com/oauthplayground
3. Gear icon (top right) → check "Use your own OAuth credentials" → paste the client ID/secret
   from step 1.
4. Under "Input your own scopes", enter `https://www.googleapis.com/auth/gmail.send` and click
   **Authorize APIs**. Sign in and grant access.
5. Back on the Playground, click **Exchange authorization code for tokens**.
6. Copy the **Refresh token** shown, then run:
   ```bash
   cd backend
   source .venv/bin/activate
   python scripts/gmail_manual_token.py <client_id> <client_secret> <refresh_token>
   ```
   This writes `token.json` and immediately exercises the refresh token against Google to
   confirm it actually works.

Check connection status any time at `GET /api/gmail/status`, or the badge on the Bulk Email page.

Sends are throttled to one every 4-5 seconds and stop automatically once today's send count
nears 450, safely under Gmail's free-tier 500/day limit (`GMAIL_DAILY_LIMIT` env var to override).

## Deploy to Render (free tier, no card required)

Render's free web service has no persistent disk, so nothing this app needs to survive a
restart can live in a local file: the database is an external free Postgres (Neon or
Supabase), and the Gmail token is an env var (`GOOGLE_TOKEN_JSON`) rather than a local
`token.json`. Uploaded sheets still land on local disk during a single upload→send session
(fine — that's normally minutes, not across restarts), but don't expect an in-progress
upload to survive the service spinning down.

Render deploys straight from this GitHub repo via Render's own dashboard integration — no
GitHub Actions workflow, no CLI, nothing to install. `render.yaml` in the repo root is a
Render "Blueprint": connecting the repo and pointing Render at this file provisions the
service with the right settings pre-filled, prompting you for the secret values.

**One-time setup, all from a browser:**

1. **Create a free Postgres database** (Neon is simplest — just a connection string, no
   extra product surface to navigate):
   - Go to neon.tech, sign up, create a project.
   - Copy the connection string it shows you (starts with `postgres://`, already includes
     `?sslmode=require`) — this is your `DATABASE_URL`.

2. **Create the Render web service:**
   - Go to render.com, sign up, connect your GitHub account, and grant it access to
     `mariastellavanrooyen-blip/Social-Media-Management-`.
   - New + → Blueprint → select this repo → Render reads `render.yaml` and shows the
     `solo-crm-ee2172` web service with its env vars.
   - It'll prompt for the `sync: false` values — fill in:
     - `DATABASE_URL` — the Neon connection string from step 1.
     - `GOOGLE_TOKEN_JSON` — the Gmail refresh token (see "Gmail setup" above for how to get
       one; never commit this value anywhere).
     - `SECRET_KEY` — a freshly generated random value (`openssl rand -hex 32`), not reused
       from anything else. Signs unsubscribe links; keeping it stable across redeploys is
       what keeps previously-sent unsubscribe links working.
     - `GOOGLE_CREDENTIALS_JSON` — optional, skip unless you want it for a future re-auth.
   - Confirm and create — Render builds the Dockerfile and deploys automatically. Every
     future push to the connected branch redeploys automatically too.

3. **Fix up the hostname once you know it.** Render assigns `https://<service-name>.onrender.com`
   (already set to `https://solo-crm-ee2172.onrender.com` in `render.yaml` to match the
   service name above) — if Render gave you a different subdomain because that name was
   taken, update `UNSUBSCRIBE_BASE_URL` in `render.yaml` to match and push.

**Verify:**
```bash
curl https://solo-crm-ee2172.onrender.com/healthz
curl https://solo-crm-ee2172.onrender.com/api/gmail/status   # should show {"connected": true}
```

Free-tier services spin down after 15 minutes idle and take a few seconds to wake on the
next request — that's expected, not a bug.

## Run locally

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

- Clients: http://127.0.0.1:8000/index.html
- Bulk email (upload/map/template/preview/send): http://127.0.0.1:8000/send.html
- Suppression list: http://127.0.0.1:8000/suppression.html
- API docs: http://127.0.0.1:8000/docs

`UNSUBSCRIBE_BASE_URL` (default `http://localhost:8000`) controls the host used in the
unsubscribe links embedded in outgoing emails — set it to wherever this app is actually
reachable from the internet before sending real campaigns, otherwise recipients can't unsubscribe.

## Test

```bash
cd backend
source .venv/bin/activate
pytest
```

Gmail sends are mocked in tests — no real network calls or valid OAuth token are required to
run the suite.
