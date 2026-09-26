"""Explicit-source radio acquisition, reusing unchanged M43H row arithmetic.

The independently supplied contract file hash binds every definition, window,
implementation pin and gate. A preparation contract is useful offline but
cannot make a network request. No legacy target config is loaded or changed.
"""
import importlib.metadata
import json
from pathlib import Path
import re
from urllib.parse import urlparse

import numpy as np

from . import source_m43h as rows
from . import http_range_v0p6 as old
from . import transport_radio as net

ARTIFACT = "radio-source-contract-v1"
GATES = ("pointing", "prospective_protocol", "codec_integration")
IMPLEMENTATION_PATHS = (
    "src/seti_repeater/source_radio.py", "src/seti_repeater/transport_radio.py",
    "src/seti_repeater/source_m43h.py", "src/seti_repeater/transport_m43h.py",
    "src/seti_repeater/http_range_v0p6.py", "src/seti_repeater/source_v0p6.py",
    "src/seti_repeater/search_v0p6.py",
)


def pinned_file(root, name, expected):
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("contract pin leaves the project")
    rows.core._frozen_sha256(expected, "file pin")
    if rows.file_hash(path) != expected:
        raise ValueError("contract file changed: " + name)
    return path


def runtime():
    import h5py
    return {"numpy": np.__version__, "h5py": h5py.__version__,
            "hdf5": h5py.version.hdf5_version,
            "hdf5plugin": importlib.metadata.version("hdf5plugin")}


def load_contract(root, path, expected_sha256):
    path = pinned_file(root, path, expected_sha256)
    cfg = json.loads(path.read_text())
    if cfg.get("artifact_type") != ARTIFACT:
        raise ValueError("not a radio source contract")
    if not set(IMPLEMENTATION_PATHS).issubset(cfg["pinned_files"]):
        raise ValueError("acquisition implementation pins incomplete")
    for name, digest in cfg["pinned_files"].items():
        pinned_file(root, name, digest)
    scans = cfg["scans"]
    if (len(scans) != 6 or len({s["label"] for s in scans}) != 6
            or len({s["url"] for s in scans}) != 6
            or [s["role"] for s in scans] != ["on", "off"] * 3):
        raise ValueError("one distinct alternating six-scan cadence required")
    geometry = []
    end = -np.inf
    for definition in scans:
        label = definition["label"]
        parsed = urlparse(definition["url"])
        if (not re.fullmatch(r"[A-Za-z0-9_-]+", label)
                or parsed.scheme != "https" or parsed.username or parsed.password
                or parsed.fragment or parsed.query or not parsed.hostname
                or definition["expected_etag"].startswith("W/")):
            raise ValueError("invalid pinned source label, URL or ETag")
        old.RemoteIdentity(definition["url"], definition["expected_remote_size_bytes"],
                           definition["expected_etag"])
        h = definition["expected_header"]
        rows.make_scope(definition, "geometry-check", (0, 2), expected_sha256, "local-fixture")
        chunks = definition["expected_chunks"]
        if (len(chunks) != 3 or any(type(c) is not int or c <= 0 for c in chunks)
                or chunks[:2] != [1, 1] or np.prod(chunks)*4 > rows.MAX_HDF5_CHUNK_BYTES
                or not np.isfinite([h["tstart_mjd"], h["tsamp_s"], h["fch1_mhz"],
                                    h["foff_mhz"], h["src_raj_hours"], h["src_dej_deg"]]).all()
                or h["tsamp_s"] <= 0 or h["tstart_mjd"] < end):
            raise ValueError("invalid source time/chunk geometry")
        if (definition["role"] == "on") != (h["source_name"] == cfg["archive_target"]):
            raise ValueError("ON/OFF labels disagree with header names")
        end = h["tstart_mjd"] + h["dataset_shape"][0]*h["tsamp_s"]/86400
        geometry.append((h["dataset_shape"], h["dataset_dtype"], h["tsamp_s"],
                         h["fch1_mhz"], h["foff_mhz"]))
    if any(g != geometry[0] for g in geometry[1:]):
        raise ValueError("cadence source geometry differs")
    identity = rows.digest(scans)
    if cfg["source_inventory_sha256"] != identity:
        raise ValueError("cadence source inventory changed")
    windows = cfg["windows"]
    if len(windows) > 3 or len({w["name"] for w in windows}) != len(windows):
        raise ValueError("invalid window inventory")
    intervals = []
    for window in windows:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", window["name"]):
            raise ValueError("invalid window name")
        for definition in scans:
            rows.make_scope(definition, window["name"], window["archive_interval"],
                            expected_sha256, "local-fixture")
        intervals.append(tuple(window["archive_interval"]))
    intervals.sort()
    if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
        raise ValueError("overlapping extraction windows")
    net.Budget(**cfg["session_limits"])
    blockers = []
    for name in GATES:
        gate = cfg["gates"][name]
        if gate["status"] != "passed":
            blockers.append(name + ": " + gate["status"])
            continue
        if gate["source_inventory_sha256"] != identity:
            raise ValueError("gate belongs to a different source inventory")
        pinned_file(root, gate["evidence_path"], gate["evidence_sha256"])
    if not windows:
        blockers.append("extraction windows not frozen")
    if not cfg.get("hdf5_runtime"):
        blockers.append("runtime not frozen")
    return cfg, {"status": "BLOCKED" if blockers else "READY_FOR_AUTHORIZED_EXTRACTION",
                 "blockers": blockers, "source_inventory_sha256": identity,
                 "contract_sha256": expected_sha256, "scan_count": len(scans),
                 "window_count": len(windows), "network_requests": 0,
                 "spectral_dataset_values_read": False}


