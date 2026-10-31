import unittest

from backend.equipment_costing.total_cost import calculate_total_cost


def exchanger(tag="HX-1", **changes):
    item = {
        "equipment_tag": tag,
        "curve_id": "G287-092",
        "size": 200,
        "size_unit": "heat-transfer area, ft²",
    }
    item.update(changes)
    return item


class EquipmentTotalTests(unittest.TestCase):
    def test_routing_counts_and_source_evidence(self):
        r = calculate_total_cost(
            [
                exchanger(quantity=2, parsed_source={"sheet": "Units", "cell": "A5"}),
                exchanger("HX-2", size=1000),
            ]
        )
        self.assertAlmostEqual(r.total, 2 * 100 * 200**0.78 + 100 * 1000**0.78)
        self.assertEqual(r.status, "calculated")
        self.assertEqual(r.equipment[0].parsed_source["cell"], "A5")
        self.assertEqual(len(r.subtotals), 1)

    def test_unit_prices_require_physical_quantities(self):
        duct = {
            "equipment_tag": "D-1",
            "curve_id": "G278-063",
            "size": 40,
            "size_unit": "duct diameter, in",
        }
        self.assertIsNone(calculate_total_cost([duct]).total)
        duct.update(quantity=100, quantity_unit="ft")
        r = calculate_total_cost([duct, exchanger()])
        self.assertAlmostEqual(r.total, 64.18 * 100 + 100 * 200**0.78)
        duct["quantity_unit"] = "m"
        converted = calculate_total_cost([duct])
        self.assertAlmostEqual(converted.equipment_cost_total, 64.18 * 100 / 0.3048)
        self.assertIsNotNone(converted.equipment[0].quantity_conversion)

    def test_unresolved_equipment_is_never_silently_dropped(self):
        r = calculate_total_cost([exchanger(), {"equipment_tag": "P-1"}])
        self.assertIsNone(r.total)
        self.assertGreater(r.subtotals[0].amount, 0)
        self.assertEqual(r.equipment[1].status, "needs_review")
        self.assertEqual(len(r.equipment), 2)

    def test_distinct_cost_bases_and_scopes_not_added(self):
        future = exchanger(
            "HX-2",
            costing_options={
                "target_index": 640,
                "target_period": "test",
                "target_index_source": "synthetic",
            },
        )
        r = calculate_total_cost([exchanger(), future])
        self.assertIsNone(r.total)
        self.assertEqual(len(r.subtotals), 2)
        installation = exchanger(
            "HX-2",
            costing_options={
                "allow_unverified": True,
                "factors": ("287.material.316_stainless",),
                "factor_basis_confirmation": "Reviewed baseline",
            },
        )
        r = calculate_total_cost([exchanger(), installation])
        self.assertIsNotNone(r.total)
        self.assertEqual(r.status, "provisional")

    def test_duplicate_tags_invalid_counts_and_empty_input(self):
        with self.assertRaises(ValueError):
            calculate_total_cost([exchanger(), exchanger(" hx-1 ")])
        with self.assertRaises(ValueError):
            calculate_total_cost([{"equipment_tag": ""}])
        for quantity in [0, -1, True, 1.5, float("nan")]:
            self.assertIsNone(
                calculate_total_cost([exchanger(quantity=quantity)]).total
            )
        self.assertIsNone(calculate_total_cost([]).total)

    def test_graph_opt_in_and_bad_mapping(self):
        graph = {
            "equipment_tag": "C-1",
            "curve_id": "G265-023",
            "size": 20,
            "size_unit": "t/hr (as printed)",
        }
        self.assertIsNone(calculate_total_cost([graph]).total)
        graph["costing_options"] = {"allow_unverified": True}
        self.assertEqual(calculate_total_cost([graph]).status, "provisional")
        graph["curve_id"] = "unknown"
        self.assertIsNone(calculate_total_cost([graph]).total)


if __name__ == "__main__":
    unittest.main()
