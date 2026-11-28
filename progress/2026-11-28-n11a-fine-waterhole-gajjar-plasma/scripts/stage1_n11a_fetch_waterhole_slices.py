#!/usr/bin/env python3
"""Stage 1 for Spor N11A: Fetch aligned 2.794 Hz Water-Hole slabs from 54 remote ~15.7 GB .0000.h5 scans via Keep-Alive HTTP Range."""
from __future__ import annotations

import csv
import hashlib
import http.client
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n11a_20261128_fine_waterhole_gajjar_plasma"
INP = ROOT / "inputs_n11a_20261128"
SLAB_DIR = INP / "slabs"
PYDEPS_N10 = ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad/pydeps"
if str(PYDEPS_N10) not in sys.path:
    sys.path.insert(0, str(PYDEPS_N10))

import hdf5plugin
import h5py
import numpy as np

CADENCES = [
    {"target": "GJ411", "master_star": "LALANDE21185", "cadence_id": "--72283", "dist_pc": 2.54613, "n_exoplanets": 2},
    {"target": "GJ65A", "master_star": "GJ65A", "cadence_id": "--73638", "dist_pc": 2.67491, "n_exoplanets": 0},
    {"target": "GJ866", "master_star": "EZAQR", "cadence_id": "--73872", "dist_pc": 3.41, "n_exoplanets": 0},
    {"target": "GJ54.1", "master_star": "YZCET", "cadence_id": "--73620", "dist_pc": 3.71668, "n_exoplanets": 3},
    {"target": "GJ273", "master_star": "GJ273", "cadence_id": "--517180", "dist_pc": 3.7861, "n_exoplanets": 2},
    {"target": "GJ687", "master_star": "GJ687", "cadence_id": "--75045", "cadence_id_ok": True, "dist_pc": 4.5498, "n_exoplanets": 2},
    {"target": "GJ1245AC", "master_star": "GJ1245B", "cadence_id": "--517935", "dist_pc": 4.66, "n_exoplanets": 0},
    {"target": "GJ1002", "master_star": "GJ1002", "cadence_id": "--72885", "dist_pc": 4.846134, "n_exoplanets": 2},
    {"target": "HIP1242", "master_star": "GJ1005", "cadence_id": "--73656", "dist_pc": 6.00, "n_exoplanets": 0},
]
TARGET_WATERHOLE_MHZ = 1425.0
CHUNK_SIZE = 1048576


