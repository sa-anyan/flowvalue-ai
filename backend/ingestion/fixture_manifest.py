"""P6 simulator fixture declarations; no simulator adapter or support certification.

A declaration is not a claim of support. Only independently reconciled,
authorised fixtures can be promoted by a separate formal review process.
"""

from dataclasses import dataclass
import re

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_FAMILIES = {"dwsim-native", "dwsim-excel", "aspen-plus", "aspen-hysys"}
_OUTCOMES = {"supported", "unsupported", "warn"}


@dataclass(frozen=True)
class Fixture:
    family: str
    source_version: str
    export_format: str
    export_version: str
    adapter_version: str
    sha256: str
    permission_reference: str
    expected_observations_reference: str
    expected_outcome: str
    expected_unmapped_fields: tuple[str, ...] = ()


def validate_fixture(fixture: Fixture) -> tuple[str, ...]:
    """Return issues; never infer a supported version or a verified result."""
    errors = []
    if fixture.family not in _FAMILIES:
        errors.append("unknown_source_family")
    for name in (
        "source_version", "export_format", "export_version",
        "adapter_version", "permission_reference",
        "expected_observations_reference",
    ):
        if not getattr(fixture, name).strip():
            errors.append(f"missing_{name}")
    if not _SHA256.fullmatch(fixture.sha256):
        errors.append("invalid_sha256")
    if fixture.expected_outcome not in _OUTCOMES:
        errors.append("unknown_expected_outcome")
    if fixture.expected_outcome == "supported" and not fixture.expected_observations_reference.strip():
        errors.append("missing_independent_expected_results")
    if any(not item.strip() for item in fixture.expected_unmapped_fields):
        errors.append("blank_unmapped_field")
    return tuple(dict.fromkeys(errors))
