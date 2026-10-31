"""Verified sessions and context-preserving background jobs; no shared tenant store."""

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar, copy_context
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from backend.revenue.advisor import NoRedirects

from .store import CloudStore

workspace = ContextVar("flowvalue_workspace", default=None)


class WorkspaceProxy:
    def __getattr__(self, name):
        current = workspace.get()
        if current is None:
            raise PermissionError("Authenticated workspace required")
        return getattr(current, name)


class ContextExecutor(ThreadPoolExecutor):
    def submit(self, fn, /, *args, **kwargs):
        context = copy_context()
        return super().submit(context.run, fn, *args, **kwargs)


def verified_workspace(token):
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_PUBLISHABLE_KEY"]
    request = Request(
        url + "/auth/v1/user",
        headers={"apikey": key, "Authorization": "Bearer " + token},
    )
    try:
        with build_opener(NoRedirects()).open(request, timeout=10) as response:
            user = json.loads(response.read(131072))
        user_id = str(uuid.UUID(user["id"]))
        if user.get("is_anonymous"):
            raise ValueError("Anonymous account not accepted")
    except (HTTPError, URLError, KeyError, ValueError) as exc:
        raise PermissionError("Sign in required") from exc
    return CloudStore(url, key, token, user_id)
