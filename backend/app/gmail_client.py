import base64
import html
import json
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

BACKEND_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = Path(os.environ.get("GOOGLE_CREDENTIALS_FILE", str(BACKEND_DIR / "credentials.json")))
TOKEN_FILE = Path(os.environ.get("GOOGLE_TOKEN_FILE", str(BACKEND_DIR / "token.json")))


class GmailNotAuthorized(Exception):
    pass


def _load_token_info() -> dict | None:
    """GOOGLE_TOKEN_JSON (a Fly secret / env var) wins over the local token.json file.

    On a cloud host there's no writable-and-persistent plain file by default, so
    production deployments should set GOOGLE_TOKEN_JSON instead of relying on TOKEN_FILE.
    """
    env_token = os.environ.get("GOOGLE_TOKEN_JSON")
    if env_token:
        return json.loads(env_token)
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def is_connected() -> bool:
    info = _load_token_info()
    if info is None:
        return False
    try:
        creds = Credentials.from_authorized_user_info(info, SCOPES)
    except Exception:
        return False
    return creds.valid or bool(creds.expired and creds.refresh_token)


def get_credentials() -> Credentials:
    """Load cached OAuth credentials, refreshing the access token if needed.

    Never triggers the interactive consent flow itself — that only happens via
    scripts/gmail_auth.py or scripts/gmail_manual_token.py, run once locally.
    """
    info = _load_token_info()
    if info is None:
        raise GmailNotAuthorized(
            "Gmail is not connected. Set the GOOGLE_TOKEN_JSON secret (or run "
            "scripts/gmail_auth.py / scripts/gmail_manual_token.py locally) to grant "
            "gmail.send access."
        )
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Only the local-file path is writable-and-persistent; a GOOGLE_TOKEN_JSON
            # secret can't be updated from inside the running app, and doesn't need to be
            # — it'll simply refresh again next time from the same refresh_token.
            if not os.environ.get("GOOGLE_TOKEN_JSON"):
                TOKEN_FILE.write_text(creds.to_json())
        else:
            raise GmailNotAuthorized(
                "Gmail authorization expired or was revoked. Re-run the auth script "
                "locally and update the GOOGLE_TOKEN_JSON secret."
            )
    return creds


def run_authorization_flow() -> None:
    """Interactive, one-time OAuth consent flow. Run manually — never from the server."""
    env_credentials = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if env_credentials and not CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.write_text(env_credentials)
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"{CREDENTIALS_FILE} not found — place your Google OAuth credentials.json there "
            "first, or set the GOOGLE_CREDENTIALS_JSON environment variable"
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())


def build_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds)


def plain_text_to_html(text: str) -> str:
    """Turn a plain-text merged body into HTML that preserves the author's line breaks.

    Sending raw text as the "html" MIME subtype (with no markup at all) makes HTML email
    clients collapse every line break into one run-on paragraph, and leaves any stray
    "<", ">", "&" in the text — including from merged spreadsheet data — unescaped.
    """
    paragraphs = re.split(r"\n\s*\n", text.strip())
    html_paragraphs = [
        html.escape(paragraph).replace("\n", "<br>") for paragraph in paragraphs if paragraph.strip()
    ]
    return "".join(f'<p style="margin:0 0 1em;">{p}</p>' for p in html_paragraphs)


def send_email(service, to: str, subject: str, body: str, unsubscribe_url: str) -> None:
    message = MIMEMultipart("alternative")
    message["To"] = to
    message["Subject"] = subject
    message["List-Unsubscribe"] = f"<{unsubscribe_url}>"

    footer = (
        '<hr><p style="font-size:12px;color:#888">'
        f'<a href="{unsubscribe_url}">Unsubscribe</a></p>'
    )
    message.attach(MIMEText(plain_text_to_html(body) + footer, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
