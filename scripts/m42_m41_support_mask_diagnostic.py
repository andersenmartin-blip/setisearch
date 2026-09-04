#!/usr/bin/env python3
"""Diagnose M41 truth-local geometric support, finiteness, and recovery."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/m42_m41_support_mask_diagnostic.json"
M41_SCRIPT = ROOT / "scripts/m41_m37_high_snr_truth_local_calibration.py"
M41_ROOT = ROOT / "results_m41_m37_high_snr_truth_local_calibration"
M41_AGGREGATE = M41_ROOT / "calibration-aggregate.json"
M41_TRANSPORT = M41_ROOT / "trial-ledger.parts.json"
EXPECTED_BASE_COMMIT = "65404156df95070f98201b8d485c9d46a6ce5b09"
EXPECTED_AGGREGATE_ID = (
    "b95220e51b02636a45d0a9e322bdc879fa47bad79f03d0577eb2566382b6f8c9"
)
EXPECTED_AGGREGATE_FILE = (
    "2564733b8c93b935e090861028fe6a6b622f70e9e7066bde81e4c083c95ca43d"
)
EXPECTED_LEDGER_SHA256 = (
    "429789c591f44cb1ea87a5b340bf79a72905b44af3aa71bef964b3d002cc50fb"
)
EXPECTED_LEDGER_NBYTES = 3_318_065
EXPECTED_TRIALS = 6_144
EXPECTED_TRUTHS = 512
EXPECTED_LEVELS = 12
EXPECTED_KNOWN_SUPPORTED = 98
GROUP_FIELDS = (
    "spectral_width_channels",
    "activity_subset_index",
    "line_index",
    "radial_stratum_index",
    "phase_stratum_index",
)

SPEC = importlib.util.spec_from_file_location("m42_m41_parent", M41_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M41 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M41)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise M41.core.V0P6IncompleteError(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain one JSON object")
    return value


def validate_config(config: Mapping[str, Any]) -> None:
    require(
        config.get("artifact_type") == "m42-m41-support-mask-diagnostic-config-v1",
        "M42 config type changed",
    )
    require(config.get("analysis_base_commit") == EXPECTED_BASE_COMMIT, "base changed")
    require(config.get("status") == "frozen-before-subgroup-diagnostic", "status changed")
    inputs = config.get("inputs")
    require(isinstance(inputs, list) and len(inputs) == 5, "input inventory changed")
    paths = []
    for item in inputs:
        require(isinstance(item, Mapping), "input entry is invalid")
        path = item.get("path")
        digest = item.get("sha256")
        require(isinstance(path, str) and path not in paths, "input path changed")
        require(
            isinstance(digest, str)
            and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest),
            "input digest changed",
        )
        paths.append(path)
    expected = config.get("expected_m41")
    require(isinstance(expected, Mapping), "expected M41 boundary is missing")
    require(expected.get("aggregate_sha256") == EXPECTED_AGGREGATE_ID, "aggregate changed")
    require(expected.get("aggregate_file_sha256") == EXPECTED_AGGREGATE_FILE, "aggregate file changed")
    require(expected.get("ledger_sha256") == EXPECTED_LEDGER_SHA256, "ledger changed")
    require(expected.get("ledger_nbytes") == EXPECTED_LEDGER_NBYTES, "ledger size changed")
    require(expected.get("trial_count") == EXPECTED_TRIALS, "trial count changed")
    require(expected.get("truth_count") == EXPECTED_TRUTHS, "truth count changed")
    require(expected.get("snr_level_count") == EXPECTED_LEVELS, "level count changed")
    require(
        expected.get("known_candidate_supported_truth_count")
        == EXPECTED_KNOWN_SUPPORTED,
        "known support count changed",
    )
    diagnostic = config.get("diagnostic")
    require(isinstance(diagnostic, Mapping), "diagnostic contract is missing")
    require(diagnostic.get("group_fields") == list(GROUP_FIELDS), "group fields changed")
    require(diagnostic.get("highest_snr_cross_section") == 256.0, "cross-section changed")
    require(diagnostic.get("geometric_support_rule") == "candidate_score_cell_count > 0", "support rule changed")
    require(diagnostic.get("finite_score_rule") == "finite best_truth_local_score_snr", "finite rule changed")
    require(diagnostic.get("recovery_rule") == "immutable M41 score_recovered", "recovery rule changed")
    boundary = config.get("claim_boundary")
    require(isinstance(boundary, Mapping), "claim boundary is missing")
    for key in (
        "new_spectral_access",
        "new_injections",
        "threshold_change",
        "unsupported_truth_removal",
        "interpolation_permitted",
        "end_to_end_completeness_claimed",
        "sensitivity_transport_claimed",
        "occurrence_rate_claimed",
        "technosignature_claimed",
    ):
        require(boundary.get(key) is False, f"{key} must remain false")
    require(
        boundary.get("endpoint")
        == "retrospective-diagnostic-of-frozen-m41-pointwise-endpoint",
        "endpoint changed",
    )


def validate_inputs(repo_root: Path, config: Mapping[str, Any]) -> list[dict[str, Any]]:
    inventory = []
    for item in config["inputs"]:
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe input path")
        path = repo_root / relative
        require(path.is_file(), f"missing input: {relative}")
        observed = sha256_file(path)
        require(observed == item["sha256"], f"input hash changed: {relative}")
        inventory.append({"path": relative.as_posix(), "sha256": observed, "nbytes": path.stat().st_size})
    return inventory


def reconstruct_ledger(repo_root: Path, transport: Mapping[str, Any]) -> bytes:
    require(
        transport.get("artifact_type")
        == "m41-m37-high-snr-truth-local-ledger-transport-v1",
        "transport type changed",
    )
    require(
        transport.get("algorithm") == "concatenate-parts-in-listed-order",
        "transport algorithm changed",
    )
    require(transport.get("output_path") == "trial-ledger.jsonl.gz", "ledger path changed")
    require(transport.get("ledger_sha256") == EXPECTED_LEDGER_SHA256, "transport ledger changed")
    require(transport.get("ledger_nbytes") == EXPECTED_LEDGER_NBYTES, "transport size changed")
    require(
        transport.get("source_aggregate_sha256") == EXPECTED_AGGREGATE_ID,
        "transport aggregate changed",
    )
    parts = transport.get("parts")
    require(isinstance(parts, list) and len(parts) == 7, "transport part inventory changed")
    payloads = []
    names = []
    for item in parts:
        require(isinstance(item, Mapping), "transport part is invalid")
        relative = Path(str(item.get("path")))
        require(
            not relative.is_absolute()
            and len(relative.parts) == 1
            and relative.name not in names,
            "unsafe or duplicate transport part",
        )
        names.append(relative.name)
        path = repo_root / "results_m41_m37_high_snr_truth_local_calibration" / relative
        require(path.is_file(), f"missing ledger part: {relative}")
        require(path.stat().st_size == item.get("nbytes"), f"part size changed: {relative}")
        require(sha256_file(path) == item.get("sha256"), f"part hash changed: {relative}")
        payloads.append(path.read_bytes())
    payload = b"".join(payloads)
    require(len(payload) == EXPECTED_LEDGER_NBYTES, "reassembled ledger size changed")
    require(hashlib.sha256(payload).hexdigest() == EXPECTED_LEDGER_SHA256, "reassembled ledger hash changed")
    return payload


def load_validated_records(
    repo_root: Path, config: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    inputs = validate_inputs(repo_root, config)
    aggregate = load_json(repo_root / M41_AGGREGATE.relative_to(ROOT))
    identity = dict(aggregate)
    observed = identity.pop("aggregate_sha256", None)
    require(observed == EXPECTED_AGGREGATE_ID, "M41 aggregate identity changed")
    require(observed == M41.sha256_json(identity), "M41 aggregate self-hash changed")
    require(sha256_file(repo_root / M41_AGGREGATE.relative_to(ROOT)) == EXPECTED_AGGREGATE_FILE, "M41 aggregate file changed")
    require(aggregate.get("status") == "complete", "M41 is not complete")
    require(aggregate.get("trial_count") == EXPECTED_TRIALS, "M41 trial count changed")
    require(aggregate.get("truth_count_per_level") == EXPECTED_TRUTHS, "M41 truth count changed")
    require(aggregate.get("snr_level_count") == EXPECTED_LEVELS, "M41 level count changed")
    transport = load_json(repo_root / M41_TRANSPORT.relative_to(ROOT))
    payload = reconstruct_ledger(repo_root, transport)

    plan = M41.make_plan()
    start = M41._validate_start(repo_root / M41_ROOT.relative_to(ROOT), M41._load_config(), plan)
    records = []
    hashes = []
    canonical_bytes = 0
    with gzip.open(io.BytesIO(payload), "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            ordinal = len(records)
            require(ordinal < EXPECTED_TRIALS, "M41 ledger has extra records")
            record = json.loads(line)
            require(isinstance(record, dict), "M41 ledger record is invalid")
            M41._validate_trial_record(record, plan.trials[ordinal], ordinal, start, M41._load_config())
            records.append(record)
            hashes.append(record["record_sha256"])
            canonical_bytes += len(M41.core.canonical_json_bytes(record))
    require(len(records) == EXPECTED_TRIALS, "M41 ledger is incomplete")
    require(M41.sha256_json(hashes) == aggregate["trial_record_inventory_sha256"], "M41 record inventory changed")
    require(canonical_bytes == aggregate["trial_record_canonical_bytes"], "M41 canonical byte count changed")
    return aggregate, records, inputs


def _finite(record: Mapping[str, Any]) -> bool:
    value = record["adapter"]["best_truth_local_score_snr"]
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _fraction(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _group_table(
    truth_rows: Sequence[Mapping[str, Any]], field: str, highest_level_index: int
) -> list[dict[str, Any]]:
    values = sorted({row["truth"][field] for row in truth_rows})
    result = []
    for value in values:
        selected = [row for row in truth_rows if row["truth"][field] == value]
        supported = sum(bool(row["supported"]) for row in selected)
        highest = [row["records"][highest_level_index] for row in selected]
        finite = sum(_finite(record) for record in highest)
        recovered = sum(bool(record["score_recovered"]) for record in highest)
        result.append(
            {
                "value": value,
                "truths": len(selected),
                "candidate_supported": supported,
                "support_fraction": _fraction(supported, len(selected)),
                "snr_256_finite": finite,
                "snr_256_recovered": recovered,
            }
        )
    return result


def build_diagnostic(repo_root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    validate_config(config)
    aggregate, records, inputs = load_validated_records(repo_root, config)
    levels = aggregate["levels"]
    by_truth: list[list[dict[str, Any]]] = [[] for _ in range(EXPECTED_TRUTHS)]
    for record in records:
        by_truth[record["trial"]["truth_ordinal"]].append(record)

    truth_rows = []
    for ordinal, selected in enumerate(by_truth):
        require(len(selected) == EXPECTED_LEVELS, "truth level inventory changed")
        selected.sort(key=lambda item: item["trial"]["level_index"])
        require(
            [item["trial"]["level_index"] for item in selected]
            == list(range(EXPECTED_LEVELS)),
            "truth level order changed",
        )
        first = selected[0]
        structural = (
            first["adapter"]["candidate_score_cell_count"],
            first["adapter"]["mask_dependency_vector_cell_count"],
            first["adapter"]["plan_inventory_sha256"],
        )
        for record in selected[1:]:
            require(
                (
                    record["adapter"]["candidate_score_cell_count"],
                    record["adapter"]["mask_dependency_vector_cell_count"],
                    record["adapter"]["plan_inventory_sha256"],
                )
                == structural,
                "truth-local structural support changed across S/N",
            )
            require(record["truth"] == first["truth"], "truth changed across S/N")
        supported = structural[0] > 0
        for record in selected:
            finite = _finite(record)
            recovered = bool(record["score_recovered"])
            require(not finite or supported, "finite score lacks geometric support")
            require(not recovered or finite, "recovery lacks finite score")
        require(first["truth"]["truth_ordinal"] == ordinal, "truth order changed")
        truth_rows.append(
            {
                "truth": first["truth"],
                "candidate_score_cell_count": structural[0],
                "mask_dependency_vector_cell_count": structural[1],
                "plan_inventory_sha256": structural[2],
                "supported": supported,
                "records": selected,
            }
        )

    supported_rows = [row for row in truth_rows if row["supported"]]
    unsupported_rows = [row for row in truth_rows if not row["supported"]]
    require(len(supported_rows) == EXPECTED_KNOWN_SUPPORTED, "M41 support count changed")
    level_rows = []
    for level_index, level in enumerate(levels):
        selected = [row["records"][level_index] for row in truth_rows]
        supported = len(supported_rows)
        finite = sum(_finite(record) for record in selected)
        recovered = sum(bool(record["score_recovered"]) for record in selected)
        require(finite == level["finite_best_score_count"], "aggregate finite count changed")
        require(recovered == level["recovered"], "aggregate recovery count changed")
        level_rows.append(
            {
                "level_index": level_index,
                "ideal_single_epoch_snr": level["ideal_single_epoch_snr"],
                "truths": EXPECTED_TRUTHS,
                "candidate_supported": supported,
                "finite_post_mask": finite,
                "recovered": recovered,
                "overall_recovery_fraction": _fraction(recovered, EXPECTED_TRUTHS),
                "finite_fraction_within_support": _fraction(finite, supported),
                "recovery_fraction_within_support": _fraction(recovered, supported),
                "recovery_fraction_within_finite": _fraction(recovered, finite),
            }
        )

    distribution = []
    for cell_count in sorted({row["candidate_score_cell_count"] for row in truth_rows}):
        distribution.append(
            {
                "candidate_score_cell_count": cell_count,
                "truth_count": sum(
                    row["candidate_score_cell_count"] == cell_count
                    for row in truth_rows
                ),
            }
        )
    highest_index = next(
        index
        for index, level in enumerate(levels)
        if level["ideal_single_epoch_snr"] == 256.0
    )
    supported_ids = [row["truth"]["truth_id"] for row in supported_rows]
    unsupported_ids = [row["truth"]["truth_id"] for row in unsupported_rows]
    result: dict[str, Any] = {
        "artifact_type": "m42-m41-support-mask-diagnostic-v1",
        "status": "complete-ledger-only-diagnostic",
        "analysis_base_commit": EXPECTED_BASE_COMMIT,
        "source_m41_aggregate_sha256": EXPECTED_AGGREGATE_ID,
        "source_m41_ledger_sha256": EXPECTED_LEDGER_SHA256,
        "input_inventory": inputs,
        "trial_count": EXPECTED_TRIALS,
        "truth_count": EXPECTED_TRUTHS,
        "snr_level_count": EXPECTED_LEVELS,
        "truth_support": {
            "candidate_supported_truth_count": len(supported_rows),
            "candidate_unsupported_truth_count": len(unsupported_rows),
            "support_fraction": _fraction(len(supported_rows), EXPECTED_TRUTHS),
            "frozen_endpoint_recovery_ceiling_count": len(supported_rows),
            "frozen_endpoint_recovery_ceiling_fraction": _fraction(
                len(supported_rows), EXPECTED_TRUTHS
            ),
            "fifty_percent_recovery_structurally_reachable": len(supported_rows) >= 256,
            "supported_truth_id_inventory_sha256": M41.sha256_json(supported_ids),
            "unsupported_truth_id_inventory_sha256": M41.sha256_json(unsupported_ids),
            "candidate_score_cell_count_distribution": distribution,
            "structural_fields_invariant_across_snr": True,
        },
        "levels": level_rows,
        "highest_snr_cross_section": level_rows[highest_index],
        "group_diagnostics_at_snr_256": {
            field: _group_table(truth_rows, field, highest_index)
            for field in GROUP_FIELDS
        },
        "decision": {
            "further_snr_extension_supported": len(supported_rows) >= 256,
            "next_action": (
                "freeze-adapter-support-repair-or-endpoint-redesign-before-more-injections"
                if len(supported_rows) < 256
                else "freeze-separate-mask-score-diagnostic-before-more-injections"
            ),
            "m42_authorizes_next_action": False,
        },
        "claim_boundary": dict(config["claim_boundary"]),
    }
    result["diagnostic_sha256"] = M41.sha256_json(result)
    return result


def write_outputs(repo_root: Path, output_root: Path, config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    result = build_diagnostic(repo_root, config)
    output_root.mkdir(parents=True, exist_ok=True)
    M41.m40._publish_json(output_root / "diagnostic.json", result)
    input_lines = [
        f"{item['sha256']}  {item['path']}" for item in result["input_inventory"]
    ]
    relative_config = config_path.resolve().relative_to(repo_root.resolve()).as_posix()
    input_lines.append(f"{sha256_file(config_path)}  {relative_config}")
    M41.m40._publish_bytes(
        output_root / "INPUT_MANIFEST.sha256",
        ("\n".join(input_lines) + "\n").encode("utf-8"),
    )
    M41.m40._publish_bytes(
        output_root / "RESULTS_MANIFEST.sha256",
        f"{sha256_file(output_root / 'diagnostic.json')}  diagnostic.json\n".encode(
            "utf-8"
        ),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--config", type=Path, default=CONFIG_PATH
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "results_m42_m41_support_mask_diagnostic",
    )
    arguments = parser.parse_args()
    result = write_outputs(
        arguments.repo_root.resolve(),
        arguments.output_root.resolve(),
        arguments.config.resolve(),
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
