"""Tests for the LHS 1140 LS4A filterbank-header preflight."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls4a_lhs1140_fil_header_preflight.json"
SCRIPT = ROOT / "scripts/ls4a_lhs1140_fil_header_preflight.py"
SPEC = importlib.util.spec_from_file_location("ls4a_header", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
LS4A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LS4A)


def keyword(name: str, value=None, kind=None) -> bytes:
    payload = struct.pack("<I", len(name)) + name.encode("ascii")
    if value is None:
        return payload
    if kind == "str":
        encoded = value.encode("ascii")
        return payload + struct.pack("<I", len(encoded)) + encoded
    return payload + struct.pack(kind, value)


def synthetic_header(source: str = "LHS1140", *, tsamp: float = 1.0) -> bytes:
    return b"".join([
        keyword("HEADER_START"), keyword("source_name", source, "str"),
        keyword("tstart", 57774.0, "<d"), keyword("tsamp", tsamp, "<d"),
        keyword("fch1", 10500.0, "<d"), keyword("foff", -0.002, "<d"),
        keyword("nchans", 500001, "<i"), keyword("nifs", 1, "<i"),
        keyword("nbits", 32, "<i"), keyword("HEADER_END"),
    ])


def header_record(source: str, tstart: float, *, tsamp: float = 1.0) -> dict:
    return {
        "source_name": source, "tstart_mjd": tstart, "tsamp_s": tsamp,
        "nchans": 500001, "nifs": 1, "nbits": 32, "ntime": 300,
        "foff_mhz": -0.002, "frequency_low_mhz": 9500.0,
        "frequency_high_mhz": 10500.0, "bandwidth_mhz": 1000.0,
        "remote_size_matches_inventory": True, "spectral_values_read": False,
    }


class LS4AHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_boundary_forbids_samples_and_search(self):
        self.assertTrue(self.config["data_boundary"]["parser_must_stop_immediately_after_header_end"])
        self.assertFalse(self.config["data_boundary"]["filterbank_spectral_sample_may_be_unpacked"])
        self.assertFalse(self.config["claim_boundary"]["search_authorized"])

    def test_parser_stops_exactly_after_header_end(self):
        payload = synthetic_header() + b"SPECTRAL_BYTES_MUST_REMAIN_UNREAD"
        handle = io.BytesIO(payload)
        header, count = LS4A.parse_sigproc_header(handle, 65536)
        self.assertEqual(header["source_name"], "LHS1140")
        self.assertEqual(header["nchans"], 500001)
        self.assertEqual(count, handle.tell())
        self.assertEqual(handle.read(), b"SPECTRAL_BYTES_MUST_REMAIN_UNREAD")

    def test_complete_abacad_cadence_passes(self):
        sources = ["LHS1140", "HIP2579", "LHS1140", "HIP2586", "LHS1140", "HIP3249"]
        scans, headers = [], {}
        for index, source in enumerate(sources):
            medium = {"url": f"https://example/_{index:04d}.gpuspec.0002.fil", "expected_size_bytes": 1_000_000_000}
            htr = {"url": f"https://example/_{index:04d}.gpuspec.8.0001.fil", "expected_size_bytes": 5_000_000_000}
            scans.append({"medium": medium, "htr": htr})
            headers[medium["url"]] = header_record(source, 57774.0 + index / 1000)
            headers[htr["url"]] = header_record(source, 57774.0 + index / 1000, tsamp=0.00035)
        result = LS4A.qualify_cadence({"band": "X", "cadence_url": "https://example/cadence", "scans": scans}, headers, self.config)
        self.assertTrue(result["medium_qualified"])
        self.assertTrue(result["fully_followup_capable"])
        self.assertTrue(result["resource_gate_passes"])
        self.assertEqual(result["conjunction"]["corner_evaluation_count"], 81)

    def test_selection_prioritizes_frequency_anchor_after_gates(self):
        def item(band, centre, separation):
            return {"band": band, "cadence_url": f"https://example/{band}", "medium_qualified": True, "fully_followup_capable": True, "resource_gate_passes": True, "medium_download_bytes": 1, "mean_band_centre_mhz": centre, "log10_frequency_distance_from_anchor": abs(__import__('math').log10(centre / 10000)), "conjunction": {"nominal_projected_separation_stellar_radii": separation, "reference_bjd_utc_approximation": 1}}
        selected = LS4A.select_cadence([item("L", 1500, 1), item("X", 10000, 100)])
        self.assertEqual(selected["band"], "X")


if __name__ == "__main__":
    unittest.main()
