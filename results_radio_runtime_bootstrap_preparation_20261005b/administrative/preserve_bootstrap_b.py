#!/usr/bin/env python3
"""Losslessly preserve a *finished* bootstrap root; never install or import it.

This is administrative publication work outside the one-shot bootstrap's selected
read/time/artifact accounting. It must be invoked separately after the child is
reaped. Output is exclusive and failures retain partial output without retry.
"""
import argparse
import base64
import codecs
import hashlib
import json
import os
import stat
import sys
import time
import zipfile

BASIS_REPOSITORY = "andersenmartin-blip/setisearch"
BASIS_COMMIT = "c1ff02e8da9dae07b5711595df6d57fd7857e67c"
BASIS_PREFIX = "results_radio_runtime_bootstrap_preparation_20261005a/"
BASIS_TREE = "3bd54744a801e3fb4e16c9922f49771ae48e2d31"

SEGMENT = 374997  # divisible by three: 499996 base64 bytes + one newline
READ = 65536
MAX_FILE = 134217728
MAX_TOTAL = 1610612736
MAX_FILES = 20000
MAX_DIRS = 4096
MAX_MEMBERS = 24576
MAX_PAYLOAD = 536870912
MAX_UTF8_COPY = 450000
NOFOLLOW = os.O_NOFOLLOW | os.O_CLOEXEC


class PreservationError(Exception):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def relative(value):
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        raise PreservationError("unsafe relative path")
    if any(x in ("", ".", "..") for x in value.split("/")) or "\x00" in value:
        raise PreservationError("unsafe relative path component")
    value.encode("utf-8", "strict")
    return value


def identity(value):
    return {"device": value.st_dev, "inode": value.st_ino, "mode": stat.S_IMODE(value.st_mode),
            "file_type_mode": stat.S_IFMT(value.st_mode), "links": value.st_nlink,
            "bytes": value.st_size, "mtime_ns": value.st_mtime_ns,
            "ctime_ns": value.st_ctime_ns, "allocated_bytes": value.st_blocks * 512}


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()}


class HeldTree:
    """Every ancestor is held; every child is opened relative to its held parent."""
    def __init__(self, absolute):
        if not os.path.isabs(absolute) or os.path.normpath(absolute) != absolute:
            raise PreservationError("absolute canonical tree path required")
        self.path = absolute
        self.ancestors = []
        current = os.open("/", os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
        self.ancestors.append((current, None, None, os.fstat(current)))
        for name in absolute.split("/")[1:]:
            if not name:
                continue
            before = os.stat(name, dir_fd=current, follow_symlinks=False)
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=current)
            after = os.fstat(child)
            if (before.st_dev, before.st_ino, before.st_mode) != (after.st_dev, after.st_ino, after.st_mode):
                os.close(child)
                raise PreservationError("ancestor name/descriptor substitution")
            self.ancestors.append((child, current, name, after))
            current = child
        self.fd = current

    def check(self):
        for fd, parent, name, original in self.ancestors:
            now = os.fstat(fd)
            if (now.st_dev, now.st_ino, now.st_mode) != (original.st_dev, original.st_ino, original.st_mode):
                raise PreservationError("held ancestor substitution")
            if parent is not None:
                named = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if (named.st_dev, named.st_ino, named.st_mode) != (now.st_dev, now.st_ino, now.st_mode):
                    raise PreservationError("named ancestor substitution")

    def parent(self, path):
        parts = relative(path).split("/")
        fd = os.dup(self.fd)
        try:
            for name in parts[:-1]:
                before = os.stat(name, dir_fd=fd, follow_symlinks=False)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                held = os.fstat(child)
                if identity(before) != identity(held):
                    os.close(child)
                    raise PreservationError("selected parent substitution")
                os.close(fd)
                fd = child
            return fd, parts[-1]
        except BaseException:
            os.close(fd)
            raise

    def file(self, path, expected=None):
        parent, name = self.parent(path)
        try:
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISREG(named.st_mode) or named.st_nlink != 1:
                raise PreservationError("selected file must be sole-link regular")
            fd = os.open(name, os.O_RDONLY | NOFOLLOW, dir_fd=parent)
            held = os.fstat(fd)
            if identity(named) != identity(held) or (expected is not None and identity(held) != expected):
                os.close(fd)
                raise PreservationError("selected file identity mismatch")
            return fd, parent, name, identity(held)
        except BaseException:
            os.close(parent)
            raise

    def finish_file(self, fd, parent, name, original):
        try:
            if identity(os.fstat(fd)) != original or identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != original:
                raise PreservationError("selected file changed during read")
        finally:
            os.close(fd)
            os.close(parent)

    def close(self):
        for fd, _, _, _ in reversed(self.ancestors):
            os.close(fd)


