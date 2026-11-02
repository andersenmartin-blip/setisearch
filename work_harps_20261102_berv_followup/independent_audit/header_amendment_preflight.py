#!/usr/bin/env python3
"""Focused independent audit of the prospectively authorized header URL amendment.

Reads saved files only. No production parser import, network or spectrum access.
"""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = HERE.parent / "header_acquisition"
NEW = HERE.parent / "header_acquisition_v2"
CHECKS = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def main():
    old, new = read(OLD / "PLAN.json"), read(NEW / "PLAN.json")
    old_result = read(OLD / "HEADER_RESULTS.json")
    freeze = read(NEW / "AMENDMENT_FREEZE.json")
    evidence = read(NEW / "docs/URL_BUILDER_RECEIPT.json")
    amendment = new["technical_amendment"]
    check(sha(OLD / "PLAN.json") == "28d9ce9d78a288c72c6a4a6e0ebcb4b6c17108eeaecd4dbee6fdc53b81b40dac", "Original published plan unchanged")
    check(sha(NEW / "PLAN.json") == "c23fde3cd9ded92543cc0bcbbd927fabcb4c76db46b953a9d725f48a3b2843d1", "Exact stable amended plan")
    check(sha(OLD / "HEADER_RESULTS.json") == "4ac1d13eb49bc92a4db9abf24f809507a7d8a25af34a8ef428e587162b91cf34", "Original failed result unchanged")
    check(read(HERE / "HEADER_RESULT_AUDIT.json")["status"] == "PASS_SAFE_STOP_WITH_HEADER_URL_CONTRACT_FAILURE", "Independent original failure audit retained")
    check(set(new) - set(old) == {"technical_amendment"}, "Only expected new plan key")
    for key in old:
        if key not in {"created_utc", "inputs", "code_hashes", "jobs"}:
            check(old[key] == new[key], "Unchanged plan field " + key)
    check(new["inputs"][:len(old["inputs"])] == old["inputs"], "Original scientific inputs preserved")
    for item in new["inputs"]:
        relative = Path(item["path"])
        check(not relative.is_absolute(), "Repository relative input " + relative.name)
        path = (ROOT / relative).resolve()
        path.relative_to(ROOT)
        check(sha(path) == item["sha256"], "Input hash " + relative.name)
    check(len(new["jobs"]) == len(old["jobs"]) == 2, "Same exact two jobs")
    for previous, current in zip(old["jobs"], new["jobs"]):
        p, c = copy.deepcopy(previous), copy.deepcopy(current)
        p.pop("url")
        c.pop("url")
        check(p == c, "All non-URL job fields unchanged " + c["dp_id"])
        check(current["url"] == previous["url"].replace("%3A", ":"), "Only colon serialization changed " + c["dp_id"])
        url = urlsplit(current["url"])
        check((url.scheme, url.netloc, url.path, url.fragment) == ("https", "archive.eso.org", "/hdr", ""), "Exact header-only endpoint " + c["dp_id"])
        check(parse_qs(url.query) == {"DpId": [c["dp_id"]]}, "Exact single DpId query " + c["dp_id"])
        check(Request(current["url"]).full_url == current["url"], "urllib preserves literal-colon URL without sending " + c["dp_id"])
    for name, digest in new["code_hashes"].items():
        check(sha(NEW / name) == digest, "New code hash " + name)
        check(sha(OLD / name) == old["code_hashes"][name], "Original code hash " + name)
    for name in ("header_tools.py", "select_extremes.py"):
        check((NEW / name).read_bytes() == (OLD / name).read_bytes(), "Scientific code byte-identical " + name)
    replacements = {
        "make_plan.py": ('"https://archive.eso.org/hdr?" + urlencode({"DpId": row["dp_id"]})', '"https://archive.eso.org/hdr?DpId=" + row["dp_id"]'),
        "fetch_headers.py": ('"https://archive.eso.org/hdr?" + urllib.parse.urlencode({"DpId": job["dp_id"]})', '"https://archive.eso.org/hdr?DpId=" + job["dp_id"]'),
    }
    for name, (before, after) in replacements.items():
        previous = (OLD / name).read_text()
        check(previous.count(before) == 1 and previous.replace(before, after) == (NEW / name).read_text(), "Single exact URL-expression code delta " + name)
    check(freeze["plan_sha256"] == sha(NEW / "PLAN.json"), "Amendment freeze binds exact plan")
    check(freeze["original_plan_sha256"] == sha(OLD / "PLAN.json"), "Amendment freeze binds original plan")
    check(freeze["old_code_hashes"] == old["code_hashes"] and freeze["new_code_hashes"] == new["code_hashes"], "Amendment freeze code identities")
    check(freeze["target_header_requests_executed_in_v2"] == 0, "Prospective zero-request amendment record")
    check(amendment["original_failed_plan_sha256"] == sha(OLD / "PLAN.json"), "Amendment ancestor exact")
    check(amendment["original_failure_body_sha256"] == sha(OLD / old_result["results"][0]["body_path"]), "Amendment preserves failed body")
    check(old_result["requests_attempted"] == amendment["prior_target_header_requests"] == 1, "One prior request accounted")
    check(amendment["new_max_target_header_requests"] == len(new["jobs"]) == 2, "Two new requests maximum")
    check(amendment["cumulative_max_target_header_requests"] == 1 + len(new["jobs"]) == 3, "At most three cumulative target header requests")
    check(amendment["prior_response_bytes"] == old_result["response_bytes"] == 2639, "Prior response bytes accounted")
    check(amendment["new_effective_response_byte_ceiling"] == len(new["jobs"]) * new["limits"]["max_response_bytes"] == 1048576, "Actual two-job byte ceiling")
    check(amendment["cumulative_response_byte_ceiling"] == 2639 + 1048576, "Cumulative 1051215-byte ceiling")
    check(evidence["sha256"] == sha(NEW / "docs/URL_BUILDER_RESPONSE.txt"), "Official saved URL-only response hash")
    response = (NEW / "docs/URL_BUILDER_RESPONSE.txt").read_text().strip()
    check(response == "https://archive.eso.org/hdr?DpId=ADP.2014-10-01T10:19:21.580", "Documented URL retains DpId and literal colons")
    check(evidence["target_header_requests"] == 0 and evidence["requests"] == 1 and evidence["bytes"] == 61, "Documentation request separated from target headers")
    check("service=header&debug=debug" in evidence["url"], "URL-only debug contract recorded")
    check(not (NEW / "ROOT_RELEASE.json").exists() and not (NEW / "REQUEST_STARTED.json").exists(), "No amendment release or target execution at review")
    out = {
        "status": "PASS_FOCUSED_HEADER_SERIALIZATION_AMENDMENT",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "checks_passed": len(CHECKS), "checks": CHECKS,
        "plan_sha256": sha(NEW / "PLAN.json"),
        "amendment_freeze_sha256": sha(NEW / "AMENDMENT_FREEZE.json"),
        "code_hashes": new["code_hashes"],
        "original_requests": 1, "new_request_bound": 2, "cumulative_request_bound": 3,
        "cumulative_response_byte_ceiling": 1051215,
        "unchanged": "Exact two IDs, all metadata, scientific parser/selector, transport, canary, no-retry/no-redirect limits, root-release guard, BERV gates and original labels.",
        "limits_of_review": "URL-only official response documents the request shape; it is not proof that either target header exists or passes identity/BERV checks. No outcome or origin inferred. Separate root publication/release remains necessary.",
        "audit_script_sha256": sha(Path(__file__)),
        "network_requests_by_audit": 0, "production_parser_imported": False,
        "science_arrays_read": 0, "labels_changed": 0,
    }
    (HERE / "HEADER_AMENDMENT_PREFLIGHT_AUDIT.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({key: out[key] for key in ("status", "checks_passed", "plan_sha256")}))


if __name__ == "__main__":
    main()
