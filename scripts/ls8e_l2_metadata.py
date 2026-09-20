#!/usr/bin/env python3
"""Header-only preflight for the two frozen LS8E GJ 876 DEFAULT L2 visits."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_ls8e_l2_metadata"
BASE = "https://cheops-webapp-pg.obsuksprd2.unige.ch/"
KEYS = [
    "CH_PR100018_TG032801_V0300",
    "CH_PR100018_TG032802_V0300",
]
BUDGET = 64 * 1024
BLOCK = 2880
SAFE = {
    "content-length", "content-type", "content-range", "accept-ranges",
    "content-disposition", "etag", "last-modified",
}
REQUIRED_COLUMNS = {"BJD_TIME", "FLUX", "FLUXERR", "STATUS", "EVENT"}
KEYWORDS = [
    "EXTNAME", "EXT_VER", "DATA_LVL", "PROC_CHN", "PIPE_VER", "TIMESYS",
    "T_STRT_U", "T_STOP_U", "NEXP", "EXPTIME", "TEXPTIME", "EXPT_TYP",
    "AP_RADI", "STACKING", "ROUNDING", "NLIN_COR", "APERTURE",
    "CHECKSUM", "DATASUM",
]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def get_url(key: str) -> str:
    payload = {
        "fileType": "lightcurves",
        "filters": {"file_key": {"equal": [key]}},
        "aperture": "default",
    }
    with urlopen(Request(
        BASE + "download",
        data=json.dumps(payload).encode(),
        headers={"Accept": "application/json", "User-Agent": "dace-query/3.0.1"},
    ), timeout=45) as response:
        info = json.load(response)
    if not isinstance(info.get("key"), str) or not info["key"]:
        raise RuntimeError(f"exact DEFAULT lightcurve unavailable: {key}")
    return BASE + "download/photometry/" + info["key"] + "?compressed=false"


def read_block(url: str, start: int, identity: dict | None, records: list) -> tuple[bytes, dict]:
    assert (len(records) + 1) * BLOCK <= BUDGET
    with urlopen(Request(url, headers={
        "Range": f"bytes={start}-{start + BLOCK - 1}",
        "Accept": "application/octet-stream",
        "Accept-Encoding": "identity",
    }), timeout=45) as response:
        assert response.status == 206
        prefix, total = response.headers["Content-Range"].split("/")
        total = int(total)
        assert prefix == f"bytes {start}-{start + BLOCK - 1}"
        assert int(response.headers["Content-Length"]) == BLOCK
        etag = response.headers.get("ETag")
        disposition = response.headers.get("Content-Disposition")
        assert isinstance(etag, str) and etag
        assert isinstance(disposition, str) and disposition
        now = {"total": total, "etag": etag, "content_disposition": disposition}
        if identity is not None:
            assert now == identity, (now, identity)
        body = response.read(BLOCK + 1)
        assert len(body) == BLOCK
        records.append({
            "start": start,
            "count": BLOCK,
            "sha256": sha(body),
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "headers": {k: v for k, v in response.headers.items() if k.lower() in SAFE},
        })
        return body, now


def read_header(url: str, start: int, identity: dict | None, records: list) -> tuple[bytes, int, dict]:
    raw = b""
    offset = start
    for _ in range(16):
        block, identity = read_block(url, offset, identity, records)
        raw += block
        offset += BLOCK
        if any(block[i:i+8] == b"END     " for i in range(0, BLOCK, 80)):
            return raw, offset, identity
    raise RuntimeError("FITS header exceeds fixed bound")


def summarize(key: str) -> dict:
    folder = OUT / key
    folder.mkdir(parents=True)
    url = get_url(key)
    records = []

    primary, offset, identity = read_header(url, 0, None, records)
    h0 = fits.Header.fromstring(primary.decode("ascii"), sep="")
    assert h0["SIMPLE"] is True

    table_header, table_start, identity = read_header(url, offset, identity, records)
    h1 = fits.Header.fromstring(table_header.decode("ascii"), sep="")
    assert h1["XTENSION"] == "BINTABLE"
    assert h1.get("EXTNAME") == "SCI_COR_Lightcurve"
    assert key in identity["content_disposition"]
    assert key.endswith("_V0300")

    declared = h1["NAXIS1"] * h1["NAXIS2"] + h1.get("PCOUNT", 0)
    assert declared > 0
    assert table_start == sum(r["count"] for r in records)
    assert table_start < identity["total"]
    assert table_start + declared <= identity["total"]

    columns = [
        {
            "index": i,
            "name": h1[f"TTYPE{i}"],
            "format": h1[f"TFORM{i}"],
            "unit": h1.get(f"TUNIT{i}"),
        }
        for i in range(1, h1["TFIELDS"] + 1)
    ]
    names = {c["name"] for c in columns}
    assert REQUIRED_COLUMNS <= names, sorted(REQUIRED_COLUMNS - names)

    pipe = h1.get("PIPE_VER", h0.get("PIPE_VER"))
    nexp = h1.get("NEXP", h0.get("NEXP"))
    exptime = h1.get("EXPTIME", h0.get("EXPTIME"))
    texptime = h1.get("TEXPTIME", h0.get("TEXPTIME"))
    assert str(pipe) == "14.1.2", pipe
    assert int(nexp) == 14, nexp
    assert abs(float(exptime) - 3.0) < 1e-9, exptime
    assert abs(float(texptime) - 42.0) < 1e-6, texptime

    (folder / "primary_header.bin").write_bytes(primary)
    (folder / "lightcurve_header.bin").write_bytes(table_header)
    save(folder / "ranges.json", {
        "budget_bytes": BUDGET,
        "total_bytes_read": sum(r["count"] for r in records),
        "ranges": records,
    })

    result = {
        "stage": "LS8E_GJ876_L2_HEADER_PREFLIGHT",
        "status": "METADATA_ONLY",
        "file_key": key,
        "selection": {"file_type": "lightcurves", "aperture": "default"},
        "total_file_bytes": identity["total"],
        "etag": identity["etag"],
        "content_disposition": identity["content_disposition"],
        "header_bytes_acquired": table_start,
        "table_data_bytes_acquired": 0,
        "table_data_start": table_start,
        "table_bytes_declared": declared,
        "rows": h1["NAXIS2"],
        "row_bytes": h1["NAXIS1"],
        "fields": h1["TFIELDS"],
        "keywords": {k: h1.get(k, h0.get(k)) for k in KEYWORDS},
        "columns": columns,
        "required_columns_present": sorted(REQUIRED_COLUMNS),
        "lightcurve_values_read": 0,
        "image_pixels_read": 0,
    }
    save(folder / "summary.json", result)
    return result


def main() -> None:
    assert not OUT.exists(), "refuse completed LS8E header-preflight overwrite"
    OUT.mkdir()
    results = [summarize(key) for key in KEYS]

    schema = [
        [(c["name"], c["format"], c["unit"]) for c in r["columns"]]
        for r in results
    ]
    compatible = (
        schema[0] == schema[1]
        and results[0]["row_bytes"] == results[1]["row_bytes"]
        and results[0]["fields"] == results[1]["fields"]
        and all(r["keywords"]["PIPE_VER"] == "14.1.2" for r in results)
        and all(abs(float(r["keywords"]["TEXPTIME"]) - 42.0) < 1e-6 for r in results)
    )
    combined = {
        "stage": "LS8E_GJ876_L2_HEADER_PREFLIGHT",
        "status": "PASS_COMPATIBLE" if compatible else "INCOMPATIBLE",
        "selected_keys": KEYS,
        "products": results,
        "compatible_schema": compatible,
        "table_data_bytes_acquired": 0,
        "lightcurve_values_read": 0,
        "image_pixels_read": 0,
    }
    save(OUT / "summary.json", combined)
    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    (OUT / "SHA256SUMS").write_text("".join(
        f"{sha(p.read_bytes())}  {p.relative_to(OUT)}\n"
        for p in files if p.name != "SHA256SUMS"
    ))
    print(json.dumps({
        "status": combined["status"],
        "products": [{
            "file_key": r["file_key"],
            "rows": r["rows"],
            "row_bytes": r["row_bytes"],
            "table_start": r["table_data_start"],
            "table_bytes": r["table_bytes_declared"],
            "header_bytes": r["header_bytes_acquired"],
            "texptime": r["keywords"]["TEXPTIME"],
        } for r in results],
        "table_data_bytes_acquired": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
