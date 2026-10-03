"""Adversarial candidate tests with new deterministic, local-only row receipts."""
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import local_receipt_receiver as bridge
from radio_receiver_adapter_common import context
from seti_repeater import http_range_v0p6 as transport


def fixtures(root, c):
    descriptor = {
        "schema": "new-receiver-bridge-unit-fixture-v1",
        "law": "integer modular rows; no random draws or telescope data",
        **bridge.receiver_window(c),
    }
    fixture_hash = bridge.rows.digest(descriptor)
    entries = []
    directories = {}
    channels = np.arange(c.geometry.channel_count, dtype=np.uint32)
    for index, scan in enumerate(c.scans):
        label = scan["label"]
        definition = {k: copy.deepcopy(v) for k, v in scan.items() if k not in ("kind", "epoch")}
        definition.update(url=f"https://{label}.invalid/unit-fixture.h5",
                          expected_remote_size_bytes=10000000 + index,
                          expected_etag=f'"new-unit-{index}"')
        scope = bridge.rows.make_scope(definition, c.window, c.native_window["archive_interval"],
                                       fixture_hash, "local-fixture")
        directory = root / label
        directory.mkdir(parents=True)
        inventory = []
        for row in range(16):
            raw = np.ascontiguousarray(((channels * 37 + row * 11 + index * 13) % 257)
                                        .astype("<f4") / np.float32(64))
            raw += (channels % 17).astype("<f4") * np.float32(index / 128)
            ascending, normalized = bridge.rows.normalize_native_row(raw)
            record = {"scope_sha256": bridge.rows.digest(scope), "row": row,
                      "native_sha256": bridge.rows.array_hash(raw),
                      "ascending_raw_sha256": bridge.rows.array_hash(ascending),
                      "normalized_sha256": bridge.rows.array_hash(normalized)}
            for key, value in (("native", raw), ("normalized", normalized)):
                p = directory / f"row{row:02d}.{key}.npy"
                bridge.rows.atomic_npy(p, value)
                record[key + "_file_sha256"] = bridge.rows.file_hash(p)
            record = bridge.rows.seal(record)
            bridge.rows.atomic_json(directory / f"row{row:02d}.json", record)
            inventory.append(record)
        identity = {"url": definition["url"], "size": definition["expected_remote_size_bytes"],
                    "etag": definition["expected_etag"]}
        checkpoint = {"artifact_type": transport.CHECKPOINT_ARTIFACT, "schema_version": 1,
                      "remote": identity, "segments": []}
        checkpoint["checkpoint_sha256"] = transport._sha256_bytes(transport._canonical_json_bytes(checkpoint))
        proof = {"kind": "local-HDF5-over-simulated-HTTP", "identity": identity,
                 "range_plan_file_sha256": bridge.rows.digest({"unit": index}),
                 "checkpoint": checkpoint, "hdf5_runtime": bridge.codec.runtime(),
                 "dataset_filters": bridge.filters.declared(definition, required=True)}
        receipt = bridge.rows._complete(directory, scope, inventory, proof)
        entries.append({"label": label, "scope": scope, "receipt_sha256": receipt["receipt_sha256"]})
        directories[label] = directory
    p = json.loads(c.factor_contract.factors.provenance_json)
    manifest = {"schema": bridge.SCHEMA, "domain": "local-fixture", **bridge.receiver_window(c),
                "context_sha256": c.identity, "receiver_factor_bank_sha256": c.factor_contract.factors.identity,
                "receiver_source_contract_sha256": p["source_contract_sha256"],
                "fixture_source_contract_sha256": fixture_hash, "runtime": bridge.codec.runtime(),
                "scans": entries}
    return manifest, directories


class LocalReceiverCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="new-local-receiver-rows-")
        cls.contexts = {role: context(role) for role in bridge.ROLES}
        cls.c = cls.contexts["validation"]
        cls.manifest, cls.directories = fixtures(Path(cls.temp.name), cls.c)
        cls.binding = bridge.bind(cls.manifest, bridge.rows.digest(cls.manifest), cls.c)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_pre_read_rejection(self, manifest=None, directories=None):
        with patch.object(np, "load", side_effect=AssertionError("row read before metadata rejection")):
            with self.assertRaises(ValueError):
                m = self.manifest if manifest is None else manifest
                b = bridge.bind(m, bridge.rows.digest(m), self.c)
                bridge.fixture_run(self.c, b, self.directories if directories is None else directories)

    def test_success_exact_six_fresh_sources_without_execution(self):
        methods = ("build_store", "cache", "calibrate", "execute", "receiver")
        with patch.object(np.random, "default_rng", side_effect=AssertionError("RNG invocation")):
            patches = [patch.object(bridge.pipeline.NativeRun, m,
                       side_effect=AssertionError("downstream execution invocation")) for m in methods]
            for p in patches:
                p.start()
            try:
                run, receipt = bridge.fixture_run(self.c, self.binding, self.directories)
            finally:
                for p in reversed(patches):
                    p.stop()
        self.assertEqual(set(run.sources), set(bridge.received.LABELS))
        self.assertEqual(len(set(run.source_ids.values())), 6)
        self.assertEqual(receipt["unique_raw_payloads"], 6)
        self.assertEqual(receipt["unique_normalized_payloads"], 6)
        self.assertEqual(receipt["context_sha256"], self.c.identity)
        self.assertFalse(receipt["telescope_provenance_established"])
        for key in ("reduction_invoked", "scoring_invoked", "rng_invoked", "controls_invoked"):
            self.assertIs(receipt[key], False)
        bridge.rows.verify(receipt)
        for source in run.sources.values():
            bridge.native.validate_source(source)
            self.assertFalse(source.values.flags.writeable)

    def test_receiver_roles_are_exactly_bound(self):
        # Every role builds its own pinned context. Metadata adapted to the role
        # is accepted; validation receipts cannot cross into another role.
        for role, c in self.contexts.items():
            m = copy.deepcopy(self.manifest)
            m.update(bridge.receiver_window(c), context_sha256=c.identity,
                     receiver_factor_bank_sha256=c.factor_contract.factors.identity)
            for entry in m["scans"]:
                old = entry["scope"]
                entry["scope"] = bridge.rows.make_scope(old["definition"], c.window,
                    c.native_window["archive_interval"], old["contract_sha256"], "local-fixture")
            b = bridge.bind(m, bridge.rows.digest(m), c)
            with patch.object(np, "load", side_effect=AssertionError("wrong-role row read")):
                if role != "validation":
                    with self.assertRaises(ValueError):
                        bridge.fixture_run(c, b, self.directories)

    def test_self_selected_manifest_digest_is_not_accepted(self):
        with self.assertRaises(ValueError):
            bridge.bind(self.manifest, "a" * 64, self.c)

    def test_inventory_order_label_role_and_receipt_duplicates_reject_before_rows(self):
        for change in (
            lambda m: m["scans"].reverse(),
            lambda m: m["scans"][1].update(label="epoch1_on"),
            lambda m: m["scans"][0]["scope"]["definition"].update(role="off"),
            lambda m: m["scans"][1].update(receipt_sha256=m["scans"][0]["receipt_sha256"]),
        ):
            m = copy.deepcopy(self.manifest)
            change(m)
            self.assert_pre_read_rejection(m)

    def test_source_header_chunk_filter_geometry_and_normalization_guards(self):
        for change in (
            lambda m: m["scans"][0]["scope"]["definition"]["expected_header"].update(tstart_mjd=1),
            lambda m: m["scans"][0]["scope"]["definition"].update(expected_chunks=[1, 1, 8192]),
            lambda m: m["scans"][0]["scope"]["definition"].update(observed_hdf5_filters=[]),
            lambda m: m["scans"][0]["scope"]["geometry"].update(raw_zero_hz=0),
            lambda m: m["scans"][0]["scope"].update(normalization="different-origin"),
            lambda m: m.update(role="pilot"),
            lambda m: m.update(context_sha256="b" * 64),
            lambda m: m.update(receiver_factor_bank_sha256="c" * 64),
            lambda m: m["scans"][0]["scope"]["definition"]["expected_header"]["dataset_shape"].__setitem__(1, True),
            lambda m: m["scans"][0]["scope"]["definition"]["expected_header"]["dataset_shape"].__setitem__(2, 264503296.0),
            lambda m: m["geometry"].update(channel_count=65536.0),
            lambda m: m["scans"][0]["scope"]["geometry"].update(channel_count=65536.0),
        ):
            m = copy.deepcopy(self.manifest)
            change(m)
            self.assert_pre_read_rejection(m)

    def test_real_urls_telescope_kind_credentials_and_query_reject_before_rows(self):
        for url in ("https://bldata.berkeley.edu/example.h5", "https://x.invalid.evil/example.h5",
                    "https://me@x.invalid/example.h5", "https://x.invalid/example.h5?q=1",
                    "http://x.invalid/example.h5", "https://x.invalid:443/example.h5"):
            m = copy.deepcopy(self.manifest)
            m["scans"][0]["scope"]["definition"]["url"] = url
            self.assert_pre_read_rejection(m)
        m = copy.deepcopy(self.manifest)
        m["scans"][0]["scope"]["kind"] = "telescope-remote"
        self.assert_pre_read_rejection(m)

    def test_wrong_last_receipt_is_rejected_before_any_rows(self):
        # Corruption in scan six must be detected before reading scan one.
        p = self.directories[bridge.received.LABELS[-1]] / "source.json"
        original = p.read_bytes()
        try:
            value = json.loads(original)
            value["transport"]["kind"] = "live-identity-bound-http-ranges"
            value = bridge.rows.seal({k: v for k, v in value.items() if k != "receipt_sha256"})
            p.write_bytes(bridge.core.canonical_json_bytes(value))
            self.assert_pre_read_rejection()
        finally:
            p.write_bytes(original)

    def test_resealed_untrusted_receipt_rejects_before_rows(self):
        p = self.directories[bridge.received.LABELS[0]] / "source.json"
        original = p.read_bytes()
        try:
            value = json.loads(original)
            value["rows"][0]["native_sha256"] = "d" * 64
            value = bridge.rows.seal({k: v for k, v in value.items() if k != "receipt_sha256"})
            p.write_bytes(bridge.core.canonical_json_bytes(value))
            self.assert_pre_read_rejection()
        finally:
            p.write_bytes(original)

    def test_oversized_source_and_row_metadata_refuse_before_payload_reads(self):
        for name, maximum in (("source.json", bridge.MAX_SOURCE_JSON_BYTES),
                              ("row00.json", bridge.MAX_ROW_JSON_BYTES)):
            p = self.directories[bridge.received.LABELS[0]] / name
            original = p.read_bytes()
            try:
                p.write_bytes(b" " * (maximum + 1))
                self.assert_pre_read_rejection()
            finally:
                p.write_bytes(original)

    def test_source_metadata_fifo_refuses_without_blocking(self):
        p = self.directories[bridge.received.LABELS[0]] / "source.json"
        original = p.read_bytes()
        try:
            p.unlink()
            os.mkfifo(p)
            self.assert_pre_read_rejection()
        finally:
            p.unlink(missing_ok=True)
            p.write_bytes(original)

    def test_authenticated_transport_checkpoint_and_row_type_aliases_reject_before_rows(self):
        p = self.directories[bridge.received.LABELS[0]] / "source.json"
        original = p.read_bytes()
        for change in (
            lambda v: v["transport"]["checkpoint"].update(schema_version=True),
            lambda v: v["transport"]["checkpoint"]["remote"].update(size=10000000.0),
            lambda v: v["rows"][0].update(row=False),
            lambda v: v["transport"].update(dataset_filters=[]),
            lambda v: v["transport"].update(kind="live-identity-bound-http-ranges"),
        ):
            try:
                value = json.loads(original)
                change(value)
                checkpoint = value["transport"]["checkpoint"]
                basis = {k: v for k, v in checkpoint.items() if k != "checkpoint_sha256"}
                checkpoint["checkpoint_sha256"] = transport._sha256_bytes(transport._canonical_json_bytes(basis))
                value["rows"][0] = bridge.rows.seal({k: v for k, v in value["rows"][0].items()
                                                   if k != "receipt_sha256"})
                value = bridge.rows.seal({k: v for k, v in value.items() if k != "receipt_sha256"})
                m = copy.deepcopy(self.manifest)
                m["scans"][0]["receipt_sha256"] = value["receipt_sha256"]
                p.write_bytes(bridge.core.canonical_json_bytes(value))
                self.assert_pre_read_rejection(m)
            finally:
                p.write_bytes(original)

    def test_row_byte_corruption_fails_rehydrate(self):
        p = self.directories[bridge.received.LABELS[0]] / "row00.native.npy"
        original = p.read_bytes()
        try:
            damaged = bytearray(original)
            damaged[-1] ^= 1
            p.write_bytes(damaged)
            with self.assertRaisesRegex(ValueError, "row file hash mismatch"):
                bridge.fixture_run(self.c, self.binding, self.directories)
        finally:
            p.write_bytes(original)

    def test_owned_row_rehashed_after_rehydrate(self):
        original_rehydrate = bridge.rows.rehydrate
        p = self.directories[bridge.received.LABELS[0]] / "row00.native.npy"
        original = p.read_bytes()

        def raced_rehydrate(*args, **kwargs):
            result = original_rehydrate(*args, **kwargs)
            damaged = bytearray(original)
            damaged[-1] ^= 1
            p.write_bytes(damaged)
            return result

        try:
            with patch.object(bridge.rows, "rehydrate", side_effect=raced_rehydrate):
                with self.assertRaisesRegex(ValueError, "native row file changed after receipt verification"):
                    bridge.fixture_run(self.c, self.binding, self.directories)
        finally:
            p.write_bytes(original)

    def test_oversized_row_header_after_rehydrate_rejects_without_np_load(self):
        original_rehydrate = bridge.rows.rehydrate
        p = self.directories[bridge.received.LABELS[0]] / "row00.native.npy"
        original = p.read_bytes()

        def raced_rehydrate(*args, **kwargs):
            result = original_rehydrate(*args, **kwargs)
            # A v2 declared header length must be bounded before parser reads.
            p.write_bytes(b"\x93NUMPY\x02\x00" + struct.pack("<I", 0xffffffff)
                          + bytes(self.c.geometry.channel_count * 4))
            return result

        try:
            with patch.object(bridge.rows, "rehydrate", side_effect=raced_rehydrate):
                with self.assertRaisesRegex(ValueError, "oversized native row NPY header before allocation"):
                    bridge.fixture_run(self.c, self.binding, self.directories)
        finally:
            p.write_bytes(original)

    def test_huge_shape_after_rehydrate_rejects_without_payload_allocation(self):
        original_rehydrate = bridge.rows.rehydrate
        p = self.directories[bridge.received.LABELS[0]] / "row00.native.npy"
        original = p.read_bytes()

        def raced_rehydrate(*args, **kwargs):
            result = original_rehydrate(*args, **kwargs)
            header = str({"descr": "<f4", "fortran_order": False, "shape": (2**40,)})
            encoded = (header + "\n").encode("latin1")
            p.write_bytes(b"\x93NUMPY\x01\x00" + struct.pack("<H", len(encoded)) + encoded
                          + bytes(self.c.geometry.channel_count * 4))
            return result

        try:
            with patch.object(bridge.rows, "rehydrate", side_effect=raced_rehydrate):
                with self.assertRaisesRegex(ValueError, "native row shape/dtype/size changed before allocation"):
                    bridge.fixture_run(self.c, self.binding, self.directories)
        finally:
            p.write_bytes(original)

    def test_fifo_and_symlink_after_rehydrate_refused_before_header_read(self):
        original_rehydrate = bridge.rows.rehydrate
        p = self.directories[bridge.received.LABELS[0]] / "row00.native.npy"
        original = p.read_bytes()
        for kind in ("fifo", "symlink"):
            def raced_rehydrate(*args, **kwargs):
                result = original_rehydrate(*args, **kwargs)
                p.unlink()
                if kind == "fifo":
                    os.mkfifo(p)
                else:
                    p.symlink_to(p.with_name("row01.native.npy"))
                return result
            try:
                with patch.object(bridge.rows, "rehydrate", side_effect=raced_rehydrate):
                    with self.assertRaises((ValueError, OSError)):
                        bridge.fixture_run(self.c, self.binding, self.directories)
            finally:
                p.unlink(missing_ok=True)
                p.write_bytes(original)

    def test_normalized_output_hashes_are_checked(self):
        original = bridge.native.normalize_synthetic_rows

        def wrong_normalizer(*args, **kwargs):
            source = original(*args, **kwargs)
            values = source.values.copy()
            values[0, 0] += np.float32(1)
            return replace(source, values=bridge.native.immutable(values))

        with patch.object(bridge.native, "normalize_synthetic_rows", side_effect=wrong_normalizer):
            with self.assertRaisesRegex(ValueError, "local codec/receiver normalization differs"):
                bridge.fixture_run(self.c, self.binding, self.directories)

    def test_directory_duplicates_and_missing_slots_reject_before_rows(self):
        d = dict(self.directories)
        d.pop(bridge.received.LABELS[-1])
        self.assert_pre_read_rejection(directories=d)
        d = dict(self.directories)
        d[bridge.received.LABELS[-1]] = d[bridge.received.LABELS[0]]
        self.assert_pre_read_rejection(directories=d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
