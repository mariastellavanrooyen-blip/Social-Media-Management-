# Solo CRM + Bulk Cold Email Tool

Lightweight CRM and bulk cold-email tool for a single user. Python/FastAPI backend,
SQLite database, plain HTML/JS frontend (no build step).

## Status

- ✅ Phase 1: Project scaffold, database models, client tracker (list/search/filter/add/edit/delete)
- ✅ Phase 2: Excel/CSV upload + column mapping, email template with merge-field preview,
  Gmail OAuth2 send queue (throttled, daily-cap safe), suppression list + unsubscribe links

## Project structure

```
backend/
  app/
    main.py          FastAPI app + all API routes, serves the frontend
    database.py      SQLAlchemy engine/session setup (SQLite; DATABASE_URL env var)
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
Dockerfile           Image for deployment (e.g. Fly.io)
fly.toml             Fly.io app config (volume, health check, scale-to-zero)
```

## Database models

- **clients** — id, name, email (unique), company, phone, status
  (`lead`/`contacted`/`active`/`closed`), notes, last_contact_date, created_at
- **sends** — log of every bulk-email attempt (recipient, subject, status `sent`/`failed`,
  error_message, timestamp)
- **suppression_list** — emails always skipped on bulk sends, even if present in an uploaded
  sheet (populated manually or via unsubscribe links)
- **email_templates** — the single reusable cold-email subject/body with `{{merge fields}}`

The SQLite file is created automatically at `backend/crm.db` on first run.

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

## Deploy to Fly.io

The app reads its persistent state from three places that must survive redeploys:
the SQLite DB (`DATABASE_URL`), uploaded sheets (`UPLOADS_DIR`), and the Gmail token
(`GOOGLE_TOKEN_JSON`). On Fly, the DB/uploads live on a mounted volume and the Gmail
token lives in a Fly secret (an env var) — never in a plain file baked into the image.

1. **Install flyctl and log in** (skip if already done):
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Reserve an app name** (must be globally unique) and put it in `fly.toml`:
   ```bash
   fly apps create your-app-name
   ```
   Edit `fly.toml`: set `app = "your-app-name"` and `primary_region` to whatever
   `fly platform regions` shows as closest to you.

3. **Create the persistent volume** (must match `fly.toml`'s `[[mounts]]` source name
   and be in the same region as step 2):
   ```bash
   fly volumes create crm_data --region <your-region> --size 1
   ```

4. **Set secrets.** Never put real values here in the README/repo — always run `fly secrets
   set` interactively (or paste values only in your own terminal), so nothing sensitive ends
   up in git history:
   ```bash
   fly secrets set GOOGLE_TOKEN_JSON='<contents of your local backend/token.json, one line>'
   fly secrets set GOOGLE_CREDENTIALS_JSON='<contents of your local backend/credentials.json>'
   fly secrets set SECRET_KEY='<a freshly generated random value, e.g. `openssl rand -hex 32`>'
   ```
   - `GOOGLE_TOKEN_JSON` is what the app actually needs to send mail — the refresh token
     inside it doesn't expire from use, so nothing here needs rotating.
   - `GOOGLE_CREDENTIALS_JSON` isn't used at runtime (only by the interactive consent
     flow, which never runs on the server) — set for completeness/future re-auth, skip it
     if you'd rather not.
   - `SECRET_KEY` signs unsubscribe links; generate a fresh one rather than reusing anything
     else. Setting it explicitly (instead of relying on an auto-generated file) means
     unsubscribe links keep working across redeploys.

5. **Point `UNSUBSCRIBE_BASE_URL` at the real hostname.** Once you know your app name,
   edit `fly.toml`'s `[env]` block:
   ```toml
   UNSUBSCRIBE_BASE_URL = "https://your-app-name.fly.dev"
   ```
   (A custom domain works the same way — just put that here instead once it's attached.)

6. **Deploy:**
   ```bash
   fly deploy
   ```
   This builds the image on Fly's remote builder (no local Docker required) and starts
   the app with the volume mounted at `/data`.

7. **Verify:**
   ```bash
   fly status
   curl https://your-app-name.fly.dev/healthz
   curl https://your-app-name.fly.dev/api/gmail/status   # should show {"connected": true}
   ```
   Then open `https://your-app-name.fly.dev/index.html` from your tablet.

This config targets Fly's smallest footprint (`shared-cpu-1x`, 256MB, a 1GB volume,
scale-to-zero via `auto_stop_machines`/`min_machines_running = 0`) to fit comfortably
within whatever free allowance Fly currently offers — check
[fly.io/docs/about/pricing](https://fly.io/docs/about/pricing) for current numbers, since
Fly's plans do change over time. Scale-to-zero means the app may take a few seconds to
wake up on the first request after being idle; that's expected.

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
