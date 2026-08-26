#!/usr/bin/env python3
"""Prepare and verify the frozen Milestone 34 legacy cap audits."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any


CLUSTER_REPRODUCTION_FIELDS = (
    "cluster_frequency_mhz",
    "max_snr",
    "member_count",
    "distinct_template_count",
    "distinct_spectral_widths",
    "distinct_activity_subsets",
    "frequency_span_hz",
    "best_hypothesis",
    "top_members",
    "off_at_best_hypothesis_snr",
    "v0p5_off_diagnostics",
    "v0p5_receiver_frame_signature",
)

WINDOW_REPRODUCTION_FIELDS = (
    "window",
    "rest_bins",
    "on_best",
    "one_channel_regression_best",
    "off_global_best",
    "empirical_null",
    "single_epoch_rfi_excision",
    "diagnostics_for_on_best",
)

ROOT_REPRODUCTION_FIELDS = (
    "pipeline",
    "preregistration",
    "global_result",
    "search_dimensions",
    "known_answer_validation",
    "completeness",
    "interpretation_limits",
)


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def write_json(path: str | Path, value: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def target_spec(spec: dict[str, Any], milestone: int) -> dict[str, Any]:
    matches = [x for x in spec["targets"] if x["milestone"] == milestone]
    if len(matches) != 1:
        raise AssertionError(f"expected one target for milestone {milestone}")
    return matches[0]


def verify_source_hashes(entry: dict[str, Any]) -> None:
    pairs = (
        (entry["primary_config"], entry["primary_config_sha256"]),
        (
            entry["primary_search_summary"],
            entry["primary_search_summary_sha256"],
        ),
        (
            entry["primary_data_manifest"],
            entry["primary_data_manifest_sha256"],
        ),
    )
    for path, expected in pairs:
        actual = sha256(path)
        if actual != expected:
            raise AssertionError(f"SHA-256 mismatch for {path}: {actual}")
    if "posthoc_source" in entry:
        actual = sha256(entry["posthoc_source"])
        if actual != entry["posthoc_source_sha256"]:
            raise AssertionError(
                f"SHA-256 mismatch for {entry['posthoc_source']}: {actual}"
            )


def prepare(spec_path: str, milestone: int, output_path: str) -> None:
    spec = load_json(spec_path)
    entry = target_spec(spec, milestone)
    verify_source_hashes(entry)
    primary = load_json(entry["primary_config"])
    reporting = primary["search"]["candidate_reporting"]
    assert reporting["max_report_clusters"] == spec["analysis"][
        "primary_report_cap"
    ]
    audit = deepcopy(primary)
    audit["search"]["candidate_reporting"]["max_report_clusters"] = spec[
        "analysis"
    ]["audit_report_cap"]
    encoded = (json.dumps(audit, indent=2) + "\n").encode()
    actual = hashlib.sha256(encoded).hexdigest()
    assert actual == entry["expected_audit_config_sha256"]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)


def manifest_entries(path: str | Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in Path(path).read_text().splitlines():
        digest, filename = line.split(maxsplit=1)
        logical_name = "/".join(Path(filename).parts[-2:])
        if logical_name in entries:
            raise AssertionError(f"duplicate manifest entry {logical_name}")
        entries[logical_name] = digest
    return entries


def cluster_projection(cluster: dict[str, Any]) -> dict[str, Any]:
    return {field: cluster.get(field) for field in CLUSTER_REPRODUCTION_FIELDS}


def known_posthoc_map(entry: dict[str, Any]) -> dict[float, str]:
    known = {
        float(item["frequency_mhz"]): item["classification"]
        for item in entry["known_posthoc_resolutions"]
    }
    if not known:
        return known
    source = load_json(entry["posthoc_source"])
    observed = {
        float(candidate["best_hypothesis"]["frequency_mhz"]): candidate[
            "posthoc_classification"
        ]
        for candidate in source["candidates"]
    }
    assert source["candidate_count"] == len(observed) == len(known)
    assert observed == known
    return known


def match_known_posthoc(frequency_mhz: float, known: dict[float, str]) -> str | None:
    matches = [
        classification
        for frequency, classification in known.items()
        if math.isclose(frequency_mhz, frequency, rel_tol=0.0, abs_tol=1e-12)
    ]
    if len(matches) > 1:
        raise AssertionError("candidate matches multiple post-hoc records")
    return matches[0] if matches else None


def finalize(
    spec_path: str,
    milestone: int,
    audit_config_path: str,
    audit_data_manifest: str,
    audit_search_summary: str,
    output_path: str,
) -> None:
    spec = load_json(spec_path)
    entry = target_spec(spec, milestone)
    verify_source_hashes(entry)
    assert sha256(audit_config_path) == entry["expected_audit_config_sha256"]

    primary_manifest = manifest_entries(entry["primary_data_manifest"])
    audit_manifest = manifest_entries(audit_data_manifest)
    assert len(primary_manifest) == len(audit_manifest) == 30
    assert audit_manifest == primary_manifest

    primary = load_json(entry["primary_search_summary"])
    audit = load_json(audit_search_summary)
    assert audit["pipeline"]["version"] == spec["analysis"]["detector_version"]
    for field in ROOT_REPRODUCTION_FIELDS:
        assert audit[field] == primary[field]

    p_global_reduce = primary["candidate_reduction"]
    a_global_reduce = audit["candidate_reduction"]
    p_settings = deepcopy(p_global_reduce["settings"])
    a_settings = deepcopy(a_global_reduce["settings"])
    assert p_settings.pop("max_report_clusters") == spec["analysis"][
        "primary_report_cap"
    ]
    assert a_settings.pop("max_report_clusters") == spec["analysis"][
        "audit_report_cap"
    ]
    assert a_settings == p_settings
    assert a_global_reduce["hypothesis_peaks_retained"] == p_global_reduce[
        "hypothesis_peaks_retained"
    ]
    assert a_global_reduce["frequency_clusters_before_report_limit"] == (
        p_global_reduce["frequency_clusters_before_report_limit"]
    )

    threshold = audit["global_result"]["operational_threshold_snr"]
    physical_vetoes = set(spec["analysis"]["physical_veto_dispositions"])
    known_posthoc = known_posthoc_map(entry)
    per_window = []
    open_cases = []
    newly_exposed = []
    raw_above_dispositions: Counter[str] = Counter()
    final_above_dispositions: Counter[str] = Counter()
    published_annotation_changes = []
    published_disposition_changes = []
    posthoc_resolutions_applied = 0
    total_clusters = 0
    total_above = 0

    assert audit["windows"].keys() == primary["windows"].keys()
    audit_report_cap = load_json(audit_config_path)["search"]["candidate_reporting"][
        "max_report_clusters"
    ]

    for window_id, primary_window in primary["windows"].items():
        audit_window = audit["windows"][window_id]
        for field in WINDOW_REPRODUCTION_FIELDS:
            assert audit_window[field] == primary_window[field]
        p_reduce = primary_window["candidate_reduction"]
        a_reduce = audit_window["candidate_reduction"]
        assert a_reduce["hypothesis_peak_count"] == p_reduce[
            "hypothesis_peak_count"
        ]
        assert a_reduce["candidate_veto_v0p5"] == p_reduce[
            "candidate_veto_v0p5"
        ]
        assert a_reduce["cluster_count_before_report_limit"] == p_reduce[
            "cluster_count_before_report_limit"
        ]
        assert a_reduce["reported_cluster_count"] == a_reduce[
            "cluster_count_before_report_limit"
        ]
        assert a_reduce["cluster_count_before_report_limit"] < audit_report_cap
        p_clusters = p_reduce["clusters"]
        a_clusters = a_reduce["clusters"]
        assert len(p_clusters) == p_reduce["reported_cluster_count"]
        assert len(a_clusters) == a_reduce["reported_cluster_count"]
        assert len(a_clusters) >= len(p_clusters)
        for p_cluster, a_cluster in zip(p_clusters, a_clusters):
            assert cluster_projection(a_cluster) == cluster_projection(p_cluster)
            primary_flags = set(p_cluster["flags"])
            audit_flags = set(a_cluster["flags"])
            cap_dependent = set(spec["analysis"]["cap_dependent_annotations"])
            assert primary_flags - cap_dependent == audit_flags - cap_dependent
            if "receiver_frame_template_alias" in primary_flags:
                assert "receiver_frame_template_alias" in audit_flags
            primary_disposition = p_cluster["disposition"]
            audit_disposition = a_cluster["disposition"]
            if (
                primary_disposition == "below_threshold"
                or primary_disposition in physical_vetoes
            ):
                assert audit_disposition == primary_disposition
            elif primary_disposition == "rfi_family_veto_pending_manual_review":
                assert audit_disposition in {
                    primary_disposition,
                    "rfi_veto_receiver_frame_alias",
                    "survives_for_followup",
                }
            if audit_flags != primary_flags:
                published_annotation_changes.append(
                    {
                        "window_id": window_id,
                        "frequency_mhz": a_cluster["cluster_frequency_mhz"],
                        "snr": a_cluster["max_snr"],
                        "primary_flags": sorted(primary_flags),
                        "audit_flags": sorted(audit_flags),
                        "added_flags": sorted(audit_flags - primary_flags),
                        "removed_flags": sorted(primary_flags - audit_flags),
                        "primary_disposition": primary_disposition,
                        "audit_disposition": audit_disposition,
                    }
                )
            if audit_disposition != primary_disposition:
                published_disposition_changes.append(
                    {
                        "window_id": window_id,
                        "frequency_mhz": a_cluster["cluster_frequency_mhz"],
                        "snr": a_cluster["max_snr"],
                        "primary_disposition": primary_disposition,
                        "audit_disposition": audit_disposition,
                        "added_flags": sorted(audit_flags - primary_flags),
                        "removed_flags": sorted(primary_flags - audit_flags),
                    }
                )

        assert all(
            a_clusters[index]["max_snr"] >= a_clusters[index + 1]["max_snr"]
            for index in range(len(a_clusters) - 1)
        )
        above = [c for c in a_clusters if c["max_snr"] >= threshold]
        published_above = [c for c in p_clusters if c["max_snr"] >= threshold]
        extra = [
            c for c in a_clusters[len(p_clusters) :] if c["max_snr"] >= threshold
        ]
        assert len(above) == len(published_above) + len(extra)
        for cluster in extra:
            newly_exposed.append(
                {
                    "window_id": window_id,
                    "frequency_mhz": cluster["cluster_frequency_mhz"],
                    "snr": cluster["max_snr"],
                    "raw_disposition": cluster["disposition"],
                }
            )

        window_open = []
        raw_counts = Counter(c["disposition"] for c in above)
        final_counts: Counter[str] = Counter()
        for cluster in above:
            raw = cluster["disposition"]
            raw_above_dispositions[raw] += 1
            if raw in physical_vetoes:
                final = raw
            else:
                posthoc = match_known_posthoc(
                    cluster["cluster_frequency_mhz"], known_posthoc
                )
                if posthoc is not None:
                    final = f"posthoc_{posthoc}"
                    posthoc_resolutions_applied += 1
                else:
                    final = "OPEN_REQUIRES_FIXED_MORPHOLOGY_REVIEW"
                    case = {
                        "window_id": window_id,
                        "frequency_mhz": cluster["cluster_frequency_mhz"],
                        "snr": cluster["max_snr"],
                        "raw_disposition": raw,
                        "best_hypothesis": cluster["best_hypothesis"],
                    }
                    open_cases.append(case)
                    window_open.append(case)
            final_counts[final] += 1
            final_above_dispositions[final] += 1

        per_window.append(
            {
                "window_id": window_id,
                "clusters_before_primary_report_limit": p_reduce[
                    "cluster_count_before_report_limit"
                ],
                "primary_reported_clusters": p_reduce["reported_cluster_count"],
                "audit_reported_clusters": a_reduce["reported_cluster_count"],
                "primary_over_threshold_clusters_published": len(published_above),
                "audit_over_threshold_clusters": len(above),
                "newly_exposed_over_threshold_clusters": len(extra),
                "raw_over_threshold_dispositions": dict(sorted(raw_counts.items())),
                "final_over_threshold_dispositions": dict(
                    sorted(final_counts.items())
                ),
                "open_cases": window_open,
            }
        )
        total_clusters += len(a_clusters)
        total_above += len(above)

    result = {
        "purpose": "Milestone 34 legacy complete-disposition audit",
        "milestone": milestone,
        "target": entry["target"],
        "detector_version": spec["analysis"]["detector_version"],
        "primary_config_sha256": entry["primary_config_sha256"],
        "audit_config_sha256": entry["expected_audit_config_sha256"],
        "primary_search_summary_sha256": entry[
            "primary_search_summary_sha256"
        ],
        "audit_search_summary_sha256": sha256(audit_search_summary),
        "primary_data_manifest_sha256": entry["primary_data_manifest_sha256"],
        "audit_data_manifest_sha256": sha256(audit_data_manifest),
        "operational_threshold_snr": threshold,
        "primary_reproduced": True,
        "all_report_caps_unsaturated": True,
        "independent_or_reserved_cadence_spectral_values_read": False,
        "total_complete_clusters": total_clusters,
        "total_over_threshold_clusters": total_above,
        "newly_exposed_over_threshold_clusters": newly_exposed,
        "newly_exposed_over_threshold_count": len(newly_exposed),
        "raw_over_threshold_dispositions": dict(
            sorted(raw_above_dispositions.items())
        ),
        "final_over_threshold_dispositions": dict(
            sorted(final_above_dispositions.items())
        ),
        "known_posthoc_resolutions_available": len(known_posthoc),
        "known_posthoc_resolutions_applied": posthoc_resolutions_applied,
        "published_cluster_annotation_changes": published_annotation_changes,
        "published_cluster_disposition_changes": published_disposition_changes,
        "open_cases": open_cases,
        "open_case_count": len(open_cases),
        "windows": per_window,
        "next_action": (
            "legacy_report_cap_debt_closed"
            if not open_cases
            else "freeze_candidate_local_morphology_protocol"
        ),
    }
    write_json(output_path, result)
    print(json.dumps(result, indent=2, sort_keys=True))


def combine(spec_path: str, root_path: str, output_path: str) -> None:
    spec = load_json(spec_path)
    root = Path(root_path)
    records = [
        load_json(root / f"m{entry['milestone']}" / "audit_summary.json")
        for entry in spec["targets"]
    ]
    assert [r["milestone"] for r in records] == [17, 21]
    result = {
        "purpose": "Milestone 34 combined legacy complete-disposition audit",
        "detector_version": spec["analysis"]["detector_version"],
        "audited_milestones": [r["milestone"] for r in records],
        "targets": [r["target"] for r in records],
        "primary_results_reproduced": all(r["primary_reproduced"] for r in records),
        "all_report_caps_unsaturated": all(
            r["all_report_caps_unsaturated"] for r in records
        ),
        "independent_or_reserved_cadences_opened": False,
        "total_complete_clusters": sum(
            r["total_complete_clusters"] for r in records
        ),
        "total_over_threshold_clusters": sum(
            r["total_over_threshold_clusters"] for r in records
        ),
        "newly_exposed_over_threshold_count": sum(
            r["newly_exposed_over_threshold_count"] for r in records
        ),
        "known_posthoc_resolutions_applied": sum(
            r["known_posthoc_resolutions_applied"] for r in records
        ),
        "published_cluster_annotation_change_count": sum(
            len(r["published_cluster_annotation_changes"]) for r in records
        ),
        "published_cluster_annotation_changes": [
            {"milestone": r["milestone"], **change}
            for r in records
            for change in r["published_cluster_annotation_changes"]
        ],
        "published_cluster_disposition_change_count": sum(
            len(r["published_cluster_disposition_changes"]) for r in records
        ),
        "published_cluster_disposition_changes": [
            {"milestone": r["milestone"], **change}
            for r in records
            for change in r["published_cluster_disposition_changes"]
        ],
        "open_case_count": sum(r["open_case_count"] for r in records),
        "per_target": records,
        "next_action": (
            "report_closed_legacy_cap_debt"
            if not any(r["open_case_count"] for r in records)
            else "freeze_review_for_newly_exposed_open_cases"
        ),
    }
    write_json(output_path, result)
    print(json.dumps(result, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)

    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--spec", required=True)
    prepare_parser.add_argument("--milestone", type=int, required=True)
    prepare_parser.add_argument("--output", required=True)

    finalize_parser = commands.add_parser("finalize")
    finalize_parser.add_argument("--spec", required=True)
    finalize_parser.add_argument("--milestone", type=int, required=True)
    finalize_parser.add_argument("--audit-config", required=True)
    finalize_parser.add_argument("--audit-data-manifest", required=True)
    finalize_parser.add_argument("--audit-search-summary", required=True)
    finalize_parser.add_argument("--output", required=True)

    combine_parser = commands.add_parser("combine")
    combine_parser.add_argument("--spec", required=True)
    combine_parser.add_argument("--root", required=True)
    combine_parser.add_argument("--output", required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    if args.command == "prepare":
        prepare(args.spec, args.milestone, args.output)
    elif args.command == "finalize":
        finalize(
            args.spec,
            args.milestone,
            args.audit_config,
            args.audit_data_manifest,
            args.audit_search_summary,
            args.output,
        )
    else:
        combine(args.spec, args.root, args.output)


if __name__ == "__main__":
    main()
