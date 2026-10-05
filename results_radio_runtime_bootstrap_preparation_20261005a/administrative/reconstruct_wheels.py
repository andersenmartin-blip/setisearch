#!/usr/bin/env python3
"""Reconstruct preserved wheel bytes without installing or importing packages.

The immutable preservation manifest's raw SHA-256 must be supplied externally.
All part raw and encoded pins remain distinct. Outputs are exclusive; failures
retain partial files and are never automatically retried.
"""
import argparse
import base64
import hashlib
import json
import os
import stat
import sys

NOFOLLOW = os.O_NOFOLLOW | os.O_CLOEXEC
MAX_MANIFEST = 16777216
MAX_PART = 500001
MAX_ARCHIVE = 134217728


class ReconstructionError(Exception):
    pass


def relative(value):
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or "\x00" in value:
        raise ReconstructionError("unsafe relative path")
    if any(p in ("", ".", "..") for p in value.split("/")):
        raise ReconstructionError("unsafe relative path component")
    return value


def ident(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_blocks)


def open_absolute_directory(path):
    if not os.path.isabs(path) or os.path.normpath(path) != path:
        raise ReconstructionError("canonical absolute directory required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
    guards = [(fd, None, None, ident(os.fstat(fd))[:3])]
    try:
        for name in path.split("/")[1:]:
            if not name:
                continue
            named = os.stat(name, dir_fd=fd, follow_symlinks=False)
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
            held = os.fstat(child)
            if ident(named) != ident(held):
                os.close(child)
                raise ReconstructionError("ancestor substituted")
            guards.append((child, fd, name, ident(held)[:3]))
            fd = child
        return fd, guards
    except BaseException:
        for item in reversed(guards):
            os.close(item[0])
        raise


def check_guards(guards):
    for fd, parent, name, original in guards:
        if ident(os.fstat(fd))[:3] != original:
            raise ReconstructionError("held ancestor substituted")
        if parent is not None and ident(os.stat(name, dir_fd=parent, follow_symlinks=False))[:3] != original:
            raise ReconstructionError("named ancestor substituted")


def read_relative(root, path, cap):
    parts = relative(path).split("/")
    fd = os.dup(root)
    guards = [(fd, None, None, ident(os.fstat(fd))[:3])]
    try:
        for name in parts[:-1]:
            named = os.stat(name, dir_fd=fd, follow_symlinks=False)
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
            if ident(named) != ident(os.fstat(child)):
                os.close(child)
                raise ReconstructionError("part parent substituted")
            guards.append((child, fd, name, ident(os.fstat(child))[:3]))
            fd = child
        named = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
        if not stat.S_ISREG(named.st_mode) or named.st_nlink != 1 or named.st_size > cap:
            raise ReconstructionError("part file type/link/size refused")
        source = os.open(parts[-1], os.O_RDONLY | NOFOLLOW, dir_fd=fd)
        try:
            original = ident(os.fstat(source))
            if original != ident(named):
                raise ReconstructionError("part file substituted")
            raw = bytearray()
            while len(raw) < named.st_size:
                chunk = os.read(source, min(65536, named.st_size - len(raw)))
                if not chunk:
                    raise ReconstructionError("part file truncated")
                raw.extend(chunk)
            if os.read(source, 1) or ident(os.fstat(source)) != original or ident(os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)) != original:
                raise ReconstructionError("part file changed")
            check_guards(guards)
            return bytes(raw)
        finally:
            os.close(source)
    finally:
        for held_fd, _, _, _ in reversed(guards):
            os.close(held_fd)


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()}


def write_all(fd, raw):
    view = memoryview(raw)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise ReconstructionError("output write made no progress")
        view = view[count:]


