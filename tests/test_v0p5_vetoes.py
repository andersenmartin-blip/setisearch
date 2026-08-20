import unittest

import numpy as np

from seti_repeater.candidates import (
    apply_candidate_flags,
    evaluate_local_off_veto,
    flag_receiver_frame_aliases,
)


def candidate(frequency_index=50, frequency_mhz=1400.000050, template_index=0):
    best = {
        "snr": 10.0,
        "frequency_mhz": frequency_mhz,
        "frequency_index": frequency_index,
        "spectral_width_channels": 1,
        "spectral_width_index": 0,
        "template_index": template_index,
        "projected_scale": float(template_index),
        "phase_offset_cycles": 0.0,
        "active_epochs_zero_based": [0, 2],
    }
    return {
        "cluster_frequency_mhz": frequency_mhz,
        "max_snr": 10.0,
        "distinct_template_count": 1,
        "best_hypothesis": best,
        "off_at_best_hypothesis_snr": 0.0,
    }


class V0p5VetoTests(unittest.TestCase):
    def setUp(self):
        self.frequencies = 1400.0 + np.arange(101) * 1e-6
        self.templates = [(0.0, 0.0), (1.0, 0.0)]
        self.subsets = [(0, 1), (0, 2), (1, 2), (0, 1, 2)]
        self.widths = (1, 3)

    def test_local_off_search_catches_different_hypothesis(self):
        bank = np.zeros((2, 2, 3, 101), dtype=np.float32)
        bank[1, 1, 0, 53] = 6.0
        bank[1, 1, 2, 53] = 6.0
        cluster = candidate()
        cluster["v0p5_off_diagnostics"] = evaluate_local_off_veto(
            bank, self.frequencies, cluster, self.templates, self.subsets,
            self.widths, tolerance_hz=20.0, single_epoch_snr_floor=5.5,
            minimum_active_epoch_snr=3.0,
        )
        apply_candidate_flags([cluster], [], 8.0, 8)
        best = cluster["v0p5_off_diagnostics"]["best_local_recurrence"]
        self.assertEqual(best["frequency_index"], 53)
        self.assertEqual(best["template_index"], 1)
        self.assertEqual(best["spectral_width_channels"], 3)
        self.assertEqual(cluster["disposition"], "rfi_veto_local_off_source")

    def test_single_adjacent_off_track_is_independent_of_recurrence(self):
        bank = np.zeros((2, 2, 3, 101), dtype=np.float32)
        bank[0, 0, 0, 50] = 6.0
        cluster = candidate()
        cluster["v0p5_off_diagnostics"] = evaluate_local_off_veto(
            bank, self.frequencies, cluster, self.templates, self.subsets,
            self.widths, tolerance_hz=20.0, single_epoch_snr_floor=5.5,
            minimum_active_epoch_snr=3.0,
        )
        apply_candidate_flags([cluster], [], 8.0, 8)
        same = cluster["v0p5_off_diagnostics"]["same_candidate_track"]
        self.assertEqual(same["matching_active_epochs_zero_based"], [0])
        self.assertEqual(cluster["disposition"], "rfi_veto_single_adjacent_off")

    def test_receiver_alias_requires_two_strong_shared_epochs(self):
        left = candidate(frequency_mhz=1400.1, template_index=0)
        right = candidate(frequency_mhz=1400.2, template_index=1)
        left["v0p5_receiver_frame_signature"] = [
            {"epoch_zero_based": 0, "peak_frequency_mhz": 1420.000000, "peak_snr": 8.0},
            {"epoch_zero_based": 2, "peak_frequency_mhz": 1420.000010, "peak_snr": 7.0},
        ]
        right["v0p5_receiver_frame_signature"] = [
            {"epoch_zero_based": 0, "peak_frequency_mhz": 1420.000011, "peak_snr": 9.0},
            {"epoch_zero_based": 2, "peak_frequency_mhz": 1420.000019, "peak_snr": 6.0},
        ]
        clusters = [left, right]
        flag_receiver_frame_aliases(clusters, 20.0, 2, 5.5)
        for cluster in clusters:
            apply_candidate_flags([cluster], [], 8.0, 8)
            self.assertEqual(cluster["disposition"], "rfi_veto_receiver_frame_alias")
            self.assertEqual(
                len(cluster["v0p5_receiver_frame_aliases"][0]["matched_active_epochs"]), 2
            )

    def test_clean_candidate_remains_for_followup(self):
        bank = np.zeros((2, 2, 3, 101), dtype=np.float32)
        cluster = candidate()
        cluster["v0p5_off_diagnostics"] = evaluate_local_off_veto(
            bank, self.frequencies, cluster, self.templates, self.subsets,
            self.widths, tolerance_hz=20.0, single_epoch_snr_floor=5.5,
            minimum_active_epoch_snr=3.0,
        )
        cluster["v0p5_receiver_frame_aliases"] = []
        apply_candidate_flags([cluster], [], 8.0, 8)
        self.assertEqual(cluster["disposition"], "survives_for_followup")

    def test_labelled_m11_failure_modes_are_all_vetoed(self):
        clusters = [candidate(frequency_mhz=1400.0 + index) for index in range(5)]
        for cluster in clusters:
            cluster["v0p5_off_diagnostics"] = {
                "best_local_recurrence": {"snr": 0.0},
                "same_candidate_track": {"matching_active_epochs_zero_based": []},
            }
            cluster["v0p5_receiver_frame_aliases"] = []
        clusters[0]["v0p5_off_diagnostics"]["best_local_recurrence"]["snr"] = 9.0
        clusters[1]["v0p5_off_diagnostics"]["same_candidate_track"][
            "matching_active_epochs_zero_based"
        ] = [0]
        clusters[2]["v0p5_receiver_frame_aliases"] = [{"other_cluster_index": 3}]
        clusters[3]["v0p5_receiver_frame_aliases"] = [{"other_cluster_index": 2}]
        clusters[4]["v0p5_off_diagnostics"]["same_candidate_track"][
            "matching_active_epochs_zero_based"
        ] = [2]
        apply_candidate_flags(clusters, [], 8.0, 8)
        self.assertTrue(all(item["disposition"].startswith("rfi_veto_") for item in clusters))

    def test_v0p4_cluster_without_new_fields_is_unchanged(self):
        cluster = candidate()
        apply_candidate_flags([cluster], [], 8.0, 8)
        self.assertEqual(cluster["flags"], [])
        self.assertEqual(cluster["disposition"], "survives_for_followup")

    def test_rehydrated_null_off_score_is_not_a_veto(self):
        cluster = candidate()
        cluster["off_at_best_hypothesis_snr"] = None
        apply_candidate_flags([cluster], [], 8.0, 8)
        self.assertEqual(cluster["disposition"], "survives_for_followup")


if __name__ == "__main__":
    unittest.main()
