#!/usr/bin/env python3
"""One fixed official catalogue query for the metadata-selected HD 1461 pilot."""
import argparse
import hashlib
import json
import math
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_restart_2026-09-26/astrometry"
FIELDS = ("pl_name", "hostname", "hip_name", "hd_name", "ra", "dec", "rastr", "decstr",
          "sy_dist", "sy_plx", "sy_pmra", "sy_pmdec", "st_radv", "pl_orbper", "pl_orbsmax",
          "pl_orbeccen", "pl_orbtper", "pl_orblper")
QUERY = f"select {','.join(FIELDS)} from pscomppars where pl_name='HD 1461 b'"
URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?" + urlencode({"query":QUERY,"format":"json"})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Official metadata redirect refused: " + newurl)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--freeze-commit", required=True)
    args = p.parse_args()
    for path in ("scripts/radio_hd1461_metadata.py", "RADIO_RESTART_2026-09-26_ASTROMETRY_PROTOCOL.md"):
        if subprocess.check_output(["git","show",args.freeze_commit+":"+path],cwd=ROOT) != (ROOT/path).read_bytes():
            raise RuntimeError("Published freeze mismatch: " + path)
    if OUT.exists(): raise RuntimeError("Preserve prior official-metadata attempt")
    OUT.mkdir(parents=True)
    result = dict(freeze_commit=args.freeze_commit, utc=datetime.now(timezone.utc).isoformat(),
                  url=URL, query=QUERY, spectral_dataset_values_read=False, attempts=[])
    try:
        for attempt in (1, 2):
            log = dict(attempt=attempt, utc=datetime.now(timezone.utc).isoformat())
            result["attempts"].append(log)
            try:
                request = Request(URL, headers={"User-Agent":"setisearch-hd1461-metadata/1.0"})
                with build_opener(NoRedirect).open(request, timeout=25) as r:
                    raw = r.read(1048577)
                    log.update(status=r.status, url=r.geturl(), bytes=len(raw), headers=dict(r.headers.items()))
                    if r.status != 200 or r.geturl() != URL or len(raw) > 1048576:
                        raise RuntimeError("Official response status/URL/size failure")
                (OUT/"official_response.json").write_bytes(raw)
                result["response_sha256"] = hashlib.sha256(raw).hexdigest()
                records = json.loads(raw)
                if not isinstance(records,list) or len(records)!=1 or set(records[0])!=set(FIELDS):
                    raise RuntimeError("Official selected-record schema mismatch")
                record = records[0]
                for key, value in dict(pl_name="HD 1461 b",hostname="HD 1461",hip_name="HIP 1499",hd_name="HD 1461").items():
                    if record[key] != value: raise RuntimeError("Official target identity mismatch: "+key)
                missing = [k for k,v in record.items() if v is None]
                for key in FIELDS[4:]:
                    if key in ("rastr","decstr") or record[key] is None: continue
                    if isinstance(record[key],bool) or not isinstance(record[key],(int,float)) or not math.isfinite(record[key]):
                        raise RuntimeError("Nonfinite/non-numeric official metadata: "+key)
                result.update(status="COMPLETE_RECORD_AVAILABLE" if not missing else "INCOMPLETE_RECORD_REQUIRES_EXPLICIT_MODEL_SCOPE",
                              record=record, missing_fields=missing,
                              note="Composite metadata for a working motion model; no search configuration, calibration or astrophysical sensitivity is implied.")
                break
            except (HTTPError,URLError,TimeoutError) as e:
                log["error"] = str(e)
                transient = not isinstance(e,HTTPError) or e.code in (408,429,500,502,503,504)
                if not transient or attempt==2: raise
                time.sleep(1)
    except Exception as e:
        result.update(status="TECHNICAL_STOP", error=f"{type(e).__name__}: {e}")
    (OUT/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__ == "__main__": main()