class KeepAliveRangeFile(io.RawIOBase):
    """Persistent HTTPS Keep-Alive file-like reader for zero-download remote HDF5 chunk reads."""
    def __init__(self, url: str) -> None:
        p = urllib.parse.urlparse(url)
        self.host = p.netloc
        self.path = p.path
        self.conn = http.client.HTTPSConnection(self.host, timeout=45)
        self.conn.request("HEAD", self.path, headers={"User-Agent": "SETIsearch-N11A/1.0"})
        r = self.conn.getresponse()
        r.read()
        self.size = int(r.getheader("Content-Length"))
        self.pos = 0
        self.bytes_read = 0
        self.n_reqs = 0
        self._cache: dict[int, bytes] = {}
        self.block_sz = 256 * 1024

    def readable(self) -> bool: return True
    def seekable(self) -> bool: return True
    def tell(self) -> int: return self.pos
    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET: self.pos = offset
        elif whence == io.SEEK_CUR: self.pos += offset
        elif whence == io.SEEK_END: self.pos = self.size + offset
        return self.pos

    def _get(self, lo: int, hi: int) -> bytes:
        for att in range(1, 5):
            try:
                self.conn.request("GET", self.path, headers={"Range": f"bytes={lo}-{hi}", "User-Agent": "SETIsearch-N11A/1.0"})
                r = self.conn.getresponse()
                buf = r.read()
                if r.status not in (200, 206):
                    raise IOError(f"HTTP {r.status}")
                self.bytes_read += len(buf)
                self.n_reqs += 1
                return buf
            except Exception:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = http.client.HTTPSConnection(self.host, timeout=45)
                time.sleep(att)
        raise IOError(f"Failed Range {lo}-{hi} on {self.path}")

    def readinto(self, b) -> int:
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        if n >= self.block_sz:
            buf = self._get(self.pos, self.pos + n - 1)
            take = min(n, len(buf))
            b[:take] = buf[:take]
            self.pos += take
            return take
        out_pos = 0
        while out_pos < n:
            bidx = self.pos // self.block_sz
            boff = self.pos % self.block_sz
            if bidx not in self._cache:
                lo = bidx * self.block_sz
                hi = min(self.size - 1, lo + self.block_sz - 1)
                if len(self._cache) > 64:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[bidx] = self._get(lo, hi)
            blk = self._cache[bidx]
            take = min(n - out_pos, len(blk) - boff)
            b[out_pos : out_pos + take] = blk[boff : boff + take]
            self.pos += take
            out_pos += take
        return n

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
        super().close()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for ch in iter(lambda: fh.read(4 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def fetch_fine_cadence(cad: dict) -> dict:
    url = f"http://seti.berkeley.edu/opendata/api/get-cadence/{cad['cadence_id']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N11A/1.0"}), timeout=25) as r:
        data = json.loads(r.read().decode("utf-8"))
    fines = sorted([x for x in data.get("data", []) if x.get("url", "").endswith(".0000.h5")], key=lambda x: float(x["mjd"]))
    if len(fines) != 6:
        raise RuntimeError(f"Expected 6 .0000.h5 files for {cad['target']}, got {len(fines)}")
    roles = ["A1", "B1", "A2", "C1", "A3", "D1"]
    scans = []
    for idx, x in enumerate(fines):
        fname = x["url"].split("/")[-1]
        scans.append({
            "role": roles[idx], "scan_idx": idx, "on_off": "ON" if idx in (0, 2, 4) else "OFF",
            "api_target": x["target"], "mjd": float(x["mjd"]), "ra_deg": float(x["ra"]), "dec_deg": float(x["decl"]),
            "center_freq_mhz": float(x["center_freq"]), "remote_bytes": int(x["size"]), "remote_md5": str(x["md5sum"]),
            "url": x["url"], "filename": fname,
            "local_slab_path": str(SLAB_DIR / cad["target"].replace(".", "_") / f"{roles[idx]}_{fname}.wh1424.npy"),
        })
    return {**cad, "scans": scans}


