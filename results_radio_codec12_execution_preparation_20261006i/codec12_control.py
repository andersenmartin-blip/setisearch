"""Inert complete codec12 producer implementation.

No current entry point can dispatch this producer. The future outer admission
integration must authenticate its inputs and qualify the H lifetime requirements
before calling _run_after_outer_admission. No such integration exists here.
"""
import ast
import hashlib
import os
from pathlib import Path
import stat
import struct
import sys
import time
from types import SimpleNamespace

from contract import MIB, canonical, parse, same, selected_nodes, sha, verify_inputs, verify_receiver_contexts

JOURNAL_CAP = 2 * MIB
RECEIPT_CAP = 2 * MIB
ZERO_HASH = "0" * 64


def produce(*args, **kwargs):
    """Public dispatch stays closed until a separately published outer exists."""
    raise ValueError("BLOCKED: complete native lifetime and one-shot outer admission not supplied")


def _output_path(output, protected_root):
    output, protected_root = Path(output), Path(protected_root)
    if not protected_root.is_absolute() or protected_root.resolve() != protected_root or not protected_root.is_dir():
        raise ValueError("canonical immutable source root required")
    if (not output.is_absolute() or output.resolve() != output or output.exists()
            or output.is_symlink() or not output.parent.is_dir() or output.is_relative_to(protected_root)):
        raise ValueError("fresh canonical output outside immutable source tree required")
    return output


def storage_snapshot(root, cap):
    logical = allocated = 0
    for path in (root, *root.rglob("*")):
        st = path.lstat()
        if not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)) or (stat.S_ISREG(st.st_mode) and st.st_nlink != 1):
            raise ValueError("ordinary single-link output custody required")
        logical += st.st_size
        allocated += st.st_blocks * 512
    if max(logical, allocated) > cap:
        raise ValueError("aggregate logical/allocated output ceiling")
    return {"logical_bytes": logical, "allocated_bytes_snapshot": allocated}