def reconstruct(args):
    repository, repo_guards = open_absolute_directory(args.repository_root)
    output_guards = []
    parent_guards = []
    try:
        raw_manifest = read_relative(repository, args.manifest, MAX_MANIFEST)
        if hashlib.sha256(raw_manifest).hexdigest() != args.manifest_sha256:
            raise ReconstructionError("external immutable manifest SHA mismatch")
        manifest = json.loads(raw_manifest)
        if manifest.get("schema") != "radio-runtime-package-bootstrap-lossless-preservation-v1":
            raise ReconstructionError("preservation manifest schema mismatch")
        wheels = manifest["expected_original_wheels"]
        if len(wheels) != 3 or len({w["filename"] for w in wheels}) != 3:
            raise ReconstructionError("three distinct original wheels required")
        originals = {w["filename"]: w for w in wheels}
        archives = [p for p in manifest["payloads"] if p["purpose"] == "wheel-archive"]
        if len(archives) > 3:
            raise ReconstructionError("archive payload cohort exceeds original three")
        if not args.allow_partial and (len(archives) != 3 or any(not p["matches_original"] for p in archives)):
            raise ReconstructionError("three complete exact original archives required")
        if not args.allow_partial and {p["expected_original"]["filename"] for p in archives} != set(originals):
            raise ReconstructionError("payload filename cohort differs from frozen originals")
        if not os.path.isabs(args.output) or os.path.normpath(args.output) != args.output or args.output == "/":
            raise ReconstructionError("canonical absolute output required")
        if args.output == args.repository_root or args.repository_root.startswith(args.output + "/"):
            raise ReconstructionError("output cannot contain repository inputs")
        parent_path, name = os.path.split(args.output)
        parent, parent_guards = open_absolute_directory(parent_path)
        os.mkdir(name, 0o700, dir_fd=parent)  # exclusive; no resume or overwrite
        os.fsync(parent)
        output, output_guards = open_absolute_directory(args.output)
        names = set()
        receipts = []
        for payload in sorted(archives, key=lambda p: p["root_relative_path"]):
            expected = payload["expected_original"]
            filename = relative(expected["filename"])
            if "/" in filename or filename in names:
                raise ReconstructionError("archive output basename duplicate/unsafe")
            if filename not in originals or expected != originals[filename]:
                raise ReconstructionError("payload expected-original row differs from frozen original")
            if payload["root_relative_path"] != "wheelhouse/" + filename:
                raise ReconstructionError("archive source path differs from original wheelhouse basename")
            matches_original = payload["raw_bytes"] == expected["bytes"] and payload["raw_sha256"] == expected["sha256"]
            if type(payload["matches_original"]) is not bool or payload["matches_original"] != matches_original:
                raise ReconstructionError("payload original-identity flag contradicts raw pins")
            names.add(filename)
            if payload["raw_bytes"] > MAX_ARCHIVE or payload["raw_bytes"] < 0:
                raise ReconstructionError("archive output size cap exceeded")
            if payload["encoding"] != "canonical-base64-plus-single-newline" or payload["raw_segment_bytes"] != 374997:
                raise ReconstructionError("archive part format mismatch")
            target = os.open(filename, os.O_RDWR | os.O_CREAT | os.O_EXCL | NOFOLLOW, 0o644, dir_fd=output)
            os.fchmod(target, 0o644)
            target_start = os.fstat(target)
            if not stat.S_ISREG(target_start.st_mode) or target_start.st_nlink != 1 or target_start.st_size != 0:
                os.close(target)
                raise ReconstructionError("exclusive output is not an empty sole-link regular file")
            sha = hashlib.sha256()
            git = hashlib.sha1(b"blob " + str(payload["raw_bytes"]).encode("ascii") + b"\0")
            offset = 0
            try:
                for index, part in enumerate(payload["parts"]):
                    if part["index"] != index or part["offset"] != offset:
                        raise ReconstructionError("part order/gap/overlap refused")
                    count = min(374997, payload["raw_bytes"] - offset)
                    if part["raw_bytes"] != count or count <= 0:
                        raise ReconstructionError("part declared raw extent mismatch")
                    stored = part["encoded"]
                    encoded = read_relative(repository, stored["repository_path"], MAX_PART)
                    if pin(encoded) != {k: stored[k] for k in ("bytes", "sha256", "git_blob")}:
                        raise ReconstructionError("encoded representation pin mismatch")
                    if not encoded.endswith(b"\n") or encoded.endswith(b"\n\n"):
                        raise ReconstructionError("encoded part newline is not canonical")
                    decoded = base64.b64decode(encoded[:-1], validate=True)
                    if base64.b64encode(decoded) + b"\n" != encoded:
                        raise ReconstructionError("encoded part base64 is not canonical")
                    if len(decoded) != count or hashlib.sha256(decoded).hexdigest() != part["raw_sha256"]:
                        raise ReconstructionError("decoded raw part pin mismatch")
                    write_all(target, decoded)
                    sha.update(decoded)
                    git.update(decoded)
                    offset += count
                if offset != payload["raw_bytes"] or sha.hexdigest() != payload["raw_sha256"] or git.hexdigest() != payload["raw_git_blob"]:
                    raise ReconstructionError("reconstructed archive raw length/hash/Git blob mismatch")
                if payload["matches_original"] and (offset != expected["bytes"] or sha.hexdigest() != expected["sha256"]):
                    raise ReconstructionError("reconstructed original archive identity mismatch")
                os.fchmod(target, 0o644)
                os.fsync(target)
                completed = os.fstat(target)
                if (completed.st_dev, completed.st_ino, completed.st_mode, completed.st_nlink, completed.st_size) != (target_start.st_dev, target_start.st_ino, target_start.st_mode, 1, offset):
                    raise ReconstructionError("held output identity/type/link/size changed")
                if ident(os.stat(filename, dir_fd=output, follow_symlinks=False)) != ident(completed):
                    raise ReconstructionError("named output does not match held file")
                os.lseek(target, 0, os.SEEK_SET)
                final_sha = hashlib.sha256()
                final_git = hashlib.sha1(b"blob " + str(offset).encode("ascii") + b"\0")
                readback_bytes = 0
                while readback_bytes < offset:
                    returned = os.read(target, min(65536, offset - readback_bytes))
                    if not returned:
                        raise ReconstructionError("complete output readback truncated")
                    readback_bytes += len(returned)
                    final_sha.update(returned)
                    final_git.update(returned)
                if os.read(target, 1) or final_sha.hexdigest() != payload["raw_sha256"] or final_git.hexdigest() != payload["raw_git_blob"]:
                    raise ReconstructionError("complete final-output raw hash readback mismatch")
                if ident(os.fstat(target)) != ident(completed) or ident(os.stat(filename, dir_fd=output, follow_symlinks=False)) != ident(completed):
                    raise ReconstructionError("held/named output changed during full readback")
            finally:
                os.close(target)
            os.fsync(output)
            receipts.append({"filename": filename, "bytes": offset, "sha256": sha.hexdigest(),
                             "git_blob": git.hexdigest(), "matches_original": matches_original,
                             "full_final_output_hash_readback_verified": True,
                             "held_named_output_identity_stable": True})
        for guards in (repo_guards, parent_guards, output_guards):
            check_guards(guards)
        report = {"schema": "radio-runtime-package-bootstrap-wheel-reconstruction-v1",
                  "bootstrap_identity": manifest["bootstrap_identity"], "manifest_sha256": args.manifest_sha256,
                  "archives": receipts, "all_three_exact_originals": len(receipts) == 3 and all(r["matches_original"] for r in receipts),
                  "administrative_installer_invocations": 0, "administrative_native_package_imports": 0, "scientific_authority": False,
                  "accounting_scope": "separate administrative publication readback, outside one-shot bootstrap counters"}
        raw = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        fd = os.open("reconstruction-receipt.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW, 0o644, dir_fd=output)
        try:
            write_all(fd, raw)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(output)
        print(json.dumps(report, sort_keys=True))
        return 0
    finally:
        for guards in (output_guards, parent_guards, repo_guards):
            for fd, _, _, _ in reversed(guards):
                os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository-root", "manifest", "manifest-sha256", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--allow-partial", action="store_true", help="retain failed acquisition bytes; default requires all three exact originals")
    return reconstruct(parser.parse_args())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("ADMINISTRATIVE_RECONSTRUCTION_FAILED " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
