#!/usr/bin/env python3
"""Stage 1 live acquisition: Complete Milky Way ATNF Pulsars + Galactic Bulge 4FGL + NVSS + CSC2 (Spor N8)."""
from __future__ import annotations

import csv
import json
import math
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(*args: Any, **kwargs: Any) -> Any:
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_getaddrinfo

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP = ROOT / "inputs_n8_20261127"


def _http_get(url: str, timeout: int = 60) -> bytes:
    last_err: Exception | None = None
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SETI-N8/1.0"}), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last_err = e
            time.sleep(2.0 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last_err}")


def parse_vizier_tsv(txt: str) -> list[dict[str, str]]:
    lines = [l for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    if len(lines) < 3:
        return []
    hdr = [c.strip() for c in lines[0].split("\t")]
    ds = 3 if len(lines) >= 3 and set(lines[2].replace("\t", "").strip()).issubset({"-", " "}) else 1
    out: list[dict[str, str]] = []
    for ln in lines[ds:]:
        parts = ln.split("\t")
        if len(parts) == len(hdr):
            out.append({k: v.strip() for k, v in zip(hdr, parts)})
    return out


def _f(v: Any) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def fetch_atnf_mw() -> list[dict[str, Any]]:
    out = INP / "atnf/atnf_milky_way_pulsars.csv"
    if out.exists() and out.stat().st_size > 10000:
        return list(csv.DictReader(out.open("r", encoding="utf-8")))
    cols = "_RAJ2000,_DEJ2000,PSRJ,GLON,GLAT,P0,P1,DM,S400,S1400,Binary,PB,Ecc,minM,medM,BINCOMP,Dist,DistDM,Assoc,Type,Bsurf,Edot,Age,P1I"
    u = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?" + urllib.parse.urlencode({
        "-source": "B/psr/psr", "-out.max": "unlimited", "-oc.form": "dec", "-out": cols,
    })
    raw = _http_get(u, timeout=75).decode("utf-8", errors="replace")
    rows = parse_vizier_tsv(raw)
    clean: list[dict[str, Any]] = []
    for r in rows:
        assoc = (r.get("Assoc") or "").upper()
        # Exclude LMC/SMC extragalactic pulsars strictly
        if "LMC" in assoc or "SMC" in assoc:
            continue
        ra = _f(r.get("_RAJ2000"))
        dec = _f(r.get("_DEJ2000"))
        if ra is None or dec is None:
            continue
        r["ra_deg"] = round(ra, 6)
        r["dec_deg"] = round(dec, 6)
        clean.append(r)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(clean[0].keys()))
        w.writeheader()
        w.writerows(clean)
    print(f"ATNF Milky Way pulsars saved: {len(clean)}", flush=True)
    return clean


def fetch_fermi_bulge() -> list[dict[str, Any]]:
    out = INP / "fermi/fermi_4fgl_galactic_bulge.csv"
    if out.exists() and out.stat().st_size > 5000:
        return list(csv.DictReader(out.open("r", encoding="utf-8")))
    cols = "_RAJ2000,_DEJ2000,4FGL,GLON,GLAT,amaj95,bmin95,Sig,F1000i,EF100,PLGam,SigCurv1,SigCurv2,VarInd,Cl1,Cl2,Assoc1,Flags"
    seen: dict[str, dict[str, Any]] = {}
    for glon_rng in ("0..10", "350..360"):
        u = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?" + urllib.parse.urlencode({
            "-source": "IX/67/4fgldr3", "-out.max": "unlimited", "-oc.form": "dec",
            "GLON": glon_rng, "GLAT": "-5..5", "-out": cols,
        })
        raw = _http_get(u, timeout=60).decode("utf-8", errors="replace")
        for r in parse_vizier_tsv(raw):
            ra, dec = _f(r.get("_RAJ2000")), _f(r.get("_DEJ2000"))
            if ra is None or dec is None:
                continue
            r["ra_deg"] = round(ra, 6)
            r["dec_deg"] = round(dec, 6)
            seen[r["4FGL"]] = r
    clean = list(seen.values())
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(clean[0].keys()))
        w.writeheader()
        w.writerows(clean)
    print(f"Fermi 4FGL-DR3 Galactic Bulge sources saved: {len(clean)}", flush=True)
    return clean


def fetch_gc_nvss() -> list[dict[str, Any]]:
    out = INP / "radio/nvss_galactic_center.csv"
    if out.exists() and out.stat().st_size > 5000:
        return list(csv.DictReader(out.open("r", encoding="utf-8")))
    u = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?" + urllib.parse.urlencode({
        "-source": "VIII/65/nvss", "-c": "266.4168 -29.0078", "-c.rd": "2.5",
        "-out.max": "unlimited", "-oc.form": "dec", "-out": "_RAJ2000,_DEJ2000,NVSS,S1.4,e_S1.4,MajAxis",
    })
    raw = _http_get(u, timeout=60).decode("utf-8", errors="replace")
    clean = []
    for r in parse_vizier_tsv(raw):
        ra, dec = _f(r.get("_RAJ2000")), _f(r.get("_DEJ2000"))
        if ra is not None and dec is not None:
            r["ra_deg"] = round(ra, 6)
            r["dec_deg"] = round(dec, 6)
            clean.append(r)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(clean[0].keys()))
        w.writeheader()
        w.writerows(clean)
    print(f"NVSS 1.4 GHz Galactic Center sources saved: {len(clean)}", flush=True)
    return clean


def fetch_gc_csc2() -> list[dict[str, Any]]:
    out = INP / "xray/csc2_galactic_center.csv"
    if out.exists() and out.stat().st_size > 5000:
        return list(csv.DictReader(out.open("r", encoding="utf-8")))
    u = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?" + urllib.parse.urlencode({
        "-source": "IX/57/csc2master", "-c": "266.4168 -29.0078", "-c.rd": "0.5",
        "-out.max": "unlimited", "-oc.form": "dec", "-out": "_RAJ2000,_DEJ2000,2CXO,GLON,GLAT,fb,fh,fs",
    })
    raw = _http_get(u, timeout=60).decode("utf-8", errors="replace")
    clean = []
    for r in parse_vizier_tsv(raw):
        ra, dec = _f(r.get("_RAJ2000")), _f(r.get("_DEJ2000"))
        if ra is not None and dec is not None:
            r["ra_deg"] = round(ra, 6)
            r["dec_deg"] = round(dec, 6)
            clean.append(r)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(clean[0].keys()))
        w.writeheader()
        w.writerows(clean)
    print(f"Chandra CSC2 Galactic Center X-ray sources saved: {len(clean)}", flush=True)
    return clean


def main() -> int:
    for d in ("atnf", "fermi", "radio", "xray"):
        (INP / d).mkdir(parents=True, exist_ok=True)
    psr = fetch_atnf_mw()
    fer = fetch_fermi_bulge()
    nv = fetch_gc_nvss()
    cs = fetch_gc_csc2()
    man = {
        "atnf_mw_pulsars": len(psr),
        "fermi_bulge_4fgl": len(fer),
        "nvss_gc_2p5deg": len(nv),
        "csc2_gc_0p5deg": len(cs),
    }
    (INP / "STAGE1_MANIFEST.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    print("STAGE1_N8_DONE:", json.dumps(man))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
