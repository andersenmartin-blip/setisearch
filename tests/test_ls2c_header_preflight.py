"""Tests for the HD 260655 LS2C header-only preflight."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls2c_hd260655_header_preflight.json"
SCRIPT = ROOT / "scripts/ls2c_header_preflight.py"
SPEC = importlib.util.spec_from_file_location("ls2c_header_preflight", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
LS2C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LS2C)


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


class LS2CHeaderPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_boundary_forbids_dataset_values_and_search(self):
        boundary = self.config["data_boundary"]
        self.assertTrue(boundary["hdf5_structure_and_attributes_may_be_read"])
        self.assertFalse(boundary["hdf5_data_dataset_may_be_indexed"])
        self.assertFalse(boundary["spectral_dataset_values_may_be_read"])
        self.assertFalse(self.config["claim_boundary"]["search_authorized"])

    def test_uncertainty_diagnostic_evaluates_all_corners(self):
        first = {
            "pl_name": "b",
            "pl_orbper": 2.0,
            "pl_orbpererr1": 0.01,
            "pl_orbpererr2": -0.01,
            "pl_tranmid": 2459000.0,
            "pl_tranmiderr1": 0.02,
            "pl_tranmiderr2": -0.02,
            "pl_orbsmax": 0.03,
        }
        second = {
            "pl_name": "c",
            "pl_orbper": 5.0,
            "pl_orbpererr1": 0.02,
            "pl_orbpererr2": -0.02,
            "pl_tranmid": 2459001.0,
            "pl_tranmiderr1": 0.03,
            "pl_tranmiderr2": -0.03,
            "pl_orbsmax": 0.05,
        }
        result = LS2C.ephemeris_uncertainty_metrics(
            2459100.0, first, second, 0.5
        )
        self.assertEqual(result["corner_evaluation_count"], 81)
        self.assertLessEqual(
            result["one_sigma_input_corner_separation_min_stellar_radii"],
            result["nominal_projected_separation_stellar_radii"],
        )
        self.assertGreaterEqual(
            result["one_sigma_input_corner_separation_max_stellar_radii"],
            result["nominal_projected_separation_stellar_radii"],
        )

    def test_header_gate_recognizes_abacad_and_full_htr(self):
        sources = ["HIP31635", "HIP30393", "Hip31635", "HIP30446", "HIP31635", "HIP30487"]
        scans = []
        headers = {}
        for index, source in enumerate(sources):
            medium_url = f"https://example/_{index:04d}.gpuspec.0002.h5"
            htr_url = f"https://example/_{index:04d}.gpuspec.8.0001.h5"
            scans.append(
                {
                    "scan_key": f"{index:04d}",
                    "medium_url": medium_url,
                    "htr_url": htr_url,
                }
            )
            headers[medium_url] = header(source, 57645.0 + index / 1000.0)
            headers[htr_url] = header(source, 57645.0 + index / 1000.0, tsamp=0.00035)
        geometry = {
            "stellar_radius_solar": 0.439,
            "eligible_planets": [
                {
                    "pl_name": "HD 260655 b",
                    "pl_orbper": 2.76953,
                    "pl_orbpererr1": 0.00003,
                    "pl_orbpererr2": -0.00003,
                    "pl_tranmid": 2459497.9102,
                    "pl_tranmiderr1": 0.0003,
                    "pl_tranmiderr2": -0.0003,
                    "pl_orbsmax": 0.02933,
                },
                {
                    "pl_name": "HD 260655 c",
                    "pl_orbper": 5.70588,
                    "pl_orbpererr1": 0.00007,
                    "pl_orbpererr2": -0.00007,
                    "pl_tranmid": 2459490.3646,
                    "pl_tranmiderr1": 0.0004,
                    "pl_tranmiderr2": -0.0004,
                    "pl_orbsmax": 0.04749,
                },
            ],
        }
        result = LS2C.qualify_cadence(
            {"cadence_url": "https://example/cadence", "scans": scans},
            headers,
            "HIP31635",
            self.config["header_criteria"],
            geometry,
        )
        self.assertTrue(result["sequence_matches_abacad"])
        self.assertTrue(result["medium_qualified"])
        self.assertTrue(result["fully_followup_capable"])
        self.assertIsNotNone(result["conjunction"])

    def test_selection_prefers_full_htr_before_smaller_separation(self):
        incomplete = {
            "cadence_url": "https://example/incomplete",
            "medium_qualified": True,
            "fully_followup_capable": False,
            "sources": [],
            "conjunction": {
                "nominal_projected_separation_stellar_radii": 0.1,
                "reference_bjd_utc_approximation": 2459000.0,
            },
        }
        complete = {
            "cadence_url": "https://example/complete",
            "medium_qualified": True,
            "fully_followup_capable": True,
            "sources": [],
            "conjunction": {
                "nominal_projected_separation_stellar_radii": 2.0,
                "reference_bjd_utc_approximation": 2459001.0,
            },
        }
        selected = LS2C.select_cadence([incomplete, complete])
        assert selected is not None
        self.assertEqual(selected["cadence_url"], "https://example/complete")


if __name__ == "__main__":
    unittest.main()
