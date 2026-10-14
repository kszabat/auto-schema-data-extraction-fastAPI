import uuid

SPEC_V1 = {
    "name": "invoice",
    "fields": [{"name": "invoice_number", "type": "str", "description": "Number"}],
}
SPEC_V2 = {
    "name": "invoice",
    "fields": [
        {"name": "invoice_number", "type": "str", "description": "Number"},
        {"name": "issue_date", "type": "date", "description": "Issue date"},
    ],
}
INVALID = {
    "name": "invoice",
    "fields": [{"name": "_id", "type": "str", "description": "x"}],
}


def create(client, headers, text="faktura"):
    return client.post("/schemas", json={"request_text": text}, headers=headers)


def create_v1(client, use_agent, headers) -> str:
    use_agent(SPEC_V1)
    return create(client, headers).json()["id"]


def test_endpoints_require_authentication(client):
    assert client.post("/schemas", json={"request_text": "x"}).status_code == 401
    assert client.get("/schemas").status_code == 401


def test_create_schema(client, use_agent, auth_headers):
    use_agent(SPEC_V1)
    response = create(client, auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "invoice"
    assert body["latest_version"]["version_number"] == 1
    fields = body["latest_version"]["definition"]["fields"]
    assert fields[0]["name"] == "invoice_number"


def test_request_text_is_validated(client, use_agent, auth_headers):
    use_agent(SPEC_V1)
    assert create(client, auth_headers, "").status_code == 422
    assert create(client, auth_headers, "x" * 5000).status_code == 422


def test_invalid_agent_output_returns_502_and_stores_nothing(
    client, use_agent, auth_headers
):
    use_agent(INVALID)
    assert create(client, auth_headers).status_code == 502
    assert client.get("/schemas", headers=auth_headers).json() == []


def test_refine_creates_new_version(client, use_agent, auth_headers):
    schema_id = create_v1(client, use_agent, auth_headers)

    use_agent(SPEC_V2)
    response = client.post(
        f"/schemas/{schema_id}/revisions",
        json={"feedback": "dodaj datę"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["version_number"] == 2
    assert response.json()["instruction"] == "dodaj datę"

    versions = client.get(f"/schemas/{schema_id}/versions", headers=auth_headers).json()
    assert [v["version_number"] for v in versions] == [1, 2]

    detail = client.get(f"/schemas/{schema_id}", headers=auth_headers).json()
    assert detail["latest_version"]["version_number"] == 2


def test_manual_edit_with_stale_version_conflicts(client, use_agent, auth_headers):
    schema_id = create_v1(client, use_agent, auth_headers)

    ok = client.put(
        f"/schemas/{schema_id}",
        json={"spec": SPEC_V2, "expected_version": 1},
        headers=auth_headers,
    )
    assert ok.status_code == 200
    assert ok.json()["version_number"] == 2

    stale = client.put(
        f"/schemas/{schema_id}",
        json={"spec": SPEC_V1, "expected_version": 1},
        headers=auth_headers,
    )
    assert stale.status_code == 409


def test_manual_edit_validates_spec(client, use_agent, auth_headers):
    schema_id = create_v1(client, use_agent, auth_headers)
    response = client.put(
        f"/schemas/{schema_id}", json={"spec": INVALID}, headers=auth_headers
    )
    assert response.status_code == 422


def test_rollback_creates_new_version(client, use_agent, auth_headers):
    schema_id = create_v1(client, use_agent, auth_headers)
    client.put(f"/schemas/{schema_id}", json={"spec": SPEC_V2}, headers=auth_headers)

    response = client.post(
        f"/schemas/{schema_id}/rollback", json={"version": 1}, headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["version_number"] == 3
    assert response.json()["definition"] == SPEC_V1 | {
        "fields": [{**SPEC_V1["fields"][0], "required": True}]
    }

    missing = client.post(
        f"/schemas/{schema_id}/rollback", json={"version": 99}, headers=auth_headers
    )
    assert missing.status_code == 404


def test_other_user_gets_404_everywhere(client, use_agent, auth_headers, other_headers):
    schema_id = create_v1(client, use_agent, auth_headers)
    base = f"/schemas/{schema_id}"
    requests = [
        ("get", base, None),
        ("get", f"{base}/versions", None),
        ("post", f"{base}/revisions", {"feedback": "x"}),
        ("put", base, {"spec": SPEC_V2}),
        ("post", f"{base}/rollback", {"version": 1}),
    ]
    for method, url, body in requests:
        response = client.request(method, url, json=body, headers=other_headers)
        assert response.status_code == 404, f"{method.upper()} {url}"

    assert client.get("/schemas", headers=other_headers).json() == []


def test_unknown_and_malformed_ids(client, auth_headers):
    unknown = client.get(f"/schemas/{uuid.uuid4()}", headers=auth_headers)
    assert unknown.status_code == 404
    assert client.get("/schemas/not-a-uuid", headers=auth_headers).status_code == 422

def test_debug_auth(client, auth_headers, db):
    from schema_extractor.db.models import User
    from schema_extractor.security import decode_access_token

    print("headers:", auth_headers)
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    user_id = decode_access_token(token)
    print("user in session:", db.get(User, user_id))

    response = client.get("/auth/me", headers=auth_headers)
    print("me:", response.status_code, response.text)