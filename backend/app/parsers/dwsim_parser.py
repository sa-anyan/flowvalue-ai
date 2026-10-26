"""Read saved DWSIM results only. Never execute embedded scripts or solve a flowsheet."""

from math import isfinite
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring
from pydantic import Field

from app.engine.costing import CostingRequest, Model
from app.parsers.stream_parser import Stream


class ImportedUnit(Model):
    unit_id: str
    native_id: str
    native_type: str
    x: float = 0
    y: float = 0
    equipment: dict | None = None
    missing_inputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DWSIMImport(Model):
    streams: list[Stream]
    units: list[ImportedUnit]
    equipment: list[dict]
    warnings: list[str]
    source: str = "DWSIM saved results (SI); not re-simulated"


def number(node, name):
    if node is None:
        return None
    raw = node.findtext(name)
    if not raw:
        return None
    try:
        value = float(raw)
        return value if isfinite(value) else None
    except ValueError:
        return None


def parse_dwxml(content: bytes) -> DWSIMImport:
    if len(content) > 5 * 1024 * 1024:
        raise ValueError("DWSIM XML exceeds 5 MiB")
    try:
        root = fromstring(content, forbid_dtd=True)
    except (ParseError, DefusedXmlException) as exc:
        raise ValueError(
            "Invalid or unsafe DWSIM XML; DTDs and entities are prohibited"
        ) from exc
    # Namespace-independent, including older DWSIM exports.
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    if root.tag != "DWSIM_Simulation_Data":
        raise ValueError("Expected a native DWSIM_Simulation_Data document (.dwxml)")
    objects = root.findall("SimulationObjects/SimulationObject")
    graphics = {
        g.findtext("Name"): g for g in root.findall("GraphicObjects/GraphicObject")
    }
    ids = [o.findtext("Name") for o in objects]
    if not objects or len(objects) > 10000 or None in ids or len(set(ids)) != len(ids):
        raise ValueError(
            "Simulation objects must have unique nonempty IDs (maximum 10000)"
        )
    tags = {i: (graphics[i].findtext("Tag") or i) if i in graphics else i for i in ids}
    if len(set(tags.values())) != len(tags):
        raise ValueError("Duplicate object tags: rename units/streams before importing")
    warnings = [
        "Saved simulator results are not independently converged or thermodynamically validated.",
        "Imported operating pressures are not design pressures. Confirm design margins, materials and sizing before using costs.",
    ]
    streams, props, units = [], {}, []
    stream_ids = {
        o.findtext("Name")
        for o in objects
        if (o.findtext("Type") or "").endswith(".MaterialStream")
    }

    def connection(g, direction, attr):
        if g is None:
            return None
        for c in g.findall(direction + "/Connector"):
            if c.get("IsAttached", "").lower() == "true":
                other = c.get(attr)
                if other in tags and other not in stream_ids:
                    return tags[other]
        return None

    for o in objects:
        native = o.findtext("Name")
        if native not in stream_ids:
            continue
        phases = {p.findtext("ID"): p for p in o.findall("Phases/Phase")}

        def phase_properties(p):
            matches = p.findall("Properties") if p is not None else []
            return next((n for n in reversed(matches) if len(n)), None)

        p = phase_properties(phases.get("0"))
        values = [number(p, n) for n in ("temperature", "pressure", "massflow")]
        if any(v is None for v in values):
            warnings.append(
                f"{tags[native]}: missing finite mixture T/P/mass flow; stream excluded."
            )
            continue
        t, pressure, mass = values
        vapor = number(phase_properties(phases.get("2")), "massfraction") or 0
        solid = number(phase_properties(phases.get("7")), "massfraction") or 0
        liquid = number(phase_properties(phases.get("1")), "massfraction") or 0
        phase = (
            "vapor"
            if vapor > 0.999
            else "solid"
            if solid > 0.999
            else "liquid"
            if liquid > 0.999
            else "mixed"
        )
        g = graphics.get(native)
        stream = Stream(
            stream_id=tags[native],
            temperature_c=t - 273.15,
            pressure_bar_abs=pressure / 1e5,
            mass_flow_kg_h=mass * 3600,
            phase=phase,
            source_unit=connection(g, "InputConnectors", "AttachedFromObjID"),
            destination_unit=connection(g, "OutputConnectors", "AttachedToObjID"),
        )
        streams.append(stream)
        props[stream.stream_id] = {
            n: number(p, n)
            for n in (
                "density",
                "volumetric_flow",
                "molecularWeight",
                "heatCapacityCp",
                "heatCapacityCv",
            )
        }
        if o.findtext("Calculated", "false").lower() != "true":
            warnings.append(
                f"{stream.stream_id}: simulator marks this stream uncalculated; saved values require review."
            )
    for o in objects:
        native = o.findtext("Name")
        typ = (o.findtext("Type") or "").rsplit(".", 1)[-1]
        if native in stream_ids or typ == "EnergyStream":
            continue
        unit_id = tags[native]
        g = graphics.get(native)
        draft = ImportedUnit(
            unit_id=unit_id,
            native_id=native,
            native_type=typ,
            x=number(g, "X") or 0,
            y=number(g, "Y") or 0,
        )
        incoming = [s for s in streams if s.destination_unit == unit_id]
        outgoing = [s for s in streams if s.source_unit == unit_id]
        spec = {"unit_id": unit_id, "material": "carbon_steel"}
        pressures = [s.pressure_bar_abs for s in incoming + outgoing]
        spec["design_pressure_barg"] = (
            max(0, max(pressures) - 1.01325) if pressures else None
        )
        kind = {
            "HeatExchanger": "heat_exchanger",
            "Pump": "pump",
            "Compressor": "compressor",
            "Vessel": "vessel",
            "Reactor_CSTR": "reactor",
            "Reactor_PFR": "reactor",
        }.get(typ)
        if kind:
            spec["kind"] = kind
        if kind == "heat_exchanger":
            spec.update(
                duty_kw=abs(number(o, "Q") or 0),
                overall_u_w_m2_k=number(o, "OverallCoefficient"),
                lmtd_k=number(o, "LMTD"),
                lmtd_correction_factor=number(o, "LMTD_F") or 1,
            )
            draft.warnings.append(
                "Shell-and-tube correlation assumed; confirm exchanger construction and carbon steel material."
            )
        elif kind in ("vessel", "reactor"):
            spec["volume_m3"] = number(o, "Volume")
            draft.warnings.append(
                "Only vessel/reactor shell cost; internals, catalyst, agitation and specialized equipment excluded."
            )
        elif kind == "pump":
            inlet = incoming[0] if len(incoming) == 1 else None
            outlet = outgoing[0] if len(outgoing) == 1 else None
            density = props.get(inlet.stream_id, {}).get("density") if inlet else None
            flow = (
                props.get(inlet.stream_id, {}).get("volumetric_flow") if inlet else None
            )
            spec.update(
                density_kg_m3=density,
                volumetric_flow_m3_h=flow * 3600 if flow else None,
                head_m=(outlet.pressure_bar_abs - inlet.pressure_bar_abs)
                * 1e5
                / density
                / 9.80665
                if inlet and outlet and density
                else None,
                efficiency=(number(o, "Eficiencia") or 0) / 100,
            )
        elif kind == "compressor":
            inlet = incoming[0] if len(incoming) == 1 else None
            outlet = outgoing[0] if len(outgoing) == 1 else None
            p = props.get(inlet.stream_id, {}) if inlet else {}
            cp, cv = p.get("heatCapacityCp"), p.get("heatCapacityCv")
            spec = {
                "unit_id": unit_id,
                "kind": kind,
                "material": "carbon_steel",
                "mass_flow_kg_s": inlet.mass_flow_kg_h / 3600 if inlet else None,
                "inlet_temperature_k": inlet.temperature_c + 273.15 if inlet else None,
                "inlet_pressure_bar_abs": inlet.pressure_bar_abs if inlet else None,
                "outlet_pressure_bar_abs": outlet.pressure_bar_abs if outlet else None,
                "molecular_weight_kg_kmol": p.get("molecularWeight"),
                "heat_capacity_ratio": cp / cv if cp and cv else None,
                "isentropic_efficiency": (number(o, "AdiabaticEfficiency") or 0) / 100,
            }
            draft.warnings.append(
                "Ideal-gas single-stage compressor sizing; confirm applicability to saved thermodynamics."
            )
        else:
            draft.missing_inputs = [
                "Unsupported costing model: supply a separate equipment estimate"
            ]
        if kind:
            missing = [
                k
                for k, v in spec.items()
                if v is None
                or (
                    isinstance(v, (float, int))
                    and v <= 0
                    and k != "design_pressure_barg"
                )
            ]
            draft.missing_inputs = missing
            if not missing:
                try:
                    validated = CostingRequest.model_validate(
                        {"equipment": [spec]}
                    ).equipment[0]
                    draft.equipment = validated.model_dump()
                except ValueError as exc:
                    draft.missing_inputs = [str(exc)]
        if o.findtext("Calculated", "false").lower() != "true":
            draft.equipment = None
            draft.missing_inputs.append(
                "Re-converge and save this uncalculated unit in DWSIM"
            )
        units.append(draft)
    if not streams:
        raise ValueError(
            "No usable material streams: converge and save the simulation before importing"
        )
    return DWSIMImport(
        streams=streams,
        units=units,
        equipment=[u.equipment for u in units if u.equipment],
        warnings=warnings,
    )
