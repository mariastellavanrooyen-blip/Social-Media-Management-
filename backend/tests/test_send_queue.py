import asyncio
from datetime import datetime

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import send_queue
from app.database import Base
from app.models import EmailSend, SuppressionEntry
from app.send_queue import SendJob


@pytest.fixture()
def send_db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(send_queue, "SessionLocal", test_session_local)
    monkeypatch.setattr(send_queue, "THROTTLE_MIN_SECONDS", 0)
    monkeypatch.setattr(send_queue, "THROTTLE_MAX_SECONDS", 0)
    yield test_session_local


def _authorize(monkeypatch, send_fn=None):
    monkeypatch.setattr(send_queue.gmail_client, "get_credentials", lambda: object())
    monkeypatch.setattr(send_queue.gmail_client, "build_service", lambda creds: object())
    monkeypatch.setattr(send_queue.gmail_client, "send_email", send_fn or (lambda *a, **k: None))


def test_run_job_sends_all_valid_rows(send_db, monkeypatch):
    sent = []
    _authorize(monkeypatch, lambda service, to, subject, body, unsubscribe_url: sent.append((to, subject)))

    df = pd.DataFrame(
        [
            {"Name": "Ada", "Email": "ada@example.com"},
            {"Name": "Grace", "Email": "grace@example.com"},
        ]
    )
    job = SendJob(job_id="j1", total=len(df))
    asyncio.run(
        send_queue.run_job(job, df, {"name": "Name", "email": "Email"}, "Hi {{name}}", "Body {{name}}")
    )

    assert job.status == "completed"
    assert job.sent == 2
    assert job.failed == 0
    assert sent == [("ada@example.com", "Hi Ada"), ("grace@example.com", "Hi Grace")]

    logs = send_db().query(EmailSend).all()
    assert len(logs) == 2
    assert all(log.status == "sent" for log in logs)


def test_run_job_skips_suppressed(send_db, monkeypatch):
    db = send_db()
    db.add(SuppressionEntry(email="grace@example.com"))
    db.commit()

    sent = []
    _authorize(monkeypatch, lambda *a, **k: sent.append(a))

    df = pd.DataFrame(
        [
            {"Name": "Ada", "Email": "ada@example.com"},
            {"Name": "Grace", "Email": "grace@example.com"},
        ]
    )
    job = SendJob(job_id="j2", total=len(df))
    asyncio.run(send_queue.run_job(job, df, {"name": "Name", "email": "Email"}, "s", "b"))

    assert job.sent == 1
    assert job.skipped_suppressed == 1
    assert len(sent) == 1


def test_run_job_logs_invalid_email(send_db, monkeypatch):
    _authorize(monkeypatch)

    df = pd.DataFrame([{"Name": "NoEmail", "Email": ""}])
    job = SendJob(job_id="j3", total=len(df))
    asyncio.run(send_queue.run_job(job, df, {"name": "Name", "email": "Email"}, "s", "b"))

    assert job.status == "completed"
    assert job.skipped_invalid == 1
    assert job.sent == 0

    logs = send_db().query(EmailSend).all()
    assert len(logs) == 1
    assert logs[0].status == "failed"


def test_run_job_logs_gmail_send_failure(send_db, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("quota exceeded")

    _authorize(monkeypatch, boom)

    df = pd.DataFrame([{"Name": "Ada", "Email": "ada@example.com"}])
    job = SendJob(job_id="j4", total=len(df))
    asyncio.run(send_queue.run_job(job, df, {"name": "Name", "email": "Email"}, "s", "b"))

    assert job.failed == 1
    assert job.sent == 0
    log = send_db().query(EmailSend).first()
    assert log.status == "failed"
    assert "quota exceeded" in log.error_message


def test_run_job_stops_at_daily_limit(send_db, monkeypatch):
    db = send_db()
    for _ in range(2):
        db.add(
            EmailSend(
                recipient_email="x@example.com",
                subject="s",
                status="sent",
                sent_at=datetime.utcnow(),
            )
        )
    db.commit()

    monkeypatch.setattr(send_queue, "DAILY_LIMIT", 2)
    sent = []
    _authorize(monkeypatch, lambda *a, **k: sent.append(a))

    df = pd.DataFrame([{"Name": "Ada", "Email": "ada@example.com"}])
    job = SendJob(job_id="j5", total=len(df))
    asyncio.run(send_queue.run_job(job, df, {"name": "Name", "email": "Email"}, "s", "b"))

    assert job.status == "stopped_daily_limit"
    assert job.sent == 0
    assert len(sent) == 0


def test_run_job_fails_cleanly_when_gmail_not_authorized(send_db, monkeypatch):
    def raise_not_authorized():
        raise send_queue.gmail_client.GmailNotAuthorized("not connected")

    monkeypatch.setattr(send_queue.gmail_client, "get_credentials", raise_not_authorized)

    df = pd.DataFrame([{"Name": "Ada", "Email": "ada@example.com"}])
    job = SendJob(job_id="j6", total=len(df))
    asyncio.run(send_queue.run_job(job, df, {"name": "Name", "email": "Email"}, "s", "b"))

    assert job.status == "failed"
    assert job.error == "not connected"
