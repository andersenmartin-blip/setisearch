"""Tests for the append-only M39 HTTP range store."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from seti_repeater import http_range_v0p6 as transport
from seti_repeater.immutable_range_store_v0p6 import ImmutableRangeStore


class ImmutableRangeStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = bytes((index * 17 + 3) % 256 for index in range(4096))
        self.identity = transport.RemoteIdentity(
            "https://example.invalid/archive.h5",
            12_700_000_000,
            '"frozen-etag"',
        )

    def _request(self, interval: transport.ByteRange) -> bytes:
        return self.payload[interval.start:interval.stop]

    def test_persists_only_requested_blobs_and_reopens(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "scan.store"
            with ImmutableRangeStore(root, self.identity, workers=1) as store:
                with mock.patch.object(store, "_request", side_effect=self._request):
                    store.prefetch((transport.ByteRange(16, 128),))
                store.seek(24)
                self.assertEqual(store.read(96), self.payload[24:120])
                self.assertEqual(store.downloaded_bytes, 112)
            blob_bytes = sum(
                path.stat().st_size for path in (root / "blobs").glob("*.range")
            )
            self.assertEqual(blob_bytes, 112)
            self.assertLess(blob_bytes, self.identity.size)
            with ImmutableRangeStore(root, self.identity, workers=1) as reopened:
                reopened.seek(24)
                self.assertEqual(reopened.read(96), self.payload[24:120])

    def test_checkpoint_binds_blob_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "scan.store"
            with ImmutableRangeStore(root, self.identity, workers=1) as store:
                with mock.patch.object(store, "_request", side_effect=self._request):
                    store.prefetch((transport.ByteRange(0, 64),))
            checkpoint = json.loads((root / "ranges.json").read_text())
            digest = checkpoint["segments"][0]["sha256"]
            self.assertEqual(digest, hashlib.sha256(self.payload[:64]).hexdigest())
            blob = root / "blobs" / f"{digest}.range"
            blob.write_bytes(b"x" * 64)
            with self.assertRaisesRegex(RuntimeError, "digest changed"):
                ImmutableRangeStore(root, self.identity, workers=1)

    def test_remote_identity_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "scan.store"
            ImmutableRangeStore(root, self.identity, workers=1).close()
            changed = transport.RemoteIdentity(
                self.identity.url, self.identity.size, '"different"'
            )
            with self.assertRaisesRegex(RuntimeError, "identity or schema"):
                ImmutableRangeStore(root, changed, workers=1)


if __name__ == "__main__":
    unittest.main()
