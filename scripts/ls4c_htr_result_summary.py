#!/usr/bin/env python3
"""Render the machine-readable LS4C HTR result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render(result: dict) -> str:
    lines = [
        "# LS4C LHS 1140 X-band HTR result",
        "",
        f"Status: **{result['status'].upper()}**.",
        "",
        "LS4C tested the exact seven LS4B survivors in the high-time-resolution A1 product against adjacent OFF scan B1.",
        "",
        "| Candidate | Stage-1 band (MHz) | ON envelope | OFF envelope | Supported subsecond scales | Disposition |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in result["candidates"]:
        event = item["stage1_event"]
        comparison = item["comparison"]
        lines.append(
            f"| `{item['candidate_id']}` | {event['frequency_start_mhz']:.3f}-{event['frequency_stop_mhz']:.3f} | "
            f"{item['on_metrics']['envelope_mean_screening_score']:.3f} | "
            f"{item['off_metrics']['envelope_mean_screening_score']:.3f} | "
            f"{comparison['supported_subsecond_scale_count']} | {comparison['disposition']} |"
        )
    lines.extend(
        [
            "",
            f"HTR diffraction-supported candidates: **{result['diffraction_supported_candidate_count']} / {result['candidate_count']}**.",
            "",
        ]
    )
    if result["diffraction_supported_candidate_count"]:
        lines.append(
            "At least one candidate passes the frozen HTR morphology rule. Independent observation is mandatory; this is not a detection or an artificial-origin claim."
        )
    else:
        lines.append(
            "No candidate passes the frozen HTR morphology rule. This rejects these seven archive events only, not light sails in general."
        )
    lines.extend(
        [
            "",
            "All seven medium-resolution survivors were co-temporal in A1 across separated frequency bands. That pattern remains suspicious context and is not a retroactive veto.",
            "",
            "The two raw 9.435 GB HTR filterbanks and all collapsed time series were deleted and not published. Scores are uncalibrated screening statistics.",
            "",
            f"Result identity: `{result['result_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--followup", type=Path, default=Path("results_ls4c_htr/followup.json")
    )
    parser.add_argument("--output", type=Path, default=Path("LS4C_HTR_RESULT.md"))
    args = parser.parse_args()
    result = json.loads(args.followup.read_text(encoding="utf-8"))
    if result.get("artifact_type") != "seti_repeater.ls4c_htr_followup":
        raise RuntimeError("wrong LS4C result artifact")
    args.output.write_text(render(result), encoding="utf-8")


if __name__ == "__main__":
    main()
