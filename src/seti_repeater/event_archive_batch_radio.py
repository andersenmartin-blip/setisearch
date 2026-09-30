"""Content-addressed batch publication for the closed v2 terminal archive.

This module never re-runs the archived work.  It binds already-published Git
blobs to a fresh namespace, predicts the complete tree from a frozen parent,
and verifies all immutable bytes with one ``git cat-file --batch`` operation.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from .empty_null_radio import canonical
from .event_archive_remote_radio import git_object, git_sha, safe_path

SOURCE_PREFIX = "results_radio_v2_parent_2026-09-30/live01"
PREFIX = "results_radio_v2_batch_2026-09-30/live01"
SCHEMA = "radio-v2-content-addressed-batch-freeze-v1"


@dataclass(frozen=True)
class Limits:
    files: int = 160
    stored_bytes: int = 6 * 1024 * 1024
    batch_entries: int = 32
    mutation_commits: int = 1
    ref_updates: int = 1
    publication_seconds: int = 300
    audit_seconds: int = 120
    peak_rss_bytes: int = 512 * 1024 * 1024


def _git(root, *args, input=None):
    return subprocess.check_output(["git", *args], cwd=root, input=input)


def _tree(root, commit):
    return git_sha(_git(root, "rev-parse", commit + "^{tree}").decode().strip())


def _ls(root, commit, prefix):
    safe_path(prefix)
    raw = _git(root, "ls-tree", "-rz", "--full-tree", commit, "--", prefix)
    rows = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        left, name = record.split(b"\t", 1)
        mode, kind, sha = left.decode().split()
        path = name.decode()
        if mode != "100644" or kind != "blob" or not path.startswith(prefix + "/"):
            raise ValueError("Only ordinary source blobs below the frozen prefix are allowed")
        safe_path(path)
        rows[path] = git_sha(sha)
    if not rows:
        raise ValueError("Frozen source inventory is empty")
    return rows


def _batch_objects(root, specs):
    request = "".join(spec + "\n" for spec in specs).encode()
    raw = _git(root, "cat-file", "--batch", input=request)
    result = []
    offset = 0
    for spec in specs:
        end = raw.index(b"\n", offset)
        fields = raw[offset:end].split()
        if len(fields) != 3 or fields[1] != b"blob":
            raise ValueError("Missing immutable blob: " + spec)
        size = int(fields[2])
        data = raw[end + 1:end + 1 + size]
        offset = end + size + 2
        if len(data) != size or raw[offset - 1:offset] != b"\n":
            raise ValueError("Malformed grouped Git object response")
        result.append((fields[0].decode(), data))
    if offset != len(raw):
        raise ValueError("Trailing grouped Git object response bytes")
    return result


def inventory(root, commit, prefix=SOURCE_PREFIX):
    root = Path(root)
    commit = git_sha(_git(root, "rev-parse", commit).decode().strip())
    leaves = _ls(root, commit, prefix)
    objects = _batch_objects(root, [commit + ":" + p for p in sorted(leaves)])
    result = {}
    for path, (blob, data) in zip(sorted(leaves), objects):
        if blob != leaves[path] or git_object("blob", data) != blob:
            raise ValueError("Source tree/blob identity differs: " + path)
        result[path] = {"blob": blob, "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()}
    return result


def _target(source_path, source_prefix=SOURCE_PREFIX, target_prefix=PREFIX):
    if not source_path.startswith(source_prefix + "/"):
        raise ValueError("Source path escaped frozen prefix")
    path = target_prefix + source_path[len(source_prefix):]
    safe_path(path)
    return path


def expected_tree(root, parent, files):
    """Use Git's own index/tree implementation as an independent hash oracle."""
    root = Path(root)
    with tempfile.NamedTemporaryFile(prefix="radio-batch-index-", delete=True) as index:
        env = {"GIT_INDEX_FILE": index.name}
        index.close()
        subprocess.run(["git", "read-tree", parent + "^{tree}"], cwd=root, env={**__import__('os').environ, **env}, check=True)
        rows = []
        for path, pin in sorted(files.items()):
            rows.extend(["--cacheinfo", "100644," + git_sha(pin["blob"]) + "," + path])
        subprocess.run(["git", "update-index", "--add", *rows], cwd=root,
                       env={**__import__('os').environ, **env}, check=True)
        return git_sha(subprocess.check_output(["git", "write-tree"], cwd=root,
                       env={**__import__('os').environ, **env}).decode().strip())


