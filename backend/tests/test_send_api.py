import io
import time

CSV_CONTENT = b"Full Name,Email Address\nAda Lovelace,ada@example.com\n"


def test_send_start_unknown_upload_returns_404(client):
    res = client.post(
        "/api/send/start",
        json={"upload_id": "nope", "mapping": {"email": "Email Address"}, "subject": "s", "body": "b"},
    )
    assert res.status_code == 404


def test_send_start_requires_email_mapping(client):
    upload_id = client.post(
        "/api/upload", files={"file": ("c.csv", io.BytesIO(CSV_CONTENT), "text/csv")}
    ).json()["upload_id"]
    res = client.post(
        "/api/send/start",
        json={"upload_id": upload_id, "mapping": {"name": "Full Name"}, "subject": "s", "body": "b"},
    )
    assert res.status_code == 400


def test_send_job_fails_cleanly_without_gmail_connection(client):
    upload_id = client.post(
        "/api/upload", files={"file": ("c.csv", io.BytesIO(CSV_CONTENT), "text/csv")}
    ).json()["upload_id"]
    start = client.post(
        "/api/send/start",
        json={
            "upload_id": upload_id,
            "mapping": {"name": "Full Name", "email": "Email Address"},
            "subject": "hi {{name}}",
            "body": "hello {{name}}",
        },
    )
    assert start.status_code == 200
    job_id = start.json()["job_id"]

    for _ in range(20):
        job = client.get(f"/api/send/jobs/{job_id}").json()
        if job["status"] != "running":
            break
        time.sleep(0.1)

    assert job["status"] == "failed"
    assert "not connected" in job["error"].lower()


def test_get_send_job_unknown_id_returns_404(client):
    res = client.get("/api/send/jobs/does-not-exist")
    assert res.status_code == 404
