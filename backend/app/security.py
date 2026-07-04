import os
import secrets
from pathlib import Path

from itsdangerous import BadSignature, URLSafeSerializer

_SECRET_FILE = Path(__file__).resolve().parent.parent / ".secret_key"


def _load_or_create_secret() -> str:
    env_secret = os.environ.get("SECRET_KEY")
    if env_secret:
        return env_secret
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()
    secret = secrets.token_hex(32)
    _SECRET_FILE.write_text(secret)
    return secret


_serializer = URLSafeSerializer(_load_or_create_secret(), salt="unsubscribe")


def make_unsubscribe_token(email: str) -> str:
    return _serializer.dumps(email.lower())


def read_unsubscribe_token(token: str) -> str | None:
    try:
        return _serializer.loads(token)
    except BadSignature:
        return None
