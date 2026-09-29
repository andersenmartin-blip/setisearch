"""Bounded grouping of independent immutable Git file readbacks.

Engineering-only transport helper.  It does not authorize a scientific lease,
render Gaussian values, or mutate Git.  The surrounding worker remains solely
responsible for serial mutation and durable case consumption.
"""
import base64
import hashlib

from .empty_null_radio import canonical
from .whole_cadence_remote_radio import git_object, git_sha, safe_path

REPO = "andersenmartin-blip/setisearch"
# Read only the already-closed archive at its immutable completion commit.
# The new scope has its own evidence directory but does not alter this prefix.
PREFIX = "results_radio_whole_cadence_batch_2026-09-29/live01/"
LIVE02_PATHS = {
    "PROJECT_DIRECTION.md",
    "PROJECT_STATUS.md",
    "RADIO_TWO_WEEK_PLAN_2026-09-26.md",
    "RADIO_WHOLE_CADENCE_READBATCH_2026-09-29_SCOPE.md",
    "config/radio_whole_cadence_readbatch_recipe_20260929.json",
    "src/seti_repeater/whole_cadence_readbatch_radio.py",
    "tests/test_radio_whole_cadence_readbatch.py",
}
MAX_FILES = 8
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
RESPONSE_OVERHEAD_PER_FILE = 768


class ReadbackStopped(RuntimeError):
    """The aggregate is ambiguous or invalid and cannot be retried."""


def _positive_int(value, label):
    if type(value) is not int or value < 1:
        raise ValueError(f"Positive integer {label} required")
    return value


def _validate_requests(requests):
    if not isinstance(requests, list) or not 1 <= len(requests) <= MAX_FILES:
        raise ValueError("Bounded immutable readback inventory required")
    expected = set(range(len(requests)))
    seen_ordinals = set()
    seen_paths = set()
    normalized = []
    for row in requests:
        if set(row) != {"ordinal", "path", "ref", "blob_sha", "cap"}:
            raise ValueError("Exact immutable readback request required")
        ordinal = row["ordinal"]
        if type(ordinal) is not int:
            raise ValueError("Integer readback ordinal required")
        path = safe_path(row["path"])
        if not (path.startswith(PREFIX) or path in LIVE02_PATHS):
            raise ValueError("Readback escaped frozen engineering namespace")
        ref = git_sha(row["ref"])
        blob_sha = git_sha(row["blob_sha"])
        cap = _positive_int(row["cap"], "readback cap")
        seen_ordinals.add(ordinal)
        if path in seen_paths:
            raise ValueError("Duplicate immutable readback path")
        seen_paths.add(path)
        normalized.append({"ordinal": ordinal, "path": path, "ref": ref,
                           "blob_sha": blob_sha, "cap": cap})
    if seen_ordinals != expected:
        raise ValueError("Readback ordinals must be complete and unique")
    return normalized