def read_file(tree, path, expected=None, cap=MAX_FILE):
    fd, parent, name, source_identity = tree.file(path, expected)
    try:
        if source_identity["bytes"] > cap:
            raise PreservationError("selected file read cap exceeded")
        raw = bytearray()
        remaining = source_identity["bytes"]
        while remaining:
            chunk = os.read(fd, min(READ, remaining))
            if not chunk:
                raise PreservationError("selected file truncated")
            raw.extend(chunk)
            remaining -= len(chunk)
        if os.read(fd, 1):
            raise PreservationError("selected file grew")
        return bytes(raw), source_identity
    finally:
        tree.finish_file(fd, parent, name, source_identity)


def inventory(tree, hashes):
    entries = []
    counters = {"files": 0, "directories": 0, "file_bytes": 0, "logical_bytes": 0, "allocated_bytes": 0}
    root_device = os.fstat(tree.fd).st_dev

    def visit(fd, path):
        before = identity(os.fstat(fd))
        if before["device"] != root_device:
            raise PreservationError("mounted subtree is outside selected root")
        counters["directories"] += 1
        if counters["directories"] > MAX_DIRS:
            raise PreservationError("directory count cap exceeded")
        entries.append({"path": path, "kind": "directory", "identity": before})
        counters["logical_bytes"] += before["bytes"]
        counters["allocated_bytes"] += before["allocated_bytes"]
        names = sorted(os.listdir(fd))
        for name in names:
            relative(name)
            child_path = name if path == "." else path + "/" + name
            named = os.stat(name, dir_fd=fd, follow_symlinks=False)
            original = identity(named)
            if named.st_dev != root_device:
                raise PreservationError("cross-device selected object")
            if stat.S_ISDIR(named.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                try:
                    if identity(os.fstat(child)) != original:
                        raise PreservationError("directory substituted")
                    visit(child, child_path)
                    if identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != original:
                        raise PreservationError("named directory changed")
                finally:
                    os.close(child)
            elif stat.S_ISREG(named.st_mode) and named.st_nlink == 1:
                counters["files"] += 1
                counters["file_bytes"] += named.st_size
                if counters["files"] > MAX_FILES or named.st_size > MAX_FILE or counters["file_bytes"] > MAX_TOTAL:
                    raise PreservationError("selected regular file count/size cap exceeded")
                row = {"path": child_path, "kind": "file", "identity": original}
                if hashes:
                    selected = os.open(name, os.O_RDONLY | NOFOLLOW, dir_fd=fd)
                    try:
                        if identity(os.fstat(selected)) != original:
                            raise PreservationError("inventory file substituted")
                        sha = hashlib.sha256()
                        git = hashlib.sha1(b"blob " + str(named.st_size).encode("ascii") + b"\0")
                        decoder = codecs.getincrementaldecoder("utf-8")("strict")
                        utf8 = True
                        remaining = named.st_size
                        while remaining:
                            chunk = os.read(selected, min(READ, remaining))
                            if not chunk:
                                raise PreservationError("inventory file truncated")
                            remaining -= len(chunk)
                            sha.update(chunk)
                            git.update(chunk)
                            if utf8:
                                try:
                                    decoder.decode(chunk, final=False)
                                except UnicodeDecodeError:
                                    utf8 = False
                        if os.read(selected, 1):
                            raise PreservationError("inventory file grew")
                        if utf8:
                            try:
                                decoder.decode(b"", final=True)
                            except UnicodeDecodeError:
                                utf8 = False
                        if identity(os.fstat(selected)) != original or identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != original:
                            raise PreservationError("inventory file changed")
                        row.update({"bytes": named.st_size, "sha256": sha.hexdigest(), "git_blob": git.hexdigest(), "valid_utf8": utf8})
                    finally:
                        os.close(selected)
                entries.append(row)
                counters["logical_bytes"] += named.st_size
                counters["allocated_bytes"] += original["allocated_bytes"]
            else:
                raise PreservationError("symlink/hardlink/special selected object rejected")
            if max(counters["logical_bytes"], counters["allocated_bytes"]) > MAX_TOTAL:
                raise PreservationError("root logical/allocated storage cap exceeded")
        if sorted(os.listdir(fd)) != names or identity(os.fstat(fd)) != before:
            raise PreservationError("directory changed during inventory")

    tree.check()
    visit(tree.fd, ".")
    tree.check()
    return {"entries": entries, "totals": counters}


class Output:
    def __init__(self, repository, path):
        self.repository = repository
        self.path = relative(path)
        parent, name = repository.parent(path)
        try:
            os.mkdir(name, 0o700, dir_fd=parent)  # exclusive: no automatic restart
            os.fsync(parent)
        finally:
            os.close(parent)
        self.tree = HeldTree(repository.path + "/" + path)
        self.artifacts = []

    def write(self, path, raw):
        parts = relative(path).split("/")
        fd = os.dup(self.tree.fd)
        directory_guards = [(fd, None, None, os.fstat(fd))]
        try:
            for name in parts[:-1]:
                try:
                    os.mkdir(name, 0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
                named = os.stat(name, dir_fd=fd, follow_symlinks=False)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                held = os.fstat(child)
                if identity(named) != identity(held):
                    os.close(child)
                    raise PreservationError("administrative output directory substituted")
                directory_guards.append((child, fd, name, held))
                fd = child
            target = os.open(parts[-1], os.O_RDWR | os.O_CREAT | os.O_EXCL | NOFOLLOW, 0o644, dir_fd=fd)
            try:
                os.fchmod(target, 0o644)
                original_target = os.fstat(target)
                if not stat.S_ISREG(original_target.st_mode) or original_target.st_nlink != 1 or original_target.st_size != 0:
                    raise PreservationError("administrative output must be empty sole-link regular")
                view = memoryview(raw)
                while view:
                    wrote = os.write(target, view)
                    if wrote <= 0:
                        raise PreservationError("administrative write made no progress")
                    view = view[wrote:]
                os.fsync(target)
                completed = os.fstat(target)
                if (completed.st_dev, completed.st_ino, completed.st_mode, completed.st_nlink, completed.st_size) != (original_target.st_dev, original_target.st_ino, original_target.st_mode, 1, len(raw)):
                    raise PreservationError("held administrative output changed")
                if identity(os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)) != identity(completed):
                    raise PreservationError("named administrative output differs from held file")
                os.lseek(target, 0, os.SEEK_SET)
                verify_sha = hashlib.sha256()
                verify_git = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0")
                returned_bytes = 0
                while returned_bytes < len(raw):
                    returned = os.read(target, min(READ, len(raw) - returned_bytes))
                    if not returned:
                        raise PreservationError("administrative output readback truncated")
                    returned_bytes += len(returned)
                    verify_sha.update(returned)
                    verify_git.update(returned)
                expected = digest(raw)
                if os.read(target, 1) or verify_sha.hexdigest() != expected["sha256"] or verify_git.hexdigest() != expected["git_blob"]:
                    raise PreservationError("administrative final-output readback hash mismatch")
                if identity(os.fstat(target)) != identity(completed) or identity(os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)) != identity(completed):
                    raise PreservationError("administrative output changed during readback")
            finally:
                os.close(target)
            os.fsync(fd)
            for held_fd, parent_fd, name, original in directory_guards:
                current = os.fstat(held_fd)
                if (current.st_dev, current.st_ino, current.st_mode) != (original.st_dev, original.st_ino, original.st_mode):
                    raise PreservationError("held administrative output directory changed")
                if parent_fd is not None and identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != identity(current):
                    raise PreservationError("named administrative output directory changed")
            self.tree.check()
        finally:
            for held_fd, _, _, _ in reversed(directory_guards):
                os.close(held_fd)
        pin = {"repository_path": self.path + "/" + path, **digest(raw), "mode": "100644"}
        self.artifacts.append(pin)
        return pin