def _write_all(fd, raw):
    offset = 0
    while offset < len(raw):
        count = os.write(fd, raw[offset:])
        if count <= 0:
            raise OSError("zero-length output write")
        offset += count


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json_new(path, value, maximum=RECEIPT_CAP):
    raw = canonical(value)
    if len(raw) > maximum:
        raise ValueError("receipt serialization ceiling")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        _write_all(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    _sync_directory(Path(path).parent)
    return {"bytes": len(raw), "sha256": sha(raw)}


class EventJournal:
    """Append, fsync, retain partial failures. No resume, truncation or replay."""
    def __init__(self, path, cap=JOURNAL_CAP):
        self.path, self.cap = Path(path), cap
        self.fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self.identity = (os.fstat(self.fd).st_dev, os.fstat(self.fd).st_ino)
        self.bytes, self.sequence, self.previous = 0, 0, ZERO_HASH
        self.closed = False
        _sync_directory(self.path.parent)

    def append(self, phase, value):
        if self.closed:
            raise ValueError("journal is closed")
        st = self.path.lstat()
        if (st.st_dev, st.st_ino) != self.identity or st.st_size != self.bytes or st.st_nlink != 1:
            raise ValueError("journal identity/length changed")
        event = {"sequence": self.sequence, "previous_sha256": self.previous, "phase": phase, "value": value}
        event["event_sha256"] = sha(canonical(event))
        raw = canonical(event)
        if self.bytes + len(raw) > self.cap:
            raise ValueError("journal byte ceiling before write")
        _write_all(self.fd, raw)
        os.fsync(self.fd)
        self.bytes += len(raw)
        self.sequence += 1
        self.previous = event["event_sha256"]
        return event

    def close(self):
        if not self.closed:
            os.close(self.fd)
            self.closed = True


def verify_journal(raw):
    if type(raw) is not bytes or len(raw) > JOURNAL_CAP or not raw or not raw.endswith(b"\n"):
        raise ValueError("complete bounded journal required")
    previous, events = ZERO_HASH, []
    for index, line in enumerate(raw.splitlines()):
        event = parse(line)
        if set(event) != {"sequence", "previous_sha256", "phase", "value", "event_sha256"}:
            raise ValueError("journal fields differ")
        same(event["sequence"], index)
        same(event["previous_sha256"], previous)
        body = {key: value for key, value in event.items() if key != "event_sha256"}
        same(event["event_sha256"], sha(canonical(body)))
        if canonical(event).rstrip(b"\n") != line:
            raise ValueError("journal is not canonical")
        previous = event["event_sha256"]
        events.append(event)
    return events


def file_pin(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or max(before.st_size, before.st_blocks * 512) > maximum:
            raise ValueError("output file byte/custody ceiling")
        digest, length = hashlib.sha256(), 0
        for block in iter(lambda: handle.read(MIB), b""):
            digest.update(block); length += len(block)
            if length > maximum:
                raise ValueError("output grew while hashing")
        after = os.fstat(handle.fileno())
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        current = Path(path).lstat()
        if length != before.st_size or any(getattr(before, key) != getattr(after, key)
                                          or getattr(before, key) != getattr(current, key) for key in fields):
            raise ValueError("output identity changed while hashing")
    return {"name": Path(path).name, "bytes": length, "allocated_bytes_snapshot": before.st_blocks * 512,
            "sha256": digest.hexdigest()}


def validate_row_receipts(rows):
    if type(rows) is not list or len(rows) != 16:
        raise ValueError("exact sixteen row receipts required")
    for i, row in enumerate(rows):
        if type(row) is not dict or set(row) != {"row", "selected_cells", "compressed_bytes", "compressed_sha256",
                                               "full_decoded_sha256", "native_descending_sha256", "ascending_raw_sha256", "normalized_sha256"}:
            raise ValueError("exact row receipt fields required")
        same(row["row"], i)
        same(row["selected_cells"], 65536)
        if type(row["compressed_bytes"]) is not int or not 0 < row["compressed_bytes"] <= 5 * MIB:
            raise ValueError("compressed row byte ceiling")
        for key in ("compressed_sha256", "full_decoded_sha256", "native_descending_sha256", "ascending_raw_sha256", "normalized_sha256"):
            value = row[key]
            if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("invalid row hash")


def handoff_receipt(scope, rows):
    validate_row_receipts(rows)
    return {"role": scope["role"], "scan": scope["scan"],
            "receiver_context_sha256": scope["receiver_context_sha256"],
            "receiver_bank_sha256": scope["receiver_bank_sha256"],
            "raw_row_sha256s": [row["native_descending_sha256"] for row in rows],
            "normalized_row_sha256s": [row["normalized_sha256"] for row in rows]}


def validate_complete_receipts(plan, handoffs):
    scopes = plan["scope"]["ordered_handoffs"]
    if type(handoffs) is not list or len(handoffs) != 12:
        raise ValueError("exact twelve ordered handoffs required")
    raw_sets = []
    for scope, record in zip(scopes, handoffs):
        if type(record) is not dict or set(record) != {"scope", "rows", "handoff", "encoder_pipeline", "legacy_pipeline", "files"}:
            raise ValueError("exact handoff receipt fields required")
        rows = record["rows"]
        same(record["scope"], scope)
        same(record["handoff"], handoff_receipt(scope, rows))
        same(record["legacy_pipeline"], plan["scope"]["legacy_pipeline"])
        same(record["encoder_pipeline"], [[32008, 1, [0, 4, 4, 0, 2]]])
        files = record["files"]
        if type(files) is not list or len(files) != 2:
            raise ValueError("exact encoder/legacy file receipts required")
        for name, pin in zip(("encoder.h5", "legacy.h5"), files):
            if type(pin) is not dict or set(pin) != {"name", "bytes", "allocated_bytes_snapshot", "sha256"}:
                raise ValueError("exact HDF5 file pin fields required")
            same(pin["name"], name)
            for key in ("bytes", "allocated_bytes_snapshot"):
                if type(pin[key]) is not int or not 0 < pin[key] <= plan["draft_envelope"]["each_hdf5_file_cap_bytes"]:
                    raise ValueError("HDF5 file byte ceiling")
            if type(pin["sha256"]) is not str or len(pin["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in pin["sha256"]):
                raise ValueError("invalid HDF5 file hash")
        raw_sets.append(tuple(row["native_descending_sha256"] for row in rows))
    if len(set(raw_sets)) != 12:
        raise ValueError("controlled raw row sets are not distinct")


def verify_success_journal(raw, plan, records, result):
    """A valid prefix is not completion: require every exact phase and result."""
    validate_complete_receipts(plan, records)
    events = verify_journal(raw)
    if len(events) != 602:
        raise ValueError("success journal requires all 602 events")
    same(events[0]["phase"], "started")
    position = 1
    for scope, record in zip(plan["scope"]["ordered_handoffs"], records):
        same(events[position]["phase"], "handoff_started")
        same(events[position]["value"], scope)
        position += 1
        for phase in ("encoded", "transferred", "row_verified"):
            for row in range(16):
                event = events[position]
                same(event["phase"], phase)
                same(event["value"]["handoff_index"], scope["handoff_index"])
                same(event["value"]["row"], row)
                if phase == "row_verified":
                    same({key: value for key, value in event["value"].items() if key != "handoff_index"}, record["rows"][row])
                position += 1
        same(events[position]["phase"], "handoff_complete")
        same(events[position]["value"], {"handoff_index": scope["handoff_index"], "receipt_sha256": sha(canonical(record))})
        position += 1
    same(events[position]["phase"], "completed")
    same(events[position]["value"], {"receipt_sha256": sha(canonical(result)), "handoffs_observed": 12})
    return {"events": len(events), "terminal_event_sha256": events[-1]["event_sha256"], "journal_sha256": sha(raw)}


def _compile(raw, selection, environment):
    nodes = selected_nodes(raw, selection)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<authenticated-maintained-nodes>", "exec"), environment)
    return environment


def _normalizer(np, inputs):
    contents, specs = inputs["contents"], inputs["selection"]["source_selections"]
    path = "src/seti_repeater/search_v0p6.py"
    errors = _compile(contents[path], specs[path], {"__name__": "_codec12_errors"})
    core = SimpleNamespace(V0P6ContractError=errors["V0P6ContractError"], V0P6CapacityError=errors["V0P6CapacityError"])
    path = "src/seti_repeater/source_v0p6.py"
    legacy = _compile(contents[path], specs[path], {"np": np, "core": core})
    path = "src/seti_repeater/source_m43h.py"
    result = _compile(contents[path], specs[path], {"np": np, "legacy": SimpleNamespace(
        normalize_float32_blocks_v0p6=legacy["normalize_float32_blocks_v0p6"])})
    return result["normalize_native_row"]


def _metadata_laws(inputs):
    """Execute authenticated H case definitions against the authenticated guard."""
    path = "src/seti_repeater/hdf5_filter_contract_radio.py"
    tree = ast.parse(inputs["contents"][path])
    if any(not isinstance(node, (ast.Expr, ast.FunctionDef)) for node in tree.body):
        raise ValueError("pure guard source capability differs")
    guard = {}
    exec(compile(tree, "<authenticated-filter-guard>", "exec"), guard)
    law_tree = ast.parse(inputs["h_raws"]["metadata_law_control.py"])
    # The H law body itself is unchanged; its filesystem guard opener is omitted.
    selected = [node for node in law_tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                and node.name in ("MetadataDataset", "observe")]
    if [node.name for node in selected] != ["MetadataDataset", "observe"]:
        raise ValueError("authenticated law definitions missing")
    import copy
    ns = {"copy": copy, "_guard": lambda _: guard, "GUARD_SHA256": sha(inputs["contents"][path]),
          "PIPELINE": inputs["plan"]["scope"]["legacy_pipeline"],
          "LAW_NAMES": tuple(row["name"] for row in inputs["plan"]["case_laws"])}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<authenticated-H-law-definitions>", "exec"), ns)
    observation = ns["observe"](None)
    same([{key: row[key] for key in ("index", "name", "expected")} for row in observation["cases"]], inputs["plan"]["case_laws"])
    return guard, observation


def _pattern(np, handoff_index, chunk, row):
    index = np.arange(1048576, dtype="<i8")
    numerator = 409600 + 256 * handoff_index + ((index * 17 + chunk * 31 + row * 13) % 4093) + 128 * ((index // 4096) % 17)
    return (numerator.astype("<f4") / np.float32(4096)).astype("<f4", copy=False)


def _scalar_selected_hash(handoff_index, chunk, row, start, stop, reverse=False):
    digest = hashlib.sha256()
    indices = range(stop - 1, start - 1, -1) if reverse else range(start, stop)
    for index in indices:
        numerator = 409600 + 256 * handoff_index + ((index * 17 + chunk * 31 + row * 13) % 4093) + 128 * ((index // 4096) % 17)
        digest.update(struct.pack("<f", numerator / 4096))
    return digest.hexdigest()


def _array_hash(array):
    return sha(memoryview(array).cast("B"))


def _check_file_size(path, maximum):
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or max(st.st_size, st.st_blocks * 512) > maximum:
        raise ValueError("controlled HDF5 file byte ceiling")


def read_filtered_chunk(dataset_id, offset, cap, expected=None):
    """Metadata ceiling/mask is checked before the native payload allocation."""
    info = dataset_id.get_chunk_info_by_coord(offset)
    if type(info.size) is not int or not 0 < info.size <= cap or type(info.filter_mask) is not int or info.filter_mask != 0:
        raise ValueError("compressed metadata size/mask before allocation")
    if expected is not None and info.size != expected["compressed_bytes"]:
        raise ValueError("retained compressed length before allocation")
    mask, payload = dataset_id.read_direct_chunk(offset)
    if type(mask) is not int or mask != 0 or type(payload) is not bytes or len(payload) != info.size:
        raise ValueError("compressed payload metadata differs")
    if expected is not None and sha(payload) != expected["compressed_sha256"]:
        raise ValueError("retained compressed bytes differ")
    return payload


def _one_handoff(np, h5py, plugin, normalize, guard, inputs, scope, directory, output, journal):
    plan, envelope = inputs["plan"], inputs["plan"]["draft_envelope"]
    shape, chunks = tuple(plan["scope"]["source_shape"]), tuple(plan["scope"]["source_chunks"])
    pipeline = plan["scope"]["legacy_pipeline"]
    chunk, handoff_index = scope["chunk_index"], scope["handoff_index"]
    origin = chunk * chunks[2]
    lo, hi = scope["archive_interval"]
    encoder, legacy = directory / "encoder.h5", directory / "legacy.h5"
    cache = 8 * MIB
    with h5py.File(encoder, "x", rdcc_nbytes=cache) as handle:
        dataset = handle.create_dataset("data", shape=shape, chunks=chunks, dtype="<f4",
                                        **plugin.Bitshuffle(nelems=0, cname="lz4"))
        creation = dataset.id.get_create_plist()
        if creation.get_nfilters() != 1:
            raise ValueError("one current encoder filter required")
        encoder_pipeline = guard["signature"]([creation.get_filter(0)])
        same(encoder_pipeline, [[32008, 1, [0, 4, 4, 0, 2]]])
        for row in range(16):
            values = _pattern(np, handoff_index, chunk, row)
            dataset[row, 0, origin:origin + chunks[2]] = values
            del values
            handle.flush()
            _check_file_size(encoder, envelope["each_hdf5_file_cap_bytes"])
            storage_snapshot(output, envelope["leaf_output_cap_bytes"])
            journal.append("encoded", {"handoff_index": handoff_index, "row": row})
        if dataset.id.get_num_chunks() != 16:
            raise ValueError("exact sixteen current encoder chunks required")
    search_paths = [h5py.h5pl.get(i) for i in range(h5py.h5pl.size())]
    compressed = []
    try:
        for i in range(h5py.h5pl.size() - 1, -1, -1):
            h5py.h5pl.remove(i)
        if not h5py.h5z.unregister_filter(32008) or h5py.h5z.filter_avail(32008):
            raise ValueError("optional legacy declaration isolation failed")
        with h5py.File(legacy, "x", rdcc_nbytes=cache) as handle:
            creation = h5py.h5p.create(h5py.h5p.DATASET_CREATE)
            creation.set_chunk(chunks)
            creation.set_filter(32008, h5py.h5z.FLAG_OPTIONAL, tuple(pipeline[0][2]))
            creation.set_fill_time(h5py.h5d.FILL_TIME_NEVER)
            dataset = h5py.Dataset(h5py.h5d.create(handle.id, b"data", h5py.h5t.IEEE_F32LE,
                                                 h5py.h5s.create_simple(shape), dcpl=creation))
            guard["check_dataset"](dataset, pipeline)
            with h5py.File(encoder, "r", rdcc_nbytes=cache) as encoded:
                for row in range(16):
                    offset = (row, 0, origin)
                    payload = read_filtered_chunk(encoded["data"].id, offset, envelope["compressed_payload_cap_bytes"])
                    record = {"row": row, "compressed_bytes": len(payload), "compressed_sha256": sha(payload)}
                    dataset.id.write_direct_chunk(offset, payload, filter_mask=0)
                    del payload
                    handle.flush()
                    _check_file_size(legacy, envelope["each_hdf5_file_cap_bytes"])
                    storage_snapshot(output, envelope["leaf_output_cap_bytes"])
                    journal.append("transferred", {"handoff_index": handoff_index, **record})
                    compressed.append(record)
    finally:
        for i in range(h5py.h5pl.size() - 1, -1, -1):
            h5py.h5pl.remove(i)
        for path in search_paths:
            h5py.h5pl.append(path)
        if not plugin.register(filters=32008, force=True):
            raise ValueError("filter restoration failed")
    rows = []
    with h5py.File(legacy, "r", rdcc_nbytes=cache) as handle:
        dataset = handle["data"]
        guard["check_dataset"](dataset, pipeline)
        if dataset.shape != shape or dataset.chunks != chunks or dataset.dtype.str != "<f4" or dataset.id.get_num_chunks() != 16:
            raise ValueError("exact legacy geometry/chunk count differs")
        for row in range(16):
            offset = (row, 0, origin)
            payload = read_filtered_chunk(dataset.id, offset, envelope["compressed_payload_cap_bytes"], compressed[row])
            del payload
            expected = _pattern(np, handoff_index, chunk, row)
            full = dataset[row, 0, origin:origin + chunks[2]]
            native = dataset[row, 0, lo:hi]
            if full.dtype.str != "<f4" or full.shape != (chunks[2],) or _array_hash(full) != _array_hash(expected):
                raise ValueError("decoded full chunk is not bit exact")
            expected_native = _scalar_selected_hash(handoff_index, chunk, row, lo - origin, hi - origin)
            expected_ascending = _scalar_selected_hash(handoff_index, chunk, row, lo - origin, hi - origin, reverse=True)
            if native.dtype.str != "<f4" or native.shape != (65536,) or _array_hash(native) != expected_native:
                raise ValueError("selected native row is not bit exact")
            ascending, normalized = normalize(native)
            if _array_hash(ascending) != expected_ascending or normalized.dtype.str != "<f4" or normalized.shape != (65536,):
                raise ValueError("ascending orientation or normalized shape differs")
            record = {**compressed[row], "full_decoded_sha256": _array_hash(full),
                      "native_descending_sha256": expected_native, "ascending_raw_sha256": expected_ascending,
                      "normalized_sha256": _array_hash(normalized), "selected_cells": 65536}
            journal.append("row_verified", {"handoff_index": handoff_index, **record})
            rows.append(record)
            del expected, full, native, ascending, normalized
    record = {"scope": scope, "rows": rows, "handoff": handoff_receipt(scope, rows),
              "encoder_pipeline": encoder_pipeline, "legacy_pipeline": pipeline,
              "files": [file_pin(path, envelope["each_hdf5_file_cap_bytes"]) for path in (encoder, legacy)]}
    write_json_new(directory / "handoff.json", record)
    journal.append("handoff_complete", {"handoff_index": handoff_index, "receipt_sha256": sha(canonical(record))})
    return record


def _run_after_outer_admission(repo_root, output, *, protected_root, runtime_prefix):
    """Future leaf body only; caller/outer authority is not implemented here.

    Do not invoke during source preparation. No safety/readiness inference can
    be made from possession of this private function or source-test fixtures.
    """
    if not sys.flags.isolated or not sys.dont_write_bytecode or Path(sys.prefix).resolve() != Path(runtime_prefix):
        raise ValueError("future isolated exact runtime required")
    if Path(repo_root) != Path(protected_root):
        raise ValueError("output exclusion must cover the entire authenticated repository root")
    # The future leaf never accepts caller-authored plan dictionaries or values.
    inputs = verify_inputs(repo_root)
    output = _output_path(output, protected_root)
    contexts = verify_receiver_contexts(inputs)
    output.mkdir(mode=0o700, exist_ok=False)
    _sync_directory(output.parent)
    journal = EventJournal(output / "events.jsonl")
    start, completed = time.monotonic(), []
    try:
        journal.append("started", {"plan_sha256": sha(inputs["h_raws"]["PLAN.json"]), "engineering_only": True})
        # Lazy native imports occur only in this future leaf body.
        import numpy as np
        import h5py
        import hdf5plugin
        import importlib.metadata
        runtime = {"numpy": np.__version__, "h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version,
                   "hdf5plugin": importlib.metadata.version("hdf5plugin")}
        same(runtime, inputs["plan"]["runtime_basis"]["versions_observed_in_closed_G"])
        guard, laws = _metadata_laws(inputs)
        write_json_new(output / "metadata-laws.json", laws)
        normalize = _normalizer(np, inputs)
        source = parse(inputs["contents"]["config/radio_hd189733_source_preparation_20260927.json"])
        for scan in source["scans"]:
            same(guard["declared"](scan, required=True), inputs["plan"]["scope"]["legacy_pipeline"])
        for scope in inputs["plan"]["scope"]["ordered_handoffs"]:
            directory = output / f"{scope['handoff_index']:02d}-{scope['role']}-{scope['scan']}"
            directory.mkdir(mode=0o700, exist_ok=False)
            _sync_directory(output)
            journal.append("handoff_started", scope)
            completed.append(_one_handoff(np, h5py, hdf5plugin, normalize, guard, inputs, scope, directory, output, journal))
        validate_complete_receipts(inputs["plan"], completed)
        result = {"schema": "codec12-complete-controlled-receipt-v1", "status": "OBSERVED_ENGINEERING_ONLY",
                  "plan_sha256": sha(inputs["h_raws"]["PLAN.json"]), "runtime": runtime,
                  "normalization_receiver_handoffs": [record["handoff"] for record in completed],
                  "handoff_receipt_pins": [{"relative_path": f"{record['scope']['handoff_index']:02d}-{record['scope']['role']}-{record['scope']['scan']}/handoff.json",
                                            "bytes": len(canonical(record)), "sha256": sha(canonical(record))}
                                           for record in completed],
                  "case_laws": [{key: row[key] for key in ("name", "expected", "observed")} for row in laws["cases"]],
                  "handoffs_observed": 12, "rows_verified": 192, "hdf5_files": 24,
                  "receiver_contexts": {role: {key: ctx[key] for key in ("context_sha256", "receiver_bank_sha256")}
                                        for role, ctx in contexts.items()},
                  "raw_row_convention": "native archive-descending selected float32 rows",
                  "elapsed_leaf_seconds_before_final_receipt": time.monotonic() - start,
                  "complete_codec_certificate_issued": False, "scientific_readiness": False,
                  "telescope_provenance": False, "archive_values_read": 0, "rng_draws": 0,
                  "network_requests": 0, "native_lifetime_qualification_issued_here": False}
        write_json_new(output / "codec12-receipt.json", result)
        journal.append("completed", {"receipt_sha256": sha(canonical(result)), "handoffs_observed": 12})
        storage_snapshot(output, inputs["plan"]["draft_envelope"]["leaf_output_cap_bytes"])
        return result
    except Exception as exc:
        failure = {"status": "FAILED_CLOSED", "exception_type": type(exc).__name__, "message": str(exc)[:4096],
                   "completed_handoffs": len(completed), "retry_permitted": False, "scientific_readiness": False}
        # Failed writes/quotas retain their partial original files; no cleanup.
        try:
            write_json_new(output / "failure.json", failure, 16 * 1024)
            journal.append("failed", failure)
        except Exception as persistence_error:
            # The original partial files stay in place. The outer stderr must
            # retain this secondary veto even if quota/disk failure forbids JSON.
            exc.add_note("failure_evidence_write_veto: " + type(persistence_error).__name__ + ": " + str(persistence_error)[:4096])
        raise
    finally:
        journal.close()


if __name__ == "__main__":
    raise SystemExit("BLOCKED_PREPARATION: no outer/native-lifetime dispatcher is installed")
