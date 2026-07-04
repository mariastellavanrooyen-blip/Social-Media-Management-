"""One-time Gmail authorization for setups with no local browser (Device flow).

Unlike scripts/gmail_auth.py, this needs no redirect URI and no port exposed
anywhere: it prints a short code and a URL that can be opened on *any* device
with a browser (phone, tablet, another computer) to complete the Google
consent, while this process polls Google in the background for the result.

Requires backend/device_credentials.json — an OAuth client of type
"TVs and Limited Input devices" from Google Cloud Console (see README).
"""

import json
import sys
import time
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEVICE_CREDENTIALS_FILE = BACKEND_DIR / "device_credentials.json"
TOKEN_FILE = BACKEND_DIR / "token.json"

SCOPE = "https://www.googleapis.com/auth/gmail.send"
DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Keep well under typical shell/tool timeouts; re-run the script for a fresh code if needed.
MAX_WAIT_SECONDS = 540


def load_client() -> tuple[str, str]:
    data = json.loads(DEVICE_CREDENTIALS_FILE.read_text())
    installed = data.get("installed", data)
    return installed["client_id"], installed["client_secret"]


def request_device_code(client_id: str) -> dict:
    res = httpx.post(DEVICE_CODE_URL, data={"client_id": client_id, "scope": SCOPE})
    res.raise_for_status()
    return res.json()


def poll_for_token(client_id: str, client_secret: str, device_code: str, interval: int) -> dict:
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(interval)
        res = httpx.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        payload = res.json()
        if res.status_code == 200:
            return payload
        error = payload.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise RuntimeError(f"Device authorization failed: {payload}")
    raise TimeoutError(
        "Timed out waiting for authorization. Run this script again for a fresh code."
    )


def main() -> None:
    if not DEVICE_CREDENTIALS_FILE.exists():
        print(f"Missing {DEVICE_CREDENTIALS_FILE}.")
        print("Create a 'TVs and Limited Input devices' OAuth client in Google Cloud")
        print("Console and save its client_id/client_secret there first.")
        raise SystemExit(1)

    client_id, client_secret = load_client()
    device = request_device_code(client_id)

    print("=" * 60)
    print(f"1. On your tablet, open: {device['verification_url']}")
    print(f"2. Enter this code:      {device['user_code']}")
    print("3. Sign in and grant access.")
    print("=" * 60, flush=True)

    token = poll_for_token(
        client_id, client_secret, device["device_code"], device.get("interval", 5)
    )

    if "refresh_token" not in token:
        print(
            "Warning: no refresh_token returned. If this app's access was already "
            "granted before, revoke it at https://myaccount.google.com/permissions "
            "and run this script again to force a fresh consent.",
            file=sys.stderr,
        )

    TOKEN_FILE.write_text(
        json.dumps(
            {
                "token": token["access_token"],
                "refresh_token": token.get("refresh_token"),
                "token_uri": TOKEN_URL,
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": [SCOPE],
            }
        )
    )
    print(f"Authorized. Token cached at {TOKEN_FILE}.")


if __name__ == "__main__":
    main()
