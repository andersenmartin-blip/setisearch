#!/usr/bin/env python3
"""Independent actual-header and BERV-selection audit; saved text only.

Astropy decodes extracted primary FITS cards; production parser/classifier is
never imported. This script performs no requests and opens no spectral arrays.
"""
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

import astropy
from astropy.io import fits

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE.parent / "header_acquisition_v2"
OLD = HERE.parent / "header_acquisition"
CHECKS = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.parts = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "pre":
            assert not self.active
            self.active, self.parts = True, []
        elif tag.lower() == "br" and self.active:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() == "pre":
            assert self.active
            self.blocks.append("".join(self.parts))
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def main():
    plan, results = read(DATA / "PLAN.json"), read(DATA / "HEADER_RESULTS.json")
    selection, release = read(DATA / "EXTREME_SELECTION.json"), read(DATA / "ROOT_RELEASE.json")
    sources = [DATA / name for name in ("PLAN.json", "ROOT_RELEASE.json", "HEADER_RESULTS.json", "EXTREME_SELECTION.json", "REQUEST_STARTED.json")]
    check(sha(DATA / "PLAN.json") == "c23fde3cd9ded92543cc0bcbbd927fabcb4c76db46b953a9d725f48a3b2843d1", "Exact published amended plan")
    check(release["approved"] is True and release["plan_sha256"] == sha(DATA / "PLAN.json"), "Exact separate root release")
    check(results["root_release_sha256"] == sha(DATA / "ROOT_RELEASE.json"), "Result binds root release")
    check(results["plan_sha256"] == sha(DATA / "PLAN.json"), "Result binds plan")
    check(results["code_hashes"] == release["code_hashes"] == plan["code_hashes"], "Matching release, result and plan code hashes")
    for filename, digest in plan["code_hashes"].items():
        check(sha(DATA / filename) == digest, "Frozen code unchanged " + filename)
    for item in plan["inputs"]:
        check(sha(ROOT / item["path"]) == item["sha256"], "Frozen input unchanged " + item["path"])
    check(results["status"] == "COMPLETE" and results["stop_reason"] is None, "Completed two-job batch")
    check(results["requests_attempted"] == len(results["results"]) == len(plan["jobs"]) == 2, "Exactly two new requests and complete job accounting")
    check(selection["header_results_sha256"] == sha(DATA / "HEADER_RESULTS.json") and selection["header_plan_sha256"] == sha(DATA / "PLAN.json"), "Selection binds exact result and plan")
    check(selection["all_planned_jobs_attempted"] and not selection["header_sampling_is_partial"], "Complete fixed header sample, no unattempted jobs")
    observations, total_bytes = [], 0
    first_start = None
    for job, result in zip(plan["jobs"], results["results"]):
        identity = job["dp_id"]
        check(all(result[key] == job[key] for key in ("job_index", "target", "dp_id", "month_number")), "Exact job identity " + identity)
        body_path, receipt_path = DATA / result["body_path"], DATA / result["receipt_path"]
        sources.extend((body_path, receipt_path))
        receipt, raw = read(receipt_path), body_path.read_bytes()
        check(sha(body_path) == result["body_sha256"] == receipt["body_sha256"], "Body identity " + identity)
        check(sha(receipt_path) == result["receipt_sha256"], "Receipt identity " + identity)
        check(receipt["plan_sha256"] == results["plan_sha256"] and receipt["code_hashes"] == plan["code_hashes"], "Receipt method binding " + identity)
        check(receipt["url"] == job["url"] and receipt["dp_id"] == identity, "Exact corrected request " + identity)
        check(receipt["attempts"] == 1 and receipt["retries"] == receipt["redirects_followed"] == 0, "One no-redirect attempt " + identity)
        check(receipt["http_status"] == 200 and receipt["complete"] and receipt["error"] is None, "Complete successful transport " + identity)
        check(len(raw) == receipt["bytes_saved"] < receipt["effective_byte_cap"] == 524288, "Hard byte-cap accounting " + identity)
        check(receipt["elapsed_seconds"] <= 30, "30-second request bound " + identity)
        start = datetime.fromisoformat(receipt["started_utc"])
        first_start = start if first_start is None else first_start
        total_bytes += len(raw)
        parser = Blocks()
        parser.feed(raw.decode("utf-8"))
        parser.close()
        check(not parser.active and len(parser.blocks) == 1, "Exactly one closed HTML PRE " + identity)
        lines = parser.blocks[0].splitlines()
        starts = [i for i, line in enumerate(lines) if re.match(r"^SIMPLE\s*=", line)]
        check(len(starts) == 1, "Exactly one primary start " + identity)
        finish = next(i for i in range(starts[0], len(lines)) if lines[i].strip() == "END")
        primary = lines[starts[0]:finish + 1]
        # ESO display text expands some quoted strings past the FITS 80-byte
        # card width. Normalize display-only comments/long strings, then use
        # Astropy scalar/card parsing; do not silently truncate a long value.
        header, display_keys = fits.Header(), []
        for line in primary[:-1]:
            if line[:8].strip() in {"", "COMMENT", "HISTORY"}:
                continue
            left, right = line.split("=", 1)
            key = " ".join(left.split()).removeprefix("HIERARCH ")
            display_keys.append(key)
            right = right.lstrip()
            if right.startswith("'"):
                match = re.match(r"'((?:[^']|'')*)'\s*(?:/.*)?$", right)
                check(match is not None, "Complete quoted display value " + identity + " " + key)
                value = match.group(1).replace("''", "'").rstrip()
                # This reconstructs any required FITS CONTINUE cards.
                card = fits.Card(("HIERARCH " + key) if len(key) > 8 else key, value)
            else:
                value_text = right.split("/", 1)[0].strip()
                prefix = ("HIERARCH " + key + " = ") if len(key) > 8 else key.ljust(8) + "= "
                card = fits.Card.fromstring(prefix + value_text)
            header.append(card)
        check(header["SIMPLE"] is True and len(primary) == 3078, "Independently decoded 3078 primary display cards " + identity)
        keys = Counter(display_keys)
        check(all(count == 1 for count in keys.values()), "No duplicate primary value keywords " + identity)
        recorded = result["inspection"]
        for key, expected in recorded["primary_header"].items():
            check(header[key] == expected, "Independent retained card " + identity + " " + key)
        check(header["ARCFILE"] in {identity, identity + ".fits"}, "Exact independent ARCFILE " + identity)
        check(header["INSTRUME"] == "HARPS" and header["SPECSYS"] == "BARYCENT", "HARPS barycentric frame " + identity)
        check(re.sub("[^A-Z0-9]", "", header["OBJECT"].upper()) == job["target"], "Independent canonical target " + identity)
        check(type(header["NCOMBINE"]) in {int, float} and header["NCOMBINE"] == 1, "One combined exposure " + identity)
        check(header["SPEC_RES"] == 115000 and header["ESO INS HEFS ST"] is False, "High-resolution closed HEFS " + identity)
        provenance = [header[key] for key in header if re.fullmatch(r"PROV\d+", key)]
        check(len(provenance) == 1 and provenance[0] in {job["source_file_ids"][0], job["source_file_ids"][0] + ".fits"}, "Complete sole raw provenance " + identity)
        metadata = job["metadata"]
        check(abs(header["MJD-OBS"] - metadata["t_min"]) <= 1e-7, "Metadata MJD agreement " + identity)
        mjd_date = datetime(1858, 11, 17) + timedelta(days=header["MJD-OBS"])
        check(abs((datetime.fromisoformat(header["DATE-OBS"]) - mjd_date).total_seconds()) <= .02, "Independent DATE-OBS/MJD agreement " + identity)
        check(abs(header["EXPTIME"] - metadata["t_exptime"]) <= .02, "Exposure duration agreement " + identity)
        check(header["RA"] == metadata["s_ra"] and header["DEC"] == metadata["s_dec"], "Exact independent position agreement " + identity)
        berv = header["ESO DRS BERV"]
        check(type(berv) in {int, float} and math.isfinite(berv) and abs(berv) <= 100, "Independent recorded BERV sanity " + identity)
        check(berv == recorded["berv_km_s"] and all(recorded["checks"].values()) and not recorded["failures"] and result["status"] == "PASS_RECORDED_BERV", "Independent PASS/BERV matches production " + identity)
        observations.append({"dp_id": identity, "target": job["target"], "berv_km_s": berv, "pipeline": header["PROCSOFT"], "raw_id": job["source_file_ids"][0], "primary_cards": len(primary), "response_bytes": len(raw)})
    marker = read(DATA / "REQUEST_STARTED.json")
    check(datetime.fromisoformat(marker["started_utc"]) <= first_start, "Execution marker precedes target requests")
    check(marker["root_release_sha256"] == sha(DATA / "ROOT_RELEASE.json"), "Execution marker binds release")
    check(total_bytes == results["response_bytes"] == 455347, "Exact new response bytes")
    old = read(OLD / "HEADER_RESULTS.json")
    check(old["requests_attempted"] + results["requests_attempted"] == 3, "Cumulative three-request bound reached, none remaining")
    check(old["response_bytes"] + total_bytes == 457986 <= plan["technical_amendment"]["cumulative_response_byte_ceiling"], "Cumulative response byte accounting")
    expected_ids = []
    diagnostics = {}
    scale = 299792.458 / 115000
    for target in ("HD122640", "HD135204"):
        observed = sorted((x for x in observations if x["target"] == target), key=lambda x: (x["berv_km_s"], x["dp_id"]))
        baseline = plan["existing_berv_benchmark"][target]
        values = [baseline["minimum_berv_km_s"], baseline["maximum_berv_km_s"]] + [x["berv_km_s"] for x in observed]
        span = max(values) - min(values)
        new_span = observed[-1]["berv_km_s"] - observed[0]["berv_km_s"] if observed else None
        ready = bool(observed) and span > scale
        target_result = selection["target_summary"][target]
        check(target_result["verified_headers"] == len(observed), "Independent verified-header count " + target)
        check(target_result["recorded_berv_span_km_s"] == new_span, "Independent new BERV span " + target)
        check(abs(target_result["combined_span_km_s"] - span) < 1e-12, "Independent combined span " + target)
        check(abs(target_result["combined_span_increase_km_s"] - (span - baseline["span_km_s"])) < 1e-12, "Independent span increase " + target)
        check(abs(target_result["combined_span_resolution_elements_R115000"] - span / scale) < 1e-12, "Independent descriptive resolution elements " + target)
        check(target_result["payload_readiness_gate_passed"] is ready, "Independent strict c/R planning gate " + target)
        chosen = [observed[0]["dp_id"], observed[-1]["dp_id"]] if ready else []
        expected_ids.extend(dict.fromkeys(chosen))
        check(target_result["selected_epochs"] == len(set(chosen)), "Selected epoch count " + target)
        diagnostics[target] = {"verified_headers": len(observed), "combined_span_km_s": span, "new_span_km_s": new_span, "combined_span_increase_km_s": span - baseline["span_km_s"], "combined_span_resolution_elements": span / scale, "payload_readiness_gate_passed": ready}
    check([x["dp_id"] for x in selection["selected"]] == expected_ids, "Exact minimum-then-maximum selection order")
    for row in selection["selected"]:
        job = next(x for x in plan["jobs"] if x["dp_id"] == row["dp_id"])
        check(row["metadata"] == job["metadata"] and row["source_file_ids"] == job["source_file_ids"], "Selection carries exact original metadata " + row["dp_id"])
        for kind in ("body", "receipt"):
            check(sha(DATA / row["header_" + kind + "_path"]) == row["header_" + kind + "_sha256"], "Selection evidence identity " + row["dp_id"] + " " + kind)
    check(selection["spectral_payload_acquisition_authorized"] is False and results["spectral_arrays_requested_or_read"] is False, "No science payload or array authorization implied")
    out = {"status": "PASS_INDEPENDENT_ACTUAL_HEADER_AND_SELECTION_AUDIT", "checked_utc": datetime.now(timezone.utc).isoformat(), "checks_passed": len(CHECKS), "checks": CHECKS,
           "independent_decoder": "Astropy FITS Card/Header " + astropy.__version__ + "; isolated primary display cards extracted from saved HTML PRE. ESO long quoted display strings normalized without truncation; numeric/boolean values decoded by Astropy.", "observations": observations,
           "target_diagnostics": diagnostics, "selected_dp_ids": expected_ids, "new_requests": 2, "cumulative_requests": 3, "new_response_bytes": total_bytes, "cumulative_response_bytes": 457986,
           "interpretation": "HD122640 has larger recorded-BERV displacement suitable for the frozen next acquisition step. This is an operational planning gate, not a claim about signal origin, statistical power or archive completeness. Both selected products report HARPS_3.8; payload representation and compatibility must still be checked before arrays. HD135204 remains without new eligible epochs.",
           "source_hashes": {str(path.relative_to(ROOT)): sha(path) for path in sources}, "audit_script_sha256": sha(Path(__file__)),
           "network_requests_by_audit": 0, "production_parser_or_classifier_imported": False, "science_arrays_read": 0, "labels_changed": 0}
    (HERE / "HEADER_V2_RESULT_AUDIT.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({key: out[key] for key in ("status", "checks_passed", "selected_dp_ids", "target_diagnostics")}))


if __name__ == "__main__":
    main()
