"""Caller-token PostgREST persistence. Every operation is protected by Supabase RLS."""

import base64
import copy
import hashlib
import os
import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from backend.orchestration.store import dump
from backend.revenue.advisor import NoRedirects


class CloudStore:
    def __init__(self, url, key, token, user_id):
        if not url.startswith("https://") or not token or not user_id:
            raise ValueError("Authenticated cloud storage required")
        self.url = url.rstrip("/") + "/rest/v1/"
        self.key = key
        self.token = token
        self.user_id = user_id

    def request(self, table, method="GET", filters=None, data=None):
        query = {
            **({"owner_id": "eq." + self.user_id} if method != "POST" else {}),
            **(filters or {}),
        }
        request = Request(
            self.url + "flowvalue_rebuild_" + table + "?" + urlencode(query),
            data=None if data is None else dump(data).encode(),
            method=method,
            headers={
                "apikey": self.key,
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )
        try:
            with build_opener(NoRedirects()).open(request, timeout=30) as response:
                raw = response.read(16 * 1024**2 + 1)
            if len(raw) > 16 * 1024**2:
                raise ValueError("Saved workspace response exceeds limit")
            return json.loads(raw or "[]")
        except (HTTPError, URLError) as exc:
            raise ValueError(
                "Saved workspace request failed; reload or sign in again"
            ) from exc

    def create(self, state, workbook):
        state = copy.deepcopy(dict(state, id=uuid.uuid4().hex, revision=0))
        self.request(
            "assessments",
            "POST",
            data={
                "owner_id": self.user_id,
                "id": state["id"],
                "revision": 0,
                "state": state,
                "workbook": base64.b64encode(workbook).decode(),
            },
        )
        return state

    def get(self, key):
        rows = self.request(
            "assessments", filters={"id": "eq." + key, "select": "state"}
        )
        if len(rows) != 1:
            raise KeyError("Assessment not found")
        return rows[0]["state"]

    def workbook(self, key):
        rows = self.request(
            "assessments", filters={"id": "eq." + key, "select": "workbook"}
        )
        if len(rows) != 1:
            raise KeyError("Assessment not found")
        return base64.b64decode(rows[0]["workbook"], validate=True)

    def put(self, state, expected):
        state = copy.deepcopy(dict(state, revision=expected + 1))
        rows = self.request(
            "assessments",
            "PATCH",
            {"id": "eq." + state["id"], "revision": "eq." + str(expected)},
            {"state": state, "revision": expected + 1},
        )
        if len(rows) != 1:
            raise ValueError("Assessment changed; reload before editing")
        return state

    def version(self, key, name, *, snapshot=None):
        if not name.strip() or len(name) > 120:
            raise ValueError("Name the version (up to120 characters)")
        state = self.get(key)  # authenticated, owner-scoped existence check
        if snapshot is not None:
            if snapshot.get("id") != key:
                raise ValueError("Snapshot must belong to this assessment")
            state = copy.deepcopy(snapshot)
        if state.get("running"):
            raise ValueError("Wait for calculation completion")
        version = uuid.uuid4().hex
        self.request(
            "versions",
            "POST",
            data={
                "owner_id": self.user_id,
                "id": version,
                "assessment_id": key,
                "name": name,
                "state": state,
            },
        )
        return version

    def versions(self, key):
        return self.request(
            "versions",
            filters={
                "assessment_id": "eq." + key,
                "select": "id,name",
                "order": "created_at.desc",
            },
        )

    def all_versions(self):
        return self.request(
            "versions",
            filters={"select": "id,name,assessment_id", "order": "created_at.desc"},
        )

    def load(self, version):
        rows = self.request(
            "versions", filters={"id": "eq." + version, "select": "state,assessment_id"}
        )
        if len(rows) != 1:
            raise KeyError("Version not found")
        row = rows[0]
        state = row["state"]
        state.update(parent_version=version, running=False)
        return self.create(state, self.workbook(row["assessment_id"]))

    def cached(self, context, compute):
        # Same rule as the local store: the model identifier is in the key.
        model = os.environ.get("OPENAI_MODEL", "").strip()
        key = hashlib.sha256(
            dump({"context": context, "ai_model": model}).encode()
        ).hexdigest()
        rows = self.request("cache", filters={"key": "eq." + key, "select": "value"})
        if rows:
            from backend.orchestration.ai_audit import record

            record("cache", model=model or None, context=context, response=rows[0]["value"], cached=True)
            return rows[0]["value"], True
        value = compute()
        self.request(
            "cache", "POST", data={"owner_id": self.user_id, "key": key, "value": value}
        )
        return value, False

    def states_by_source(self, source_sha256):
        rows = self.request(
            "assessments",
            filters={
                "state->>source_sha256": "eq." + source_sha256,
                "select": "state",
                "order": "created_at.asc",
                "limit": "100",
            },
        )
        return [r["state"] for r in rows]

    def related_states(self, parent):
        rows = self.request(
            "assessments",
            filters={
                "state->>parent_assessment": "eq." + parent,
                "select": "state",
                "limit": "100",
            },
        )
        return [r["state"] for r in rows]

    def clear_history(self):
        """Atomically remove this signed-in owner's studies, versions and AI cache.

        The database RPC runs as the caller with RLS. Its owner check and
        running-study guard execute in one transaction; other users are untouched.
        No service-role credentials are used.
        """
        request = Request(
            self.url + "rpc/flowvalue_rebuild_reset_history",
            data=b"{}",
            method="POST",
            headers={
                "apikey": self.key,
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with build_opener(NoRedirects()).open(request, timeout=30) as response:
                raw = response.read(4096 + 1)
            if len(raw) > 4096:
                raise ValueError("Hosted reset response exceeded size limit")
            counts = json.loads(raw)
            if not isinstance(counts, dict) or any(
                not isinstance(counts.get(name), int)
                or isinstance(counts.get(name), bool)
                or counts[name] < 0
                for name in ("assessments", "versions", "ai_cache")
            ):
                raise ValueError("Hosted reset returned an invalid response")
            return {name: counts[name] for name in ("assessments", "versions", "ai_cache")}
        except HTTPError as exc:
            if exc.code in {400, 409}:
                raise ValueError(
                    "A calculation may still be running, or hosted reset is not configured. "
                    "Check your project and try again."
                ) from exc
            raise ValueError("Hosted reset failed; sign in again or retry.") from exc
        except (URLError, json.JSONDecodeError) as exc:
            raise ValueError("Hosted reset failed; no changes were confirmed.") from exc
