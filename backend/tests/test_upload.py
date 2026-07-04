import io

CSV_CONTENT = (
    b"Full Name,Email Address,Org\n"
    b"Ada Lovelace,ada@example.com,Analytical Engines\n"
    b"Grace Hopper,grace@example.com,COBOL Inc\n"
)


def upload_csv(client, content=CSV_CONTENT, filename="contacts.csv"):
    return client.post(
        "/api/upload",
        files={"file": (filename, io.BytesIO(content), "text/csv")},
    )


def test_upload_csv_returns_columns_and_preview(client):
    res = upload_csv(client)
    assert res.status_code == 200
    body = res.json()
    assert body["row_count"] == 2
    assert body["columns"] == ["Full Name", "Email Address", "Org"]
    assert len(body["preview_rows"]) == 2
    assert "upload_id" in body


def test_upload_rejects_unsupported_extension(client):
    res = upload_csv(client, filename="contacts.txt")
    assert res.status_code == 400


def test_upload_rejects_empty_file(client):
    res = upload_csv(client, content=b"Full Name,Email Address,Org\n")
    assert res.status_code == 400


def test_preview_merge_renders_samples(client):
    upload_id = upload_csv(client).json()["upload_id"]
    res = client.post(
        f"/api/upload/{upload_id}/preview",
        json={
            "mapping": {"name": "Full Name", "email": "Email Address", "company": "Org"},
            "subject": "Hi {{name}}",
            "body": "{{name}} works at {{company}}. Also: {{typo}}",
            "sample_size": 2,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total_rows"] == 2
    assert body["unknown_fields"] == ["typo"]
    assert body["items"][0]["recipient_email"] == "ada@example.com"
    assert body["items"][0]["subject"] == "Hi Ada Lovelace"
    assert "Analytical Engines" in body["items"][0]["body"]


def test_preview_merge_flags_suppressed_recipients(client):
    client.post("/api/suppression", json={"email": "grace@example.com"})
    upload_id = upload_csv(client).json()["upload_id"]
    res = client.post(
        f"/api/upload/{upload_id}/preview",
        json={
            "mapping": {"name": "Full Name", "email": "Email Address"},
            "subject": "Hi {{name}}",
            "body": "body",
            "sample_size": 2,
        },
    )
    items = {item["recipient_email"]: item for item in res.json()["items"]}
    assert items["grace@example.com"]["is_suppressed"] is True
    assert items["ada@example.com"]["is_suppressed"] is False


def test_preview_merge_requires_email_mapping(client):
    upload_id = upload_csv(client).json()["upload_id"]
    res = client.post(
        f"/api/upload/{upload_id}/preview",
        json={"mapping": {"name": "Full Name"}, "subject": "s", "body": "b"},
    )
    assert res.status_code == 400


def test_preview_merge_unknown_upload_id(client):
    res = client.post(
        "/api/upload/does-not-exist/preview",
        json={"mapping": {"email": "Email Address"}, "subject": "s", "body": "b"},
    )
    assert res.status_code == 404
