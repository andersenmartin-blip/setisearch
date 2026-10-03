"""Candidate local codec receipts -> receiver SyntheticSource handoff.

Only independently pinned local-fixture receipts at .invalid URLs cross this
boundary. Six fresh native row sets are normalized separately. This module
constructs NativeRun without invoking reduction, scores, controls or RNG.
Published receiver metadata remains ancestry, never telescope provenance.
"""
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
from urllib.parse import urlparse

import numpy as np

from seti_repeater import hdf5_filter_contract_radio as filters
from seti_repeater import pipeline_receiver_radio as pipeline
from seti_repeater import receiver_bank_radio as received
from seti_repeater import search_v0p6 as core
from seti_repeater import source_m43h as rows
from seti_repeater import source_radio as codec
from seti_repeater import transfer_m43g as native

SCHEMA = "radio-local-codec-receiver-binding-candidate-v1"
HANDOFF_SCHEMA = "radio-local-codec-receiver-handoff-candidate-v1"
ROLES = ("calibration", "validation", "pilot")
MAX_SOURCE_JSON_BYTES = 128 * 1024
MAX_ROW_JSON_BYTES = 4 * 1024


def _exact(left, right):
    """Type-sensitive JSON equality; bool/int and float/int are distinct."""
    return core.canonical_json_bytes(left) == core.canonical_json_bytes(right)


def _bounded_json(path, maximum):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 < before.st_size <= maximum):
            raise ValueError("receipt metadata must be one bounded regular file")
        payload = handle.read(maximum + 1)
        if len(payload) != before.st_size or len(payload) > maximum:
            raise ValueError("receipt metadata size changed during bounded read")
    return json.loads(payload)


def receiver_window(context):
    """Bound receiver metadata without carrying historical archive URLs."""
    p = json.loads(context.factor_contract.factors.provenance_json)
    return {
        "role": context.native_window["role"],
        "window": context.window,
        "receiver_window_identity": context.native_window["identity"],
        "archive_interval": context.native_window["archive_interval"],
        "geometry": asdict(context.geometry),
        "receiver_window_design_sha256": p["window_design_sha256"],
    }


