#!/usr/bin/env python3
"""Supplement acquisition receipts with intended-target FITS header metadata.

Only primary header blocks are read. No spectral table or numerical science
array is interpreted. FITS RA/DEC versus ObsCore agreement is a consistency
test, not an independent verification of astrophysical target identity.
"""
import csv
import datetime
import hashlib
import json
import pathlib
import re

from download_selected import read_header

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "acquisition"


def normalize(value):
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def sexagesimal_deg(value, hours=False):
    number = float(value)
    magnitude = abs(number)
    leading = int(magnitude // 10000)
    minutes = int((magnitude - leading * 10000) // 100)
    seconds = magnitude - leading * 10000 - minutes * 100
    if minutes >= 60 or seconds >= 60:
        raise ValueError("Invalid compact sexagesimal coordinate")
    degrees = leading + minutes / 60 + seconds / 3600
    return (-1 if number < 0 else 1) * degrees * (15 if hours else 1)


def main():
    rows = []
    for csvpath in (ROOT / "selection" / "DEVELOPMENT_AND_VALIDATION.csv", ROOT / "selection" / "MAIN100.csv"):
        rows.extend(csv.DictReader(csvpath.open()))
    output = []
    for row in rows:
        receipt_path = OUT / "receipts" / (row["dp_id"].replace(":", "_") + ".json")
        if not receipt_path.exists():
            output.append({"dp_id": row["dp_id"], "role": row["role"], "status": "RECEIPT_NOT_AVAILABLE"})
            continue
        receipt = json.loads(receipt_path.read_text())
        path = pathlib.Path(receipt["path"])
        if not path.exists():
            output.append({"dp_id": row["dp_id"], "role": row["role"], "status": "FILE_NOT_AVAILABLE"})
            continue
        with path.open("rb") as stream:
            header = read_header(stream)
        keys = {"RA", "DEC", "RADECSYS", "EQUINOX", "OBJECT", "MJD-OBS", "DATE-OBS", "EXPTIME"}
        target_header = {key: value for key, value in header.items() if key in keys or "TARG" in key}
        item = {
            "dp_id": row["dp_id"],
            "canonical_target": row["canonical_target"],
            "role": row["role"],
            "path": str(path),
            "file_sha256_from_acquisition": receipt.get("sha256"),
            "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            "status": "PRIMARY_HEADER_READ",
            "header": target_header,
            "obs_targ_name_matches_selected_name": normalize(header.get("HIERARCH ESO OBS TARG NAME", "")) == normalize(row["canonical_target"]),
            "array_values_inspected": False,
        }
        try:
            item["tel_targ_alpha_decimal_deg"] = sexagesimal_deg(header["HIERARCH ESO TEL TARG ALPHA"], hours=True)
            item["tel_targ_delta_decimal_deg"] = sexagesimal_deg(header["HIERARCH ESO TEL TARG DELTA"])
        except (KeyError, ValueError) as error:
            item["coordinate_conversion_error"] = str(error)
        output.append(item)
    report = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "code_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "header_parser_code_sha256": hashlib.sha256((OUT / "download_selected.py").read_bytes()).hexdigest(),
        "scope": "Primary FITS headers only, with all TARG cards preserved. Compact sexagesimal ALPHA and DELTA are converted to degrees without applying proper motion or frame transformations.",
        "identity_limitation": "Agreement of FITS RA/DEC with ObsCore establishes metadata consistency only. Intended-target ALPHA/DELTA, proper motion, epoch and frame require review for physical target identity. Pointing variations alone are not automatically classified as mispointing.",
        "array_values_inspected": False,
        "counts": {status: sum(row["status"] == status for row in output) for status in sorted({row["status"] for row in output})},
        "files": output,
    }
    (OUT / "TARGET_COORDINATE_HEADERS.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"counts": report["counts"], "path": str(OUT / "TARGET_COORDINATE_HEADERS.json")}))


if __name__ == "__main__":
    main()
