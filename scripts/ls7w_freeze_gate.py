#!/usr/bin/env python3
"""Validate the LS7W prospective CHEOPS native-image freeze gate.

This tool does not read science-image data.  It checks only the machine-readable
preparation manifest and exits successfully only when the manifest is internally
consistent.  Readiness for target-image evaluation additionally requires every
mandatory blocking field to be resolved explicitly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PREPARED_STATE = "PREPARED_NOT_FROZEN_TARGET_PIXELS_CLOSED"
FROZEN_STATE = "FROZEN_READY_FOR_BOUNDED_TARGET_PIXEL_ACQUISITION"

MANDATORY_BLOCKERS = (
    "gcoadd_operator_source",
    "gain_operator_source",
    "lut100_sha256",
    "flat_sha256",
    "dark_sha256",
    "dark_native_validity",
    "dark_drp_selection_rule",
    "badmap_sha256",
    "badmap_native_validity",
    "badmap_drp_selection_rule",
    "psf_input",
    "uncertainty_propagation",
    "saturation_policy",
    "pulse_phase_grid",
    "amplitude_grid",
    "protected_guard_region_seconds",
    "final_signal_recovery_requirements",
    "final_false_acceptance_requirements",
    "final_availability_requirements",
)

EXPECTED_PULSE_WIDTHS = [30, 60, 100]
EXPECTED_FILE_KEY = "CH_PR300024_TG000301_V0300"
EXPECTED_OBSID = 1015522


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def validate(manifest: dict) -> list[str]:
    errors: list[str] = []
    if manifest.get("document_type") != "prospective_native_image_study_preparation":
        errors.append("unexpected document_type")
    if manifest.get("observation", {}).get("file_key") != EXPECTED_FILE_KEY:
        errors.append("observation file_key changed")
    if manifest.get("observation", {}).get("obsid") != EXPECTED_OBSID:
        errors.append("observation OBSID changed")
    if manifest.get("fixed_signal_family", {}).get("pulse_width_seconds") != EXPECTED_PULSE_WIDTHS:
        errors.append("fixed pulse-width family changed")
    if manifest.get("no_retuning_after_evaluation") is not True:
        errors.append("no-retuning invariant is not true")
    if manifest.get("external_contact_authorized") is not False:
        errors.append("manifest must not infer external-contact authorization")
    blockers = manifest.get("blocking_fields")
    if not isinstance(blockers, dict):
        errors.append("blocking_fields missing or not an object")
        blockers = {}
    missing_keys = [k for k in MANDATORY_BLOCKERS if k not in blockers]
    if missing_keys:
        errors.append("mandatory blocker keys missing: " + ", ".join(missing_keys))

    state = manifest.get("state")
    opened = manifest.get("target_image_pixels_opened")
    unresolved = [k for k in MANDATORY_BLOCKERS if blockers.get(k) in (None, "", [], {})]

    if state == PREPARED_STATE:
        if opened is not False:
            errors.append("prepared state requires target_image_pixels_opened=false")
    elif state == FROZEN_STATE:
        if opened is not False:
            errors.append("frozen pre-acquisition state requires target_image_pixels_opened=false")
        if unresolved:
            errors.append("frozen state still has unresolved blockers: " + ", ".join(unresolved))
    else:
        errors.append(f"unrecognized state: {state!r}")
    return errors


def status(manifest: dict) -> dict:
    blockers = manifest.get("blocking_fields", {})
    unresolved = [k for k in MANDATORY_BLOCKERS if blockers.get(k) in (None, "", [], {})]
    return {
        "state": manifest.get("state"),
        "target_image_pixels_opened": manifest.get("target_image_pixels_opened"),
        "mandatory_blockers_total": len(MANDATORY_BLOCKERS),
        "mandatory_blockers_unresolved": len(unresolved),
        "unresolved": unresolved,
        "ready_for_target_pixel_acquisition": (
            manifest.get("state") == FROZEN_STATE
            and manifest.get("target_image_pixels_opened") is False
            and not unresolved
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=Path("LS7W_NATIVE_STUDY_PREPARATION.json"),
    )
    args = ap.parse_args()
    manifest = load_manifest(args.manifest)
    errors = validate(manifest)
    report = status(manifest)
    report["validation_errors"] = errors
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