@dataclass(frozen=True)
class FixtureBinding:
    manifest_json: str
    identity: str

    @property
    def record(self):
        return json.loads(self.manifest_json)

    def validate(self, context):
        if type(context) is not pipeline.Context:
            raise ValueError("typed receiver context required")
        context.validate()
        value = self.record
        expected_keys = {
            "schema", "domain", "window", "role", "context_sha256",
            "receiver_factor_bank_sha256", "receiver_source_contract_sha256",
            "fixture_source_contract_sha256", "receiver_window_identity",
            "archive_interval", "geometry", "receiver_window_design_sha256",
            "runtime", "scans",
        }
        p = json.loads(context.factor_contract.factors.provenance_json)
        if (set(value) != expected_keys or rows.digest(value) != self.identity
                or value["schema"] != SCHEMA or value["domain"] != "local-fixture"
                or value["context_sha256"] != context.identity
                or value["receiver_factor_bank_sha256"] != context.factor_contract.factors.identity
                or value["receiver_source_contract_sha256"] != p["source_contract_sha256"]
                or value["role"] not in ROLES
                or any(not _exact(value[k], v) for k, v in receiver_window(context).items())):
            raise ValueError("local codec/receiver binding or context ancestry changed")
        core._frozen_sha256(value["fixture_source_contract_sha256"], "fixture source contract")
        if not _exact(value["runtime"], codec.runtime()):
            raise ValueError("local codec/receiver runtime changed")
        entries = value["scans"]
        if (not isinstance(entries, list) or len(entries) != 6
                or any(not isinstance(e, dict) or set(e) != {"label", "scope", "receipt_sha256"}
                       for e in entries)
                or tuple(e["label"] for e in entries) != received.LABELS):
            raise ValueError("exact ordered six-scan local fixture inventory required")
        for entry, scan in zip(entries, context.scans, strict=True):
            core._frozen_sha256(entry["receipt_sha256"], "trusted local receipt")
            scope = entry["scope"]
            if not isinstance(scope, dict):
                raise ValueError("exact local source scope required")
            definition = scope["definition"]
            parsed = urlparse(definition["url"])
            # The receiver retains timing/header/chunk/filter ancestry. Remote
            # identity is replaced with an explicit local fixture identity.
            expected_definition = {k: v for k, v in scan.items()
                                   if k not in ("kind", "epoch", "url", "expected_remote_size_bytes", "expected_etag")}
            actual_definition = {k: v for k, v in definition.items()
                                 if k not in ("url", "expected_remote_size_bytes", "expected_etag")}
            if (not _exact(actual_definition, expected_definition)
                    or definition["label"] != entry["label"]
                    or parsed.scheme != "https" or not parsed.hostname
                    or not parsed.hostname.endswith(".invalid")
                    or parsed.username or parsed.password or parsed.query or parsed.fragment
                    or parsed.port is not None
                    or type(definition["expected_remote_size_bytes"]) is not int
                    or definition["expected_remote_size_bytes"] <= 0
                    or not isinstance(definition["expected_etag"], str)
                    or not definition["expected_etag"].startswith('"')
                    or not definition["expected_etag"].endswith('"')
                    or scope["kind"] != "local-fixture"
                    or scope["window"] != context.window
                    or scope["contract_sha256"] != value["fixture_source_contract_sha256"]
                    or not _exact(scope["archive_interval"], value["archive_interval"])
                    or not _exact(scope["geometry"], value["geometry"])
                    or definition["expected_header"]["dataset_shape"][0] != 16):
                raise ValueError("only exact receiver-matched local fixture scope is allowed")
            filters.declared(definition, required=True)
            rebuilt = rows.make_scope(definition, scope["window"], scope["archive_interval"],
                                      scope["contract_sha256"], "local-fixture")
            if not _exact(scope, rebuilt):
                raise ValueError("noncanonical local fixture normalization/geometry scope")
        if (len({e["scope"]["definition"]["url"] for e in entries}) != 6
                or len({e["receipt_sha256"] for e in entries}) != 6):
            raise ValueError("six distinct fixture sources and receipt identities required")
        channels = context.geometry.channel_count
        if native.memory_bound(16, channels) > native.CONTRACT["memory_cap_bytes"]:
            raise core.V0P6CapacityError("codec/receiver adapter memory cap exceeded before rows")
        if pipeline.legacy.modelled_array_bytes(context, 16, channels) > context.memory_limit_bytes:
            raise core.V0P6CapacityError("codec/receiver cadence memory cap exceeded before rows")


def bind(manifest, trusted_manifest_sha256, context):
    """The caller supplies the trusted digest; never derive trust from a file."""
    core._frozen_sha256(trusted_manifest_sha256, "trusted local receiver binding")
    binding = FixtureBinding(core.canonical_json_bytes(manifest).decode(), trusted_manifest_sha256)
    binding.validate(context)
    return binding


