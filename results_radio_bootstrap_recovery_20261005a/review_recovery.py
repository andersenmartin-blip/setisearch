"""Administrative, read-only review of interrupted bootstrap-result publication.

Never invokes acquisition, the gate, an installer or a native scientific import.
Historical inode custody and current restored-content observations stay distinct.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


def identities(raw):
    return len(raw), hashlib.sha256(raw).hexdigest(), hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def stable_raw(path):
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read()
        after = os.fstat(fd)
    finally:
        os.close(fd)
    named = path.lstat()
    keys = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink,
                      s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    assert keys(before) == keys(opened) == keys(after) == keys(named)
    return raw, before


def review(repo, meta, commit, root):
    assert git(repo, "show", "-s", "--format=%P", commit).decode().strip() == meta["base_commit"]
    assert git(repo, "show", "-s", "--format=%T", commit).decode().strip() == meta["expected_tree"]
    publication = []
    for row in meta["files"]:
        raw = git(repo, "show", commit + ":" + row["path"])
        assert identities(raw) == (row["bytes"], row["sha256"], row["git_blob"]), row["path"]
        member = git(repo, "ls-tree", commit, "--", row["path"]).decode().strip()
        assert member == f'{row["mode"]} blob {row["git_blob"]}\t{row["path"]}'
        publication.append({k: row[k] for k in ("path", "bytes", "sha256", "git_blob", "mode")})
    prefix = "results_radio_runtime_bootstrap_preparation_20261005a/actual/"
    manifest = json.loads(git(repo, "show", commit + ":" + prefix + "preservation-manifest.json"))
    entries = manifest["before"]["entries"]
    expected_names = {e["path"] for e in entries}

    def inventory():
        names = {"."}
        for parent, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                p = Path(parent) / name
                assert not p.is_symlink()
                names.add(p.relative_to(root).as_posix())
        assert names == expected_names
        return {name: (root / name).lstat() for name in names}

    before = inventory()
    mismatched_historical_inodes = 0
    files = 0
    raw_total = 0
    for entry in entries:
        p = root / entry["path"]
        observed = before[entry["path"]]
        old = entry["identity"]
        if (observed.st_dev, observed.st_ino) != (old["device"], old["inode"]):
            mismatched_historical_inodes += 1
        assert stat.S_IMODE(observed.st_mode) == old["mode"]
        if entry["kind"] == "directory":
            assert stat.S_ISDIR(observed.st_mode)
            continue
        raw, _ = stable_raw(p)
        assert identities(raw) == (entry["bytes"], entry["sha256"], entry["git_blob"]), entry["path"]
        files += 1
        raw_total += len(raw)
        preservation = entry["preservation"]
        if preservation["kind"] == "installer-basis-reference":
            encoded = git(repo, "show", manifest["input_pins"]["prepared_commit"] + ":" + preservation["repository_path"]) if "prepared_commit" in manifest["input_pins"] else git(repo, "show", meta["base_commit"] + ":" + preservation["repository_path"])
            decoded = base64.b64decode(encoded.strip(), validate=True) if preservation["stored_encoding"] == "base64" else encoded
            assert decoded == raw
        elif preservation["kind"] == "exact-utf8-file":
            assert git(repo, "show", commit + ":" + preservation["stored"]["repository_path"]) == raw
    for payload in manifest["payloads"]:
        pieces = []
        for part in payload["parts"]:
            encoded = git(repo, "show", commit + ":" + part["encoded"]["repository_path"])
            piece = base64.b64decode(encoded.strip(), validate=True)
            assert len(piece) == part["raw_bytes"] and hashlib.sha256(piece).hexdigest() == part["raw_sha256"]
            pieces.append(piece)
        decoded = b"".join(pieces)
        assert identities(decoded) == (payload["raw_bytes"], payload["raw_sha256"], payload["raw_git_blob"])
        assert decoded == (root / payload["root_relative_path"]).read_bytes()
    after = inventory()
    stable = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    assert all(stable(before[k]) == stable(after[k]) for k in before)
    report = json.loads(git(repo, "show", commit + ":" + prefix + "retained/supervisor-result.json"))
    assert report["status"] == "CLOSED_FAILED" and report["pip_child"] is None
    assert report["engineering_reservation_spent"] is True
    assert report["telescope_reads"] == report["native_package_imports"] == report["scientific_cases_run"] == 0
    return {
        "schema": "bootstrap-interrupted-publication-recovery-review-v1",
        "date": "2026-10-05", "result_commit": commit,
        "result_tree": meta["expected_tree"], "sole_parent": meta["base_commit"],
        "publication_files": publication, "publication_file_count": len(publication),
        "publication_raw_bytes": sum(p["bytes"] for p in publication),
        "restored_root": str(root), "restored_regular_files": files,
        "restored_regular_bytes": raw_total, "restored_directories": len(entries) - files,
        "restored_content_and_mode_match_historical_pins": True,
        "current_before_after_stable": True,
        "historical_inode_mismatch_count": mismatched_historical_inodes,
        "current_inode_custody_is_original_run_custody": False,
        "historical_metadata_preserved_without_rewrite": True,
        "actual_bootstrap_reinvocations": 0, "new_acquisition_attempts": 0,
        "new_installers": 0, "native_imports": 0, "scientific_authority": False,
        "verdict": "CLOSED_FAILURE_RECOVERED_CONTENT_VERIFIED_AND_FULL_IMMUTABLE_RESULT_READBACK"
    }


if __name__ == "__main__":
    repo, meta_path, commit, root = sys.argv[1:]
    result = review(Path(repo), json.loads(Path(meta_path).read_bytes()), commit, Path(root))
    print(json.dumps(result, indent=2, sort_keys=True))
