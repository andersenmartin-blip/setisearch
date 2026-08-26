"""Tests for the Milestone 37 metadata-only continuous coverage proof."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import unittest

import numpy as np

from seti_repeater.orbit import (
    C_M_S,
    celestial_frequency_factor,
    make_location,
    make_target,
    planet_radial_velocity,
)
from seti_repeater.search import make_rest_grid
from seti_repeater.spectral import normalized_boxcar


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "hd156668b_m37_preflight.json"
SCRIPT_PATH = ROOT / "scripts" / "m37_coverage_preflight.py"
SPEC = importlib.util.spec_from_file_location("m37_coverage_preflight", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


class M37CoverageResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_cwd = Path.cwd()
        if cls.original_cwd != ROOT:
            import os

            os.chdir(ROOT)
        cls.result = PREFLIGHT.check_config(load_config())

    @classmethod
    def tearDownClass(cls):
        if Path.cwd() != cls.original_cwd:
            import os

            os.chdir(cls.original_cwd)

    def test_actual_config_runs_and_expected_summary(self):
        result = self.result
        self.assertTrue(result["passed"])
        for flag in (
            "spectral_payload_inspected",
            "spectral_dataset_values_read",
            "remote_files_opened",
            "telescope_remote_request_made",
            "network_access_required",
        ):
            self.assertFalse(result[flag])
        envelope = result["continuous_circular_orbit_envelope"]
        self.assertEqual(envelope["checks"], 30)
        self.assertEqual(envelope["scan_window_integration_evaluations"], 480)
        self.assertEqual(envelope["minimum_lower_headroom_channels"], 113883)
        self.assertEqual(envelope["minimum_upper_headroom_channels"], 55929)
        self.assertEqual(envelope["maximum_dedoppler_margin_channels"], 837)
        self.assertEqual(
            envelope["maximum_mapped_spectral_support_margin_channels"], 65
        )
        legacy = result["legacy_m36_v0p5_21_template_regression"]
        self.assertEqual(legacy["template_count"], 21)
        self.assertEqual(legacy["checks"], 630)
        self.assertEqual(legacy["maximum_dedoppler_margin_channels"], 804)
        self.assertEqual(legacy["minimum_any_edge_headroom_channels"], 115215)

    def test_expected_per_window_envelope_table(self):
        expected = {
            "m37_1400p5": (116776, 59816, 822),
            "m37_1406p5": (116067, 58864, 826),
            "m37_1412p5": (115360, 57913, 829),
            "m37_1418p5": (114650, 56960, 833),
            "m37_1425p0": (113883, 55929, 837),
        }
        records = self.result["continuous_circular_orbit_envelope"]["records"]
        for window_id, values in expected.items():
            selected = [item for item in records if item["window_id"] == window_id]
            actual = (
                min(item["lower_headroom_channels"] for item in selected),
                min(item["upper_headroom_channels"] for item in selected),
                max(item["dedoppler_margin_channels"] for item in selected),
            )
            self.assertEqual(actual, values)

    def test_exact_extraction_geometry_snapshot(self):
        records = self.result["continuous_circular_orbit_envelope"]["records"]
        geometries = {}
        for record in records:
            geometries.setdefault(record["window_id"], record["extraction_geometry"])
            self.assertEqual(
                geometries[record["window_id"]], record["extraction_geometry"]
            )
        expected = {
            "m37_1400p5": (167400554, 168317500, 916946),
            "m37_1406p5": (165284527, 166201474, 916947),
            "m37_1412p5": (163168501, 164085448, 916947),
            "m37_1418p5": (161052475, 161969421, 916946),
            "m37_1425p0": (158760113, 159677059, 916946),
        }
        for key, values in expected.items():
            geometry = geometries[key]
            self.assertEqual(
                (
                    geometry["channel_start"],
                    geometry["channel_stop"],
                    geometry["channel_count"],
                ),
                values,
            )

    def test_width_tolerance_control_and_conditional_dimensions(self):
        width = self.result["width_envelope"]
        self.assertAlmostEqual(width["circular_orbital_speed_m_s"], 117092.49980661187)
        self.assertAlmostEqual(
            width["maximum_circular_acceleration_m_s2"], 1.8330011579451448
        )
        self.assertEqual(width["first_legacy_width_covering_proxy_sweep_channels"], 65)
        self.assertEqual(
            width["maximum_mapped_extraction_support_margin_channels"], 65
        )
        self.assertFalse(width["all_legacy_rest_grid_bins_finite_claim"])
        tolerance = self.result["literal_frequency_tolerance"]
        self.assertEqual(tolerance["radius_channels"], 7)
        self.assertLessEqual(tolerance["radius_hz"], 20.0)
        self.assertGreater(tolerance["next_channel_radius_hz"], 20.0)
        control = self.result["control_geometry"]
        self.assertTrue(control["one_repeated_control_direction"])
        self.assertEqual(control["temporal_control_measurements"], 3)
        self.assertEqual(control["distinct_spatial_control_directions"], 1)
        dimensions = self.result[
            "conditional_search_dimensions_for_legacy_21_template_bank"
        ]
        self.assertTrue(dimensions["not_a_detector_freeze"])
        self.assertEqual(dimensions["hypotheses_per_window"], 672)
        self.assertEqual(dimensions["nominal_score_tensor_cells_total"], 1184974560)

    def test_legacy_regression_is_explicitly_nonnormative(self):
        envelope = self.result["continuous_circular_orbit_envelope"]
        legacy = self.result["legacy_m36_v0p5_21_template_regression"]
        self.assertTrue(envelope["is_normative_extraction_guard_proof"])
        self.assertTrue(envelope["does_not_freeze_detector_v0p6"])
        self.assertTrue(envelope["does_not_claim_continuous_search_sensitivity"])
        self.assertFalse(legacy["is_normative_extraction_guard_proof"])
        self.assertEqual(self.result["phase_scope"]["m37_v0p6_template_bank"], "not frozen")
        self.assertFalse(
            self.result["phase_scope"]["orbital_parameter_uncertainties_covered"]
        )
        self.assertFalse(self.result["phase_scope"]["full_orbit_search_sensitivity_claim"])


class M37CoverageMathTests(unittest.TestCase):
    def test_rint_integer_tie_requires_extra_bound(self):
        self.assertEqual(PREFLIGHT.rounded_difference_bound(0.0), 0)
        self.assertEqual(PREFLIGHT.rounded_difference_bound(0.999), 1)
        self.assertEqual(PREFLIGHT.rounded_difference_bound(1.0), 2)
        self.assertEqual(PREFLIGHT.rounded_difference_bound(1.001), 2)
        self.assertEqual(abs(int(np.rint(1.5)) - int(np.rint(0.5))), 2)

    def test_quadrature_reconstructs_direct_planet_velocity(self):
        config = load_config()
        times = PREFLIGHT.integration_times(config["scans"][4]["expected_header"])
        zero = planet_radial_velocity(times, 1.0, 0.0, config["orbit"])
        quarter = planet_radial_velocity(times, 1.0, 0.25, config["orbit"])
        for phase in np.linspace(0.0, 1.0, 41, endpoint=False):
            angle = 2.0 * math.pi * phase
            reconstructed = zero * math.cos(angle) + quarter * math.sin(angle)
            direct = planet_radial_velocity(times, 1.0, phase, config["orbit"])
            # The implementation adds phase offsets to a large BJD before
            # subtraction, so micro-m/s cancellation is expected numerically.
            np.testing.assert_allclose(reconstructed, direct, rtol=1e-9, atol=1e-4)

    def test_dense_scale_phase_tracks_are_inside_envelope(self):
        config = load_config()
        scan = config["scans"][-1]
        window = config["windows"][-1]
        target = make_target(config["target"])
        location = make_location(config["observatory"])
        record = PREFLIGHT.continuous_circular_envelope(
            config, scan, window, target, location, spectral_rest_half_width=64
        )
        times = PREFLIGHT.integration_times(scan["expected_header"])
        _, observer, _ = celestial_frequency_factor(
            times, 0.0, 0.0, target, location, config["orbit"]
        )
        observer_factor = 1.0 + observer / C_M_S
        geometry = record["extraction_geometry"]
        zero_mhz = geometry["frequency_low_mhz"]
        df_mhz = geometry["channel_width_mhz"]
        rest_grid = make_rest_grid(window, df_mhz)
        rng = np.random.default_rng(370037)
        samples = [
            (float(scale), float(phase))
            for scale in (0.0, 0.5, 1.0)
            for phase in np.linspace(0.0, 1.0, 721, endpoint=False)
        ]
        samples += [(float(rng.random()), float(rng.random())) for _ in range(500)]
        maximum_mapped_support = 0
        for scale, phase in samples:
            planet = planet_radial_velocity(times, scale, phase, config["orbit"])
            factor = observer_factor * (1.0 - planet / C_M_S)
            track = float(window["rest_center_mhz"]) * factor
            indices = np.rint((track - zero_mhz) / df_mhz).astype(int)
            margin = int(np.max(np.abs(indices - indices[0])))
            self.assertLessEqual(margin, record["dedoppler_margin_channels"])
            mapped = np.rint((rest_grid * factor[0] - zero_mhz) / df_mhz).astype(int)
            actual_lower = int(mapped.min() - record["total_margin_channels"])
            actual_upper = int(
                geometry["channel_count"]
                - 1
                - mapped.max()
                - record["total_margin_channels"]
            )
            self.assertGreaterEqual(actual_lower, record["lower_headroom_channels"])
            self.assertGreaterEqual(actual_upper, record["upper_headroom_channels"])
            center = float(rest_grid[-1])
            support_indices = np.rint(
                (
                    np.array([center, center + 64 * df_mhz]) * factor[0]
                    - zero_mhz
                )
                / df_mhz
            ).astype(int)
            mapped_support = abs(int(support_indices[1] - support_indices[0]))
            maximum_mapped_support = max(maximum_mapped_support, mapped_support)
            self.assertLessEqual(
                mapped_support,
                record["spectral_mapped_support_margin_channels"],
            )
        self.assertEqual(maximum_mapped_support, 65)

    def test_current_boxcar_has_64_nan_edge_bins_at_width_129(self):
        values = np.ones(352671, dtype=np.float32)
        filtered = normalized_boxcar(values, 129)
        self.assertTrue(np.all(np.isnan(filtered[:64])))
        self.assertTrue(np.all(np.isnan(filtered[-64:])))
        self.assertTrue(np.all(np.isfinite(filtered[64:-64])))


class M37CoverageMutationTests(unittest.TestCase):
    def test_nonzero_eccentricity_rejected(self):
        config = load_config()
        config["orbit"]["eccentricity"] = 0.01
        target = make_target(config["target"])
        location = make_location(config["observatory"])
        with self.assertRaisesRegex(ValueError, "eccentricity == 0"):
            PREFLIGHT.continuous_circular_envelope(
                config,
                config["scans"][0],
                config["windows"][0],
                target,
                location,
                64,
            )

    def test_nonfull_phase_or_scale_domain_rejected(self):
        for key, value in (("phase_cycles", "sampled"), ("projected_scale_max", 1.01)):
            config = load_config()
            config["coverage_domain"][key] = value
            target = make_target(config["target"])
            location = make_location(config["observatory"])
            with self.assertRaises(ValueError):
                PREFLIGHT.continuous_circular_envelope(
                    config,
                    config["scans"][0],
                    config["windows"][0],
                    target,
                    location,
                    64,
                )

    def test_metadata_mutation_rejected(self):
        config = load_config()
        config["target"]["parallax_mas"] += 0.001
        with self.assertRaisesRegex(ValueError, "official metadata parallax"):
            PREFLIGHT.validate_selected_metadata(config)

    def test_header_identity_or_order_mutation_rejected(self):
        for mutate in (
            lambda c: c["scans"][0].__setitem__("expected_etag", "changed"),
            lambda c: c["scans"][0].__setitem__("url", c["scans"][1]["url"]),
            lambda c: c["scans"][0].__setitem__("kind", "off"),
            lambda c: c["scans"][2]["expected_header"].__setitem__(
                "tstart_mjd", c["scans"][2]["expected_header"]["tstart_mjd"] + 1e-6
            ),
        ):
            config = load_config()
            mutate(config)
            with self.assertRaises(ValueError):
                PREFLIGHT.validate_scan_headers(config)

    def test_window_or_width_domain_mutation_rejected(self):
        config = load_config()
        config["windows"][0]["fmin_mhz"] = 1399.1
        with self.assertRaisesRegex(ValueError, "five-window geometry"):
            PREFLIGHT.validate_windows(config)
        config = load_config()
        config["coverage_domain"]["maximum_spectral_width_channels"] = 131
        with self.assertRaisesRegex(ValueError, "maximum width guard"):
            PREFLIGHT.check_config(config)


if __name__ == "__main__":
    unittest.main()