def _extract_bound_source(definition, window, contract_sha256, directory, mirror_root,
                          budget, *, kind):
    """Common codec path; fixtures call this with kind='local-fixture'."""
    import h5py
    import hdf5plugin  # Registers the archive codec; no scientific inputs.
    scope = rows.make_scope(definition, window["name"], window["archive_interval"],
                            contract_sha256, kind)
    identity = net.live_identity(definition["url"], budget)
    if (identity.size != definition["expected_remote_size_bytes"]
            or identity.etag != definition["expected_etag"]):
        raise ValueError("live source differs from contract")
    mirror_root = Path(mirror_root)
    mirror_root.mkdir(parents=True, exist_ok=True)
    label = definition["label"]

    def dataset_checked(handle):
        dataset = rows.validate_dataset(handle, scope)
        if list(dataset.chunks) != definition["expected_chunks"]:
            raise ValueError("HDF5 chunks differ from source contract")
        return dataset

    with net.RadioMirror(mirror_root/(label+".h5.sparse"), identity, budget) as mirror:
        with h5py.File(mirror, "r", rdcc_nbytes=rows.HDF5_CACHE_BYTES) as handle:
            dataset = dataset_checked(handle)
            creation = dataset.id.get_create_plist()
            filters = [list(creation.get_filter(i)[:3]) for i in range(creation.get_nfilters())]
            interval = tuple(window["archive_interval"])
            ranges = old.discover_hdf5_chunk_ranges(dataset, (interval,))
            plan = old.range_plan_record(identity, dataset_shape=dataset.shape,
                dataset_chunks=dataset.chunks, channel_intervals=(interval,), ranges=ranges)
        plan_path = mirror_root/(label+"."+window["name"]+".range-plan.json")
        plan_hash = old.publish_range_plan(plan_path, plan)
        mirror.prefetch(ranges)
        mirror.seek(0)
        with h5py.File(mirror, "r", rdcc_nbytes=rows.HDF5_CACHE_BYTES) as handle:
            dataset_checked(handle)
            inventory, resumed = rows._extract_rows(handle, scope, directory)
        if any(old._subtract_covered(r, mirror.covered_ranges) for r in ranges):
            raise ValueError("planned source chunks missing")
        checkpoint = json.loads(mirror.checkpoint_path.read_text())
        rows.verify_transport_checkpoint(checkpoint, identity.record())
        proof = {"kind": "live-identity-bound-http-ranges" if kind == "telescope-remote"
                 else "local-HDF5-over-simulated-HTTP", "identity": identity.record(),
                 "range_plan_file_sha256": plan_hash, "checkpoint": checkpoint,
                 "hdf5_runtime": runtime(), "dataset_filters": filters}
        budget.remaining_seconds()
        receipt = rows._complete(directory, scope, inventory, proof)
    rows.rehydrate(directory, receipt["receipt_sha256"], required_kind=kind)
    budget.remaining_seconds()
    return receipt, {"resumed_rows": resumed, "range_plan": plan, "budget": budget.record()}


def extract_remote(root, contract_path, contract_sha256, scan_label, window_name,
                   directory, mirror_root, budget, *, spectral_access_authorized=False):
    if spectral_access_authorized is not True:
        raise ValueError("spectral access not authorized")
    cfg, readiness = load_contract(root, contract_path, contract_sha256)
    if readiness["blockers"]:
        raise ValueError("source contract blocked: " + "; ".join(readiness["blockers"]))
    if budget.record()["limits"] != cfg["session_limits"]:
        raise ValueError("session budget differs from source contract")
    if runtime() != cfg["hdf5_runtime"]:
        raise ValueError("source contract runtime differs")
    definition = next((s for s in cfg["scans"] if s["label"] == scan_label), None)
    window = next((w for w in cfg["windows"] if w["name"] == window_name), None)
    if definition is None or window is None:
        raise ValueError("unknown source scan/window")
    return _extract_bound_source(definition, window, contract_sha256, directory,
                                 mirror_root, budget, kind="telescope-remote")
