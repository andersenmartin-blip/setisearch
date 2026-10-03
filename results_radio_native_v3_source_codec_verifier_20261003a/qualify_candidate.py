"""Construct a candidate engineering envelope and verify the held local run.

This driver uses independently supplied pins for the already frozen run c.
It writes only new candidate evidence/result files with exclusive creation.
"""
from pathlib import Path
import argparse
import json
import os
import source_specific_codec_evidence_v1 as verifier

SOURCE = Path("/workspace/scratch/8fcd6bf45392/setisearch-20261003-archive")
PROBE = Path("/workspace/scratch/fa2e54995e11/source-candidate/all-rows-probe-20261003c")
OUT = Path(__file__).resolve().parent
PROBE_SHA = "e98bb2735128980c2f95efe3747e8a0794d2829d45fb0efac94347b435340dca"
BEFORE_SHA = "93bfd8416e85e06b0862652bb29957c6035cd05cd23082140b98bf7f859438ab"
AFTER_SHA = "4dd4865e9c4384ada9ff91b830d9c9e34aab10ce76a9b55d212aac079ae4b531"


def pin(path):
    data = path.read_bytes()
    stat = path.stat()
    return {"path": str(path), "bytes": len(data), "sha256": verifier.sha256(data), "allocated_bytes": stat.st_blocks * 512}


def write_new(path, data):
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def prepare():
    probe_pin = pin(PROBE / "all-rows-probe.json")
    before_pin = pin(PROBE / "runtime-closure-before.json")
    after_pin = pin(PROBE / "runtime-closure-after.json")
    for actual, expected in ((probe_pin["sha256"], PROBE_SHA), (before_pin["sha256"], BEFORE_SHA), (after_pin["sha256"], AFTER_SHA)):
        if actual != expected:
            raise verifier.EvidenceError("driver's independent frozen-run pin differs")
    probe = verifier.strict_json((PROBE / "all-rows-probe.json").read_bytes())
    before = verifier.strict_json((PROBE / "runtime-closure-before.json").read_bytes())
    source = verifier.strict_json((SOURCE / "config/radio_hd189733_source_preparation_20260927.json").read_bytes())
    geometry = verifier.strict_json((SOURCE / "results_radio_hd189733_geometry_2026-09-27/window_geometry.json").read_bytes())
    evidence = {
        "schema": verifier.SCHEMA,
        "case_law_version": verifier.LAW,
        "authority": "candidate-engineering-only",
        "source_inventory_sha256": verifier.INVENTORY,
        "ordered_source_scans": source["scans"],
        "ordered_window_metadata": geometry["windows"],
        "runtime": dict(verifier.RUNTIME),
        "exact_source_filter_pipeline": verifier.SOURCE_FILTER,
        "current_encoder_filter_pipeline": verifier.ENCODER_FILTER,
        "probe": probe_pin,
        "runtime_closure_before": before_pin,
        "runtime_closure_after": after_pin,
        "code_input_pins": probe["held_metadata_and_source_pins"],
        "verifier_code_pin": pin(Path(verifier.__file__).resolve()),
        "runtime_closure_payload_sha256": verifier.sha256(verifier.canonical(before["files"])),
        "telescope_admission_authorized": False,
        "scientific_admission_authorized": False,
        "public_authentication_established": False,
        "complete_runtime_lifetime_established": False,
    }
    raw = verifier.canonical(evidence)
    trusted = verifier.TrustedPins(
        evidence_sha256=verifier.sha256(raw), probe_sha256=PROBE_SHA,
        closure_before_sha256=BEFORE_SHA, closure_after_sha256=AFTER_SHA,
        verifier_sha256=evidence["verifier_code_pin"]["sha256"],
        source_root=str(SOURCE), probe_root=str(PROBE),
        candidate_runtime_root="/workspace/scratch/8fcd6bf45392/seti-hdf5-runtime-candidate-20261003a/venv",
        base_runtime_root="/opt/codex/runtimes/codex-primary-runtime/dependencies/python")
    return evidence, raw, trusted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to(OUT):
        raise verifier.EvidenceError("qualification output must remain under candidate directory")
    output.mkdir(parents=True, exist_ok=True)
    evidence, raw, trusted = prepare()
    result = verifier.verify_candidate_evidence(raw, trusted)
    # Verification finishes before any successful qualification artifact is saved.
    write_new(output / "candidate-codec-evidence.json", raw)
    write_new(output / "candidate-codec-qualification.json", verifier.canonical(result))
    write_new(output / "candidate-verification-pins.json", verifier.canonical(trusted.__dict__))
    print(json.dumps({"status": result["status"], "runtime_file_pins": result["live_runtime_file_pins_verified"], "telescope_admission_authorized": False, "scientific_admission_authorized": False}, sort_keys=True))


if __name__ == "__main__":
    main()
