#!/usr/bin/env python3
"""One separately frozen, single-use package-source operation; no installation.

This helper uses only the Python standard library. It never imports a wheel,
opens an archive member or HDF5 file, activates another workflow, or qualifies
a native/scientific runtime. Offline tests inject an opener into acquire().
"""

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import resource
import signal
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


IDENTITY = "radio-hosted-package-source-20261005a"
REPOSITORY = "andersenmartin-blip/setisearch"
FREEZE_SCHEMA = "radio-hosted-package-source-freeze-v1"
MARKER_SCHEMA = "radio-hosted-package-source-activation-v1"
FREEZE_PATH = "config/radio_package_source_20261005a.freeze.json"
MARKER_PATH = "config/radio_package_source_20261005a.activate.json"
ORIGINAL_PATH = "results_radio_runtime_bootstrap_preparation_20261005b/original-plan.json"
ORIGINAL_SHA256 = "fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25"
SOURCE_PATHS = frozenset((
    "scripts/radio_package_source_20261005a.py",
    "tests/test_radio_package_source_20261005a.py",
    ".github/workflows/radio-package-source-20261005a.yml",
    "RADIO_HOSTED_PACKAGE_SOURCE_2026-10-05_PROTOCOL.md",
    ORIGINAL_PATH,
))
LIMITS = {
    "download_wall_seconds": 180,
    "preservation_wall_seconds": 60,
    "request_timeout_seconds": 30,
    "per_original_bytes": 128 * 1024 * 1024,
    "artifact_storage_bytes": 512 * 1024 * 1024,
    "address_space_bytes": 512 * 1024 * 1024,
    "total_received_bytes": 68409067,
    "export_part_bytes": 23 * 1024 * 1024,
}
READ_CHUNK = 64 * 1024
_WHEEL_ROWS = (
    ("numpy", "2.3.5", "numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl", 16606086,
     "0d8163f43acde9a73c2a33605353a4f1bc4798745a8b1d73183b28e5b435ae28",
     "b6/23/2a1b231b8ff672b4c450dac27164a8b2ca7d9b7144f9c02d2396518352eb"),
    ("h5py", "3.16.0", "h5py-3.16.0-cp312-cp312-manylinux_2_28_x86_64.whl", 5405250,
     "dfc21898ff025f1e8e67e194965a95a8d4754f452f83454538f98f8a3fcb207e",
     "9e/e9/1a19e42cd43cc1365e127db6aae85e1c671da1d9a5d746f4d34a50edb577"),
    ("hdf5plugin", "7.1.0", "hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl", 46397731,
     "9d4cf36434819fae53e4da432f0287ebaeb02386ab97b73d261092efbab12247",
     "26/56/3f788afb8d7fc451d20a66a64ea58bbe189f6f11780b28ba09148974fb33"),
)
WHEELS = tuple(dict(name=n, version=v, filename=f, bytes=b, sha256=h,
                    url="https://files.pythonhosted.org/packages/" + u + "/" + f)
               for n, v, f, b, h, u in _WHEEL_ROWS)
WHEEL_KEYS = frozenset(("name", "version", "filename", "bytes", "sha256", "url"))


class Refusal(Exception):
    """A bounded failure with a stable, secret-free public description."""


class DownloadDeadline(Refusal):
    pass


