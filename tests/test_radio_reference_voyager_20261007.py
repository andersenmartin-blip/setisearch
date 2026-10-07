import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("voyager_reference", ROOT / "scripts/radio_reference_voyager_20261007.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CONFIG = ROOT / "config/radio_reference_voyager_20261007.json"


class ReferenceContractTests(unittest.TestCase):
    def test_frozen_config_is_engineering_only(self):
        cfg = MODULE.strict_config(CONFIG)
        self.assertTrue(all(value is False for value in cfg["authority"].values()))
        self.assertIsNone(cfg["source"]["expected_sha256"])
        self.assertEqual(cfg["limits"]["attempts"], 1)

    def test_duplicate_json_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"status":"FROZEN_ENGINEERING_REFERENCE_NOT_PILOT","status":"other"}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON"):
                MODULE.strict_config(path)

    def test_nonfinite_json_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"value":NaN}')
            with self.assertRaisesRegex(ValueError, "non-finite JSON"):
                MODULE.strict_config(path)

    def test_unapproved_or_credentialed_urls_are_refused(self):
        for url in ["https://example.com/file.h5", "file:///tmp/file.h5",
                    "https://user:secret@blpd0.ssl.berkeley.edu/file.h5",
                    "https://blpd0.ssl.berkeley.edu/file.h5?changed=1"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                MODULE.validate_url(url)

    def test_exact_header_passes(self):
        cfg = json.loads(CONFIG.read_text())
        expected = cfg["expected_header"]
        header = {"source_name": "Voyager1", "fch1": expected["fch1_mhz"],
                  "foff": expected["foff_mhz"], "tsamp": expected["tsamp_s"],
                  "tstart": expected["tstart_mjd"]}
        checks = MODULE.validate_header(header, tuple(expected["shape"]), expected)
        self.assertTrue(all(checks.values()))

    def test_changed_header_is_refused(self):
        cfg = json.loads(CONFIG.read_text())
        expected = cfg["expected_header"]
        header = {"source_name": "pilot", "fch1": expected["fch1_mhz"],
                  "foff": expected["foff_mhz"], "tsamp": expected["tsamp_s"],
                  "tstart": expected["tstart_mjd"]}
        with self.assertRaisesRegex(ValueError, "header mismatch"):
            MODULE.validate_header(header, tuple(expected["shape"]), expected)

    def test_official_reference_hits_pass(self):
        cfg = json.loads(CONFIG.read_text())["search"]
        rows = [{"frequency_mhz": x["frequency_mhz"], "snr": x["snr"], "drift_hz_s": -0.4}
                for x in cfg["expected_reference_hits"]]
        self.assertEqual(len(MODULE.validate_hits(rows, cfg["expected_reference_hits"],
                                                  cfg["frequency_tolerance_mhz"],
                                                  cfg["snr_tolerance"])), 3)

    def test_missing_or_changed_reference_hit_is_refused(self):
        cfg = json.loads(CONFIG.read_text())["search"]
        rows = [{"frequency_mhz": x["frequency_mhz"], "snr": x["snr"], "drift_hz_s": -0.4}
                for x in cfg["expected_reference_hits"]]
        rows.pop()
        with self.assertRaises(ValueError):
            MODULE.validate_hits(rows, cfg["expected_reference_hits"],
                                 cfg["frequency_tolerance_mhz"], cfg["snr_tolerance"])
        rows = [{"frequency_mhz": x["frequency_mhz"], "snr": x["snr"] + 1, "drift_hz_s": -0.4}
                for x in cfg["expected_reference_hits"]]
        with self.assertRaisesRegex(ValueError, "SNR mismatch"):
            MODULE.validate_hits(rows, cfg["expected_reference_hits"],
                                 cfg["frequency_tolerance_mhz"], cfg["snr_tolerance"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
