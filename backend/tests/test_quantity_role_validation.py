import pytest
from backend.equipment_costing.unit_conversion.bridges.basis_validation import (
    validate_bulk_liquid_basis,
)


def test_oxygen_feed_does_not_become_broth_inventory_even_with_liquid_density_assumption():
    report = {
        "entities": [
            {
                "key": "bio",
                "values": [
                    {"property": "name", "normalized_value": "Continuous bioreactor"}
                ],
            },
            {
                "key": "oxygen",
                "values": [
                    {
                        "property": "description",
                        "normalized_value": "O2 entering bioreactor",
                    }
                ],
            },
            {
                "key": "broth",
                "values": [
                    {
                        "property": "description",
                        "normalized_value": "Broth leaving bioreactor",
                    }
                ],
            },
        ]
    }
    with pytest.raises(ValueError, match="total broth throughput"):
        validate_bulk_liquid_basis(
            report, "bio", {"entity_key": "oxygen"}, "vessel_volume"
        )
    with pytest.raises(ValueError):
        validate_bulk_liquid_basis(
            report, "bio", {"entity_key": "oxygen"}, "mixing_power"
        )
    validate_bulk_liquid_basis(report, "bio", {"entity_key": "broth"}, "vessel_volume")
    # Supplied dimensions or a distinct validated gas-residence method remain possible.
    validate_bulk_liquid_basis(report, "bio", {"entity_key": "oxygen"}, "direct")