def reserved_response_bytes(requests):
    """Conservative base64 plus JSON allowance, charged before dispatch."""
    rows = _validate_requests(requests)
    return sum(4 * ((row["cap"] + 2) // 3) + RESPONSE_OVERHEAD_PER_FILE
               for row in rows)


class ImmutableReadbackBatch:
    """One no-retry aggregate with per-underlying-request accounting."""

    def __init__(self, invoke, *, prior_calls=0, prior_response_bytes=0,
                 call_limit=MAX_FILES, response_limit=MAX_RESPONSE_BYTES):
        self.invoke = invoke
        self.call_limit = _positive_int(call_limit, "call limit")
        self.response_limit = _positive_int(response_limit, "response limit")
        if (type(prior_calls) is not int or prior_calls < 0 or
                type(prior_response_bytes) is not int or prior_response_bytes < 0):
            raise ValueError("Nonnegative prior charges required")
        if prior_calls > call_limit or prior_response_bytes > response_limit:
            raise ValueError("Prior charges exceed aggregate limits")
        self.underlying_calls = prior_calls
        self.response_bytes = prior_response_bytes
        self.reserved_bytes = 0
        self.events = []
        self.stopped = False

    def read(self, requests):
        if self.stopped:
            raise ReadbackStopped("Readback batch already stopped; inspect evidence")
        candidate = None
        try:
            rows = _validate_requests(requests)
            reserve = reserved_response_bytes(rows)
            if self.underlying_calls + len(rows) > self.call_limit:
                raise ValueError("Underlying request limit exhausted")
            if self.response_bytes + reserve > self.response_limit:
                raise ValueError("Aggregate response reservation exceeds cap")

            # Charge each underlying request and the whole possible response
            # before any connector work.  Reservations are nonrefundable.
            self.underlying_calls += len(rows)
            self.reserved_bytes += reserve
            candidate = {
                "kind": "dispatch",
                "underlying_requests_charged": len(rows),
                "aggregate_response_bytes_reserved": reserve,
                "request_sha256": hashlib.sha256(canonical(rows)).hexdigest(),
            }
            self.events.append(candidate)
            result = self.invoke("fetch_files", {
                "repository_full_name": REPO,
                "aggregate_response_bytes": reserve,
                "requests": [
                    {"ordinal": row["ordinal"], "path": row["path"],
                     "ref": row["ref"], "encoding": "base64"}
                    for row in rows
                ],
            })
            raw_result = canonical(result)
            self.response_bytes += len(raw_result)
            if len(raw_result) > reserve or self.response_bytes > self.response_limit:
                raise ValueError("Actual aggregate response exceeds reserved cap")
            if (not isinstance(result, dict) or set(result) != {"items", "underlying_request_count"}
                    or result["underlying_request_count"] != len(rows)
                    or not isinstance(result["items"], list)):
                raise ValueError("Exact aggregate response frame required")

            indexed = {}
            failures = []
            for item in result["items"]:
                if not isinstance(item, dict) or type(item.get("ordinal")) is not int:
                    raise ValueError("Readback reply identity absent")
                ordinal = item["ordinal"]
                if ordinal in indexed:
                    raise ValueError("Duplicate readback reply")
                indexed[ordinal] = item
            if set(indexed) != set(range(len(rows))):
                raise ValueError("Missing or unexpected readback reply")

            decoded = {}
            by_ordinal = {row["ordinal"]: row for row in rows}
            for ordinal, item in indexed.items():
                row = by_ordinal[ordinal]
                if item.get("ok") is False:
                    if set(item) != {"ordinal", "ok", "error", "automatic_retry"}:
                        raise ValueError("Exact failed readback receipt required")
                    if item["automatic_retry"] is not False or not isinstance(item["error"], str):
                        raise ValueError("Failed readback cannot authorize retry")
                    failures.append({"ordinal": ordinal, "error": item["error"]})
                    continue
                if set(item) != {"ordinal", "ok", "result"} or item["ok"] is not True:
                    raise ValueError("Exact successful readback receipt required")
                response = item["result"]
                if (not isinstance(response, dict) or response.get("sha") != row["blob_sha"]
                        or response.get("encoding") != "base64" or
                        not isinstance(response.get("content"), str)):
                    raise ValueError("Git blob size/encoding/identity differs")
                encoded = response["content"].replace("\n", "").replace("\r", "")
                if len(encoded) > 4 * ((row["cap"] + 2) // 3):
                    raise ValueError("Encoded immutable blob exceeds cap")
                data = base64.b64decode(encoded, validate=True)
                if len(data) > row["cap"]:
                    raise ValueError("Decoded immutable blob exceeds cap")
                if git_object("blob", data) != row["blob_sha"]:
                    raise ValueError("Immutable Git blob content hash differs")
                decoded[ordinal] = data
            candidate["reply_order"] = [item["ordinal"] for item in result["items"]]
            candidate["actual_response_bytes"] = len(raw_result)
            candidate["failures"] = failures
            if failures:
                raise ValueError("Partial immutable readback failure")
            candidate["status"] = "verified"
            return [decoded[i] for i in range(len(rows))]
        except BaseException as error:
            self.stopped = True
            self.events.append({
                "kind": "stopped",
                "error": repr(error),
                "underlying_charges_nonrefundable": True,
                "automatic_retry": False,
            })
            raise ReadbackStopped("Immutable readback batch stopped without retry: " + str(error)) from error
