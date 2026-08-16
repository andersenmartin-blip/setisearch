import unittest

import numpy as np

from seti_repeater.cli import run_synthetic_validation
from seti_repeater.candidates import (
    apply_candidate_flags, build_single_epoch_rfi_mask, cluster_peaks,
    detect_arithmetic_frequency_families,
)
from seti_repeater.diagnostics import acceleration_smearing, leakage_summary
from seti_repeater.search import empirical_p, make_subsets, scramble_maxima, search_bank
from seti_repeater.spectral import make_spectral_bank, normalized_boxcar


class PipelineTests(unittest.TestCase):
    def test_known_answer(self):
        self.assertTrue(run_synthetic_validation()["passed"])

    def test_loss_models(self):
        leakage = leakage_summary()
        self.assertAlmostEqual(leakage["worst_retained_fraction_half_bin"], (2 / np.pi) ** 2, places=6)
        smear = acceleration_smearing(1.0, 16.777216, 3.814697265625)
        self.assertGreater(smear["bins_crossed_per_integration"], 4.0)
        self.assertLess(smear["approx_peak_retained_fraction"], 0.25)

    def test_scramble_is_deterministic(self):
        rng = np.random.default_rng(7)
        banks = {"a": rng.normal(size=(3, 3, 1024)).astype(np.float32)}
        subsets = make_subsets(3)
        first, _ = scramble_maxima(banks, subsets, 8, seed=4, min_shift_bins=64)
        second, _ = scramble_maxima(banks, subsets, 8, seed=4, min_shift_bins=64)
        np.testing.assert_array_equal(first, second)
        self.assertGreaterEqual(empirical_p(float(first.max()), first), 1 / 9)

    def test_boxcar_has_unit_noise_norm(self):
        impulse = np.zeros(101, dtype=np.float32)
        impulse[50] = 1.0
        filtered = normalized_boxcar(impulse, 5)
        self.assertAlmostEqual(float(np.nansum(filtered**2)), 1.0, places=6)

    def test_spectral_bank_recovers_five_channel_shape(self):
        vectors = np.zeros((1, 3, 101), dtype=np.float32)
        vectors[0, 0, 48:53] = 1.0
        vectors[0, 2, 48:53] = 1.0
        bank = make_spectral_bank(vectors, (1, 3, 5, 9))
        peaks = [float(np.nanmax(bank[index, 0, 0])) for index in range(4)]
        self.assertEqual(int(np.argmax(peaks)), 2)

    def test_candidate_clustering_and_family_flags(self):
        records = []
        for frequency, template in ((1400.0, 0), (1400.000010, 1), (1400.001, 0), (1400.002, 0)):
            records.append({
                "snr": 8.0 - template / 10,
                "frequency_mhz": frequency,
                "frequency_index": 1,
                "spectral_width_channels": 3,
                "spectral_width_index": 1,
                "template_index": template,
                "projected_scale": 0.0,
                "phase_offset_cycles": 0.0,
                "active_epochs_zero_based": [0, 2],
                "epoch_values_at_frequency": [4.0, 0.0, 4.0],
            })
        clusters = cluster_peaks(records, tolerance_hz=20.0)
        self.assertEqual(len(clusters), 3)
        families = detect_arithmetic_frequency_families(clusters, tolerance_hz=20.0)
        self.assertTrue(families)
        for cluster in clusters:
            cluster["off_at_best_hypothesis_snr"] = 0.0
        apply_candidate_flags(clusters, families, operational_threshold=7.0, template_multiplicity_flag=8)
        self.assertTrue(any("arithmetic_frequency_family" in item["flags"] for item in clusters))

    def test_recurrence_guard_rejects_one_epoch_spike(self):
        vectors = np.zeros((1, 3, 101), dtype=np.float32)
        vectors[0, 0, 50] = 100.0
        vectors[0, 2, 50] = 1.0
        vectors[0, 0, 60] = 6.0
        vectors[0, 2, 60] = 6.0
        best = search_bank(
            vectors, np.arange(101, dtype=float), [(0.0, 0.0)],
            [(0, 2)], minimum_active_epoch_snr=3.0,
        )
        self.assertEqual(best["frequency_index"], 60)

    def test_single_epoch_rfi_mask_tracks_only_dominant_epoch(self):
        bank = np.zeros((4, 2, 3, 101), dtype=np.float32)
        bank[:, 0, 1, 50] = 12.0
        bank[:, 1, 0, 70] = 12.0
        bank[:, 1, 2, 70] = 4.0
        mask = build_single_epoch_rfi_mask(bank, 10.0, 3.0, 2)
        self.assertEqual(mask.shape, bank.shape)
        self.assertTrue(np.all(mask[:, 0, 1, 48:53]))
        self.assertFalse(np.any(mask[:, 0, 0, 48:53]))
        self.assertFalse(np.any(mask[:, 1, :, 68:73]))


if __name__ == "__main__":
    unittest.main()