def preserve_parts(root, row, output, prefix):
    fd, parent, name, original = root.file(row["path"], row["identity"])
    parts = []
    sha = hashlib.sha256()
    offset = 0
    try:
        while offset < row["bytes"]:
            count = min(SEGMENT, row["bytes"] - offset)
            raw = bytearray()
            while len(raw) < count:
                chunk = os.read(fd, count - len(raw))
                if not chunk:
                    raise PreservationError("part source truncated")
                raw.extend(chunk)
            raw = bytes(raw)
            sha.update(raw)
            encoded = base64.b64encode(raw) + b"\n"
            if len(encoded) > 500001:
                raise PreservationError("encoded part transport cap exceeded")
            stored = output.write(prefix + "/" + str(len(parts)).zfill(6) + ".base64", encoded)
            parts.append({"index": len(parts), "offset": offset, "raw_bytes": len(raw),
                          "raw_sha256": hashlib.sha256(raw).hexdigest(), "encoded": stored})
            offset += len(raw)
        if os.read(fd, 1) or sha.hexdigest() != row["sha256"]:
            raise PreservationError("part source full length/hash mismatch")
    finally:
        root.finish_file(fd, parent, name, original)
    return {"root_relative_path": row["path"], "raw_bytes": row["bytes"], "raw_sha256": row["sha256"],
            "raw_git_blob": row["git_blob"], "raw_segment_bytes": SEGMENT,
            "encoding": "canonical-base64-plus-single-newline", "parts": parts}


