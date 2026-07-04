"""Run this once, locally, on a machine with a browser, to grant Gmail send access.

    cd backend
    source .venv/bin/activate
    python scripts/gmail_auth.py

It opens a browser for the Google OAuth consent screen and caches the resulting
refresh token in token.json (gitignored). The web app reads that token to send
mail — it never runs this interactive flow itself.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.gmail_client import CREDENTIALS_FILE, TOKEN_FILE, run_authorization_flow  # noqa: E402

if __name__ == "__main__":
    if not CREDENTIALS_FILE.exists():
        print(f"Missing {CREDENTIALS_FILE}. Download your OAuth client credentials from")
        print("Google Cloud Console and save them there before running this script.")
        raise SystemExit(1)

    run_authorization_flow()
    print(f"Authorized. Token cached at {TOKEN_FILE}.")
