#!/usr/bin/env python3
"""Retain actual local test results and every native engineering-panel ledger."""
import gzip
from importlib import metadata
import io
import json
from pathlib import Path
import platform
import sys
import unittest
from seti_repeater import pipeline_radio as radio
from seti_repeater import source_m43h as rows
from radio_pipeline_fixture import panel, DESIGN

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"results_radio_pipeline_2026-09-26"
PINS = ["src/seti_repeater/"+s+".py" for s in (
    "pipeline_radio", "source_radio", "source_m43h", "transfer_m43g", "transfer_m43i",
    "source_v0p6", "search_v0p6", "detector_m43u", "mask_m43u", "injection_m43r",
    "receiver_m43q", "receiver_v0p6", "adjacent_v0p6", "alias_v0p6", "significance_v0p6")]
PINS += ["scripts/radio_pipeline_fixture.py", "scripts/radio_pipeline_qualification.py",
         "scripts/m43g_reference.py", "tests/test_radio_pipeline.py", str(DESIGN.relative_to(ROOT))]


def write(name, value):
    path = OUT/name
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
    path.write_bytes(gzip.compress(data, mtime=0) if name.endswith(".gz") else data)
    # Verify the delivered encoding, not just the pre-write object.
    actual = gzip.decompress(path.read_bytes()) if name.endswith(".gz") else path.read_bytes()
    if json.loads(actual) != value:
        raise ValueError("persisted report changed: "+name)


def main():
    OUT.mkdir(exist_ok=True)
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT/"tests"), "test_radio_pipeline.py")
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (OUT/"test.log").write_text(stream.getvalue())
    try:
        p = panel()
        write("context.json", p["context"].record() | {"context_sha256": p["context"].identity,
            "basis_times_mjd": p["context"].basis.times_mjd.tolist(),
            "basis_baseline": p["context"].basis.baseline.tolist(),
            "basis_orbital": p["context"].basis.orbital.tolist(),
            "labels": [l.as_record() for l in p["context"].basis.labels],
            "catalogue": p["context"].bank, "bridge": p["context"].bridge})
        write("calibration.json", p["calibration"].receipt | {"receipt_sha256": p["calibration"].receipt_sha256})
        inputs = {}
        runs = {"calibration": p["calibration_run"]} | {name: run for name, (run, _) in p["evaluation_runs"].items()}
        for name, run in runs.items():
            inputs[name] = [{"scan": label, "source_identity": src.identity,
                "raw_sha256": src.raw_sha256, "normalized_sha256": src.normalized_sha256,
                "scope": json.loads(src.scope_json)} for label, src in sorted(run.sources.items())]
        write("input_inventory.json", inputs)
        for name, report in p["reports"].items():
            write(name+".json.gz", report)
        write("outcomes.json", p["outcomes"])
        summary = [{"case": name, **{k: v for k, v in o.items() if k.endswith("count") or k == "recovered"},
                    "associated_final_members": len(o["final_associated_ids"]),
                    "unassociated_final_members": len(o["unassociated_final_ids"]),
                    "unassociated_final_clusters": len(o["unassociated_final_cluster_ids"])}
                   for name, o in p["outcomes"].items()]
    except Exception as error:
        write("failure.json", {"complete": False, "error": repr(error), "telescope_requests": 0})
        print(stream.getvalue(), end="")
        raise
    runtime = {"python": platform.python_version()}
    for package in ("numpy", "h5py", "hdf5plugin"):
        try:
            runtime[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            runtime[package] = None
    report = {"status": "LOCAL_INTEGRATION_CHECKS_PASS" if result.wasSuccessful() else "FAIL",
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "runtime": runtime,
              "primary": radio.METHOD["primary"], "method_sha256": radio.digest(radio.METHOD),
              "context_sha256": p["context"].identity, "summary": summary,
              "calibration_threshold": p["calibration"].threshold.operational_threshold_snr,
              "calibration_scrambles": len(p["calibration"].accumulator.null_maxima),
              "distinct_calibration_shift_rows": p["calibration"].receipt["distinct_shift_rows"],
              "score_oracle_cells": 6*8*len(p["context"].bank)*p["context"].grid.support_bin_count,
              "normalization_oracle_cells": 6*16*p["config"]["native_channels"],
              "receiver_oracle_queries": 8*3,
              "modelled_array_bound_bytes": p["calibration_run"].modelled_bytes,
              "modelled_array_limit_bytes": p["config"]["modelled_array_limit_bytes"],
              "distinct_synthetic_noise_cadences": 2, "evaluation_cases_reuse_one_background": True,
              "distinct_raw_scan_payloads_including_modifications": len({s["raw_sha256"] for scans in inputs.values() for s in scans}),
              "distinct_normalized_scan_payloads_including_modifications": len({s["normalized_sha256"] for scans in inputs.values() for s in scans}),
              "calibration_is_structured_engineering_fixture": True,
              "telescope_requests": 0, "telescope_spectral_values_read": False,
              "telescope_protocol_frozen": False, "detector_scientifically_qualified": False,
              "claim": "Raw-native local integration and failure-boundary checks only; no astrophysical sensitivity or false-alarm calibration.",
              "implementation_sha256": {p: rows.file_hash(ROOT/p) for p in PINS},
              "evidence_sha256": {str(p.relative_to(OUT)): rows.file_hash(p) for p in sorted(OUT.iterdir())
                                  if p.is_file() and p.name not in ("qualification.json", "failure.json")}}
    write("qualification.json", report)
    print(stream.getvalue(), end="")
    print(json.dumps({k: report[k] for k in ("status", "tests_run", "failures", "errors", "summary")}, indent=2))
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    main()
