"""Tests for the HD 63433 LS3B header-only preflight."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls3b_hd63433_header_preflight.json"
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location(
    "ls3b_hd63433_header_preflight", SCRIPT_DIR / "ls3b_hd63433_header_preflight.py"
)
assert SPEC is not None and SPEC.loader is not None
LS3B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LS3B)


def header(source: str, tstart: float, *, tsamp: float = 1.0) -> dict:
    return {
        "source_name": source,
        "tstart_mjd": tstart,
        "tsamp_s": tsamp,
        "nchans": 1024,
        "ntime": 300,
        "foff_mhz": -0.002,
        "frequency_low_mhz": 1100.0,
        "frequency_high_mhz": 1900.0,
        "bandwidth_mhz": 800.0,
        "spectral_dataset_values_read": False,
    }


class LS3BHeaderPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_boundary_forbids_dataset_values_and_search(self):
        boundary = self.config["data_boundary"]
        self.assertTrue(boundary["hdf5_structure_and_attributes_may_be_read"])
        self.assertFalse(boundary["hdf5_data_dataset_may_be_indexed"])
        self.assertFalse(boundary["spectral_dataset_values_may_be_read"])
        self.assertFalse(self.config["claim_boundary"]["search_authorized"])

    def test_all_adjacent_pairs_are_frozen_in_orbital_order(self):
        pairs = LS3B.adjacent_planet_pairs(self.config["ephemeris"]["planets"])
        self.assertEqual(
            [[left["pl_name"], right["pl_name"]] for left, right in pairs],
            [["HD 63433 d", "HD 63433 b"], ["HD 63433 b", "HD 63433 c"]],
        )

    def test_header_gate_computes_both_pairs(self):
        sources = ["HIP38228", "HIP37035", "Hip38228", "HIP37071", "HIP38228", "HIP37095"]
        scans = []
        headers = {}
        for index, source in enumerate(sources):
            medium_url = f"https://example/_{index:04d}.gpuspec.0002.h5"
            htr_url = f"https://example/_{index:04d}.gpuspec.8.0001.h5"
            scans.append({"scan_key": f"{index:04d}", "medium_url": medium_url, "htr_url": htr_url})
            headers[medium_url] = header(source, 57824.0 + index / 1000.0)
            headers[htr_url] = header(source, 57824.0 + index / 1000.0, tsamp=0.00035)
        result = LS3B.qualify_cadence(
            {"cadence_url": "https://example/cadence", "scans": scans},
            headers,
            "HIP38228",
            self.config["header_criteria"],
            self.config["ephemeris"]["planets"],
            self.config["target"]["stellar_radius_solar"],
        )
        self.assertTrue(result["sequence_matches_abacad"])
        self.assertTrue(result["medium_qualified"])
        self.assertTrue(result["fully_followup_capable"])
        self.assertEqual(len(result["pair_conjunctions"]), 2)
        self.assertTrue(all(item["conjunction"]["corner_evaluation_count"] == 81 for item in result["pair_conjunctions"]))

    def test_selection_uses_best_pair_after_htr_priority(self):
        def cadence(url: str, htr: bool, values: list[float]) -> dict:
            return {
                "cadence_url": url,
                "medium_qualified": True,
                "fully_followup_capable": htr,
                "sources": [],
                "pair_conjunctions": [
                    {
                        "planet_pair": ["d", "b"],
                        "conjunction": {
                            "nominal_projected_separation_stellar_radii": values[0],
                            "reference_bjd_utc_approximation": 2459000.0,
                        },
                    },
                    {
                        "planet_pair": ["b", "c"],
                        "conjunction": {
                            "nominal_projected_separation_stellar_radii": values[1],
                            "reference_bjd_utc_approximation": 2459000.0,
                        },
                    },
                ],
            }
        selected = LS3B.select_cadence_pair(
            [cadence("https://example/no-htr", False, [0.01, 0.02]), cadence("https://example/htr", True, [2.0, 1.0])]
        )
        assert selected is not None
        self.assertEqual(selected["cadence_url"], "https://example/htr")
        self.assertEqual(selected["planet_pair"], ["b", "c"])


if __name__ == "__main__":
    unittest.main()
