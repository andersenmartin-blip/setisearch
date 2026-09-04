#!/usr/bin/env python3
"""Render the machine-readable LS4B Stage-1 result as a concise report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render(result: dict) -> str:
    lines = [
        "# LS4B LHS 1140 X-band Stage-1 result",
        "",
        f"Status: **{result['status'].upper()}**.",
        "",
        "LS4B searched the frozen GBT X-band ABACAD cadence `--114966` over 8-12 GHz with the LS1 broadband detector core.",
        "",
        "| Scan | Role | Retained events | Truncated |",
        "|---|---|---:|---|",
    ]
    for scan in result["scans"]:
        lines.append(
            f"| {scan['label']} | {scan['role']} | {len(scan['search']['events'])} | "
            f"{'yes' if scan['search']['retention_truncated'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"ON events at the frozen threshold: **{result['on_threshold_event_count']}**.  ",
            f"Events surviving the adjacent-OFF veto: **{result['surviving_event_count']}**.",
            "",
        ]
    )
    if result["high_time_resolution_followup_preregistration_required"]:
        lines.append(
            "At least one event survived. Any HTR access requires a separately committed candidate-conditioned preregistration; Stage 1 alone is not a detection."
        )
    else:
        lines.append(
            "No HTR access is authorized by the frozen rule. This closes only this cadence and signal screen."
        )
    lines.extend(
        [
            "",
            "The 8-12 GHz interval is the closest archive test so far to the paper-motivated tens-of-GHz regime, but the approximate LHS 1140 c-b projected separation is 90.065 stellar radii. This is a frequency complement, not a close-conjunction case.",
            "",
            "All six raw filterbanks were deleted after screening and were not published. Scores are screening statistics, not calibrated significances. No technosignature, sensitivity, occurrence-rate or general light-sail claim is made.",
            "",
            f"Result identity: `{result['result_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen", type=Path, default=Path("results_ls4b/screen.json"))
    parser.add_argument("--output", type=Path, default=Path("LS4B_STAGE1_RESULT.md"))
    args = parser.parse_args()
    result = json.loads(args.screen.read_text(encoding="utf-8"))
    if result.get("artifact_type") != "seti_repeater.ls4b_medium_resolution_screen":
        raise RuntimeError("wrong LS4B result artifact")
    args.output.write_text(render(result), encoding="utf-8")


if __name__ == "__main__":
    main()
