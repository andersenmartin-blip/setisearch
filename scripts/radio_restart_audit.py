#!/usr/bin/env python3
"""Offline receipt replay and final restart audit; no network or spectra."""
import base64
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

import h5py

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results_radio_restart_2026-09-26"


def read(path): return json.loads((ROOT/path).read_text())


def scalar(v):
    if hasattr(v,"tolist"):v=v.tolist()
    if isinstance(v,bytes):return v.decode()
    if isinstance(v,(tuple,list)):return [scalar(x) for x in v]
    return v


class OfflineRanges(io.RawIOBase):
    def __init__(self,size,segments):self.size,self.segments,self.pos=size,segments,0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        assert 0<=self.pos<=self.size
        return self.pos
    def readinto(self,b):
        assert len(b)<524288
        count=min(len(b),self.size-self.pos)
        for i in range(count):
            matches=[raw[self.pos+i-start] for start,raw in self.segments if start<=self.pos+i<start+len(raw)]
            assert matches and len(set(matches))==1,"Missing or inconsistent retained header byte"
            b[i]=matches[0]
        self.pos+=count
        return count


def main():
    cfg=read("config/radio_restart_metadata_20260926.json")
    first=read("results_radio_restart_2026-09-26/metadata_result.json")
    latest=read("results_radio_restart_2026-09-26/attempt02/metadata_result.json")
    first_receipts=read("results_radio_restart_2026-09-26/transport_receipts.json")
    receipts=read("results_radio_restart_2026-09-26/attempt02/transport_receipts.json")
    native=read("results_radio_restart_2026-09-26/attempt02/pilot_headers.json")
    payload_bytes=0;segments={};heads={}
    for r in receipts:
        assert "error" not in r and r["status"] in (200,206)
        raw=base64.b64decode(r["body_base64"],validate=True)
        assert len(raw)==r["bytes"] and hashlib.sha256(raw).hexdigest()==r["sha256"]
        payload_bytes+=len(raw)
        if r["method"]=="HEAD":heads[r["url"]]=r
        if "Range" in r["request_headers"]:
            a,z=map(int,re.fullmatch(r"bytes=(\d+)-(\d+)",r["request_headers"]["Range"]).groups())
            assert z-a+1==len(raw)
            segments.setdefault(r["url"],[]).append((a,raw))
    assert first["transport"]["bytes"]==0 and len(first_receipts)==2
    assert payload_bytes==latest["transport"]["bytes"]
    assert len(first_receipts)+len(receipts)==latest["transport"]["requests"]
    assert latest["transport"]["bytes"]<cfg["budgets"]["total_bytes"]
    assert latest["transport"]["requests"]<=cfg["budgets"]["requests"]
    assert latest["transport"]["seconds"]<cfg["budgets"]["seconds"]
    assert [h["url"] for h in native]==cfg["pilot"]["scan_urls"]
    assert len(native)==len(heads)==len(segments)==6
    replayed=[]
    for h in native:
        with OfflineRanges(h["remote_size_bytes"],segments[h["url"]]) as remote:
            with h5py.File(remote,"r") as f:
                d=f["data"]
                assert {k:scalar(v) for k,v in f.attrs.items()}==h["root_attributes"]
                assert {k:scalar(v) for k,v in d.attrs.items()}==h["data_attributes"]
                assert list(d.shape)==h["dataset_shape"] and str(d.dtype)==h["dataset_dtype"]
                assert list(d.chunks)==h["dataset_chunks"]
        old=next(x for x in cfg["pilot"]["headers"] if x["url"]==h["url"])
        for k in ("etag","remote_size_bytes","root_attributes","data_attributes","dataset_shape","dataset_dtype","dataset_chunks"):
            assert old[k]==h[k]
        replayed.append(dict(url=h["url"],metadata_replayed=True,spectral_dataset_values_read=False))
    raw=(OUT/"astrometry/official_response.json").read_bytes()
    astro=read("results_radio_restart_2026-09-26/astrometry/result.json")
    assert hashlib.sha256(raw).hexdigest()==astro["response_sha256"]
    assert json.loads(raw)==[astro["record"]] and not astro["missing_fields"]
    candidates=read("results_radio_restart_2026-09-26/candidate_register.json")
    assert dict(Counter(x["latest_recorded_classification"] for x in candidates["candidates"]))==candidates["classifications"]
    assert candidates["candidate_count"]==len(candidates["candidates"])
    pointing=read("results_radio_restart_2026-09-26/pointing/result.json")
    pointing_receipts=read("results_radio_restart_2026-09-26/pointing/transport_receipts.json")
    pointing_rows=read("results_radio_restart_2026-09-26/pointing/target_only_catalogue.json")
    assert len(pointing_receipts)==1
    pr=pointing_receipts[0];pb=base64.b64decode(pr["body_base64"],validate=True)
    assert hashlib.sha256(pb).hexdigest()==pr["sha256"] and len(pb)==pr["bytes"]
    pd=json.loads(pb);assert pd["result"]=="success" and pd["data"]==pointing_rows
    assert pointing["total_rows"]==len(pointing_rows)<2000
    starts={c["start_mjd"] for c in pointing["comparisons"]}
    matched=[r for r in pointing_rows if r.get("target")=="HIP1499" and r.get("mjd") in starts]
    assert matched==pointing["same_on_scan_rows"]
    assert [r for r in matched if str(r.get("url","")).lower().endswith((".fil",".raw"))]==pointing["matching_original_products"]
    assert len(pointing["comparisons"])==3 and pointing["automatic_coordinate_correction_applied"] is False
    assert all(abs(c["separation_arcmin"]-c["astropy_separation_arcmin"])<1e-8 for c in pointing["comparisons"])
    final=dict(audit_passed=True,receipt_payload_hashes_verified=len(receipts),metadata_bytes_verified=payload_bytes,
        offline_hdf5_header_replays=replayed,official_record_verified=True,candidate_register_verified=True,
        pointing_arithmetic_agrees=True,pointing_catalogue_verified=True,scientific_readiness="HOLD_POINTING_PROVENANCE_UNRESOLVED",
        source_identity_check_passed=True,calibration_or_search_run=False,spectral_dataset_values_read=False,
        note="Audit success certifies the retained metadata/evidence accounting; it does not resolve the pointing discrepancy or qualify a detector.")
    (OUT/"audit.json").write_text(json.dumps(final,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in final.items() if k!="offline_hdf5_header_replays"},indent=2))


if __name__=="__main__":main()
