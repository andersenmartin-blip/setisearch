"""Tests for the prospectively frozen LS4C HTR follow-up."""

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
CONFIG = ROOT / "config/ls4c_lhs1140_x_htr_followup.json"
LS1_HTR_CONFIG = ROOT / "config/ls1_htr_followup.json"
FOLLOWUP_SCRIPT = ROOT / "scripts/ls4c_htr_followup.py"
SYNTHETIC_SCRIPT = ROOT / "scripts/ls4c_htr_synthetic_validation.py"
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FOLLOWUP = load_script("ls4c_followup", FOLLOWUP_SCRIPT)
SYNTHETIC = load_script("ls4c_synthetic", SYNTHETIC_SCRIPT)


def keyword(value: str) -> bytes:
    encoded = value.encode("ascii")
    return struct.pack("<I", len(encoded)) + encoded


def synthetic_filterbank(path: Path, data: np.ndarray, source: str, tstart: float) -> int:
    fields = [
        ("machine_id", "<i", 10),
        ("telescope_id", "<i", 6),
        ("data_type", "<i", 1),
        ("source_name", "str", source),
        ("src_raj", "<d", 4459.28),
        ("src_dej", "<d", -151616.32),
        ("az_start", "<d", 0.0),
        ("za_start", "<d", 0.0),
        ("fch1", "<d", 1063.0),
        ("foff", "<d", -1.0),
        ("nchans", "<i", data.shape[1]),
        ("nifs", "<i", 1),
        ("nbits", "<i", 8),
        ("tstart", "<d", tstart),
        ("tsamp", "<d", 0.001),
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
    path.write_bytes(header + np.asarray(data, dtype=np.uint8).tobytes(order="C"))
    return len(header)


class LS4CHTRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.ls1 = json.loads(LS1_HTR_CONFIG.read_text(encoding="utf-8"))

    def test_followup_is_exactly_stage1_conditioned_and_claim_closed(self):
        self.assertTrue(self.config["stage1"]["followup_preregistration_required"])
        self.assertTrue(self.config["freeze_boundary"]["post_stage1_candidate_conditioning"])
        self.assertFalse(self.config["freeze_boundary"]["htr_values_read_before_freeze"])
        self.assertEqual(len(FOLLOWUP.verify_stage1(self.config)), 7)
        self.assertFalse(self.config["claim_boundary"]["technosignature_claimed"])
        self.assertFalse(self.config["claim_boundary"]["positive_result_is_detection"])

    def test_htr_analysis_is_exactly_inherited_from_ls1(self):
        self.assertEqual(self.config["analysis"], self.ls1["analysis"])
        FOLLOWUP.verify_analysis_inheritance(self.config, LS1_HTR_CONFIG)

    def test_seven_survivors_are_co_temporal_a1_events(self):
        candidates = self.config["candidates"]
        self.assertEqual(len(candidates), 7)
        self.assertEqual({item["on_label"] for item in candidates}, {"A1"})
        self.assertEqual({item["off_label"] for item in candidates}, {"B1"})
        self.assertEqual({item["spectral_width_bins"] for item in candidates}, {1})
        self.assertEqual({item["requested_duration_s"] for item in candidates}, {64.0})
        overlap_start = max(item["time_start_s"] for item in candidates)
        overlap_stop = min(item["time_stop_s"] for item in candidates)
        self.assertGreater(overlap_stop, overlap_start)
        self.assertIn("suspicious", self.config["candidate_group_context"]["interpretation"])

    def test_only_required_a1_b1_sources_are_selected(self):
        sources = self.config["sources"]
        self.assertEqual([item["label"] for item in sources], ["A1", "B1"])
        total = sum(item["expected_size_bytes"] for item in sources)
        self.assertEqual(total, 18870174378)
        self.assertLessEqual(total, self.config["resource_policy"]["maximum_total_htr_download_bytes"])
        self.assertFalse(self.config["resource_policy"]["raw_files_may_be_published"])

    def test_sigproc_decoder_batch_extracts_exact_candidate_means(self):
        data = np.arange(32 * 64, dtype=np.uint16).reshape(32, 64) % 251
        data = data.astype(np.uint8)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-htr.fil"
            tstart = 57774.96857638889
            data_offset = synthetic_filterbank(path, data, "LHS1140", tstart)
            config = copy.deepcopy(self.config)
            config["expected_filterbank_header"] = {
                "header_bytes": data_offset,
                "fch1_mhz": 1063.0,
                "foff_mhz": -1.0,
                "nchans": 64,
                "nifs": 1,
                "nbits": 8,
                "ntime": 32,
                "tsamp_s": 0.001,
            }
            config["resource_policy"]["chunk_rows"] = 7
            candidates = [
                {
                    "candidate_id": "c1",
                    "frequency_start_mhz": 1030.0,
                    "frequency_stop_mhz": 1032.0,
                    "frequency_padding_mhz": 0.1,
                },
                {
                    "candidate_id": "c2",
                    "frequency_start_mhz": 1000.0,
                    "frequency_stop_mhz": 1002.0,
                    "frequency_padding_mhz": 0.1,
                },
            ]
            source = {
                "label": "A1",
                "expected_source_name": "LHS1140",
                "expected_tstart_mjd": tstart,
                "expected_size_bytes": path.stat().st_size,
            }
            header, offset = FOLLOWUP.parse_and_validate_header(path, source, config)
            series, bands = FOLLOWUP.extract_candidate_series(
                path, header, offset, candidates, config
            )
        for candidate in candidates:
            candidate_id = candidate["candidate_id"]
            start = bands[candidate_id]["channel_start"]
            stop = bands[candidate_id]["channel_stop"]
            np.testing.assert_allclose(series[candidate_id], data[:, start:stop].mean(axis=1))

    def test_inherited_htr_synthetic_injection_is_recovered(self):
        result = SYNTHETIC.run_validation()
        self.assertTrue(result["recovered"])
        self.assertEqual(result["artifact_type"], "seti_repeater.ls4c_htr_synthetic_validation")
        self.assertEqual(result["inherited_htr_detector"], "LS1 unchanged")


if __name__ == "__main__":
    unittest.main()
