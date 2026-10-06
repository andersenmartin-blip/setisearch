"""One administrative copy operation after the immutable K source readback."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import stat
import sys
import time

HERE = Path(__file__).resolve().parent


def load_component():
    spec = importlib.util.spec_from_file_location("k_recovery", HERE / "recovery.py")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--new-output", required=True)
    parser.add_argument("--freeze-sha256", required=True)
    args = parser.parse_args()
    # Hash component bytes before importing even this stdlib-only component.
    if (HERE / "SOURCE_FREEZE.json").is_symlink() or not stat.S_ISREG((HERE / "SOURCE_FREEZE.json").lstat().st_mode):
        raise ValueError("ordinary freeze required")
    if (HERE / "SOURCE_FREEZE.json").stat().st_size > 65536:
        raise ValueError("bounded freeze required")
    freeze_raw = (HERE / "SOURCE_FREEZE.json").read_bytes()
    if hashlib.sha256(freeze_raw).hexdigest() != args.freeze_sha256:
        raise ValueError("exact independently read-back source freeze required")
    freeze = json.loads(freeze_raw)
    if freeze["status"] != "ADMINISTRATIVE_COPY_ONLY_NO_NATIVE_AUTHORITY":
        raise ValueError("inert administrative source freeze required")
    source_read = len(freeze_raw)
    for name, expected in freeze["source_files"].items():
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("flat source member required")
        path = HERE / name
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("ordinary source member required")
        if path.stat().st_size != expected["bytes"] or expected["bytes"] > 2 * 1024 ** 2:
            raise ValueError("bounded original source member required")
        raw = path.read_bytes(); source_read += len(raw)
        if {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} != expected:
            raise ValueError("source freeze member differs")
    if not {"recovery.py", "run_recovery.py"} <= set(freeze["source_files"]):
        raise ValueError("both executable source components must be frozen")
    component = load_component()
    component.same(freeze["authority_commit"], component.AUTHORITY)
    component.same(freeze["limits"], component.LIMITS)
    component.same(freeze["sources"], component.FIXED_SOURCES)
    manifest = Path(args.manifest)
    component.ordinary_path(manifest)
    if not stat.S_ISREG(manifest.lstat().st_mode) or manifest.stat().st_size != component.MANIFEST_PIN["bytes"]:
        raise ValueError("original manifest size differs")
    raw = manifest.read_bytes(); source_read += len(raw)
    rows = component.expected_rows(raw)
    for name, maximum in ((resource.RLIMIT_CPU, component.LIMITS["cpu_seconds"]),
                          (resource.RLIMIT_AS, component.LIMITS["address_space_bytes"]),
                          (resource.RLIMIT_FSIZE, component.LIMITS["per_file_bytes"]),
                          (resource.RLIMIT_NOFILE, component.LIMITS["descriptor_limit"])):
        resource.setrlimit(name, (maximum, maximum))
    started = time.monotonic()
    root = Path(args.new_output)
    result = component.recover(rows, component.FIXED_SOURCES, root)
    review = component.verify_candidate(root, result)
    files = []; logical = allocated = 0
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode): continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise component.Refusal("ordinary single-link retained artifact required")
        logical += info.st_size; allocated += info.st_blocks * 512
        files.append({"path": str(path.relative_to(root)), "bytes": info.st_size,
                      "mode": stat.S_IMODE(info.st_mode)})
    elapsed = time.monotonic() - started
    result_body = (root / "RESULT.json").read_bytes()
    total_read = source_read + result["read_bytes"] + review["read_bytes"] + len(result_body)
    if (total_read > component.LIMITS["read_bytes"] or elapsed > component.LIMITS["wall_seconds"]
            or logical > component.LIMITS["artifact_bytes"] or allocated > component.LIMITS["artifact_bytes"]):
        raise component.Refusal("final administrative envelope differs")
    receipt = {"schema": "radio-K-administrative-review-v1", "result_pin": component.pin(result_body),
               "independent_review": review, "source_freeze_pin": component.pin(freeze_raw),
               "authority_commit": component.AUTHORITY, "source_and_manifest_reads": source_read,
               "explicit_read_bytes_before_review_receipt": total_read,
               "artifact_logical_bytes_before_review_receipt": logical,
               "artifact_allocated_bytes_before_review_receipt": allocated,
               "measured_copy_and_review_seconds": elapsed, "retained_files_before_review_receipt": files,
               "controller_peak_rss_kib_before_review_receipt": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "enforced_rlimits": {"cpu_seconds": component.LIMITS["cpu_seconds"],
                                    "address_space_bytes": component.LIMITS["address_space_bytes"],
                                    "file_bytes": component.LIMITS["per_file_bytes"],
                                    "descriptors": component.LIMITS["descriptor_limit"]},
               "controller_mode": "isolated stdlib only; recovered target never executed",
               "runtime_qualified": False, "codec_allocation": False, "science_allocation": False}
    body = component.canonical(receipt)
    if logical + len(body) > component.LIMITS["artifact_bytes"]:
        raise component.Refusal("review receipt artifact cap")
    fd = os.open(root / "REVIEW.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        if os.write(fd, body) != len(body): raise component.Refusal("short review receipt write")
        os.fsync(fd)
    finally: os.close(fd)
    print(json.dumps({"status": result["status"], "copied_files": result["copied_files"],
                      "copied_original_bytes": result["copied_original_bytes"],
                      "missing_or_mismatched": result["missing_or_mismatched"],
                      "independent_review": review["status"], "seconds": elapsed,
                      "output": str(root)}))


if __name__ == "__main__":
    main()
