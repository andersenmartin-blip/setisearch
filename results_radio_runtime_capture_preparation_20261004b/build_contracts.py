"""Preparation-only capture-b contracts; never dispatches or imports a producer.

Runtime bytes are represented by a separately completed bounded preread. This
builder opens only small repository preparation inputs and the empty new root.
The fresh activation marker, detached publication proof and live execution are
separate operations. No local self-created hash grants scientific authority.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

IDENTITY = "e3d5aae494ef041c668a9fbec11edc2ac821a0e27bef15588181d166e125736c"
PLAN_SHA = "fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25"
PLAN_REL = "results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json"
HERE_REL = "results_radio_runtime_capture_preparation_20261004b"
PROTOCOL_REL = "RADIO_RUNTIME_METADATA_CAPTURE_2026-10-04B_PROTOCOL.md"
CHILD_REL = "config/radio_runtime_metadata_capture_20261004b.collector.json"
FREEZE_REL = "config/radio_runtime_metadata_capture_20261004b.freeze.json"
ACTIVATION_REL = "config/radio_runtime_metadata_capture_20261004b.activate.json"
ROOT_IDENTITY = {"device": 27, "inode": 1575156, "mode": "0700"}
MIB = 1024 ** 2
AUTHORITY_KEYS = (
    "acquisition_authorized", "allocation_created", "cas_qualified", "certificate_issued",
    "download_authorized", "execution_authorized", "hosted_transport_qualified",
    "installation_authorized", "metadata_capture_dispatch_authorized", "reservation_authorized",
    "rng_authorized", "runtime_import_authorized", "runtime_qualified",
    "scientific_execution_authorized", "source_contract_admitted", "spectral_access_authorized")


class PreparationError(Exception):
    pass


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PreparationError("duplicate JSON field")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(PreparationError("nonfinite JSON")))
    except (ValueError, UnicodeError) as exc:
        raise PreparationError("invalid JSON") from exc


def absolute(path):
    if type(path) is not str or not path.startswith("/") or str(Path(path)) != path or ".." in Path(path).parts or "\0" in path:
        raise PreparationError("canonical absolute path required")
    return path


def valid_pin(pin):
    if type(pin) is not dict or set(pin) != {"path", "bytes", "sha256", "mode"}:
        raise PreparationError("exact input pin required")
    absolute(pin["path"])
    if type(pin["bytes"]) is not int or not 0 <= pin["bytes"] <= 64 * MIB:
        raise PreparationError("finite pin bytes")
    if type(pin["sha256"]) is not str or len(pin["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in pin["sha256"]):
        raise PreparationError("SHA-256 pin required")
    if pin["mode"] not in ("0644", "0755"):
        raise PreparationError("regular mode pin required")
    return pin


def pin_for(path, raw, mode="0644"):
    return valid_pin({"path": str(path), "bytes": len(raw), "sha256": sha(raw), "mode": mode})


def read_preparation(path, cap=2 * MIB):
    """Read bounded sole-link repository input through held no-follow ancestors."""
    parts = Path(absolute(str(path))).parts[1:]
    if len(parts) > 64:
        raise PreparationError("finite path depth")
    directories = [os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)]
    bindings, fd = [], None
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directories[-1])
            info = os.fstat(child)
            bindings.append((directories[-1], part, info.st_dev, info.st_ino))
            directories.append(child)
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directories[-1])
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > cap:
            raise PreparationError("bounded sole-link regular input required")
        chunks, total = [], 0
        while total < before.st_size:
            chunk = os.read(fd, min(65536, before.st_size - total))
            if not chunk:
                raise PreparationError("input truncated during read")
            chunks.append(chunk)
            total += len(chunk)
        after = os.fstat(fd)
        named = os.stat(parts[-1], dir_fd=directories[-1], follow_symlinks=False)
        signature = lambda p: (p.st_dev, p.st_ino, p.st_mode, p.st_nlink, p.st_size, p.st_mtime_ns, p.st_ctime_ns)
        if signature(before) != signature(after) or signature(after) != signature(named):
            raise PreparationError("input changed during read")
        for directory, part, dev, inode in bindings:
            info = os.stat(part, dir_fd=directory, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != (dev, inode):
                raise PreparationError("input ancestor changed")
        raw = b"".join(chunks)
        return raw, pin_for(path, raw, format(stat.S_IMODE(before.st_mode), "04o"))
    finally:
        if fd is not None:
            os.close(fd)
        for directory in reversed(directories):
            os.close(directory)


def input_paths(repo):
    here = repo / HERE_REL
    return sorted([here / "collector.py", here / "elf_metadata.py", here / "capture_gate.py",
                   here / "runtime-preread-pins.json", repo / PROTOCOL_REL, repo / PLAN_REL], key=str)


def validate_ready(ready, artifacts, validation_artifacts, identity=IDENTITY):
    if type(ready) is not dict or set(ready) != {"schema", "capture_identity", "status", "input_pins", "validation_pins"}:
        raise PreparationError("exact final readiness schema required")
    if ready["schema"] != "radio-runtime-capture-b-inputs-ready-v1" or ready["capture_identity"] != identity or ready["status"] != "FINAL_FOR_CONTRACT_PREPARATION":
        raise PreparationError("new final input readiness required")
    pins = ready["input_pins"]
    if type(pins) is not list or any(type(p) is not dict for p in pins) or pins != sorted(pins, key=lambda p: p.get("path", "")):
        raise PreparationError("sorted readiness pin list required")
    for pin in pins:
        valid_pin(pin)
    if len(pins) != len(artifacts) or len({p["path"] for p in pins}) != len(pins):
        raise PreparationError("readiness duplicate or incomplete")
    for pin in pins:
        if pin["path"] not in artifacts or pin != artifacts[pin["path"]][1] or sha(artifacts[pin["path"]][0]) != pin["sha256"]:
            raise PreparationError("final preparation input drift")
    checks = ready["validation_pins"]
    if type(checks) is not list or len(checks) != 6 or any(type(p) is not dict for p in checks) or checks != sorted(checks, key=lambda p: p.get("path", "")):
        raise PreparationError("bounded final validation-only pins required")
    if len({p["path"] for p in checks}) != len(checks) or {p["path"] for p in checks} != set(validation_artifacts):
        raise PreparationError("validation-only input mismatch")
    if set(validation_artifacts) & set(artifacts):
        raise PreparationError("validation-only inputs overlap prospective capture dependencies")
    test_names = {Path(p).name for p in validation_artifacts if p.endswith(".py")}
    log_paths = [p for p in validation_artifacts if p.endswith(".log")]
    if test_names != {"test_capture_gate.py", "test_collector.py", "test_elf_metadata.py"} or len(log_paths) != 3:
        raise PreparationError("three exact producer tests and three final logs required")
    for pin in checks:
        valid_pin(pin)
        if pin != validation_artifacts[pin["path"]][1] or sha(validation_artifacts[pin["path"]][0]) != pin["sha256"]:
            raise PreparationError("final validation-only input drift")
    for path in log_paths:
        raw = validation_artifacts[path][0]
        if not raw.rstrip().endswith(b"\nOK") or b"\nRan " not in raw or b" tests in " not in raw:
            raise PreparationError("successful final producer test log required")


def proof_upper_bound(repo, supervisor):
    """Canonical full-body proof bound, including maximum JSON provenance escaping.

    Git identities have fixed lengths. Pin row bytes and base64 lengths are exact.
    One Unicode scalar can need twelve ASCII JSON escape bytes; 2048 scalars is
    therefore conservative for the producer's provenance character ceiling.
    """
    rows = []
    for pin in supervisor["source_pins"]:
        rows.append({**pin, "repository_path": str(Path(pin["path"]).relative_to(repo)),
                     "git_blob": "a" * 40, "content_base64": "A" * (4 * ((pin["bytes"] + 2) // 3))})
    proof = {"schema": "radio-runtime-metadata-capture-publication-readback-v1",
             "repository": "andersenmartin-blip/setisearch", "branch": "m43-support-qualification",
             "prepared_commit": "a" * 40, "prepared_tree": "a" * 40,
             "activation_commit": "b" * 40, "activation_tree": "b" * 40, "activation_parent": "a" * 40,
             "activation_changed_path": ACTIVATION_REL, "contract_sha256": "a" * 64,
             "publication_files": rows, "activation_sha256": "a" * 64,
             "capture_identity": IDENTITY, "collector_contract_sha256": supervisor["collector_contract_sha256"],
             "plan_sha256": PLAN_SHA, "provenance": "\U00010000" * 2048}
    marker = {"schema": "radio-runtime-metadata-capture-activation-v1", "capture_identity": IDENTITY,
              "prepared_commit": "a" * 40, "prepared_tree": "a" * 40,
              "contract_sha256": "a" * 64, "engineering_only": True, "single_use": True}
    return len(canonical(proof)), len(canonical(marker))


def assemble(repo, output_root, artifacts, ready, validation_artifacts):
    """Pure assembly from already-read repository inputs and preread pin rows."""
    repo, output_root = Path(absolute(str(repo))), Path(absolute(str(output_root)))
    expected_paths = {str(p) for p in input_paths(repo)}
    if set(artifacts) != expected_paths:
        raise PreparationError("exact acyclic preparation input set required")
    validate_ready(ready, artifacts, validation_artifacts)
    for path, (raw, pin) in artifacts.items():
        if type(raw) is not bytes or pin_for(path, raw, pin["mode"]) != pin:
            raise PreparationError("artifact raw pin mismatch")
    plan_raw, plan_pin = artifacts[str(repo / PLAN_REL)]
    plan = parse(plan_raw)
    if plan_pin["sha256"] != PLAN_SHA or plan.get("schema") != "radio-source-bound-runtime-materialization-plan-v1" or plan.get("status") != "PENDING" or plan.get("evidence_domain") != "inert-metadata-preparation-only" or plan.get("authority") != {k: False for k in AUTHORITY_KEYS}:
        raise PreparationError("original inert plan unchanged required")
    preread_raw, _ = artifacts[str(repo / HERE_REL / "runtime-preread-pins.json")]
    preread = parse(preread_raw)
    if type(preread) is not dict or preread.get("schema") != "radio-runtime-metadata-prospective-preread-pins-v1" or preread.get("capture_identity") != IDENTITY:
        raise PreparationError("fresh completed preread required")
    selected = preread.get("selected_files")
    if type(selected) is not list or not selected or len(selected) + 7 > 1024:
        raise PreparationError("finite explicit runtime cohort required")
    files, runtimes = [], []
    for row in selected:
        if type(row) is not dict or set(row) != {"path", "role", "bytes", "sha256", "mode", "filesystem_mode"}:
            raise PreparationError("exact preread selected row")
        pin = {k: row[k] for k in ("path", "bytes", "sha256")} | {"mode": row["filesystem_mode"]}
        valid_pin(pin)
        if row["mode"] != {"0644": "100644", "0755": "100755"}[pin["mode"]] or row["role"] not in ("code", "input", "runtime", "elf", "plugin"):
            raise PreparationError("preread role/mode mapping")
        runtimes.append(pin)
        files.append({k: row[k] for k in ("path", "role", "bytes", "sha256", "mode")})
    if len({p["path"] for p in runtimes}) != len(runtimes) or set(p["path"] for p in runtimes) & expected_paths:
        raise PreparationError("runtime duplicate or preparation overlap")
    runtimes.sort(key=lambda p: p["path"])
    runtime_bytes = sum(p["bytes"] for p in runtimes)
    if preread.get("selected_file_count") != len(runtimes) or preread.get("selected_file_bytes") != runtime_bytes:
        raise PreparationError("completed preread cohort totals mismatch")
    python_path = absolute(preread.get("python_path"))
    python = next((p for p in runtimes if p["path"] == python_path), None)
    if python is None:
        raise PreparationError("interpreter exact selected runtime pin required")
    for path in sorted(expected_paths):
        pin = artifacts[path][1]
        # The preread manifest is parent provenance, not a child execution
        # dependency. Preserve the original 765+5 child closure without cycles.
        if path != str(repo / HERE_REL / "runtime-preread-pins.json"):
            files.append({**pin, "mode": {"0644": "100644", "0755": "100755"}[pin["mode"]],
                          "role": "code" if path.endswith(("/collector.py", "/elf_metadata.py", "/capture_gate.py")) else "input"})
    files.sort(key=lambda p: p["path"])
    for field, cap in (("loader_paths", 32), ("missing_paths", 16)):
        values = preread.get(field)
        if type(values) is not list or len(values) > cap or len(set(values)) != len(values):
            raise PreparationError("finite preread path list")
        for path in values:
            absolute(path)
        if field == "missing_paths" and set(values) & {p["path"] for p in files}:
            raise PreparationError("missing/existing paths overlap")
    if type(preread.get("distributions")) is not list or len(preread["distributions"]) > 3:
        raise PreparationError("finite static distributions")
    distribution_names = set()
    versions = {"numpy": "2.3.5", "h5py": "3.16.0", "hdf5plugin": "7.1.0"}
    existing_paths = {p["path"] for p in files}
    for distribution in preread["distributions"]:
        if (type(distribution) is not dict
                or set(distribution) != {"name", "metadata_path", "wheel_path", "record_path", "expected_version"}
                or distribution["name"] not in versions or distribution["name"] in distribution_names
                or distribution["expected_version"] != versions[distribution["name"]]):
            raise PreparationError("static distribution exact name/version")
        distribution_names.add(distribution["name"])
        for field in ("metadata_path", "wheel_path", "record_path"):
            if absolute(distribution[field]) not in existing_paths:
                raise PreparationError("static distribution input not selected")
    child = {"schema": "radio-runtime-metadata-capture-contract-v1", "evidence_domain": "metadata-capture-only",
             "capture_identity": IDENTITY, "capture_authorized": True,
             "externally_bound_publication_required": True, "activation_required": True,
             "plan_sha256": PLAN_SHA, "python_path": python_path, "python_sha256": python["sha256"],
             "files": files, "imports": [], "import_paths": [], "loader_paths": preread["loader_paths"],
             "distributions": preread["distributions"], "missing_paths": preread["missing_paths"],
             "limits": {"files": 1024, "per_file_bytes": 64 * MIB, "read_bytes": 140 * MIB,
                        "maps_bytes": MIB, "module_count": 4096, "result_bytes": MIB - 1,
                        "elf_program_headers": 1024, "elf_dynamic_entries": 4096,
                        "elf_strings": 512, "elf_string_bytes": 65536}}
    child_raw = canonical(child)
    if len(child_raw) > 262144:
        raise PreparationError("child contract finite CLI cap")
    sources = sorted([artifacts[p][1] for p in expected_paths] + [pin_for(repo / CHILD_REL, child_raw)], key=lambda p: p["path"])
    collector_path = str(repo / HERE_REL / "collector.py")
    if artifacts[collector_path][1]["bytes"] > 65536:
        raise PreparationError("bounded held collector bootstrap cap")
    supervisor = {"schema": "radio-runtime-metadata-capture-supervisor-v1", "capture_identity": IDENTITY,
                  "evidence_domain": "metadata-capture-only", "source_pins": sources, "runtime_pins": runtimes,
                  "python_executable": python_path, "python_sha256": python["sha256"],
                  "collector_path": collector_path, "collector_contract_path": str(repo / CHILD_REL),
                  "collector_contract_sha256": sha(child_raw), "plan_path": str(repo / PLAN_REL), "plan_sha256": PLAN_SHA,
                  "output_root": str(output_root), "output_root_identity": dict(ROOT_IDENTITY),
                  "spent_path": str(output_root / "spent.json"), "activation_path": str(repo / ACTIVATION_REL),
                  "limits": {"wall_seconds": 60, "child_seconds": 50, "reap_seconds": 5,
                             "artifact_bytes": 8 * MIB, "rss_bytes": 512 * MIB,
                             "read_bytes": 256 * MIB, "stream_bytes": MIB, "sample_count": 1200}}
    supervisor_raw = canonical(supervisor)
    if len(supervisor_raw) > 262144:
        raise PreparationError("supervisor contract finite preparation cap")
    proof_bound, marker_bytes = proof_upper_bound(repo, supervisor)
    if proof_bound > 2 * MIB:
        raise PreparationError("detached full source proof exceeds child CLI witness cap")
    parent_inventory = sum(p["bytes"] for p in sources + runtimes)
    child_inventory = sum(p["bytes"] for p in files)
    parent_cli = len(supervisor_raw) + proof_bound + marker_bytes
    # Parent CLI + one preliminary child-contract read + 2 complete selected
    # inventories + marker re-read. Held collector bootstrap does not re-read.
    # Terminal selected-file floor has a one-byte EOF/overflow allowance for
    # the first empty file encountered; zero actually received bytes cost zero.
    terminal_pin_eof_allowance = 1
    parent_known = parent_cli + len(child_raw) + 2 * parent_inventory + marker_bytes + terminal_pin_eof_allowance
    child_known = len(child_raw) + len(plan_raw) + proof_bound + 2 * child_inventory + 2 * MIB
    parent_cap, child_cap = 116 * MIB, 140 * MIB
    # The admission producer reserves 2 MiB beyond two selected inventory
    # passes. Sample/report artifact reserves are separate from read budgets.
    proc_minimum = 2 * MIB
    proc_single_record_cap = 16384 + 1  # Includes an actually received probe.
    parent_anchor_proc_bound = 3 * proc_single_record_cap
    terminal_pidfd_proc_bound = proc_single_record_cap
    # Each sample has six direct-child kernel records. Group successful raw
    # content is smaller than its retained base64 evidence ceiling; reserve one
    # additional full failed/probe record rather than infer unreceived bytes.
    proc_sample_read_bound = 6 * proc_single_record_cap + 128 * 1024 + proc_single_record_cap
    if parent_known + proc_minimum > parent_cap or child_known > child_cap:
        raise PreparationError("joined explicit-read headroom cannot cover prospective scope")
    pin_rows_bytes = len(canonical(sources + runtimes))
    # The dynamic gate accounts actual blocks/root bytes. Static logical room
    # deliberately reserves the full two streams and maximum escaped proof.
    artifact_fixed = 2 * pin_rows_bytes + proof_bound + 2 * MIB + 2 + 65536 + 512 * 1024 + 65536 + 16
    if artifact_fixed + 512 * 1024 > 8 * MIB:
        raise PreparationError("prospective artifact headroom cannot cover one bounded sample")
    headroom = {"schema": "radio-runtime-capture-b-preparation-headroom-v1", "capture_identity": IDENTITY,
                "status": "PROSPECTIVE_STATIC_BOUNDS_ONLY_NO_CAPTURE", "authority": {k: False for k in AUTHORITY_KEYS},
                "source_pin_count": len(sources), "runtime_pin_count": len(runtimes), "child_file_count": len(files),
                "collector_contract": {"bytes": len(child_raw), "sha256": sha(child_raw)},
                "supervisor_contract": {"bytes": len(supervisor_raw), "sha256": sha(supervisor_raw)},
                "full_source_publication_proof_upper_bound_bytes": proof_bound, "activation_marker_canonical_bytes": marker_bytes,
                "parent_inventory_one_pass_bytes": parent_inventory, "parent_inventory_two_pass_bytes": 2 * parent_inventory,
                "parent_cli_upper_bound_bytes": parent_cli, "parent_additional_preliminary_child_contract_read_bytes": len(child_raw),
                "parent_additional_marker_read_bytes": marker_bytes, "parent_known_explicit_read_upper_bound_bytes": parent_known,
                "parent_explicit_read_allocation_bytes": parent_cap, "parent_procfs_read_headroom_bytes": parent_cap - parent_known,
                "producer_admission_extra_read_guard_bytes": proc_minimum,
                "terminal_after_inventory_read_reservation_bytes": parent_inventory,
                "terminal_pin_eof_read_allowance_bytes": terminal_pin_eof_allowance,
                "terminal_pidfd_read_reservation_bytes": terminal_pidfd_proc_bound,
                "terminal_read_floor_bytes": parent_inventory + terminal_pin_eof_allowance + terminal_pidfd_proc_bound,
                "parent_anchor_kernel_read_upper_bound_bytes": parent_anchor_proc_bound,
                "one_live_sample_explicit_kernel_read_upper_bound_bytes": proc_sample_read_bound,
                "terminal_pidfd_kernel_read_upper_bound_bytes": terminal_pidfd_proc_bound,
                "conservative_maximum_full_size_sample_units_by_read_headroom":
                    (parent_cap - parent_known - parent_anchor_proc_bound - terminal_pidfd_proc_bound) // proc_sample_read_bound,
                "child_selected_inventory_two_pass_bytes": 2 * child_inventory,
                "child_cli_upper_bound_bytes": len(child_raw) + len(plan_raw) + proof_bound,
                "child_maps_two_pass_cap_bytes": 2 * MIB, "child_known_explicit_read_upper_bound_bytes": child_known,
                "child_explicit_read_reservation_bytes": child_cap, "child_explicit_read_headroom_bytes": child_cap - child_known,
                "joined_conservative_known_plus_parent_minimum_slack_bytes": parent_known + proc_minimum + child_cap,
                "joined_explicit_read_ceiling_bytes": 256 * MIB, "child_reservation_refunded": False,
                "streams_combined_declared_maximum_bytes": 2 * MIB, "streams_combined_reservation_with_probe_bytes": 2 * MIB + 2,
                "spent_record_static_reservation_bytes": 65536,
                "child_result_bytes_before_one_CLI_newline": MIB - 1,
                "artifact_fixed_conservative_logical_upper_bound_bytes": artifact_fixed,
                "artifact_remaining_logical_bytes": 8 * MIB - artifact_fixed,
                "group_snapshot_serialized_evidence_cap_bytes": 128 * 1024,
                "next_sample_and_terminal_report_cap_each_bytes": 512 * 1024, "accounting_slack_bytes": 65536,
                "preparation_live_child_dispatches": 0, "new_allocation_created": False,
                "engineering_subtotal_before_seconds": 970, "engineering_subtotal_before_artifact_MiB": 48,
                "engineering_subtotal_if_separately_activated_seconds": 1030,
                "engineering_subtotal_if_separately_activated_artifact_MiB": 56,
                "scientific_fields_pending": 11,
                "limitations": ["Static arithmetic cannot guarantee wall time or RSS success.",
                                "Actual block allocation and root-directory bytes require dynamic accounting.",
                                "1200 is a sample-count ceiling; maximum-sized samples are not all prepaid.",
                                "Optional proc reads preserve the full terminal pin reread and bounded terminal pidfd floor; insufficient optional room closes failed.",
                                "Explicit read accounting excludes implicit interpreter/kernel/loader reads.",
                                "Preread and builder scripts are administrative preparation, not dispatched dependencies.",
                                "No old capture identity/root/marker/proof/freeze is adopted."]}
    return child_raw, supervisor_raw, canonical(headroom)


def save_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
    with os.fdopen(fd, "wb") as handle:
        os.fchmod(handle.fileno(), 0o644)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    repo = Path(__file__).resolve().parent.parent
    here = repo / HERE_REL
    output = repo.parent / "radio-runtime-metadata-capture-20261004b"
    if output.is_symlink() or not output.is_dir() or output.resolve() != output or list(output.iterdir()):
        raise PreparationError("fresh empty b output root required")
    info = output.stat()
    if {"device": info.st_dev, "inode": info.st_ino, "mode": format(stat.S_IMODE(info.st_mode), "04o")} != ROOT_IDENTITY:
        raise PreparationError("externally supplied b root identity changed")
    targets = [repo / CHILD_REL, repo / FREEZE_REL, here / "headroom.json"]
    if any(os.path.lexists(p) for p in targets + [repo / ACTIVATION_REL]):
        raise PreparationError("new contracts/headroom/activation must not already exist")
    ready_raw, _ = read_preparation(here / "inputs-ready.json", 65536)
    ready = parse(ready_raw)
    if type(ready) is not dict or type(ready.get("validation_pins")) is not list:
        raise PreparationError("final readiness validation pins absent")
    validation_artifacts = {}
    for pin in ready["validation_pins"]:
        valid_pin(pin)
        path = Path(pin["path"])
        if path.parent != here or not (path.name.startswith("test_") and path.suffix == ".py" or path.suffix == ".log"):
            raise PreparationError("validation-only path outside new preparation source/log scope")
        validation_artifacts[str(path)] = read_preparation(path)
    artifacts = {str(p): read_preparation(p) for p in input_paths(repo)}
    results = assemble(repo, output, artifacts, ready, validation_artifacts)
    # All arithmetic and raw-body schema preparation precede the first write.
    for path, raw in zip(targets, results):
        save_new(path, raw)
    print(canonical({"status": "CONTRACTS_PREPARED_NO_CAPTURE", "capture_identity": IDENTITY,
                     "outputs": [pin_for(p, raw) for p, raw in zip(targets, results)],
                     "live_child_dispatches": 0, "allocation_created": False}).decode(), end="")


if __name__ == "__main__":
    try:
        main()
    except (PreparationError, OSError) as exc:
        raise SystemExit("CLOSED_FAILED_PREPARATION: " + str(exc))
