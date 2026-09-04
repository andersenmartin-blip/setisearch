"""Tests for the post-LS2 dedicated cadence-view discovery."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls2b_cadence_discovery.json"
SCRIPT = ROOT / "scripts/ls2b_cadence_discovery.py"
SPEC = importlib.util.spec_from_file_location("ls2b_cadence_discovery", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
LS2B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LS2B)


def cadence(url: str, mjd: float, medium: int, htr: int = 0) -> dict:
    return {
        "cadence_url": url,
        "summary": {
            "has_at_least_six_scan_times": True,
            "mjd_min": mjd,
            "mjd_max": mjd + 0.03,
            "center_frequencies_mhz": [1475.09765625],
            "product_counts": {
                "medium_resolution_hdf5": medium,
                "high_time_resolution_hdf5": htr,
            },
        },
    }


class LS2BCadenceDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_boundary_is_metadata_only(self):
        boundary = self.config["data_boundary"]
        self.assertTrue(boundary["archive_query_json_may_be_read"])
        self.assertTrue(boundary["cadence_listing_json_may_be_read"])
        self.assertFalse(boundary["linked_hdf5_or_filterbank_may_be_opened"])
        self.assertFalse(boundary["spectral_dataset_values_may_be_read"])
        self.assertFalse(self.config["claim_boundary"]["search_authorized"])
        self.assertFalse(
            self.config["claim_boundary"]["previous_ls2_result_may_be_overwritten"]
        )

    def test_targets_are_conditioned_on_ls2_aliases(self):
        self.assertEqual(
            [item["archive_alias"] for item in self.config["targets"]],
            ["HIP31635", "HIP115752"],
        )

    def test_selection_requires_six_medium_products(self):
        targets = [
            {
                "source_priority": 3,
                "target_id": "hd_260655",
                "hostname": "HD 260655",
                "archive_alias": "HIP31635",
                "cadences": [cadence("https://example/incomplete", 59000.0, 5, 6)],
            }
        ]
        self.assertIsNone(LS2B.select_preflight_cadence(targets))

    def test_selection_preserves_target_priority_before_time(self):
        targets = [
            {
                "source_priority": 3,
                "target_id": "hd_260655",
                "hostname": "HD 260655",
                "archive_alias": "HIP31635",
                "cadences": [cadence("https://example/hd", 60000.0, 6, 6)],
            },
            {
                "source_priority": 4,
                "target_id": "gj_9827",
                "hostname": "GJ 9827",
                "archive_alias": "HIP115752",
                "cadences": [cadence("https://example/gj", 59000.0, 6, 6)],
            },
        ]
        selected = LS2B.select_preflight_cadence(targets)
        assert selected is not None
        self.assertEqual(selected["target_id"], "hd_260655")

    def test_selection_uses_earliest_cadence_within_target(self):
        targets = [
            {
                "source_priority": 3,
                "target_id": "hd_260655",
                "hostname": "HD 260655",
                "archive_alias": "HIP31635",
                "cadences": [
                    cadence("https://example/later", 60001.0, 6),
                    cadence("https://example/earlier", 60000.0, 6),
                ],
            }
        ]
        selected = LS2B.select_preflight_cadence(targets)
        assert selected is not None
        self.assertEqual(selected["cadence_url"], "https://example/earlier")


if __name__ == "__main__":
    unittest.main()
