"""Versioned immutable financial inputs and safe allowlisted snapshot restoration."""

import hashlib
import json
from dataclasses import asdict, fields, is_dataclass, replace
from datetime import date
from decimal import Decimal

from backend.revenue.models import Assumption

from . import models


def _encode(obj):
    if is_dataclass(obj):
        return {
            "type": type(obj).__name__,
            "fields": {f.name: _encode(getattr(obj, f.name)) for f in fields(obj)},
        }
    if isinstance(obj, Decimal):
        return {"decimal": str(obj)}
    if type(obj) is date:
        return {"date": obj.isoformat()}
    if isinstance(obj, tuple):
        return {"tuple": [_encode(x) for x in obj]}
    if obj is None or isinstance(obj, (str, int, bool, float)):
        return obj
    raise TypeError("Unsupported snapshot type")


def freeze_inputs(inputs):
    if not isinstance(inputs, models.FinancialInputs):
        raise TypeError("FinancialInputs required")
    return json.dumps(
        {"schema_version": 1, "inputs": _encode(inputs)},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def snapshot_id(inputs):
    return hashlib.sha256(freeze_inputs(inputs).encode()).hexdigest()


def restore_inputs(snapshot):
    payload = json.loads(snapshot)
    if (
        set(payload) != {"schema_version", "inputs"}
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
    ):
        raise ValueError("Unsupported financial snapshot schema")
    allowed = {
        name: cls
        for name, cls in vars(models).items()
        if isinstance(cls, type) and is_dataclass(cls)
    }
    allowed["Assumption"] = Assumption

    def decode(value):
        if not isinstance(value, dict):
            return value
        if set(value) == {"decimal"}:
            result = Decimal(value["decimal"])
            if not result.is_finite():
                raise ValueError("Nonfinite saved amount")
            return result
        if set(value) == {"date"}:
            return date.fromisoformat(value["date"])
        if set(value) == {"tuple"}:
            return tuple(decode(x) for x in value["tuple"])
        if set(value) == {"type", "fields"} and value["type"] in allowed:
            return allowed[value["type"]](
                **{k: decode(v) for k, v in value["fields"].items()}
            )
        raise ValueError("Unsupported snapshot record")

    result = decode(payload["inputs"])
    if not isinstance(result, models.FinancialInputs):
        raise TypeError("Snapshot is not FinancialInputs")
    return result


def revise_inputs(inputs, *, actor, reason, expected_snapshot_id, **changes):
    if (
        expected_snapshot_id != snapshot_id(inputs)
        or not actor.strip()
        or not reason.strip()
    ):
        raise ValueError("Matching revision, actor and rationale required")
    if set(changes) - {"assumptions", "capital", "operations"}:
        raise ValueError("Only explicit financial inputs can be revised")
    return replace(
        inputs,
        **changes,
        revision=inputs.revision + 1,
        parent_snapshot_id=snapshot_id(inputs),
        actor=actor,
        change_reason=reason,
    )


def save_assessment(inputs, result, path):
    from pathlib import Path

    if snapshot_id(inputs) != result.snapshot_id:
        raise ValueError("Stale financial result")
    content = json.dumps(
        {
            "schema_version": 1,
            "inputs": json.loads(freeze_inputs(inputs)),
            "result": asdict(result),
        },
        default=str,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    )
    destination = Path(path)
    with destination.open("x", encoding="utf8") as file:
        file.write(content)
    return destination
