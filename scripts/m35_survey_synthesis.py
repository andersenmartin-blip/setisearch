#!/usr/bin/env python3
"""Reproduce the frozen Milestone 35 1412 MHz survey synthesis."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy


EXPECTED_RESULT_FILES = (
    "analysis_summary.json",
    "occurrence_bounds.csv",
    "target_accounting.csv",
    "score_recovery_bounds.png",
    "run_metadata.json",
    "INPUT_MANIFEST.sha256",
)
EXPECTED_ANALYSIS_BASE_COMMIT = "521b2936214da296cd07a3dd1aeb89a609500119"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_close(actual: float, expected: float, message: str) -> None:
    require(
        math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12),
        f"{message}: got {actual!r}, expected {expected!r}",
    )


def binomial_upper_tail(n: int, probability: float, observed: int) -> float:
    """Return P(Binomial(n, probability) >= observed)."""

    if observed <= 0:
        return 1.0
    if observed > n:
        return 0.0
    return math.fsum(
        math.comb(n, successes)
        * probability**successes
        * (1.0 - probability) ** (n - successes)
        for successes in range(observed, n + 1)
    )


def mattner_tasto_lower_bound(
    recovered: int, trials: int, alpha: float
) -> float:
    """One-sided lower bound for an inhomogeneous Bernoulli mean.

    This implements the high-confidence branch of Mattner and Tasto (2015),
    Theorem 1.2: zero for no successes, alpha / n for one success, and the
    ordinary lower Clopper--Pearson endpoint for two or more successes.
    """

    require(0 <= recovered <= trials, "invalid recovery count")
    require(0.0 < alpha < 1.0, "alpha must lie strictly between zero and one")
    if recovered == 0:
        return 0.0
    if recovered == 1:
        return alpha / trials

    lower = 0.0
    upper = 1.0
    for _ in range(120):
        midpoint = (lower + upper) / 2.0
        if binomial_upper_tail(trials, midpoint, recovered) < alpha:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def poisson_binomial_cdf(probabilities: list[float], maximum: int) -> float:
    """Return the inclusive exact lower tail P(T <= maximum)."""

    require(maximum >= 0, "the observed upper count must be non-negative")
    distribution = [1.0] + [0.0] * len(probabilities)
    populated = 0
    for probability in probabilities:
        require(0.0 <= probability <= 1.0, "invalid Bernoulli probability")
        for count in range(populated + 1, 0, -1):
            distribution[count] = (
                distribution[count] * (1.0 - probability)
                + distribution[count - 1] * probability
            )
        distribution[0] *= 1.0 - probability
        populated += 1
    return math.fsum(distribution[: maximum + 1])


def invert_poisson_binomial_tail(
    efficiencies: list[float], maximum: int, alpha: float
) -> dict[str, float | bool | None]:
    """Invert the inclusive Poisson-binomial lower tail over 0 <= f <= 1."""

    tail_at_one = poisson_binomial_cdf(efficiencies, maximum)
    if tail_at_one > alpha:
        return {
            "nontrivial": False,
            "upper_fraction": None,
            "trivial_upper_fraction": 1.0,
            "tail_probability_at_f_equals_1": tail_at_one,
        }

    lower = 0.0
    upper = 1.0
    for _ in range(120):
        midpoint = (lower + upper) / 2.0
        probabilities = [midpoint * efficiency for efficiency in efficiencies]
        if poisson_binomial_cdf(probabilities, maximum) > alpha:
            lower = midpoint
        else:
            upper = midpoint
    result = (lower + upper) / 2.0
    return {
        "nontrivial": True,
        "upper_fraction": result,
        "trivial_upper_fraction": 1.0,
        "tail_probability_at_f_equals_1": tail_at_one,
    }


def validate_completeness(
    completeness: dict[str, Any],
    search: dict[str, Any],
    milestone: int,
    analysis: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    embedded = dict(completeness)
    trials = embedded.pop("trials")
    require(
        search["completeness"] == embedded,
        f"M{milestone}: embedded completeness differs from standalone record",
    )
    require(
        completeness["active_epochs_zero_based"]
        == analysis["active_epochs_zero_based"],
        f"M{milestone}: active injection epochs changed",
    )
    require(
        completeness["truth_template_indices"]
        == analysis["truth_template_indices"],
        f"M{milestone}: truth-template mixture changed",
    )
    require(
        completeness["stack_statistic"] == "minimum_epoch",
        f"M{milestone}: unexpected stack statistic",
    )
    require(
        completeness["single_epoch_rfi_mask_applied"] is True,
        f"M{milestone}: injection RFI-mask setting changed",
    )
    expected_method = (
        f"Real m{milestone}_1412p5 planet-frame noise vectors are independently "
        "circularly shifted by epoch; signals use time-averaged sinc-squared "
        "leakage and model acceleration within each integration."
    )
    require(
        completeness["method"] == expected_method,
        f"M{milestone}: completeness background method changed",
    )
    require_close(
        float(completeness["detection_threshold_snr"]),
        float(search["global_result"]["operational_threshold_snr"]),
        f"M{milestone}: completeness threshold mismatch",
    )

    expected_widths = [1, 3, 5, 9, 17, 33] if milestone >= 31 else [1, 3, 5, 9]
    require(
        completeness["spectral_widths_channels"] == expected_widths,
        f"M{milestone}: unexpected completeness width bank",
    )
    require(
        search["search_dimensions"]["spectral_width_templates"]
        == expected_widths,
        f"M{milestone}: search/completeness width-bank mismatch",
    )

    expected_levels = analysis["ideal_single_epoch_snr_levels"]
    levels = completeness["levels"]
    require(
        [int(level["ideal_single_epoch_snr"]) for level in levels]
        == expected_levels,
        f"M{milestone}: unexpected injection S/N grid",
    )
    expected_trials = analysis["trials_per_target_level"]
    require(
        len(trials) == expected_trials * len(expected_levels),
        f"M{milestone}: unexpected total injection count",
    )

    trials_by_level: dict[int, list[dict[str, Any]]] = defaultdict(list)
    frequency_center = analysis["calibration_signal_distribution"][
        "truth_frequency_center_mhz"
    ]
    maximum_frequency_offset = analysis["calibration_signal_distribution"][
        "truth_frequency_validation_maximum_offset_mhz"
    ]
    for trial in trials:
        level = int(trial["ideal_single_epoch_snr"])
        require(level in expected_levels, f"M{milestone}: undeclared trial S/N")
        require(
            type(trial["multi_channel_recovered"]) is bool,
            f"M{milestone}: multichannel recovery is not Boolean",
        )
        require(
            type(trial["one_channel_recovered"]) is bool,
            f"M{milestone}: one-channel recovery is not Boolean",
        )
        require(
            trial["selected_width_channels"] in expected_widths,
            f"M{milestone}: trial selected an undeclared width",
        )
        require(
            abs(trial["truth_frequency_mhz"] - frequency_center)
            <= maximum_frequency_offset,
            f"M{milestone}: truth frequency is outside the frozen generator envelope",
        )
        require(
            len(trial["noise_shifts_bins"]) == 3
            and all(type(shift) is int for shift in trial["noise_shifts_bins"]),
            f"M{milestone}: epoch noise-shift record changed",
        )
        require(
            [entry["epoch_zero_based"] for entry in trial["epoch_diagnostics"]]
            == analysis["active_epochs_zero_based"],
            f"M{milestone}: trial epoch diagnostics changed",
        )
        trials_by_level[level].append(trial)

    for trial_index in range(expected_trials):
        repeated_model = sorted(
            (
                trial
                for trial in trials
                if trial["trial_index"] == trial_index
            ),
            key=lambda trial: trial["ideal_single_epoch_snr"],
        )
        require(
            len(repeated_model) == len(expected_levels),
            f"M{milestone}: trial model is not repeated over all S/N levels",
        )
        require(
            len({trial["truth_frequency_mhz"] for trial in repeated_model}) == 1
            and len({trial["template_index"] for trial in repeated_model}) == 1,
            f"M{milestone}: truth model changed between S/N levels",
        )

    validated: dict[int, dict[str, Any]] = {}
    for level_record in levels:
        level = int(level_record["ideal_single_epoch_snr"])
        level_trials = sorted(
            trials_by_level[level], key=lambda trial: trial["trial_index"]
        )
        require(
            len(level_trials) == expected_trials,
            f"M{milestone} S/N {level}: trial count mismatch",
        )
        require(
            [trial["trial_index"] for trial in level_trials]
            == list(range(expected_trials)),
            f"M{milestone} S/N {level}: trial indices are not 0..31",
        )
        require(
            level_record["trials"] == expected_trials,
            f"M{milestone} S/N {level}: level trial count changed",
        )

        template_counts = Counter(
            trial["template_index"] for trial in level_trials
        )
        require(
            template_counts
            == Counter(
                {
                    template: expected_trials
                    // len(analysis["truth_template_indices"])
                    for template in analysis["truth_template_indices"]
                }
            ),
            f"M{milestone} S/N {level}: truth-template balance changed",
        )
        multi_recovered = sum(
            trial["multi_channel_recovered"] for trial in level_trials
        )
        one_recovered = sum(
            trial["one_channel_recovered"] for trial in level_trials
        )
        require(
            multi_recovered == level_record["multi_channel_recovered"],
            f"M{milestone} S/N {level}: multichannel count mismatch",
        )
        require(
            one_recovered == level_record["one_channel_recovered"],
            f"M{milestone} S/N {level}: one-channel count mismatch",
        )
        require_close(
            float(level_record["multi_channel_recovery_fraction"]),
            multi_recovered / expected_trials,
            f"M{milestone} S/N {level}: multichannel fraction mismatch",
        )
        require_close(
            float(level_record["one_channel_recovery_fraction"]),
            one_recovered / expected_trials,
            f"M{milestone} S/N {level}: one-channel fraction mismatch",
        )
        observed_selected_width_counts = Counter(
            str(trial["selected_width_channels"]) for trial in level_trials
        )
        selected_width_counts = {
            str(width): observed_selected_width_counts[str(width)]
            for width in expected_widths
        }
        require(
            dict(selected_width_counts) == level_record["selected_width_counts"],
            f"M{milestone} S/N {level}: selected-width counts mismatch",
        )

        by_template = {
            record["template_index"]: record
            for record in level_record["by_truth_template"]
        }
        require(
            set(by_template) == set(analysis["truth_template_indices"]),
            f"M{milestone} S/N {level}: template summary changed",
        )
        for template, template_record in by_template.items():
            template_trials = [
                trial
                for trial in level_trials
                if trial["template_index"] == template
            ]
            template_recovered = sum(
                trial["multi_channel_recovered"] for trial in template_trials
            )
            require(
                template_record["trials"] == len(template_trials) == 8,
                f"M{milestone} S/N {level}: template trial count mismatch",
            )
            require_close(
                float(template_record["multi_channel_recovery_fraction"]),
                template_recovered / len(template_trials),
                f"M{milestone} S/N {level}: template fraction mismatch",
            )

        validated[level] = {
            "trials": expected_trials,
            "multi_channel_recovered": multi_recovered,
            "multi_channel_recovery_fraction": multi_recovered / expected_trials,
        }
    return validated


def validate_target(
    repo_root: Path,
    target: dict[str, Any],
    analysis: dict[str, Any],
    input_records: list[tuple[str, str]],
) -> dict[str, Any]:
    milestone = int(target["milestone"])
    search_path = repo_root / target["search_summary"]
    completeness_path = repo_root / target["completeness"]
    for path, expected_hash, label in (
        (search_path, target["search_summary_sha256"], "search summary"),
        (completeness_path, target["completeness_sha256"], "completeness"),
    ):
        require(path.is_file(), f"M{milestone}: missing {label}: {path}")
        actual_hash = sha256(path)
        require(
            actual_hash == expected_hash,
            f"M{milestone}: {label} SHA-256 mismatch",
        )
        input_records.append((expected_hash, str(path.relative_to(repo_root))))

    search = load_json(search_path)
    completeness = load_json(completeness_path)
    require(
        search["pipeline"]["version"] == analysis["detector_version"],
        f"M{milestone}: detector version changed",
    )
    require(
        search["pipeline"]["python"] == "3.12.14",
        f"M{milestone}: detector Python version changed",
    )
    require(
        search["pipeline"]["numpy"] == "2.5.2",
        f"M{milestone}: detector NumPy version changed",
    )
    completeness_by_level = validate_completeness(
        completeness, search, milestone, analysis
    )

    window_id = f"m{milestone}_1412p5"
    require(window_id in search["windows"], f"M{milestone}: missing 1412 window")
    window = search["windows"][window_id]
    window_metadata = window["window"]
    band = analysis["background_band"]
    require(window_metadata["id"] == window_id, f"M{milestone}: window ID mismatch")
    require_close(
        float(window_metadata["rest_center_mhz"]),
        float(band["rest_center_mhz"]),
        f"M{milestone}: rest center changed",
    )
    require_close(
        float(window_metadata["rest_half_width_khz"]),
        float(band["rest_half_width_khz"]),
        f"M{milestone}: rest half-width changed",
    )
    require(
        window_metadata["fmin_mhz"] <= band["rest_min_mhz"]
        and window_metadata["fmax_mhz"] >= band["rest_max_mhz"],
        f"M{milestone}: extraction guard does not contain the frozen band",
    )

    reduction = window["candidate_reduction"]
    clusters = reduction["clusters"]
    require(
        reduction["cluster_count_before_report_limit"]
        == reduction["reported_cluster_count"]
        == len(clusters),
        f"M{milestone}: 1412 cluster list is not fully retained",
    )
    for cluster in clusters:
        require(
            band["rest_min_mhz"]
            <= cluster["cluster_frequency_mhz"]
            <= band["rest_max_mhz"],
            f"M{milestone}: cluster outside the matched rest-frequency band",
        )

    threshold = float(search["global_result"]["operational_threshold_snr"])
    above_threshold = [
        cluster for cluster in clusters if cluster["max_snr"] >= threshold
    ]
    below_threshold = [
        cluster for cluster in clusters if cluster["max_snr"] < threshold
    ]
    require(
        all(cluster["disposition"] == "below_threshold" for cluster in below_threshold),
        f"M{milestone}: sub-threshold disposition mismatch",
    )
    require(
        all(cluster["disposition"] != "below_threshold" for cluster in above_threshold),
        f"M{milestone}: above-threshold disposition mismatch",
    )
    physical = set(analysis["physical_veto_dispositions"])
    physically_vetoed = [
        cluster
        for cluster in above_threshold
        if cluster["disposition"] in physical
    ]
    candidate_clusters = [
        cluster
        for cluster in above_threshold
        if cluster["disposition"] not in physical
    ]

    return {
        "milestone": milestone,
        "preregistration_name": search["preregistration"]["name"],
        "search_summary": target["search_summary"],
        "completeness": target["completeness"],
        "threshold_snr": threshold,
        "spectral_widths_channels": completeness["spectral_widths_channels"],
        "complete_1412_cluster_count": len(clusters),
        "above_threshold_1412_cluster_count": len(above_threshold),
        "physically_vetoed_1412_cluster_count": len(physically_vetoed),
        "candidate_positive": bool(candidate_clusters),
        "candidate_clusters": [
            {
                "frequency_mhz": cluster["cluster_frequency_mhz"],
                "max_snr": cluster["max_snr"],
                "disposition": cluster["disposition"],
            }
            for cluster in candidate_clusters
        ],
        "completeness_by_snr": completeness_by_level,
    }


def validate_m16_evidence(
    repo_root: Path,
    evidence: dict[str, Any],
    target_records: dict[int, dict[str, Any]],
    input_records: list[tuple[str, str]],
) -> dict[str, Any]:
    for path_key, hash_key in (
        ("investigation", "investigation_sha256"),
        ("followup", "followup_sha256"),
    ):
        path = repo_root / evidence[path_key]
        require(path.is_file(), f"missing M16 {path_key} evidence")
        require(sha256(path) == evidence[hash_key], f"M16 {path_key} hash mismatch")
        input_records.append((evidence[hash_key], evidence[path_key]))

    frequency = float(evidence["frequency_mhz"])
    primary_candidates = target_records[16]["candidate_clusters"]
    require(len(primary_candidates) == 1, "M16 matched band must have one candidate")
    primary = primary_candidates[0]
    require_close(primary["frequency_mhz"], frequency, "M16 primary frequency mismatch")
    require(
        primary["disposition"] == evidence["primary_disposition"],
        "M16 primary disposition mismatch",
    )

    investigation = load_json(repo_root / evidence["investigation"])
    investigation_matches = [
        candidate
        for candidate in investigation["candidates"]
        if math.isclose(
            candidate["best_hypothesis"]["frequency_mhz"],
            frequency,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ]
    require(len(investigation_matches) == 1, "M16 investigation match is not unique")
    investigation_match = investigation_matches[0]
    require(
        investigation_match["frozen_original_disposition"]
        == evidence["primary_disposition"],
        "M16 investigation changed the frozen disposition",
    )
    require(
        investigation_match["posthoc_classification"]
        == evidence["investigation_classification"],
        "M16 investigation classification mismatch",
    )

    followup = load_json(repo_root / evidence["followup"])
    followup_matches = [
        candidate
        for candidate in followup["candidates"]
        if math.isclose(
            candidate["best_hypothesis"]["frequency_mhz"],
            frequency,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ]
    require(len(followup_matches) == 1, "M16 follow-up match is not unique")
    followup_match = followup_matches[0]
    require(
        followup_match["original_posthoc_classification"]
        == evidence["investigation_classification"],
        "M16 follow-up changed the investigation classification",
    )
    require(
        followup_match["followup_classification"]
        == evidence["followup_classification"],
        "M16 follow-up classification mismatch",
    )
    require(
        evidence["count_as_candidate_positive_despite_nonredetection"] is True,
        "M16 must remain candidate-positive for the primary-cadence synthesis",
    )
    return {
        "milestone": 16,
        "frequency_mhz": frequency,
        "primary_disposition": primary["disposition"],
        "investigation_classification": investigation_match[
            "posthoc_classification"
        ],
        "followup_classification": followup_match["followup_classification"],
        "synthesis_treatment": "candidate_positive_system",
        "reason": (
            "Independent-cadence non-redetection is not a calibrated physical "
            "veto of the primary event."
        ),
    }


def cohort_accounting(
    cohort: dict[str, Any], target_records: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    milestones = cohort["milestones"]
    records = [target_records[milestone] for milestone in milestones]
    candidate_milestones = [
        record["milestone"] for record in records if record["candidate_positive"]
    ]
    result = {
        "id": cohort["id"],
        "role": cohort["role"],
        "milestones": milestones,
        "system_count": len(records),
        "complete_1412_cluster_count": sum(
            record["complete_1412_cluster_count"] for record in records
        ),
        "above_threshold_1412_cluster_count": sum(
            record["above_threshold_1412_cluster_count"] for record in records
        ),
        "physically_vetoed_1412_cluster_count": sum(
            record["physically_vetoed_1412_cluster_count"] for record in records
        ),
        "candidate_positive_milestones": candidate_milestones,
        "candidate_positive_system_count_used_as_upper_bound_on_true_detections": (
            cohort[
                "candidate_positive_system_count_used_as_upper_bound_on_true_detections"
            ]
        ),
    }
    for field in (
        "complete_1412_cluster_count",
        "above_threshold_1412_cluster_count",
        "physically_vetoed_1412_cluster_count",
    ):
        require(
            result[field] == cohort[f"expected_{field}"],
            f"{cohort['id']}: frozen {field} did not reproduce",
        )
    require(
        candidate_milestones == cohort["candidate_positive_milestones"],
        f"{cohort['id']}: candidate-positive systems changed",
    )
    require(
        len(candidate_milestones)
        == cohort[
            "candidate_positive_system_count_used_as_upper_bound_on_true_detections"
        ],
        f"{cohort['id']}: candidate upper count changed",
    )
    return result


def calculate_bounds(
    cohort: dict[str, Any],
    accounting: dict[str, Any],
    target_records: dict[int, dict[str, Any]],
    analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    records = [target_records[milestone] for milestone in cohort["milestones"]]
    system_count = len(records)
    maximum = accounting[
        "candidate_positive_system_count_used_as_upper_bound_on_true_detections"
    ]
    calibration_alpha = float(analysis["finite_calibration_alpha"])
    per_target_alpha = calibration_alpha / system_count
    survey_alpha = float(analysis["finite_survey_tail_alpha"])
    nominal_alpha = float(analysis["point_estimate_tail_alpha"])
    results = []
    for level in analysis["ideal_single_epoch_snr_levels"]:
        observed_efficiencies = [
            record["completeness_by_snr"][level][
                "multi_channel_recovery_fraction"
            ]
            for record in records
        ]
        lower_efficiencies = [
            mattner_tasto_lower_bound(
                record["completeness_by_snr"][level]["multi_channel_recovered"],
                record["completeness_by_snr"][level]["trials"],
                per_target_alpha,
            )
            for record in records
        ]
        nominal = invert_poisson_binomial_tail(
            observed_efficiencies, maximum, nominal_alpha
        )
        finite = invert_poisson_binomial_tail(
            lower_efficiencies, maximum, survey_alpha
        )
        results.append(
            {
                "cohort_id": cohort["id"],
                "cohort_role": cohort["role"],
                "system_count": system_count,
                "candidate_positive_system_upper_count": maximum,
                "ideal_single_epoch_snr": level,
                "observed_effective_target_exposure": math.fsum(
                    observed_efficiencies
                ),
                "nominal_plugin_tail_alpha": nominal_alpha,
                "nominal_plugin_status": (
                    "nontrivial_bound"
                    if nominal["nontrivial"]
                    else "no_nontrivial_bound"
                ),
                "nominal_plugin_nontrivial": nominal["nontrivial"],
                "nominal_plugin_upper_fraction": nominal["upper_fraction"],
                "nominal_plugin_trivial_upper_fraction": nominal[
                    "trivial_upper_fraction"
                ],
                "nominal_plugin_tail_probability_at_f_equals_1": nominal[
                    "tail_probability_at_f_equals_1"
                ],
                "finite_calibration_familywise_alpha": calibration_alpha,
                "finite_calibration_per_target_alpha": per_target_alpha,
                "finite_calibration_lower_effective_target_exposure": math.fsum(
                    lower_efficiencies
                ),
                "finite_survey_tail_alpha": survey_alpha,
                "finite_pointwise_95_status": (
                    "nontrivial_bound"
                    if finite["nontrivial"]
                    else "no_nontrivial_bound"
                ),
                "finite_pointwise_95_nontrivial": finite["nontrivial"],
                "finite_pointwise_95_upper_fraction": finite["upper_fraction"],
                "finite_pointwise_95_trivial_upper_fraction": finite[
                    "trivial_upper_fraction"
                ],
                "finite_pointwise_tail_probability_at_f_equals_1": finite[
                    "tail_probability_at_f_equals_1"
                ],
            }
        )
    return results


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def format_csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return format(value, ".12f")
    return value


def write_occurrence_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_csv_value(value) for key, value in row.items()})


def write_target_csv(
    path: Path,
    target_records: dict[int, dict[str, Any]],
    cohorts: list[dict[str, Any]],
    levels: list[int],
) -> None:
    cohort_membership = {
        milestone: ";".join(
            cohort["id"]
            for cohort in cohorts
            if milestone in cohort["milestones"]
        )
        for milestone in target_records
    }
    fields = [
        "milestone",
        "preregistration_name",
        "cohort_membership",
        "search_summary",
        "completeness",
        "threshold_snr",
        "spectral_widths_channels",
        "complete_1412_cluster_count",
        "above_threshold_1412_cluster_count",
        "physically_vetoed_1412_cluster_count",
        "candidate_positive",
        "candidate_frequencies_mhz",
    ]
    for level in levels:
        fields.extend(
            [
                f"snr_{level}_recovered",
                f"snr_{level}_trials",
                f"snr_{level}_recovery_fraction",
            ]
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for milestone, record in sorted(target_records.items()):
            row: dict[str, Any] = {
                "milestone": milestone,
                "preregistration_name": record["preregistration_name"],
                "cohort_membership": cohort_membership[milestone],
                "search_summary": record["search_summary"],
                "completeness": record["completeness"],
                "threshold_snr": record["threshold_snr"],
                "spectral_widths_channels": ";".join(
                    str(width) for width in record["spectral_widths_channels"]
                ),
                "complete_1412_cluster_count": record[
                    "complete_1412_cluster_count"
                ],
                "above_threshold_1412_cluster_count": record[
                    "above_threshold_1412_cluster_count"
                ],
                "physically_vetoed_1412_cluster_count": record[
                    "physically_vetoed_1412_cluster_count"
                ],
                "candidate_positive": record["candidate_positive"],
                "candidate_frequencies_mhz": ";".join(
                    format(candidate["frequency_mhz"], ".12f")
                    for candidate in record["candidate_clusters"]
                ),
            }
            for level in levels:
                completeness = record["completeness_by_snr"][level]
                row[f"snr_{level}_recovered"] = completeness[
                    "multi_channel_recovered"
                ]
                row[f"snr_{level}_trials"] = completeness["trials"]
                row[f"snr_{level}_recovery_fraction"] = completeness[
                    "multi_channel_recovery_fraction"
                ]
            writer.writerow(
                {key: format_csv_value(value) for key, value in row.items()}
            )


def write_chart(path: Path, primary_rows: list[dict[str, Any]]) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    nontrivial = [
        row
        for row in primary_rows
        if row["nominal_plugin_nontrivial"]
        and row["finite_pointwise_95_nontrivial"]
    ]
    x_values = [row["ideal_single_epoch_snr"] for row in nontrivial]
    nominal = [row["nominal_plugin_upper_fraction"] for row in nontrivial]
    finite = [row["finite_pointwise_95_upper_fraction"] for row in nontrivial]

    fig, axis = plt.subplots(figsize=(8.4, 4.9))
    fig.subplots_adjust(left=0.11, right=0.98, top=0.88, bottom=0.22)
    axis.plot(
        x_values,
        nominal,
        color="#2563a6",
        marker="o",
        linewidth=2.2,
        markersize=5.5,
        label="Nominal plug-in (calibration fixed)",
    )
    axis.plot(
        x_values,
        finite,
        color="#c76818",
        marker="s",
        linewidth=2.2,
        markersize=5.2,
        label="Finite-injection 95% upper bound",
    )
    maximum = max(float(value) for value in finite)
    y_max = min(1.0, maximum * 1.18)
    axis.set_ylim(0.0, y_max)
    axis.set_xlim(7.0, 41.0)
    axis.set_xticks([row["ideal_single_epoch_snr"] for row in primary_rows])
    axis.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    axis.set_xlabel("Exact ideal single-epoch S/N benchmark")
    axis.set_ylabel("Conditional occurrence-fraction upper bound")
    axis.set_title("M14–M33 conditional 1412 MHz score-recovery bounds", loc="left")
    axis.grid(axis="y", color="#d9dee5", linewidth=0.8)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, loc="upper right")
    axis.annotate(
        "S/N 8: no non-trivial bound",
        xy=(8, y_max * 0.88),
        xytext=(9.4, y_max * 0.88),
        va="center",
        fontsize=9,
        color="#4b5563",
        arrowprops={"arrowstyle": "-", "color": "#8b95a1", "lw": 1.0},
    )
    fig.text(
        0.11,
        0.035,
        "Pointwise; K=1. Conditional on randomized background and downstream survival.",
        fontsize=8.5,
        color="#4b5563",
    )
    fig.savefig(
        path,
        dpi=180,
        metadata={"Software": "setisearch Milestone 35"},
    )
    plt.close(fig)
    return matplotlib.__version__


def write_manifest(path: Path, records: list[tuple[str, str]]) -> None:
    path.write_text(
        "".join(f"{digest}  {filename}\n" for digest, filename in records),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        default="config/m35_survey_synthesis.json",
        type=Path,
    )
    parser.add_argument(
        "--output-dir",
        default="results_m35_survey_synthesis",
        type=Path,
    )
    args = parser.parse_args()

    spec_path = args.spec.resolve()
    repo_root = spec_path.parent.parent
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    allowed_existing = set(EXPECTED_RESULT_FILES) | {"RESULTS_MANIFEST.sha256"}
    unexpected_existing = {
        path.name for path in output_dir.iterdir() if path.name not in allowed_existing
    }
    require(
        not unexpected_existing,
        f"output directory contains unexpected files: {sorted(unexpected_existing)}",
    )

    spec = load_json(spec_path)
    analysis = spec["analysis"]
    require(
        spec["analysis_base_commit"] == EXPECTED_ANALYSIS_BASE_COMMIT,
        "analysis base commit changed",
    )
    require(analysis["retrospective_not_blind"] is True, "status must be retrospective")
    require(
        analysis["raw_spectral_arrays_read"] is False,
        "synthesis must not read raw spectral arrays",
    )
    require(
        analysis["completeness_endpoint"] == "multi_channel_recovered",
        "only multichannel recovery is permitted",
    )
    require(
        analysis["pointwise_over_snr_not_simultaneous"] is True,
        "S/N inference must remain pointwise",
    )
    require(
        analysis["primary_and_secondary_not_jointly_simultaneous"] is True,
        "cohort results must not be presented as jointly simultaneous",
    )
    require(
        analysis["no_interpolation_between_snr_levels"] is True,
        "S/N interpolation must remain disabled",
    )
    require(analysis["no_poisson_approximation"] is True, "exact tail required")
    require_close(
        analysis["finite_calibration_alpha"]
        + analysis["finite_survey_tail_alpha"],
        0.05,
        "finite-injection error allocation",
    )
    require_close(
        analysis["point_estimate_tail_alpha"],
        0.05,
        "nominal plug-in tail alpha",
    )
    require_close(
        analysis["finite_calibration_alpha"],
        0.025,
        "finite-injection calibration alpha",
    )
    require_close(
        analysis["finite_survey_tail_alpha"],
        0.025,
        "finite-injection survey-tail alpha",
    )

    input_records: list[tuple[str, str]] = []
    target_records = {
        int(target["milestone"]): validate_target(
            repo_root, target, analysis, input_records
        )
        for target in spec["targets"]
    }
    require(
        sorted(target_records) == list(range(14, 34)),
        "primary administrative target sequence must be M14--M33",
    )
    require(
        len(input_records) == 40 and len({path for _, path in input_records}) == 40,
        "expected 40 unique target input records",
    )
    m16_evidence = validate_m16_evidence(
        repo_root,
        spec["candidate_positive_evidence"],
        target_records,
        input_records,
    )
    require(
        len(input_records) == 42 and len({path for _, path in input_records}) == 42,
        "expected 42 unique frozen input records",
    )
    require(
        spec["candidate_positive_evidence"]["milestone"] == 16,
        "candidate-positive evidence must remain M16",
    )

    accounting_records = [
        cohort_accounting(cohort, target_records) for cohort in spec["cohorts"]
    ]
    require(
        spec["cohorts"][0]["milestones"] == list(range(14, 34)),
        "primary cohort must be exactly M14--M33",
    )
    require(
        spec["cohorts"][1]["milestones"] == list(range(23, 34)),
        "secondary cohort must be exactly M23--M33",
    )
    require(
        [cohort["id"] for cohort in spec["cohorts"]]
        == ["all_heldout_v0p5_m14_m33", "fully_retained_m23_m33"],
        "cohort IDs or ordering changed",
    )
    require(
        [record["role"] for record in accounting_records]
        == ["primary", "secondary_complete-retention_check"],
        "expected one primary and one secondary cohort",
    )
    bounds_by_cohort: dict[str, list[dict[str, Any]]] = {}
    all_bound_rows: list[dict[str, Any]] = []
    for cohort, accounting in zip(spec["cohorts"], accounting_records):
        rows = calculate_bounds(
            cohort, accounting, target_records, analysis
        )
        bounds_by_cohort[cohort["id"]] = rows
        all_bound_rows.extend(rows)

    primary_id = spec["cohorts"][0]["id"]
    primary_rows = bounds_by_cohort[primary_id]
    primary_snr_40 = next(
        row for row in primary_rows if row["ideal_single_epoch_snr"] == 40
    )
    unconditional_limit = {
        "upper_fraction": 1.0,
        "status": "trivial_only_without_both_mandatory_assumptions",
        "reason": (
            "Score recovery does not measure survival through clustering, report "
            "retention, physical vetoes, or adjudication, and its average over "
            "randomized backgrounds is not a fixed-frequency lower efficiency; "
            "without both mandatory assumptions the documented efficiency lower "
            "bound is zero."
        ),
    }
    summary = {
        "analysis_label": "M35_RETROSPECTIVE_1412_MHZ_SCORE_RECOVERY_SYNTHESIS",
        "analysis_base_commit": spec["analysis_base_commit"],
        "status": "retrospective_not_blind",
        "raw_spectral_arrays_read": False,
        "scope": {
            "rest_frequency_interval_mhz": [
                analysis["background_band"]["rest_min_mhz"],
                analysis["background_band"]["rest_max_mhz"],
            ],
            "exact_ideal_single_epoch_snr_levels": analysis[
                "ideal_single_epoch_snr_levels"
            ],
            "no_interpolation": True,
            "pointwise_not_simultaneous_over_snr": True,
            "completeness_endpoint": analysis["completeness_endpoint"],
            "parameter": (
                "f(S): archive-cohort system occurrence fraction for the frozen "
                "injected signal class at exact ideal S/N benchmark S, conditional "
                "on the randomized truth-frequency/background distribution"
            ),
            "occurrence_model": analysis["occurrence_model"],
            "calibration_signal_distribution": analysis[
                "calibration_signal_distribution"
            ],
        },
        "input_validation": {
            "frozen_sha256_records_verified": len(input_records),
            "target_count": len(target_records),
            "detector_version": analysis["detector_version"],
            "trials_per_target_level": analysis["trials_per_target_level"],
            "trial_endpoint_used": "multi_channel_recovered",
            "one_channel_endpoint_used": False,
            "all_1412_cluster_lists_fully_retained": True,
        },
        "candidate_accounting": accounting_records,
        "m16_candidate_evidence": m16_evidence,
        "method": {
            "nominal_plugin": (
                "Exact inclusive Poisson-binomial lower-tail inversion at alpha=0.05 "
                "using observed target recovery fractions."
            ),
            "finite_injection_pointwise_95": (
                "Mattner--Tasto Theorem 1.2 target lower bounds with Bonferroni "
                "familywise calibration alpha=0.025, followed by an exact "
                "Poisson-binomial survey-tail inversion at alpha=0.025."
            ),
            "finite_calibration_reference": analysis[
                "finite_calibration_reference"
            ],
            "poisson_approximation_used": False,
        },
        "bounds_by_cohort": bounds_by_cohort,
        "headline_primary_exact_snr_40": {
            "candidate_positive_system_upper_count": primary_snr_40[
                "candidate_positive_system_upper_count"
            ],
            "observed_effective_target_exposure": primary_snr_40[
                "observed_effective_target_exposure"
            ],
            "nominal_plugin_upper_fraction": primary_snr_40[
                "nominal_plugin_upper_fraction"
            ],
            "finite_pointwise_95_upper_fraction": primary_snr_40[
                "finite_pointwise_95_upper_fraction"
            ],
            "interpretation": (
                "conditional_randomized_background_score_recovery_only"
            ),
        },
        "mandatory_endpoint_assumption": analysis[
            "candidate_endpoint_assumption"
        ],
        "mandatory_calibration_distribution_assumption": analysis[
            "calibration_distribution_assumption"
        ],
        "unconditional_end_to_end_result": unconditional_limit,
        "interpretation_limits": [
            analysis["interpretation"],
            "No five-window bound: injections were calibrated only on mXX_1412p5.",
            "No fixed-frequency guarantee: recovery averages the frozen randomized background distribution.",
            "No greater-than-S/N claim: only the seven exact benchmark amplitudes are evaluated.",
            "The finite-injection bounds are pointwise, not simultaneous over S/N.",
            "Primary and secondary bounds are not a joint simultaneous confidence statement.",
            "Ideal S/N is not a common flux or EIRP threshold across targets.",
            "The injected activity pattern is scans 1 and 3 with four equally represented truth templates.",
            "Target independence and injection-trial independence are model assumptions.",
            "The archive/rank-selected cohort is not a random exoplanet population sample.",
        ],
        "rejected_primary_analyses": spec["rejected_primary_analyses"],
    }

    write_json(output_dir / "analysis_summary.json", summary)
    write_occurrence_csv(output_dir / "occurrence_bounds.csv", all_bound_rows)
    write_target_csv(
        output_dir / "target_accounting.csv",
        target_records,
        spec["cohorts"],
        analysis["ideal_single_epoch_snr_levels"],
    )
    matplotlib_version = write_chart(
        output_dir / "score_recovery_bounds.png", primary_rows
    )
    plan_path = repo_root / "MILESTONE_35_SURVEY_SYNTHESIS_PLAN.md"
    workflow_path = repo_root / ".github/workflows/m35_survey_synthesis.yml"
    require(plan_path.is_file(), "missing frozen M35 analysis plan")
    require(workflow_path.is_file(), "missing M35 execution workflow")
    write_json(
        output_dir / "run_metadata.json",
        {
            "analysis_base_commit": spec["analysis_base_commit"],
            "implementation": "scripts/m35_survey_synthesis.py",
            "implementation_sha256": sha256(
                repo_root / "scripts/m35_survey_synthesis.py"
            ),
            "matplotlib": matplotlib_version,
            "numpy": numpy.__version__,
            "plan": str(plan_path.relative_to(repo_root)),
            "plan_sha256": sha256(plan_path),
            "protocol": str(spec_path.relative_to(repo_root)),
            "protocol_sha256": sha256(spec_path),
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "workflow": str(workflow_path.relative_to(repo_root)),
            "workflow_sha256": sha256(workflow_path),
        },
    )
    write_manifest(output_dir / "INPUT_MANIFEST.sha256", input_records)

    result_records = [
        (sha256(output_dir / filename), filename)
        for filename in EXPECTED_RESULT_FILES
    ]
    write_manifest(output_dir / "RESULTS_MANIFEST.sha256", result_records)
    actual_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    require(
        actual_files == allowed_existing,
        f"unexpected result-file set: {sorted(actual_files)}",
    )

    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "primary_candidate_positive_systems": 1,
                "primary_snr_40_nominal_plugin_upper_fraction": primary_snr_40[
                    "nominal_plugin_upper_fraction"
                ],
                "primary_snr_40_finite_pointwise_95_upper_fraction": primary_snr_40[
                    "finite_pointwise_95_upper_fraction"
                ],
                "unconditional_end_to_end_upper_fraction": 1.0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (KeyError, TypeError, ValueError) as error:
        print(f"M35 validation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
