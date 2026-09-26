#!/usr/bin/env python3
"""Describe already published LS8 cohort results; never open new science data.

Run from any checkout containing SOURCE_COMMIT. --source-root may point to an
export of that commit; every consumed byte is still checked against its Git
tree. This is a bookkeeping audit, not a rerun of the scientific analyses.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

SOURCE_COMMIT = "0432c9d42fa7c6849369fb652f1a36f121e85304"
SCREENS = "k n q s v w y aa ac af ai ak al ao aq at au av aw ax ba bc bd".split()
IMAGES = {
    1: "l", 2: "o", 3: "r", 4: "t", 6: "x", 7: "z", 8: "ab",
    9: "ad", 10: "ag", 11: "aj", 13: "am", 14: "ap", 15: "ar",
    20: "ay", 21: "bb", 23: "be",
}
RESIDUALS = {1: "m", 2: "p", 4: "u", 9: "ae", 10: "ah", 13: "an", 15: "as", 20: "az"}
LABELS = ("CORRECTION_LINKED", "SPATIALLY_STRUCTURED", "UNRESOLVED_WITHIN_FIXED_SCOPE")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("results_two_week_review_2026-09-26"))
    parser.add_argument("--plot", action="store_true", help="Also render the descriptive SVG figure with matplotlib")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    tree = {}
    listing = subprocess.check_output(["git", "ls-tree", "-r", SOURCE_COMMIT], cwd=repo, text=True)
    for line in listing.splitlines():
        meta, path = line.split("\t", 1)
        tree[path] = meta.split()[2]
    sources = {}

    def read(path):
        if args.source_root:
            data = (args.source_root / path).read_bytes()
        else:
            data = subprocess.check_output(["git", "show", f"{SOURCE_COMMIT}:{path}"], cwd=repo)
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        require(blob == tree[path], f"Source differs from pinned Git tree: {path}")
        sources[path] = {"path": path, "git_blob_sha": blob,
                         "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        return data.decode("utf-8")

    def read_json(path):
        return json.loads(read(path))

    ledger = read_json("results_ls8j_reconciliation/reconciliation.json")
    require(ledger["status"] == "PASS", "Cohort reconciliation did not pass")
    require(ledger["complete_cohort_order_equal"] is True, "Cohort order changed")
    cohorts = ledger["eligible_cohorts"]
    require(len(cohorts) == 107, "Unexpected fixed cohort count")
    rows, events, zero_window_visits = [], [], []
    seen_visits, seen_events = set(), set()
    for rank, stage in enumerate(SCREENS, 1):
        cohort = cohorts[rank - 1]
        require(cohort["rank"] == rank, "Cohort rank disagreement")
        folder = f"results_ls8{stage}_l2_" + ("recovered" if stage == "v" else "screen")
        screen = read_json(folder + "/summary.json")
        require(screen["status"] == "COMPLETE_AUDITED", f"Unaudited screen: {folder}")
        selected = [v["file_key"] for v in cohort["selected_visits"]]
        require(screen["selected_keys"] == selected, f"Wrong selected pair at rank {rank}")
        require([v["file_key"] for v in screen["visits"]] == selected, "Visit-order disagreement")
        require(not (seen_visits & set(selected)), "Duplicate visit across cohorts")
        seen_visits.update(selected)
        require(screen["candidate_claims"] == 0 and screen["detector_qualified"] is False,
                "Unexpected qualification claim in source")
        require(screen["screen_threshold"] == 8.5 and screen["durations_rows"] == [1, 2, 3],
                "Screen endpoints changed")
        totals = screen["totals"]
        count_fields = ("rows", "eligible_windows", "positive_windows", "negative_windows",
                        "positive_clusters", "negative_clusters")
        for key in count_fields:
            require(totals[key] == sum(v[key] for v in screen["visits"]),
                    f"Pair/visit count disagreement: {rank}/{key}")
        for visit in screen["visits"]:
            for key in ("eligible_windows", "positive_windows", "negative_windows"):
                require(visit[key] == sum(d[key] for d in visit["duration_results"]),
                        f"Visit/duration count disagreement: {rank}/{key}")
            if visit["eligible_windows"] == 0:
                zero_window_visits.append({"rank": rank, "target": cohort["archive_target_name"],
                                          "file_key": visit["file_key"], "rows": visit["rows"]})
        label_counts = collections.Counter()
        diagnostics = []
        if rank in IMAGES:
            image_folder = f"results_ls8{IMAGES[rank]}_images"
            image_summary = read_json(image_folder + "/summary.json")
            diagnostics = read_json(image_folder + "/diagnostics.json")
            require(image_summary["status"] == "COMPLETE_AUDITED", "Unaudited images")
            for event in diagnostics:
                require(event["file_key"] in selected, "Event belongs to another pair")
                identity = (event["file_key"], event["id"])
                require(identity not in seen_events, "Duplicate representative")
                seen_events.add(identity)
                require(event["classification"] in LABELS, "Unexpected event label")
                require(event["sign"] in ("positive", "negative"), "Unexpected sign")
                label_counts[event["classification"]] += 1
                events.append({"rank": rank, "target": cohort["archive_target_name"],
                               "file_key": event["file_key"], "event_id": event["id"],
                               "sign": event["sign"], "start_row_zero_based": event["start"],
                               "duration_rows": event["duration"],
                               "classification": event["classification"],
                               "image_report": image_folder + "/REPORT.md",
                               "bounded_followup": "LS8" + RESIDUALS[rank].upper() if rank in RESIDUALS else ""})
            require(dict(label_counts) == image_summary["outcomes"], "Image label totals disagree")
            require(len(diagnostics) == image_summary["contexts"], "Image context count disagrees")
        for sign in ("positive", "negative"):
            require(sum(e["sign"] == sign for e in diagnostics) == totals[sign + "_clusters"],
                    f"Incomplete signed image follow-up: {rank}/{sign}")
        if label_counts[LABELS[2]]:
            require(rank in RESIDUALS, "Unresolved set lacks a recorded bounded follow-up")
            followup = RESIDUALS[rank]
            residual_folder = f"results_ls8{followup}_" + ("verified" if followup == "p" else "residuals")
            read_json(residual_folder + "/summary.json")
            read(f"LS8{followup.upper()}_CONTINUATION.md")
        rows.append({"rank": rank, "target": cohort["archive_target_name"], "stage": "LS8" + stage.upper(),
                     "selected_visits": len(selected), **{key: totals[key] for key in count_fields},
                     **{label: label_counts[label] for label in LABELS}, "screen_report": folder + "/REPORT.md"})

    # Narrative sources are pinned too; no new calibration or scientific result is inferred.
    for path in ("TWO_WEEK_PLAN_2026-09-14.md", "TWO_WEEK_REPORT_2026-09-14.md", "PROJECT_STATUS.md",
                 "LS7N_CONTINUATION.md", "LS7O_CONTINUATION.md", "LS8BE_CONTINUATION.md",
                 "CHEOPS_REQUIRED_INPUTS.json", "CHEOPS_CALIBRATION_REQUEST.md"):
        read(path)
    unresolved = [e for e in events if e["classification"] == LABELS[2]]
    keys = ("selected_visits", *count_fields, *LABELS)
    totals = {key: sum(row[key] for row in rows) for key in keys}
    by_sign = {sign: dict(collections.Counter(e["classification"] for e in events if e["sign"] == sign))
               for sign in ("positive", "negative")}
    result = {
        "review_date": "2026-09-26", "source_commit": SOURCE_COMMIT,
        "scope": "First 23 pairs in the fixed 107-cohort LS8J queue; excludes earlier pilots/other targets",
        "cohorts_completed": len(rows), "cohorts_in_fixed_queue": len(cohorts),
        "totals": totals, "classifications_by_sign": by_sign,
        "zero_eligible_window_visits": zero_window_visits,
        "unresolved_event_count": len(unresolved),
        "unresolved_target_count": len({e["target"] for e in unresolved}),
        "qualified_candidate_claims": 0, "new_science_data_accessed": False,
        "qualified_observing_coverage_computed": False, "independent_trial_count_computed": False,
        "next_rank": cohorts[23]["rank"], "next_target": cohorts[23]["archive_target_name"],
        "next_pair": [v["file_key"] for v in cohorts[23]["selected_visits"]],
        "source_files_verified": len(sources),
    }
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "source_manifest.json").write_text(json.dumps({"source_commit": SOURCE_COMMIT,
        "sources": [sources[p] for p in sorted(sources)]}, indent=2) + "\n")
    for filename, records in (("cohorts.csv", rows), ("events.csv", events), ("unresolved_events.csv", unresolved)):
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
        (output / filename).write_text(buf.getvalue(), newline="")
    lines = ["# CHEOPS fixed-cohort accounting through 24 September 2026", "",
             "Derived on 26 September from sealed summaries and original image classifications.",
             "Counts are descriptive: windows overlap; labels are not physical causes; rows are not qualified coverage.", "",
             "| Rank | Target | Rows | Eligible windows | Positive / negative clusters | Correction-linked | Spatial | Unresolved |",
             "|---:|---|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['rank']} | {row['target']} | {row['rows']:,} | {row['eligible_windows']:,} | "
                     f"{row['positive_clusters']} / {row['negative_clusters']} | {row[LABELS[0]]} | {row[LABELS[1]]} | {row[LABELS[2]]} |")
    lines += ["", "## Unresolved register", "", "Every original label is retained. Each bounded follow-up is closed; the physical cause remains unassigned.", "",
              "| Target | Original event | Sign | Zero-based row | Duration in rows | Bounded follow-up |",
              "|---|---|---|---:|---:|---|"]
    for event in unresolved:
        lines.append(f"| {event['target']} | {event['event_id']} | {event['sign']} | {event['start_row_zero_based']} | {event['duration_rows']} | {event['bounded_followup']} |")
    (output / "TABLES.md").write_text("\n".join(lines) + "\n")
    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.family": "DejaVu Sans", "svg.hashsalt": "seti-review-20260926"})
        fig, ax = plt.subplots(figsize=(9.2, 4.3))
        positive = [by_sign["positive"].get(label, 0) for label in LABELS]
        negative = [by_sign["negative"].get(label, 0) for label in LABELS]
        ax.barh(range(3), positive, color="#237b94", label="Positive excursion")
        ax.barh(range(3), negative, left=positive, color="#8365a8", label="Negative excursion")
        for i, (p, n) in enumerate(zip(positive, negative)):
            ax.text(p / 2, i, str(p), ha="center", va="center", color="white", weight="bold")
            ax.text(p + n / 2, i, str(n), ha="center", va="center", color="white", weight="bold")
            ax.text(p + n + .4, i, str(p + n), va="center", color="#243746")
        ax.set_yticks(range(3), ["Correction-linked", "Spatially structured", "Unresolved"])
        ax.invert_yaxis()
        ax.set_xlim(0, 27)
        ax.set_xlabel("Signed event representatives")
        ax.set_title("CHEOPS: 49 representatives in the first 23 fixed cohorts", loc="left", pad=16, weight="bold")
        ax.legend(loc="upper center", bbox_to_anchor=(.48, -.19), ncol=2, frameon=False)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.tick_params(axis="y", length=0)
        fig.text(.02, .025, "Results through 24 Sep 2026. Descriptive labels; physical causes are not established.", fontsize=9, color="#52616b")
        fig.subplots_adjust(left=.23, right=.97, top=.82, bottom=.3)
        fig.savefig(output / "event_classifications.svg", metadata={"Date": "2026-09-26"})
        plt.close(fig)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
