"""Administrative source/fixture evidence only. Never executes a native target."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AUTHORITY = "71d0073faac7cd1a487e950f28a6f74b7daf75ab"
INPUTS = (
    "results_radio_codec12_execution_preparation_20261006i/codec12_control.py",
    "results_radio_codec12_execution_preparation_20261006i/contract.py",
    "results_radio_codec12_execution_preparation_20261006i/SOURCE_FREEZE.json",
    "results_radio_codec12_execution_preparation_20261006i/PUBLIC_READBACK.json",
    "results_radio_codec12_preparation_20261006h/PLAN.json",
    "results_radio_codec12_preparation_20261006h/PROTOCOL.md",
    "results_radio_codec16_control_20261006g/native/NATIVE_REVIEW.md",
    "results_radio_codec16_control_20261006g/outer/CONTRACT.md",
    "results_radio_codec16_control_20261006g/outer/supervisor/leaf_guard.c",
    "results_radio_codec16_control_20261006g/outer/supervisor/proc_custody.py",
    "results_radio_codec16_control_20261006g/runtime-restoration-review.md",
)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def write(name, raw):
    with (HERE / name).open("xb") as handle:
        handle.write(raw)


def signature(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns]


def observe_file(name):
    path = Path(name)
    try:
        named = os.lstat(path)
    except FileNotFoundError as exc:
        return {"declared_path": name, "presence": "ABSENT", "errno": exc.errno,
                "no_substitution_or_restoration": True}
    resolved = path.resolve(strict=True)
    fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 64 * 1024 ** 2:
            raise ValueError("administrative input bound/kind")
        total = 0
        digest = hashlib.sha256()
        while True:
            raw = handle.read(65536)
            if not raw: break
            total += len(raw)
            if total > before.st_size: raise ValueError("file grew during read")
            digest.update(raw)
        after = os.fstat(handle.fileno())
    if (total != before.st_size or signature(before) != signature(after)
            or signature(os.stat(resolved, follow_symlinks=False)) != signature(before)
            or signature(os.lstat(path)) != signature(named) or path.resolve(strict=True) != resolved):
        raise ValueError("administrative input identity drift")
    return {"declared_path": name, "resolved_path": str(resolved), "presence": "PRESENT_READ_ONLY",
            "declared_path_is_symlink": stat.S_ISLNK(named.st_mode), "held_file_identity": signature(before),
            "bytes": total, "sha256": digest.hexdigest(), "executed": False,
            "collector_capability_or_runtime_qualification": False}


def main():
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != AUTHORITY:
        raise ValueError("exact source continuation required")
    inputs = []
    for path in INPUTS:
        raw = subprocess.check_output(["git", "show", AUTHORITY + ":" + path], cwd=ROOT)
        inputs.append({"path": path, **pin(raw)})
    write("CONTEXT_INPUT_MANIFEST.json", canonical({"schema": "loader-J-context-inputs-v1",
          "authority_commit": AUTHORITY, "files": inputs, "bytes": sum(row["bytes"] for row in inputs),
          "historical_inputs_are_context_not_current_runtime": True}))
    old = "/workspace/scratch/da6462abff17/radio-offline-runtime-materialization-20261005c/installer/venv/bin/python"
    observations = [observe_file(old), observe_file("/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python"),
                    observe_file("/usr/bin/strace"), observe_file("/usr/bin/readelf")]
    write("CURRENT_RUNTIME_BOUNDARY.json", canonical({"schema": "loader-J-current-boundary-v1",
          "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "status": "CURRENT_CANONICAL_RUNTIME_ABSENT" if observations[0]["presence"] == "ABSENT" else "PRESENT_NOT_QUALIFIED",
          "observations": observations, "administrative_file_bytes_read": sum(row.get("bytes", 0) for row in observations),
          "native_target_executions": 0, "native_package_imports": 0, "kernel_traces_collected": 0,
          "runtime_restorations_or_installs": 0, "activation_or_allocation_created": False,
          "continuous_custody_or_runtime_qualified": False}))
    spec = importlib.util.spec_from_file_location("loader_J_fixtures", HERE / "test_loader_lifetime.py")
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    events = fixtures.bodies(fixtures.fixture())
    receipt = fixtures.checked(fixtures.fixture())
    write("FIXTURE.events.jsonl", b"".join(events))
    write("FIXTURE.receipt.json", canonical({"manufactured_fixture_not_actual_observation": True,
                                             "invented_paths_pins_and_process_identity": True,
                                             "receipt": receipt}))
    print(json.dumps({"context_inputs": len(inputs), "context_bytes": sum(row["bytes"] for row in inputs),
                      "fixture_events": len(events), "transient_generations_retained": receipt["transient_generations_retained"],
                      "old_runtime_presence": observations[0]["presence"], "native_target_executions": 0}))


if __name__ == "__main__":
    main()
