"""Validate and emit the unexecuted prospective control-panel freeze."""
import json
from pathlib import Path

from seti_repeater import control_freeze_radio as freeze

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/radio_fresh_control_freeze_20260926.json"
OUT = ROOT / "results_radio_cross_window_2026-09-26"


def main():
    config = json.loads(CONFIG.read_text())
    panel = freeze.build(config)
    result = {**panel.record(), "freeze_sha256": panel.identity,
        "evaluation_case_count": len(config["cases"]),
        "calibration_identity_count": len(config["calibration_identities"]),
        "fresh_identity_count": len(config["cases"]) + len(config["calibration_identities"]),
        "broad_width_leakage_gate_channels": [65, 129],
        "previous_failed_panel_rerun": False,
        "evaluation_executed": False,
        "telescope_values_opened": False,
        "telescope_requests": 0}
    (OUT / "control_freeze.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
