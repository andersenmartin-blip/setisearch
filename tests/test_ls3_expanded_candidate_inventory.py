"""Tests for the metadata-only LS3 expanded target inventory."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls3_expanded_candidate_inventory.json"
SCRIPT = ROOT / "scripts/ls3_expanded_candidate_inventory.py"
SPEC = importlib.util.spec_from_file_location("ls3_inventory", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
LS3 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LS3)


def cadence(url: str, medium: int, mjds: int = 6, htr: int = 6) -> dict:
    return {
        "cadence_url": url,
        "summary": {
            "has_at_least_six_scan_times": mjds >= 6,
            "distinct_mjd_count": mjds,
            "product_counts": {
                "medium_resolution_hdf5": medium,
                "high_time_resolution_hdf5": htr,
            },
        },
    }


def target(
    priority: int,
    target_id: str,
    geometry_ready: bool,
    cadences: list[dict],
) -> dict:
    return {
        "priority": priority,
        "cohort": "test",
        "target_id": target_id,
        "hostname": target_id.upper(),
        "distance_pc": float(priority),
        "resolved_archive_aliases": [target_id],
        "geometry": {
            "geometry_ready": geometry_ready,
            "eligible_planet_count": 2 if geometry_ready else 1,
        },
        "cadences": cadences,
    }


class LS3ExpandedInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_boundary_stops_before_radio_file_access(self):
        boundary = self.config["data_boundary"]
        self.assertTrue(boundary["catalogue_json_may_be_read"])
        self.assertTrue(boundary["archive_query_json_may_be_read"])
        self.assertTrue(boundary["cadence_listing_json_may_be_read"])
        self.assertFalse(boundary["linked_hdf5_or_filterbank_may_be_opened"])
        self.assertFalse(boundary["spectral_dataset_values_may_be_read"])
        self.assertFalse(self.config["claim_boundary"]["search_authorized"])
        self.assertFalse(self.config["claim_boundary"]["technosignature_claimed"])

    def test_candidate_set_has_carryovers_and_nine_new_systems(self):
        targets = self.config["targets"]
        self.assertEqual([item["priority"] for item in targets], list(range(1, 14)))
        self.assertEqual(
            [item["hostname"] for item in targets[:4]],
            ["LTT 1445 A", "L 98-59", "TRAPPIST-1", "GJ 9827"],
        )
        new_targets = [item for item in targets if item["cohort"] == "new nearby candidate"]
        self.assertEqual(len(new_targets), 9)
        self.assertIn("LHS 1140", [item["hostname"] for item in new_targets])
        self.assertIn("AU Mic", [item["hostname"] for item in new_targets])
        self.assertNotIn("HD 260655", [item["hostname"] for item in targets])

    def test_data_ready_requires_six_scans_and_six_medium_products(self):
        self.assertTrue(LS3.cadence_is_data_ready(cadence("ok", 6, 6)))
        self.assertFalse(LS3.cadence_is_data_ready(cadence("five-products", 5, 6)))
        self.assertFalse(LS3.cadence_is_data_ready(cadence("five-scans", 6, 5)))

    def test_every_qualified_system_advances(self):
        inputs = [
            target(1, "first", True, [cadence("a", 6)]),
            target(2, "second", True, [cadence("b", 6), cadence("c", 6)]),
            target(3, "no_geometry", False, [cadence("d", 6)]),
            target(4, "no_cadence", True, [cadence("e", 5)]),
        ]
        advancing = LS3.advancing_candidates(inputs)
        self.assertEqual([item["target_id"] for item in advancing], ["first", "second"])
        self.assertEqual(advancing[1]["cadence_count"], 2)

    def test_alias_lists_are_nonempty_and_target_ids_unique(self):
        targets = self.config["targets"]
        self.assertEqual(len({item["target_id"] for item in targets}), len(targets))
        self.assertTrue(all(item["archive_aliases"] for item in targets))
        self.assertTrue(all(item["science_reference"].startswith("https://") for item in targets))


if __name__ == "__main__":
    unittest.main()
