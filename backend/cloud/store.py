"""Caller-token PostgREST persistence. Every operation is protected by Supabase RLS."""

import base64
import copy
import hashlib
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

    def version(self, key, name):
        if not name.strip() or len(name) > 120:
            raise ValueError("Name the version (up to120 characters)")
        state = self.get(key)
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
        key = hashlib.sha256(dump(context).encode()).hexdigest()
        rows = self.request("cache", filters={"key": "eq." + key, "select": "value"})
        if rows:
            return rows[0]["value"], True
        value = compute()
        self.request(
            "cache", "POST", data={"owner_id": self.user_id, "key": key, "value": value}
        )
        return value, False

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
