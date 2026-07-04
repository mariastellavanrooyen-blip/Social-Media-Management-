def test_get_template_defaults_to_empty(client):
    res = client.get("/api/template")
    assert res.status_code == 200
    body = res.json()
    assert body["subject"] == ""
    assert body["body"] == ""


def test_save_and_reload_template(client):
    res = client.put(
        "/api/template",
        json={"subject": "Hi {{name}}", "body": "Hello {{name}} from {{company}}"},
    )
    assert res.status_code == 200
    assert res.json()["subject"] == "Hi {{name}}"

    res = client.get("/api/template")
    body = res.json()
    assert body["subject"] == "Hi {{name}}"
    assert body["body"] == "Hello {{name}} from {{company}}"


def test_save_template_overwrites_single_row(client):
    client.put("/api/template", json={"subject": "First", "body": "a"})
    client.put("/api/template", json={"subject": "Second", "body": "b"})
    res = client.get("/api/template")
    assert res.json()["subject"] == "Second"
