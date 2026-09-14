#!/usr/bin/env python3
"""LS7L source/header audit. Reads table schemas, never engineering samples."""
import hashlib
import json
from pathlib import Path
from astropy.io import fits
from ls7l_restore_engineering import ROOT, CACHE, OUT, SIZES

TIME_KEYS = ("TIMESYS", "TIMEREF", "TIMEUNIT", "BJDREFI", "BJDREFF",
             "MJDREFI", "MJDREFF", "JDREF", "TSTART", "TSTOP", "TIMEZERO",
             "TIMEDEL", "TIMEPIXR", "CAMERA", "CAM", "CCD")
def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()

def raw_headers(path):
    """Walk physical FITS blocks independently of HDU byte offsets."""
    records = []
    size, offset = path.stat().st_size, 0
    with path.open("rb") as stream:
        while offset < size:
            stream.seek(offset)
            blocks = []
            for _ in range(90):
                block = stream.read(2880)
                assert len(block) == 2880
                blocks.append(block)
                if any(block[k:k+8] == b"END     " for k in range(0,2880,80)):
                    break
            else:
                raise AssertionError("individual FITS header exceeds 256 KiB")
            raw = b"".join(blocks)
            header = fits.Header.fromstring(raw.decode("ascii"), sep="")
            elements = 0 if header["NAXIS"] == 0 else 1
            for i in range(1, header["NAXIS"] + 1):
                elements *= header[f"NAXIS{i}"]
            assert not header.get("GROUPS", False), "random groups not supported"
            data_bytes = (abs(header["BITPIX"]) // 8 * elements
                          + header.get("PCOUNT", 0)) * header.get("GCOUNT", 1)
            records.append((header, {"header_offset": offset, "header_bytes": len(raw),
                "header_sha256": hashlib.sha256(raw).hexdigest(),
                "data_offset": offset + len(raw), "data_bytes": data_bytes}))
            offset += len(raw) + ((data_bytes + 2879) // 2880) * 2880
    assert offset == size
    return records

def main():
    sources = json.loads((OUT / "sources.json").read_text())
    assert len(sources) == 4
    expected = json.loads((ROOT / "results_ls7k_inputs/inventory.json").read_text())["engineering"]["selected_links"]
    assert {(s["sector"], s["name"], s["url"]) for s in sources} == {
        (s["sector"], s["name"], s["url"]) for s in expected}
    inventory, checks = [], []
    for source in sources:
        path = CACHE / source["name"]
        assert path.stat().st_size == source["bytes"] == SIZES[source["sector"]][source["kind"]]
        assert digest(path) == source["sha256"]
        saved = json.loads((OUT / (source["name"] + ".headers.json")).read_text())
        walked = raw_headers(path)
        assert len(walked) == len(saved["hdus"])
        product = {**source, "hdus": []}
        with fits.open(path, memmap=True) as hdus:
            hdus.verify("exception")
            for index, ((header, offsets), hdu, archived) in enumerate(zip(walked, hdus, saved["hdus"], strict=True)):
                assert header.tostring() == hdu.header.tostring()
                assert index == archived["index"]
                assert offsets["data_offset"] == hdu.fileinfo()["datLoc"]
                # Missing mission checksums are reported, not treated as failed checks.
                checksums = {}
                for key, method in (("CHECKSUM", hdu.verify_checksum), ("DATASUM", hdu.verify_datasum)):
                    checksums[key] = method() if key in header else None
                    assert checksums[key] in (None, 1)
                fields = []
                for number in range(1, header.get("TFIELDS", 0) + 1):
                    fields.append({key: header.get(f"{key}{number}") for key in
                        ("TTYPE", "TFORM", "TUNIT", "TNULL", "TSCAL", "TZERO")})
                product["hdus"].append({"index": index, "name": hdu.name,
                    "rows": header.get("NAXIS2"), "row_bytes": header.get("NAXIS1"),
                    "time_metadata": {key: header[key] for key in TIME_KEYS if key in header},
                    "fields": fields, "checksums": checksums, **offsets})
        inventory.append(product)
        checks.append({"name": source["name"], "raw_header_chain_pass": True,
                       "full_source_sha256_pass": True, "hdus": len(walked)})
    result = {"study": "LS7L engineering schema", "stage": "schema",
        "source_commit": __import__("os").environ.get("GITHUB_SHA"),
        "sample_rows_extracted": 0, "native_response_comparisons": 0,
        "sources": inventory}
    (OUT / "schema.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (OUT / "SCHEMA_AUDIT.json").write_text(json.dumps({"pass": True, "checks": checks,
        "prior_range_attempt": "Original range blocks were not present in the recovered Git tree; no reconstruction or completeness claim."}, indent=2) + "\n")
    lines = ["# LS7L engineering source and schema inspection", "",
        "Four previously specified engineering/quaternion products are restored.",
        "All original file sizes, repeated source hashes and physical FITS header chains pass verification.",
        "No engineering sample rows or native pixel-response outcomes are evaluated at this stage.", "",
        "| Sector | Product | Bytes | HDUs |", "|---|---|---:|---:|"]
    for s in inventory:
        lines.append(f'| {s["sector"]} | {s["kind"]} | {s["bytes"]:,} | {len(s["hdus"])} |')
    lines += ["", "The source hashes identify the downloaded originals; they are not a previously known mission hash.",
        "Missing FITS checksum keywords are recorded explicitly in schema.json.",
        "The full original files are a reproducible cache, excluded from the Git result payload.",
        "Complete original header cards, offsets and header hashes are published.",
        "", "Next: freeze exact fields, time conventions and row windows before extracting closed-context samples.",
        "No detector is adopted, unused sector opened, or old result changed.", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps({"schema_audit_pass": True, "sources": checks, "sample_rows_extracted": 0}), flush=True)

if __name__ == "__main__":
    main()
