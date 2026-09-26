"""Changed orchestration boundaries and independent native arithmetic checks."""
import copy
import inspect
from dataclasses import replace
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from seti_repeater import pipeline_radio as radio
from seti_repeater import search_v0p6 as core
from seti_repeater import source_m43h as rows
from radio_pipeline_fixture import panel, context, make_sources, account_truth
from m43g_reference import sorted_reference, direct_reference

ROOT = Path(__file__).resolve().parents[1]


class RadioPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = panel()

    def test_full_native_store_against_independent_oracle(self):
        p = self.p
        c, run, store = p["context"], p["calibration_run"], p["calibration_store"]
        self.assertEqual(len(store.expected_ids), 2*2*8)
        self.assertEqual(len(store.provenance["native_caches"]), 6*8)
        for scan in c.scans:
            label = scan["label"]
            normalized = sorted_reference(p["calibration_raw"][label])
            np.testing.assert_array_equal(normalized.view("<u4"), run.sources[label].values.view("<u4"))
            factors = core.factor_table_for_scan(c.table, c.basis, label)
            for width in core.M37_SPECTRAL_WIDTHS:
                expected = direct_reference(normalized, run.sources[label].geometry, factors, c.grid,
                                            width, 0, c.grid.support_bin_count)
                observed = np.stack([store.get(scan["kind"], t, width)[0][scan["epoch"]-1] for t in range(2)])
                np.testing.assert_array_equal(observed.view("<u4"), expected.view("<u4"))

    def test_receiver_against_direct_native_windows(self):
        run = self.p["calibration_run"]
        c = self.p["context"]
        src = run.sources["epoch1_on"]
        for width in core.M37_SPECTRAL_WIDTHS:
            cache = run.cache("epoch1_on", width)
            for t, q in [(0, 0), (1, c.grid.score_bin_count//2), (1, c.grid.score_bin_count-1)]:
                sig, receipt = radio.synthetic_signature(cache, t, q)
                # Explicit ordered scalar accumulation, independent of the production helper.
                total = 0.
                for f in cache.factors[t]:
                    total += float(c.grid.score_hz[q])*float(f)
                predicted = (total/16)/1e6
                frequencies = (src.geometry.raw_zero_hz + np.arange(src.geometry.channel_count)*src.geometry.channel_width_hz)/1e6
                indices = np.flatnonzero(np.abs((frequencies-predicted)*1e6) <= 100.)
                scores = np.zeros(len(indices), dtype="<f4")
                for row in range(16):
                    windows = src.values[row, indices[:, None]+np.arange(-(width//2), width//2+1)]
                    scores += (np.sum(windows, axis=-1, dtype=np.float32)/np.sqrt(width)).astype("<f4")
                scores /= np.float32(math.sqrt(16))
                winner = int(np.argmax(scores))
                self.assertEqual(sig["predicted_mid_mhz"], predicted)
                self.assertEqual(sig["peak_frequency_mhz"], float(frequencies[indices[winner]]))
                self.assertEqual(sig["peak_snr"], float(scores[winner]))
                self.assertEqual(receipt["winning_raw_index"], int(indices[winner]))

    def test_all_six_cases_complete_and_partition_every_member(self):
        p = self.p
        self.assertEqual(set(p["reports"]), {c["name"] for c in p["config"]["cases"]})
        self.assertTrue(np.isfinite(p["calibration"].accumulator.null_maxima).all())
        for name, result in p["reports"].items():
            d = result["detector"]
            on = {r["record_id"] for r in d["retained"]["on"]}
            members = [rid for c in result["clusters"] for rid in c["member_ids"]]
            self.assertEqual(set(members), on, name)
            self.assertEqual(len(members), len(on), name)
            self.assertEqual(on, {r["record_id"] for r in d["decisions"]})
            self.assertFalse(result["scientific_candidate_selection_authorized"])
            self.assertTrue(result["complete"])
            self.assertEqual(result["calibration_receipt_sha256"], p["calibration"].receipt_sha256)
            self.assertFalse(any(x["scientific_candidate"] for x in d["decisions"]))
        # Structural known-answer assertions; fixture outcomes are all reported separately.
        self.assertGreater(p["outcomes"]["signal_three_epochs"]["all_on_member_count"], 0)
        self.assertGreater(p["outcomes"]["matched_on_off"]["all_off_member_count"], 0)
        dispositions = {r["physical_disposition"] for r in p["reports"]["matched_on_off"]["detector"]["decisions"]}
        self.assertIn("rfi_veto_matched_off_same_hypothesis", dispositions)
        for name in ("signal_three_epochs", "signal_two_epochs_width5"):
            self.assertTrue(p["outcomes"][name]["recovered"])
        for name in ("noise", "matched_on_off", "single_on_epoch", "single_paired_off"):
            self.assertEqual(p["outcomes"][name]["all_final_member_count"], 0)
        self.assertIn("rfi_veto_single_adjacent_off", {
            r["physical_disposition"] for r in p["reports"]["single_paired_off"]["detector"]["decisions"]})

    def test_truth_is_only_post_detection_accounting(self):
        report = self.p["reports"]["signal_three_epochs"]
        before = radio.digest(report)
        wrong = {"template_index": 0, "score_index": 0, "active_epochs": [0, 1]}
        account_truth(report, self.p["context"], wrong)
        self.assertEqual(radio.digest(report), before)
        self.assertEqual(list(inspect.signature(radio.NativeRun.execute).parameters), ["self", "store", "calibration"])

    def test_source_score_and_calibration_mismatches_rejected(self):
        p = self.p
        run, store = p["evaluation_runs"]["noise"]
        with self.assertRaisesRegex(ValueError, "cadence differ"):
            run.execute(p["calibration_store"], p["calibration"])
        changed = copy.deepcopy(p["calibration"].receipt)
        changed["null_maxima"][0] += 1
        bad = replace(p["calibration"], receipt=changed)
        with self.assertRaisesRegex(ValueError, "receipt changed"):
            run.execute(store, bad)
        c = context(p["config"], maximum_records=9999)
        with self.assertRaisesRegex(ValueError, "context or receipt changed"):
            p["calibration"].validate(c)
        sources = dict(run.sources)
        first = sources["epoch1_on"]
        sources["epoch1_on"] = replace(first, values=first.values.copy())
        with self.assertRaisesRegex(ValueError, "identity or payload mismatch"):
            radio.NativeRun.from_synthetic(p["context"], sources)
        corrupt = copy.copy(store)
        corrupt.expected_ids = dict(store.expected_ids)
        corrupt.expected_ids["on", 0, 1] = "0"*64
        with self.assertRaisesRegex(ValueError, "payload changed"):
            run.execute(corrupt, p["calibration"])

    def test_capacity_failure_never_returns_truncated_success(self):
        p = self.p
        c = context(p["config"], maximum_records=1)
        calibration_run = radio.NativeRun.from_synthetic(c, p["calibration_run"].sources)
        store = calibration_run.build_store()
        cfg = p["config"]
        calibration = calibration_run.calibrate(store, shifts=p["calibration"].accumulator.scramble_shifts,
            minimum_shift_bins=cfg["minimum_shift_bins"], reference_floor=cfg["reference_floor"],
            quantile=cfg["quantile"], rank_ceiling=cfg["rank_ceiling"])
        signal = radio.NativeRun.from_synthetic(c, p["evaluation_runs"]["signal_three_epochs"][0].sources)
        with self.assertRaises(core.V0P6CapacityError):
            signal.execute(signal.build_store(), calibration)
        c = context(cfg, memory_limit_bytes=1)
        with self.assertRaises(core.V0P6CapacityError):
            radio.NativeRun.from_synthetic(c, p["calibration_run"].sources)

    def test_hd1461_hold_blocks_before_local_telescope_loading(self):
        path = "config/radio_hd1461_source_preparation_20260926.json"
        with patch.object(radio.telescope, "load_telescope_source", side_effect=AssertionError("row files opened")) as load:
            with self.assertRaisesRegex(ValueError, "source contract blocked"):
                radio.NativeRun.from_telescope(self.p["context"], root=ROOT, contract_path=path,
                                               contract_sha256=rows.file_hash(ROOT/path), receipts={})
            load.assert_not_called()

    def test_empty_conditional_calibration_is_an_explicit_failure(self):
        p = self.p
        run, store = p["evaluation_runs"]["noise"]
        cfg = p["config"]
        with self.assertRaisesRegex(core.V0P6IncompleteError, "maxima are not finite"):
            run.calibrate(store, shifts=p["calibration"].accumulator.scramble_shifts,
                minimum_shift_bins=cfg["minimum_shift_bins"], reference_floor=cfg["reference_floor"],
                quantile=cfg["quantile"], rank_ceiling=cfg["rank_ceiling"])


if __name__ == "__main__":
    unittest.main()
