"""Post-data exploratory cached drift sweep:64 fixed metadata tiles, no GETs.

Inputs: --source-manifest --arrays-dir --broad-receipt --outdir(new).
Tilek core=[159383552+(1+4*k)*4096,+4096),k=0..63, decodehalo640.
Each ON: all4096 carriers percore,763 drifts±4Hz/s,widths1/3,16rows;
reference at each ON first midpoint. Original detector remains unchanged.
Full carrier maxima/progress persist after each completed tile. Missing tiles
remain explicit NaN/zero-count inputs, never a scientific zero-hit result.
Top20 perON display NMS3sourcechannels; top6 fixed six-scan review/plots.
No OFF veto, qualified sensitivity, FAP/SNR/flux/EIRP or sky-null inference.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import h5py
import hdf5plugin
from pilot_engine_20261008.detector import Config, Scan, preprocess, search_scan
from tools.radio_quicklook_20261009.quick_search import box_arrays, fixed_witness, track_plot

ORIGIN, COUNT = 159383552, 1048576
CORES = [(ORIGIN + (1 + 4 * k) * 4096, ORIGIN + (1 + 4 * k) * 4096 + 4096) for k in range(64)]
SOURCE_SHA256 = "6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for body in iter(lambda: f.read(1024 * 1024), b""):
            h.update(body)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def make_scan(item, full_power, core, halo):
    lo, hi = core[0] - halo, core[1] + halo
    if not ORIGIN <= lo < hi <= ORIGIN + COUNT:
        raise ValueError("Declared tile/review crop exceeds physical source chunk")
    h = item["current_header"]["data_attributes"]
    return Scan(item["label"], item["role"].upper(), full_power[:, lo - ORIGIN:hi - ORIGIN],
                float(h["tstart"]), float(h["tsamp"]), float(h["fch1"]) * 1e6,
                float(h["foff"]) * 1e6, lo, np.arange(core[0], core[1], dtype=np.int64))


def ranked(scores, channels, count=20):
    selected = []
    for index in np.lexsort((channels, -scores)):
        i = int(index)
        if not np.isfinite(scores[i]):
            continue
        if all(abs(int(channels[i]) - int(channels[j])) > 3 for j in selected):
            selected.append(i)
        if len(selected) == count:
            break
    return selected


def persist_maxima(out, label, arrays):
    temporary = out / (label + "_all_carrier_maxima.npz.tmp")
    with temporary.open("wb") as f:
        np.savez_compressed(f, **arrays)
    temporary.replace(out / (label + "_all_carrier_maxima.npz"))


def sweep(args):
    out, arrays_dir = Path(args.outdir), Path(args.arrays_dir)
    started, initial_cpu = time.monotonic(), time.process_time()
    scope = json.loads((ROOT / 'tools/radio_quicklook_20261009/tile_scope.json').read_text())
    for name, expected in scope['pinned_files'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('Frozen tile scope mismatch: ' + name)
    if digest(args.source_manifest) != SOURCE_SHA256:
        raise ValueError("Original source manifest differs")
    source = json.loads(Path(args.source_manifest).read_text())
    acquired = json.loads((arrays_dir / "acquisition_summary.json").read_text())
    broad = json.loads(Path(args.broad_receipt).read_text())
    if acquired["status"] != "SIX_SCANS_ACQUIRED_EXPLORATORY_ONLY" or broad["status"] != "COMPLETED_EXPLORATORY_BROAD_ZERO_DRIFT_INVENTORY":
        raise ValueError("Complete acquired source and authenticated broad receipt required")
    if broad["source_manifest_sha256"] != SOURCE_SHA256 or not broad["all96_local_compressed_chunk_hashes_matched_received_source_payloads"]:
        raise ValueError("Prior complete local compressed-source proof is absent")
    items = source["sources"]
    if len(items) != 6 or [x["role"].upper() for x in items] != ["ON", "OFF"] * 3:
        raise ValueError("Original six-scan order changed")
    powers, compact_hashes = {}, {}
    for item in items:
        label = item["label"]
        path = arrays_dir / f"{label}.compact.h5"
        sha = digest(path)
        if sha != broad["original_compact_file_sha256"][label]:
            raise ValueError(f"{label}: compact source bytes changed after full source proof")
        with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as handle:
            data = handle["data"]
            if data.shape != (16, 1, COUNT) or data.dtype != np.dtype("<f4"):
                raise ValueError("Wrong complete chunk shape or dtype")
            power = np.asarray(data[:, 0, :], dtype=np.float32)
        if not np.isfinite(power).all() or (power < 0).any():
            raise ValueError("Invalid complete physical chunk powers")
        powers[label], compact_hashes[label] = power, sha
    cfg, drifts = Config(widths=(1, 3)), np.linspace(-4, 4, 763)
    channels = np.concatenate([np.arange(lo, hi, dtype=np.int64) for lo, hi in CORES])
    anchor = min(float(x["current_header"]["data_attributes"]["tstart"]) for x in items)
    coverage, normalization, complete, global_arrays, tops, tracks = [], {}, {}, {}, {}, []
    for item in items:
        if item["role"].upper() != "ON":
            continue
        label = item["label"]
        h = item["current_header"]["data_attributes"]
        result_arrays = {"source_reference_channels": channels,
                         "frequency_hz_at_tref": float(h["fch1"]) * 1e6 + float(h["foff"]) * 1e6 * channels,
                         "maximum_robust_box_track_score": np.full(len(channels), np.nan),
                         "winning_drift_hz_s": np.full(len(channels), np.nan),
                         "winning_width_channels": np.zeros(len(channels), dtype=np.int16),
                         "valid_hypothesis_count": np.zeros(len(channels), dtype=np.int64),
                         "drift_grid_hz_s": drifts}
        global_arrays[label] = result_arrays
        complete[label], normalization[label] = [], []
        for k, core in enumerate(CORES):
            scan = make_scan(item, powers[label], core, 640)
            times = np.arange(16) * scan.tsamp_s
            mismatch = float((drifts[1] - drifts[0]) * times[-1] / (2 * abs(scan.df_hz)))
            if mismatch > .5 + 1e-12:
                raise ValueError("Grid mismatch exceeds half a channel")
            sl = slice(k * 4096, (k + 1) * 4096)
            result, _ = search_scan(scan, result_arrays["frequency_hz_at_tref"][sl], times, drifts, cfg)
            if not np.isfinite(result["maximum_robust_box_track_score"]).all() or not np.all(result["valid_hypothesis_count"] == 1526):
                raise ValueError("Incomplete per-tile hypothesis coverage")
            for name in ("maximum_robust_box_track_score", "winning_drift_hz_s", "winning_width_channels", "valid_hypothesis_count"):
                result_arrays[name][sl] = result[name]
            norm = {key: value for key, value in result["normalization"].items() if key != "normalization_source_channels"}
            normalization[label].append({"tile_index": k, "normalization_core_half_open": list(core), "per_row": norm})
            complete[label].append(k)
            coverage.append({"scan_id": label, "tile_index": k, "core_half_open": list(core),
                             "decode_crop_half_open": [core[0] - 640, core[1] + 640],
                             "carrier_count": 4096, "valid_hypotheses_per_carrier": 1526,
                             "drift_trials": 763, "widths_channels": [1, 3],
                             "maximum_half_grid_mismatch_channels": mismatch,
                             "reference_mjd": float(scan.tstart_mjd + .5 * scan.tsamp_s / 86400)})
            persist_maxima(out, label, result_arrays)
            save(out / "tile_normalization.json", normalization)
            save(out / "coverage_manifest.json", {"status": "RUNNING_OR_PARTIAL_UNTIL_FINAL_RECEIPT",
                        "metadata_cores_half_open": CORES, "completed_tile_indices_by_ON": complete, "completed_coverage": coverage})
            print("SEARCHED", label, "tile", k, "carriers4096", flush=True)
    for item in items:
        if item["role"].upper() != "ON":
            continue
        label = item["label"]
        result = global_arrays[label]
        h = item["current_header"]["data_attributes"]
        ref = (h["tstart"] - anchor) * 86400 + .5 * h["tsamp"]
        top = []
        for rank, i in enumerate(ranked(result["maximum_robust_box_track_score"], channels), 1):
            k = i // 4096
            track = {"track_id": f"{label}_sweep_rank_{rank:02d}", "originating_scan": label,
                     "display_rank": rank, "originating_tile_index": k, "source_reference_channel": int(channels[i]),
                     "reference_frequency_hz": float(result["frequency_hz_at_tref"][i]),
                     "reference_seconds_from_anchor": float(ref), "reference_mjd": float(anchor + ref / 86400),
                     "drift_hz_s": float(result["winning_drift_hz_s"][i]),
                     "width_channels": int(result["winning_width_channels"][i]),
                     "maximum_robust_box_track_score": float(result["maximum_robust_box_track_score"][i]),
                     "status": "POST_DATA_EXPLORATORY_RANKED_TRACK_UNCLASSIFIED"}
            top.append(track.copy())
            if rank <= 6:
                scans, zs, witnesses, norms = [], {}, [], {}
                for target in items:
                    scan = make_scan(target, powers[target["label"]], CORES[k], 4000)
                    z, mask, norm = preprocess(scan, cfg)
                    if not mask.all():
                        raise ValueError("Complete unmasked witness crop required")
                    mids = (scan.tstart_mjd - anchor) * 86400 + (np.arange(16) + .5) * scan.tsamp_s
                    witnesses.append(fixed_witness(scan, box_arrays(z), mids - ref, track["reference_frequency_hz"],
                                                   track["drift_hz_s"], track["width_channels"]))
                    norms[scan.scan_id] = {key: value for key, value in norm.items() if key != "normalization_source_channels"}
                    scans.append(scan)
                    zs[scan.scan_id] = z
                track["six_scan_fixed_track_witnesses"] = witnesses
                track["fixed_review_normalization_core_half_open"] = list(CORES[k])
                track["fixed_review_normalization_per_scan"] = norms
                track_plot(scans, zs, anchor, track, out / f"{track['track_id']}.png")
                tracks.append(track)
            tops[label] = top
            save(out / "global_top20_per_on.json", tops)
            save(out / "selected_track_witnesses.json", tracks)
    receipt = {"status": "COMPLETED_POST_DATA_EXPLORATORY_CACHED_TILE_DRIFT_SWEEP",
               "script_sha256": digest(__file__), "source_manifest_sha256": SOURCE_SHA256,
               "prior_broad_receipt_sha256": digest(args.broad_receipt), "compact_file_sha256": compact_hashes,
               "new_GETs": 0, "new_external_source_bytes": 0, "independent_visits": 1,
               "complete_tiles_per_ON": complete, "complete_carriers_per_ON": len(channels),
               "searched_disjoint_channel_edge_band_width_hz_per_ON": len(channels) * abs(float(items[0]["current_header"]["data_attributes"]["foff"])) * 1e6,
               "drift_trials": 763, "widths_channels": [1, 3], "hypotheses_per_carrier": 1526,
               "ON_integration_exposure_seconds": sum(16 * float(x["current_header"]["data_attributes"]["tsamp"]) for x in items if x["role"].upper() == "ON"),
               "old_A_B_qualification": "FAIL_CLOSED_UNCHANGED", "OFF_veto_or_detection_classification": False,
               "calibrated_SNR_FAP_flux_EIRP": False, "full_physical_chunk_drift_coverage": False,
               "reference": "Each ON first integration midpoint; tile cores are spaced metadata selections",
               "selection": "Post-data exploratory decision; fixed64tile geometry is not amplitude-selected",
               "limits": "Linear topocentric drift widths1/3 only; unknown calibrated sensitivity; no sky-null inference",
               "analysis_wall_seconds": time.monotonic() - started, "analysis_CPU_seconds": time.process_time() - initial_cpu,
               "process_CPU_seconds_including_imports": time.process_time(),
               "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    save(out / "TILE_SWEEP_RECEIPT.json", receipt)
    save(out / "coverage_manifest.json", {"status": receipt["status"], "metadata_cores_half_open": CORES,
                    "completed_tile_indices_by_ON": complete, "completed_coverage": coverage})
    print(json.dumps(receipt, allow_nan=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-manifest", "arrays-dir", "broad-receipt", "outdir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    Path(args.outdir).mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CPU, (800, 810))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError("Bounded tile sweep CPU/wall deadline")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(1800)
    try:
        sweep(args)
    except BaseException as exc:
        save(Path(args.outdir) / "TILE_SWEEP_FAILURE.json", {"status": "FAILED_OR_PARTIAL_EXPLORATORY_TILE_SWEEP",
             "error_type": type(exc).__name__, "error": str(exc), "retry_authorized": False,
             "complete_tiles_and_maxima_preserved_in_coverage_manifest": True})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
