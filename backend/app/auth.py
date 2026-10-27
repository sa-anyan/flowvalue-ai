"""Validate Supabase bearer tokens server-side; never trust a client user ID."""

import httpx
from fastapi import HTTPException, Request
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    require_auth: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def public_config():
    c = AuthSettings()
    return {
        "supabase_url": c.supabase_url,
        "supabase_publishable_key": c.supabase_publishable_key,
        "require_auth": c.require_auth,
    }


async def authenticated_user(request: Request):
    c = AuthSettings()
    token = request.headers.get("authorization", "")
    if not token.startswith("Bearer ") or not token[7:].strip():
        raise HTTPException(401, "Sign in to access saved projects and protected APIs")
    if not c.supabase_url or not c.supabase_publishable_key:
        raise HTTPException(503, "Supabase is not configured")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                c.supabase_url.rstrip("/") + "/auth/v1/user",
                headers={"apikey": c.supabase_publishable_key, "Authorization": token},
            )
        if response.status_code >= 500 or response.status_code == 429:
            raise HTTPException(503, "Authentication provider unavailable; retry later")
        if response.status_code != 200:
            raise HTTPException(401, "Session expired or invalid; sign in again")
        user = response.json()
        if not user.get("id"):
            raise HTTPException(401, "Invalid session")
        return user
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Authentication provider unavailable") from exc


async def project_rest(request: Request, method: str, path: str, *, body=None):
    c = AuthSettings()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                c.supabase_url.rstrip("/") + "/rest/v1/" + path,
                headers={
                    "apikey": c.supabase_publishable_key,
                    "Authorization": request.headers.get("authorization", ""),
                    "Prefer": "return=representation",
                },
                json=body,
            )
        if response.status_code >= 400:
            if response.status_code == 401:
                raise HTTPException(401, "Session expired or invalid; sign in again")
            if response.status_code == 409 or "Revision conflict" in response.text:
                raise HTTPException(409, "Revision conflict: refresh project history or save as a new project")
            raise HTTPException(
                503, "Project storage request failed; check schema and account access"
            )
        return response.json() if response.content else None
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Project storage unavailable") from exc