class PreservationDeadline(Refusal):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def json_object(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (UnicodeError, ValueError, TypeError):
        raise Refusal("invalid_json") from None
    require(isinstance(value, dict), "json_object_required")
    return value


def safe_path(value):
    require(isinstance(value, str), "path_string_required")
    parts = PurePosixPath(value).parts
    require(bool(parts) and not value.startswith("/") and
            ".." not in parts and "." not in parts and
            "\\" not in value and "\0" not in value and
            str(PurePosixPath(value)) == value, "unsafe_source_path")
    return value


def read_source(root, relative):
    path = root.joinpath(*PurePosixPath(safe_path(relative)).parts)
    cursor = root
    for component in PurePosixPath(relative).parts:
        cursor = cursor / component
        require(not cursor.is_symlink(), "symlink_source_refused")
    require(path.is_file() and path.stat().st_size <= 4 * 1024 * 1024,
            "source_missing_or_oversize")
    return path.read_bytes()


def git(root, *arguments):
    try:
        result = subprocess.run(["git", "-C", str(root), *arguments],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("git_verification_failed") from None
    require(len(result.stdout) <= 4 * 1024 * 1024, "git_result_oversize")
    return result.stdout


def validate_url(url, filename):
    require(isinstance(url, str), "url_string_required")
    parsed = urllib.parse.urlsplit(url)
    require(parsed.scheme == "https" and parsed.netloc == "files.pythonhosted.org" and
            parsed.hostname == "files.pythonhosted.org" and
            parsed.username is None and parsed.password is None and
            parsed.port is None and not parsed.query and not parsed.fragment and
            parsed.path.startswith("/packages/") and
            parsed.path.endswith("/" + filename), "nonofficial_url_refused")


def validate_freeze(freeze, original):
    require(freeze.get("schema") == FREEZE_SCHEMA and
            freeze.get("identity") == IDENTITY, "freeze_identity_mismatch")
    require(freeze.get("marker_path") == MARKER_PATH and
            freeze.get("original_plan_path") == ORIGINAL_PATH and
            freeze.get("original_plan_sha256") == ORIGINAL_SHA256,
            "freeze_path_or_original_pin_mismatch")
    require(freeze.get("limits") == LIMITS and
            all(type(value) is int for value in freeze["limits"].values()),
            "limits_mismatch")
    sources = freeze.get("sources")
    require(isinstance(sources, dict) and frozenset(sources) == SOURCE_PATHS,
            "exact_source_set_required")
    require(all(isinstance(pin, str) and re.fullmatch(r"[0-9a-f]{64}", pin)
                for pin in sources.values()), "invalid_source_pin")
    require(sources[ORIGINAL_PATH] == ORIGINAL_SHA256, "original_source_pin_mismatch")
    frozen_wheels = freeze.get("wheels")
    require(isinstance(frozen_wheels, list) and len(frozen_wheels) == 3,
            "exact_three_wheels_required")
    for observed, expected in zip(frozen_wheels, WHEELS):
        require(isinstance(observed, dict) and frozenset(observed) == WHEEL_KEYS and
                observed == expected and type(observed.get("bytes")) is int,
                "original_wheel_cohort_mismatch")
        validate_url(observed["url"], observed["filename"])
    require(sha256(original) == ORIGINAL_SHA256, "original_plan_bytes_mismatch")
    plan = json_object(original)
    actual = plan.get("materialization", {}).get("official_wheels")
    require(isinstance(actual, list) and len(actual) == 3 and
            [{key: row.get(key) for key in WHEEL_KEYS} for row in actual] == list(WHEELS),
            "original_plan_wheels_mismatch")


def admit(freeze_path, marker_path, env, git_call=git):
    """Verify exact source bytes and marker-only child commit before any request."""
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_REPOSITORY"):
        require(isinstance(env.get(key), str), "github_identity_missing")
    require(re.fullmatch(r"[1-9][0-9]{0,19}", env["GITHUB_RUN_ID"]) is not None,
            "invalid_run_id")
    require(env["GITHUB_RUN_ATTEMPT"] == "1", "rerun_refused")
    require(env["GITHUB_REPOSITORY"] == REPOSITORY, "repository_mismatch")
    require(re.fullmatch(r"[0-9a-f]{40}", env["GITHUB_SHA"]) is not None,
            "invalid_github_sha")
    root = Path(git_call(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip()).resolve()
    require(Path(freeze_path).resolve() == root / FREEZE_PATH and
            Path(marker_path).resolve() == root / MARKER_PATH,
            "cli_source_path_mismatch")
    raw_freeze = read_source(root, FREEZE_PATH)
    raw_marker = read_source(root, MARKER_PATH)
    freeze, marker = json_object(raw_freeze), json_object(raw_marker)
    require(marker.get("schema") == MARKER_SCHEMA and marker.get("identity") == IDENTITY and
            marker.get("single_use") is True and marker.get("package_only") is True and
            marker.get("automatic_successor") is False, "inactive_or_invalid_marker")
    commit, tree = marker.get("prepared_commit"), marker.get("prepared_tree")
    require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) and
            isinstance(tree, str) and re.fullmatch(r"[0-9a-f]{40}", tree),
            "invalid_prepared_git_identity")
    require(marker.get("freeze_sha256") == sha256(raw_freeze), "freeze_sha_mismatch")
    head = git_call(root, "rev-parse", "HEAD").decode().strip()
    require(head == env["GITHUB_SHA"], "checkout_head_mismatch")
    parents = git_call(root, "show", "-s", "--format=%P", head).decode().strip().split()
    require(parents == [commit], "sole_prepared_parent_required")
    require(git_call(root, "rev-parse", commit + "^{tree}").decode().strip() == tree,
            "prepared_tree_mismatch")
    changed = git_call(root, "diff", "--name-only", "-z", commit, head).decode().split("\0")
    require(changed == [MARKER_PATH, ""], "activation_must_change_marker_only")
    require(git_call(root, "show", head + ":" + MARKER_PATH) == raw_marker,
            "marker_worktree_mismatch")
    require(git_call(root, "show", commit + ":" + FREEZE_PATH) == raw_freeze,
            "freeze_worktree_mismatch")
    original = read_source(root, ORIGINAL_PATH)
    validate_freeze(freeze, original)
    snapshots = {FREEZE_PATH: raw_freeze, MARKER_PATH: raw_marker}
    for relative, expected_hash in freeze["sources"].items():
        raw = read_source(root, relative)
        require(sha256(raw) == expected_hash, "source_hash_mismatch")
        require(git_call(root, "show", commit + ":" + relative) == raw,
                "source_committed_bytes_mismatch")
        snapshots[relative] = raw
    return freeze, {"identity": IDENTITY, "repository": env["GITHUB_REPOSITORY"],
                    "run_id": env["GITHUB_RUN_ID"], "run_attempt": 1,
                    "github_sha": head, "prepared_commit": commit, "prepared_tree": tree,
                    "freeze_sha256": sha256(raw_freeze), "marker_sha256": sha256(raw_marker),
                    "source_sha256": dict(freeze["sources"])}, snapshots


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if fp is not None:
            fp.close()
        raise Refusal("redirect_refused")


def official_opener():
    # Empty ProxyHandler deliberately disables inherited proxy/credential routing.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                      urllib.request.HTTPSHandler(context=ssl.create_default_context()),
                                      NoRedirect())


