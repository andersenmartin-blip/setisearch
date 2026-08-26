"""Tests for the M37 detector-v0.6 metadata-only bank preflight."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "hd156668b_m37_v0p6_bank_preflight.json"
SCRIPT_PATH = ROOT / "scripts" / "m37_v0p6_bank_preflight.py"
SPEC = importlib.util.spec_from_file_location("m37_v0p6_bank_preflight", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


class M37V0P6BankResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_cwd = Path.cwd()
        if cls.original_cwd != ROOT:
            import os

            os.chdir(ROOT)
        cls.config = load_config()
        cls.result = PREFLIGHT.check_config(cls.config)

    @classmethod
    def tearDownClass(cls):
        if Path.cwd() != cls.original_cwd:
            import os

            os.chdir(cls.original_cwd)

    def test_metadata_only_boundary_and_summary(self):
        result = self.result
        self.assertTrue(result["passed"])
        for flag in (
            "spectral_payload_inspected",
            "spectral_dataset_values_read",
            "remote_files_opened",
            "telescope_remote_request_made",
            "network_access_required",
            "detector_v0p6_implementation_frozen",
            "spectral_access_authorized",
            "search_sensitivity_claimed",
            "native_raw_filter_implementation_verified",
        ):
            self.assertFalse(result[flag])
        self.assertEqual(result["factor_basis"]["integration_midpoints"], 96)
        self.assertEqual(result["factor_basis"]["scan_count"], 6)
        self.assertEqual(
            result["factor_basis"]["basis_sha256"],
            "492d2fe31d8cbe14968c9ce0296e898f42bf298540310f3f06a74ec8c971c143",
        )
        self.assertLess(
            result["factor_basis"]["maximum_direct_orbit_reconstruction_residual"],
            2e-12,
        )

    def test_bank_identity_order_and_endpoints(self):
        bank = self.result["template_bank"]
        self.assertEqual(bank["count"], 93)
        self.assertEqual(
            bank["canonical_sha256"],
            "8b0c5488944133db9bf500f7ed108971f42ef4d29ce36aa67f9a89ffac3a2d63",
        )
        records = bank["records"]
        self.assertEqual([item["line_index"] for item in records[:7]], [0, 1, -1, 2, -2, 3, -3])
        self.assertEqual([item["line_index"] for item in records[-2:]], [46, -46])
        self.assertEqual(records[0]["projected_scale"], 0.0)
        self.assertAlmostEqual(records[-1]["projected_scale"], 92 / 93)
        np.testing.assert_allclose(
            bank["direction"],
            [-0.6558897197989564, 0.75485672512209],
            rtol=0,
            atol=2e-16,
        )
        self.assertAlmostEqual(float(np.linalg.norm(bank["direction"])), 1.0)

    def test_discrete_lattice_cover_passes_with_margin(self):
        cover = self.result["selected_93_template_discrete_cover"]
        self.assertTrue(cover["passed"])
        self.assertAlmostEqual(cover["minimum_guarded_interval_width_hz"], 4.891987244442117)
        self.assertAlmostEqual(cover["minimum_interval_excess_over_lattice_hz"], 2.0564838259894405)
        self.assertGreater(cover["minimum_upper_grid_headroom_hz"], 3327.4)
        self.assertGreater(cover["minimum_lower_grid_headroom_hz"], 3718.0)
        expected_widths = {
            "m37_1400p5": 8.102064152012531,
            "m37_1406p5": 7.320820827709554,
            "m37_1412p5": 6.539577503406605,
            "m37_1418p5": 5.758334179103656,
            "m37_1425p0": 4.911987244442116,
        }
        for record in cover["records"]:
            self.assertTrue(record["passed"])
            self.assertTrue(record["lattice_point_guaranteed"])
            self.assertTrue(record["finite_grid_containment_guaranteed"])
            self.assertAlmostEqual(
                record["minimum_feasible_interval_width_hz"],
                expected_widths[record["window_id"]],
            )

    def test_smaller_banks_do_not_certify_production_grid(self):
        diagnostic = self.result["smaller_bank_discrete_lattice_diagnostics"]
        self.assertFalse(diagnostic["is_normative"])
        self.assertTrue(diagnostic["all_smaller_counts_fail_at_least_one_window"])
        self.assertEqual(diagnostic["evaluated_counts"], [89, 91])
        statuses = {
            count: {
                item["window_id"]: item["certified_for_discrete_lattice"]
                for item in records
            }
            for count, records in diagnostic["records_by_count"].items()
        }
        self.assertEqual(
            statuses,
            {
                "89": {
                    "m37_1400p5": False,
                    "m37_1406p5": False,
                    "m37_1412p5": False,
                    "m37_1418p5": False,
                    "m37_1425p0": False,
                },
                "91": {
                    "m37_1400p5": True,
                    "m37_1406p5": True,
                    "m37_1412p5": True,
                    "m37_1418p5": False,
                    "m37_1425p0": False,
                },
            },
        )

    def test_spectral_proxy_grid_and_extraction_snapshots(self):
        spectral = self.result["spectral_budget"]
        self.assertEqual(spectral["maximum_width_channels"], 129)
        self.assertEqual(spectral["half_width_channels"], 64)
        self.assertEqual(spectral["composed_nearest_channel_reserve_channels"], 2)
        self.assertAlmostEqual(
            spectral["sampled_endpoint_diagnostic"][
                "maximum_center_to_endpoint_smear_hz"
            ],
            79.05702037789543,
        )
        self.assertAlmostEqual(
            spectral["continuous_integration_smear_bound"][
                "maximum_center_to_any_integration_time_smear_hz"
            ],
            80.53452803677948,
        )
        self.assertAlmostEqual(spectral["center_track_error_budget_hz"], 95.26668390728645)
        self.assertEqual(spectral["floating_point_roundoff_operation_budget"], 4096)
        self.assertLess(spectral["derived_numeric_error_bound_hz"], 0.0016)
        self.assertLess(spectral["twice_derived_numeric_error_bound_hz"], 0.01)
        self.assertTrue(spectral["numeric_guard_dominates_error_bound"])
        self.assertEqual(spectral["center_track_rint_bound_channels"], 34)
        self.assertEqual(spectral["integration_motion_rint_bound_channels"], 29)
        self.assertEqual(spectral["composed_rint_bound_channels"], 63)
        self.assertTrue(spectral["composed_rint_bound_within_filter_radius"])
        self.assertEqual(
            spectral["filter_coordinate"],
            "native_raw_channel_axis_before_q_track_gather",
        )
        self.assertFalse(spectral["q_domain_boxcar_permitted"])
        self.assertTrue(spectral["raw_channel_inclusion_geometry_certified"])
        self.assertTrue(
            spectral[
                "native_filter_contract_requires_future_implementation_verification"
            ]
        )
        carrier = self.result["proxy_carrier_semantics"]
        self.assertEqual(carrier["axis_label"], "proxy_carrier_mhz")
        self.assertFalse(carrier["is_physical_rest_frequency"])
        self.assertEqual(carrier["score_half_bins"], 373832)
        self.assertEqual(carrier["score_bin_count"], 747665)
        self.assertEqual(carrier["q_support_guard_bins_each_edge"], 64)
        self.assertEqual(carrier["support_bin_count"], 747793)
        extraction = self.result["extraction_coverage"]
        self.assertTrue(extraction["passed"])
        self.assertEqual(extraction["checks"], 30)
        self.assertEqual(extraction["minimum_proxy_support_headroom_channels"], 52707)
        self.assertEqual(extraction["native_raw_filter_radius_channels"], 64)
        self.assertEqual(
            extraction[
                "minimum_proxy_support_with_native_filter_headroom_channels"
            ],
            52643,
        )
        self.assertEqual(extraction["minimum_truth_headroom_channels"], 56831)
        self.assertEqual(extraction["truth_integration_motion_margin_channels"], 29)
        self.assertEqual(
            extraction["minimum_truth_any_integration_time_headroom_channels"],
            56802,
        )

        mapping = self.result["q_to_raw_mapping_diagnostic"]
        self.assertTrue(mapping["passed"])
        self.assertEqual(mapping["mapping_evaluations"], 44_640)
        self.assertTrue(mapping["all_nearest_channel_mappings_injective"])
        self.assertTrue(mapping["all_nearest_channel_mappings_non_surjective"])
        self.assertEqual(mapping["minimum_skipped_raw_channels_over_support"], 38)
        self.assertEqual(mapping["maximum_skipped_raw_channels_over_support"], 48)
        self.assertEqual(
            sum(mapping["skipped_raw_channel_histogram"].values()),
            mapping["mapping_evaluations"],
        )
        self.assertFalse(mapping["q_domain_boxcar_permitted"])
        self.assertEqual(
            mapping["required_filter_coordinate"],
            "native_raw_channel_axis_before_q_track_gather",
        )
        self.assertEqual(
            mapping["minimum_native_raw_channels_supplied_by_q_support_guard"],
            64,
        )
        self.assertEqual(
            mapping["maximum_native_raw_channels_supplied_by_q_support_guard"],
            65,
        )
        self.assertTrue(mapping["q_support_guard_covers_native_filter_radius"])

    def test_dimensions_capacity_and_nontruncation(self):
        capacity = self.result["capacity"]
        self.assertEqual(capacity["hypotheses_per_window"], 2976)
        self.assertEqual(capacity["score_cells_per_window"], 2_225_051_040)
        self.assertEqual(capacity["score_cells_total"], 11_125_255_200)
        self.assertEqual(capacity["null_score_cells_total"], 2_848_065_331_200)
        self.assertEqual(capacity["full_spectral_bank_bytes_per_kind_per_window"], 6_675_153_120)
        self.assertEqual(capacity["core_streaming_array_bytes_per_template"], 23_180_687)
        self.assertTrue(capacity["core_streaming_arrays_below_live_cap"])
        self.assertEqual(
            capacity["maximum_evidence_canonical_bytes_derived_per_window"],
            89_967_424,
        )
        self.assertFalse(capacity["truncation_permitted"])
        self.assertEqual(capacity["capacity_overflow_outcome"], "M37_INVALID_NO_CONCLUSION")


class M37V0P6BankMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_cwd = Path.cwd()
        if cls.original_cwd != ROOT:
            import os

            os.chdir(ROOT)
        cls.config = load_config()
        cls.upstream = PREFLIGHT.load_json(PREFLIGHT.UPSTREAM_CONFIG)
        (
            cls.times,
            cls.labels,
            cls.baseline,
            cls.orbital,
            cls.basis_hash,
        ) = PREFLIGHT.factor_basis(cls.upstream)
        cls.direction, cls.perpendicular = PREFLIGHT.bank_direction(cls.config)

    @classmethod
    def tearDownClass(cls):
        if Path.cwd() != cls.original_cwd:
            import os

            os.chdir(cls.original_cwd)

    def test_disk_strip_extrema_dominate_dense_samples(self):
        rng = np.random.default_rng(3706001)
        lower, upper = 17 / 93, 19 / 93
        constant = np.array([0.3, -0.7, 1.1])
        vectors = np.array([[1.2, -0.4], [-0.3, 0.8], [0.1, 0.2]])
        minimum, maximum = PREFLIGHT.linear_extrema_on_disk_strip(
            constant,
            vectors @ self.direction,
            vectors @ self.perpendicular,
            lower,
            upper,
        )
        xs = rng.uniform(lower, upper, 20_000)
        ys = rng.uniform(-1.0, 1.0, 20_000) * np.sqrt(1.0 - xs * xs)
        points = xs[:, None] * self.direction + ys[:, None] * self.perpendicular
        values = constant[:, None] + vectors @ points.T
        self.assertTrue(np.all(values >= minimum[:, None] - 1e-14))
        self.assertTrue(np.all(values <= maximum[:, None] + 1e-14))

    def test_rint_composition_bound_includes_integer_tie(self):
        self.assertEqual(PREFLIGHT.rounded_difference_bound(0.0), 0)
        self.assertEqual(PREFLIGHT.rounded_difference_bound(0.999), 1)
        self.assertEqual(PREFLIGHT.rounded_difference_bound(1.0), 2)
        self.assertEqual(abs(int(np.rint(1.5)) - int(np.rint(0.5))), 2)

    def test_dense_truths_have_an_actual_finite_q_lattice_witness(self):
        rng = np.random.default_rng(3706091)
        count = 93
        half = 46
        df = float(self.config["spectral_support"]["channel_width_hz"])
        error = float(self.config["spectral_support"]["center_track_error_budget_hz"])
        physical_half = float(self.config["truth_domain"]["physical_frequency_half_width_hz"])
        grid_half = int(self.config["proxy_carrier_grid"]["score_half_bins"])
        for window in self.upstream["windows"]:
            center = float(window["rest_center_mhz"]) * 1e6
            samples = []
            for line_index in range(-half, half + 1):
                for boundary in (
                    max(-1.0, (2 * line_index - 1) / count),
                    min(1.0, (2 * line_index + 1) / count),
                ):
                    samples.append((boundary, math.sqrt(max(0.0, 1.0 - boundary**2))))
                    samples.append((boundary, -math.sqrt(max(0.0, 1.0 - boundary**2))))
            radius = np.sqrt(rng.random(1000))
            angle = rng.uniform(0.0, 2.0 * math.pi, 1000)
            random_points = np.column_stack((radius * np.cos(angle), radius * np.sin(angle)))
            samples.extend(
                (float(point @ self.direction), float(point @ self.perpendicular))
                for point in random_points
            )
            for x_line, y_line in samples:
                line_index = min(half, max(-half, int(math.floor(count * x_line / 2.0 + 0.5))))
                template = 2.0 * line_index / count * self.direction
                truth = x_line * self.direction + y_line * self.perpendicular
                template_factor = self.baseline + self.orbital @ template
                for frequency in (
                    center - physical_half,
                    center + physical_half,
                    center + rng.uniform(-physical_half, physical_half),
                ):
                    truth_factor = self.baseline + self.orbital @ truth
                    lower = float(np.max((frequency * truth_factor - error) / template_factor))
                    upper = float(np.min((frequency * truth_factor + error) / template_factor))
                    first_index = math.ceil(math.nextafter((lower - center) / df, -math.inf))
                    proxy = center + first_index * df
                    self.assertGreaterEqual(first_index, -grid_half)
                    self.assertLessEqual(first_index, grid_half)
                    self.assertGreaterEqual(proxy + 1e-7, lower)
                    self.assertLessEqual(proxy, upper + 1e-7)


class M37V0P6BankMutationTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = Path.cwd()
        if self.original_cwd != ROOT:
            import os

            os.chdir(ROOT)

    def tearDown(self):
        if Path.cwd() != self.original_cwd:
            import os

            os.chdir(self.original_cwd)

    def test_bank_or_factor_hash_mutation_rejected(self):
        for key in ("expected_bank_sha256", "expected_factor_basis_sha256"):
            config = load_config()
            config["template_bank"][key] = "0" * 64
            with self.assertRaisesRegex(ValueError, "hash"):
                PREFLIGHT.check_config(config)

    def test_unfrozen_hash_sentinel_rejected(self):
        for key in ("expected_bank_sha256", "expected_factor_basis_sha256"):
            config = load_config()
            config["template_bank"][key] = "TO_BE_FROZEN"
            with self.assertRaisesRegex(ValueError, "frozen.*SHA-256"):
                PREFLIGHT.check_config(config)

    def test_contract_count_and_grid_mutations_rejected(self):
        mutations = (
            lambda config: config["track_contract"].__setitem__("name", "legacy"),
            lambda config: config["track_contract"].__setitem__("formula", "legacy"),
            lambda config: config["track_contract"].__setitem__("truth_formula", "legacy"),
            lambda config: config["track_contract"].__setitem__(
                "carrier_restarts_between_scans", True
            ),
            lambda config: config["truth_domain"].__setitem__(
                "coefficient_disk", "x^2 + y^2 < 1"
            ),
            lambda config: config["template_bank"].__setitem__("selected_odd_count", 91),
            lambda config: config["proxy_carrier_grid"].__setitem__("score_half_bins", 373831),
            lambda config: config["retention_capacity"].__setitem__("truncation_permitted", True),
            lambda config: config["streaming_contract"].__setitem__(
                "complete_threshold_replay_required", False
            ),
            lambda config: config["streaming_contract"].__setitem__(
                "nms_is_normative", True
            ),
            lambda config: config["spectral_support"].__setitem__(
                "filter_coordinate", "q_domain_after_gather"
            ),
            lambda config: config["spectral_support"].__setitem__(
                "q_domain_boxcar_permitted", True
            ),
            lambda config: config["outcomes"].__setitem__("invalid", "partial"),
        )
        for mutate in mutations:
            config = load_config()
            mutate(config)
            with self.assertRaises((ValueError, AssertionError)):
                PREFLIGHT.check_config(config)

    def test_upstream_source_hash_mutation_rejected(self):
        config = load_config()
        config["project"]["source_hashes"]["continuous_preflight_result"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source hash"):
            PREFLIGHT.check_config(config)


if __name__ == "__main__":
    unittest.main()
