import copy
import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ls7w_freeze_gate", ROOT / "scripts" / "ls7w_freeze_gate.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def manifest():
    return json.loads((ROOT / "LS7W_NATIVE_STUDY_PREPARATION.json").read_text())


def test_current_preparation_manifest_is_consistent_but_not_ready():
    m = manifest()
    assert gate.validate(m) == []
    s = gate.status(m)
    assert s["state"] == gate.PREPARED_STATE
    assert s["target_image_pixels_opened"] is False
    assert s["mandatory_blockers_unresolved"] > 0
    assert s["ready_for_target_pixel_acquisition"] is False


def test_cannot_claim_frozen_with_unresolved_blockers():
    m = manifest()
    m["state"] = gate.FROZEN_STATE
    errors = gate.validate(m)
    assert any("unresolved blockers" in e for e in errors)


def test_target_pixels_cannot_be_opened_in_pre_acquisition_states():
    m = manifest()
    m["target_image_pixels_opened"] = True
    assert gate.validate(m)


def test_visit_and_pulse_family_are_immutable():
    m = manifest()
    a = copy.deepcopy(m)
    a["observation"]["obsid"] = 0
    assert any("OBSID changed" in e for e in gate.validate(a))
    b = copy.deepcopy(m)
    b["fixed_signal_family"]["pulse_width_seconds"] = [30, 60]
    assert any("pulse-width family changed" in e for e in gate.validate(b))


def test_external_contact_authorization_is_not_inferred():
    m = manifest()
    m["external_contact_authorized"] = True
    assert any("external-contact authorization" in e for e in gate.validate(m))