def exclusive_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


@contextlib.contextmanager
def durable_original(path):
    with path.open("xb") as stream:
        try:
            yield stream
        finally:
            # Partial originals have the same durability requirement as
            # success bytes; filesystem failure still closes the attempt.
            stream.flush()
            os.fsync(stream.fileno())


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def storage_bytes(output):
    return sum(path.stat().st_size for path in output.rglob("*") if path.is_file())


def runtime_metadata():
    executable = Path(sys.executable).resolve()
    return {"python_version": sys.version, "python_executable": str(executable),
            "python_executable_sha256": sha256(executable.read_bytes()),
            "implementation": sys.implementation.name,
            "machine": platform.machine(), "platform": platform.system(),
            "kernel_release": platform.release(),
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "image_os": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"),
            "observation_only": True, "runtime_qualified": False}


def export_parts(output, path, wheel, part_bytes=LIMITS["export_part_bytes"],
                 clock=time.monotonic, deadline=None):
    """Copy raw received bytes, without unpacking them; include empty partials."""
    exports = []
    remaining, index = path.stat().st_size, 0
    with path.open("rb") as stream:
        while remaining > 0 or index == 0:
            require(deadline is None or clock() < deadline, "preservation_wall_deadline")
            group = wheel["name"]
            if group == "hdf5plugin":
                group += "-part%03d" % index
            destination = output / "exports" / group / (path.name + ".part%03d" % index)
            chunk = stream.read(min(part_bytes, remaining))
            exclusive_write(destination, chunk)
            exports.append({"path": str(destination.relative_to(output)),
                            "artifact_group": group, "index": index,
                            "bytes": len(chunk), "sha256": sha256(chunk)})
            remaining -= len(chunk)
            index += 1
            require(storage_bytes(output) <= LIMITS["artifact_storage_bytes"],
                    "artifact_storage_limit")
            if remaining == 0:
                break
    return exports


