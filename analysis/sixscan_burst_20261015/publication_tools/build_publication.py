#!/usr/bin/env python3
"""Prepare byte-exact public metadata; no network, science, retry, or ref mutation.

Run against closed evidence only.  Scientific conclusions are taken verbatim
from separately reviewed report/prepend files, never computed here.  Immutable
commit/tree metadata and downloaded blob bytes are required for final readback.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

REPOSITORY = "andersenmartin-blip/setisearch"
BASE_HEAD = "fc0922ec078bc28d203e3680edf810e3183a46d1"
SCOPE_SHA = "551288e6eca87aa5d7449d186916cd84fa6aebdc5743736d914fee14b1ef84ea"
PUBLIC = "analysis/sixscan_burst_20261015"
PHASES = ("PRIMARY_CALIBRATION", "PRIMARY_VALIDATION", "QA", "EXPOSED", "QA_EXPOSED")
DOCS = ("README.md", "PROJECT_STATUS.md", "PROJECT_DIRECTION.md")
TEXT = {".json", ".jsonl", ".csv", ".tsv", ".md", ".txt", ".log", ".py", ".sha256"}
BINARIES = {".npz", ".npy", ".zip", ".gz", ".png", ".jpg", ".pdf", ".h5", ".fil"}
TERMINAL = {"COMPLETE", "CLOSED", "STOPPED_RETAINED_NO_RETRY", "ALL_FROZEN_PHASES_CLOSED"}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def parse(data):
    def pairs(items):
        out = {}
        for k, v in items:
            require(k not in out, "Duplicate JSON key: " + k)
            out[k] = v
        return out
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def jb(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def gitblob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def pin(data):
    return {"bytes": len(data), "sha256": sha(data), "git_blob_sha": gitblob(data)}


def stream_pin(path):
    """Opaque byte hashing only, including archive-only large text."""
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Expected regular archive member")
    before = path.stat()
    h, g, count = hashlib.sha256(), hashlib.sha1(), 0
    g.update(b"blob " + str(before.st_size).encode() + b"\0")
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
            g.update(block)
            count += len(block)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
            and count == before.st_size, "Archive-only source changed")
    return {"bytes": count, "sha256": h.hexdigest(), "git_blob_sha": g.hexdigest()}


def safe(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and name == p.as_posix() and not p.is_absolute()
            and name and ".." not in p.parts and "." not in p.parts and "\\" not in name,
            "Unsafe publication path: " + str(name))
    return name


def read(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Expected regular file: " + str(path))
    require(not any(p.is_symlink() for p in path.absolute().parents), "Symlinked parent: " + str(path))
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    require((before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns) and len(data) == before.st_size,
            "Source changed while reading: " + str(path))
    return data


def load(path):
    return parse(read(path))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(data)


def external_output(out, roots):
    out = out.resolve()
    for root in roots:
        root = root.resolve()
        require(out != root and root not in out.parents and out not in root.parents,
                "Output must be separate from every input tree: " + str(root))
    require(not out.exists(), "Choose a new, nonexistent output directory")
    return out


def tree_rows(tree):
    require(tree.get("truncated") is not True, "Truncated Git tree cannot establish readback")
    rows = tree.get("tree", tree.get("entries"))
    require(isinstance(rows, list), "Raw immutable Git tree JSON required")
    return rows


def verify_base(commit, tree, base_dir, expected_commit, documents):
    require(re.fullmatch(r"[0-9a-f]{40}", expected_commit or ""), "Exact base commit SHA required")
    require(commit.get("sha") == expected_commit, "Base commit metadata differs from requested parent")
    require(commit.get("tree", {}).get("sha") == tree.get("sha"), "Base commit/tree binding differs")
    rows = {r["path"]: r for r in tree_rows(tree)}
    result = {}
    for name in documents:
        data = read(base_dir / name)
        require(name in rows and rows[name].get("type") == "blob"
                and rows[name].get("sha") == gitblob(data), "Full base document Git blob differs: " + name)
        result[name] = pin(data)
    return result


def closed_object(obj, label, accepted=TERMINAL):
    require(obj.get("status") in accepted, "Not terminal: " + label + " (" + str(obj.get("status")) + ")")
    for key in ("running", "live", "live_jobs", "running_jobs", "active_children", "live_children"):
        require(not obj.get(key), "Live/unreconciled children in " + label + ":" + key)
    if "commands" in obj:
        require(all(c.get("status") == "CLOSED" for c in obj["commands"]), "Open command in " + label)


class Builder:
    def __init__(self, out, max_blob):
        require(65536 <= max_blob <= 16 * 1024 * 1024, "Public blob cap must be 64KiB..16MiB")
        self.out, self.max_blob = out, max_blob
        self.members, self.sources, self.split, self.omitted = {}, [], [], []

    def add_bytes(self, name, data, role, source=None):
        safe(name)
        data.decode("utf-8")  # GitHub subset is text only; no silent binary transcoding.
        require(name not in self.members, "Duplicate public destination: " + name)
        if len(data) <= self.max_blob:
            write(self.out / "payload" / name, data)
            self.members[name] = {**pin(data), "role": role, "local_file": "payload/" + name}
            return
        # Exact original UTF-8 byte stream, split at a valid codepoint boundary.
        # Reassemble by ordered concatenation; nothing is parsed or truncated.
        fragments, offset = [], 0
        while offset < len(data):
            end = min(offset + self.max_blob, len(data))
            while end < len(data) and (data[end] & 0xC0) == 0x80:
                end -= 1
            require(end > offset, "Unable to split UTF-8")
            fragment = data[offset:end]
            part = name + ".parts/part" + f"{len(fragments) + 1:04d}" + ".txt"
            self.add_bytes(part, fragment, role + ":exact_text_part")
            fragments.append({"path": part, **pin(fragment)})
            offset = end
        record = {"original_path": name, **pin(data), "encoding": "UTF-8",
                  "reconstruction": "Concatenate ordered part bytes without separators.", "parts": fragments}
        self.split.append(record)
        self.add_bytes(name + ".PARTS.json", jb(record), role + ":text_reconstruction_manifest")

    def add(self, name, path, role):
        data = read(path)
        self.sources.append({"source": str(Path(path).resolve()), "destination": name, **pin(data), "role": role})
        self.add_bytes(name, data, role)

    def receipts(self, root, destination, role, paths):
        """Exact source text in bounded JSONL shards, with source/hash/line index.

        Reconstruct each source as content_utf8.encode('utf-8'); JSON whitespace,
        CRLF, trailing newline, and original Unicode bytes are all preserved.
        """
        index, buffer, size, shard_number = [], [], 0, 1
        root = root.resolve()
        def flush():
            nonlocal buffer, size, shard_number
            if buffer:
                self.add_bytes(destination + f"/receipts{shard_number:04d}.jsonl", b"".join(buffer), role)
                buffer, size, shard_number = [], 0, shard_number + 1
        for path in paths:
            data = read(path)
            relative = safe(path.relative_to(root).as_posix())
            declaration = {"source_relative_path": relative, **pin(data)}
            record = {**declaration, "content_utf8": data.decode("utf-8")}
            line = (json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode()
            if buffer and size + len(line) > self.max_blob:
                flush()
            shard = destination + f"/receipts{shard_number:04d}.jsonl"
            index.append({**declaration, "shard": shard, "line_number_1_based": len(buffer) + 1})
            self.sources.append({"source": str(path.resolve()), "destination": shard,
                                 "receipt_source_relative_path": relative, **pin(data), "role": role})
            buffer.append(line)
            size += len(line)
        flush()
        for record in index:
            if record["shard"] not in self.members:
                record["shard_reconstruction_manifest"] = record["shard"] + ".PARTS.json"
        self.add_bytes(destination + "/RECEIPT_INDEX.json", jb({"schema": "SETI_EXACT_UTF8_RECEIPT_SHARDS_V1",
            "reconstruction": "Parse one JSONL record and write content_utf8.encode('utf-8') at its safe source_relative_path; verify all three pins.",
            "records": index}), role + ":exact_source_index")

    def tree(self, root, destination, role, select=None, pack_receipts=False):
        root = root.resolve()
        require(root.is_dir() and not root.is_symlink(), "Missing regular metadata tree: " + str(root))
        packed = []
        for path in sorted(root.rglob("*")):
            require(not path.is_symlink(), "Symlink in metadata tree: " + str(path))
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if "__pycache__" in relative.parts or any(x.startswith(".") for x in relative.parts):
                continue
            if select and not select(relative):
                continue
            if path.suffix.lower() not in TEXT:
                self.omitted.append({"source": str(path), "reason": "nontext_or_binary_not_public", "bytes": path.stat().st_size})
                continue
            if pack_receipts and len(relative.parts) > 1 and relative.parts[0] in {"claims", "original_receipts", "results"}:
                # Top-level result summaries/tables remain directly readable.
                if relative.parts[0] != "results" or len(relative.parts) > 2:
                    packed.append(path)
                    continue
            self.add(safe(destination + "/" + relative.as_posix()), path, role)
        if packed:
            self.receipts(root, destination + "/receipt_shards", role + ":source_receipt_text", packed)

    def target(self, name):
        return name if name in self.members else name + ".PARTS.json"

    def archive_only(self, path, member, locator, reason):
        declaration = {"source": str(path.resolve()), "archive_member": safe(member),
                       "owner_archive_locator": locator, "reason": reason, **stream_pin(path)}
        self.sources.append({**declaration, "destination": None, "archive_only": True, "role": "owner_archive_only_exact_byte_pin"})
        self.omitted.append(declaration)

    def finish(self, parent, base_tree, branch, closure, base_proofs, dependencies=(), public_build=True):
        # Freeze all observed source bytes a second time before issuing the manifest.
        for item in self.sources:
            actual = stream_pin(item["source"]) if item.get("archive_only") else pin(read(item["source"]))
            require(actual == {k: item[k] for k in ("bytes", "sha256", "git_blob_sha")},
                    "Source changed during publication preparation: " + item["source"])
        archive_only = [x for x in self.sources if x.get("archive_only")]
        if archive_only and public_build:
            self.add_bytes(PUBLIC + "/publication/OWNER_ARCHIVE_ONLY_MEMBERS.json", jb({
                "schema": "SETI_PUBLIC_PINS_FOR_OWNER_ARCHIVE_ONLY_MEMBERS_V1",
                "interpretation": "No public raw-table completeness or validated-candidate claim.",
                "members": archive_only}), "large_unqualified_table_exact_pin_and_owner_archive_locator")
        build = {"schema": "SETI_PUBLIC_METADATA_BUILD_V1", "repository": REPOSITORY,
                 "branch": branch, "expected_parent_sha": parent, "base_tree_sha": base_tree,
                 "mode": closure["mode"], "closure": closure, "base_document_proofs": base_proofs,
                 "sources": self.sources, "omitted_nonpublic_files": self.omitted,
                 "exact_text_splits": self.split, "immutable_dependencies": list(dependencies),
                 "no_science_executed": True, "no_remote_mutation": True,
                 "missing_failed_unknown_not_measured_nulls": True,
                 "qualification_interpretation": "Report content is preserved verbatim; this is a byte/publication audit only."}
        if public_build:
            self.add_bytes(PUBLIC + "/publication/PUBLICATION_BUILD.json", jb(build), "public_byte_provenance")
        else:
            write(self.out / "PUBLICATION_BUILD.json", jb(build))
        manifest = {"schema": "SETI_EXPECTED_PUBLIC_GIT_BLOBS_V1", "repository": REPOSITORY,
                    "branch": branch, "expected_parent_sha": parent, "base_tree_sha": base_tree,
                    "files": self.members}
        write(self.out / "EXPECTED_BLOBS.json", jb(manifest))
        tree = {"repository_full_name": REPOSITORY, "base_tree_sha": base_tree,
                "tree_elements": [{"path": p, "mode": "100644", "type": "blob", "sha": d["git_blob_sha"]}
                                  for p, d in sorted(self.members.items())]}
        write(self.out / "TREE_PAYLOAD.json", jb(tree))
        write(self.out / "BLOB_UPLOADS.jsonl", b"".join((json.dumps({"repository_full_name": REPOSITORY,
              "path": p, "content_file": d["local_file"], "encoding": "utf-8",
              "expected_sha": d["git_blob_sha"]}, sort_keys=True) + "\n").encode() for p, d in sorted(self.members.items())))
        write(self.out / "COMMIT_AND_REF_PLAN.json", jb({"repository_full_name": REPOSITORY,
              "branch_name": branch, "parent_sha": parent, "tree_sha": "USE_RETURNED_CREATE_TREE_SHA",
              "message": "Record closed six-scan controls and resource-amendment evidence",
              "expected_sha": parent, "force": False,
              "ref_update_requires_exact_expected_head_lease": True,
              "post_update_immutable_all_blob_readback_required": True}))
        return {"status": "LOCAL_PUBLIC_PAYLOAD_PREPARED_NOT_PUBLISHED", "blobs": len(self.members),
                "payload_bytes": sum(x["bytes"] for x in self.members.values()), "output": str(self.out)}


def stage_selection(p):
    parts = p.parts
    if len(parts) == 1:
        return p.suffix.lower() in {".json", ".md", ".log", ".txt"}
    if parts[0] == "claims":
        return p.suffix == ".json"
    if parts[0] != "results":
        return False
    if len(parts) == 2 or (len(parts) >= 3 and parts[1] == "qa"):
        return p.suffix.lower() in TEXT
    return p.name in {"COMMITTED.json", "artifact_manifest.json", "admission.json", "STDOUT.log", "STDERR.log"}


def extension_selection(p):
    # Full resource/command closures and prospective protocol are metadata.
    # Huge per-case raw output hypotheses and truth payloads stay in delivery.
    return stage_selection(p) or (len(p.parts) == 1 and p.suffix.lower() == ".py") or (
        p.parts[0] not in {"results", "cases", "exposed", "__pycache__"} and p.suffix.lower() in TEXT)


def add_primary_receipt_index(builder, stage, metrics, byte_index):
    """Small metadata-only map of all planned source receipts, including absent."""
    cases = load(stage / "case_bank.json")
    require(len(cases) == 205, "Original identity denominator changed")
    sources = {s["source"]: s for s in builder.sources}
    by_label = {r["label"]: r for r in byte_index["records"] if not r["exposed"]}
    records, committed = [], 0
    for i, case in enumerate(cases):
        label = f"C{i:04d}"
        folder = stage / "results/cases" / label
        paths = {"COMMITTED": folder / "COMMITTED.json",
                 "artifact_manifest": folder / "artifact_manifest.json",
                 "producer_claim": stage / "claims" / (label + ".json")}
        item = {"index": i, "label": label, "case_id": case["case_id"], "family": case["family"],
                "byte_index_evidence_status": by_label.get(label, {}).get("evidence_status", "UNKNOWN"),
                "source_receipts": {}}
        for name, path in paths.items():
            source = sources.get(str(path.resolve()))
            if source:
                item["source_receipts"][name] = {k: source[k] for k in ("bytes", "sha256", "git_blob_sha")}
                item["source_receipts"][name]["source_stage_path"] = path.relative_to(stage).as_posix()
        if "COMMITTED" in item["source_receipts"]:
            require(len(item["source_receipts"]) == 3, "Producer commit missing manifest/claim metadata: " + label)
            commit, claim = load(paths["COMMITTED"]), load(paths["producer_claim"])
            require(commit["case_index"] == claim["case_index"] == i
                    and commit["case_id"] == claim["case_id"] == case["case_id"]
                    and commit["exposed"] is False and claim["exposed"] is False,
                    "Producer receipt identity differs: " + label)
            expected_manifest = item["source_receipts"]["artifact_manifest"]["sha256"]
            require(commit["artifact_manifest_sha256"] == claim["artifact_manifest_sha256"] == expected_manifest,
                    "Producer commit/claim manifest pin differs: " + label)
            item["receipt_presence"] = "COMMIT_MANIFEST_CLAIM_PRESENT_NOT_SCIENTIFIC_QUALIFICATION"
            committed += 1
        else:
            item["receipt_presence"] = "NO_COMMIT_NOT_A_MEASURED_NULL_OR_RECOVERY"
        records.append(item)
    if metrics.get("schema") == "SETI_BOUNDED_FAILURE_REPORT_METRICS_V1":
        require(committed == metrics["synthetic"]["worker_committed"], "Bounded report/source receipt census differs")
    builder.add_bytes(PUBLIC + "/publication/ORIGINAL_PRIMARY_RECEIPT_INDEX.json",
        jb({"schema": "SETI_ORIGINAL_PRODUCER_RECEIPT_SOURCE_INDEX_V1", "planned": 205,
            "complete_commit_manifest_claim_triples_present": committed,
            "missing_commits_not_measured_nulls": 205 - committed,
            "original_scientific_qualification": "FAIL_CLOSED", "records": records}),
        "exact_original_205_identity_commit_manifest_claim_source_index")
    stream = io.StringIO(newline="")
    fields = ["index", "label", "case_id", "family", "receipt_presence", "byte_index_evidence_status",
              "COMMITTED_sha256", "artifact_manifest_sha256", "producer_claim_sha256"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for item in records:
        row = {key: item[key] for key in fields[:6]}
        for name in ("COMMITTED", "artifact_manifest", "producer_claim"):
            row[name + "_sha256"] = item["source_receipts"].get(name, {}).get("sha256", "")
        writer.writerow(row)
    builder.add_bytes(PUBLIC + "/publication/ORIGINAL_PRIMARY_RECEIPT_INDEX.csv",
                      stream.getvalue().encode(), "source_receipt_index_readable_table")


def prepare_research(a):
    stage, base, reports, evidence = [Path(x).resolve() for x in (a.stage, a.base_dir, a.report_dir, a.evidence_dir)]
    roots = [stage, base, reports, evidence]
    if a.extension_root:
        roots.append(a.extension_root)
    if a.extension_report_dir:
        roots.append(a.extension_report_dir)
    roots += [Path(x.split("=", 1)[1]) for x in a.extra_tree]
    out = external_output(a.out, roots)
    commit, tree = load(a.base_commit_json), load(a.base_tree_json)
    bases = verify_base(commit, tree, base, a.base_commit, DOCS)
    scope_bytes, go_bytes = read(stage / "SCOPE.json"), read(stage / "GO.json")
    require(sha(scope_bytes) == SCOPE_SHA, "Wrong frozen study scope")
    scope, go = parse(scope_bytes), parse(go_bytes)
    require(go["scope_sha256"] == SCOPE_SHA and go["status"] == "ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK", "Invalid exact public GO")
    for row in scope["code_pins"]:
        data = read(stage / safe(row["path"]))
        require(sha(data) == row["sha256"] and len(data) == row["bytes"], "Frozen source changed: " + row["path"])
    scheduler = load(a.original_scheduler)
    closed_object(scheduler, "original scheduler", {"ALL_FROZEN_PHASES_CLOSED", "STOPPED_RETAINED_NO_RETRY"})
    require(scheduler.get("scope_sha256") == SCOPE_SHA, "Original scheduler scope differs")
    phases = {}
    for name in PHASES:
        path = stage / (name + "_RUN_STATE.json")
        if path.exists():
            value = load(path)
            closed_object(value, name)
            phases[name] = {"status": value["status"], **pin(read(path))}
        else:
            phases[name] = {"status": "ABSENT_NOT_MEASURED"}
    summary = load(stage / "results/SUMMARY.json")
    metrics = load(reports / "REPORT_METRICS.json")
    index = load(evidence / "EVIDENCE_INDEX.json")
    require(metrics.get("scope_sha256") == index.get("scope_sha256") == SCOPE_SHA, "Derived original outputs bind wrong scope")
    require(metrics.get("qualified_SETI_detection") is False and metrics.get("original_A_B") == "FAIL_CLOSED", "Original report qualification changed")
    if metrics.get("schema") == "SETI_BOUNDED_FAILURE_REPORT_METRICS_V1":
        require(a.mode == "failure", "Bounded failure report requires explicit failure mode")
        require(metrics.get("original_summary_sha256") == sha(read(stage / "results/SUMMARY.json")),
                "Bounded failure report original SUMMARY pin differs")
        require(metrics.get("evidence_index_sha256") == sha(read(evidence / "EVIDENCE_INDEX.json")),
                "Bounded failure report byte-evidence index pin differs")
        require(metrics.get("report_metadata_integrity_gate") is True
                and metrics.get("report_complete_for_bounded_failure") is True
                and metrics.get("report_bindings_verified") is True,
                "Bounded failure report metadata binding incomplete")
        require(metrics.get("integrity_gate") is False and metrics.get("joint_gate") is False,
                "Bounded failure cannot upgrade original qualification")
    closure = {"mode": a.mode, "scope_sha256": SCOPE_SHA, "GO_sha256": sha(go_bytes),
               "original_scheduler": {"status": scheduler["status"], **pin(read(a.original_scheduler))},
               "original_phase_closures": phases, "original_frozen_summary_status": summary.get("status"),
               "original_frozen_summary_sha256": sha(read(stage / "results/SUMMARY.json")),
               "all_five_phase_report_verified": metrics.get("complete_report_verified"),
               "bounded_failure_report_bindings_verified": metrics.get("report_bindings_verified"),
               "original_AB": "FAIL_CLOSED"}
    if a.mode == "complete":
        require(scheduler["status"] == "ALL_FROZEN_PHASES_CLOSED" and all(x["status"] == "COMPLETE" for x in phases.values()), "Complete mode requires five closed complete phases")
        require(metrics.get("complete_report_verified") is True, "Complete report not independently bound")
    if a.mode == "resource-extension":
        require(a.extension_root and a.extension_report_dir and a.extension_state, "Extension root/report/terminal state required")
        require(summary.get("integrity_gate") is False, "Resource extension must retain original failed integrity qualification")
        extstate = load(a.extension_state)
        closed_object(extstate, "extension dispatcher", set(a.extension_terminal_status))
        derived = load(a.extension_report_dir / "SUMMARY.json")
        require(derived.get("schema") == "SETI_RESOURCE_AMENDED_DERIVATIVE_GAMMA16_SUMMARY_V1", "Wrong separate derivative summary")
        require(derived.get("original_summary_sha256") == closure["original_frozen_summary_sha256"], "Derivative original-summary binding differs")
        require(derived.get("original_trial_qualification") == "FAIL_CLOSED_RESOURCE_GUARD_STOP", "Original qualification must remain FAIL")
        require(derived.get("original_summary_integrity_gate") is False and derived.get("original_summary_joint_gate") is False, "Original gates must remain failed")
        require(derived.get("status") in {"PASS_DERIVATIVE_GAMMA16_CONTROLS_UNDER_RESOURCE_AMENDMENT", "FAIL_CLOSED_DERIVATIVE_GAMMA16_CONTROLS"}, "Derivative status not qualified")
        require(derived.get("qualified_SETI_detection") is False and derived.get("original_A_B") == "FAIL_CLOSED", "Derivative qualification changed")
        require(derived.get("terminal_no_live_workers") is True, "Derivative report lacks terminal closure")
        require(derived.get("exposed") == {"status": "NOT_RUN_BLOCKED_BY_ORIGINAL_ADMISSION_GUARD", "cases": 9, "measured_candidates": None}, "Nine unavailable real bands must remain unavailable")
        # Reuse the reviewed pure metadata check also used by transport. This
        # imports no detector, creates no jobs, and does not recompute scores.
        # A derivative integrity failure may still be honestly published.
        validation_pin = pin(read(a.extension_validator))
        if derived.get("integrity_gate") is True:
            spec = importlib.util.spec_from_file_location("seti_publication_union_metadata", a.extension_validator)
            validator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(validator)
            validator.check_union_documents(load(a.extension_root / "UNION_LEDGER_GATE.json"), extstate,
                {name: load(a.extension_root / (name + "_RUN_STATE.json")) for name in ("PRIMARY_VALIDATION_EXTENSION", "QA_EXTENSION")},
                load(stage / "case_bank.json"), load(a.extension_root / "ADMISSION_SNAPSHOT.json"), derived)
        else:
            require(derived.get("joint_gate") is False and derived["status"] == "FAIL_CLOSED_DERIVATIVE_GAMMA16_CONTROLS", "An incomplete derivative cannot claim PASS")
        closure["extension"] = {"status": derived["status"], "terminal_dispatcher_status": extstate["status"],
            "dispatcher_pin": pin(read(a.extension_state)), "summary_pin": pin(read(a.extension_report_dir / "SUMMARY.json")),
            "integrity_gate": derived.get("integrity_gate"), "joint_gate": derived.get("joint_gate"),
            "resources_and_union_metadata": derived.get("resources_and_union_metadata"),
            "reused_union_validator": validation_pin,
            "all205_bound_union_metadata_check_passed": derived.get("integrity_gate") is True,
            "original_immutable_evidence_after_readback": derived.get("original_immutable_evidence_after_readback"),
            "original_exposed_bands": "NOT_RUN_BLOCKED; never imputed as zero"}
    elif a.extension_root or a.extension_report_dir or a.extension_state:
        raise ValueError("Extension inputs require explicit resource-extension mode")
    out.mkdir(parents=True)
    b = Builder(out, a.max_blob_bytes)
    b.tree(stage, PUBLIC, "original_frozen_metadata_results_and_full_phase_closures",
           lambda p: stage_selection(p) and p.as_posix() != "results/CALIBRATED_HITS.csv", pack_receipts=True)
    hits = stage / "results/CALIBRATED_HITS.csv"
    if hits.exists():
        b.archive_only(hits, stage.name + "/results/CALIBRATED_HITS.csv", a.owner_archive_locator,
                       "Large un-QAed raw-hypothesis table is retained only in the complete owner evidence archive; hypotheses are not validated candidates.")
    add_primary_receipt_index(b, stage, metrics, index)
    b.tree(reports, PUBLIC + "/report", "original_report")
    b.add(PUBLIC + "/REPORT.md", reports / "REPORT.md", "original_report_entrypoint")
    b.tree(evidence, PUBLIC + "/evidence", "original_byte_binding_evidence_and_receipt_copies", pack_receipts=True)
    b.add(PUBLIC + "/execution/SCHEDULER_STATE.json", a.original_scheduler, "full_original_scheduler_closure")
    if a.mode == "resource-extension":
        b.tree(a.extension_root, PUBLIC + "/resource_extension", "separate_external_resource_extension_metadata", extension_selection, pack_receipts=True)
        b.tree(a.extension_report_dir, PUBLIC + "/resource_extension/derived_report", "separate_derivative_report_and_union_evidence")
        b.add(PUBLIC + "/resource_extension/execution/TERMINAL_DISPATCHER_STATE.json", a.extension_state, "full_extension_terminal_dispatcher")
        b.add(PUBLIC + "/publication_tools/resource_extension_pack.py", a.extension_validator, "shared_non_numerical_union_metadata_validation")
    prefix_dir = a.prepend_dir or (a.extension_report_dir if a.mode == "resource-extension" else reports)
    for name in DOCS:
        prefix = read(Path(prefix_dir) / (name.removesuffix(".md") + "_PREPEND.md"))
        require(prefix.strip() and b"{{" not in prefix, "Missing/unresolved final prepend text: " + name)
        links = ("\n\nOffentlig evidens: [oprindelig rapport](" + b.target(PUBLIC + "/REPORT.md") + "), [byteindeks](" + b.target(PUBLIC + "/evidence/EVIDENCE_INDEX.json") + ")" +
                 (", [separat ressourceudvidelse](" + PUBLIC + "/resource_extension/derived_report/REPORT.md)" if a.mode == "resource-extension" else "") + ".\n").encode()
        prior = read(base / name)
        newprefix = prefix + links + b"\n---\n\n"
        combined = newprefix + prior
        require(combined[len(newprefix):] == prior, "Base suffix changed")
        bases[name].update(prefix_bytes=len(newprefix), suffix_bytes_preserved=True, final_blob=gitblob(combined))
        b.add_bytes(name, combined, "overview_prepend_with_full_immutable_history")
    for spec in a.extra_file:
        destination, source = spec.split("=", 1)
        b.add(safe(destination), Path(source), "explicit_resource_witness_delivery_or_publication_receipt")
    for spec in a.extra_tree:
        destination, source = spec.split("=", 1)
        b.tree(Path(source), safe(destination), "explicit_small_evidence_tree")
    b.add(PUBLIC + "/publication_tools/build_publication.py", Path(__file__), "non_numerical_publication_builder")
    b.add(PUBLIC + "/publication_tools/USAGE.md", Path(__file__).with_name("USAGE.md"), "publication_and_readback_instructions")
    return b.finish(a.base_commit, tree["sha"], a.branch, closure, bases)


def prepare_amendment(a):
    """Prepare prospective resource-change publication before extension GO."""
    stage, base, amendment = a.stage.resolve(), a.base_dir.resolve(), a.amendment_root.resolve()
    roots = [stage, base, amendment, a.prepend_dir.resolve()]
    roots += [Path(x.split("=", 1)[1]) for x in a.extra_tree]
    out = external_output(a.out, roots)
    commit, tree = load(a.base_commit_json), load(a.base_tree_json)
    bases = verify_base(commit, tree, base, a.base_commit, DOCS)
    scope_bytes, go_bytes = read(stage / "SCOPE.json"), read(stage / "GO.json")
    require(sha(scope_bytes) == SCOPE_SHA, "Wrong original frozen scope")
    scope, go = parse(scope_bytes), parse(go_bytes)
    require(go.get("scope_sha256") == SCOPE_SHA and go.get("status") == "ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK", "Original exact-public GO differs")
    for row in scope["code_pins"]:
        data = read(stage / safe(row["path"]))
        require(sha(data) == row["sha256"] and len(data) == row["bytes"], "Original frozen source differs")
    scheduler = load(a.original_scheduler)
    closed_object(scheduler, "original stopped scheduler", {"STOPPED_RETAINED_NO_RETRY"})
    require(scheduler.get("scope_sha256") == SCOPE_SHA, "Original scheduler scope differs")
    phases = {}
    for name in PHASES:
        path = stage / (name + "_RUN_STATE.json")
        if path.exists():
            phase = load(path)
            closed_object(phase, name)
            require(all(j.get("wait4_reaped") is True for j in phase.get("jobs", [])), "Original unreconciled child in " + name)
            phases[name] = {"status": phase["status"], "reaped_jobs": len(phase.get("jobs", [])),
                "unsubmitted_indices": phase.get("unsubmitted", []), **pin(read(path))}
        else:
            phases[name] = {"status": "ABSENT_NOT_MEASURED"}
    frozen_summary = load(stage / "results/SUMMARY.json")
    require(frozen_summary.get("integrity_gate") is False and frozen_summary.get("joint_gate") is False,
            "Original frozen failure SUMMARY must remain failed")
    out.mkdir(parents=True)
    b = Builder(out, a.max_blob_bytes)
    def closure_only(p):
        return (len(p.parts) == 1 and (p.name.endswith("_RUN_STATE.json") or p.name in {"SCOPE.json", "GO.json"})) or (
            len(p.parts) == 2 and p.parts[0] == "results" and p.suffix.lower() in {".json", ".csv"})
    b.tree(stage, PUBLIC, "original_terminal_failure_closure_unchanged", closure_only)
    b.add(PUBLIC + "/execution/SCHEDULER_STATE.json", a.original_scheduler, "original_full_terminal_scheduler")
    b.tree(amendment, PUBLIC + "/resource_extension", "prospective_resource_amendment_code_and_review")
    for spec in a.extra_file:
        destination, source = spec.split("=", 1)
        b.add(safe(destination), Path(source), "explicit_closed_or_prospective_receipt")
    for spec in a.extra_tree:
        destination, source = spec.split("=", 1)
        b.tree(Path(source), safe(destination), "explicit_closed_or_prospective_evidence_tree")
    for name in DOCS:
        prefix = read(a.prepend_dir / (name.removesuffix(".md") + "_PREPEND.md"))
        require(prefix.strip() and b"{{" not in prefix, "Missing/unresolved prospective prefix")
        prior = read(base / name)
        prefix += b"\n\n---\n\n"
        combined = prefix + prior
        require(combined[len(prefix):] == prior, "Historical base suffix changed")
        bases[name].update(prefix_bytes=len(prefix), suffix_bytes_preserved=True, final_blob=gitblob(combined))
        b.add_bytes(name, combined, "prospective_prepend_preserving_entire_history")
    b.add(PUBLIC + "/publication_tools/build_publication.py", Path(__file__), "non_numerical_publication_preparation")
    b.add(PUBLIC + "/publication_tools/USAGE.md", Path(__file__).with_name("USAGE.md"), "publication_and_readback_instructions")
    closure = {"mode": "prospective_resource_amendment_before_GO", "scope_sha256": SCOPE_SHA,
        "GO_sha256": sha(go_bytes), "original_scheduler_status": scheduler["status"],
        "original_phase_closures": phases, "original_frozen_summary_pin": pin(read(stage / "results/SUMMARY.json")),
        "original_frozen_integrity_gate": False, "original_frozen_joint_gate": False,
        "no_extension_outcomes_read": True, "no_extension_GO_asserted": True,
        "original_A_B": "FAIL_CLOSED", "qualified_SETI_detection": False}
    return b.finish(a.base_commit, tree["sha"], a.branch, closure, bases)


def verify_readback(a):
    expected = load(a.bundle / "EXPECTED_BLOBS.json")
    require(a.blob_root.resolve() != (a.bundle / "payload").resolve() and a.bundle.resolve() not in a.blob_root.resolve().parents,
            "Immutable readback bytes must be downloaded separately from the prepared local payload")
    commit, tree = load(a.commit_json), load(a.tree_json)
    require(commit.get("sha") == a.commit, "Readback commit SHA differs")
    require(commit.get("tree", {}).get("sha") == tree.get("sha"), "Readback commit/tree differs")
    require([x.get("sha") for x in commit.get("parents", [])] == [expected["expected_parent_sha"]], "Readback commit parent differs")
    rows = tree_rows(tree)
    lookup = {r["path"]: r for r in rows}
    require(len(lookup) == len(rows), "Duplicate paths in immutable tree readback")
    checked = []
    for name, declaration in sorted(expected["files"].items()):
        require(name in lookup and lookup[name].get("type") == "blob" and lookup[name].get("mode") == "100644"
                and lookup[name].get("sha") == declaration["git_blob_sha"], "Immutable tree blob differs: " + name)
        data = read(a.blob_root / safe(name))
        require(pin(data) == {k: declaration[k] for k in ("bytes", "sha256", "git_blob_sha")}, "Immutable blob bytes differ: " + name)
        checked.append({"path": name, **pin(data)})
    receipt = {"schema": "SETI_EXACT_PUBLICATION_READBACK_V1", "status": "ALL_EXPECTED_PUBLIC_BLOBS_EXACT",
               "repository": expected["repository"], "branch": expected["branch"], "commit_sha": a.commit,
               "tree_sha": tree["sha"], "parent_sha": expected["expected_parent_sha"],
               "expected_manifest_sha256": sha(read(a.bundle / "EXPECTED_BLOBS.json")),
               "verified_blobs": len(checked), "files": checked,
               "ref_head_verified_separately_required": True, "scientific_qualification_not_changed": True}
    require(a.receipt.resolve() not in [a.commit_json.resolve(), a.tree_json.resolve()], "Readback receipt would overwrite input")
    write(a.receipt, jb(receipt))
    return {"status": receipt["status"], "commit_sha": a.commit, "verified_blobs": len(checked), "receipt": str(a.receipt)}


def prepare_main(a):
    proof = load(a.research_readback)
    require(proof.get("schema") == "SETI_EXACT_PUBLICATION_READBACK_V1" and proof.get("status") == "ALL_EXPECTED_PUBLIC_BLOBS_EXACT", "Verified research publication required before main preparation")
    require(proof.get("repository") == REPOSITORY and proof.get("branch") != "main", "Research readback identity differs")
    result_commit = proof["commit_sha"]
    require(re.fullmatch(r"[0-9a-f]{40}", result_commit or ""), "Exact verified research commit required")
    base = a.base_file.resolve()
    out = external_output(a.out, [base.parent, a.prepend_file.resolve().parent])
    commit, tree = load(a.base_commit_json), load(a.base_tree_json)
    # Main base is stored locally under a descriptive filename; verify its actual README path.
    data = read(base)
    require(commit.get("sha") == a.base_commit and commit.get("tree", {}).get("sha") == tree.get("sha"), "Main base commit/tree mismatch")
    row = next((r for r in tree_rows(tree) if r["path"] == "README.md"), {})
    require(row.get("sha") == gitblob(data), "Full main README base differs from exact immutable tree")
    prefix = read(a.prepend_file)
    require(prefix.strip() and b"{{" not in prefix, "Missing/unresolved main prepend")
    url = f"https://github.com/{REPOSITORY}/blob/{result_commit}/{PUBLIC}"
    prefix += ("\n\nVerificeret forskning: [rapport](" + url + "/REPORT.md), [byteindeks](" + url + "/evidence/EVIDENCE_INDEX.json).\n\n---\n\n").encode()
    out.mkdir(parents=True)
    b = Builder(out, a.max_blob_bytes)
    b.add_bytes("README.md", prefix + data, "main_overview_prepend_full_history_preserved")
    bases = {"README.md": {**pin(data), "prefix_bytes": len(prefix), "suffix_bytes_preserved": True}}
    return b.finish(a.base_commit, tree["sha"], "main", {"mode": "main_overview_only"}, bases,
                    [{"research_commit_sha": result_commit, "readback_sha256": sha(read(a.research_readback))}], public_build=False)


def cli():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("prepare-research")
    for name in ("stage", "report-dir", "evidence-dir", "base-dir", "base-commit-json", "base-tree-json", "original-scheduler", "out"):
        r.add_argument("--" + name, type=Path, required=True)
    r.add_argument("--base-commit", default=BASE_HEAD)
    r.add_argument("--branch", required=True)
    r.add_argument("--mode", choices=("complete", "failure", "resource-extension"), required=True)
    r.add_argument("--extension-root", type=Path)
    r.add_argument("--extension-report-dir", type=Path)
    r.add_argument("--extension-state", type=Path)
    r.add_argument("--extension-terminal-status", action="append", default=[])
    r.add_argument("--extension-validator", type=Path, default=Path(__file__).resolve().parents[1] / "reporting_sixscan/resource_extension_pack.py")
    r.add_argument("--prepend-dir", type=Path)
    r.add_argument("--extra-file", action="append", default=[], metavar="REPO_PATH=LOCAL_FILE")
    r.add_argument("--extra-tree", action="append", default=[], metavar="REPO_PREFIX=LOCAL_DIRECTORY")
    r.add_argument("--max-blob-bytes", type=int, default=4 * 1024 * 1024)
    r.add_argument("--owner-archive-locator", default="Complete owner evidence archive; durable file/part IDs must be taken from the final delivery receipt. This builder does not claim upload success.")
    q = sub.add_parser("prepare-amendment")
    for name in ("stage", "base-dir", "base-commit-json", "base-tree-json", "original-scheduler", "amendment-root", "prepend-dir", "out"):
        q.add_argument("--" + name, type=Path, required=True)
    q.add_argument("--base-commit", default=BASE_HEAD)
    q.add_argument("--branch", required=True)
    q.add_argument("--extra-file", action="append", default=[], metavar="REPO_PATH=LOCAL_FILE")
    q.add_argument("--extra-tree", action="append", default=[], metavar="REPO_PREFIX=LOCAL_DIRECTORY")
    q.add_argument("--max-blob-bytes", type=int, default=4 * 1024 * 1024)
    v = sub.add_parser("verify-readback")
    for name in ("bundle", "commit-json", "tree-json", "blob-root", "receipt"):
        v.add_argument("--" + name, type=Path, required=True)
    v.add_argument("--commit", required=True)
    m = sub.add_parser("prepare-main")
    for name in ("base-file", "base-commit-json", "base-tree-json", "prepend-file", "research-readback", "out"):
        m.add_argument("--" + name, type=Path, required=True)
    m.add_argument("--base-commit", required=True)
    m.add_argument("--max-blob-bytes", type=int, default=4 * 1024 * 1024)
    args = p.parse_args()
    if args.command == "prepare-research" and args.mode == "resource-extension":
        require(args.extension_terminal_status, "Explicit accepted terminal extension status required; never guess dispatcher schema")
    result = {"prepare-research": prepare_research, "prepare-amendment": prepare_amendment,
              "verify-readback": verify_readback, "prepare-main": prepare_main}[args.command](args)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    cli()