def buffer_parts(raw, output, prefix):
    """Transport an administrative document without claiming it was binary."""
    parts = []
    for offset in range(0, len(raw), SEGMENT):
        selected = raw[offset:offset + SEGMENT]
        stored = output.write(prefix + "/" + str(len(parts)).zfill(6) + ".base64",
                              base64.b64encode(selected) + b"\n")
        parts.append({"index": len(parts), "offset": offset, "raw_bytes": len(selected),
                      "raw_sha256": hashlib.sha256(selected).hexdigest(), "encoded": stored})
    raw_pin = digest(raw)
    return {"raw_bytes": raw_pin["bytes"], "raw_sha256": raw_pin["sha256"],
            "raw_git_blob": raw_pin["git_blob"], "raw_segment_bytes": SEGMENT,
            "encoding": "canonical-base64-plus-single-newline", "parts": parts}


def archive_members(root, row, spec, totals):
    fd, parent, name, original = root.file(row["path"], row["identity"])
    result = []
    try:
        with os.fdopen(os.dup(fd), "rb") as stream:
            with zipfile.ZipFile(stream, "r") as archive:
                seen = set()
                for member in archive.infolist():
                    totals["members"] += 1
                    if totals["members"] > MAX_MEMBERS:
                        raise PreservationError("archive member count cap exceeded")
                    path = member.filename[:-1] if member.is_dir() else member.filename
                    relative(path)
                    if member.filename in seen:
                        raise PreservationError("duplicate archive member")
                    seen.add(member.filename)
                    if member.flag_bits & 1 or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                        raise PreservationError("encrypted/unsupported archive member")
                    mode = member.external_attr >> 16
                    if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                        raise PreservationError("archive special member")
                    if member.is_dir():
                        continue
                    totals["payload"] += member.file_size
                    if member.file_size > MAX_FILE or totals["payload"] > MAX_PAYLOAD:
                        raise PreservationError("archive declared payload cap exceeded")
                    sha = hashlib.sha256()
                    got = 0
                    with archive.open(member, "r") as source:
                        while True:
                            raw = source.read(min(READ, member.file_size - got + 1))
                            if not raw:
                                break
                            got += len(raw)
                            if got > member.file_size:
                                raise PreservationError("archive expanded member bound exceeded")
                            sha.update(raw)
                    if got != member.file_size:
                        raise PreservationError("archive expanded member length mismatch")
                    result.append({"archive_root_relative_path": row["path"], "archive_filename": spec["filename"],
                                   "archive_raw_sha256": row["sha256"], "member_path": member.filename,
                                   "bytes": got, "sha256": sha.hexdigest(), "crc32": member.CRC})
    finally:
        root.finish_file(fd, parent, name, original)
    return result


