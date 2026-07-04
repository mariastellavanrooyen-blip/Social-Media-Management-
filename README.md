# Solo CRM + Bulk Cold Email Tool

Lightweight CRM and bulk cold-email tool for a single user. Python/FastAPI backend,
SQLite database, plain HTML/JS frontend (no build step).

## Status

- ✅ Phase 1: Project scaffold, database models, client tracker (list/search/filter/add/edit/delete)
- ⏳ Phase 2 (next): Excel/CSV upload, column mapping, email templates, Gmail send queue,
  suppression list enforcement

## Project structure

```
backend/
  app/
    main.py       FastAPI app + client API routes, serves the frontend
    database.py   SQLAlchemy engine/session setup (SQLite)
    models.py     Client, EmailSend, SuppressionEntry tables
    schemas.py    Pydantic request/response models
    crud.py       DB access functions
  tests/          pytest suite for the client API
  requirements.txt
frontend/
  index.html      Client list: search, filter by status, add
  client.html      Client detail: view/edit notes & fields, delete
  static/          CSS + vanilla JS (list.js, detail.js)
```

## Database models

- **clients** — id, name, email (unique), company, phone, status
  (`lead`/`contacted`/`active`/`closed`), notes, last_contact_date, created_at
- **sends** — log of bulk-email attempts (recipient, subject, status, timestamp).
  Wired up in phase 2.
- **suppression_list** — emails to always skip on bulk sends (unsubscribes/bounces).
  Wired up in phase 2.

The SQLite file is created automatically at `backend/crm.db` on first run.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/index.html to use the client tracker.
API docs are at http://127.0.0.1:8000/docs.

## Test

```bash
cd backend
source .venv/bin/activate
pytest
```
