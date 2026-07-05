import asyncio
import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from app import gmail_client, merge
from app.crud import get_client_by_email, is_suppressed
from app.database import SessionLocal
from app.models import EmailSend
from app.security import make_unsubscribe_token

DAILY_LIMIT = int(os.environ.get("GMAIL_DAILY_LIMIT", "450"))
THROTTLE_MIN_SECONDS = 4.0
THROTTLE_MAX_SECONDS = 5.0
UNSUBSCRIBE_BASE_URL = os.environ.get("UNSUBSCRIBE_BASE_URL", "http://localhost:8000")


@dataclass
class SendJob:
    job_id: str
    total: int
    status: str = "running"  # running | completed | stopped_daily_limit | failed
    sent: int = 0
    failed: int = 0
    skipped_suppressed: int = 0
    skipped_invalid: int = 0
    error: str | None = None


JOBS: dict[str, SendJob] = {}


def _sent_today_count(db) -> int:
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(EmailSend)
        .filter(EmailSend.status == "sent", EmailSend.sent_at >= start_of_day)
        .count()
    )


def start_job(df: pd.DataFrame, mapping: dict[str, str], subject: str, body: str) -> SendJob:
    job = SendJob(job_id=uuid.uuid4().hex, total=len(df))
    JOBS[job.job_id] = job
    asyncio.create_task(run_job(job, df, mapping, subject, body))
    return job


def get_job(job_id: str) -> SendJob | None:
    return JOBS.get(job_id)


async def run_job(
    job: SendJob, df: pd.DataFrame, mapping: dict[str, str], subject: str, body: str
) -> None:
    db = SessionLocal()
    try:
        try:
            creds = gmail_client.get_credentials()
            service = gmail_client.build_service(creds)
        except gmail_client.GmailNotAuthorized as e:
            job.status = "failed"
            job.error = str(e)
            return

        for _, row in df.iterrows():
            context = merge.build_context(row.to_dict(), mapping)
            recipient = context.get("email", "").strip()

            if not recipient or "@" not in recipient:
                job.skipped_invalid += 1
                db.add(
                    EmailSend(
                        client_id=None,
                        recipient_email=recipient or "(missing)",
                        subject=subject,
                        status="failed",
                        error_message="missing or invalid email address",
                    )
                )
                db.commit()
                continue

            if is_suppressed(db, recipient):
                job.skipped_suppressed += 1
                continue

            if _sent_today_count(db) >= DAILY_LIMIT:
                job.status = "stopped_daily_limit"
                return

            rendered_subject = merge.render_template(subject, context)
            rendered_body = merge.render_template(body, context)
            unsubscribe_url = (
                f"{UNSUBSCRIBE_BASE_URL}/api/unsubscribe"
                f"?token={make_unsubscribe_token(recipient)}"
            )

            client = get_client_by_email(db, recipient)
            try:
                gmail_client.send_email(
                    service, recipient, rendered_subject, rendered_body, unsubscribe_url
                )
                job.sent += 1
                db.add(
                    EmailSend(
                        client_id=client.id if client else None,
                        recipient_email=recipient,
                        subject=rendered_subject,
                        status="sent",
                    )
                )
            except Exception as e:
                job.failed += 1
                db.add(
                    EmailSend(
                        client_id=client.id if client else None,
                        recipient_email=recipient,
                        subject=rendered_subject,
                        status="failed",
                        error_message=str(e),
                    )
                )
            db.commit()

            await asyncio.sleep(random.uniform(THROTTLE_MIN_SECONDS, THROTTLE_MAX_SECONDS))

        if job.status == "running":
            job.status = "completed"
    except Exception as e:
        # Safety net: whatever else goes wrong (an expired/revoked token producing a
        # RefreshError rather than our own GmailNotAuthorized, a transient network or DB
        # error, etc.), the job must reach a terminal state instead of silently freezing
        # at "running" forever with no visible error.
        job.status = "failed"
        job.error = f"Send job failed unexpectedly: {e}"
    finally:
        db.close()