def prepare_freeze(root, parent, *, source_commit=None, limits=Limits()):
    root = Path(root)
    parent = git_sha(_git(root, "rev-parse", parent).decode().strip())
    source_commit = git_sha(_git(root, "rev-parse", source_commit or parent).decode().strip())
    if _git(root, "ls-tree", "-r", "--name-only", parent, "--", PREFIX).strip():
        raise ValueError("Fresh immutable target namespace required")
    source = inventory(root, source_commit)
    target = {_target(path): {**pin, "source_path": path} for path, pin in source.items()}
    total = sum(pin["bytes"] for pin in target.values())
    if len(target) > limits.files or total > limits.stored_bytes:
        raise ValueError("Frozen archive exceeds file/stored-byte allocation")
    batches = []
    paths = sorted(target)
    for index in range(0, len(paths), limits.batch_entries):
        batch = paths[index:index + limits.batch_entries]
        batches.append({"index": len(batches), "paths": batch,
                        "entries": len(batch), "bytes": sum(target[p]["bytes"] for p in batch)})
    freeze = {
        "schema": SCHEMA, "mode": "ENGINEERING_ONLY", "repository": "andersenmartin-blip/setisearch",
        "branch": "m43-support-qualification", "parent": parent, "parent_tree": _tree(root, parent),
        "source_commit": source_commit, "source_prefix": SOURCE_PREFIX, "target_prefix": PREFIX,
        "files": target, "file_count": len(target), "stored_bytes": total,
        "batches": batches, "expected_tree": expected_tree(root, parent, target),
        "limits": asdict(limits), "source_cat_file_batch_operations": 1,
        "mutation_commits": 1, "ref_updates": 1, "force": False,
        "exact_original_bytes": True, "reuses_existing_git_blobs": True,
        "execution_restart_authorized": False, "scientific_admission_authorized": False,
        "new_random_values": 0, "new_receiver_measurements": 0, "new_telescope_reads": 0,
    }
    freeze["inventory_sha256"] = hashlib.sha256(canonical(target)).hexdigest()
    return freeze


def validate_freeze(root, freeze, *, require_parent=None):
    if freeze.get("schema") != SCHEMA or freeze.get("mode") != "ENGINEERING_ONLY":
        raise ValueError("Exact engineering batch freeze required")
    if freeze.get("source_prefix") != SOURCE_PREFIX or freeze.get("target_prefix") != PREFIX:
        raise ValueError("Frozen source/target namespace changed")
    parent = git_sha(freeze["parent"])
    if require_parent is not None and parent != git_sha(require_parent):
        raise ValueError("Frozen parent conflicts with current branch")
    limits = Limits(**freeze["limits"])
    if limits != Limits():
        raise ValueError("Resource limits changed")
    actual = prepare_freeze(root, parent, source_commit=freeze["source_commit"], limits=limits)
    if canonical(actual) != canonical(freeze):
        raise ValueError("Prospective freeze or source bytes changed")
    return actual


def verify_readback(root, commit, freeze):
    """Verify every target in one grouped immutable object read."""
    root = Path(root)
    commit = git_sha(_git(root, "rev-parse", commit).decode().strip())
    if _tree(root, commit) != freeze["expected_tree"]:
        raise ValueError("Published commit tree differs from frozen tree")
    paths = sorted(freeze["files"])
    objects = _batch_objects(root, [commit + ":" + p for p in paths])
    total = 0
    for path, (blob, data) in zip(paths, objects):
        pin = freeze["files"][path]
        if (blob != pin["blob"] or len(data) != pin["bytes"] or
                hashlib.sha256(data).hexdigest() != pin["sha256"] or
                git_object("blob", data) != blob):
            raise ValueError("Immutable batch readback differs: " + path)
        total += len(data)
    return {"commit": commit, "tree": freeze["expected_tree"], "files": len(paths),
            "stored_bytes": total, "git_cat_file_batch_operations": 1,
            "exact_original_bytes": True, "scientific_admission_authorized": False}

