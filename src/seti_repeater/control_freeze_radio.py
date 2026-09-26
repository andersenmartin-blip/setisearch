"""Validation for the unexecuted fresh radio recovery/RFI/null panel freeze."""
from dataclasses import dataclass, replace
import json

from .detector_m43u import digest

SCHEMA = "radio-fresh-control-panel-freeze-v1"
WIDTHS = (1, 5, 33, 65, 129)
POWERS = (100.0, 500.0)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class PanelFreeze:
    cross_window_contract_sha256: str
    config_json: str
    identity: str

    @property
    def config(self):
        return json.loads(self.config_json)

    def record(self):
        return {"schema": SCHEMA,
            "cross_window_contract_sha256": self.cross_window_contract_sha256,
            "panel_sha256": digest(self.config),
            "status": "FROZEN_NOT_EXECUTABLE",
            "scientific_evaluation_authorized": False,
            "spectral_access_authorized": False}

    def validate(self):
        cfg = self.config
        if (cfg.get("artifact_type") != SCHEMA
                or cfg.get("cross_window_contract_sha256") != self.cross_window_contract_sha256
                or cfg.get("status") != "FROZEN_NOT_EXECUTABLE"
                or cfg.get("primary") != "neighbor9"):
            raise ValueError("fresh panel header changed")
        if (cfg.get("source_domain") != "synthetic-prospective"
                or cfg.get("previous_failed_panel_role") != "closed-development-evidence-only"
                or cfg.get("previous_failed_panel_rerun") is not False):
            raise ValueError("failed development evidence boundary changed")
        if (tuple(cfg.get("detector_width_bank_channels", ())) != WIDTHS
                or tuple(cfg.get("injection_total_digital_power_bank", ())) != POWERS):
            raise ValueError("fresh panel width or amplitude bank changed")
        cases = cfg.get("cases", [])
        if len(cases) != 24 or len({item["case_id"] for item in cases}) != 24:
            raise ValueError("fresh panel requires exactly 24 unique evaluation cases")
        if len({item["seed"] for item in cases}) != 24:
            raise ValueError("fresh evaluation seeds are not disjoint")
        kinds = [item["kind"] for item in cases]
        if (kinds.count("noise_null") != 2 or kinds.count("on_signal") != 10
                or kinds.count("matched_on_off") != 10
                or kinds.count("single_adjacent_off") != 2):
            raise ValueError("fresh panel case inventory changed")
        signal_pairs = {(item["injection_width_channels"], item["total_digital_power"])
                        for item in cases if item["kind"] == "on_signal"}
        matched_pairs = {(item["injection_width_channels"], item["total_digital_power"])
                         for item in cases if item["kind"] == "matched_on_off"}
        expected = {(width, power) for width in WIDTHS for power in POWERS}
        if signal_pairs != expected or matched_pairs != expected:
            raise ValueError("signal or matched-control factorial coverage changed")
        for item in cases:
            if (not item["source_identity_namespace"].startswith("radio-fresh-eval-")
                    or item["outcomes_may_select_settings"] is not False):
                raise ValueError("fresh evaluation identity or tuning boundary changed")
        calibration = cfg.get("calibration_identities", [])
        if (len(calibration) != 3
                or len({x["seed"] for x in calibration} | {x["seed"] for x in cases}) != 27
                or len({x["source_identity_namespace"] for x in calibration}
                       | {x["source_identity_namespace"] for x in cases}) != 27):
            raise ValueError("calibration and evaluation identities are not disjoint")
        gates = cfg.get("gates", {})
        required = {
            "complete_member_cluster_partition",
            "on_signal_recovery",
            "noise_null",
            "matched_rfi",
            "single_adjacent_rfi",
            "broad_width_leakage",
        }
        if set(gates) != required:
            raise ValueError("recovery/RFI/null gate inventory changed")
        if gates["broad_width_leakage"] != {
                "detector_width_channels": [65, 129],
                "unassociated_final_members_each_width": 0,
                "unassociated_final_clusters_each_width": 0}:
            raise ValueError("broad-width leakage gate changed")
        budgets = cfg.get("attempt_budgets", {})
        if budgets != {"calibration_realizations": 3, "evaluation_cases": 24,
                       "evaluation_runs": 1, "remedy_attempts_after_freeze": 0,
                       "pilot_runs": 0}:
            raise ValueError("fresh panel attempt budget changed")
        blockers = cfg.get("execution_blockers", [])
        if set(blockers) != {"pointing_provenance_unresolved",
                "qualified_motion_bank_missing", "cross_window_transfer_unqualified",
                "codec_receipt_missing", "runtime_manifest_missing",
                "cumulative_resource_ledger_missing"}:
            raise ValueError("fresh panel blocker inventory changed")
        if (cfg.get("spectral_access_authorized") is not False
                or cfg.get("scientific_candidate_selection_authorized") is not False
                or self.config_json != canonical(cfg)
                or self.identity != digest(self.record())):
            raise ValueError("fresh panel freeze changed")


def build(config):
    contract = config["cross_window_contract_sha256"]
    if not isinstance(contract, str) or len(contract) != 64:
        raise ValueError("invalid cross-window contract identity")
    initial = PanelFreeze(contract, canonical(config), "")
    result = replace(initial, identity=digest(initial.record()))
    result.validate()
    return result
