"""P6 adapter manifest negative tests; synthetic metadata only."""

from dataclasses import replace

from backend.ingestion.fixture_manifest import Fixture, validate_fixture


def sample():
    return Fixture(
        family="dwsim-native", source_version="fixture-v1",
        export_format="dwxml", export_version="fixture-v1",
        adapter_version="candidate-v0", sha256="a" * 64,
        permission_reference="synthetic-test",
        expected_observations_reference="synthetic-expected.json",
        expected_outcome="supported",
    )


def test_complete_synthetic_declaration_has_no_metadata_errors():
    assert validate_fixture(sample()) == ()


def test_unknown_family_and_unsupported_version_are_not_silently_supported():
    assert "unknown_source_family" in validate_fixture(replace(sample(), family="other"))
    assert "missing_source_version" in validate_fixture(replace(sample(), source_version=""))


def test_source_hash_permission_and_independent_expected_results_are_required():
    for changed, issue in [
        ({"sha256": "bad"}, "invalid_sha256"),
        ({"permission_reference": ""}, "missing_permission_reference"),
        ({"expected_observations_reference": ""}, "missing_expected_observations_reference"),
    ]:
        assert issue in validate_fixture(replace(sample(), **changed))


def test_unmapped_fields_must_be_named():
    assert "blank_unmapped_field" in validate_fixture(
        replace(sample(), expected_unmapped_fields=("pressure", " "))
    )


def test_hysys_and_aspen_plus_are_distinct_families():
    for family in ("aspen-plus", "aspen-hysys", "dwsim-excel"):
        assert validate_fixture(replace(sample(), family=family)) == ()
