def make_client(client, **overrides):
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "company": "Acme",
        "phone": "555-1234",
        "status": "lead",
        "notes": "Met at conference",
    }
    payload.update(overrides)
    return client.post("/api/clients", json=payload)


def test_create_client(client):
    res = make_client(client)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Jane Doe"
    assert body["status"] == "lead"
    assert "id" in body
    assert "created_at" in body


def test_create_client_duplicate_email_rejected(client):
    make_client(client)
    res = make_client(client, name="Someone Else")
    assert res.status_code == 409


def test_create_client_invalid_email_rejected(client):
    res = make_client(client, email="not-an-email")
    assert res.status_code == 422


def test_list_clients(client):
    make_client(client, email="a@example.com", name="Alice")
    make_client(client, email="b@example.com", name="Bob")
    res = client.get("/api/clients")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_clients_filter_by_status(client):
    make_client(client, email="a@example.com", name="Alice", status="lead")
    make_client(client, email="b@example.com", name="Bob", status="active")
    res = client.get("/api/clients", params={"status": "active"})
    body = res.json()
    assert len(body) == 1
    assert body[0]["name"] == "Bob"


def test_list_clients_search(client):
    make_client(client, email="a@example.com", name="Alice", company="Widgets Inc")
    make_client(client, email="b@example.com", name="Bob", company="Gizmos LLC")
    res = client.get("/api/clients", params={"search": "widgets"})
    body = res.json()
    assert len(body) == 1
    assert body[0]["name"] == "Alice"


def test_get_client(client):
    created = make_client(client).json()
    res = client.get(f"/api/clients/{created['id']}")
    assert res.status_code == 200
    assert res.json()["email"] == "jane@example.com"


def test_get_client_not_found(client):
    res = client.get("/api/clients/999")
    assert res.status_code == 404


def test_update_client(client):
    created = make_client(client).json()
    res = client.put(
        f"/api/clients/{created['id']}",
        json={"status": "contacted", "last_contact_date": "2026-07-01"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "contacted"
    assert body["last_contact_date"] == "2026-07-01"
    assert body["name"] == "Jane Doe"  # untouched fields preserved


def test_update_client_duplicate_email_rejected(client):
    make_client(client, email="a@example.com", name="Alice")
    bob = make_client(client, email="b@example.com", name="Bob").json()
    res = client.put(f"/api/clients/{bob['id']}", json={"email": "a@example.com"})
    assert res.status_code == 409


def test_update_client_not_found(client):
    res = client.put("/api/clients/999", json={"status": "active"})
    assert res.status_code == 404


def test_delete_client(client):
    created = make_client(client).json()
    res = client.delete(f"/api/clients/{created['id']}")
    assert res.status_code == 204
    res = client.get(f"/api/clients/{created['id']}")
    assert res.status_code == 404


def test_delete_client_not_found(client):
    res = client.delete("/api/clients/999")
    assert res.status_code == 404
