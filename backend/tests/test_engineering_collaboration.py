"""API ownership checks complement the real transactional RLS SQL fixture."""

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_engineering_analyst import body, project

from app.auth import authenticated_user
from app.main import app

OWNER = "00000000-0000-4000-8000-00000000b001"
PEER = "00000000-0000-4000-8000-00000000b002"
VERSION = "00000000-0000-4000-8000-00000000d001"
client = TestClient(app)


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    state = {"actor": OWNER, "events": [], "access": [], "writes": []}
    p = project()
    state["project"] = p
    row = {
        "id": VERSION,
        "project_id": str(uuid4()),
        "user_id": OWNER,
        "name": "Synthetic review",
        "revision": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "payload": {"project": p.model_dump(mode="json")},
    }

    async def rest(request, method, path, *, body=None):
        table = path.split("?")[0]
        q = parse_qs(urlsplit("https://test.invalid/" + path).query)
        if table == "project_versions":
            return [row]
        if table == "engineering_review_events" and method == "GET":
            result = state["events"]
            for field in ("id", "unit_id", "action"):
                if field in q:
                    value = q[field][0].removeprefix("eq.")
                    result = [e for e in result if e[field] == value]
            return result
        if table == "engineering_review_access" and method == "GET":
            return state["access"]
        state["writes"].append((method, table, body))
        record = {
            "id": str(uuid4()),
            "created_at": datetime.now(UTC).isoformat(),
            **body,
        }
        if method == "POST":
            state[
                "events" if table == "engineering_review_events" else "access"
            ].append(record)
        return [record]

    monkeypatch.setattr("app.engineering.collaboration.project_rest", rest)
    monkeypatch.setattr("app.main.project_rest", rest)

    async def auth(request=None):
        return {"id": state["actor"]}

    monkeypatch.setattr("app.main.authenticated_user", auth)
    app.dependency_overrides[authenticated_user] = auth
    yield state
    app.dependency_overrides.clear()


def test_only_owner_can_share_and_grants_require_explicit_scope_confirmation(storage):
    url = f"/api/engineering/reviews/{VERSION}/access"
    assert client.post(url, json={"reviewer_id": PEER}).status_code == 422
    storage["actor"] = PEER
    assert (
        client.post(
            url, json={"reviewer_id": OWNER, "confirm_snapshot_access": True}
        ).status_code
        == 403
    )
    storage["actor"] = OWNER
    assert (
        client.post(
            url, json={"reviewer_id": OWNER, "confirm_snapshot_access": True}
        ).status_code
        == 422
    )
    result = client.post(
        url, json={"reviewer_id": PEER, "confirm_snapshot_access": True}
    )
    assert result.status_code == 200
    assert storage["writes"][-1][2]["owner_id"] == OWNER
    assert storage["writes"][-1][2]["reviewer_id"] == PEER


def test_events_use_authenticated_identity_and_peer_cannot_resolve(storage):
    url = f"/api/engineering/reviews/{VERSION}/events"
    unit = storage["project"].study.engineering_cases[0].unit_id
    storage["actor"] = PEER
    result = client.post(
        url,
        json={
            "unit_id": unit,
            "action": "challenge",
            "message": "Check impurity and cleaning basis",
        },
    )
    assert result.status_code == 200
    challenge = result.json()[0]
    assert challenge["author_id"] == PEER
    assert (
        client.post(
            url,
            json={
                "unit_id": unit,
                "action": "resolve",
                "message": "Not allowed",
                "parent_id": challenge["id"],
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            url,
            json={
                "unit_id": unit,
                "action": "comment",
                "message": "Cannot forge author",
                "author_id": OWNER,
            },
        ).status_code
        == 422
    )
    storage["actor"] = OWNER
    assert (
        client.post(
            url,
            json={
                "unit_id": "V1",
                "action": "resolve",
                "message": "Wrong unit",
                "parent_id": challenge["id"],
            },
        ).status_code
        == 422
    )
    resolved = client.post(
        url,
        json={
            "unit_id": unit,
            "action": "resolve",
            "message": "Documented review of synthetic service conditions",
            "parent_id": challenge["id"],
        },
    )
    assert resolved.status_code == 200
    snap = client.get(f"/api/engineering/reviews/{VERSION}").json()
    assert snap["is_owner"] and not snap["open_challenges"]
    assert len(snap["events"]) == 2


def test_open_cloud_challenge_blocks_owner_baseline(storage):
    unit = storage["project"].study.engineering_cases[0].unit_id
    challenge = {
        "id": str(uuid4()),
        "unit_id": unit,
        "action": "challenge",
        "parent_id": None,
    }
    storage["events"].append(challenge)
    request = body(storage["project"]) | {
        "reviewer": "R",
        "basis": "Synthetic test",
        "confirm": True,
        "review_version_id": VERSION,
    }
    assert (
        client.post(
            "/api/engineering/apply-baseline",
            json=request,
            headers={"Authorization": "Bearer synthetic-test-token"},
        ).status_code
        == 409
    )
    storage["events"].append(
        {
            "id": str(uuid4()),
            "unit_id": unit,
            "action": "resolve",
            "parent_id": challenge["id"],
        }
    )
    assert (
        client.post(
            "/api/engineering/apply-baseline",
            json=request,
            headers={"Authorization": "Bearer synthetic-test-token"},
        ).status_code
        == 200
    )
    storage["actor"] = PEER
    assert (
        client.post(
            "/api/engineering/apply-baseline",
            json=request,
            headers={"Authorization": "Bearer synthetic-test-token"},
        ).status_code
        == 403
    )


def test_revocation_is_owner_only_and_uses_matching_snapshot(storage):
    url = f"/api/engineering/reviews/{VERSION}/revoke"
    storage["actor"] = PEER
    assert client.post(url, json={"access_id": str(uuid4())}).status_code == 403
    storage["actor"] = OWNER
    result = client.post(url, json={"access_id": str(uuid4())})
    assert result.status_code == 200 and result.json()["revoked"]
    assert list(storage["writes"][-1][2]) == ["revoked_at"]
