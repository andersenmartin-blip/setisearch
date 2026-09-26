#!/usr/bin/env python3
"""Retained-metadata pointing comparison plus one fixed original-product listing."""
import argparse
import json
import math
import subprocess
from pathlib import Path
from urllib.parse import urlencode

from astropy import units as u
from astropy.coordinates import SkyCoord
from radio_restart_metadata import Transport, save

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_restart_2026-09-26/pointing"
INPUTS = (
    "scripts/radio_restart_pointing.py", "scripts/radio_restart_metadata.py",
    "RADIO_RESTART_2026-09-26_POINTING_PROTOCOL.md",
    "results_radio_restart_2026-09-26/attempt02/pilot_headers.json",
    "results_radio_restart_2026-09-26/astrometry/result.json",
    "results_radio_restart_2026-09-26/coordinate_format_sources.json",
)


def separation_arcmin(ra1, dec1, ra2, dec2):
    r1,d1,r2,d2 = map(math.radians,(ra1,dec1,ra2,dec2))
    a = math.sin((d1-d2)/2)**2 + math.cos(d1)*math.cos(d2)*math.sin((r1-r2)/2)**2
    return math.degrees(2*math.atan2(math.sqrt(a),math.sqrt(1-a))) * 60


def main():
    p=argparse.ArgumentParser();p.add_argument("--freeze-commit",required=True);args=p.parse_args()
    for path in INPUTS:
        if subprocess.check_output(["git","show",args.freeze_commit+":"+path],cwd=ROOT)!=(ROOT/path).read_bytes():
            raise RuntimeError("Pointing freeze mismatch: "+path)
    if OUT.exists(): raise RuntimeError("Preserve completed pointing diagnosis")
    OUT.mkdir(parents=True)
    headers=json.loads((ROOT/INPUTS[3]).read_text())
    official=json.loads((ROOT/INPUTS[4]).read_text())["record"]
    target=SkyCoord(official["ra"]*u.deg,official["dec"]*u.deg)
    comparisons=[]
    for h in headers:
        a=h["data_attributes"]
        if a["source_name"]!="HIP1499":continue
        manual=separation_arcmin(a["src_raj"]*15,a["src_dej"],official["ra"],official["dec"])
        reference=SkyCoord(a["src_raj"]*u.hourangle,a["src_dej"]*u.deg).separation(target).arcmin
        if not math.isclose(manual,reference,rel_tol=0,abs_tol=1e-8): raise RuntimeError("Angular arithmetic disagreement")
        comparisons.append(dict(url=h["url"],start_mjd=a["tstart"],header_ra_hours=a["src_raj"],
            header_dec_degrees=a["src_dej"],catalogue_ra_degrees=official["ra"],catalogue_dec_degrees=official["dec"],
            separation_arcmin=manual,astropy_separation_arcmin=reference))
    result=dict(freeze_commit=args.freeze_commit,spectral_dataset_values_read=False,comparisons=comparisons,
        status="POINTING_PROVENANCE_UNRESOLVED",automatic_coordinate_correction_applied=False,
        interpretation="Literal header-versus-catalogue comparison; no reference-epoch correction assumed. The metadata mismatch does not prove the telescope actually pointed away from HD 1461.")
    b=dict(total_bytes=2097152,per_json_bytes=2097152,requests=2,seconds=60,timeout_seconds=25,attempts_per_request=2)
    t=Transport(b,OUT)
    url="http://seti.berkeley.edu/opendata/api/query-files?"+urlencode(dict(target="HIP1499",telescope="GBT",limit="2000"))
    try:
        records=t.json(url)
        save(OUT/"target_only_catalogue.json",records)
        if len(records)>=2000:raise RuntimeError("Target-only row cap reached")
        starts={c["start_mjd"] for c in comparisons}
        matched=[r for r in records if r.get("target")=="HIP1499" and r.get("mjd") in starts]
        originals=[r for r in matched if str(r.get("url","")).lower().endswith((".fil",".raw"))]
        result.update(catalogue_check_complete=True,total_rows=len(records),same_on_scan_rows=matched,
                      matching_original_products=originals,
                      next_required_evidence="Original same-scan header or observing-log record establishing pointing or a documented file-specific coordinate conversion; no spectrum-based correction.")
    except Exception as e:
        result.update(catalogue_check_complete=False,catalogue_error=f"{type(e).__name__}: {e}")
    result["transport"]=dict(requests=t.requests,bytes=t.bytes)
    save(OUT/"result.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="same_on_scan_rows"},indent=2))


if __name__=="__main__":main()
