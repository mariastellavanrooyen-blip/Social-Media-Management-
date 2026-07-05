---
name: verify
description: Project-specific recipe for driving Marisol CRM (FastAPI + SQLite/Postgres + Gmail send) at runtime to verify changes.
---

# Verify: Marisol CRM

## Build/launch

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # first time only
rm -f crm.db                                                          # fresh DB
.venv/bin/uvicorn app.main:app --port 8xxx
```

Run in background (`run_in_background: true` with the Bash tool, or `nohup ... &` plus
`disown` — plain `cmd &` in the same call as a later `sleep`/`curl` is flaky in this sandbox
and tends to throw exit 144). Always pick a fresh port per run to avoid stale binds.

- `GET /healthz` → `{"status":"ok"}` confirms the process is up.
- `GET /api/gmail/status` confirms Gmail auth state (see caveat below).

## Real Gmail send pipeline (no mocks)

This sandbox has a real, working Gmail OAuth token in `backend/token.json` (`GOOGLE_TOKEN_JSON`
env var also works and takes priority — see `app/gmail_client.py`). That means the full
upload → merge → send pipeline can be driven for real, not just unit-tested:

```bash
printf 'Name,Email\nTest,youraddress@example.com\n' > /tmp/t.csv
curl -s -F "file=@/tmp/t.csv;type=text/csv" http://127.0.0.1:8xxx/api/upload   # -> upload_id
curl -s -X POST http://127.0.0.1:8xxx/api/upload/<id>/preview -H "Content-Type: application/json" \
  -d '{"mapping":{"name":"Name","email":"Email"},"subject":"...","body":"...","sample_size":1}'
curl -s -X POST http://127.0.0.1:8xxx/api/send/start -H "Content-Type: application/json" \
  -d '{"upload_id":"<id>","mapping":{...},"subject":"...","body":"..."}'          # -> job_id
curl -s http://127.0.0.1:8xxx/api/send/jobs/<job_id>   # poll until status != "running"
```

**To simulate a Gmail auth failure** (e.g. to test error handling in `send_queue.run_job`),
override the token with a broken one via env var rather than touching the real
`backend/token.json`:

```bash
cat > /tmp/broken_token.json << 'EOF'
{"token": "fake", "refresh_token": "1//invalid", "token_uri": "https://oauth2.googleapis.com/token",
 "client_id": "<real client_id>", "client_secret": "wrong-secret",
 "scopes": ["https://www.googleapis.com/auth/gmail.send"], "expiry": "2020-01-01T00:00:00Z"}
EOF
GOOGLE_TOKEN_JSON="$(cat /tmp/broken_token.json)" .venv/bin/uvicorn app.main:app --port 8xxx
```

The past `expiry` forces a real refresh attempt against Google's token endpoint, which fails
with a genuine `google.auth.exceptions.RefreshError` (distinct from our own
`GmailNotAuthorized`) — this is what actually exposed the "job stuck at running forever" bug,
since only `GmailNotAuthorized` was being caught around credential setup.

Caveat: `is_connected()` / `GET /api/gmail/status` only checks that a refresh token is
*present*, not that it actually works — it can report `connected: true` even for a broken
token. Don't treat that endpoint as proof a send will succeed.

## Frontend (Playwright)

Chromium is pre-installed: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`,
`executable_path="/opt/pw-browsers/chromium"`. `pip install playwright` (no `playwright
install` needed/wanted). Drive `http://127.0.0.1:8xxx/index.html` etc. with
`sync_playwright()`; the 4 pages are `index.html`, `client.html`, `send.html`,
`suppression.html`.

Gotchas:
- `page.wait_for_selector("#foo.hidden")` defaults to waiting for *visible* — use
  `state="attached"` when waiting for an element to gain a class that hides it.
- Re-running a script that adds a client with the same hardcoded email will hit the unique
  constraint (409) on the second run — the modal correctly stays open, but it'll look like a
  failure if you don't expect it. Use a fresh email or wipe `crm.db` between runs.
- External hosts (Google Fonts, fly.io, render.com, neon.tech, etc.) are blocked by this
  sandbox's egress policy — expect `net::ERR_CONNECTION_RESET` / `403 CONNECT tunnel failed`
  for those specifically; same-origin requests are unaffected.

## No live deploy access

`fly.io`, `onrender.com`, `neon.tech`, `supabase.com` are all blocked from this sandbox
(egress policy, confirmed repeatedly — don't retry, don't try to route around it). Render
deploy status must be checked by the user via their own dashboard/browser; ask for a
screenshot rather than trying to curl it.

## Cleanup between runs

```bash
pkill -f "uvicorn app.main:app" 2>/dev/null
rm -f backend/crm.db backend/uploads/*.csv
```