def _guard_receipt(directory, entry, binding):
    """Metadata-only guard, called for all six scans before any NPY is read."""
    receipt = rows.verify(_bounded_json(Path(directory) / "source.json", MAX_SOURCE_JSON_BYTES))
    if (set(receipt) != {"scope", "rows", "transport", "complete", "receipt_sha256"}
            or receipt["receipt_sha256"] != entry["receipt_sha256"]
            or not _exact(receipt["scope"], entry["scope"]) or receipt["complete"] is not True
            or len(receipt["rows"]) != 16):
        raise ValueError("codec receipt differs from trusted local receiver binding")
    transport = receipt["transport"]
    definition = entry["scope"]["definition"]
    expected_remote = {"url": definition["url"], "size": definition["expected_remote_size_bytes"],
                       "etag": definition["expected_etag"]}
    if (set(transport) != {"kind", "identity", "range_plan_file_sha256", "checkpoint",
                          "hdf5_runtime", "dataset_filters"}
            or transport["kind"] != "local-HDF5-over-simulated-HTTP"
            or not _exact(transport["identity"], expected_remote)
            or not _exact(transport["hdf5_runtime"], binding.record["runtime"])
            or not _exact(filters.signature(transport["dataset_filters"]), filters.declared(definition, required=True))):
        raise ValueError("local codec transport/filter/runtime ancestry changed")
    core._frozen_sha256(transport["range_plan_file_sha256"], "local source range plan")
    checkpoint = transport["checkpoint"]
    if (type(checkpoint.get("schema_version")) is not int
            or checkpoint["schema_version"] != 1
            or not _exact(checkpoint.get("remote"), expected_remote)):
        raise ValueError("local transport checkpoint metadata types changed")
    rows.verify_transport_checkpoint(checkpoint, expected_remote)
    for i, row in enumerate(receipt["rows"]):
        rows.verify(row)
        if type(row["row"]) is not int or row["row"] != i or row["scope_sha256"] != rows.digest(entry["scope"]):
            raise ValueError("codec receipt row order or scope changed")
        # These metadata files are separately bounded before the inherited
        # rehydrate call; no row payload is opened by the cadence guard.
        retained = rows.verify(_bounded_json(Path(directory) / f"row{i:02d}.json", MAX_ROW_JSON_BYTES))
        if not _exact(retained, row):
            raise ValueError("row metadata differs from trusted source receipt")
    return receipt


