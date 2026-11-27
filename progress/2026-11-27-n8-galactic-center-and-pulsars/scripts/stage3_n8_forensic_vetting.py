#!/usr/bin/env python3
"""Stage 3 forensic vetting across all Spor N8 Galactic Center & Milky Way Pulsar triggers."""
from __future__ import annotations

import collections
import csv
import json
import math
import socket
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(*args: Any, **kwargs: Any) -> Any:
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_getaddrinfo

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n8_20261127_galactic_center_and_pulsars"
RES = WS / "results"


def _http_get(url: str, timeout: int = 25) -> bytes:
    last_err: Exception | None = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SETI-N8/1.0"}), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last_err}")


def fetch_atnf_ep1(psrj: str) -> tuple[float | None, str]:
    u = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?" + urllib.parse.urlencode({
        "-source": "B/psr/psr", "PSRJ": psrj, "-out": "PSRJ,P1,e_P1,r_P1",
    })
    txt = _http_get(u, timeout=20).decode("utf-8", errors="replace")
    lines = [l for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    for i, ln in enumerate(lines):
        if set(ln.replace("\t", "").strip()).issubset({"-", " "}) and i + 1 < len(lines):
            cols = [c.strip() for c in lines[i + 1].split("\t")]
            try:
                ep1 = float(cols[2]) if len(cols) > 2 and cols[2] else None
            except ValueError:
                ep1 = None
            ref = cols[3] if len(cols) > 3 else ""
            return ep1, ref
    return None, ""


def query_simbad(ra: str, dec: str) -> tuple[str, str]:
    q = urllib.parse.urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
        "QUERY": f"SELECT TOP 2 main_id, otype, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',{ra},{dec}))*3600 AS sep FROM basic WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},0.02))=1 ORDER BY sep ASC",
    })
    try:
        lines = _http_get(f"https://simbad.harvard.edu/simbad/sim-tap/sync?{q}", timeout=15).decode("utf-8", errors="replace").splitlines()
        if len(lines) >= 2:
            row = next(csv.reader([lines[1]]))
            return row[0], row[1]
    except Exception:
        pass
    return "", ""


def main() -> int:
    trigs = list(csv.DictReader((RES / "N8_STAGE2_TRIGGERS.csv").open("r", encoding="utf-8")))
    vetted: list[dict[str, Any]] = []
    counts: collections.Counter[str] = collections.Counter()

    for r in trigs:
        nm = r["name"]
        reasons = r["trigger_reasons"]
        assoc = r["assoc"]
        p1 = float(r["p1"]) if r["p1"] else 0.0
        ep1, ref = fetch_atnf_ep1(nm)
        sim_id, sim_ot = query_simbad(r["ra_deg"], r["dec_deg"])
        p1_sigma = abs(p1) / ep1 if (ep1 and ep1 > 0) else 999.0

        if "GC:" in assoc.upper():
            vclass = "GLOBULAR_CLUSTER_GRAVITATIONAL_ACCEL"
            note = f"Cluster gravitational acceleration in {assoc} mimics negative P1 (P1={p1:.3e}, ref={ref}, simbad={sim_id} {sim_ot})"
        elif "N8_PSR_SPINUP_ANOMALY" in reasons and ep1 is not None and p1_sigma < 2.0:
            vclass = "TIMING_NOISE_UNSIGNIFICANT_P1"
            note = f"Unconstrained timing fit: P1={p1:.2e} +- {ep1:.2e} ({p1_sigma:.2f} sigma from 0, {ref})"
        elif nm == "J2144-3933" or "N8_PSR_DEATHLINE_VIOLATION" in reasons:
            vclass = "CURVED_SPACETIME_SLOW_RADIO_PULSAR"
            note = f"Known 8.51s nearby curved-spacetime pulsar Young+1999 ({ref}; B={r['bsurf']}G, simbad={sim_id} {sim_ot})"
        else:
            vclass = "UNRESOLVED_ETI_CANDIDATE"
            note = "Unresolved anomaly"

        status = "UNRESOLVED_ETI_CANDIDATE" if vclass == "UNRESOLVED_ETI_CANDIDATE" else "VETOED_ASTROPHYSICAL_OR_NOISE"
        counts[vclass] += 1
        vetted.append({
            **r,
            "atnf_e_p1": ep1 if ep1 is not None else "",
            "p1_significance_sigma": round(p1_sigma, 2),
            "atnf_p1_ref": ref,
            "simbad_id": sim_id,
            "simbad_otype": sim_ot,
            "vetting_class": vclass,
            "eti_status": status,
            "vetting_note": note,
        })

    with (RES / "N8_CANDIDATES_VETTED.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(vetted[0].keys()))
        w.writeheader()
        w.writerows(vetted)

    s2 = json.loads((RES / "N8_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "milky_way_pulsars_vetted": s2["milky_way_pulsars_total"],
        "fermi_bulge_sources_vetted": s2["fermi_bulge_sources_total"],
        "stage2_triggers_vetted": len(vetted),
        "vetting_class_counts": dict(counts),
        "verified_eti_candidates": sum(1 for v in vetted if v["eti_status"] == "UNRESOLVED_ETI_CANDIDATE"),
    }
    (RES / "N8_STAGE3_VETTING.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
