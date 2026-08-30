"""Synthetic restart and identity tests for the M37 sparse range transport."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater import http_range_v0p6 as transport


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _Response:
    def __init__(self, payload: bytes, headers: dict[str, str], status: int) -> None:
        self._payload = payload
        self.headers = _Headers(headers)
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None


def _server(payload: bytes, etag: str = '"exact"'):
    calls: list[tuple[int, int]] = []

    def open_request(request, timeout=0):
        if request.get_method() == "HEAD":
            return _Response(
                b"",
                {
                    "Content-Length": str(len(payload)),
                    "ETag": etag,
                    "Accept-Ranges": "bytes",
                },
                200,
            )
        value = request.headers["Range"]
        start_text, stop_text = value.removeprefix("bytes=").split("-")
        start, stop = int(start_text), int(stop_text)
        calls.append((start, stop + 1))
        body = payload[start : stop + 1]
        return _Response(
            body,
            {
                "Content-Range": f"bytes {start}-{stop}/{len(payload)}",
                "Content-Length": str(len(body)),
                "ETag": etag,
            },
            206,
        )

    return calls, open_request


class SparseRangeMirrorTests(unittest.TestCase):
    def test_head_prefetch_read_and_exact_restart(self):
        payload = bytes(range(256)) * 64
        calls, server = _server(payload)
        with tempfile.TemporaryDirectory() as directory, patch.object(
            transport, "urlopen", side_effect=server
        ):
            identity = transport.remote_identity("https://example.invalid/data.h5")
            self.assertEqual(identity.size, len(payload))
            path = Path(directory) / "mirror.h5"
            with transport.SparseRangeMirror(path, identity, workers=3) as mirror:
                mirror.prefetch(
                    (
                        transport.ByteRange(100, 300),
                        transport.ByteRange(900, 1200),
                    )
                )
                self.assertEqual(mirror.downloaded_bytes, 500)
                mirror.seek(100)
                self.assertEqual(mirror.read(200), payload[100:300])
                self.assertEqual(len(calls), 2)
                checkpoint = json.loads(mirror.checkpoint_path.read_bytes())
                self.assertEqual(len(checkpoint["segments"]), 2)
                self.assertEqual(
                    checkpoint["segments"][0]["sha256"],
                    hashlib.sha256(payload[100:300]).hexdigest(),
                )

            calls.clear()
            with transport.SparseRangeMirror(path, identity) as reopened:
                reopened.seek(900)
                self.assertEqual(reopened.read(300), payload[900:1200])
                self.assertEqual(reopened.downloaded_bytes, 500)
            self.assertEqual(calls, [])

    def test_on_demand_read_ahead_is_checkpointed(self):
        payload = os.urandom(5 * 1024 * 1024)
        calls, server = _server(payload)
        with tempfile.TemporaryDirectory() as directory, patch.object(
            transport, "urlopen", side_effect=server
        ):
            identity = transport.RemoteIdentity(
                "https://example.invalid/data.h5", len(payload), '"exact"'
            )
            with transport.SparseRangeMirror(
                Path(directory) / "mirror.h5", identity
            ) as mirror:
                mirror.seek(17)
                self.assertEqual(mirror.read(32), payload[17:49])
                self.assertEqual(
                    calls, [(17, 17 + transport.ON_DEMAND_READ_AHEAD_BYTES)]
                )
                self.assertEqual(
                    mirror.downloaded_bytes, transport.ON_DEMAND_READ_AHEAD_BYTES
                )

    def test_payload_tamper_and_response_identity_fail_closed(self):
        payload = bytes(range(100))
        _, server = _server(payload)
        with tempfile.TemporaryDirectory() as directory, patch.object(
            transport, "urlopen", side_effect=server
        ):
            identity = transport.RemoteIdentity(
                "https://example.invalid/data.h5", len(payload), '"exact"'
            )
            path = Path(directory) / "mirror.h5"
            with transport.SparseRangeMirror(path, identity) as mirror:
                mirror.prefetch((transport.ByteRange(5, 20),))
            with path.open("r+b") as stream:
                stream.seek(5)
                stream.write(b"X")
            with self.assertRaisesRegex(RuntimeError, "payload digest"):
                transport.SparseRangeMirror(path, identity)

        def wrong_response(request, timeout=0):
            return _Response(
                payload[:10],
                {
                    "Content-Range": f"bytes 0-9/{len(payload)}",
                    "ETag": '"wrong"',
                },
                206,
            )

        with tempfile.TemporaryDirectory() as directory, patch.object(
            transport, "urlopen", side_effect=wrong_response
        ), patch.object(transport.time, "sleep"):
            identity = transport.RemoteIdentity(
                "https://example.invalid/data.h5", len(payload), '"exact"'
            )
            with transport.SparseRangeMirror(
                Path(directory) / "mirror.h5", identity, retries=2
            ) as mirror:
                with self.assertRaisesRegex(RuntimeError, "retry budget"):
                    mirror.prefetch((transport.ByteRange(0, 10),))

    def test_range_plan_and_chunk_discovery_are_exact(self):
        class Info:
            def __init__(self, byte_offset, size):
                self.byte_offset = byte_offset
                self.size = size

        class Identifier:
            @staticmethod
            def get_chunk_info_by_coord(coord):
                integration, _, channel = coord
                return Info(1000 + integration * 100 + channel, 50)

        class Dataset:
            shape = (2, 1, 20)
            chunks = (1, 1, 10)
            id = Identifier()

        ranges = transport.discover_hdf5_chunk_ranges(
            Dataset(), ((2, 4), (11, 19))
        )
        self.assertEqual(len(ranges), 4)
        identity = transport.RemoteIdentity(
            "https://example.invalid/data.h5", 10_000, '"exact"'
        )
        record = transport.range_plan_record(
            identity,
            dataset_shape=Dataset.shape,
            dataset_chunks=Dataset.chunks,
            channel_intervals=((2, 4), (11, 19)),
            ranges=ranges,
        )
        self.assertEqual(record["range_count"], 4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            first = transport.publish_range_plan(path, record)
            second = transport.publish_range_plan(path, record)
            self.assertEqual(first, second)
            changed = dict(record)
            changed["payload_nbytes"] += 1
            with self.assertRaisesRegex(RuntimeError, "differs"):
                transport.publish_range_plan(path, changed)


if __name__ == "__main__":
    unittest.main()