def _owned_native_row(path, channels, expected):
    """Read bounded bytes from one nofollow FD; never allocate from NPY shape.

    Existing generated receipts use NPY v1 or v2. Metadata parsing is bounded,
    stat size and exact shape precede the fixed-length immutable byte read, and
    hashes cover the actual file and owned payload. Path replacement cannot
    switch the already-open FD; same-inode changes still fail retained hashes.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        payload_size = channels * 4
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not payload_size < before.st_size <= payload_size + 4096):
            raise ValueError("native row must be one bounded regular file before allocation")
        version = np.lib.format.read_magic(handle)
        if version == (1, 0):
            size_format = "<H"
            header_reader = np.lib.format.read_array_header_1_0
        elif version == (2, 0):
            size_format = "<I"
            header_reader = np.lib.format.read_array_header_2_0
        else:
            raise ValueError("unsupported native row NPY version")
        length_bytes = handle.read(struct.calcsize(size_format))
        if len(length_bytes) != struct.calcsize(size_format):
            raise ValueError("truncated native row NPY header")
        header_length = struct.unpack(size_format, length_bytes)[0]
        if header_length > 4096:
            raise ValueError("oversized native row NPY header before allocation")
        header_bytes = handle.read(header_length)
        if len(header_bytes) != header_length:
            raise ValueError("truncated native row NPY header")
        shape, fortran, dtype = header_reader(io.BytesIO(length_bytes + header_bytes), max_header_size=4096)
        header_size = handle.tell()
        if (shape != (channels,) or any(type(n) is not int for n in shape)
                or fortran is not False or dtype != np.dtype("<f4")
                or header_size > 4096
                or os.fstat(handle.fileno()).st_size != header_size + payload_size):
            raise ValueError("native row shape/dtype/size changed before allocation")
        handle.seek(0)
        encoded_header = handle.read(header_size)
        payload = handle.read(payload_size)
        if len(encoded_header) != header_size or len(payload) != payload_size or handle.read(1):
            raise ValueError("native row length changed during bounded read")
    file_hash = hashlib.sha256(encoded_header)
    file_hash.update(payload)
    if file_hash.hexdigest() != expected["native_file_sha256"]:
        raise ValueError("native row file changed after receipt verification")
    value = np.frombuffer(payload, dtype="<f4").copy()
    if rows.array_hash(value) != expected["native_sha256"]:
        raise ValueError("native row changed after receipt verification")
    return value


def _adapt_fixture(directory, entry, binding, context, guarded):
    receipt = rows.rehydrate(directory, entry["receipt_sha256"], required_kind="local-fixture")
    if not _exact(receipt, guarded):
        raise ValueError("codec receipt changed after metadata-only guard")

    def reader(row):
        return _owned_native_row(Path(directory) / f"row{row:02d}.native.npy",
                                 context.geometry.channel_count, receipt["rows"][row])

    source = native.normalize_synthetic_rows(reader, context.geometry, 16,
        input_orientation="descending", scope={
            "kind": "synthetic", "input_domain": "local-codec-receiver-candidate",
            "scan": entry["label"], "window": context.window,
            "role": binding.record["role"], "context_sha256": context.identity,
            "receiver_factor_bank_sha256": context.factor_contract.factors.identity,
            "codec_receiver_binding_sha256": binding.identity,
            "codec_receipt_sha256": entry["receipt_sha256"],
            "codec_scope_sha256": rows.digest(entry["scope"]),
            "fixture_source_contract_sha256": binding.record["fixture_source_contract_sha256"],
            "receiver_source_contract_sha256": binding.record["receiver_source_contract_sha256"],
            "receiver_window_identity": binding.record["receiver_window_identity"],
            "telescope_provenance": False, "independent_draws": False,
            "scientific_candidate_selection_authorized": False,
        })
    for i, expected in enumerate(receipt["rows"]):
        if native.array_hash(source.values[i]) != expected["normalized_sha256"]:
            raise ValueError("local codec/receiver normalization differs")
    native.validate_source(source)
    return source


def fixture_run(context, binding, directories):
    """Return NativeRun plus handoff receipt, without executing it.

    This candidate bounds its own metadata and payload reads. The inherited
    rehydrate implementation reopens row paths; mutable hostile filesystems
    during that inherited call are outside this engineering qualification.
    Actual owned post-rehydrate bytes are nevertheless bounded and rehashed.
    """
    if type(binding) is not FixtureBinding:
        raise ValueError("typed local codec/receiver binding required")
    binding.validate(context)
    if set(directories) != set(received.LABELS):
        raise ValueError("exact six-directory local fixture inventory required")
    if len({Path(directories[label]).resolve() for label in received.LABELS}) != 6:
        raise ValueError("six distinct local source directories required")
    entries = binding.record["scans"]
    guarded = {entry["label"]: _guard_receipt(directories[entry["label"]], entry, binding)
               for entry in entries}
    sources = {entry["label"]: _adapt_fixture(directories[entry["label"]], entry, binding,
                                             context, guarded[entry["label"]])
               for entry in entries}
    run = pipeline.NativeRun(context, sources)
    receipt = {
        "schema": HANDOFF_SCHEMA, "binding_sha256": binding.identity,
        **receiver_window(context), "context_sha256": context.identity,
        "receiver_factor_bank_sha256": context.factor_contract.factors.identity,
        "fixture_source_contract_sha256": binding.record["fixture_source_contract_sha256"],
        "source_ids": run.source_ids,
        "codec_receipt_sha256s": {e["label"]: e["receipt_sha256"] for e in entries},
        "normalized_row_sha256s": {label: [native.array_hash(a) for a in src.values]
                                    for label, src in sources.items()},
        "unique_raw_payloads": len({s.raw_sha256 for s in sources.values()}),
        "unique_normalized_payloads": len({s.normalized_sha256 for s in sources.values()}),
        "explicit_scan_slots": 6, "rows_per_scan": 16,
        "modelled_array_bound_bytes": run.modelled_bytes,
        "independent_draws_established": False, "gaussian_renderer_qualified": False,
        "telescope_provenance_established": False,
        "scientific_candidate_selection_authorized": False,
        "reduction_invoked": False, "scoring_invoked": False,
        "rng_invoked": False, "controls_invoked": False,
        "scientific_allocation_charged": False,
    }
    return run, rows.seal(receipt)
