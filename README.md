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
    database.py      SQLAlchemy engine/session setup (SQLite)
    models.py        Client, EmailSend, SuppressionEntry, EmailTemplate tables
    schemas.py       Pydantic request/response models
    crud.py          DB access functions
    upload_store.py  Parses .csv/.xlsx uploads (pandas), persists them to backend/uploads/
    merge.py         {{merge field}} rendering for the email template
    security.py      Signed unsubscribe tokens (itsdangerous)
    gmail_client.py  Gmail API OAuth2 client (credentials.json / token.json)
    send_queue.py    Throttled background bulk-send job runner
  scripts/
    gmail_auth.py    One-time interactive OAuth consent — run locally, not by the server
  tests/             pytest suite (client API, upload/merge, template, suppression, send queue)
  requirements.txt
frontend/
  index.html         Client list: search, filter by status, add
  client.html        Client detail: view/edit notes & fields, delete
  send.html          Bulk email: upload sheet -> map columns -> edit template -> preview -> send
  suppression.html   View/add/remove suppressed addresses
  static/            CSS + vanilla JS
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

## Run

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