def slice_one_scan(scan: dict) -> dict:
    dest = Path(scan["local_slab_path"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta_p = dest.with_suffix(".json")
    if dest.exists() and meta_p.exists():
        arr = np.load(dest, mmap_mode="r")
        if arr.shape[1] == CHUNK_SIZE and arr.shape[0] >= 12:
            m = json.loads(meta_p.read_text(encoding="utf-8"))
            return {**scan, **m, "status": "CACHED_OK"}

    for att in range(1, 4):
        rf = KeepAliveRangeFile(scan["url"])
        try:
            with h5py.File(rf, "r") as hf:
                ds = hf["data"]
                at = dict(ds.attrs)
                fch1 = float(at["fch1"])
                foff = float(at["foff"])
                tsamp = float(at["tsamp"])
                idx_app = int(round((TARGET_WATERHOLE_MHZ - fch1) / foff))
                c0 = (idx_app // CHUNK_SIZE) * CHUNK_SIZE
                c1 = c0 + CHUNK_SIZE
                f_hi = fch1 + foff * c0
                f_lo = fch1 + foff * (c1 - 1)
                slab = np.asarray(ds[:, 0, c0:c1], dtype=np.float32) if ds.ndim == 3 else np.asarray(ds[:, c0:c1], dtype=np.float32)
            part = dest.with_suffix(".part.npy")
            with part.open("wb") as fh:
                np.save(fh, slab)
            part.replace(dest)
            meta = {
                "chunk_c0": c0, "chunk_c1": c1, "slab_f_lo_mhz": round(min(f_lo, f_hi), 6),
                "slab_f_hi_mhz": round(max(f_lo, f_hi), 6), "foff_mhz": foff, "tsamp_s": tsamp,
                "shape": list(slab.shape), "http_bytes_fetched": rf.bytes_read, "http_reqs": rf.n_reqs,
                "slab_sha256": sha256_file(dest),
            }
            meta_p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            return {**scan, **meta, "status": "SLICED_OK"}
        except Exception as exc:
            print(f"  [WARN] attempt {att} slice failed for {scan['filename']}: {exc}", flush=True)
            time.sleep(2 * att)
        finally:
            rf.close()
    raise RuntimeError(f"Failed to slice {scan['filename']}")


def main() -> int:
    t0 = time.time()
    INP.mkdir(parents=True, exist_ok=True)
    SLAB_DIR.mkdir(parents=True, exist_ok=True)
    cads = [fetch_fine_cadence(c) for c in CADENCES]
    all_scans = [s for c in cads for s in c["scans"]]
    print(f"[N11A Stage 1] Resolved {len(cads)} fine cadences ({len(all_scans)} ~15.7 GB .0000.h5 files = {sum(s['remote_bytes'] for s in all_scans)/(1<<40):.2f} TiB remote).", flush=True)

    done_map: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(slice_one_scan, s): s for s in all_scans}
        done_n = 0
        for fut in as_completed(futs):
            res = fut.result()
            done_map[res["local_slab_path"]] = res
            done_n += 1
            if done_n % 6 == 0 or done_n == len(all_scans):
                print(f"  [{done_n}/{len(all_scans)}] {res['role']} {res['filename']} ({res['status']}, HTTP={res['http_bytes_fetched']/1e6:.1f} MB)", flush=True)

    for c in cads:
        c["scans"] = [done_map[s["local_slab_path"]] for s in c["scans"]]
        c["slab_f_lo_mhz"] = c["scans"][0]["slab_f_lo_mhz"]
        c["slab_f_hi_mhz"] = c["scans"][0]["slab_f_hi_mhz"]
        c["foff_mhz"] = c["scans"][0]["foff_mhz"]
        c["tsamp_s"] = c["scans"][0]["tsamp_s"]

    manifest = {"campaign": "SPOR_N11A_FINE_WATERHOLE_GAJJAR_PLASMA", "acquired_utc": datetime.now(timezone.utc).isoformat(), "cadences": cads}
    (INP / "n11a_waterhole_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    csv_rows = [
        {k: s[k] for k in ("api_target", "role", "filename", "remote_bytes", "http_bytes_fetched", "chunk_c0", "chunk_c1", "slab_f_lo_mhz", "slab_f_hi_mhz", "foff_mhz", "tsamp_s", "slab_sha256")}
        for c in cads for s in c["scans"]
    ]
    with (INP / "n11a_waterhole_scans.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(csv_rows[0].keys())); w.writeheader(); w.writerows(csv_rows)

    tot_http = sum(s["http_bytes_fetched"] for s in csv_rows)
    tot_remote = sum(s["remote_bytes"] for s in csv_rows)
    log = {
        "campaign": "SPOR_N11A_FINE_WATERHOLE_GAJJAR_PLASMA",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "cadences": len(cads), "scans_sliced": len(csv_rows),
        "total_remote_archive_bytes": tot_remote,
        "total_http_range_bytes": tot_http,
        "bandwidth_saved_factor": round(tot_remote / max(tot_http, 1), 2),
        "external_contacts": 0,
    }
    (INP / "stage1_acquisition_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"[N11A Stage 1] Complete in {log['elapsed_s']}s: 54/54 fine Water-Hole slabs sliced ({tot_http/(1<<30):.2f} GiB over HTTP vs {tot_remote/(1<<40):.2f} TiB remote)!", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
