#!/usr/bin/env python3
"""
Stage 1 Live All-Sky Radio Catalog Acquisition for Spor N4 (1,083 Master Stars):
- Forces IPv4 (socket.AF_INET)
- ASTRON TAP multipart UPLOAD (single-shot xmatch across all 1,083 stars):
    * lolss.source_catalog (54 MHz)
    * lotss_dr3.main_sources (144 MHz)
    * tgssadr.main (150 MHz)
- CSIRO CASDA TAP (OR-batched CONTAINS across Dec < +49 deg):
    * AS110.racs_low2_v02 (888 MHz)
    * AS110.racs_mid_25arcsec_sources_v01 (1367.5 MHz)
- NASA HEASARC TAP VOTable (OR-batched CONTAINS):
    * nvss (1.4 GHz), first (1.4 GHz), sumss (843 MHz), vlssr (74 MHz)
- Harvard CfA VizieR:
    * CHIME/FRB Catalog 1 (J/ApJS/257/59/table2)
Standardizes every match CSV to: star,source_name,ra,dec,total_flux_mjy,e_total_flux_mjy,peak_flux_mjy,rms_mjy,sep_arcsec
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

# Critical IPv4 force helper
_orig_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, fam=0, t=0, pr=0, fl=0: _orig_gai(h, p, socket.AF_INET, t, pr, fl)

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n4_20261127_lowfreq_radio_bridge_1083"
INP = ROOT / "inputs_n4_20261127"
TABLE1 = ROOT / "setisearch" / "zenodo_package" / "tables" / "table1_master_catalog_1083stars.csv"

OUT_COLS = ["star", "source_name", "ra", "dec", "total_flux_mjy", "e_total_flux_mjy", "peak_flux_mjy", "rms_mjy", "sep_arcsec"]


def _f(v: Any) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def _http_req(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 45, retries: int = 4) -> bytes:
    hdrs = {"User-Agent": "SETI-N4-Radio/1.0"}
    if headers:
        hdrs.update(headers)
    last_err = None
    for att in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (att + 1))
    raise RuntimeError(f"Failed {url}: {last_err}")


def _write_std_csv(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in OUT_COLS})


def build_stars_votable(stars: list[dict[str, Any]]) -> str:
    hdr = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">\n'
        '<RESOURCE><TABLE>\n'
        '<FIELD name="star" datatype="char" arraysize="*"/>\n'
        '<FIELD name="ra_deg" datatype="double"/>\n'
        '<FIELD name="dec_deg" datatype="double"/>\n'
        '<DATA><TABLEDATA>\n'
    )
    trs = "".join(f"<TR><TD>{s['star']}</TD><TD>{s['ra_deg']}</TD><TD>{s['dec_deg']}</TD></TR>\n" for s in stars)
    return hdr + trs + "</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>"


def astron_tap_upload(vot_xml: str, adql: str) -> list[dict[str, str]]:
    bd = "----ASTRON_N4_BOUNDARY_77"
    parts = []
    for k, v in [("REQUEST", "doQuery"), ("LANG", "ADQL"), ("FORMAT", "csv"), ("UPLOAD", "stars,param:stars_vot"), ("QUERY", adql)]:
        parts.append(f"--{bd}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8"))
    parts.append(f"--{bd}\r\nContent-Disposition: form-data; name=\"stars_vot\"; filename=\"stars.vot\"\r\nContent-Type: application/x-votable+xml\r\n\r\n{vot_xml}\r\n".encode("utf-8"))
    parts.append(f"--{bd}--\r\n".encode("utf-8"))
    raw = _http_req("https://vo.astron.nl/tap/sync", data=b"".join(parts), headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, timeout=90)
    txt = raw.decode("utf-8", errors="replace")
    if txt.lstrip().startswith("<") and "ERROR" in txt[:600]:
        raise RuntimeError(f"ASTRON TAP error: {txt[:500]}")
    return list(csv.DictReader(txt.splitlines()))


def _astron_query_csv(adql: str, timeout: int = 45) -> list[dict[str, str]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}).encode("utf-8")
    raw = _http_req("https://vo.astron.nl/tap/sync", data=data, timeout=timeout)
    txt = raw.decode("utf-8", errors="replace")
    if txt.lstrip().startswith("<") and "ERROR" in txt[:600]:
        raise RuntimeError(f"ASTRON TAP error: {txt[:500]}")
    return list(csv.DictReader(txt.splitlines()))


def acquire_astron(stars: list[dict[str, Any]]) -> None:
    vot = build_stars_votable(stars)

    # 1. LoLSS 54 MHz (fast on 54 MHz catalog)
    p_lol = INP / "astron" / "lolss_54mhz_matches.csv"
    if not p_lol.exists():
        rows = astron_tap_upload(
            vot,
            "SELECT u.star, s.source AS source_name, s.ra, s.dec, s.tot_flux AS total_flux, s.e_tot_flux AS e_total_flux, s.peak_flux, s.isl_rms AS rms, "
            "DISTANCE(POINT('ICRS',u.ra_deg,u.dec_deg),POINT('ICRS',s.ra,s.dec))*3600 AS sep_arcsec "
            "FROM TAP_UPLOAD.stars AS u JOIN lolss.source_catalog AS s "
            "ON 1=CONTAINS(POINT('ICRS',u.ra_deg,u.dec_deg), CIRCLE('ICRS',s.ra,s.dec, 0.05))"
        )
        std = [{
            "star": r["star"], "source_name": r.get("source_name", ""), "ra": r["ra"], "dec": r["dec"],
            "total_flux_mjy": r.get("total_flux", ""), "e_total_flux_mjy": r.get("e_total_flux", ""),
            "peak_flux_mjy": r.get("peak_flux", ""), "rms_mjy": r.get("rms", "4.0"), "sep_arcsec": f"{float(r['sep_arcsec']):.4f}",
        } for r in rows]
        _write_std_csv(p_lol, std)
        print(f"LoLSS 54 MHz matches (<180\"): {len(std)}", flush=True)
    fp_lol = INP / "astron" / "lolss_54_footprint.csv"
    if not fp_lol.exists():
        mrows = astron_tap_upload(
            vot,
            "SELECT DISTINCT u.star FROM TAP_UPLOAD.stars AS u JOIN lolss.source_catalog AS s "
            "ON 1=CONTAINS(POINT('ICRS',u.ra_deg,u.dec_deg), CIRCLE('ICRS',s.ra,s.dec, 1.5))"
        )
        in_fp = {r["star"] for r in mrows}
        with fp_lol.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["star", "in_footprint"])
            w.writeheader()
            for s in stars:
                w.writerow({"star": s["star"], "in_footprint": s["star"] in in_fp})
        print(f"LoLSS 54 MHz: {len(in_fp)} stars in empirical footprint", flush=True)

    # 2. LoTSS DR3 144 MHz via fast Q3C OR-batched cones (Dec > -10 deg) & lotss_dr3.mosaics footprint
    p_lot = INP / "astron" / "lotss_dr3_144mhz_matches.csv"
    if not p_lot.exists():
        sub_n = [s for s in stars if float(s["dec_deg"]) >= -10.0]
        std = []
        for i in range(0, len(sub_n), 25):
            chunk = sub_n[i:i + 25]
            cond = " OR ".join(f"1=CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',{float(s['ra_deg']):.6f},{float(s['dec_deg']):.6f},0.02))" for s in chunk)
            rows = _astron_query_csv(f"SELECT source_name, ra, dec, total_flux, e_total_flux, peak_flux, isl_rms FROM lotss_dr3.main_sources WHERE {cond}")
            for r in rows:
                r_ra, r_dec = _f(r.get("ra")), _f(r.get("dec"))
                if r_ra is None or r_dec is None:
                    continue
                for s in chunk:
                    sep = angsep_arcsec(float(s["ra_deg"]), float(s["dec_deg"]), r_ra, r_dec)
                    if sep <= 72.0:
                        std.append({
                            "star": s["star"], "source_name": r.get("source_name", ""), "ra": r["ra"], "dec": r["dec"],
                            "total_flux_mjy": r.get("total_flux", ""), "e_total_flux_mjy": r.get("e_total_flux", ""),
                            "peak_flux_mjy": r.get("peak_flux", ""), "rms_mjy": r.get("isl_rms", "0.10"), "sep_arcsec": f"{sep:.4f}",
                        })
            time.sleep(0.10)
        _write_std_csv(p_lot, std)
        print(f"LoTSS DR3 144 MHz matches (<72\"): {len(std)}", flush=True)

    fp_lot = INP / "astron" / "lotss_dr3_144_footprint.csv"
    if not fp_lot.exists():
        mosaics = _astron_query_csv("SELECT centeralpha, centerdelta FROM lotss_dr3.mosaics")
        in_fp = set()
        for s in stars:
            sra, sdec = float(s["ra_deg"]), float(s["dec_deg"])
            if sdec < -10.0:
                continue
            for m in mosaics:
                mra, mdec = _f(m.get("centeralpha")), _f(m.get("centerdelta"))
                if mra is not None and mdec is not None and abs(mdec - sdec) <= 3.6:
                    if angsep_arcsec(sra, sdec, mra, mdec) <= 3.5 * 3600.0:
                        in_fp.add(s["star"])
                        break
        with fp_lot.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["star", "in_footprint"])
            w.writeheader()
            for s in stars:
                w.writerow({"star": s["star"], "in_footprint": s["star"] in in_fp})
        print(f"LoTSS DR3 144 MHz: {len(in_fp)} stars in empirical mosaic footprint", flush=True)

    # 3. TGSS ADR1 150 MHz via fast Q3C OR-batched cones (Dec > -53 deg)
    p_tgs = INP / "astron" / "tgss_150mhz_matches.csv"
    if not p_tgs.exists():
        sub_t = [s for s in stars if float(s["dec_deg"]) >= -53.0]
        std = []
        for i in range(0, len(sub_t), 25):
            chunk = sub_t[i:i + 25]
            cond = " OR ".join(f"1=CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',{float(s['ra_deg']):.6f},{float(s['dec_deg']):.6f},0.03))" for s in chunk)
            rows = _astron_query_csv(f"SELECT id, ra, dec, sint, e_sint, spk, island_rms FROM tgssadr.main WHERE {cond}")
            for r in rows:
                r_ra, r_dec = _f(r.get("ra")), _f(r.get("dec"))
                if r_ra is None or r_dec is None:
                    continue
                for s in chunk:
                    sep = angsep_arcsec(float(s["ra_deg"]), float(s["dec_deg"]), r_ra, r_dec)
                    if sep <= 108.0:
                        std.append({
                            "star": s["star"], "source_name": r.get("id", ""), "ra": r["ra"], "dec": r["dec"],
                            "total_flux_mjy": r.get("sint", ""), "e_total_flux_mjy": r.get("e_sint", ""),
                            "peak_flux_mjy": r.get("spk", ""), "rms_mjy": r.get("island_rms", "3.5"), "sep_arcsec": f"{sep:.4f}",
                        })
            time.sleep(0.10)
        _write_std_csv(p_tgs, std)
        print(f"TGSS 150 MHz matches (<108\"): {len(std)}", flush=True)


def _casda_query_csv(adql: str) -> list[dict[str, str]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}).encode("utf-8")
    raw = _http_req("https://casda.csiro.au/casda_vo_tools/tap/sync", data=data, timeout=45)
    txt = raw.decode("utf-8", errors="replace")
    if txt.lstrip().startswith("<") and "ERROR" in txt[:600]:
        raise RuntimeError(f"CASDA error: {txt[:400]}")
    return list(csv.DictReader(txt.splitlines()))


def _box_cond(chunk: list[dict[str, Any]], radius_deg: float) -> str:
    parts = []
    for s in chunk:
        ra, dec = float(s["ra_deg"]), float(s["dec_deg"])
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


def acquire_casda(stars: list[dict[str, Any]]) -> None:
    sub = [s for s in stars if float(s["dec_deg"]) <= 49.0]
    specs = [
        ("AS110.racs_low2_v02", INP / "casda" / "racs_low_888mhz_matches.csv", "0.30", "RACS-low 888 MHz"),
        ("AS110.racs_mid_25arcsec_sources_v01", INP / "casda" / "racs_mid_1367mhz_matches.csv", "0.20", "RACS-mid 1367.5 MHz"),
    ]
    for tbl, out_p, def_rms, lbl in specs:
        if out_p.exists():
            continue
        col_rows = _casda_query_csv(f"SELECT column_name, unit FROM tap_schema.columns WHERE table_name='{tbl}'")
        cmap = {r["column_name"]: (r.get("unit") or "").lower() for r in col_rows}
        c_name = next((c for c in ("source_name", "name", "id") if c in cmap), list(cmap)[0])
        c_tf = next(c for c in ("total_flux_source", "total_flux", "flux_int", "s_int") if c in cmap)
        c_etf = next((c for c in ("e_total_flux_source", "e_total_flux", "e_flux_int") if c in cmap), c_tf)
        c_pf = next((c for c in ("peak_flux", "flux_peak") if c in cmap), c_tf)
        c_rms = next((c for c in ("noise", "rms", "rms_noise") if c in cmap), None)
        sel = f"{c_name}, ra, dec, {c_tf}, {c_etf}, {c_pf}" + (f", {c_rms}" if c_rms else "")
        tf_mult = 1000.0 if cmap.get(c_tf, "") == "jy" else 1.0

        std: list[dict[str, Any]] = []
        bs = 35
        for i in range(0, len(sub), bs):
            chunk = sub[i:i + bs]
            cond = _box_cond(chunk, 0.017)
            rows = _casda_query_csv(f"SELECT {sel} FROM {tbl} WHERE {cond}")
            for r in rows:
                r_ra, r_dec = _f(r.get("ra")), _f(r.get("dec"))
                if r_ra is None or r_dec is None:
                    continue
                for s in chunk:
                    sep = angsep_arcsec(float(s["ra_deg"]), float(s["dec_deg"]), r_ra, r_dec)
                    if sep <= 54.0:
                        tf = (_f(r.get(c_tf)) or 0.0) * tf_mult
                        etf = (_f(r.get(c_etf)) or 0.0) * tf_mult
                        pf = (_f(r.get(c_pf)) or 0.0) * tf_mult
                        rm = ((_f(r.get(c_rms)) or 0.0) * tf_mult) if c_rms else float(def_rms)
                        std.append({
                            "star": s["star"], "source_name": r.get(c_name, ""), "ra": f"{r_ra:.6f}", "dec": f"{r_dec:.6f}",
                            "total_flux_mjy": f"{tf:.4f}", "e_total_flux_mjy": f"{etf:.4f}",
                            "peak_flux_mjy": f"{pf:.4f}", "rms_mjy": f"{rm:.4f}", "sep_arcsec": f"{sep:.4f}",
                        })
            if (i // bs) % 6 == 0:
                print(f"  {lbl}: {min(i + bs, len(sub))}/{len(sub)} stars ({len(std)} hits)", flush=True)
            time.sleep(0.05)
        _write_std_csv(out_p, std)
        print(f"{lbl}: {len(std)} matches (<54\") across {len(sub)} stars", flush=True)


def _parse_votable(xml_bytes: bytes) -> tuple[list[dict[str, str]], dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    for info in root.iter(f"{ns}INFO"):
        if info.attrib.get("name") == "QUERY_STATUS" and info.attrib.get("value") == "ERROR":
            raise RuntimeError(f"HEASARC TAP ERROR: {(info.text or '').strip()}")
    fields: list[tuple[str, str, str]] = []
    units: dict[str, str] = {}
    for fld in root.iter(f"{ns}FIELD"):
        nm = fld.attrib.get("name", "")
        dt = fld.attrib.get("datatype", "char")
        arr = fld.attrib.get("arraysize", "1")
        fields.append((nm, dt, arr))
        units[nm] = (fld.attrib.get("unit") or "").lower()

    rows: list[dict[str, str]] = []
    trs = list(root.iter(f"{ns}TR"))
    if trs:
        for tr in trs:
            vals = [td.text.strip() if td.text else "" for td in tr.findall(f"{ns}TD")]
            if len(vals) == len(fields):
                rows.append(dict(zip([f[0] for f in fields], vals)))
        return rows, units

    stream = root.find(f".//{ns}BINARY/{ns}STREAM")
    if stream is not None and stream.text and stream.text.strip():
        buf = base64.b64decode(stream.text.strip())
        pos = 0
        blen = len(buf)
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
                    raw_s = buf[pos:pos + max(0, n) * step]
                    pos += max(0, n) * step
                    rec[nm] = raw_s.decode("utf-8" if step == 1 else "utf-16-be", errors="replace").strip("\x00 ")
                elif dt == "double":
                    v = struct.unpack_from(">d", buf, pos)[0]
                    pos += 8
                    rec[nm] = f"{v:.10g}" if math.isfinite(v) else ""
                elif dt == "float":
                    v = struct.unpack_from(">f", buf, pos)[0]
                    pos += 4
                    rec[nm] = f"{v:.8g}" if math.isfinite(v) else ""
                elif dt == "int":
                    v = struct.unpack_from(">i", buf, pos)[0]
                    pos += 4
                    rec[nm] = str(v)
                elif dt == "short":
                    v = struct.unpack_from(">h", buf, pos)[0]
                    pos += 2
                    rec[nm] = str(v)
                elif dt == "long":
                    v = struct.unpack_from(">q", buf, pos)[0]
                    pos += 8
                    rec[nm] = str(v)
                elif dt in ("unsignedByte", "boolean"):
                    v = struct.unpack_from(">B", buf, pos)[0]
                    pos += 1
                    rec[nm] = str(v)
                else:
                    raise ValueError(f"Unsupported VOTable BINARY datatype: {dt}")
            rows.append(rec)
    return rows, units


def _heasarc_query(adql: str) -> tuple[list[dict[str, str]], dict[str, str]]:
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "votable", "QUERY": adql}).encode("utf-8")
    raw = _http_req("https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync", data=data, timeout=45)
    return _parse_votable(raw)


def acquire_heasarc(stars: list[dict[str, Any]]) -> None:
    specs = [
        ("nvss", INP / "heasarc" / "nvss_1400mhz_matches.csv", -40.0, 90.0, 0.015, 0.45,
         "name, ra, dec, flux_20_cm, flux_20_cm_error", "flux_20_cm", "flux_20_cm_error", "flux_20_cm", None, "NVSS 1.4 GHz"),
        ("first", INP / "heasarc" / "first_1400mhz_matches.csv", -11.0, 90.0, 0.012, 0.15,
         "name, ra, dec, int_flux_20_cm, flux_20_cm_error, flux_20_cm", "int_flux_20_cm", "flux_20_cm_error", "flux_20_cm", None, "FIRST 1.4 GHz"),
        ("sumss", INP / "heasarc" / "sumss_843mhz_matches.csv", -90.0, -30.0, 0.015, 1.20,
         "name, ra, dec, int_flux_36_cm, int_flux_36_cm_error, flux_36_cm", "int_flux_36_cm", "int_flux_36_cm_error", "flux_36_cm", None, "SUMSS 843 MHz"),
        ("vlssr", INP / "heasarc" / "vlssr_74mhz_matches.csv", -30.0, 90.0, 0.025, 100.0,
         "name, ra, dec, flux_74_mhz, flux_74_mhz_error, rms_74_mhz", "flux_74_mhz", "flux_74_mhz_error", "flux_74_mhz", "rms_74_mhz", "VLSSr 74 MHz"),
    ]
    for tbl, out_p, dmin, dmax, r_deg, def_rms, sel, c_tf, c_etf, c_pf, c_rms, lbl in specs:
        if out_p.exists():
            continue
        sub = [s for s in stars if dmin <= float(s["dec_deg"]) <= dmax]
        std: list[dict[str, Any]] = []
        bs = 35
        for i in range(0, len(sub), bs):
            chunk = sub[i:i + bs]
            cond = _box_cond(chunk, r_deg * 1.15)
            rows, _ = _heasarc_query(f"SELECT {sel} FROM {tbl} WHERE {cond}")
            for r in rows:
                r_ra, r_dec = _f(r.get("ra")), _f(r.get("dec"))
                if r_ra is None or r_dec is None:
                    continue
                for s in chunk:
                    sep = angsep_arcsec(float(s["ra_deg"]), float(s["dec_deg"]), r_ra, r_dec)
                    if sep <= r_deg * 3600.0:
                        tf = _f(r.get(c_tf)) or 0.0
                        etf = _f(r.get(c_etf)) or def_rms
                        pf = _f(r.get(c_pf)) or tf
                        rm = (_f(r.get(c_rms)) or def_rms) if c_rms else def_rms
                        std.append({
                            "star": s["star"], "source_name": r.get("name", ""), "ra": f"{r_ra:.6f}", "dec": f"{r_dec:.6f}",
                            "total_flux_mjy": f"{tf:.4f}", "e_total_flux_mjy": f"{etf:.4f}",
                            "peak_flux_mjy": f"{pf:.4f}", "rms_mjy": f"{rm:.4f}", "sep_arcsec": f"{sep:.4f}",
                        })
            if (i // bs) % 6 == 0:
                print(f"  {lbl}: {min(i + bs, len(sub))}/{len(sub)} stars ({len(std)} hits)", flush=True)
            time.sleep(0.05)
        _write_std_csv(out_p, std)
        print(f"{lbl}: {len(std)} matches across {len(sub)} stars", flush=True)

    fp_first = INP / "heasarc" / "first_1400_footprint.csv"
    if not fp_first.exists():
        sub_f = [s for s in stars if float(s["dec_deg"]) >= -11.0]
        in_fp: set[str] = set()
        bs = 35
        for i in range(0, len(sub_f), bs):
            chunk = sub_f[i:i + bs]
            cond = _box_cond(chunk, 0.25)
            rows, _ = _heasarc_query(f"SELECT ra, dec FROM first WHERE {cond}")
            for r in rows:
                r_ra, r_dec = _f(r.get("ra")), _f(r.get("dec"))
                if r_ra is None or r_dec is None:
                    continue
                for s in chunk:
                    if s["star"] not in in_fp and angsep_arcsec(float(s["ra_deg"]), float(s["dec_deg"]), r_ra, r_dec) <= 1800.0:
                        in_fp.add(s["star"])
            if (i // bs) % 6 == 0:
                print(f"  FIRST footprint: {min(i + bs, len(sub_f))}/{len(sub_f)} ({len(in_fp)} in)", flush=True)
            time.sleep(0.05)
        with fp_first.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["star", "in_footprint"])
            w.writeheader()
            for s in stars:
                w.writerow({"star": s["star"], "in_footprint": s["star"] in in_fp})
        print(f"FIRST 1.4 GHz empirical footprint: {len(in_fp)} stars", flush=True)


def acquire_chime() -> None:
    p_ch = INP / "chime" / "chime_frb_cat1.tsv"
    if p_ch.exists():
        return
    u = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-source=J/ApJS/257/59/table2&-out.max=unlimited&-out=FRB,RAJ2000,DEJ2000,e_RAJ2000,e_DEJ2000,DM,Fluence,PeakFlux,Rep"
    raw = _http_req(u, timeout=30)
    p_ch.parent.mkdir(parents=True, exist_ok=True)
    p_ch.write_bytes(raw)
    lines = [l for l in raw.decode("utf-8", "replace").splitlines() if l and not l.startswith("#")]
    print(f"CHIME/FRB Cat 1 downloaded: {len(lines)} TSV lines", flush=True)


def main() -> int:
    stars = list(csv.DictReader(TABLE1.open(encoding="utf-8")))
    assert len(stars) == 1083
    acquire_astron(stars)
    acquire_casda(stars)
    acquire_heasarc(stars)
    acquire_chime()

    manifest = {"acquired_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "stars": len(stars), "files": {}}
    for p in sorted(INP.rglob("*")):
        if p.is_file() and p.name != "STAGE1_MANIFEST.json":
            manifest["files"][str(p.relative_to(INP))] = {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (INP / "STAGE1_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("STAGE 1 COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
