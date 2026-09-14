#!/usr/bin/env python3
"""Reproduce LS7Q metadata accounting; no native science pixels are opened.

Python standard library only. Inputs are saved public archive HTML headers,
catalogue rows and request metadata. Optional --reference audits against the
timing arithmetic in the separately obtained, pinned official hcam.py source.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from types import SimpleNamespace

D = Decimal
SOURCE_COMMIT = "6a0b9a9d9053b831517a0aa4f8935e8878c3fc13"
SOURCE_SHA256 = "b73eb3001503ac62c7d97b083490a15e33b9e8222a6b0df86755b66b6ae9a6fb"


class HeaderHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.active = True

    def handle_endtag(self, tag):
        if tag == "pre":
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def read_header(path):
    parser = HeaderHTML()
    parser.feed(path.read_text(encoding="latin1"))
    fields = {}
    for line in "".join(parser.parts).splitlines():
        if "=" not in line:
            continue
        key, raw = line.split("=", 1)
        key = key.strip().removeprefix("HIERARCH ")
        raw = raw.strip()
        if raw.startswith("'"):
            value = raw[1:raw.index("'", 1)].strip()
        else:
            raw = raw.split("/", 1)[0].strip()
            if raw in ("T", "F"):
                value = raw == "T"
            else:
                try:
                    value = D(raw.replace("D", "E"))
                except Exception:
                    value = raw
        if key in fields and fields[key] != value:
            raise ValueError(f"Conflicting duplicate card: {key}")
        fields[key] = value
    if not {"SIMPLE", "BITPIX", "NAXIS3", "ORIGFILE", "IMAGETYP"} <= fields.keys():
        raise ValueError(f"No complete expected header in {path}")
    return fields


def timing(header, nskip, frame):
    """No-clear, non-drift intervals derived from the exposure start/end.

    Offsets are relative to a frame's timestamp, in seconds. The first real
    read in a channel has a shorter exposure; dummy frames are unavailable.
    """
    if frame < 1 or nskip < 0:
        raise ValueError("Positive frame and nonnegative nskip required")
    if header["ESO DET CLRCCD"] or "Drift" in header["ESO DET READ CURNAME"]:
        raise ValueError("LS7Q only evaluates the identified no-clear modes")
    delay = header["ESO DET TDELAY"] / 1000
    read = (header["ESO DET TREAD"] - header["ESO DET TFT"]) / 1000
    period = (header["ESO DET TREAD"] + header["ESO DET TDELAY"]) / 1000
    first = frame == nskip + 1
    start = -period * nskip - (D(0) if first else read)
    end = delay
    return {
        "valid": frame % (nskip + 1) == 0,
        "first": first,
        "start_offset_s": start,
        "end_offset_s": end,
        "mid_offset_s": (start + end) / 2,
        "exposure_s": end - start,
        "channel_period_s": period * (nskip + 1),
        "dead_time_s": header["ESO DET TFT"] / 1000,
    }


def source_audit(path, headers):
    """Execute only the official timing block and method, not module imports.

    The inspected upstream AST is pinned by SHA256 in the output. This avoids
    installing the full instrument pipeline to check its scalar arithmetic.
    """
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Official hcam.py bytes differ from the inspected source pin")
    source = path.read_text()
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Rhead")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "timing")
    idx = next(i for i, n in enumerate(init.body)
               if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "E" for t in n.targets))
    block = ast.Module(body=init.body[idx:idx + 2], type_ignores=[])
    assert isinstance(block.body[1], ast.If)
    namespace = {"DAYSEC": 86400.0}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), "pinned-hcam-timing", "exec"), namespace)
    checked = 0
    max_error = 0.0
    for h in headers:
        if h["ESO DET CLRCCD"] or "Drift" in h["ESO DET READ CURNAME"]:
            continue
        obj = SimpleNamespace(clear=False, drift=False,
            nskips=tuple(int(h[f"ESO DET NSKIPS{i}"]) for i in range(1, 6)))
        env = {"self": obj, "hd": {k:float(v) if isinstance(v, D) else v for k,v in h.items()}}
        exec(compile(ast.fix_missing_locations(block), "pinned-hcam-offsets", "exec"), env)
        for channel, skip in enumerate(obj.nskips):
            # Initial, first valid, first regular, adjacent dummy and final
            # boundary. These are arithmetic checks, not observed timestamps.
            frames = sorted({1, skip + 1, 2*(skip+1), 2*(skip+1)+1, int(h["NAXIS3"])})
            for frame in frames:
                mid, exp, flag = namespace["timing"](obj, frame, channel)
                ours = timing(h, skip, frame)
                assert bool(flag) == ours["valid"]
                error = max(abs(mid*86400-float(ours["mid_offset_s"])), abs(exp-float(ours["exposure_s"])))
                assert error < 1e-12, (channel, frame, error)
                max_error = max(max_error, error)
                checked += 1
    return {"upstream_commit": SOURCE_COMMIT, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "timing_tuples_checked": checked, "max_absolute_seconds_error": max_error,
            "status": "PASS", "scope": "metadata arithmetic only; no per-frame timestamps or pixels"}


def plain(value):
    if isinstance(value, D):
        return str(value)
    raise TypeError(type(value).__name__)


def build(root):
    rows = json.loads((root / "gtc_first100_rows.json").read_text())
    ids = [r["cells"][0] for r in rows]
    assert len(ids) == len(set(ids)) == 100
    assert all(r["cells"][9] == "HiPERCAM" for r in rows)
    assert all(r["cells"][11] < "2025-09-14" for r in rows)
    files = sorted(root.glob("*header.html"))
    headers = {p.stem: read_header(p) for p in files}
    science = headers["xo2b_5070352_header"]
    flat = headers["xo2b_5070341_flat_header"]
    bias = headers["xo2b_5070335_bias_header"]
    assert science["IMAGETYP"] == "data"
    assert flat["IMAGETYP"] == "flat"
    assert bias["IMAGETYP"] == "bias"
    channels = []
    nframes = int(science["NAXIS3"])
    for index, label in enumerate(science["FILTERS"].split(","), 1):
        skip = int(science[f"ESO DET NSKIPS{index}"])
        regular = timing(science, skip, 2*(skip+1))
        first = timing(science, skip, skip+1)
        channels.append({"ccd": index, "filter_label": label, "nskip": skip,
                         "regular": regular, "first": first,
                         "nominal_real_frames": nframes//(skip+1),
                         "nominal_regular_frames": max(0, nframes//(skip+1)-1)})
    keys = ["ORIGFILE", "OBJECT", "IMAGETYP", "DATE-OBS", "DATE", "NAXIS1", "NAXIS2", "NAXIS3",
            "EXPTIME", "FILTERS", "ESO DET READ CURNAME", "ESO DET SPEED", "ESO DET BINX1",
            "ESO DET BINY1", "ESO DET WIN1 XSLL", "ESO DET WIN1 XSLR", "ESO DET WIN1 NX",
            "ESO DET WIN1 NY", "ESO DET CLRCCD", "ESO DET CHIP1 GAIN", "ESO DET CHIP1 RON"]
    selected = {k:{key:h[key] for key in keys if key in h} for k,h in headers.items()}
    raw_bytes = int(abs(science["BITPIX"])/8 * science["NAXIS1"] * science["NAXIS2"] * science["NAXIS3"])
    base_cycle = (science["ESO DET TREAD"] + science["ESO DET TDELAY"])/1000
    assert base_cycle == science["ESO DET TCYCLE"]/1000
    archive_row = next(r for r in rows if r["cells"][0] == "5070352")
    stamp_delta = (datetime.fromisoformat(science["DATE"]) - datetime.fromisoformat(science["DATE-OBS"])).total_seconds()
    http = json.loads((root/"http_acquisition.json").read_text())
    head = next(r for r in http if r.get("method") == "HEAD")
    assert int(head["headers"]["Content-Length"]) < 0
    range_result = next(r for r in http if r.get("request_range") == "bytes=0-0")
    result = {
        "scope": "exploratory metadata feasibility; not a native search or detector qualification",
        "catalogue": {"query_total_reported_by_ui": 1035, "rows_inspected": len(rows),
                      "date_cutoff": "2025-09-13", "page": 1, "pages_reported": 11,
                      "targets_on_page": dict(sorted(Counter(r["cells"][4] for r in rows).items()))},
        "selected_headers": selected,
        "science_timing": {"channels": channels, "base_cycle_s":base_cycle,
                           "regular_exptime_minus_generic_header_s": channels[1]["regular"]["exposure_s"]-science["EXPTIME"],
                           "frame_count_times_cycle_s": base_cycle*nframes,
                           "file_creation_minus_sequence_start_s": stamp_delta,
                           "archive_row_exptime_s": archive_row["cells"][13],
                           "archive_row_end_time": archive_row["cells"][12],
                           "caution": "Nominal header-derived quantities; per-frame GPS validity, gaps and elapsed observing coverage unmeasured."},
        "size": {"uncompressed_primary_data_bytes_excluding_FITS_padding": raw_bytes,
                 "nominal_frame_data_bytes": int(abs(science["BITPIX"])/8*science["NAXIS1"]*science["NAXIS2"]),
                 "compressed_transport_size": None},
        "calibration": {"science_filters":science["FILTERS"],"flat_filters":flat["FILTERS"],
                        "matching_filter_labels": [a==b for a,b in zip(science["FILTERS"].split(','),flat["FILTERS"].split(','))],
                        "science_read_speed":science["ESO DET SPEED"],"flat_read_speed":flat["ESO DET SPEED"],
                        "bias_read_speed":bias["ESO DET SPEED"],
                        "decision": "UNESTABLISHED: NaI versus rs flat, fast science versus slow full-frame bias; no matched noise/defect/response contract"},
        "access": {"head":head,"bounded_range_attempt":range_result,
                   "science_pixel_bytes_acquired":0,"decision":"UNESTABLISHED: invalid Content-Length and failed byte-range request"},
        "pilot_readiness":"NOT_READY",
        "new_science_coverage_days":0,
        "candidate_searches_run":0,
    }
    return result, list(headers.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("results_ls7q_metadata"))
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    result, headers = build(args.root)
    (args.root/"summary.json").write_text(json.dumps(result,default=plain,indent=2)+"\n")
    if args.reference:
        audit = source_audit(args.reference, headers)
        (args.root/"timing_audit.json").write_text(json.dumps(audit,indent=2)+"\n")
        print(json.dumps(audit,indent=2))
    print("LS7Q metadata complete: 100 catalogue rows, six header records, pilot NOT_READY; zero science pixels.")


if __name__ == "__main__":
    main()
