#!/usr/bin/env python3
"""Run the unchanged frozen detector on the 100 frozen main exposures.

This driver was prepared before the main spectra were opened. Invoking it
performs the main analysis; preparing or importing this file does not.
Use a new --output directory for each repeat. All input hashes and metadata
checks are validated for the whole cohort before the first science-array read.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time
import traceback


EVENT_FIELDS = [
    "canonical_target", "dp_id", "input_sha256", "start_index",
    "end_index_exclusive", "peak_index", "run_pixels", "status",
    "wave_start_angstrom", "wave_end_angstrom", "wave_peak_angstrom",
    "peak_flux_adu", "continuum_adu", "local_std_adu", "peak_local_contrast",
    "observed_fwhm_angstrom", "observed_fwhm_pixels",
]
EXPOSURE_FIELDS = [
    "canonical_target", "dp_id", "status", "input_sha256", "input_path",
    "mjd_obs", "exptime_seconds", "total_samples", "searched_samples",
    "sum_searched_bin_widths_angstrom", "all_threshold_run_count",
    "preliminary_hit_count", "short_run_count", "wide_run_count",
    "cpu_seconds", "wall_seconds", "result_path", "threshold_runs_path",
    "error_type", "error",
]
TARGET_FIELDS = [
    "canonical_target", "selected_exposures", "completed_exposures",
    "failed_exposures", "selected_exposure_seconds", "completed_exposure_seconds",
    "searched_samples", "sum_searched_bin_widths_angstrom",
    "all_threshold_run_count", "preliminary_hit_count", "short_run_count",
    "wide_run_count", "cpu_seconds", "wall_seconds",
]


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_csv(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(path, root):
    # A copied project uses these paths without retaining the original workspace.
    return str(Path(path).resolve().relative_to(root.resolve()))


def validate_inputs(root):
    paths = {
        "selection": root / "selection/MAIN100.csv",
        "selection_record": root / "selection/SELECTION.json",
        "download_manifest": root / "acquisition/DOWNLOAD_MANIFEST.json",
        "acquisition_scope": root / "acquisition/ACQUISITION_SCOPE.json",
        "detector_freeze": root / "code/DETECTOR_FREEZE.json",
        "detector": root / "code/harps_detector.py",
        "config": root / "code/DETECTOR_CONFIG.json",
        "runner": Path(__file__).resolve(),
    }
    hashes = {name: {"path": relative(path, root), "sha256": sha256(path)}
              for name, path in paths.items()}
    scope = json.loads(paths["acquisition_scope"].read_text())
    freeze = json.loads(paths["detector_freeze"].read_text())
    selection_record = json.loads(paths["selection_record"].read_text())
    config = json.loads(paths["config"].read_text())
    rows = list(csv.DictReader(paths["selection"].open()))
    manifest = json.loads(paths["download_manifest"].read_text())
    require(hashes["selection"]["sha256"] == scope["input_selection_hashes"]["selection/MAIN100.csv"],
            "Frozen selection CSV hash mismatch")
    require(hashes["detector"]["sha256"] == freeze["source_hashes"]["harps_detector.py"],
            "Detector code differs from the detector freeze")
    require(hashes["config"]["sha256"] == freeze["source_hashes"]["DETECTOR_CONFIG.json"],
            "Detector config hash differs from the detector freeze")
    require(config == freeze["config"], "Detector config values differ from the freeze")
    require(len(rows) == 100, "Exactly 100 selected main exposures required")
    require(all(row["role"] == "main_unopened" for row in rows), "Non-main selection row")
    require(len({row["dp_id"] for row in rows}) == 100, "Duplicate selected dp_id")
    counts = Counter(row["canonical_target"] for row in rows)
    require(len(counts) == 20 and set(counts.values()) == {5}, "Require 20 targets with five exposures each")
    require(set(counts) == set(selection_record["main_targets"]), "Selection target list mismatch")
    require(selection_record["main_exposures"] == 100, "Selection record size mismatch")
    require(len({entry["dp_id"] for entry in manifest}) == len(manifest), "Duplicate manifest dp_id")
    main_manifest = {entry["dp_id"]: entry for entry in manifest if entry["role"] == "main_unopened"}
    require(set(main_manifest) == {row["dp_id"] for row in rows}, "Main manifest and selection differ")
    checked = []
    for row in rows:
        receipt = main_manifest[row["dp_id"]]
        require(receipt["download_status"] == "DOWNLOADED", "Download status: " + row["dp_id"])
        require(receipt["header_status"] == "PASS_METADATA_ONLY", "Header status: " + row["dp_id"])
        require(bool(receipt.get("checks")) and all(value is True for value in receipt["checks"].values()),
                "Metadata check failed: " + row["dp_id"])
        require(receipt["canonical_target"] == row["canonical_target"], "Manifest target mismatch")
        require(not receipt.get("upstream_raw_matches"), "Upstream raw overlap: " + row["dp_id"])
        # Prefer portable project-local data, then the manifest path only if it
        # resolves to the same project data/main directory.
        path = root / "data/main" / Path(receipt["path"]).name
        if not path.is_file():
            candidate = Path(receipt["path"])
            path = candidate if candidate.is_absolute() else root / candidate
        require(path.resolve().parent == (root / "data/main").resolve(), "Main path outside data/main")
        require(path.is_file(), "Missing main FITS: " + str(path))
        require(path.stat().st_size == receipt["bytes"], "FITS size mismatch: " + row["dp_id"])
        actual_hash = sha256(path)
        require(actual_hash == receipt["sha256"], "FITS hash mismatch: " + row["dp_id"])
        checked.append({"row": row, "path": path, "sha256": actual_hash,
                        "raw_progenitor_ids": receipt["raw_progenitor_ids"]})
    versions = {"python": sys.version, "python_major_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
                "python_implementation": platform.python_implementation(),
                **{name: importlib.metadata.version(name) for name in ("numpy", "scipy", "astropy")}}
    # Preserve both full Python build strings for audit; compiler/patch build
    # equality is informative, while Python 3.12 and exact scientific package
    # versions are the required pre-run compatibility checks.
    version_matches = {name: versions.get(name) == expected for name, expected in freeze["versions"].items()}
    version_matches["python_major_minor"] = versions["python_major_minor"] == "3.12"
    required_matches = ["python_major_minor", "numpy", "scipy", "astropy"]
    require(all(version_matches[name] for name in required_matches),
            "Runtime fails the frozen compatibility policy: " + json.dumps(version_matches))
    return checked, config, hashes, versions, freeze, version_matches


def aggregate(exposures):
    grouped = defaultdict(list)
    for entry in exposures:
        grouped[entry["canonical_target"]].append(entry)
    output = []
    sums = ["searched_samples", "sum_searched_bin_widths_angstrom", "all_threshold_run_count",
            "preliminary_hit_count", "short_run_count", "wide_run_count", "cpu_seconds", "wall_seconds"]
    for target in sorted(grouped):
        all_rows = grouped[target]
        completed = [row for row in all_rows if row["status"] == "COMPLETED"]
        record = dict(canonical_target=target, selected_exposures=len(all_rows),
                      completed_exposures=len(completed), failed_exposures=len(all_rows)-len(completed),
                      selected_exposure_seconds=sum(row["exptime_seconds"] for row in all_rows),
                      completed_exposure_seconds=sum(row["exptime_seconds"] for row in completed))
        record.update({field: sum(row.get(field, 0) for row in completed) for field in sums})
        output.append(record)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("production"),
                        help="New or empty output directory; relative paths resolve under the project root")
    args = parser.parse_args()
    root = args.project_root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    output = output.resolve()
    require(not output.exists() or not any(output.iterdir()), "Output must be new or empty; choose another --output")
    output.mkdir(parents=True, exist_ok=True)
    started = utcnow()
    initial_cpu, initial_wall = time.process_time(), time.monotonic()
    try:
        checked, config, hashes, versions, freeze, version_matches = validate_inputs(root)
    except Exception as error:
        write_json(output / "RUN_FAILURE.json", {"status": "INPUT_VALIDATION_FAILED", "created_utc": utcnow(),
                   "error_type": type(error).__name__, "error": str(error), "main_science_arrays_opened": 0})
        raise
    write_json(output / "RUN_INPUTS.json", {
        "status": "ALL_INPUTS_VALIDATED_BEFORE_SCIENCE_ARRAY_READ", "started_utc": started,
        "input_hashes": hashes, "versions": versions, "frozen_versions": freeze["versions"],
        "version_matches": version_matches,
        "version_policy": {"required_python_major_minor": "3.12", "exact_package_versions": ["numpy", "scipy", "astropy"],
                           "python_full_string_match_required": False},
        "config": config, "selected_main_exposures": len(checked),
        "inputs": [{"dp_id": item["row"]["dp_id"], "canonical_target": item["row"]["canonical_target"],
                    "path": relative(item["path"], root), "sha256": item["sha256"],
                    "raw_progenitor_ids": item["raw_progenitor_ids"]} for item in checked],
        "command_template": "python code/run_main.py --output production_repeat",
        "interpretation": "Emission threshold runs are not identified lasers. Trial totals and local contrast do not supply a calibrated false-alarm probability.",
    })
    # Import only after the detector's source hash and the complete inputs pass.
    sys.path.insert(0, str(root / "code"))
    import harps_detector
    require(Path(harps_detector.__file__).resolve() == (root / "code/harps_detector.py").resolve(),
            "Imported detector from an unexpected location")
    spectra_dir = output / "spectra"
    spectra_dir.mkdir()
    exposures = []
    all_events = []
    for item in checked:
        row, path = item["row"], item["path"]
        target, dp_id = row["canonical_target"], row["dp_id"]
        token = dp_id.replace(":", "_")
        result_path = spectra_dir / (token + ".json")
        events_path = spectra_dir / (token + "_all_threshold_runs.csv")
        exposure = {"canonical_target": target, "dp_id": dp_id, "input_sha256": item["sha256"],
                    "input_path": relative(path, root), "mjd_obs": float(row["t_min"]),
                    "exptime_seconds": float(row["t_exptime"]),
                    "result_path": str(result_path.relative_to(output)),
                    "threshold_runs_path": str(events_path.relative_to(output))}
        cpu_start, wall_start = time.process_time(), time.monotonic()
        try:
            wave, flux, metadata = harps_detector.read_spectrum(path)
            require(metadata["sha256"] == item["sha256"], "FITS changed between validation and detector read")
            result, arrays = harps_detector.analyze_arrays(wave, flux, config)
            del arrays, wave, flux
            result.update(input=metadata, canonical_target=target, dp_id=dp_id,
                          input_path=relative(path, root), run_status="COMPLETED",
                          cpu_seconds=time.process_time()-cpu_start, wall_seconds=time.monotonic()-wall_start)
            events = [{"canonical_target": target, "dp_id": dp_id, "input_sha256": item["sha256"], **event}
                      for event in result["all_threshold_runs"]]
            write_csv(events_path, EVENT_FIELDS, events)
            write_json(result_path, result)
            all_events.extend(events)
            exposure.update(status="COMPLETED", all_threshold_run_count=len(events),
                            **{key: result[key] for key in ["total_samples", "searched_samples",
                                "sum_searched_bin_widths_angstrom", "preliminary_hit_count", "short_run_count",
                                "wide_run_count", "cpu_seconds", "wall_seconds"]})
        except Exception as error:
            exposure.update(status="FAILED", cpu_seconds=time.process_time()-cpu_start,
                            wall_seconds=time.monotonic()-wall_start, error_type=type(error).__name__, error=str(error))
            write_json(result_path, {**exposure, "traceback": traceback.format_exc()})
            write_csv(events_path, EVENT_FIELDS, [])
        exposures.append(exposure)
        write_csv(output / "EXPOSURE_SUMMARY.csv", EXPOSURE_FIELDS, exposures)
        print(json.dumps({key: exposure.get(key) for key in ("canonical_target", "dp_id", "status", "preliminary_hit_count", "searched_samples")}), flush=True)
    write_csv(output / "ALL_THRESHOLD_RUNS.csv", EVENT_FIELDS, all_events)
    write_csv(output / "PRELIMINARY_HITS.csv", EVENT_FIELDS,
              [event for event in all_events if event["status"] == "PRELIMINARY_EMISSION_HIT"])
    targets = aggregate(exposures)
    write_csv(output / "TARGET_SUMMARY.csv", TARGET_FIELDS, targets)
    statuses = dict(Counter(row["status"] for row in exposures))
    completed = [row for row in exposures if row["status"] == "COMPLETED"]
    write_json(output / "RUN_SUMMARY.json", {
        "status": "COMPLETED" if len(completed) == 100 else "COMPLETED_WITH_FAILURES",
        "started_utc": started, "finished_utc": utcnow(), "exposure_status_counts": statuses,
        "selected_targets": len(targets), "selected_exposures": len(exposures),
        "searched_samples": sum(row["searched_samples"] for row in completed),
        "sum_searched_bin_widths_angstrom": sum(row["sum_searched_bin_widths_angstrom"] for row in completed),
        "threshold_run_status_counts": dict(Counter(row["status"] for row in all_events)),
        "cpu_seconds": time.process_time()-initial_cpu, "wall_seconds": time.monotonic()-initial_wall,
        "detector_cpu_seconds": sum(row["cpu_seconds"] for row in exposures),
        "output_hashes": {str(path.relative_to(output)): sha256(path) for path in sorted(output.rglob("*")) if path.is_file()},
        "interpretation": "All threshold runs retained, including short and wide runs. Per-spectrum JSON preserves exact searched intervals. No candidate-origin classification or calibrated significance is implied.",
    })
    return 0 if len(completed) == 100 else 1


if __name__ == "__main__":
    raise SystemExit(main())
