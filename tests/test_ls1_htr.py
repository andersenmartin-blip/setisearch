"""Tests for LS1's separately frozen high-time-resolution follow-up."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from seti_repeater.light_sail_htr import compare_on_off, evaluate_timeseries


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls1_htr_followup.json"


class LS1HTRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_followup_is_exactly_stage1_conditioned_and_claim_closed(self):
        self.assertTrue(self.config["stage1"]["followup_authorized"])
        self.assertTrue(self.config["freeze_boundary"]["post_stage1_candidate_conditioning"])
        self.assertFalse(self.config["freeze_boundary"]["htr_values_read_before_freeze"])
        self.assertEqual(len(self.config["candidates"]), 2)
        self.assertEqual(
            {item["on_label"] for item in self.config["candidates"]}, {"A1"}
        )
        self.assertFalse(self.config["claim_boundary"]["technosignature_claimed"])
        self.assertFalse(
            self.config["claim_boundary"]["raw_spectral_payload_may_be_published"]
        )

    def test_synthetic_envelope_and_pulses_pass(self):
        generator = np.random.default_rng(4)
        dt = 0.001
        count = 80_000
        on = generator.normal(10.0, 1.0, count)
        off = generator.normal(10.0, 1.0, count)
        on[20_000:50_000] += 0.3
        for center in range(20_050, 50_000, 100):
            on[center : center + 5] += 6.0
        kwargs = {
            "sample_time_s": dt,
            "envelope_start_s": 20.0,
            "envelope_stop_s": 50.0,
            "pulse_width_s": [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0],
            "reference_guard_s": 2.0,
            "pulse_score_threshold": 8.0,
        }
        comparison = compare_on_off(
            evaluate_timeseries(on, **kwargs),
            evaluate_timeseries(off, **kwargs),
            envelope_on_threshold=8.0,
            envelope_off_veto_threshold=6.0,
            pulse_score_threshold=8.0,
            minimum_on_off_pulse_margin=2.0,
            required_subsecond_scales=2,
        )
        self.assertTrue(comparison["htr_envelope_confirmed"])
        self.assertTrue(comparison["diffraction_structure_supported"])

    def test_adjacent_off_envelope_veto_fails_closed(self):
        generator = np.random.default_rng(9)
        on = generator.normal(0.0, 1.0, 50_000)
        off = generator.normal(0.0, 1.0, 50_000)
        on[10_000:30_000] += 1.0
        off[10_000:30_000] += 1.0
        kwargs = {
            "sample_time_s": 0.001,
            "envelope_start_s": 10.0,
            "envelope_stop_s": 30.0,
            "pulse_width_s": [0.01, 0.1, 1.0],
            "reference_guard_s": 1.0,
            "pulse_score_threshold": 8.0,
        }
        comparison = compare_on_off(
            evaluate_timeseries(on, **kwargs),
            evaluate_timeseries(off, **kwargs),
            envelope_on_threshold=8.0,
            envelope_off_veto_threshold=6.0,
            pulse_score_threshold=8.0,
            minimum_on_off_pulse_margin=2.0,
            required_subsecond_scales=2,
        )
        self.assertTrue(comparison["adjacent_off_htr_veto"])
        self.assertFalse(comparison["htr_envelope_confirmed"])


if __name__ == "__main__":
    unittest.main()
