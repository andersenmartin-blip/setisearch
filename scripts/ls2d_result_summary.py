#!/usr/bin/env python3
"""Render the machine-readable LS2D Stage-1 result as a concise report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render(result: dict) -> str:
    lines = [
        "# LS2D HD 260655 Stage-1 result",
        "",
        f"Status: **{result['status'].upper()}**.",
        "",
        "LS2D searched the frozen GBT L-band ABACAD cadence `--64524` with the unchanged LS1 broadband detector.",
        "",
        "| Scan | Role | Retained events | Truncated |",
        "|---|---|---:|---|",
    ]
    for scan in result["scans"]:
        lines.append(
            f"| {scan['label']} | {scan['role']} | "
            f"{len(scan['search']['events'])} | "
            f"{'yes' if scan['search']['retention_truncated'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"ON events at the frozen threshold: **{result['on_threshold_event_count']}**. ",
            f"Events surviving the adjacent-OFF veto: **{result['surviving_event_count']}**.",
            "",
        ]
    )
    if result["high_time_resolution_followup_authorized"]:
        lines.append(
            "The frozen rule authorizes a separately committed, candidate-conditioned HTR follow-up. Stage 1 alone is not a detection."
        )
    else:
        lines.append(
            "No HTR follow-up is authorized by the frozen rule. This closes only this cadence and signal screen."
        )
    lines.extend(
        [
            "",
            "The nominal projected planet-pair separation was 32.5777 stellar radii, about 5.21 times the LS1 selected value. The observation is therefore not a close-conjunction test.",
            "",
            "Scores are screening statistics, not calibrated significances. No technosignature, sensitivity, occurrence-rate or general light-sail claim is made.",
            "",
            f"Result identity: `{result['result_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--screen", type=Path, default=Path("results_ls2d/screen.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("LS2D_STAGE1_RESULT.md")
    )
    args = parser.parse_args()
    result = json.loads(args.screen.read_text(encoding="utf-8"))
    if result.get("artifact_type") != "seti_repeater.ls2d_medium_resolution_screen":
        raise RuntimeError("wrong LS2D result artifact")
    args.output.write_text(render(result), encoding="utf-8")


if __name__ == "__main__":
    main()
