"""New-source isolation, actual codec integration, and pre-network gates."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import h5py
import hdf5plugin
import numpy as np

from seti_repeater import source_radio as source
from seti_repeater import source_m43h as rows
from seti_repeater import transport_radio as net
from seti_repeater import http_range_v0p6 as old
from m43g_reference import sorted_reference

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "config/radio_hd1461_source_preparation_20260926.json"


class Response:
    def __init__(self, url, payload, status, headers):
        self.url, self.payload, self.status, self.headers = url, payload, status, headers
        self.reads = 0

    def geturl(self): return self.url
    def read(self, n):
        self.reads += 1
        return self.payload[:n]
    def __enter__(self): return self
    def __exit__(self, *args): pass


class LocalServer:
    def __init__(self, definition, payload):
        self.definition, self.payload = definition, payload
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request.get_method(), request.headers.get("Range")))
        h = {"ETag": self.definition["expected_etag"], "Accept-Ranges": "bytes",
             "Content-Length": str(len(self.payload))}
        if request.get_method() == "HEAD":
            return Response(request.full_url, b"", 200, h)
        a, b = map(int, request.headers["Range"].removeprefix("bytes=").split("-"))
        if request.headers.get("If-match") != self.definition["expected_etag"]:
            raise AssertionError("fixture request lost the identity condition")
        h.update({"Content-Range": f"bytes {a}-{b}/{len(self.payload)}",
                  "Content-Length": str(b-a+1)})
        return Response(request.full_url, self.payload[a:b+1], 206, h)


def fixture(directory, codec):
    values = np.random.default_rng(261926).normal(12., 2., (3, 1, 20000)).astype("<f4")
    definition = {"label": "fixture", "role": "on", "url": "https://example.invalid/fixture.h5",
        "expected_etag": '"fixture-only"', "expected_chunks": [1, 1, 4096],
        "expected_header": {"source_name": "fixture", "src_raj_hours": 1., "src_dej_deg": -2.,
            "tstart_mjd": 50000., "tsamp_s": 3., "dataset_shape": [3, 1, 20000],
            "dataset_dtype": "float32", "fch1_mhz": 1500., "foff_mhz": -0.000003}}
    path = directory/"input.h5"
    with h5py.File(path, "w") as f:
        f.create_dataset("data", data=values, chunks=(1, 1, 4096), **codec)
        f.attrs.update({"source_name": "fixture", "src_raj": 1., "src_dej": -2.,
            "tstart": 50000., "tsamp": 3., "fch1": 1500., "foff": -0.000003})
    payload = path.read_bytes()
    definition["expected_remote_size_bytes"] = len(payload)
    return values, definition, payload


class RadioSourceTests(unittest.TestCase):
    def test_codecs_native_mapping_restart_and_fixture_separation(self):
        for name, codec in [("gzip", {"compression": "gzip", "compression_opts": 1}),
                            ("bitshuffle_lz4", dict(hdf5plugin.Bitshuffle(cname="lz4")))]:
            with self.subTest(codec=name), tempfile.TemporaryDirectory() as td:
                directory = Path(td)
                original, definition, payload = fixture(directory, codec)
                server = LocalServer(definition, payload)
                budget = net.Budget(900, 4*1024**2, 120)
                window = {"name": "synthetic", "archive_interval": [501, 4604]}
                destination = directory/"rows"
                atomic = rows.atomic_json
                def interrupt(path, record):
                    atomic(path, record)
                    if Path(path).name == "row00.json":
                        raise InterruptedError("intentional fixture interruption")
                with patch.object(net, "open_response", side_effect=server):
                    with patch.object(rows, "atomic_json", side_effect=interrupt):
                        with self.assertRaises(InterruptedError):
                            source._extract_bound_source(definition, window, "a"*64,
                                destination, directory/"mirror", budget, kind="local-fixture")
                    self.assertFalse((destination/"source.json").exists())
                    receipt, detail = source._extract_bound_source(definition, window, "a"*64,
                        destination, directory/"mirror", budget, kind="local-fixture")
                    self.assertEqual(detail["resumed_rows"], 1)
                    gets = sum(method == "GET" for method, _ in server.calls)
                    again, detail2 = source._extract_bound_source(definition, window, "a"*64,
                        destination, directory/"mirror", budget, kind="local-fixture")
                    self.assertEqual(again, receipt)
                    self.assertEqual(detail2["resumed_rows"], 3)
                    self.assertEqual(gets, sum(method == "GET" for method, _ in server.calls))
                geometry = receipt["scope"]["geometry"]
                expected_low = (1500. - 0.000003*4603)*1e6
                self.assertAlmostEqual(geometry["raw_zero_hz"], expected_low, places=5)
                for row in range(3):
                    native = np.load(destination/f"row{row:02d}.native.npy", allow_pickle=False)
                    normalized = np.load(destination/f"row{row:02d}.normalized.npy", allow_pickle=False)
                    np.testing.assert_array_equal(native, original[row, 0, 501:4604])
                    np.testing.assert_array_equal(normalized, sorted_reference(native[::-1][None, :])[0])
                with self.assertRaisesRegex(ValueError, "wrong-kind"):
                    rows.rehydrate(destination, receipt["receipt_sha256"])
                with (destination/"row01.native.npy").open("r+b") as f:
                    f.seek(-4, 2); f.write(b"XXXX")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    rows.rehydrate(destination, receipt["receipt_sha256"], required_kind="local-fixture")

    def test_live_preparation_blocks_before_any_network(self):
        digest = rows.file_hash(ROOT/CONTRACT)
        with patch.object(net, "open_response", side_effect=AssertionError("network reached")) as opened:
            cfg, readiness = source.load_contract(ROOT, CONTRACT, digest)
            self.assertEqual(readiness["status"], "BLOCKED")
            self.assertEqual(readiness["scan_count"], 6)
            self.assertIn("pointing: unresolved", readiness["blockers"])
            with self.assertRaisesRegex(ValueError, "source contract blocked"):
                source.extract_remote(ROOT, CONTRACT, digest, "epoch1_on", "unused",
                    "/unused", "/unused", net.Budget(**cfg["session_limits"]),
                    spectral_access_authorized=True)
            with self.assertRaisesRegex(ValueError, "not authorized"):
                source.extract_remote(ROOT, CONTRACT, digest, "epoch1_on", "unused",
                    "/unused", "/unused", net.Budget(**cfg["session_limits"]))
            opened.assert_not_called()

    def test_changed_contract_hash_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "contract file changed"):
            source.load_contract(ROOT, CONTRACT, "0"*64)

    def test_source_gate_and_implementation_cannot_drift(self):
        original = json.loads((ROOT/CONTRACT).read_text())
        for fault in ("source", "gate", "code", "overlap"):
            with self.subTest(fault=fault), tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", dir=ROOT/"config") as f:
                cfg = copy.deepcopy(original)
                if fault == "source": cfg["source_inventory_sha256"] = "0"*64
                if fault == "gate": cfg["gates"]["pointing"] = {
                    "status": "passed", "source_inventory_sha256": "0"*64}
                if fault == "code": cfg["pinned_files"][source.IMPLEMENTATION_PATHS[0]] = "0"*64
                if fault == "overlap": cfg["windows"] = [
                    {"name": "a", "archive_interval": [100, 500]},
                    {"name": "b", "archive_interval": [400, 600]}]
                json.dump(cfg, f); f.flush()
                relative = str(Path(f.name).relative_to(ROOT))
                with patch.object(net, "open_response", side_effect=AssertionError("network reached")) as opened:
                    with self.assertRaisesRegex(ValueError, "changed|different source|overlapping"):
                        source.load_contract(ROOT, relative, rows.file_hash(f.name))
                    opened.assert_not_called()

    def test_identity_and_response_faults_stop_before_body(self):
        identity = old.RemoteIdentity("https://example.invalid/fixture.h5", 100, '"a"')
        good = {"Content-Range": "bytes 0-9/100", "Content-Length": "10", "ETag": '"a"'}
        for change in [{"ETag": '"changed"'}, {"Content-Range": "bytes 1-10/100"},
                       {"Content-Length": "100"}, {"Content-Encoding": "gzip"}]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as td:
                response = Response(identity.url, b"0123456789", 206, {**good, **change})
                budget = net.Budget(3, 100, 60)
                with net.RadioMirror(Path(td)/"mirror", identity, budget) as mirror:
                    with patch.object(net, "open_response", return_value=response):
                        with self.assertRaisesRegex(ValueError, "before body read"):
                            mirror.prefetch((old.ByteRange(0, 10),))
                self.assertEqual(response.reads, 0)
                self.assertEqual(budget.attempts, 1)
                self.assertEqual(budget.reserved_bytes, 11)
                self.assertEqual(budget.accepted_bytes, 0)

    def test_budget_and_redirect_fail_closed(self):
        budget = net.Budget(1, 10, 60)
        budget.reserve(10)
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            budget.reserve(0)
        with self.assertRaisesRegex(ValueError, "redirect refused"):
            net.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid")
        budget = net.Budget(2, 10, 60)
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            budget.reserve(11)
        budget.started -= 61
        with self.assertRaisesRegex(ValueError, "time budget"):
            budget.reserve(0)

    def test_wrong_live_identity_header_and_chunks_rejected(self):
        for field in ("expected_etag", "expected_remote_size_bytes", "header", "chunks"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                directory = Path(td)
                _, definition, payload = fixture(directory, {"compression": "gzip"})
                server = LocalServer(copy.deepcopy(definition), payload)
                if field == "expected_etag": definition[field] = '"different"'
                if field == "expected_remote_size_bytes": definition[field] += 1
                if field == "header": definition["expected_header"]["src_dej_deg"] += 1
                if field == "chunks": definition["expected_chunks"][2] = 2048
                with patch.object(net, "open_response", side_effect=server):
                    with self.assertRaisesRegex(ValueError, "differs|header|chunks"):
                        source._extract_bound_source(definition,
                            {"name": "synthetic", "archive_interval": [501, 4604]}, "a"*64,
                            directory/"rows", directory/"mirror", net.Budget(900, 4*1024**2, 120),
                            kind="local-fixture")
                self.assertFalse((directory/"rows"/"source.json").exists())
                if field in ("expected_etag", "expected_remote_size_bytes"):
                    self.assertEqual(server.calls, [("HEAD", None)])


if __name__ == "__main__":
    unittest.main()
