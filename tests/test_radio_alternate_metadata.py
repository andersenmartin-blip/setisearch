"""New source-admission, coordinate and filter-metadata boundaries only."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import radio_alternate_metadata_20260927 as m


class AlternateMetadataTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / m.CONFIG).read_text())
        self.entry = self.cfg["shortlist"][0]
        self.urls = [self.entry["primary_url"]] + [self.entry["session_prefix"] + f"test_{i}.gpuspec.0000.h5" for i in range(5)]
        self.rows = [{"url": u} for u in self.urls]

    def test_fixed_order_and_three_period_slots(self):
        self.assertEqual([(e["rank"], e["cadence_id"]) for e in self.cfg["shortlist"]], [(41,85030),(43,73005)])
        self.assertEqual(self.cfg["shortlist_slots_including_hd1461"], 3)
        self.assertEqual(self.cfg["max_combined_source_screen_usage"]["requests"], 283)
        self.assertEqual(self.cfg["preceding_source_screen_usage"]["requests"], 83)

    def test_every_prior_or_reserved_overlap_rejected(self):
        for u in self.urls:
            with self.subTest(url=u), self.assertRaises(m.previous.Stop):
                m.validate_catalogue(self.rows, self.entry, {u})
        self.assertEqual(m.validate_catalogue(self.rows,self.entry,set()), sorted(self.urls))

    def test_partial_foreign_or_missing_primary_catalogue_rejected(self):
        for rows in [self.rows[:-1], self.rows[1:]+[{"url":self.entry["session_prefix"]+"extra.gpuspec.0000.h5"}], self.rows[:-1]+[{"url":"https://example.org/other.gpuspec.0000.h5"}]]:
            with self.subTest(rows=rows), self.assertRaises(m.previous.Stop):
                m.validate_catalogue(rows,self.entry,set())

    def test_ra_hours_and_wrap_in_pointing_comparison(self):
        e={"planet_name":"test b","host":"test","archive_target":"HIP1"}
        h=[{"url":str(i),"data_attributes":{"source_name":"HIP1","src_raj":23.9999,"src_dej":20}} for i in range(3)]
        r=[{"pl_name":"test b","hostname":"test","hip_name":"HIP 1","ra":.0015,"dec":20}]
        self.assertTrue(all(c["within_fixed_proximity"] for c in m.pointing_checks(h,r,e,60)))
        r[0]["dec"]=21
        self.assertFalse(any(c["within_fixed_proximity"] for c in m.pointing_checks(h,r,e,60)))
        r[0]["hip_name"]="HIP2"
        with self.assertRaises(m.previous.Stop): m.pointing_checks(h,r,e,60)

    def test_unknown_endpoint_refused_before_transport_charge(self):
        with tempfile.TemporaryDirectory() as d:
            t=m.Transport(self.cfg,Path(d))
            with self.assertRaises(m.previous.Stop): t.request("https://example.org/metadata")
            self.assertEqual(t.requests,0)

    def test_filter_declaration_read_without_spectral_chunk_contact(self):
        import h5py
        import numpy as np
        buf=io.BytesIO()
        with h5py.File(buf,"w") as f:
            ds=f.create_dataset("data",data=np.ones((2,1,32),dtype="<f4"),chunks=(1,1,32),compression="gzip")
            ds.attrs["source_name"]="fixture"
            chunks=[(ds.id.get_chunk_info(i).byte_offset,ds.id.get_chunk_info(i).size) for i in range(ds.id.get_num_chunks())]
        raw=buf.getvalue()
        class Fake:
            b={"per_header_bytes":524288}
            def __init__(self):self.ranges=[]
            def request(self,url,method="GET",headers=None,limit=None):
                if method=="HEAD":return b"",{"content-length":str(len(raw)),"etag":'"fixture"',"accept-ranges":"bytes"},200
                a,z=map(int,headers["Range"][6:].split("-"));self.ranges.append((a,z))
                return raw[a:z+1],{"etag":'"fixture"',"content-range":f"bytes {a}-{z}/{len(raw)}"},206
        t=Fake();r=m.header(t,"fixture")
        self.assertEqual(r["hdf5_filters"][0][0],1)
        self.assertFalse(r["spectral_dataset_values_read"])
        self.assertTrue(all(z<s or a>=s+n for a,z in t.ranges for s,n in chunks))


if __name__ == "__main__": unittest.main()