def acquire(output, wheels, identity, snapshots, opener=None, clock=time.monotonic,
            limits=LIMITS, host_metadata=None, network_closed=None, preservation_closed=None):
    """Consume admitted bytes once. Dependencies may be injected for offline tests.

    Source/Git admission is separate and mandatory in main(). A failure closes
    this acquisition; later wheels are skipped and a rerun is never attempted.
    """
    output = Path(output)
    require(output.is_absolute() and str(output.resolve()) == str(output),
            "new_absolute_output_required")
    require(output.parent.is_dir() and not output.parent.is_symlink(),
            "output_parent_missing_or_symlink")
    require(sum(len(raw) for raw in snapshots.values()) <= 1024 * 1024,
            "source_receipt_size_limit")
    try:
        output.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError:
        raise Refusal("existing_output_refused") from None
    receipt = output / "exports" / "receipt"
    receipt.mkdir(parents=True)
    started = clock()
    deadline = started + limits["download_wall_seconds"]
    manifest = {"schema": "radio-hosted-package-source-receipt-v1", "identity": identity,
                "status": "FAILED_CLOSED", "package_only": True,
                "runtime_qualified": False, "scientific_authority": False,
                "automatic_successor": False, "limits": dict(limits),
                "runtime_observation": host_metadata if host_metadata is not None else runtime_metadata(),
                "received_bytes": 0, "requests": [], "artifacts": [],
                "skipped_wheels": [], "elapsed_download_seconds": None}
    spent = {"schema": "radio-hosted-package-source-spent-v1", "identity": identity,
             "spent": True, "single_use": True, "package_only": True,
             "automatic_successor": False, "before_first_request": True}
    exclusive_write(output / "spent.json", json_bytes(spent))
    exclusive_write(receipt / "spent.json", json_bytes(spent))
    for relative, raw in snapshots.items():
        exclusive_write(receipt / "sources" / safe_path(relative), raw)
    active_opener = opener
    failed = False
    try:
        for index, wheel in enumerate(wheels):
            if failed:
                manifest["skipped_wheels"].append(wheel["filename"])
                continue
            row = {"name": wheel["name"], "filename": wheel["filename"],
                   "url": wheel["url"], "method": "GET", "request_number": index + 1,
                   "attempts": 0, "status": "FAILED", "http_status": None,
                   "expected_bytes": wheel["bytes"], "expected_sha256": wheel["sha256"],
                   "received_bytes": 0, "received_sha256": None, "error": None, "exports": []}
            manifest["requests"].append(row)
            raw_path = output / "originals" / (wheel["filename"] + ".partial")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            response = None
            try:
                validate_url(wheel["url"], wheel["filename"])
                require(type(wheel["bytes"]) is int and 0 < wheel["bytes"] <= limits["per_original_bytes"],
                        "per_original_size_limit")
                require(clock() < deadline, "download_deadline_before_request")
                with durable_original(raw_path) as stream:
                    if active_opener is None:
                        active_opener = official_opener()
                    timeout = min(limits["request_timeout_seconds"], deadline - clock())
                    require(timeout > 0, "download_deadline_before_request")
                    request = urllib.request.Request(wheel["url"], method="GET",
                                                     headers={"User-Agent": IDENTITY,
                                                              "Accept-Encoding": "identity"})
                    row["attempts"] = 1
                    response = active_opener.open(request, timeout=timeout)
                    row["http_status"] = response.getcode()
                    require(response.geturl() == wheel["url"], "changed_response_url_refused")
                    require(row["http_status"] == 200, "non_200_response")
                    lengths = response.headers.get_all("Content-Length")
                    require(lengths is not None and len(lengths) == 1 and
                            lengths[0] == str(wheel["bytes"]), "content_length_mismatch")
                    require(not response.headers.get("Content-Encoding") or
                            response.headers.get("Content-Encoding").lower() == "identity",
                            "encoded_response_refused")
                    require(not response.headers.get("Transfer-Encoding"), "transfer_encoding_refused")
                    while True:
                        require(clock() < deadline, "download_deadline_during_read")
                        remaining_total = limits["total_received_bytes"] - manifest["received_bytes"]
                        expected_remaining = wheel["bytes"] - row["received_bytes"]
                        if remaining_total == 0:
                            require(expected_remaining == 0, "total_received_limit")
                            break
                        allowance = min(READ_CHUNK, remaining_total,
                                        limits["per_original_bytes"] - row["received_bytes"],
                                        max(1, expected_remaining + 1))
                        require(allowance > 0, "per_original_received_limit")
                        chunk = response.read(allowance)
                        require(isinstance(chunk, bytes) and len(chunk) <= allowance,
                                "response_read_contract_violation")
                        if not chunk:
                            break
                        # These bytes have actually been received: retain even an
                        # allowed overrun byte before closing the failed attempt.
                        digest.update(chunk)
                        row["received_bytes"] += len(chunk)
                        manifest["received_bytes"] += len(chunk)
                        stream.write(chunk)
                        stream.flush()
                        require(row["received_bytes"] <= wheel["bytes"], "original_length_overrun")
                        require(storage_bytes(output) <= limits["artifact_storage_bytes"],
                                "artifact_storage_limit")
                    os.fsync(stream.fileno())
                    require(clock() < deadline, "download_deadline_after_read")
                    require(row["received_bytes"] == wheel["bytes"], "original_length_short")
                    require(digest.hexdigest() == wheel["sha256"], "original_sha256_mismatch")
                row["status"] = "EXACT_ORIGINAL_ARCHIVE"
            except Exception as exc:
                failed = True
                if isinstance(exc, urllib.error.HTTPError):
                    row["http_status"] = exc.code
                    row["error"] = "http_error_" + str(exc.code)
                    try:
                        exc.close()
                    except Exception:
                        row["error"] += "_close_failed"
                elif isinstance(exc, Refusal):
                    row["error"] = str(exc)
                else:
                    row["error"] = "transport_or_io_" + type(exc).__name__
            finally:
                if response is not None:
                    try:
                        response.close()
                    except Exception:
                        failed = True
                        row["status"] = "FAILED"
                        row["error"] = "response_close_failed"
                if not raw_path.exists():
                    exclusive_write(raw_path, b"")
                # Bind the retained path before any fallible stat/hash so a
                # closed acquisition can still export its actual raw bytes.
                row["raw_path"] = str(raw_path.relative_to(output))
                row["received_sha256"] = digest.hexdigest()
                row["retained_bytes"] = None
                row["retained_sha256"] = None
                try:
                    row["retained_bytes"] = raw_path.stat().st_size
                    row["retained_sha256"] = hash_file(raw_path)
                    require(row["retained_bytes"] == row["received_bytes"] and
                            row["retained_sha256"] == row["received_sha256"],
                            "received_byte_retention_failed")
                except Exception as exc:
                    failed = True
                    row["status"] = "FAILED"
                    row["error"] = str(exc) if isinstance(exc, Refusal) else "retained_original_validation_" + type(exc).__name__
                if row["status"] == "EXACT_ORIGINAL_ARCHIVE":
                    complete = raw_path.with_suffix("")
                    raw_path.rename(complete)
                    raw_path = complete
                row["raw_path"] = str(raw_path.relative_to(output))
    except Exception as exc:
        manifest["status"] = "FAILED_CLOSED"
        manifest["finalization_error"] = str(exc) if isinstance(exc, Refusal) else type(exc).__name__
    finally:
        manifest["elapsed_download_seconds"] = max(0, clock() - started)
        preservation_started = clock()
        preservation_deadline = preservation_started + limits["preservation_wall_seconds"]
        if network_closed is not None:
            network_closed()
        # Acquisition is closed permanently before raw-byte preservation.
        # No opener/request is reachable from this bounded finalization phase.
        try:
            for row, wheel in zip(manifest["requests"], wheels):
                raw_path = output / row["raw_path"]
                row["exports"] = export_parts(output, raw_path, wheel, limits["export_part_bytes"],
                                              clock, preservation_deadline)
                manifest["artifacts"].extend(row["exports"])
            groups = {part["artifact_group"] for part in manifest["artifacts"]
                      if part["bytes"] > 0}
            require(storage_bytes(receipt) <= 1024 * 1024, "receipt_size_limit")
            complete = (not failed and "finalization_error" not in manifest and
                        len(manifest["requests"]) == 3 and
                        all(row["status"] == "EXACT_ORIGINAL_ARCHIVE"
                            for row in manifest["requests"]))
            if complete:
                require(groups == {"numpy", "h5py", "hdf5plugin-part000", "hdf5plugin-part001"},
                        "complete_export_groups_required")
                require(all(sum(part["bytes"] for part in row["exports"]) == row["expected_bytes"]
                            for row in manifest["requests"]), "complete_raw_exports_required")
                manifest["status"] = "EXACT_THREE_ORIGINAL_ARCHIVES"
        except Exception as exc:
            manifest["status"] = "FAILED_CLOSED"
            manifest["finalization_error"] = str(exc) if isinstance(exc, Refusal) else type(exc).__name__
        manifest["retained_original_archive_bytes"] = sum(row.get("retained_bytes") or 0 for row in manifest["requests"])
        manifest["receipt_artifact_group"] = "receipt"
        manifest["elapsed_preservation_seconds"] = max(0, clock() - preservation_started)
        manifest_paths = (receipt / "manifest.json", output / "manifest.json")
        try:
            payload = json_bytes(manifest)
            require(clock() < preservation_deadline, "preservation_wall_deadline")
            require(storage_bytes(receipt) + len(payload) <= 1024 * 1024, "receipt_size_limit")
            for path in manifest_paths:
                exclusive_write(path, payload)
            require(clock() < preservation_deadline, "preservation_wall_deadline")
        except Exception as exc:
            manifest["status"] = "FAILED_CLOSED"
            manifest["finalization_error"] = str(exc) if isinstance(exc, Refusal) else type(exc).__name__
            # Repair an earlier success copy if a later receipt write failed.
            # Raw archives/partial exports are never removed or overwritten.
            for path in manifest_paths:
                try:
                    if clock() < preservation_deadline:
                        with path.open("wb") as stream:
                            stream.write(json_bytes(manifest))
                            stream.flush()
                            os.fsync(stream.fileno())
                except Exception:
                    pass
        finally:
            if preservation_closed is not None:
                preservation_closed()
    return manifest


