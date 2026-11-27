#!/usr/bin/env python3
"""
Stage 1 Live Catalog Acquisition for Spor N2:
- NASA/JPL SBDB Hyperbolic Objects (e > 1.0)
- NASA/JPL SBDB Non-Grav Asteroids (A1/A2/A3 defined) + Detailed Profiles
- Fink Vera Rubin LSST SSOFT (SHG1G2)
- Fink Vera Rubin LSST faint_trails
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import time
import urllib.parse
import urllib.request
from typing import Any

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP = ROOT / "inputs_n2_20261127"


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch_url(url: str, payload: dict[str, Any] | None = None, timeout: int = 45, retries: int = 3) -> bytes:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"User-Agent": "SETI-Spor-N2-Acquire/1.0"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed fetching {url}: {last_err}")


def main() -> int:
    manifest: dict[str, Any] = {
        "acquired_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": {},
    }

    # 1. JPL SBDB hyperbolic objects (e > 1.0)
    url_hyp = (
        "https://ssd-api.jpl.nasa.gov/sbdb_query.api?"
        "fields=spkid,full_name,pdes,class,e,q,i,a,H,M1,A1,A2,A3,first_obs,last_obs,n_obs_used,data_arc,condition_code,moid,neo,pha"
        "&sb-cdata=%7B%22AND%22:%5B%22e%7CGT%7C1.0%22%5D%7D"
    )
    b_hyp = fetch_url(url_hyp)
    d_hyp = json.loads(b_hyp.decode("utf-8"))
    p_hyp = INP / "sbdb" / "jpl_hyperbolic_e_gt_1.json"
    p_hyp.write_bytes(b_hyp)
    manifest["files"]["sbdb/jpl_hyperbolic_e_gt_1.json"] = {
        "records": len(d_hyp.get("data", [])),
        "bytes": len(b_hyp),
        "sha256": _sha256_bytes(b_hyp),
    }
    print(f"JPL hyperbolic e>1.0: {len(d_hyp.get('data', []))} objects")

    # 2. JPL SBDB asteroids with non-grav A1/A2/A3 defined
    url_ng = (
        "https://ssd-api.jpl.nasa.gov/sbdb_query.api?"
        "fields=spkid,full_name,pdes,class,e,q,i,a,H,A1,A2,A3,first_obs,last_obs,n_obs_used,data_arc,condition_code,moid,neo,pha"
        "&sb-kind=a&sb-cdata=%7B%22OR%22:%5B%22A1%7CDF%22,%22A2%7CDF%22,%22A3%7CDF%22%5D%7D"
    )
    b_ng = fetch_url(url_ng)
    d_ng = json.loads(b_ng.decode("utf-8"))
    p_ng = INP / "sbdb" / "jpl_nongrav_asteroids.json"
    p_ng.write_bytes(b_ng)
    manifest["files"]["sbdb/jpl_nongrav_asteroids.json"] = {
        "records": len(d_ng.get("data", [])),
        "bytes": len(b_ng),
        "sha256": _sha256_bytes(b_ng),
    }
    print(f"JPL non-grav asteroids: {len(d_ng.get('data', []))} objects")

    # 3. JPL SBDB detailed profiles for ISOs + high-e comets + all strong non-grav asteroids (max >= 1e-12 AU/d^2)
    nf = d_ng["fields"]
    ia1, ia2, ia3, ipdes = nf.index("A1"), nf.index("A2"), nf.index("A3"), nf.index("pdes")
    targets = ["1I", "2I", "3I", "C/1980 E1", "C/1954 O1"]
    for rec in d_ng.get("data", []):
        vals = [abs(float(rec[ix])) for ix in (ia1, ia2, ia3) if rec[ix] is not None]
        if vals and max(vals) >= 1e-12:
            pdes = str(rec[ipdes]).strip()
            if pdes and pdes not in targets:
                targets.append(pdes)

    detail_profiles: dict[str, Any] = {}
    for tgt in targets:
        q = urllib.parse.quote(tgt)
        raw = fetch_url(f"https://ssd-api.jpl.nasa.gov/sbdb.api?sstr={q}&phys-par=1", timeout=25)
        detail_profiles[tgt] = json.loads(raw.decode("utf-8"))
        time.sleep(0.15)
    b_det = json.dumps(detail_profiles, indent=2).encode("utf-8")
    p_det = INP / "sbdb" / "jpl_detail_profiles.json"
    p_det.write_bytes(b_det)
    manifest["files"]["sbdb/jpl_detail_profiles.json"] = {
        "records": len(detail_profiles),
        "bytes": len(b_det),
        "sha256": _sha256_bytes(b_det),
    }
    print(f"JPL detail profiles fetched: {len(detail_profiles)}")

    # 4. Fink Vera Rubin LSST SSOFT (SHG1G2)
    b_ssoft = fetch_url("https://api.lsst.fink-portal.org/api/v1/ssoft", {"flavor": "SHG1G2", "output-format": "json"}, timeout=60)
    d_ssoft = json.loads(b_ssoft.decode("utf-8"))
    p_ssoft = INP / "ssoft" / "fink_ssoft_shg1g2.json"
    p_ssoft.write_bytes(b_ssoft)
    manifest["files"]["ssoft/fink_ssoft_shg1g2.json"] = {
        "records": len(d_ssoft),
        "bytes": len(b_ssoft),
        "sha256": _sha256_bytes(b_ssoft),
    }
    print(f"Fink SSOFT SHG1G2: {len(d_ssoft)} objects")

    # 5. Fink Vera Rubin LSST faint_trails
    b_ft = fetch_url("https://api.lsst.fink-portal.org/api/v1/tags", {"tag": "faint_trails", "n": 1000, "output-format": "json"}, timeout=45)
    d_ft = json.loads(b_ft.decode("utf-8"))
    p_ft = INP / "faint_trails" / "fink_faint_trails.json"
    p_ft.write_bytes(b_ft)
    manifest["files"]["faint_trails/fink_faint_trails.json"] = {
        "records": len(d_ft),
        "bytes": len(b_ft),
        "sha256": _sha256_bytes(b_ft),
    }
    print(f"Fink faint_trails: {len(d_ft)} alerts")

    (INP / "STAGE1_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("STAGE 1 COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
