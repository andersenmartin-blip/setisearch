"""Tests for the frozen Milestone 36 exhaustive retention supplement."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
from astropy.time import Time

from seti_repeater.candidates import (
    build_receiver_frame_signature,
    collect_hypothesis_peaks,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "m36_exhaustive_retention_audit.py"
SPEC = importlib.util.spec_from_file_location("m36_exhaustive_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class ExhaustiveNmsTests(unittest.TestCase):
    @staticmethod
    def bank_from_scores(scores: np.ndarray, width: int = 1) -> np.ndarray:
        values = np.asarray(scores, dtype=np.float32) / np.sqrt(2.0)
        bank = np.zeros((1, 1, 3, values.size), dtype=np.float32)
        bank[0, 0, 0] = values
        bank[0, 0, 1] = values
        return bank

    def test_four_separated_peaks_exposes_top_three_stop(self):
        scores = np.zeros(128, dtype=np.float32)
        scores[[10, 40, 70, 100]] = [20.0, 19.0, 18.0, 17.0]
        bank = self.bank_from_scores(scores)
        rest = 1400.0 + np.arange(scores.size) * 1e-6
        old = collect_hypothesis_peaks(
            bank,
            rest,
            [(0.0, 0.0)],
            [(0, 1)],
            (1,),
            3,
            5.5,
            None,
            "minimum_epoch",
            None,
        )
        rebuilt_scores = AUDIT.stack_hypothesis(
            bank, 0, 0, (0, 1), None, "minimum_epoch", None
        )
        eligible, selected, owners = AUDIT.greedy_cover(
            rebuilt_scores, 15.0, 1
        )
        self.assertEqual(len(old), 3)
        self.assertEqual(selected.tolist(), [10, 40, 70, 100])
        self.assertEqual(eligible.tolist(), [10, 40, 70, 100])
        self.assertTrue(np.array_equal(eligible, owners))

    def test_rank_sixteen_peak_exposes_wide_pool_blind_spot(self):
        scores = np.zeros(220, dtype=np.float32)
        crowded = [57] + [index for index in range(50, 65) if index != 57]
        for offset, index in enumerate(crowded):
            scores[index] = 40.0 - offset
        scores[150] = 25.0
        bank = self.bank_from_scores(scores, width=17)
        rest = 1400.0 + np.arange(scores.size) * 1e-6
        old = collect_hypothesis_peaks(
            bank,
            rest,
            [(0.0, 0.0)],
            [(0, 1)],
            (17,),
            3,
            5.5,
            None,
            "minimum_epoch",
            None,
        )
        rebuilt_scores = AUDIT.stack_hypothesis(
            bank, 0, 0, (0, 1), None, "minimum_epoch", None
        )
        _, selected, _ = AUDIT.greedy_cover(rebuilt_scores, 15.0, 8)
        self.assertEqual([item["frequency_index"] for item in old], [57])
        self.assertIn(150, selected.tolist())
        self.assertGreaterEqual(len(selected), 2)

    def test_ties_use_ascending_frequency_index(self):
        scores = np.zeros(12, dtype=np.float32)
        scores[[9, 5, 1]] = 20.0
        _, selected, _ = AUDIT.greedy_cover(scores, 15.0, 1)
        self.assertEqual(selected.tolist(), [1, 5, 9])

    def test_literal_twenty_hz_boundary_is_seven_not_eight_channels(self):
        df_hz = 2.7939677238464355
        rest = 1400.0 + np.arange(64) * df_hz / 1e6
        radius = AUDIT.literal_tolerance_bins(rest, 20.0)
        self.assertEqual(radius, 7)
        scores = np.zeros(64, dtype=np.float32)
        scores[[20, 27, 28]] = [30.0, 20.0, 19.0]
        eligible, selected, owners = AUDIT.greedy_cover(scores, 15.0, radius)
        owner = dict(zip(eligible.tolist(), owners.tolist()))
        self.assertEqual(selected.tolist(), [20, 28])
        self.assertEqual(owner[27], 20)
        self.assertEqual(owner[28], 28)

    def test_minimum_epoch_floor_and_moving_mask_match_primary_semantics(self):
        bank = np.zeros((1, 1, 3, 6), dtype=np.float32)
        bank[0, 0, 0] = [4, 4, 4, 2, 5, 5]
        bank[0, 0, 1] = [4, 2, 4, 5, 5, 5]
        mask = np.zeros_like(bank, dtype=bool)
        mask[0, 0, 0, 2] = True
        stack = AUDIT.stack_hypothesis(
            bank, 0, 0, (0, 1), 3.0, "minimum_epoch", mask
        )
        self.assertTrue(np.isfinite(stack[0]))
        self.assertLess(stack[1], 0)
        self.assertLess(stack[2], 0)
        self.assertLess(stack[3], 0)
        self.assertTrue(np.isfinite(stack[4]))

    def test_coverage_owner_is_stronger_and_within_radius_at_edges(self):
        scores = np.zeros(10, dtype=np.float32)
        scores[[0, 1, 2, 9]] = [10, 9, 8, 7]
        eligible, selected, owners = AUDIT.greedy_cover(scores, 7.0, 2)
        self.assertEqual(selected.tolist(), [0, 9])
        for index, owner in zip(eligible, owners):
            self.assertLessEqual(abs(int(index) - int(owner)), 2)
            self.assertGreaterEqual(float(scores[owner]), float(scores[index]))


class AuditEvidenceTests(unittest.TestCase):
    @staticmethod
    def record(index: int, frequency_mhz: float) -> dict:
        return {
            "audit_record_id": f"r{index}",
            "snr": float(1000 - index),
            "frequency_mhz": frequency_mhz,
            "frequency_index": index,
            "spectral_width_channels": 1,
            "spectral_width_index": 0,
            "template_index": 0,
            "projected_scale": 0.0,
            "phase_offset_cycles": 0.0,
            "active_epochs_zero_based": [0, 1],
        }

    def test_full_cluster_member_ledger_is_not_top_twenty_truncated(self):
        records = [self.record(index, 1400.0) for index in range(25)]
        clusters = AUDIT.cluster_all_records(records, 20.0)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["member_count"], 25)
        self.assertEqual(len(clusters[0]["member_ids"]), 25)

    def test_more_than_2200_clusters_are_never_report_capped(self):
        records = [
            self.record(index, 1400.0 + index * 30.0 / 1e6)
            for index in range(2201)
        ]
        clusters = AUDIT.cluster_all_records(records, 20.0)
        self.assertEqual(len(clusters), 2201)

    def test_rounded_local_veto_cannot_close_literal_twenty_hz_ledger(self):
        base = {
            "audit_operational_threshold_snr": 15.0,
            "off_at_same_hypothesis_snr": 1.0,
            "receiver_frame_alias_witness": None,
            "v0p5_rounded_local_off_diagnostics": {
                "best_local_recurrence": {"snr": 16.0},
                "same_candidate_track": {
                    "matching_active_epochs_zero_based": []
                },
            },
            "literal_20hz_local_off_diagnostics": {
                "best_local_recurrence": {"snr": 14.0},
                "same_candidate_track": {
                    "matching_active_epochs_zero_based": []
                },
            },
        }
        self.assertEqual(
            AUDIT.disposition_for_record(base, literal=False),
            "rfi_veto_local_off_source",
        )
        self.assertEqual(
            AUDIT.disposition_for_record(base, literal=True),
            "survives_for_followup",
        )

    def test_member_level_veto_mechanisms_and_fail_closed_survivor(self):
        def base():
            return {
                "audit_operational_threshold_snr": 15.0,
                "off_at_same_hypothesis_snr": 1.0,
                "receiver_frame_alias_witness": None,
                "v0p5_rounded_local_off_diagnostics": {
                    "best_local_recurrence": {"snr": 1.0},
                    "same_candidate_track": {
                        "matching_active_epochs_zero_based": []
                    },
                },
                "literal_20hz_local_off_diagnostics": {
                    "best_local_recurrence": {"snr": 1.0},
                    "same_candidate_track": {
                        "matching_active_epochs_zero_based": []
                    },
                },
            }

        exact = base()
        exact["off_at_same_hypothesis_snr"] = 15.0
        self.assertEqual(
            AUDIT.disposition_for_record(exact, literal=True),
            "rfi_veto_off_source",
        )
        single = base()
        single["literal_20hz_local_off_diagnostics"]["same_candidate_track"][
            "matching_active_epochs_zero_based"
        ] = [0]
        self.assertEqual(
            AUDIT.disposition_for_record(single, literal=True),
            "rfi_veto_single_adjacent_off",
        )
        alias = base()
        alias["receiver_frame_alias_witness"] = {"other_record_id": "x"}
        self.assertEqual(
            AUDIT.disposition_for_record(alias, literal=True),
            "rfi_veto_receiver_frame_alias",
        )
        self.assertEqual(
            AUDIT.disposition_for_record(base(), literal=True),
            "survives_for_followup",
        )

    def test_receiver_alias_requires_two_qualified_shared_epochs(self):
        left = {
            "receiver_frame_signature": [
                {
                    "epoch_zero_based": epoch,
                    "peak_frequency_mhz": 1400.0 + epoch * 1e-6,
                    "peak_snr": 8.0,
                }
                for epoch in (0, 1)
            ]
        }
        right = {
            "receiver_frame_signature": [
                {
                    "epoch_zero_based": epoch,
                    "peak_frequency_mhz": 1400.0 + epoch * 1e-6 + 10e-6,
                    "peak_snr": 9.0,
                }
                for epoch in (0, 1)
            ]
        }
        matches = AUDIT.receiver_alias_matches(left, right, 20.0, 2, 5.5)
        self.assertEqual(len(matches), 2)
        right["receiver_frame_signature"][1]["peak_snr"] = 5.0
        self.assertEqual(
            AUDIT.receiver_alias_matches(left, right, 20.0, 2, 5.5), []
        )

    def test_bucketed_receiver_alias_assigns_only_cross_cluster_witnesses(self):
        records = []
        for index, offset_hz in enumerate((0.0, 5.0, 10.0)):
            records.append(
                {
                    "audit_record_id": f"r{index}",
                    "receiver_frame_signature": [
                        {
                            "epoch_zero_based": epoch,
                            "peak_frequency_mhz": (
                                1400.0 + epoch * 1e-6 + offset_hz / 1e6
                            ),
                            "peak_snr": 8.0,
                        }
                        for epoch in (0, 1)
                    ],
                }
            )
        cluster_by_member = {"r0": 0, "r1": 0, "r2": 1}
        AUDIT.assign_receiver_alias_witnesses(
            records, cluster_by_member, 20.0, 2, 5.5
        )
        self.assertEqual(records[0]["receiver_frame_alias_witness"]["other_record_id"], "r2")
        self.assertEqual(records[1]["receiver_frame_alias_witness"]["other_record_id"], "r2")
        self.assertIn(
            records[2]["receiver_frame_alias_witness"]["other_record_id"],
            {"r0", "r1"},
        )

    def test_indexed_receiver_signature_equals_frozen_full_mask(self):
        config = json.loads(
            (ROOT / "config" / "hip48714b_heldout_m36.json").read_text()
        )
        candidate = {
            "best_hypothesis": {
                "frequency_mhz": 1400.0,
                "projected_scale": 0.0,
                "phase_offset_cycles": 0.0,
                "spectral_width_channels": 3,
                "active_epochs_zero_based": [0, 2],
            }
        }
        times = Time([57619.7, 57619.7001], format="mjd", scale="utc")
        rng = np.random.default_rng(3620260826)

        def factor(scan_times, *_args):
            size = len(scan_times)
            return np.ones(size), np.zeros(size), np.zeros(size)

        for descending in (False, True):
            frequencies = 1399.9998 + np.arange(201) * 2.0 / 1e6
            if descending:
                frequencies = frequencies[::-1]
            scans = [
                {
                    "times": times,
                    "frequency_mhz": frequencies,
                    "normalized": rng.normal(size=(2, frequencies.size)).astype(
                        np.float32
                    ),
                }
                for _ in range(3)
            ]
            with mock.patch(
                "seti_repeater.orbit.celestial_frequency_factor",
                side_effect=factor,
            ):
                frozen = build_receiver_frame_signature(
                    candidate, scans, config, 100.0
                )
                indexed = AUDIT.build_receiver_frame_signature_indexed(
                    candidate, scans, config, 100.0
                )
            self.assertEqual(indexed, frozen)

    def test_indexed_local_frequency_window_matches_full_boolean_mask(self):
        for descending in (False, True):
            frequencies = 1400.0 + np.arange(301) * 2.7939677238464355 / 1e6
            if descending:
                frequencies = frequencies[::-1]
            for center in (
                float(frequencies[0]),
                float(frequencies[150]),
                float(frequencies[-1]),
                1400.000123456,
            ):
                expected = np.flatnonzero(
                    np.abs((frequencies - center) * 1e6) <= 100.0
                )
                actual = AUDIT.local_frequency_indices(
                    frequencies, center, 100.0
                )
                self.assertTrue(np.array_equal(actual, expected))

    def test_deterministic_gzip_jsonl(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / name for name in ("a.gz", "b.gz")]
            for path in paths:
                with AUDIT.DeterministicGzipJsonl(path) as writer:
                    writer.write({"z": 1, "a": [2, 3]})
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())


class SummaryOnlyInventoryTests(unittest.TestCase):
    def test_detector_import_is_bound_to_current_repository(self):
        AUDIT.verify_imported_detector("0.5.0")

    def test_frozen_inventory_reproduces_exactly(self):
        summary_path = ROOT / "results_m36" / "search_summary.json"
        expected_path = ROOT / "MILESTONE_36_RETENTION_BOUND.json"
        raw = summary_path.read_bytes()
        inventory = AUDIT.build_summary_only_inventory(json.loads(raw))
        inventory["source"]["search_summary_sha256"] = hashlib.sha256(raw).hexdigest()
        actual = AUDIT.canonical_json_bytes(inventory)
        self.assertEqual(actual, expected_path.read_bytes())
        self.assertEqual(
            hashlib.sha256(actual).hexdigest(),
            "35fd0d940dd73af6c49b274e686fa0230bfb756427f6473b76f93107d2a8e3f3",
        )
        self.assertEqual(inventory["counts"]["total_hypotheses"], 3360)
        self.assertEqual(inventory["counts"]["unresolved_total"], 195)
        self.assertEqual(
            inventory["canonical_tuple_csv_sha256"],
            "8d9504a3845f4f80d9d4e51187d1c4ef009d7d8579cab0d4d8bb4d8521d86a13",
        )


if __name__ == "__main__":
    unittest.main()
