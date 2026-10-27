"""Auth boundary and storage failures without real credentials or network calls."""

import asyncio

import httpx
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.auth import authenticated_user, project_rest


def request(token="test-access-token"):
    return Request(
        {"type": "http", "headers": [(b"authorization", f"Bearer {token}".encode())]}
    )


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-test-key")
    original = httpx.AsyncClient

    def install(status, payload):
        def handle(req):
            assert req.headers["authorization"] == "Bearer test-access-token"
            assert req.headers["apikey"] == "public-test-key"
            return httpx.Response(status, json=payload)

        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda **kw: original(**kw, transport=httpx.MockTransport(handle)),
        )

    return install


def test_auth_uses_verified_provider_identity(provider):
    provider(200, {"id": "verified-owner"})
    assert (asyncio.run(authenticated_user(request())))["id"] == "verified-owner"


@pytest.mark.parametrize("status,expected", [(401, 401), (500, 503), (429, 503)])
def test_auth_distinguishes_bad_session_from_outage(provider, status, expected):
    provider(status, {"message": "private provider details"})
    with pytest.raises(HTTPException) as error:
        asyncio.run(authenticated_user(request()))
    assert error.value.status_code == expected
    assert "private provider details" not in error.value.detail


@pytest.mark.parametrize(
    "status,payload,expected",
    [
        (401, {}, 401),
        (400, {"message": "Revision conflict: stale"}, 409),
        (500, {"message": "private database details"}, 503),
    ],
)
def test_storage_preserves_actionable_errors(provider, status, payload, expected):
    provider(status, payload)
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            project_rest(request(), "POST", "rpc/save_project_version", body={})
        )
    assert error.value.status_code == expected
    assert "private database details" not in error.value.detail
