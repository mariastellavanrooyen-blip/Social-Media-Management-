from app.security import make_unsubscribe_token, read_unsubscribe_token


def test_add_and_list_suppression(client):
    res = client.post("/api/suppression", json={"email": "Bounced@Example.com", "reason": "bounced"})
    assert res.status_code == 201
    assert res.json()["email"] == "bounced@example.com"

    res = client.get("/api/suppression")
    assert len(res.json()) == 1


def test_add_suppression_is_idempotent(client):
    client.post("/api/suppression", json={"email": "a@example.com"})
    client.post("/api/suppression", json={"email": "a@example.com"})
    res = client.get("/api/suppression")
    assert len(res.json()) == 1


def test_delete_suppression(client):
    entry = client.post("/api/suppression", json={"email": "a@example.com"}).json()
    res = client.delete(f"/api/suppression/{entry['id']}")
    assert res.status_code == 204
    assert client.get("/api/suppression").json() == []


def test_delete_suppression_not_found(client):
    res = client.delete("/api/suppression/999")
    assert res.status_code == 404


def test_unsubscribe_token_roundtrip():
    token = make_unsubscribe_token("Someone@Example.com")
    assert read_unsubscribe_token(token) == "someone@example.com"


def test_unsubscribe_token_rejects_tampering():
    token = make_unsubscribe_token("someone@example.com")
    assert read_unsubscribe_token(token + "x") is None


def test_unsubscribe_endpoint_adds_to_suppression_list(client):
    token = make_unsubscribe_token("clicked@example.com")
    res = client.get(f"/api/unsubscribe?token={token}")
    assert res.status_code == 200
    assert "clicked@example.com" in res.text

    entries = client.get("/api/suppression").json()
    assert any(e["email"] == "clicked@example.com" for e in entries)


def test_unsubscribe_endpoint_rejects_bad_token(client):
    res = client.get("/api/unsubscribe?token=not-a-real-token")
    assert res.status_code == 400
