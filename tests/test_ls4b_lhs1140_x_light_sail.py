"""Tests for the prospectively frozen LHS 1140 LS4B X-band screen."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls4b_lhs1140_x_light_sail.json"
LS1_CONFIG = ROOT / "config/ls1_hd219134_light_sail.json"
SCREEN_SCRIPT = ROOT / "scripts/ls4b_filterbank_screen.py"
SYNTHETIC_SCRIPT = ROOT / "scripts/ls4b_synthetic_validation.py"
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCREEN = load_script("ls4b_screen", SCREEN_SCRIPT)
SYNTHETIC = load_script("ls4b_synthetic", SYNTHETIC_SCRIPT)


def keyword(value: str) -> bytes:
    encoded = value.encode("ascii")
    return struct.pack("<I", len(encoded)) + encoded


def synthetic_filterbank(path: Path, data: np.ndarray, source: str, tstart: float) -> int:
    fields = [
        ("machine_id", "<i", 20),
        ("telescope_id", "<i", 6),
        ("data_type", "<i", 1),
        ("source_name", "str", source),
        ("src_raj", "<d", 4459.28),
        ("src_dej", "<d", -151616.32),
        ("az_start", "<d", 0.0),
        ("za_start", "<d", 0.0),
        ("fch1", "<d", 1102.3),
        ("foff", "<d", -0.1),
        ("nchans", "<i", data.shape[1]),
        ("nifs", "<i", 1),
        ("nbits", "<i", 32),
        ("tstart", "<d", tstart),
        ("tsamp", "<d", 1.0),
    ]
    parts = [keyword("HEADER_START")]
    for name, kind, value in fields:
        parts.append(keyword(name))
        if kind == "str":
            encoded = str(value).encode("ascii")
            parts.append(struct.pack("<I", len(encoded)) + encoded)
        else:
            parts.append(struct.pack(kind, value))
    parts.append(keyword("HEADER_END"))
    header = b"".join(parts)
    path.write_bytes(header + np.asarray(data, dtype="<f4").tobytes(order="C"))
    return len(header)


class LS4BLightSailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.ls1 = json.loads(LS1_CONFIG.read_text(encoding="utf-8"))

    def test_freeze_is_prospective_and_claims_are_closed(self):
        boundary = self.config["freeze_boundary"]
        self.assertTrue(boundary["sigproc_headers_read_before_freeze"])
        self.assertFalse(boundary["medium_resolution_values_read_before_freeze"])
        self.assertFalse(boundary["high_time_resolution_values_read_before_freeze"])
        self.assertFalse(self.config["claim_boundary"]["technosignature_claimed"])
        self.assertFalse(self.config["resource_policy"]["raw_files_may_be_published"])

    def test_detector_core_is_inherited_with_only_declared_adaptations(self):
        allowed = {"implementation", "product_suffix", "science_band_mhz"}
        actual = {
            key: value
            for key, value in self.config["medium_resolution_screen"].items()
            if key not in allowed
        }
        expected = {
            key: value
            for key, value in self.ls1["medium_resolution_screen"].items()
            if key not in allowed
        }
        self.assertEqual(actual, expected)
        self.assertEqual(self.config["medium_resolution_screen"]["science_band_mhz"], [8000.0, 12000.0])

    def test_sequence_and_header_result_are_frozen(self):
        sequence = self.config["selected_sequence"]
        self.assertEqual([item["label"] for item in sequence], ["A1", "B1", "A2", "C1", "A3", "D1"])
        self.assertEqual([item["role"] for item in sequence], ["ON", "OFF", "ON", "OFF", "ON", "OFF"])
        self.assertTrue(all(item["medium_resolution"]["url"].endswith(".gpuspec.0002.fil") for item in sequence))
        self.assertTrue(all(item["high_time_resolution"]["url"].endswith(".gpuspec.8.0001.fil") for item in sequence))
        self.assertEqual(sum(item["medium_resolution"]["expected_size_bytes"] for item in sequence), 9412019946)
        SCREEN.verify_header_source(self.config)

    def test_geometry_is_explicitly_a_weak_conjunction_case(self):
        geometry = self.config["geometry"]
        self.assertGreater(geometry["nominal_projected_separation_stellar_radii"], geometry["ls1_selected_separation_stellar_radii"])
        self.assertGreater(geometry["nominal_projected_separation_stellar_radii"], geometry["ls3c_selected_separation_stellar_radii"])
        self.assertIn("weak conjunction", geometry["interpretation_limit"])

    def test_science_window_passes_frozen_memory_gate(self):
        expected = self.config["expected_filterbank_header"]
        low, high = self.config["medium_resolution_screen"]["science_band_mhz"]
        start, stop = SCREEN.channel_bounds(
            expected["fch1_mhz"], expected["foff_mhz"], expected["nchans"], low, high
        )
        window_bytes = expected["ntime"] * (stop - start) * 4
        self.assertLessEqual(window_bytes, self.config["resource_policy"]["maximum_science_window_bytes_per_scan"])
        self.assertGreater(stop - start, 1_000_000)

    def test_sigproc_reader_recovers_a_synthetic_broadband_event(self):
        generator = np.random.default_rng(41)
        data = generator.normal(20.0, 1.0, size=(128, 1024)).astype(np.float32)
        data[48:72, 320:576] += np.float32(5.0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.fil"
            data_offset = synthetic_filterbank(path, data, "LHS1140", 57774.96857638889)
            config = copy.deepcopy(self.config)
            config["expected_filterbank_header"] = {
                "header_bytes": data_offset,
                "fch1_mhz": 1102.3,
                "foff_mhz": -0.1,
                "nchans": 1024,
                "nifs": 1,
                "nbits": 32,
                "ntime": 128,
                "tsamp_s": 1.0,
            }
            config["medium_resolution_screen"].update(
                {
                    "science_band_mhz": [1000.0, 1102.3],
                    "base_bin_native_channels": 16,
                    "spectral_width_base_bins": [1, 4, 8, 16],
                    "duration_s": [4.0, 8.0, 16.0, 24.0, 32.0],
                    "off_veto_score_threshold": 6.0,
                }
            )
            config["resource_policy"]["maximum_science_window_bytes_per_scan"] = 1_000_000
            scan = copy.deepcopy(config["selected_sequence"][0])
            scan["medium_resolution"]["expected_size_bytes"] = path.stat().st_size
            result = SCREEN.screen_scan(scan, config, path, "0" * 64)
        self.assertTrue(result["search"]["events"])
        self.assertEqual(result["source_name"], "LHS1140")
        self.assertEqual(result["source_sha256"], "0" * 64)

    def test_inherited_synthetic_injection_is_recovered(self):
        result = SYNTHETIC.run_validation()
        self.assertTrue(result["recovered"])
        self.assertEqual(result["artifact_type"], "seti_repeater.ls4b_synthetic_validation")
        self.assertEqual(result["inherited_detector_core"], "LS1 unchanged")


if __name__ == "__main__":
    unittest.main()
