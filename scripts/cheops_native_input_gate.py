#!/usr/bin/env python3
"""Hard preflight gate for the prospective CHEOPS native-image LS study.

This script intentionally performs no science-image reads. It validates only
the declared physical-input contract and exits non-zero unless every required
dependency has been verified and the protocol is frozen.
"""
import argparse, hashlib, json
from pathlib import Path

REQUIRED_OPERATOR_IDS = {
    "gain_and_units",
    "stacking_and_offline_nonlinearity",
    "reference_applicability",
}
REQUIRED_REFERENCES = {
    "CH_TU2018-01-01T00-00-00_REF_APP_CCDLinearisationLUT100_V0104.fits",
    "CH_TU2020-01-29T00-00-00_REF_APP_FlatFieldTeff-PointSource_V0104.fits",
    "CH_TU2020-03-17T12-29-01_REF_APP_DarkFrame_V0201.fits",
    "CH_TU2020-03-17T12-29-01_REF_APP_BadPixelMap_V0201.fits",
}
ALLOWED_PULSES_SECONDS = [30, 60, 100]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

def fail(msg):
    raise SystemExit("NOT_READY: " + msg)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--study", required=True, type=Path)
    ap.add_argument("--reference-root", type=Path)
    args = ap.parse_args()
    contract = load(args.contract)
    study = load(args.study)

    if study.get("state") != "FROZEN":
        fail("study protocol is not frozen")
    if study.get("target_image_access_authorized") is not True:
        fail("target-image access is not explicitly enabled in the frozen protocol")
    if study.get("pulse_widths_seconds") != ALLOWED_PULSES_SECONDS:
        fail("pulse widths differ from the predeclared 30/60/100 s set")

    questions = {x["id"]: x for x in contract.get("operator_questions", [])}
    if set(questions) != REQUIRED_OPERATOR_IDS:
        fail("operator-question set changed")
    unresolved = [k for k, v in questions.items() if v.get("status") != "VERIFIED"]
    if unresolved:
        fail("unverified operators: " + ", ".join(sorted(unresolved)))

    refs = {x["filename"]: x for x in contract.get("reference_inputs", [])}
    missing_defs = REQUIRED_REFERENCES - set(refs)
    if missing_defs:
        fail("required reference definitions absent: " + ", ".join(sorted(missing_defs)))

    root = args.reference_root
    for name in sorted(REQUIRED_REFERENCES):
        rec = refs[name]
        if rec.get("contents_received") is not True:
            fail(f"reference not received: {name}")
        expected = rec.get("sha256")
        if not expected or len(expected) != 64:
            fail(f"reference SHA-256 not frozen: {name}")
        if rec.get("native_validity_start_utc") is None or rec.get("native_validity_stop_utc") is None:
            fail(f"native validity unresolved: {name}")
        if rec.get("version_relevant_selection_rule") in (None, "", "UNRESOLVED"):
            fail(f"selection/interpolation rule unresolved: {name}")
        if root is not None:
            p = root / name
            if not p.is_file():
                fail(f"reference file missing locally: {name}")
            actual = sha256(p)
            if actual != expected:
                fail(f"reference SHA-256 mismatch: {name}")

    gain = contract.get("already_available_gain", {})
    if gain.get("contents_verified") is not True:
        fail("gain reference contents are not verified")
    if gain.get("physical_convention_adopted") is not True:
        fail("gain physical convention is not adopted")
    if contract.get("science_ready") is not True:
        fail("contract science_ready is not true")
    if contract.get("message_delivery_state") == "PREPARED_UNSENT" and contract.get("new_external_input_received") is not True:
        fail("no new external calibration input has been received")
    print("READY: physical contract and frozen-study gate passed; target-image stage may start.")

if __name__ == "__main__":
    main()
