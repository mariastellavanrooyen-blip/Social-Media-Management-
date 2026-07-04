import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

BACKEND_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BACKEND_DIR / "credentials.json"
TOKEN_FILE = BACKEND_DIR / "token.json"


class GmailNotAuthorized(Exception):
    pass


def is_connected() -> bool:
    if not TOKEN_FILE.exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    except Exception:
        return False
    return creds.valid or bool(creds.expired and creds.refresh_token)


def get_credentials() -> Credentials:
    """Load cached OAuth credentials, refreshing the access token if needed.

    Never triggers the interactive consent flow itself — that only happens via
    `scripts/gmail_auth.py`, run once on a machine with browser access.
    """
    if not TOKEN_FILE.exists():
        raise GmailNotAuthorized(
            "Gmail is not connected. Run `python scripts/gmail_auth.py` once "
            "on a machine with a browser to grant gmail.send access."
        )
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        else:
            raise GmailNotAuthorized(
                "Gmail authorization expired or was revoked. Run "
                "`python scripts/gmail_auth.py` again."
            )
    return creds


def run_authorization_flow() -> None:
    """Interactive, one-time OAuth consent flow. Run manually — never from the server."""
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"{CREDENTIALS_FILE} not found — place your Google OAuth credentials.json there first"
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())


def build_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds)


def send_email(service, to: str, subject: str, html_body: str, unsubscribe_url: str) -> None:
    message = MIMEMultipart("alternative")
    message["To"] = to
    message["Subject"] = subject
    message["List-Unsubscribe"] = f"<{unsubscribe_url}>"

    footer = (
        '<hr><p style="font-size:12px;color:#888">'
        f'<a href="{unsubscribe_url}">Unsubscribe</a></p>'
    )
    message.attach(MIMEText(html_body + footer, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
