"""Tests for the separate LS1 light-sail leakage search track."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np

from seti_repeater.light_sail import (
    CircularTransitPlanet,
    apply_abacad_veto,
    rank_cadences,
    search_broadband_events,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls1_hd219134_light_sail.json"
RANK_SCRIPT = ROOT / "scripts/ls1_conjunction_rank.py"
SPEC = importlib.util.spec_from_file_location("ls1_rank", RANK_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RANK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RANK)


class LS1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_claim_and_spectral_boundaries_are_closed(self):
        boundary = self.config["freeze_boundary"]
        self.assertFalse(boundary["medium_resolution_values_read_before_freeze"])
        self.assertFalse(boundary["high_time_resolution_values_read_before_freeze"])
        claims = self.config["claim_boundary"]
        self.assertFalse(claims["first_power_beaming_search_claimed"])
        self.assertFalse(claims["calibrated_false_alarm_claimed"])
        self.assertFalse(claims["technosignature_claimed"])
        self.assertFalse(claims["raw_spectral_payload_may_be_published"])

    def test_metadata_only_ranking_reproduces_selected_cadence(self):
        result = RANK.build_ranking(
            self.config,
            ROOT / self.config["archive_inventory"]["source_path"],
        )
        self.assertEqual(result["status"], "complete-metadata-only-ranking")
        self.assertEqual(result["selected_cadence_id"], "--63424")
        self.assertEqual(
            [item["cadence_id"] for item in result["ranking"]],
            ["--63424", "--67073", "--67169", "--65393", "--66869"],
        )
        self.assertAlmostEqual(
            result["ranking"][0]["projected_pair_separation_stellar_radii"],
            6.255883,
            places=5,
        )
        self.assertFalse(result["spectral_dataset_values_read"])

    def test_rank_tie_break_is_deterministic(self):
        planet = CircularTransitPlanet("p", 2.0, 2450000.0, 0.1)
        cadences = [
            {"cadence_id": "b", "first_on_tstart_mjd": 50000.0, "first_on_duration_s": 10.0},
            {"cadence_id": "a", "first_on_tstart_mjd": 50000.0, "first_on_duration_s": 10.0},
        ]
        ranked = rank_cadences(cadences, planet, planet, 1.0)
        self.assertEqual([item["cadence_id"] for item in ranked], ["a", "b"])

    def test_synthetic_broadband_envelope_is_recovered(self):
        generator = np.random.default_rng(13)
        data = generator.normal(20.0, 1.0, size=(128, 1024)).astype(np.float32)
        data[48:72, 320:576] += np.float32(5.0)
        frequency = np.linspace(1100.0, 1200.0, 1024, endpoint=False)
        result = search_broadband_events(
            data,
            frequency,
            1.0,
            base_bin_channels=16,
            spectral_width_bins=(1, 4, 8, 16),
            duration_s=(4.0, 8.0, 16.0, 24.0, 32.0),
            minimum_score=6.0,
            maximum_events=128,
        )
        self.assertTrue(result["events"])
        best = result["events"][0]
        self.assertLessEqual(best["time_start_s"], 52.0)
        self.assertGreaterEqual(best["time_stop_s"], 68.0)
        self.assertLess(best["frequency_start_mhz"], 1140.0)
        self.assertGreater(best["frequency_stop_mhz"], 1130.0)
        self.assertFalse(result["retention_truncated"])

    def test_adjacent_off_coincidence_veto(self):
        event = {
            "score": 10.0,
            "frequency_start_mhz": 1200.0,
            "frequency_stop_mhz": 1220.0,
            "time_start_s": 10.0,
            "time_stop_s": 30.0,
        }
        off_event = {**event, "score": 7.0, "time_start_s": 100.0, "time_stop_s": 120.0}
        scans = [
            {
                "label": "A1",
                "role": "ON",
                "adjacent_off_labels": ["B1"],
                "search": {"events": [event]},
            },
            {
                "label": "B1",
                "role": "OFF",
                "adjacent_off_labels": [],
                "search": {"events": [off_event]},
            },
        ]
        candidates = apply_abacad_veto(
            scans,
            on_threshold=8.0,
            off_threshold=6.0,
            minimum_frequency_overlap=0.5,
        )
        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0]["survives_adjacent_off_veto"])


if __name__ == "__main__":
    unittest.main()