def deadline_handler(_signum, _frame):
    raise DownloadDeadline("download_wall_deadline")


def preservation_handler(_signum, _frame):
    raise PreservationDeadline("preservation_wall_deadline")


def begin_preservation():
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, preservation_handler)
    signal.setitimer(signal.ITIMER_REAL, LIMITS["preservation_wall_seconds"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--marker", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    env = {key: os.environ.get(key) for key in
           ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_REPOSITORY")}
    try:
        freeze, identity, snapshots = admit(args.freeze, args.marker, env)
        previous_limit = resource.getrlimit(resource.RLIMIT_AS)
        require(previous_limit[0] == resource.RLIM_INFINITY or previous_limit[0] >= LIMITS["address_space_bytes"],
                "preexisting_address_space_limit_too_small")
        resource.setrlimit(resource.RLIMIT_AS, (LIMITS["address_space_bytes"], LIMITS["address_space_bytes"]))
        signal.signal(signal.SIGALRM, deadline_handler)
        signal.setitimer(signal.ITIMER_REAL, LIMITS["download_wall_seconds"])
        try:
            manifest = acquire(args.output, freeze["wheels"], identity, snapshots,
                               network_closed=begin_preservation,
                               preservation_closed=lambda: signal.setitimer(signal.ITIMER_REAL, 0))
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        print(manifest["status"])
        return 0 if manifest["status"] == "EXACT_THREE_ORIGINAL_ARCHIVES" else 1
    except Refusal as exc:
        print("REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
