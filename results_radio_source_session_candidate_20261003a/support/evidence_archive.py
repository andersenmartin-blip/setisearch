#!/usr/bin/env python3
"""Bounded, lossless, content-deduplicated evidence tar.zst and safe restoration.

Requires Python 3.10+ and zstandard. Never imports or executes evidence files.
Archive equality concerns file bytes, not source inode, sparse allocation, path
lifetime, acquisition success, telescope provenance, or scientific qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import resource
import shutil
import stat
import tarfile
import tempfile

import zstandard as zstd

MIB = 1024 * 1024
BLOCK = MIB
SOURCE_SCHEMA = "seti-lossless-evidence-source-manifest-v1"
ARCHIVE_SCHEMA = "seti-lossless-evidence-archive-v1"
ALLOWED_DIRS = (
    "acquisition-candidate", "frozen-project", "receiver-candidate",
    "archive-support",
)
OBSERVATION_PREFIXES = ("acquisition-observation-", "receiver-observation-", "handoff-observation-")


def canonical_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_all(file, data):
    view = memoryview(data)
    while view:
        written = file.write(view)
        if not isinstance(written, int) or written <= 0 or written > len(view):
            raise OSError("file writer made no valid progress")
        view = view[written:]


def write_verified_file(path, data):
    with path.open("xb") as file:
        write_all(file, data)
        file.flush()
        os.fsync(file.fileno())
    digest, signature = hash_file(path)
    if digest != sha(data) or signature[2] != len(data):
        raise OSError("written file differs from intended bytes: " + str(path))


def enforce_memory_limit(limit_mib):
    if not 128 <= limit_mib <= 512:
        raise ValueError("memory cap must be between 128 and 512 MiB")
    limit = limit_mib * MIB
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY:
        limit = min(limit, hard)
    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))


def safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("invalid relative path")
    p = PurePosixPath(value)
    if p.is_absolute() or value != p.as_posix() or any(
        x in ("", ".", "..") or x.startswith(".") or ":" in x for x in p.parts
    ):
        raise ValueError("unsafe relative path: " + repr(value))
    return p


def file_signature(p):
    s = p.lstat()
    if not stat.S_ISREG(s.st_mode):
        raise ValueError("only regular source files are allowed: " + str(p))
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def hash_file(p):
    before = file_signature(p)
    h = hashlib.sha256()
    with p.open("rb") as f:
        while b := f.read(BLOCK):
            h.update(b)
    if before != file_signature(p):
        raise RuntimeError("source changed while hashing: " + str(p))
    return h.hexdigest(), before


def inventory(root, output=None, extra_dirs=()):
    """Known owned directories and visible root files; no unrelated directories."""
    allowed = set(ALLOWED_DIRS) | set(extra_dirs)
    found = []
    for top in sorted(root.iterdir()):
        if top.name.startswith(".") or top.name in ("__pycache__", "publishing", "publication"):
            continue
        if output and (top == output or output in top.parents):
            continue
        if top.is_symlink():
            raise ValueError("source symlinks are prohibited: " + str(top))
        if top.is_file():
            found.append(top)
        elif top.is_dir() and (top.name in allowed or top.name.startswith(OBSERVATION_PREFIXES)):
            for directory, dirs, files in os.walk(top, followlinks=False):
                parent = Path(directory)
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "__pycache__")
                kept = []
                for d in dirs:
                    p = parent / d
                    if output and (p == output or output in p.parents):
                        continue
                    if p.is_symlink():
                        raise ValueError("source directory symlinks are prohibited: " + str(p))
                    kept.append(d)
                dirs[:] = kept
                for name in sorted(files):
                    if not name.startswith("."):
                        p = parent / name
                        file_signature(p)
                        found.append(p)
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


class PartWriter:
    def __init__(self, directory, chunk_bytes, cap_bytes):
        self.directory, self.chunk_bytes, self.cap_bytes = directory, chunk_bytes, cap_bytes
        self.parts = []
        self.total = 0
        self.full_hash = hashlib.sha256()
        self.current = None
        self.part_bytes = 0
        self.part_hash = None

    def _finish(self):
        if self.current is None:
            return
        path = Path(self.current.name)
        self.current.flush()
        os.fsync(self.current.fileno())
        self.current.close()
        digest, signature = hash_file(path)
        if signature[2] != self.part_bytes or digest != self.part_hash.hexdigest():
            raise OSError("written archive part differs from intended bytes: " + str(path))
        self.parts.append({"filename": self.current.name.rsplit("/", 1)[-1],
                           "bytes": self.part_bytes, "sha256": self.part_hash.hexdigest()})
        self.current = None

    def write(self, data):
        if self.total + len(data) > self.cap_bytes:
            raise RuntimeError("compressed archive exceeds its fixed byte cap")
        view = memoryview(data)
        while view:
            if self.current is None:
                self.current = (self.directory / f"evidence.tar.zst.part{len(self.parts):04d}").open("xb")
                self.part_bytes, self.part_hash = 0, hashlib.sha256()
            amount = min(len(view), self.chunk_bytes - self.part_bytes)
            piece, view = view[:amount], view[amount:]
            write_all(self.current, piece)
            self.part_hash.update(piece)
            self.full_hash.update(piece)
            self.part_bytes += amount
            self.total += amount
            if self.part_bytes == self.chunk_bytes:
                self._finish()
        return len(data)

    def flush(self):
        if self.current:
            self.current.flush()

    def close(self):
        self._finish()


class CheckedSource:
    def __init__(self, path, expected_digest, signature):
        if file_signature(path) != signature:
            raise RuntimeError("source changed before archiving: " + str(path))
        self.path, self.expected_digest, self.signature = path, expected_digest, signature
        self.file = path.open("rb")
        self.digest = hashlib.sha256()
        self.count = 0

    def read(self, size=-1):
        data = self.file.read(size)
        self.digest.update(data)
        self.count += len(data)
        return data

    def close_verified(self):
        self.file.close()
        if (self.count != self.signature[2] or self.digest.hexdigest() != self.expected_digest
                or file_signature(self.path) != self.signature):
            raise RuntimeError("source changed during archiving: " + str(self.path))


def tar_header(name, size):
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o644
    info.mtime = info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def read_exact(reader, amount):
    pieces, remaining = [], amount
    while remaining:
        data = reader.read(min(BLOCK, remaining))
        if not data:
            raise ValueError("truncated tar stream")
        pieces.append(data)
        remaining -= len(data)
    return b"".join(pieces)


def strict_header(reader):
    data = read_exact(reader, 512)
    if data == bytes(512):
        return None
    member = tarfile.TarInfo.frombuf(data, encoding="utf-8", errors="strict")
    # Parsing one raw USTAR header prevents implicit PAX/long-name extensions,
    # links, devices, or oversized extension payloads from being processed.
    if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE):
        raise ValueError("archive member is not an ordinary regular file")
    return member


def consume_padding(reader, size):
    padding = (-size) % 512
    if padding and read_exact(reader, padding) != bytes(padding):
        raise ValueError("nonzero tar member padding")


def build(args):
    enforce_memory_limit(args.memory_mib)
    root, output = Path(args.root).resolve(), Path(args.output).resolve()
    if output.exists() or output == root:
        raise ValueError("archive output must be a new directory")
    for name in args.include_dir:
        if len(safe_relative(name).parts) != 1:
            raise ValueError("--include-dir must name a visible top-level directory")
    files = inventory(root, output, args.include_dir)
    if not files:
        raise ValueError("source inventory is empty")
    entries, blobs, signatures = [], {}, {}
    for path in files:
        digest, signature = hash_file(path)
        relative = path.relative_to(root).as_posix()
        safe_relative(relative)
        mode = stat.S_IMODE(path.stat().st_mode) & 0o777
        entry = {"path": relative, "bytes": signature[2], "sha256": digest, "mode": mode}
        entries.append(entry)
        signatures[relative] = signature
        if digest in blobs and blobs[digest][1] != signature[2]:
            raise RuntimeError("same digest has inconsistent sizes")
        blobs.setdefault(digest, (path, signature[2], signature))
    manifest = {
        "schema": SOURCE_SCHEMA, "original_root": str(root), "files": entries,
        "source_file_count": len(entries), "source_logical_bytes": sum(e["bytes"] for e in entries),
        "unique_blob_count": len(blobs), "unique_blob_bytes": sum(b[1] for b in blobs.values()),
        "capture_contract": {
            "file_bytes_lossless": True, "all_original_relative_paths_recorded": True,
            "original_inode_preserved": False, "original_path_lifetime_preserved": False,
            "sparse_holes_preserved": False, "original_timestamps_preserved": False,
            "archive_restore_executes_evidence": False, "scientific_qualification": False,
            "telescope_provenance_asserted": False,
        },
        "inventory_policy": {"owned_directories": sorted(set(ALLOWED_DIRS) | set(args.include_dir)),
                             "observation_prefixes": list(OBSERVATION_PREFIXES),
                             "visible_root_regular_files": True,
                             "excluded": ["hidden entries", "__pycache__", "publishing", "publication", "archive output directory"]},
    }
    manifest_bytes = canonical_json(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".archive-staging-", dir=output.parent))
    sink = PartWriter(stage, args.part_mib * MIB, args.archive_cap_mib * MIB)
    parameters = zstd.ZstdCompressionParameters.from_level(
        9, window_log=25, enable_ldm=True, ldm_hash_log=20, threads=0)
    try:
        with zstd.ZstdCompressor(compression_params=parameters).stream_writer(sink, closefd=False) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.USTAR_FORMAT) as tar:
                tar.addfile(tar_header("source-manifest.json", len(manifest_bytes)), io.BytesIO(manifest_bytes))
                for digest, (path, size, signature) in sorted(blobs.items()):
                    source = CheckedSource(path, digest, signature)
                    try:
                        tar.addfile(tar_header("blobs/" + digest, size), source)
                    finally:
                        source.close_verified()
        sink.close()
        if files != inventory(root, output, args.include_dir):
            raise RuntimeError("source inventory changed during archive build")
        for path in files:
            if file_signature(path) != signatures[path.relative_to(root).as_posix()]:
                raise RuntimeError("source metadata changed during archive build: " + str(path))
        archive = {
            "schema": ARCHIVE_SCHEMA, "format": "content-deduplicated-ustar-zstd",
            "compression": {"algorithm": "zstd", "level": 9, "window_log": 25,
                            "enable_ldm": True, "ldm_hash_log": 20, "threads": 0,
                            "zstandard_python_version": zstd.__version__,
                            "zstd_library_version": list(zstd.ZSTD_VERSION)},
            "fixed_caps": {"compressed_archive_bytes": args.archive_cap_mib * MIB,
                           "part_bytes": args.part_mib * MIB, "address_space_bytes": args.memory_mib * MIB},
            "compressed_bytes": sink.total, "compressed_sha256": sink.full_hash.hexdigest(),
            "source_manifest_bytes": len(manifest_bytes), "source_manifest_sha256": sha(manifest_bytes),
            "source_file_count": len(entries), "source_logical_bytes": manifest["source_logical_bytes"],
            "unique_blob_count": len(blobs), "unique_blob_bytes": manifest["unique_blob_bytes"],
            "parts": sink.parts,
        }
        write_verified_file(stage / "source-manifest.json", manifest_bytes)
        write_verified_file(stage / "archive-manifest.json", canonical_json(archive))
        stage.rename(output)
        print(json.dumps({"output": str(output), "file_count": len(entries), "unique_blobs": len(blobs),
                          "source_bytes": manifest["source_logical_bytes"],
                          "compressed_bytes": sink.total, "compressed_sha256": archive["compressed_sha256"]}))
    except BaseException:
        sink.close()
        shutil.rmtree(stage, ignore_errors=True)
        raise


class ConcatenatedParts(io.RawIOBase):
    def __init__(self, paths):
        super().__init__()
        self.paths, self.index, self.current = paths, 0, None

    def readable(self):
        return True

    def readinto(self, buffer):
        while self.index < len(self.paths):
            if self.current is None:
                self.current = self.paths[self.index].open("rb")
            amount = self.current.readinto(buffer)
            if amount:
                return amount
            self.current.close()
            self.current = None
            self.index += 1
        return 0

    def close(self):
        if self.current:
            self.current.close()
        super().close()


def restore(args):
    enforce_memory_limit(args.memory_mib)
    directory = Path(args.archive).resolve()
    verifying = args.command == "verify"
    destination = None if verifying else Path(args.dest).resolve()
    if destination is not None and destination.exists():
        raise ValueError("restore destination must not already exist")
    archive_path = directory / "archive-manifest.json"
    if file_signature(archive_path)[2] > MIB:
        raise ValueError("archive manifest exceeds fixed limit")
    archive = json.loads(archive_path.read_bytes())
    if archive.get("schema") != ARCHIVE_SCHEMA:
        raise ValueError("wrong archive schema")
    if archive["compressed_bytes"] > 64 * MIB or archive["source_logical_bytes"] > args.restore_cap_mib * MIB:
        raise ValueError("archive exceeds restore caps")
    if not 0 < archive["source_manifest_bytes"] <= 16 * MIB:
        raise ValueError("source manifest exceeds fixed limit")
    paths, total, compressed_hash = [], 0, hashlib.sha256()
    parts = archive["parts"]
    if not isinstance(parts, list) or not 1 <= len(parts) <= 64:
        raise ValueError("invalid part count")
    for index, part in enumerate(parts):
        expected_name = f"evidence.tar.zst.part{index:04d}"
        if part["filename"] != expected_name or not 0 < part["bytes"] <= 16 * MIB:
            raise ValueError("unsafe or oversized archive part")
        path = directory / expected_name
        signature = file_signature(path)
        h = hashlib.sha256()
        with path.open("rb") as f:
            while data := f.read(BLOCK):
                h.update(data)
                compressed_hash.update(data)
                total += len(data)
                if total > 64 * MIB:
                    raise ValueError("actual archive bytes exceed fixed cap")
        if signature != file_signature(path) or signature[2] != part["bytes"] or h.hexdigest() != part["sha256"]:
            raise ValueError("archive part identity mismatch: " + expected_name)
        paths.append(path)
    if total != archive["compressed_bytes"] or compressed_hash.hexdigest() != archive["compressed_sha256"]:
        raise ValueError("concatenated archive identity mismatch")
    stage = None
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".restore-staging-", dir=destination.parent))
    try:
        groups, expected_files, seen_blobs = {}, {}, set()
        raw = ConcatenatedParts(paths)
        with raw, zstd.ZstdDecompressor(max_window_size=64 * MIB).stream_reader(raw) as decompressed:
            first = strict_header(decompressed)
            if first is None or first.name != "source-manifest.json" or first.size != archive["source_manifest_bytes"]:
                raise ValueError("source manifest must be the first regular member")
            manifest_bytes = read_exact(decompressed, first.size)
            consume_padding(decompressed, first.size)
            if sha(manifest_bytes) != archive["source_manifest_sha256"]:
                raise ValueError("source manifest identity mismatch")
            sidecar = directory / "source-manifest.json"
            if (file_signature(sidecar)[2] != first.size or sidecar.read_bytes() != manifest_bytes):
                raise ValueError("source manifest sidecar differs from archived manifest")
            manifest = json.loads(manifest_bytes)
            if manifest.get("schema") != SOURCE_SCHEMA:
                raise ValueError("wrong source manifest schema")
            entries = manifest["files"]
            if not isinstance(entries, list) or len(entries) != archive["source_file_count"] or len(entries) > 100_000:
                raise ValueError("invalid source file count")
            source_bytes = 0
            for entry in entries:
                relative = safe_relative(entry["path"]).as_posix()
                size, digest, mode = entry["bytes"], entry["sha256"], entry["mode"]
                if relative in expected_files or not isinstance(size, int) or size < 0 or size > args.restore_cap_mib * MIB:
                    raise ValueError("invalid source file declaration")
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                    raise ValueError("invalid source file digest")
                if not isinstance(mode, int) or not 0 <= mode <= 0o777:
                    raise ValueError("invalid source file mode")
                expected_files[relative] = entry
                groups.setdefault(digest, []).append(entry)
                if groups[digest][0]["bytes"] != size:
                    raise ValueError("same digest declares conflicting sizes")
                source_bytes += size
            if source_bytes != archive["source_logical_bytes"] or source_bytes > args.restore_cap_mib * MIB:
                raise ValueError("source byte total mismatch")
            if len(groups) != archive["unique_blob_count"] or sum(g[0]["bytes"] for g in groups.values()) != archive["unique_blob_bytes"]:
                raise ValueError("unique blob totals mismatch")
            while (member := strict_header(decompressed)) is not None:
                if not member.name.startswith("blobs/"):
                    raise ValueError("unknown archive member")
                digest = member.name[6:]
                if digest not in groups or member.name != "blobs/" + digest or digest in seen_blobs:
                    raise ValueError("unknown or duplicate blob")
                entries_for_blob = groups[digest]
                if member.size != entries_for_blob[0]["bytes"]:
                    raise ValueError("blob length mismatch")
                first_path = None if stage is None else stage / entries_for_blob[0]["path"]
                out = None
                if first_path is not None:
                    first_path.parent.mkdir(parents=True, exist_ok=True)
                    out = first_path.open("xb")
                h, remaining = hashlib.sha256(), member.size
                try:
                    while remaining:
                        data = decompressed.read(min(BLOCK, remaining))
                        if not data:
                            raise ValueError("truncated blob")
                        remaining -= len(data)
                        h.update(data)
                        if out:
                            write_all(out, data)
                finally:
                    if out:
                        out.flush()
                        os.fsync(out.fileno())
                        out.close()
                consume_padding(decompressed, member.size)
                if h.hexdigest() != digest:
                    raise ValueError("archived blob identity mismatch")
                if first_path is not None:
                    for entry in entries_for_blob[1:]:
                        target = stage / entry["path"]
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with first_path.open("rb") as source, target.open("xb") as copy:
                            while data := source.read(BLOCK):
                                write_all(copy, data)
                            copy.flush()
                            os.fsync(copy.fileno())
                seen_blobs.add(digest)
            if seen_blobs != set(groups):
                raise ValueError("archive has missing blobs")
            # USTAR permits zero final blocking padding; no appended payloads.
            suffix = 512
            while data := decompressed.read(BLOCK):
                suffix += len(data)
                if suffix > 10240 or data.strip(b"\0"):
                    raise ValueError("unexpected trailing decompressed data")
        verification_root = Path(args.source_root).resolve() if verifying else stage
        for relative, entry in expected_files.items():
            digest, signature = hash_file(verification_root / relative)
            if digest != entry["sha256"] or signature[2] != entry["bytes"]:
                raise ValueError("file verification failed: " + relative)
        if verifying:
            extras = manifest["inventory_policy"]["owned_directories"]
            actual = {p.relative_to(verification_root).as_posix() for p in inventory(verification_root, directory, extras)}
        else:
            actual = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
            for relative, entry in expected_files.items():
                os.chmod(stage / relative, entry["mode"])
        if actual != set(expected_files):
            raise ValueError("verified file inventory mismatch")
        receipt = {"schema": "seti-lossless-evidence-restore-receipt-v1",
                   "compressed_sha256": archive["compressed_sha256"],
                   "source_manifest_sha256": archive["source_manifest_sha256"],
                   "verified_regular_files": len(expected_files), "verified_bytes": source_bytes,
                   "evidence_reexecuted": False, "scientific_qualification": False,
                   "original_inode_or_path_lifetime_preserved": False}
        receipt["verification_mode"] = "streamed_archive_against_original_files" if verifying else "safe_restore_then_every_file_hashed"
        if stage is not None:
            stage.rename(destination)
        print(json.dumps(receipt, sort_keys=True))
    except BaseException:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    b = commands.add_parser("build", help="run only after all intended source work is frozen")
    b.add_argument("--root", required=True)
    b.add_argument("--output", required=True)
    b.add_argument("--include-dir", action="append", default=[])
    b.add_argument("--part-mib", type=int, default=1)
    b.add_argument("--archive-cap-mib", type=int, default=64)
    b.add_argument("--memory-mib", type=int, default=512)
    b.set_defaults(func=build)
    r = commands.add_parser("restore", help="verify all parts, safely restore, verify every file")
    r.add_argument("--archive", required=True)
    r.add_argument("--dest", required=True)
    r.add_argument("--restore-cap-mib", type=int, default=4096)
    r.add_argument("--memory-mib", type=int, default=512)
    r.set_defaults(func=restore)
    v = commands.add_parser("verify", help="stream all blobs and hash original files; no extra payload copy")
    v.add_argument("--archive", required=True)
    v.add_argument("--source-root", required=True)
    v.add_argument("--restore-cap-mib", type=int, default=4096)
    v.add_argument("--memory-mib", type=int, default=512)
    v.set_defaults(func=restore)
    args = parser.parse_args()
    if args.command == "build" and (not 1 <= args.part_mib <= 16 or not 1 <= args.archive_cap_mib <= 64):
        parser.error("part cap must be 1–16 MiB; compressed archive cap must be 1–64 MiB")
    if args.command in ("restore", "verify") and not 1 <= args.restore_cap_mib <= 4096:
        parser.error("restore logical byte cap must be 1–4096 MiB")
    args.func(args)


if __name__ == "__main__":
    main()
