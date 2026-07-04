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

### Option B — no local browser (e.g. running this on a headless box, driving it from a tablet/phone)

Uses Google's Device Authorization flow — no redirect URI and no exposed port required.

1. In Google Cloud Console, create a **separate** OAuth client of type **"TVs and Limited Input
   devices"** (Gmail API must already be enabled on the project) and save its `client_id`/
   `client_secret` as `backend/device_credentials.json` (gitignored), e.g.:
   ```json
   {"installed": {"client_id": "...", "client_secret": "..."}}
   ```
2. Make sure your Google account is under **OAuth consent screen → Test users** and that
   `gmail.send` is listed as a scope.
3. Run:
   ```bash
   cd backend
   source .venv/bin/activate
   python scripts/gmail_device_auth.py
   ```
   It prints a short code and a URL (`google.com/device`) — open that URL and enter the code on
   any device with a browser (your tablet is fine), sign in, and grant access. The script polls
   Google in the background and writes `token.json` once you approve it.

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
