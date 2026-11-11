"""SIZE-C03 cross-file integration; real synthetic workbooks, no AI calls.
Known XLS Boolean type loss is deliberately a failing ingestion contract,
owned by Engineer 2; never weaken or xfail it here.
"""

import math
from pathlib import Path

import pytest
from backend.orchestration.ingest import parse
from backend.orchestration.sizing import derive_size
from backend.engineering_sizing.adapter import derive

FIXTURES = Path(__file__).parent / "fixtures/sizing_cross_file"
FORMATS = ["xlsx", "xlsm", "xls"]
VARIANTS = ["rows", "columns", "rows_units"]


def load(filename):
    path = FIXTURES / filename
    return parse(path.read_bytes(), path.name)["report"]


def stream(report, name):
    return next(
        e
        for e in report["entities"]
        if e["kind"] == "material" and e["identifier"] == name
    )


def sizing(report, method, *, efficiency=0.5, gauge=False):
    name = {
        "gas_compression": "C-IN",
        "pump_duty": "P-IN",
        "exchanger_area": "H-IN",
        "vaporizer_area": "V-IN",
    }[method]
    params = {
        "gas_compression": dict(
            molecular_weight_kg_kmol=28,
            heat_capacity_ratio=math.nextafter(1.0, 2.0),
            discharge_pressure_bar=2,
            efficiency=0.75,
            compressibility_z=1,
        ),
        "pump_duty": dict(differential_pressure_bar=1, efficiency=efficiency),
        "exchanger_area": dict(overall_u_w_m2_k=500, lmtd_k=20, lmtd_correction=1),
        "vaporizer_area": dict(overall_u_w_m2_k=1000, lmtd_k=25, lmtd_correction=0.8),
    }[method]
    if gauge:
        params["atmospheric_pressure_bar"] = 1
    return {
        "method": method,
        "stream_key": stream(report, name)["key"],
        "parameters": params,
    }


@pytest.mark.parametrize("ext", FORMATS)
@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize(
    "method,expected,unit",
    [
        ("gas_compression", 82.33066173777114, "kW"),
        ("pump_duty", 0.2298895010734333601697918125, "1000 US_gpm_psi"),
        ("exchanger_area", 10, "m2"),
        ("vaporizer_area", 12.5, "m2"),
    ],
)
def test_equivalent_real_workbook_inputs(ext, variant, method, expected, unit):
    report = load(variant + "." + ext)
    proposal = {"sizing": sizing(report, method)}
    # Existing orchestration dispatcher, not a duplicate equation implementation.
    value, actual_unit, audit = derive_size(proposal, report)
    assert value == pytest.approx(expected, rel=5e-12, abs=0)
    assert actual_unit == unit and audit["source_evidence"]
    equipment = {
        e["identifier"] for e in report["entities"] if e["kind"] == "equipment"
    }
    assert {"C-101", "P-101", "HE-101", "V-101"} <= equipment
    if method == "pump_duty":
        assert audit["calculation"]["hydraulic_power_kw"] == pytest.approx(0.1)
        assert audit["calculation"]["shaft_power_kw"] == pytest.approx(0.2)


@pytest.mark.parametrize("ext", FORMATS)
@pytest.mark.parametrize("boolean", [True, False])
@pytest.mark.parametrize("method", ["exchanger_area", "vaporizer_area"])
def test_boolean_heat_from_file_must_not_be_costed(ext, boolean, method):
    report = load("rows_bool_" + str(boolean).lower() + "." + ext)
    proposal = sizing(report, method)
    # Both aliases must refuse the invalid H-IN duty, even when labelled vaporizer.
    proposal["stream_key"] = stream(report, "H-IN")["key"]
    with pytest.raises(ValueError):
        derive(proposal, report)


@pytest.mark.parametrize("ext", FORMATS)
def test_pump_overflow_after_real_ingestion(ext):
    report = load("rows." + ext)
    with pytest.raises(ValueError, match="shaft power.*finite"):
        derive(sizing(report, "pump_duty", efficiency=1e-320), report)


@pytest.mark.parametrize("ext", FORMATS)
def test_gauge_pressure_requires_explicit_atmosphere(ext):
    report = load("rows_gauge." + ext)
    with pytest.raises(ValueError):
        derive(sizing(report, "gas_compression"), report)
    value, unit, _ = derive(sizing(report, "gas_compression", gauge=True), report)
    assert unit == "kW" and value == pytest.approx(82.33066173777114, rel=5e-12, abs=0)


@pytest.mark.parametrize("ext", FORMATS)
@pytest.mark.parametrize("method", ["exchanger_area", "vaporizer_area"])
def test_missing_heat_units_remain_unresolved(ext, method):
    report = load("rows_missing_units." + ext)
    with pytest.raises(ValueError):
        derive(sizing(report, method), report)


@pytest.mark.parametrize(
    "suffix", ["csv", "pdf", "docx", "json", "dwxml", "png", "xlsb"]
)
def test_unavailable_active_upload_types_are_explicitly_rejected(suffix):
    with pytest.raises(ValueError, match="Only .xlsx, .xls and .xlsm"):
        parse(b"not an engineering workbook", "synthetic." + suffix)
