#!/usr/bin/env python3
"""
Spor N6 Stage 1 Live Local Supercluster + All-Sky Radio Acquisition:
1) VizieR HECATE (J/MNRAS/506/1896/hecate): D in [0.5, 40.0] Mpc, logMtot >= 9.0,
   complete K+W1-W4+logMtot photometry.
2) NASA HEASARC NVSS 1.4 GHz (Dec >= -40 deg, VOTable <BINARY> pure-stdlib decoder)
3) CSIRO CASDA RACS-low 888 MHz & RACS-mid 1367.5 MHz (Dec <= +49 deg)
4) ASTRON LoTSS DR3 144 MHz (Dec >= -10 deg, + empirical mosaics footprint)
Forces IPv4 (socket.AF_INET).
"""
from __future__ import annotations

import base64
import csv
import datetime
import hashlib
import json
import math
import pathlib
import socket
import struct
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

_orig_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, fam=0, t=0, pr=0, fl=0: _orig_gai(h, p, socket.AF_INET, t, pr, fl)

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP = ROOT / "inputs_n6_20261127"


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).strip().lower() in ("nan", "null", "none", "inf", "-inf", "--"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def _http_req(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 45) -> bytes:
    hdrs = {"User-Agent": "SETI-N6/1.0"}
    if headers:
        hdrs.update(headers)
    last_err: Exception | None = None
    for i in range(6):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            time.sleep(2.0 * (i + 1))
    raise RuntimeError(f"HTTP failed {url}: {last_err}")


def acquire_hecate() -> list[dict[str, str]]:
    out_p = INP / "hecate" / "hecate_local_supercluster.csv"
    if out_p.exists() and out_p.stat().st_size > 4096:
        rows = list(csv.DictReader(out_p.open(encoding="utf-8")))
        print(f"HECATE cached: {len(rows)} galaxies", flush=True)
        return rows

    cols = "PGC,NED,RAJ2000,DEJ2000,D,MajAxis,t,Jmag,Hmag,Kmag,W1mag,W2mag,W3mag,W4mag,F12um,F25um,F60um,F100um,logLTIR,logLFIR,logMtot,logSFRh,Nuclear,AGNs17,AGNh"
    u = f"https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-source=J/MNRAS/506/1896/hecate&-out.max=unlimited&D=0.5..40&logMtot=>=9.0&-out={cols}"
    raw = _http_req(u, timeout=60).decode("utf-8", errors="replace")
    lines = [l for l in raw.splitlines() if l.strip() and not l.startswith("#")]
    hdr = lines[0].split("\t")
    ds = 3 if len(lines) >= 3 and set(lines[2].replace("\t", "").strip()).issubset({"-", " "}) else 1
    rows: list[dict[str, str]] = []
    seen_pgc: set[str] = set()
    req_num = ("RAJ2000", "DEJ2000", "D", "Kmag", "W1mag", "W2mag", "W3mag", "W4mag", "logMtot")
    for ln in lines[ds:]:
        parts = ln.split("\t")
        if len(parts) != len(hdr):
            continue
        rec = {k: v.strip() for k, v in zip(hdr, parts)}
        pgc = rec.get("PGC", "")
        if not pgc or pgc in seen_pgc:
            continue
        if all(_f(rec.get(k)) is not None for k in req_num):
            seen_pgc.add(pgc)
            rows.append(rec)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with out_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        w.writeheader()
        w.writerows(rows)
    print(f"HECATE Local Supercluster saved: {len(rows)} complete galaxies (D<=40 Mpc, logM>=9.0)", flush=True)
    return rows


def _box_cond(chunk: list[dict[str, str]], radius_deg: float) -> str:
    parts = []
    for g in chunk:
        ra, dec = float(g["RAJ2000"]), float(g["DEJ2000"])
        dr = min(10.0, radius_deg / max(0.15, math.cos(math.radians(dec))))
        dlo, dhi = max(-90.0, dec - radius_deg), min(90.0, dec + radius_deg)
        rlo, rhi = ra - dr, ra + dr
        if rlo < 0.0:
            rcond = f"(ra >= {rlo + 360.0:.6f} OR ra <= {rhi:.6f})"
        elif rhi > 360.0:
            rcond = f"(ra >= {rlo:.6f} OR ra <= {rhi - 360.0:.6f})"
        else:
            rcond = f"ra BETWEEN {rlo:.6f} AND {rhi:.6f}"
        parts.append(f"({rcond} AND dec BETWEEN {dlo:.6f} AND {dhi:.6f})")
    return " OR ".join(parts)


def _parse_votable(xml_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    fields = [(f.attrib.get("name", ""), f.attrib.get("datatype", "char"), f.attrib.get("arraysize", "1")) for f in root.iter(f"{ns}FIELD")]
    rows: list[dict[str, str]] = []
    trs = list(root.iter(f"{ns}TR"))
    if trs:
        for tr in trs:
            vals = [td.text.strip() if td.text else "" for td in tr.findall(f"{ns}TD")]
            if len(vals) == len(fields):
                rows.append(dict(zip([f[0] for f in fields], vals)))
        return rows
    stream = root.find(f".//{ns}BINARY/{ns}STREAM")
    if stream is not None and stream.text and stream.text.strip():
        buf = base64.b64decode(stream.text.strip())
        pos, blen = 0, len(buf)
        while pos < blen:
            rec: dict[str, str] = {}
            for nm, dt, arr in fields:
                if dt in ("char", "unicodeChar"):
                    step = 2 if dt == "unicodeChar" else 1
                    if arr == "*":
                        n = struct.unpack_from(">i", buf, pos)[0]
                        pos += 4
                    else:
                        n = int(arr) if arr.isdigit() else 1
                    rec[nm] = buf[pos:pos + max(0, n) * step].decode("utf-8" if step == 1 else "utf-16-be", errors="replace").strip("\x00 ")
                    pos += max(0, n) * step
                elif dt == "double":
                    v = struct.unpack_from(">d", buf, pos)[0]; pos += 8
                    rec[nm] = f"{v:.10g}" if math.isfinite(v) else ""
                elif dt == "float":
                    v = struct.unpack_from(">f", buf, pos)[0]; pos += 4
                    rec[nm] = f"{v:.8g}" if math.isfinite(v) else ""
                elif dt == "int":
                    v = struct.unpack_from(">i", buf, pos)[0]; pos += 4; rec[nm] = str(v)
                elif dt == "short":
                    v = struct.unpack_from(">h", buf, pos)[0]; pos += 2; rec[nm] = str(v)
                elif dt == "long":
                    v = struct.unpack_from(">q", buf, pos)[0]; pos += 8; rec[nm] = str(v)
                else:
                    v = struct.unpack_from(">B", buf, pos)[0]; pos += 1; rec[nm] = str(v)
            rows.append(rec)
    return rows


def _write_radio_csv(out_p: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    out_p.parent.mkdir(parents=True, exist_ok=True)
    cols = ["pgc", "source_name", "ra", "dec", "total_flux_mjy", "sep_arcsec"]
    with out_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def acquire_nvss(galaxies: list[dict[str, str]]) -> None:
    out_p = INP / "radio" / "nvss_1400mhz_galaxies.csv"
    if out_p.exists() and out_p.stat().st_size > 100:
        return
    sub = [g for g in galaxies if float(g["DEJ2000"]) >= -40.0]
    std = []
    bs = 45
    for i in range(0, len(sub), bs):
        chunk = sub[i:i + bs]
        data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "votable", "QUERY": f"SELECT name, ra, dec, flux_20_cm FROM nvss WHERE {_box_cond(chunk, 0.028)}"}).encode()
        rows = _parse_votable(_http_req("https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync", data=data, timeout=45))
        for r in rows:
            rra, rdec = _f(r.get("ra")), _f(r.get("dec"))
            if rra is None or rdec is None:
                continue
            for g in chunk:
                sep = angsep_arcsec(float(g["RAJ2000"]), float(g["DEJ2000"]), rra, rdec)
                if sep <= 95.0:
                    std.append({"pgc": g["PGC"], "source_name": r.get("name", ""), "ra": f"{rra:.6f}", "dec": f"{rdec:.6f}", "total_flux_mjy": r.get("flux_20_cm", ""), "sep_arcsec": f"{sep:.2f}"})
        if (i // bs) % 10 == 0:
            print(f"  NVSS 1.4 GHz: {min(i + bs, len(sub))}/{len(sub)} ({len(std)} hits)", flush=True)
    _write_radio_csv(out_p, std)
    print(f"NVSS saved: {len(std)} matches", flush=True)


def acquire_casda(galaxies: list[dict[str, str]]) -> None:
    sub = [g for g in galaxies if float(g["DEJ2000"]) <= 49.0]
    specs = [
        ("AS110.racs_low2_v02", "id", INP / "radio" / "racs_low_888mhz_galaxies.csv", "RACS-low 888 MHz"),
        ("AS110.racs_mid_25arcsec_sources_v01", "name", INP / "radio" / "racs_mid_1367mhz_galaxies.csv", "RACS-mid 1367.5 MHz"),
    ]
    for tbl, cname, out_p, lbl in specs:
        if out_p.exists() and out_p.stat().st_size > 100:
            continue
        std = []
        bs = 45
        for i in range(0, len(sub), bs):
            chunk = sub[i:i + bs]
            data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": f"SELECT {cname}, ra, dec, total_flux FROM {tbl} WHERE {_box_cond(chunk, 0.026)}"}).encode()
            raw = _http_req("https://casda.csiro.au/casda_vo_tools/tap/sync", data=data, timeout=45).decode("utf-8", errors="replace")
            for r in csv.DictReader(raw.splitlines()):
                rra, rdec = _f(r.get("ra")), _f(r.get("dec"))
                if rra is None or rdec is None:
                    continue
                for g in chunk:
                    sep = angsep_arcsec(float(g["RAJ2000"]), float(g["DEJ2000"]), rra, rdec)
                    if sep <= 90.0:
                        std.append({"pgc": g["PGC"], "source_name": r.get(cname, ""), "ra": f"{rra:.6f}", "dec": f"{rdec:.6f}", "total_flux_mjy": r.get("total_flux", ""), "sep_arcsec": f"{sep:.2f}"})
            if (i // bs) % 10 == 0:
                print(f"  {lbl}: {min(i + bs, len(sub))}/{len(sub)} ({len(std)} hits)", flush=True)
        _write_radio_csv(out_p, std)
        print(f"{lbl} saved: {len(std)} matches", flush=True)


def acquire_lotss(galaxies: list[dict[str, str]]) -> None:
    out_p = INP / "radio" / "lotss_dr3_144mhz_galaxies.csv"
    fp_p = INP / "radio" / "lotss_dr3_144_footprint.csv"
    sub = [g for g in galaxies if float(g["DEJ2000"]) >= -10.0]

    def _vizier_lotss_post(clist: str, rad_arcsec: int, cols: str, out_max: int = 5000) -> list[dict[str, str]]:
        b = "----N6VIZLOTSS"
        parts = [("-source", "J/A+A/659/A1/catalog"), ("-out", cols), ("-c.rs", str(rad_arcsec)), ("-out.max", str(out_max))]
        body = b""
        for k, v in parts:
            body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"-c\"; filename=\"pos.txt\"\r\nContent-Type: text/plain\r\n\r\n{clist}\r\n--{b}--\r\n".encode("utf-8")
        raw = _http_req("https://vizier.cfa.harvard.edu/viz-bin/asu-tsv", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"}, timeout=45).decode("utf-8", errors="replace")
        lines = [l for l in raw.splitlines() if l.strip() and not l.startswith("#")]
        if len(lines) < 4:
            return []
        hdr = lines[0].split("\t")
        ds = 3 if len(lines) >= 3 and set(lines[2].replace("\t", "").strip()).issubset({"-", " "}) else 1
        return [{k: v.strip() for k, v in zip(hdr, ln.split("\t"))} for ln in lines[ds:] if len(ln.split("\t")) == len(hdr)]

    if not out_p.exists():
        std = []
        bs = 120
        for i in range(0, len(sub), bs):
            chunk = sub[i:i + bs]
            clist = "\n".join(f"{float(g['RAJ2000']):.6f} {float(g['DEJ2000']):.6f}" for g in chunk) + "\n"
            rows = _vizier_lotss_post(clist, 85, "Source,RAJ2000,DEJ2000,SpeakTot")
            for r in rows:
                rra, rdec = _f(r.get("RAJ2000")), _f(r.get("DEJ2000"))
                if rra is None or rdec is None:
                    continue
                for g in chunk:
                    sep = angsep_arcsec(float(g["RAJ2000"]), float(g["DEJ2000"]), rra, rdec)
                    if sep <= 85.0:
                        std.append({"pgc": g["PGC"], "source_name": r.get("Source", ""), "ra": f"{rra:.6f}", "dec": f"{rdec:.6f}", "total_flux_mjy": r.get("SpeakTot", ""), "sep_arcsec": f"{sep:.2f}"})
            print(f"  VizieR LoTSS DR2 144 MHz: {min(i + bs, len(sub))}/{len(sub)} ({len(std)} hits)", flush=True)
        _write_radio_csv(out_p, std)
        print(f"LoTSS DR2 (VizieR mirror) saved: {len(std)} matches", flush=True)

    if not fp_p.exists():
        in_fp: set[str] = set()
        bs = 120
        for i in range(0, len(sub), bs):
            chunk = sub[i:i + bs]
            clist = "\n".join(f"{float(g['RAJ2000']):.6f} {float(g['DEJ2000']):.6f}" for g in chunk) + "\n"
            rows = _vizier_lotss_post(clist, 1800, "RAJ2000,DEJ2000", out_max=20000)
            for r in rows:
                rra, rdec = _f(r.get("RAJ2000")), _f(r.get("DEJ2000"))
                if rra is None or rdec is None:
                    continue
                for g in chunk:
                    if g["PGC"] not in in_fp and abs(float(g["DEJ2000"]) - rdec) <= 0.52 and angsep_arcsec(float(g["RAJ2000"]), float(g["DEJ2000"]), rra, rdec) <= 1800.0:
                        in_fp.add(g["PGC"])
        with fp_p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["pgc", "in_footprint"])
            w.writeheader()
            for g in galaxies:
                w.writerow({"pgc": g["PGC"], "in_footprint": g["PGC"] in in_fp})
        print(f"LoTSS 144 MHz empirical footprint: {len(in_fp)} galaxies", flush=True)


def main() -> int:
    galaxies = acquire_hecate()
    acquire_nvss(galaxies)
    acquire_casda(galaxies)
    acquire_lotss(galaxies)

    manifest = {"acquired_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "galaxies": len(galaxies), "files": {}}
    for p in sorted(INP.rglob("*")):
        if p.is_file() and p.name != "STAGE1_MANIFEST.json":
            manifest["files"][str(p.relative_to(INP))] = {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (INP / "STAGE1_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("STAGE 1 COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
