import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import gmail_client
from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def isolate_gmail_credentials(tmp_path, monkeypatch):
    """Never let tests see (or hit APIs with) whatever real token.json sits on disk locally."""
    monkeypatch.delenv("GOOGLE_TOKEN_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_CREDENTIALS_JSON", raising=False)
    monkeypatch.setattr(gmail_client, "TOKEN_FILE", tmp_path / "token.json")
    monkeypatch.setattr(gmail_client, "CREDENTIALS_FILE", tmp_path / "credentials.json")


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
