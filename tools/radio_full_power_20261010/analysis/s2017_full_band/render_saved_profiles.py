"""Render one completed S2017 extension batch; no raw source read.

Prepare this renderer before fresh values, and run only after root GO following
a COMPLETE search. The cyan line is the selected, frozen track coordinate.
It does not identify a detected signal. All three fixed ranks are displayed.
The supplied receipt hash identifies one completed batch, kept separate from
the previously completed q128 search. No new visit or blind validation is added.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

VISIT_LABEL = "visit20170428_Sband"
TSAMP = 18.253611008
SCANS = ["epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off"]
COMPLETE_STATUS = "COMPLETE_S2017_PREVIOUSLY_UNSEARCHED_INTERIOR_BATCH_EXPLORATORY_ONLY"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--expected-receipt-sha256", required=True)
    parser.add_argument("--out", required=True, help="Rank1 PNG; rank2/rank3 use the same filename stem")
    parser.add_argument("--root-go-after-complete", action="store_true")
    args = parser.parse_args()
    if not args.root_go_after_complete:
        raise ValueError("Root GO after completed search is required")
    started = time.monotonic()
    directory = Path(args.measurement).resolve()
    scope_path = Path(args.scope).resolve()
    receipt_path = directory/"EXECUTION_RECEIPT.json"
    if digest(receipt_path) != args.expected_receipt_sha256:
        raise ValueError("Actual completed batch receipt hash differs")
    receipt = json.loads(receipt_path.read_text())
    # Admit metadata before reading any saved scientific patches.
    if (receipt.get("status") != COMPLETE_STATUS
            or receipt.get("phase") != "previously_unsearched_interior_batch"
            or receipt.get("scope_sha256") != digest(scope_path)):
        raise ValueError("Completed search receipt and matching scope required")
    scope = json.loads(scope_path.read_text())
    declared_search_suffix = "/"+scope["output_stage"].strip("/")
    if not str(directory).endswith(declared_search_suffix):
        raise ValueError("Measurement directory differs from this receipt's scope stage")
    if (scope.get("tsamp_s") != TSAMP or scope.get("scan_order") != SCANS
            or scope.get("rows_per_scan") != 16
            or scope.get("native_chunk_index") != 171
            or scope.get("expected_fixed_profiles") != 9
            or scope.get("new_visit") is not False or scope.get("new_acquisition") is not False
            or scope.get("original_q128_search_rerun") is not False
            or scope.get("batch_id") not in ("batch01","batch02","batch03")
            or receipt.get("batch_id") != scope.get("batch_id")):
        raise ValueError("S2017 extension geometry differs from the verified scope")
    summary = receipt["search_summary"]
    core_count = len(scope["core_q_indices"])
    if (summary["completed_ON_maps"] != 3*core_count
            or summary["cores_per_ON"] != core_count
            or summary["carriers_per_ON"] != 4096*core_count
            or summary["drift_grid_count"] != 785 or summary["widths_channels"] != [1,3]
            or receipt["fixed_profile_summary"]["profile_count"] != 9):
        raise ValueError("Completed fixed search/profile family required")
    profiles_path = directory/"FIXED_TOP3_PROFILES.json"
    records = json.loads(profiles_path.read_text())
    if len(records) != 9:
        raise ValueError("Exactly nine saved profiles required")
    top_path = directory/"DRIFT_TOP20.json"
    if digest(top_path) != receipt["fixed_profile_summary"]["source_top20_sha256"]:
        raise ValueError("Saved selection source differs")
    tops = json.loads(top_path.read_text())
    for record in records:
        track = record["selected_track"]
        saved = next(t for t in tops[track["originating_scan"]]
                     if t["display_rank"] == track["display_rank"])
        if track != saved or scope["batch_id"] not in track["track_id"]:
            raise ValueError("Fixed profile identity differs from the pinned batch selection")
    identities = [(r["selected_track"]["originating_scan"], r["selected_track"]["display_rank"])
                  for r in records]
    if set(identities) != {(s,r) for s in SCANS[::2] for r in (1,2,3)}:
        raise ValueError("Three fixed ranks for each origin ON required")
    output = Path(args.out).resolve()
    outputs = [output] + [output.with_name(output.stem+f"_RANK{rank}"+output.suffix) for rank in (2,3)]
    report_path = output.with_suffix(".json")
    if output.suffix.lower() != ".png" or any(p.exists() for p in outputs+[report_path]):
        raise ValueError("New PNG destinations and receipt required; no overwrite")
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output.parent.mkdir(parents=True, exist_ok=True)
    sources = []
    for rank, destination in zip((1,2,3),outputs):
        chosen = [next(r for r in records if r["selected_track"]["originating_scan"] == scan
                       and r["selected_track"]["display_rank"] == rank) for scan in SCANS[::2]]
        fig, axes = plt.subplots(6,3,figsize=(13,15),constrained_layout=True)
        for col, record in enumerate(chosen):
            track = record["selected_track"]
            if VISIT_LABEL not in track["track_id"]:
                raise ValueError("Track has incorrect visit label")
            path = (directory/record["patch"]["path"]).resolve()
            if not path.is_relative_to(directory) or path.suffix != ".npz":
                raise ValueError("Only confined saved patches are permitted")
            if path.stat().st_size != record["patch"]["bytes"] or digest(path) != record["patch"]["sha256"]:
                raise ValueError("Saved patch differs")
            sources.append({"track_id":track["track_id"],"path":str(path),"sha256":digest(path),"bytes":path.stat().st_size})
            with np.load(path,allow_pickle=False) as data:
                power = data["row_normalized_power"]
                baseline = data["fixed_flank_median_row_normalized_power"]
                offsets = data["source_channel_offsets"]
                df = float(data["df_hz"])
                scans = data["scans"].tolist()
                if (power.shape != (6,16,129) or baseline.shape != (6,16)
                        or scans != SCANS or df != scope["df_hz"]
                        or not np.array_equal(offsets,np.arange(-64,65))):
                    raise ValueError("Saved patch geometry differs")
                residual = power-baseline[:,:,None]
                if not np.isfinite(residual).all():
                    raise ValueError("Nonfinite display input")
                vmin, vmax = np.percentile(residual,[1,99])
                if not vmax > vmin:
                    raise ValueError("Degenerate display scale")
                # df is negative; reverse the spectral columns for ascending Hz.
                frequency_edges = [(offsets[-1]+0.5)*df,(offsets[0]-0.5)*df]
                for row,scan in enumerate(scans):
                    ax = axes[row,col]
                    im = ax.imshow(residual[row,:,::-1],aspect="auto",origin="lower",
                        extent=[*frequency_edges,0,16*TSAMP],vmin=vmin,vmax=vmax,
                        cmap="magma",interpolation="nearest")
                    ax.axvline(0,color="cyan",lw=.7,alpha=.8)
                    if col == 0:
                        scan_name = scan.replace("epoch", "Scan ").replace("_", " ").upper()
                        ax.set_ylabel(scan_name+"\nElapsed time in scan (s)")
                    if row == 5:
                        ax.set_xlabel("Offset from frozen track (Hz)")
                    if row == 0:
                        ax.set_title(f"{track['originating_scan']} rank {rank}\n"
                            f"{track['reference_frequency_hz']/1e6:.6f} MHz, {track['drift_hz_s']:+.3f} Hz/s")
                fig.colorbar(im,ax=axes[:,col],label="Native-row normalized power minus saved flank baseline",shrink=.65)
        fig.suptitle(VISIT_LABEL+f" {scope['batch_id']} — fixed rank {rank} tracks in six scans\n"
                     "Cyan: frozen ON-selected track; no detected-signal inference. Colors are not calibrated SNR.",fontsize=12)
        fig.savefig(destination,dpi=130)
        plt.close(fig)
    rendering = {"status":"RENDERED_COMPLETED_S2017_EXTENSION_SAVED_PROFILES_ONLY", "visit_label":VISIT_LABEL,
        "batch_id":scope["batch_id"],"new_visit":False,"q128_outputs_preserved":True,
        "code_sha256":digest(__file__),"scope_sha256":digest(scope_path),
        "scope_path":str(scope_path),"measurement_directory":str(directory),
        "execution_receipt_path":str(receipt_path),"receipt_public_freeze_commit":receipt.get("public_freeze_commit"),
        "execution_receipt_sha256":digest(receipt_path),"profiles_json_sha256":digest(profiles_path),
        "inputs":sources,"outputs":[{"path":str(p),"sha256":digest(p),"bytes":p.stat().st_size} for p in outputs],
        "profile_count":9,"scan_panels":54,"tsamp_s":TSAMP,
        "display_percentiles":[1,99],"display_scale_shared_across_six_scans_of_each_selected_track":True,
        "cyan_line_is_fixed_frozen_track_not_detected_signal":True,
        "new_measurements_or_detector_runs":0,"new_raw_HDF5_reads":0,"new_telescope_bytes":0,
        "elapsed_wall_s":time.monotonic()-started,"same_frequency_replication_of_old_Lband_cases":False}
    report_path.write_text(json.dumps(rendering,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":rendering["status"],"figures":[str(p) for p in outputs],"receipt":str(report_path)}))


if __name__ == "__main__":
    main()
