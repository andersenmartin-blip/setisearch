"""Changed transport boundary: real HDF5 metadata, fake HTTP, no live data."""
import importlib.util
import io
import unittest
from pathlib import Path

import h5py
import numpy as np

spec = importlib.util.spec_from_file_location(
    "radio_metadata", Path(__file__).resolve().parents[1] / "scripts/radio_restart_metadata.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MetadataTransportTest(unittest.TestCase):
    def setUp(self):
        buf = io.BytesIO()
        with h5py.File(buf, "w") as f:
            d = f.create_dataset("data", data=np.ones((16, 1, 64), dtype="<f4"), chunks=(1, 1, 64))
            d.attrs["source_name"] = "HIP1499"
            f.attrs["CLASS"] = "FILTERBANK"
            self.chunks = [(d.id.get_chunk_info(i).byte_offset, d.id.get_chunk_info(i).size)
                           for i in range(d.id.get_num_chunks())]
        self.raw = buf.getvalue()

    def fake(self, status=206, etag='"fixture"', total=None):
        raw = self.raw
        class Fake:
            b = {"per_header_bytes": 524288}
            def __init__(self): self.ranges = []
            def request(self, url, method="GET", headers=None, limit=None):
                if method == "HEAD":
                    return b"", {"content-length": str(len(raw)), "etag": '"fixture"', "accept-ranges": "bytes"}, 200
                a, z = map(int, headers["Range"][6:].split("-"))
                self.ranges.append((a, z))
                return raw[a:z + 1], {"content-range": f"bytes {a}-{z}/{len(raw) if total is None else total}", "etag": etag}, status
        return Fake()

    def test_attributes_without_spectral_chunk_reads(self):
        f = self.fake()
        observed = m.header(f, "https://bldata.berkeley.edu/fixture.h5")
        self.assertEqual(observed["dataset_shape"], [16, 1, 64])
        self.assertEqual(observed["data_attributes"]["source_name"], "HIP1499")
        self.assertTrue(all(z < s or a >= s + n for a, z in f.ranges for s, n in self.chunks))

    def test_source_and_range_integrity(self):
        for f in (self.fake(etag='"changed"'), self.fake(status=200), self.fake(total=1)):
            with self.subTest(transport=f), self.assertRaises(m.Stop):
                m.header(f, "https://bldata.berkeley.edu/fixture.h5")

    def test_unbounded_and_over_budget_reads(self):
        for count in (-1, 16):
            f = self.fake()
            f.b = {"per_header_bytes": 8}
            with self.subTest(count=count), self.assertRaises(m.Stop):
                m.RangeReader(f, "https://bldata.berkeley.edu/fixture.h5", len(self.raw), '"fixture"').read(count)
            self.assertFalse(f.ranges)


if __name__ == "__main__":
    unittest.main()
