"""Cache a manually-obtained Gmail refresh token into backend/token.json.

For setups with no local browser to complete the standard flow (scripts/gmail_auth.py)
and where Google's Device Authorization Grant isn't an option — Google rejects
restricted/sensitive scopes like gmail.send on that flow entirely.

Get a refresh token via Google's OAuth Playground (works from any browser, e.g. a tablet):
  1. Create a "Web application" OAuth client in Google Cloud Console with
     https://developers.google.com/oauthplayground registered as an authorized
     redirect URI. Note its client ID and client secret.
  2. Go to https://developers.google.com/oauthplayground
  3. Click the gear icon (top right) -> check "Use your own OAuth credentials" ->
     paste that client ID and client secret.
  4. In the left panel, under "Input your own scopes", enter
     https://www.googleapis.com/auth/gmail.send and click "Authorize APIs".
  5. Sign in and grant access. You'll be returned to the Playground.
  6. Click "Exchange authorization code for tokens".
  7. Copy the "Refresh token" value shown.

Usage:
    python scripts/gmail_manual_token.py <client_id> <client_secret> <refresh_token>

This writes token.json and immediately exercises the refresh token against Google
to confirm it actually works, rather than waiting to find out at send time.
"""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = BACKEND_DIR / "token.json"
SCOPE = "https://www.googleapis.com/auth/gmail.send"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: python scripts/gmail_manual_token.py "
            "<client_id> <client_secret> <refresh_token>"
        )
        raise SystemExit(1)

    client_id, client_secret, refresh_token = sys.argv[1:4]

    TOKEN_FILE.write_text(
        json.dumps(
            {
                "refresh_token": refresh_token,
                "token_uri": TOKEN_URI,
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": [SCOPE],
            }
        )
    )

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), [SCOPE])
    creds.refresh(Request())  # exercises the refresh token now, not at first send
    TOKEN_FILE.write_text(creds.to_json())
    print(f"Gmail is connected. Token cached at {TOKEN_FILE}.")


if __name__ == "__main__":
    main()
