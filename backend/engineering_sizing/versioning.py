"""Deterministic identity of loaded engineering code, not Git or on-disk text.

Only owned engineering/unit modules are followed transitively. External callable
boundaries are identified but this is not an environment/SBOM attestation.
Only immutable code-object digests are memoized; live globals are read afresh.
No result, source-file, timestamp, path or user-input cache is used.
"""

import dataclasses
import functools
import hashlib
import inspect
import json
import types
from collections.abc import Mapping
from types import MappingProxyType

METHOD_VERSIONS = MappingProxyType(
    {
        name: "1.0.0"
        for name in (
            "ion_exchange_capacity",
            "vaporizer_area",
            "gas_compression",
            "phase_change_duty",
            "evaporated_water",
            "ion_exchange_ebct",
            "vessel_hold_up",
            "pump_duty",
            "exchanger_area",
            "filter_area",
            "gas_volume",
            "dryer_chamber",
            "vessel_mass",
            "vessel_productivity",
            "mixing_power",
        )
    }
)
SCHEME = "flowvalue-loaded-engineering-v1"
OWNED = ("backend.engineering_sizing", "backend.equipment_costing.unit_conversion")
NATIVE_DEPENDENCIES = {
    "mixing_power": ("vessel_hold_up",),
    "dryer_chamber": ("dryer_chamber", "gas_volume"),
    "vaporizer_area": ("vaporizer_area", "phase_change_duty"),
    "exchanger_area": ("exchanger_area", "phase_change_duty"),
}


def _qualified(value):
    return (
        (getattr(value, "__module__", None) or "<anonymous>") + "." + value.__qualname__
    )


def _code(code):
    # Debug positions/filenames are deliberately excluded; nested code and
    # executable literals remain part of the identity.
    return {
        "bytecode": code.co_code.hex(),
        "constants": code.co_consts,
        "names": code.co_names,
        "locals": code.co_varnames,
        "freevars": code.co_freevars,
        "cellvars": code.co_cellvars,
        "arguments": (
            code.co_argcount,
            code.co_posonlyargcount,
            code.co_kwonlyargcount,
        ),
        "flags": code.co_flags,
    }


def _referenced_names(code):
    names = set(code.co_names)
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            names.update(_referenced_names(value))
    return names


