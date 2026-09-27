#!/usr/bin/env python3
"""Replay the new metadata receipts offline and bind a preparation contract."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

import radio_alternate_metadata_20260927 as screen
from seti_repeater import source_radio, source_m43h

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results_radio_alternate_2026-09-27"
ATTEMPT = BASE / "attempt01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


class ReceiptReplay:
    """Return only bytes present in recorded successful metadata ranges."""
    b = {"per_header_bytes": 524288}

    def __init__(self, receipts, url):
        self.url = url
        own = [r for r in receipts if r["url"] == url]
        heads = [r for r in own if r["method"] == "HEAD" and r.get("status") == 200]
        if len(heads) != 1:
            raise ValueError("Expected one retained HEAD per source")
        self.http = {k.lower(): v for k,v in heads[0]["response_headers"].items()}
        self.size = int(self.http["content-length"])
        self.etag = self.http["etag"]
        self.data = {}
        self.verified_ranges = 0
        for r in own:
            if r["method"] != "GET":
                continue
            a,z = map(int, re.fullmatch(r"bytes=(\d+)-(\d+)", r["request_headers"]["Range"]).groups())
            body = base64.b64decode(r["body_base64"], validate=True)
            h = {k.lower():v for k,v in r["response_headers"].items()}
            if (r.get("status") != 206 or r["request_headers"].get("If-Match") != self.etag
                or h.get("etag") != self.etag or h.get("content-range") != f"bytes {a}-{z}/{self.size}"
                or len(body) != z-a+1 or hashlib.sha256(body).hexdigest() != r["body_sha256"]):
                raise ValueError("Retained range identity/hash mismatch")
            for offset, value in enumerate(body,a):
                if offset in self.data and self.data[offset] != value:
                    raise ValueError("Overlapping metadata ranges disagree")
                self.data[offset] = value
            self.verified_ranges += 1
        self.calls = 0

    def request(self, url, method="GET", headers=None, limit=None):
        if url != self.url:
            raise ValueError("Replay cannot fetch another source")
        self.calls += 1
        if method == "HEAD":
            return b"", self.http, 200
        a,z=map(int, re.fullmatch(r"bytes=(\d+)-(\d+)",headers["Range"]).groups())
        if headers.get("If-Match") != self.etag:
            raise ValueError("Replay ETag changed")
        try:
            body=bytes(self.data[i] for i in range(a,z+1))
        except KeyError as error:
            raise ValueError("Replay requested an unrecorded byte; no network fallback") from error
        return body, {"etag":self.etag,"content-range":f"bytes {a}-{z}/{self.size}"},206


def main():
    result = json.loads((ATTEMPT / "result.json").read_text())
    cfg = json.loads((ROOT / screen.CONFIG).read_text())
    selected = result["selected"]
    if result["status"] != "NEW_SOURCE_PREPARATION_SELECTED" or not selected:
        raise ValueError("No completed consistent metadata selection to prepare")
    entry = next(e for e in cfg["shortlist"] if e["cadence_id"] == selected["cadence_id"])
    directory = ATTEMPT / str(selected["cadence_id"])
    headers = json.loads((directory / "headers.json").read_text())
    receipts = json.loads((ATTEMPT / "transport_receipts.json").read_text())
    rows = json.loads((directory / "catalogue.json").read_text())
    inventory = json.loads((ROOT / screen.INVENTORY).read_text())
    deny = {s["url"] for s in inventory["sources"]}
    screen.validate_catalogue(rows,entry,deny)
    fields = ("url","remote_size_bytes","etag","data_attributes","root_attributes",
              "dataset_shape","dataset_dtype","dataset_chunks","hdf5_filters","spectral_dataset_values_read")
    replays = []
    scans = []
    for index,h in enumerate(headers):
        replay = ReceiptReplay(receipts,h["url"])
        again = screen.header(replay,h["url"])
        if any(again[k] != h[k] for k in fields):
            raise ValueError("Offline metadata replay differs from retained parse")
        a=h["data_attributes"]
        if a["nchans"] != h["dataset_shape"][2] or a["nifs"] != h["dataset_shape"][1] or a["nbits"] != 32:
            raise ValueError("Stored dtype/axis geometry disagrees with header attributes")
        role="on" if index%2==0 else "off"
        scans.append({"label":f"epoch{index//2+1}_{role}","role":role,"url":h["url"],
            "expected_remote_size_bytes":h["remote_size_bytes"],"expected_etag":h["etag"],
            "expected_chunks":h["dataset_chunks"],"observed_hdf5_filters":h["hdf5_filters"],
            "expected_header":{"dataset_dtype":h["dataset_dtype"],"dataset_shape":h["dataset_shape"],
              "source_name":a["source_name"],"fch1_mhz":a["fch1"],"foff_mhz":a["foff"],
              "tstart_mjd":a["tstart"],"tsamp_s":a["tsamp"],"src_raj_hours":a["src_raj"],"src_dej_deg":a["src_dej"]}})
        replays.append({"url":h["url"],"verified_retained_ranges":replay.verified_ranges,
                       "unique_metadata_bytes":len(replay.data),"offline_reader_calls":replay.calls,
                       "metadata_and_filter_fields_match":True,"spectral_dataset_values_read":False})
    if not screen.previous.qualifying(headers,entry["archive_target"]):
        raise ValueError("Retained cadence qualification no longer agrees")
    official = json.loads((directory / "official_metadata.json").read_text())
    pointing = screen.pointing_checks(headers,official,entry,cfg["pointing_proximity_arcsec"])
    if not all(x["within_fixed_proximity"] for x in pointing):
        raise ValueError("Retained pointing proximity fails")
    source_id = source_m43h.digest(scans)
    evidence = {"schema":"radio-alternate-source-metadata-qualification-v1",
        "selected":selected,"source_inventory_sha256":source_id,
        "metadata_freeze_commit":result["freeze_commit"],"source_metadata_proximity_gate_passed":True,
        "pointing_scope":"Declared source identity and gross header/catalogue direction consistency within the prospective 60-arcsecond tolerance; no independent measured-pointing audit or epoch propagation.",
        "pointing_checks":pointing,"replayed_sources":replays,"network_requests":0,
        "spectral_dataset_values_read":False,"old_frozen_input_pins_unchanged":{},
        "physical_motion_bank_qualified":False,"telescope_codec_handoff_qualified":False,
        "cross_window_numeric_transfer_qualified":False,"recovery_rfi_null_evaluation_qualified":False}
    for path,expected in cfg["unchanged_science_pins"].items():
        raw=subprocess.check_output(["git","show",cfg["source_commit"]+":"+path],cwd=ROOT)
        if hashlib.sha256(raw).hexdigest()!=expected:
            raise ValueError("Prior evidence pin mismatch")
        if (ROOT/path).exists() and sha(ROOT/path)!=expected:
            raise ValueError("Locally retained prior evidence changed")
        evidence["old_frozen_input_pins_unchanged"][path]=expected
    evidence_path=BASE/"source_qualification.json"
    save(evidence_path,evidence)
    pins={p:sha(ROOT/p) for p in source_radio.IMPLEMENTATION_PATHS}
    for p in [ROOT/screen.CONFIG,ROOT/screen.PROTOCOL,ROOT/screen.SCRIPT,evidence_path,
              ATTEMPT/'result.json',ATTEMPT/'transport_receipts.json',directory/'headers.json',directory/'official_metadata.json']:
        pins[str(p.relative_to(ROOT))]=sha(p)
    contract={"artifact_type":"radio-source-contract-v1","stage":"preparation-only-no-spectral-access",
        "archive_target":entry["archive_target"],"cadence_id":entry["cadence_id"],
        "source_inventory_sha256":source_id,"scans":scans,"windows":[],"hdf5_runtime":None,
        "session_limits":{"max_requests":500,"max_bytes":536870912,"max_seconds":1200},
        "gates":{"pointing":{"status":"passed","source_inventory_sha256":source_id,
            "evidence_path":str(evidence_path.relative_to(ROOT)),"evidence_sha256":sha(evidence_path)},
            "prospective_protocol":{"status":"not-frozen-for-new-source"},
            "codec_integration":{"status":"not-qualified-for-this-source-contract"}},
        "pinned_files":pins,"notes":["New owner-authorized source; HD1461 preparation and unresolved hold remain unchanged.",
            "Pointing gate is the published metadata/proximity criterion, not an independent telescope measured-pointing calibration.",
            "Session limits are inactive ceilings; no telescope reservation, namespace activation or trial is performed.",
            "No old native sample, control-panel exposure, physical support or threshold calibration is transferred."]}
    name="hd189733" if entry['cadence_id']==85030 else "gj724"
    path=ROOT/f"config/radio_{name}_source_preparation_20260927.json"
    save(path,contract)
    _,validation=source_radio.load_contract(ROOT,str(path.relative_to(ROOT)),sha(path))
    if validation['status']!='BLOCKED' or validation['network_requests']!=0:
        raise ValueError("Preparation contract unexpectedly permits extraction")
    save(BASE/'preparation_validation.json',validation)
    first=scans[0]['expected_header']; last=scans[-1]['expected_header']
    duration=first['tsamp_s']*first['dataset_shape'][0]
    per_scan=[]
    for s in scans:
        a=s['expected_header']
        utc=datetime(1858,11,17,tzinfo=timezone.utc)+timedelta(seconds=round(a['tstart_mjd']*86400))
        per_scan.append({'label':s['label'],'source':a['source_name'],'utc_rounded_to_second':utc.isoformat(),
                         'mjd':a['tstart_mjd'],'integrations':a['dataset_shape'][0],'integration_seconds':a['tsamp_s']})
    save(BASE/'scan_geometry.json',{'selected':selected,'scans':per_scan,'duration_seconds_per_scan':duration,
        'start_to_start_span_seconds':(last['tstart_mjd']-first['tstart_mjd'])*86400,
        'first_start_to_last_end_seconds':(last['tstart_mjd']-first['tstart_mjd'])*86400+duration,
        'channel_width_hz':abs(first['foff_mhz'])*1e6,'frequency_endpoints_mhz':sorted([first['fch1_mhz'],first['fch1_mhz']+(first['dataset_shape'][2]-1)*first['foff_mhz']]),
        'unique_dates_in_this_cadence':1,'independent_repeat_observation_established':False,
        'spectral_dataset_values_read':False})
    print(json.dumps({'contract':str(path.relative_to(ROOT)),'source_inventory_sha256':source_id,
        'offline_replayed_sources':len(replays),'verified_ranges':sum(x['verified_retained_ranges'] for x in replays),
        'old_pins_verified':len(evidence['old_frozen_input_pins_unchanged']),
        'max_pointing_separation_arcsec':max(x['separation_arcsec'] for x in pointing),'readiness':validation},indent=2))


if __name__ == '__main__':main()
