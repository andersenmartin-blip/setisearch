"""Tests for the metadata-only LS2 candidate-system inventory."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from seti_repeater.light_sail_catalog import (
    geometry_planet_inventory,
    rank_target_inventory,
    resolve_archive_aliases,
    summarize_cadence_records,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls2_candidate_inventory.json"


class LS2CandidateInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_scope_stops_before_spectral_access(self):
        boundary = self.config["data_boundary"]
        self.assertTrue(boundary["catalogue_json_may_be_read"])
        self.assertTrue(boundary["cadence_listing_json_may_be_read"])
        self.assertFalse(boundary["linked_hdf5_or_filterbank_may_be_opened"])
        self.assertFalse(boundary["spectral_dataset_values_may_be_read"])
        self.assertFalse(self.config["scientific_scope"]["spectral_search_authorized"])
        self.assertFalse(self.config["claim_boundary"]["technosignature_claimed"])

    def test_priority_list_is_complete_and_stable(self):
        targets = self.config["targets"]
        self.assertEqual([item["priority"] for item in targets], [1, 2, 3, 4, 5])
        self.assertEqual(
            [item["hostname"] for item in targets],
            ["LTT 1445 A", "L 98-59", "HD 260655", "GJ 9827", "TRAPPIST-1"],
        )
        self.assertEqual(len({item["target_id"] for item in targets}), 5)

    def test_archive_alias_resolution_is_exact_after_normalization(self):
        resolved = resolve_archive_aliases(
            ["TRAPPIST-1", "2MASS J23062928-0502285"],
            ["Trappist1", "2MASSJ23062928-0502285", "TRAPPIST-10"],
        )
        self.assertEqual(resolved, ["2MASSJ23062928-0502285", "Trappist1"])

    def test_geometry_inventory_retains_adjacent_pairs(self):
        records = [
            {
                "pl_name": "Example c",
                "hostname": "Example",
                "pl_orbper": 5.0,
                "pl_tranmid": 2459001.0,
                "pl_orbsmax": 0.05,
                "tran_flag": 1,
            },
            {
                "pl_name": "Example b",
                "hostname": "Example",
                "pl_orbper": 2.0,
                "pl_tranmid": 2459000.0,
                "pl_orbsmax": 0.02,
                "tran_flag": 1,
            },
            {
                "pl_name": "Example d",
                "hostname": "Example",
                "pl_orbper": 10.0,
                "pl_tranmid": None,
                "pl_orbsmax": 0.1,
                "tran_flag": 1,
            },
        ]
        result = geometry_planet_inventory(records)
        self.assertTrue(result["geometry_ready"])
        self.assertEqual(result["eligible_planet_count"], 2)
        self.assertEqual(
            [item["pl_name"] for item in result["eligible_planets"]],
            ["Example b", "Example c"],
        )
        self.assertEqual(result["adjacent_pairs"][0]["inner_planet"], "Example b")
        self.assertIn("missing_transit_midpoint", result["rejected_planets"][0]["reasons"])

    def test_cadence_summary_recognizes_ls_products_and_scan_count(self):
        records = []
        for index in range(6):
            records.extend(
                [
                    {
                        "mjd": 60000.0 + index / 1000.0,
                        "utc": f"2023-01-01T00:0{index}:00",
                        "center_freq": 1500.0,
                        "telescope": "GBT",
                        "url": f"https://example/{index}.gpuspec.0002.h5",
                    },
                    {
                        "mjd": 60000.0 + index / 1000.0,
                        "utc": f"2023-01-01T00:0{index}:00",
                        "center_freq": 1500.0,
                        "telescope": "GBT",
                        "url": f"https://example/{index}.gpuspec.8.0001.h5",
                    },
                ]
            )
        summary = summarize_cadence_records(records)
        self.assertTrue(summary["has_medium_resolution_hdf5"])
        self.assertTrue(summary["has_high_time_resolution_hdf5"])
        self.assertTrue(summary["has_at_least_six_scan_times"])
        self.assertEqual(summary["distinct_mjd_count"], 6)

    def test_ranking_selects_first_priority_eligible_target(self):
        targets = [
            {
                "priority": 1,
                "target_id": "first",
                "hostname": "First",
                "geometry": {"geometry_ready": True},
                "resolved_archive_aliases": ["FIRST"],
                "cadences": [],
            },
            {
                "priority": 2,
                "target_id": "second",
                "hostname": "Second",
                "geometry": {"geometry_ready": True},
                "resolved_archive_aliases": ["SECOND"],
                "cadences": [
                    {
                        "cadence_url": "https://example/cadence/2",
                        "summary": {
                            "has_medium_resolution_hdf5": True,
                            "has_at_least_six_scan_times": True,
                        },
                    }
                ],
            },
        ]
        ranked = rank_target_inventory(targets)
        self.assertFalse(ranked[0]["eligible_for_header_preflight"])
        self.assertTrue(ranked[1]["eligible_for_header_preflight"])


if __name__ == "__main__":
    unittest.main()