@functools.lru_cache(maxsize=512)
def _code_digest(code):
    encoded = _Encoder(None).encode(_code(code))
    return hashlib.sha256(
        json.dumps(
            encoded, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


class _Encoder:
    def __init__(self, method_id):
        self.method_id = method_id
        self.stack = set()
        self.memo = {}  # per-snapshot component digests, never calculation data
        self.keepalive = []  # prevent temporary-object ID reuse within a snapshot

    def encode(self, value):
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            return {"float": value.hex()}
        if isinstance(value, bytes):
            return {"bytes": value.hex()}
        if isinstance(value, complex):
            return {"complex": (value.real.hex(), value.imag.hex())}
        if value is Ellipsis:
            return {"literal": "Ellipsis"}
        marker = id(value)  # cycle detection only: never serialized
        if marker in self.memo:
            return self.memo[marker]
        if marker in self.stack:
            return {"cycle": type(value).__name__}
        self.stack.add(marker)
        self.keepalive.append(value)
        try:
            component = self._compound(value)
            encoded = json.dumps(
                component, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
            result = {
                "component_type": type(value).__name__,
                "sha256": hashlib.sha256(encoded).hexdigest(),
            }
            self.memo[marker] = result
            return result
        finally:
            self.stack.remove(marker)

    def _compound(self, value):
        if isinstance(value, functools.partial):
            return {"partial": self.encode((value.func, value.args, value.keywords))}
        if isinstance(value, types.CodeType):
            return self.encode(_code(value))
        if isinstance(value, Mapping):
            keys = sorted(
                value, key=lambda k: json.dumps(self.encode(k), sort_keys=True)
            )
            return {"mapping": [(self.encode(k), self.encode(value[k])) for k in keys]}
        if isinstance(value, (tuple, list)):
            return [self.encode(x) for x in value]
        if isinstance(value, (set, frozenset)):
            return {
                "set": sorted(
                    (self.encode(x) for x in value),
                    key=lambda x: json.dumps(x, sort_keys=True),
                )
            }
        if inspect.isfunction(value):
            result = {
                "function": _qualified(value),
                "code_sha256": _code_digest(value.__code__),
                "defaults": self.encode(value.__defaults__),
                "kwdefaults": self.encode(value.__kwdefaults__),
            }
            # Closure *values* can be project inputs (e.g. a conversion context).
            # Their definitions are in nested code; data belongs in provenance.
            if (value.__module__ or "").startswith(
                OWNED
            ) and value.__module__ != __name__:
                referenced = {}
                names = _referenced_names(value.__code__)
                for name in sorted(names):
                    if name not in value.__globals__ or name in {
                        "__file__",
                        "__cached__",
                        "__builtins__",
                    }:
                        continue
                    item = value.__globals__[name]
                    if name == "METHODS" and value.__module__ in {
                        "backend.engineering_sizing.registry",
                        "backend.engineering_sizing.adapter",
                    }:
                        ids = NATIVE_DEPENDENCIES.get(self.method_id, (self.method_id,))
                        item = {key: item.get(key) for key in ids}
                    if inspect.ismodule(item) and not item.__name__.startswith(OWNED):
                        referenced[name] = {
                            "module": item.__name__,
                            "referenced_attributes": self.encode(
                                {
                                    key: getattr(item, key)
                                    for key in sorted(names)
                                    if hasattr(item, key)
                                }
                            ),
                        }
                    else:
                        referenced[name] = self.encode(item)
                result["referenced_globals"] = referenced
            return result
        if inspect.ismodule(value):
            if value.__name__.startswith(OWNED) and value.__name__ != __name__:
                return {
                    "module": value.__name__,
                    "functions": self.encode(
                        {
                            k: v
                            for k, v in vars(value).items()
                            if inspect.isfunction(v) and v.__module__ == value.__name__
                        }
                    ),
                }
            return {"module": value.__name__}
        if inspect.isclass(value):
            result = {"class": _qualified(value)}
            if value.__module__.startswith(OWNED) and value.__module__ != __name__:
                result["methods"] = self.encode(
                    {k: v for k, v in vars(value).items() if inspect.isfunction(v)}
                )
            return result
        if dataclasses.is_dataclass(value):
            return {
                "dataclass": _qualified(type(value)),
                "fields": self.encode(
                    {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
                ),
            }
        if callable(value):
            return {
                "callable": (
                    _qualified(value)
                    if hasattr(value, "__qualname__")
                    else _qualified(type(value))
                )
            }
        if not type(value).__module__.startswith(OWNED):
            return {"external_type": _qualified(type(value))}
        raise TypeError(
            "Unsupported engineering fingerprint component: " + _qualified(type(value))
        )


def method_metadata(
    method_id,
    implementation,
    *,
    execution_layer="native",
    dependencies=(),
    contract=None
):
    """Fresh metadata snapshot of the loaded implementation at this boundary.

    Stable across installation paths/debug line changes. A different execution
    layer intentionally has a distinct fingerprint. Explicit version changes
    are reviewed manually; actual loaded code/global changes invalidate the hash
    even when a developer forgets to bump that version.
    """
    version = METHOD_VERSIONS[method_id]
    if not inspect.isfunction(implementation):
        raise TypeError("Engineering method identity requires a loaded Python function")
    encoder = _Encoder(method_id)
    payload = {
        "scheme": SCHEME,
        "method_id": method_id,
        "method_version": version,
        "owned_dependency_scope": OWNED,
        "native_dependency_ids": NATIVE_DEPENDENCIES.get(method_id, (method_id,)),
        "execution_layer": execution_layer,
        "implementation": encoder.encode(implementation),
        "dependencies": encoder.encode(dependencies),
        "contract": encoder.encode(contract),
        "versioning_implementation": encoder.encode(
            (
                _code,
                _referenced_names,
                _code_digest.__wrapped__,
                _qualified,
                _Encoder.__init__,
                _Encoder.encode,
                _Encoder._compound,
                method_metadata,
            )
        ),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return {
        "method_id": method_id,
        "method_version": version,
        "implementation_fingerprint": "sha256:" + hashlib.sha256(encoded).hexdigest(),
        "fingerprint_scheme": SCHEME,
        "execution_layer": execution_layer,
    }