def read_json_pin(repository, path, expected_sha256, cap):
    raw, original = read_file(repository, relative(path), cap=cap)
    pin = {"repository_path": path, **digest(raw), "identity": original}
    if pin["sha256"] != expected_sha256:
        raise PreservationError("administrative input raw SHA mismatch")
    return json.loads(raw), pin


def preserve(args):
    started = time.monotonic_ns()
    repository = HeldTree(args.repository_root)
    root = None
    basis_repository = None
    output = None
    try:
        if len(args.bootstrap_identity) != 64 or any(c not in "0123456789abcdef" for c in args.bootstrap_identity):
            raise PreservationError("external bootstrap identity must be lowercase SHA-256")
        absolute_output = args.repository_root + "/" + relative(args.output)
        if absolute_output == args.root or absolute_output.startswith(args.root + "/") or args.root.startswith(absolute_output + "/"):
            raise PreservationError("administrative output must be separate from actual root")
        plan, plan_pin = read_json_pin(repository, args.plan, args.plan_sha256, 1048576)
        basis_repository = HeldTree(args.basis_repository_root)
        preread, preread_pin = read_json_pin(basis_repository, args.installer_preread, args.installer_preread_sha256, 4194304)
        catalog, catalog_pin = read_json_pin(repository, args.basis_tree_catalog, args.basis_tree_catalog_sha256, 4194304)
        if catalog.get("sha") != BASIS_TREE or catalog.get("truncated") is not False:
            raise PreservationError("immutable installer basis catalog must be the complete pinned subtree")
        published = {BASIS_PREFIX + row["path"]: row for row in catalog["tree"] if row.get("type") == "blob"}
        def published_reference(path, bytes_count, blob, mode="100644"):
            row = published.get(path)
            if row is None or row["sha"] != blob or row["size"] != bytes_count or row["mode"] != mode:
                raise PreservationError("installer basis path/bytes/blob/mode absent from immutable catalog")
            return {"repository": BASIS_REPOSITORY, "commit": BASIS_COMMIT,
                    "preparation_subtree": BASIS_TREE, "repository_path": path,
                    "git_blob": blob, "mode": mode}
        preread_pin["immutable_publication"] = published_reference(args.installer_preread, preread_pin["bytes"], preread_pin["git_blob"])
        wheels = plan.get("materialization", {}).get("official_wheels")
        if not isinstance(wheels, list) or len(wheels) != 3:
            raise PreservationError("exact original three-wheel plan required")
        for wheel in wheels:
            relative(wheel["filename"])
            if "/" in wheel["filename"] or not wheel["filename"].endswith(".whl"):
                raise PreservationError("wheel basename required")
        root = HeldTree(args.root)
        root.check()
        before = inventory(root, hashes=True)
        root.check()
        output = Output(repository, args.output)
        files = {r["path"]: r for r in before["entries"] if r["kind"] == "file"}
        for receipt_path in ("spent.json", "supervisor-result.json"):
            if receipt_path in files:
                receipt_raw, _ = read_file(root, receipt_path, files[receipt_path]["identity"], cap=16777216)
                receipt = json.loads(receipt_raw)
                if receipt.get("bootstrap_identity") != args.bootstrap_identity:
                    raise PreservationError("actual-root receipt bootstrap identity mismatch")
        seed = {"installer/" + relative(r["seed_relative_path"]): r for r in preread["installer_source_files"]}
        expected_archives = {"wheelhouse/" + w["filename"]: w for w in wheels}
        payloads = []
        complete_archives = []
        members = []
        archive_inspection_failures = []
        archive_totals = {"members": 0, "payload": 0}
        for path, spec in sorted(expected_archives.items()):
            if path not in files:
                continue
            row = files[path]
            payload = preserve_parts(root, row, output, "wheel-parts/" + spec["filename"])
            payload.update({"purpose": "wheel-archive", "expected_original": spec,
                            "matches_original": row["bytes"] == spec["bytes"] and row["sha256"] == spec["sha256"]})
            payloads.append(payload)
            row["preservation"] = {"kind": "parts", "payload_root_relative_path": path}
            if payload["matches_original"]:
                complete_archives.append(path)
                try:
                    members.extend(archive_members(root, row, spec, archive_totals))
                except (PreservationError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
                    # Acquisition/preflight failures must still be preserved. A
                    # refused member inspection supplies no equivalence mapping;
                    # installed binary bytes then receive their own exact parts.
                    archive_inspection_failures.append({"archive_root_relative_path": path,
                        "exception": type(exc).__name__, "message": str(exc),
                        "wheel_member_equivalence_admitted": False, "raw_archive_parts_retained": True})
        content_index = {}
        for member in members:
            content_index.setdefault((member["bytes"], member["sha256"]), []).append(member)
        basis_inputs = []
        for path, row in sorted(files.items()):
            if "preservation" in row:
                continue
            if path in seed and row["bytes"] == seed[path]["bytes"] and row["sha256"] == seed[path]["sha256"]:
                basis = seed[path]
                raw, source_identity = read_file(basis_repository, basis["repository_artifact_path"], cap=MAX_FILE)
                if digest(raw) != {"bytes": basis["repository_bytes"], "sha256": basis["repository_sha256"], "git_blob": basis["repository_git_blob"]}:
                    raise PreservationError("installer basis representation pin mismatch")
                if basis["stored_encoding"] == "base64":
                    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
                        raise PreservationError("installer basis newline is not canonical")
                    decoded = base64.b64decode(raw[:-1], validate=True)
                    if base64.b64encode(decoded) + b"\n" != raw:
                        raise PreservationError("installer basis base64 is not canonical")
                elif basis["stored_encoding"] == "utf8":
                    raw.decode("utf-8", "strict")
                    decoded = raw
                else:
                    raise PreservationError("installer basis encoding unsupported")
                if len(decoded) != row["bytes"] or hashlib.sha256(decoded).hexdigest() != row["sha256"]:
                    raise PreservationError("installer basis decoded raw mismatch")
                immutable = published_reference(basis["repository_artifact_path"], len(raw), basis["repository_git_blob"], basis["stored_mode"])
                reference = {"kind": "installer-basis-reference", "repository_path": basis["repository_artifact_path"],
                             "immutable_publication": immutable,
                             "stored_encoding": basis["stored_encoding"], "encoded_bytes": len(raw),
                             "encoded_sha256": basis["repository_sha256"], "encoded_git_blob": basis["repository_git_blob"],
                             "raw_bytes": row["bytes"], "raw_sha256": row["sha256"]}
                row["preservation"] = reference
                basis_inputs.append({"repository_path": basis["repository_artifact_path"], **digest(raw), "identity": source_identity, "immutable_publication": immutable})
                continue
            matches = content_index.get((row["bytes"], row["sha256"]), []) if path.startswith("site/") else []
            if matches:
                matches = sorted(matches, key=lambda m: (m["member_path"] != path[5:], m["archive_root_relative_path"], m["member_path"]))
                row["preservation"] = {"kind": "wheel-member-byte-equivalence", "member": matches[0],
                                       "equivalence_candidates": len(matches), "causal_installation_origin_certified": False}
            elif row["valid_utf8"] and row["bytes"] <= MAX_UTF8_COPY:
                raw, _ = read_file(root, path, row["identity"])
                raw.decode("utf-8", "strict")
                if digest(raw) != {"bytes": row["bytes"], "sha256": row["sha256"], "git_blob": row["git_blob"]}:
                    raise PreservationError("retained UTF-8 raw hash mismatch")
                row["preservation"] = {"kind": "exact-utf8-file", "stored": output.write("retained/" + path, raw)}
            else:
                payload = preserve_parts(root, row, output, "other-file-parts/" + path)
                payload["purpose"] = "unmatched-file-bytes"
                payload["raw_file_valid_utf8"] = row["valid_utf8"]
                payloads.append(payload)
                row["preservation"] = {"kind": "parts", "payload_root_relative_path": path}
        after = inventory(root, hashes=False)
        before_metadata = [{"path": r["path"], "kind": r["kind"], "identity": r["identity"]} for r in before["entries"]]
        if before_metadata != after["entries"] or before["totals"] != after["totals"]:
            raise PreservationError("full actual-root before/after inventory changed")
        root.check()
        repository.check()
        basis_repository.check()
        output.tree.check()
        manifest = {"schema": "radio-runtime-package-bootstrap-lossless-preservation-v2",
                    "bootstrap_identity": args.bootstrap_identity, "status": "LOSSLESS_ADMINISTRATIVE_PRESERVATION",
                    "actual_root": args.root, "output_repository_path": args.output,
                    "scientific_authority": False, "bootstrap_retry_or_reactivation": False,
                    "administrative_installer_invocations": 0, "administrative_native_package_imports": 0,
                    "accounting_scope": "separate administrative reads/transforms/publication; not charged as observed bootstrap child I/O or bootstrap elapsed time",
                    "elapsed_administrative_before_manifest_seconds": (time.monotonic_ns() - started) / 1000000000,
                    "limits": {"file_bytes": MAX_FILE, "root_bytes": MAX_TOTAL, "files": MAX_FILES, "directories": MAX_DIRS,
                               "expanded_archive_payload_bytes": MAX_PAYLOAD, "archive_members": MAX_MEMBERS,
                               "direct_retained_utf8_file_bytes": MAX_UTF8_COPY},
                    "input_pins": [plan_pin, preread_pin, catalog_pin],
                    "immutable_installer_basis": {"repository": BASIS_REPOSITORY, "commit": BASIS_COMMIT, "preparation_subtree": BASIS_TREE}, "referenced_installer_basis_inputs": basis_inputs,
                    "expected_original_wheels": wheels, "complete_original_archive_paths": complete_archives,
                    "all_three_original_archives_present_and_exact": len(complete_archives) == 3,
                    "before": before, "after": after, "full_before_after_identity_equal": True,
                    "payloads": payloads, "archive_members": members,
                    "archive_member_equivalence_inspection_failures": archive_inspection_failures,
                    "published_artifacts_before_manifest": output.artifacts,
                    "lossless_scope": "every sole-link regular actual-root file is represented by exact UTF-8 bytes, canonical base64 parts, verified wheel-member raw-byte equivalence, or verified preread seed representation; directories retain full metadata; manifest excludes its own raw pin",
                    "excluded_operational_objects": [],
                    "caller_cli_streams": "outside actual root; caller must separately retain exact stdout/stderr"}
        manifest_raw = canonical(manifest)
        manifest_pin = output.write("preservation-manifest.json", manifest_raw)
        transport_parts = buffer_parts(manifest_raw, output, "publication-transport/preservation-manifest")
        manifest_transport = {"schema": "radio-runtime-bootstrap-lossless-publication-transport-v1",
                              "path": manifest_pin["repository_path"],
                              "bytes": manifest_pin["bytes"], "sha256": manifest_pin["sha256"],
                              "git_blob": manifest_pin["git_blob"],
                              "parts": [{"path": p["encoded"]["repository_path"],
                                         "raw_offset": p["offset"], "raw_bytes": p["raw_bytes"],
                                         "raw_sha256": p["raw_sha256"],
                                         "bytes": p["encoded"]["bytes"], "sha256": p["encoded"]["sha256"],
                                         "git_blob": p["encoded"]["git_blob"]}
                                        for p in transport_parts["parts"]],
                              "encoding": "canonical-base64-segments", "scientific_authority": False}
        transport_pin = output.write("publication-transport/preservation-manifest.transport.json", canonical(manifest_transport))
        print(json.dumps({"status": manifest["status"], "manifest": manifest_pin,
                          "manifest_transport": transport_pin,
                          "files": before["totals"]["files"], "complete_original_archives": len(complete_archives)}, sort_keys=True))
        return 0
    except BaseException as exc:
        if output is not None:
            try:
                output.write("administrative-failure.json", canonical({"schema": "bootstrap-administrative-preservation-failure-v1",
                            "bootstrap_identity": args.bootstrap_identity, "exception": type(exc).__name__, "message": str(exc),
                            "partial_output_retained": True, "retry_performed": False, "scientific_authority": False}))
            except BaseException:
                pass
        raise
    finally:
        if output is not None:
            output.tree.close()
        if root is not None:
            root.close()
        if basis_repository is not None:
            basis_repository.close()
        repository.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "repository-root", "output", "plan", "plan-sha256", "installer-preread", "installer-preread-sha256", "bootstrap-identity", "basis-repository-root", "basis-tree-catalog", "basis-tree-catalog-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    return preserve(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("ADMINISTRATIVE_PRESERVATION_FAILED " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
