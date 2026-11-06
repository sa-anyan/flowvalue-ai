"""Source-only temperature feasibility facts; never a topology or duty selection."""

from itertools import permutations
from .derivations import derive


def temperature_arrangements(observations, stream_context, limit=24):
    by_stream = {}
    for v in observations:
        if v["property"] == "temperature":
            by_stream.setdefault(v["entity_key"], []).append(v)
    usable = [values[0] for values in by_stream.values() if len(values) == 1]
    ambiguous = [key for key, values in by_stream.items() if len(values) != 1]
    roles = {
        s["entity_key"]: {c.get("role") for c in s.get("connections", [])}
        for s in stream_context
    }
    arrangements = []
    truncated = len(usable) > 8
    usable = usable[:8]
    for values in permutations(usable, 4):
        if any(
            (
                "source" in roles.get(v["entity_key"], set())
                and "destination" not in roles.get(v["entity_key"], set())
            )
            for v in (values[0], values[2])
        ):
            continue
        if any(
            (
                "destination" in roles.get(v["entity_key"], set())
                and "source" not in roles.get(v["entity_key"], set())
            )
            for v in (values[1], values[3])
        ):
            continue
        result = {}
        for arrangement in ["countercurrent", "parallel"]:
            try:
                inputs, _ = derive(
                    [
                        {
                            "name": "lmtd_k",
                            "method": "lmtd_" + arrangement,
                            "measurement_ids": [v["id"] for v in values],
                        }
                    ],
                    observations,
                    {},
                    {},
                )
                result[arrangement] = {"valid": True, "lmtd_k": inputs["lmtd_k"]}
            except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
                result[arrangement] = {"valid": False, "reason": str(exc)}
        if not any(v["valid"] for v in result.values()):
            continue
        if len(arrangements) >= limit:
            truncated = True
            break
        arrangements.append(
            {
                "roles": dict(
                    zip(
                        ["hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet"],
                        [v["entity_key"] for v in values],
                    )
                ),
                "source_measurement_ids": [v["id"] for v in values],
                "feasibility": result,
            }
        )
    return {
        "arrangements": arrangements,
        "truncated": truncated,
        "ambiguous_temperature_streams": ambiguous,
        "notice": "Python temperature-only hypotheses, not confirmed fluid pairing, physical connections, flow arrangement, heat duty or exchanger design. Select compatible source streams explicitly. Equal outlet temperatures do not imply zero countercurrent driving force. Isothermal phase change may require a separate latent-heat basis.",
    }


def enthalpy_pairings(observations, stream_context, limit=32):
    """Bounded signed arithmetic hypotheses, not confirmed fluid-side pairings."""
    from .. import convert
    from .heat_exchanger import signed_enthalpy_duty

    by_stream = {}
    for observation in observations:
        if observation["property"] == "enthalpy_flow":
            by_stream.setdefault(observation["entity_key"], []).append(observation)
    ambiguous = [key for key, values in by_stream.items() if len(values) != 1]
    usable = [values[0] for values in by_stream.values() if len(values) == 1]
    truncated = len(usable) > 8
    usable = usable[:8]
    roles = {
        s["entity_key"]: {c.get("role") for c in s.get("connections", [])}
        for s in stream_context
    }
    pairs = []
    for inlet, outlet in permutations(usable, 2):
        if roles.get(inlet["entity_key"]) == {"source"} or roles.get(
            outlet["entity_key"]
        ) == {"destination"}:
            continue
        hi = convert(inlet["value"], inlet["unit"], "kW")
        ho = convert(outlet["value"], outlet["unit"], "kW")
        if hi.value is None or ho.value is None:
            continue
        if len(pairs) >= limit:
            truncated = True
            break
        pairs.append(
            {
                "inlet_stream_key": inlet["entity_key"],
                "outlet_stream_key": outlet["entity_key"],
                "source_measurement_ids": [inlet["id"], outlet["id"]],
                "hot_release_kw": signed_enthalpy_duty(hi.value, ho.value, "hot"),
                "cold_absorption_kw": signed_enthalpy_duty(hi.value, ho.value, "cold"),
            }
        )
    return {
        "pairings": pairs,
        "truncated": truncated,
        "ambiguous_enthalpy_streams": ambiguous,
        "notice": "Signed Python arithmetic only. Pairings, common enthalpy reference, utility allocation and physical service are NOT confirmed. Do not take an absolute value or silently change source measurements.",
    }
