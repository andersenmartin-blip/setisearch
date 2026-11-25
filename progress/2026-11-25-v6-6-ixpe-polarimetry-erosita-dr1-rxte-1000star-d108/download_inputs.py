#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D108 Physical Archival Downloader & Integrity Verifier (`V6.6`):
  - Enforces Stage-1 seal (`LOCK_RECEIPT.json`, `METHOD_LOCK.json`, all 7 SHA-256 hashes)
    and mandatory chronology lag (>= 10.0 s) BEFORE creating `inputs_d108_v6_6/`.
  - Downloads and physically validates every locked FITS / FITS.GZ / TAR.XZ / CALDB file
    across IXPE GPD, SRG/eROSITA-DE DR1, RXTE HEXTE/PCA, and ESO NIRPS/ESPRESSO/HARPS/UVES.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import tarfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from astropy.io import fits

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d108_v6_6"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _verify_stage1_locks() -> tuple[dict[str, Any], dict[str, Any], str]:
    lr = json.loads((WS / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    ml = json.loads((WS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    if lr.get("status") != "STAGE-1 SEALED":
        raise RuntimeError(f"Invalid LOCK_RECEIPT status: {lr.get('status')}")
    if lr.get("inputs_dir_exists_at_seal") is not False:
        raise RuntimeError("LOCK_RECEIPT did not certify absent inputs dir at Stage-1 seal!")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")
    if ml_sha != lr.get("method_lock_sha256"):
        raise RuntimeError("METHOD_LOCK.json SHA-256 mismatch vs LOCK_RECEIPT.json!")
    for fn, exp_sha in ml["stage_1_files"].items():
        actual = _sha256_file(WS / fn)
        if actual != exp_sha:
            raise RuntimeError(f"Stage-1 SHA-256 drift on {fn}: {actual} != {exp_sha}")
    return lr, ml, ml_sha


def _download_with_retry(url: str, dest: Path, expected_bytes: int = 0) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        if expected_bytes <= 0 or dest.stat().st_size == expected_bytes:
            return int(dest.stat().st_size)
    part = dest.with_name(dest.name + ".part")
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D108-V66/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status not in (200, 206):
                    raise RuntimeError(f"HTTP {resp.status} for {url}")
                with part.open("wb") as out:
                    while True:
                        chunk = resp.read(1 << 18)
                        if not chunk:
                            break
                        out.write(chunk)
            sz = int(part.stat().st_size)
            if sz <= 0 or (expected_bytes > 0 and sz != expected_bytes):
                raise RuntimeError(f"Byte size mismatch for {url}: got {sz}, expected {expected_bytes}")
            part.replace(dest)
            return sz
        except Exception as exc:
            last_err = exc
            if part.exists():
                part.unlink(missing_ok=True)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Download failed after retries for {url}: {last_err}")


def _validate_physical_file(inst: str, path: Path, rel: str) -> dict[str, Any]:
    low = rel.lower()
    if inst == "IXPE_GPD":
        if low.endswith((".arf", ".mrf", ".rmf")):
            with fits.open(path, memmap=False) as hdul:
                exts = [h.name.upper() for h in hdul]
                hdu_ok = [h for h in hdul[1:] if getattr(h, "data", None) is not None and len(h.data) >= 100]
                if not hdu_ok:
                    raise RuntimeError(f"Invalid IXPE CALDB file {rel}: exts={exts}")
                return {"type": "IXPE_CALDB", "exts": exts, "nrows": int(len(hdu_ok[0].data))}
        with fits.open(path, memmap=False) as hdul:
            ev = hdul["EVENTS"]
            cols = {c.upper() for c in ev.data.names}
            need = {"TIME", "PI", "Q", "U", "X", "Y"}
            if not need.issubset(cols) or len(ev.data) < 50:
                raise RuntimeError(f"Missing IXPE EVENTS columns in {rel}: {cols}")
            exp_s = float(ev.header.get("LIVETIME", ev.header.get("EXPOSURE", 0.0)))
            if exp_s <= 0.0:
                raise RuntimeError(f"Zero LIVETIME/EXPOSURE in IXPE {rel}")
            return {"type": "IXPE_EVT2", "detnam": str(ev.header.get("DETNAM", "")), "n_events": int(len(ev.data)), "livetime_s": exp_s}

    if inst == "EROSITA_DR1":
        with tarfile.open(path, "r:xz") as tf:
            names = [m.name for m in tf.getmembers() if m.isfile()]
            src020 = [n for n in names if "_020_SourceSpec_" in n]
            bg020 = [n for n in names if "_020_BackgrSpec_" in n]
            arf020 = [n for n in names if "_020_ARF_" in n]
            rmf020 = [n for n in names if "_020_RMF_" in n]
            if not (src020 and bg020 and arf020 and rmf020):
                raise RuntimeError(f"Incomplete eROSITA SourceProducts tar.xz {rel}: {names[:10]}")
            with fits.open(io.BytesIO(tf.extractfile(src020[0]).read()), memmap=False) as hs:
                spec_hdu = hs["SPECTRUM"]
                exp_s = float(spec_hdu.header.get("EXPOSURE", 0.0))
                nchan = int(len(spec_hdu.data))
                if exp_s <= 0.0 or nchan < 128:
                    raise RuntimeError(f"Invalid eROSITA 020 SourceSpec in {rel}: exp={exp_s}, nchan={nchan}")
            with fits.open(io.BytesIO(tf.extractfile(arf020[0]).read()), memmap=False) as ha:
                narf = int(len(ha["SPECRESP"].data))
            tm_specs = [n for n in names if "_SourceSpec_" in n and "_020_SourceSpec_" not in n]
            return {"type": "EROSITA_SOURCEPRODUCTS", "n_files": len(names), "n_tm_specs": len(tm_specs), "nchan": nchan, "narf": narf, "exposure_s": exp_s}

    if inst in ("RXTE_HEXTE", "RXTE_PCA"):
        with fits.open(path, memmap=False) as hdul:
            if low.endswith(".pha.gz"):
                sp = hdul["SPECTRUM"]
                exp_s = float(sp.header.get("EXPOSURE", 0.0))
                if exp_s <= 0.0 or len(sp.data) < 16:
                    raise RuntimeError(f"Invalid RXTE PHA {rel}: exp={exp_s}, n={len(sp.data)}")
                return {"type": f"{inst}_PHA", "nchan": int(len(sp.data)), "exposure_s": exp_s}
            hdu_ok = [h for h in hdul[1:] if getattr(h, "data", None) is not None and len(h.data) >= 16]
            if not hdu_ok:
                raise RuntimeError(f"Invalid RXTE response {rel}")
            return {"type": f"{inst}_RESP", "nrows": int(len(hdu_ok[0].data))}

    # ESO ESPRESSO / HARPS / NIRPS / UVES 1D Phase-3 spectra
    with fits.open(path, memmap=False) as hdul:
        tbl = hdul[1].data
        cols = {c.upper() for c in tbl.names}
        if "WAVE" not in cols or not ({"FLUX", "FLUX_REDUCED"} & cols):
            raise RuntimeError(f"Invalid ESO 1D spectrum {rel}: {cols}")
        w = tbl["WAVE"].ravel()
        if len(w) < 1000:
            raise RuntimeError(f"Short ESO spectrum {rel}: len={len(w)}")
        return {"type": "ESO_1D_SPECTRUM", "npts": int(len(w))}


def _process_physical_file(sp: dict[str, Any]) -> dict[str, Any]:
    rel = sp["rel"]
    dest = RAW_DIR / rel
    sz = _download_with_retry(sp["url"], dest, int(sp.get("bytes") or 0))
    info = _validate_physical_file(sp["instrument"], dest, rel)
    sha = _sha256_file(dest)
    return {
        "rel_path": rel,
        "url": sp["url"],
        "instrument": sp["instrument"],
        "bytes": sz,
        "sha256": sha,
        "info": info,
    }


def main() -> None:
    lr, ml, ml_sha = _verify_stage1_locks()
    lock_epoch = float(lr["locked_unix_epoch"])
    now = time.time()
    if now - lock_epoch < 10.5:
        wait_s = 10.5 - (now - lock_epoch)
        print(f"Respecting mandatory >=10s lock->download chronology lag (waiting {wait_s:.2f}s)...")
        time.sleep(wait_s)

    first_epoch = time.time()
    receipt = {
        "schema": "D108_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
        "phase_id": "D108",
        "locked_utc": ml["locked_utc"],
        "locked_unix_epoch": round(lock_epoch, 4),
        "first_download_utc": datetime.fromtimestamp(first_epoch, tz=timezone.utc).isoformat(),
        "first_download_unix_epoch": round(first_epoch, 4),
        "chronology_lag_seconds": round(first_epoch - lock_epoch, 3),
        "method_lock_sha256": ml_sha,
    }
    if receipt["chronology_lag_seconds"] < 10.0:
        raise RuntimeError(f"Chronology lag {receipt['chronology_lag_seconds']} s < 10.0 s!")
    (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    with open(WS / "FROZEN_COHORT_D108.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    exp_obs = int(ml["d108_total_observations"])
    if len(rows) != exp_obs:
        raise RuntimeError(f"Expected {exp_obs} cohort rows, got {len(rows)}")

    phys_specs: dict[str, dict[str, Any]] = {}
    for r in rows:
        rel = r["f1_rel"]
        if rel not in phys_specs:
            phys_specs[rel] = {
                "rel": rel,
                "url": r["f1_url"],
                "bytes": int(r.get("f1_bytes") or 0),
                "instrument": r["instrument"],
            }
        extras = json.loads(r.get("extra_files") or "[]")
        for ex in extras:
            erel = ex["rel"]
            if erel not in phys_specs:
                phys_specs[erel] = {
                    "rel": erel,
                    "url": ex["url"],
                    "bytes": int(ex.get("bytes") or 0),
                    "instrument": r["instrument"],
                }

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    phys_done: dict[str, dict[str, Any]] = {}
    phys_errors: dict[str, str] = {}

    non_eso_items = sorted([sp for sp in phys_specs.values() if "dataportal.eso.org" not in sp["url"]], key=lambda x: x["rel"])
    eso_items = sorted([sp for sp in phys_specs.values() if "dataportal.eso.org" in sp["url"]], key=lambda x: x["rel"])

    print(f"Downloading & validating {len(non_eso_items)} IXPE / eROSITA / RXTE archival files...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        fut_map = {ex.submit(_process_physical_file, sp): sp for sp in non_eso_items}
        for i, fut in enumerate(as_completed(fut_map), 1):
            sp = fut_map[fut]
            rel = sp["rel"]
            try:
                rec = fut.result()
                phys_done[rel] = rec
                if i % 20 == 0 or i == len(non_eso_items):
                    print(f"  [HE {i}/{len(non_eso_items)}] {rec['instrument']} {rel} OK ({rec['bytes']:,} B)")
            except Exception as exc:
                phys_errors[rel] = str(exc)
                print(f"  [ERR] {rel}: {exc}")

    print(f"Downloading & validating {len(eso_items)} ESO Orbit #193-#198 & UVES FITS (paced max_workers=2)...")
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_map = {ex.submit(_process_physical_file, sp): sp for sp in eso_items}
        for i, fut in enumerate(as_completed(fut_map), 1):
            sp = fut_map[fut]
            rel = sp["rel"]
            try:
                rec = fut.result()
                phys_done[rel] = rec
                if i % 10 == 0 or i == len(eso_items):
                    print(f"  [ESO {i}/{len(eso_items)}] {rec['instrument']} {rel} OK ({rec['bytes']:,} B)")
            except Exception as exc:
                phys_errors[rel] = str(exc)
                print(f"  [ERR] {rel}: {exc}")

    obs_results: list[dict[str, Any]] = []
    obs_errors: list[dict[str, str]] = []
    for r in rows:
        rels = [r["f1_rel"]] + [ex["rel"] for ex in json.loads(r.get("extra_files") or "[]")]
        if any(rel in phys_errors for rel in rels):
            err_msg = "; ".join(f"{rel}: {phys_errors[rel]}" for rel in rels if rel in phys_errors)
            obs_errors.append({"dp_id": r["dp_id"], "star": r["canonical_target"], "error": err_msg})
            continue
        f_list = []
        for idx_f, rel in enumerate(rels):
            pm = phys_done[rel]
            f_list.append({
                "role": "PRIMARY" if idx_f == 0 else f"EXTRA_{idx_f}",
                "rel_path": pm["rel_path"],
                "url": pm["url"],
                "bytes": pm["bytes"],
                "sha256": pm["sha256"],
            })
        pm0 = phys_done[rels[0]]
        obs_results.append({
            "status": "DOWNLOADED",
            "dp_id": r["dp_id"],
            "instrument": r["instrument"],
            "star": r["canonical_target"],
            "rel_path": pm0["rel_path"],
            "url": pm0["url"],
            "bytes": sum(int(x["bytes"]) for x in f_list),
            "sha256": pm0["sha256"],
            "info": pm0["info"],
            "files": f_list,
        })

    obs_results.sort(key=lambda x: (x["instrument"], x["star"], x["dp_id"]))
    tot_unique_bytes = sum(int(v["bytes"]) for v in phys_done.values())
    manifest = {
        "schema": "D108_FULL_INPUT_MANIFEST",
        "phase_id": "D108",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "raw_dir": str(RAW_DIR),
        "expected_observations": len(rows),
        "valid_observations": len(obs_results),
        "failed_observations": len(obs_errors),
        "expected_physical_files": len(phys_specs),
        "valid_physical_files": len(phys_done),
        "failed_physical_files": len(phys_errors),
        "total_bytes": tot_unique_bytes,
        "total_mib": round(tot_unique_bytes / (1024.0 * 1024.0), 4),
        "errors": obs_errors,
        "physical_file_errors": phys_errors,
        "physical_files": sorted(phys_done.values(), key=lambda x: x["rel_path"]),
        "observations": obs_results,
    }
    (WS / "FULL_D108_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest written: valid_obs={len(obs_results)}/{len(rows)}, valid_files={len(phys_done)}/{len(phys_specs)}, total={manifest['total_mib']:.2f} MiB")
    if obs_errors or len(phys_done) != len(phys_specs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
