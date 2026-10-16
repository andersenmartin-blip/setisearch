"""Engineering semantic integration, never a scientific study dispatcher.

The legacy numerical and QA modules are imported without invoking their mains,
admission functions, generators, RNG, or case bank.  Six deterministic full-size
raw arrays exercise actual preprocessing and cadence/alias geometry.  Retained
maps, hit scores and OFF inventories are explicitly controlled format fixtures;
they are NOT results of a complete search.  Actual legacy witness, recovery,
serializer, QA decode/hit/recovery and summarizer functions consume them.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LEGACY = REPO / "analysis" / "sixscan_burst_20261015"
IDENTITY = "SETI_SCIENCE_PAYLOAD_ENGINEERING_FORMAT_20261016_V1"
PAYLOAD_CAP = 64 * 1024 ** 2
MODE = "ENGINEERING_FIXTURES_ONLY"
LOG_CAP = 64 * 1024


class BoundedText:
    """Bound the controlled Python child stdout/stderr, retaining the prefix."""
    def __init__(self, stream):
        self.stream, self.remaining, self.overflow = stream, LOG_CAP, False
    def write(self, text):
        encoded = str(text).encode("utf-8", errors="replace")
        kept = encoded[:self.remaining]
        self.remaining -= len(kept)
        self.overflow |= len(kept) != len(encoded)
        self.stream.write(kept.decode("utf-8", errors="ignore"))
        return len(str(text))
    def flush(self): self.stream.flush()
    def isatty(self): return False


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    path = Path(path)
    encoded = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    require(len(encoded) <= 2 * 1024 ** 2, "Engineering JSON receipt exceeds the2MiB file bound")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded.decode("utf-8"))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def modules():
    import numpy as np
    worker = load_module(LEGACY / "worker.py", "engineering_legacy_worker")
    detector = load_module(LEGACY / "detector.py", "engineering_legacy_detector")
    qa = load_module(LEGACY / "qa.py", "engineering_legacy_qa")
    qa.np = np
    summary = load_module(LEGACY / "summarize.py", "engineering_legacy_summary")
    return np, worker, detector, qa, summary


def import_transport():
    # The local directory is the only added import path, never the old stage.
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import payload
    return payload


def pins():
    return {name: {"sha256": sha(LEGACY / name), "bytes": (LEGACY / name).stat().st_size}
            for name in ("worker.py", "detector.py", "qa.py", "summarize.py", "contract.json")}


def deterministic_raw(np, index):
    """Exactly representable positive float32 arithmetic; no random generator."""
    columns = np.arange(12096, dtype=np.int64)[None, :]
    rows = np.arange(16, dtype=np.int64)[:, None]
    value = 1.0 + ((37 * columns + 17 * rows + 13 * index) % 257 - 128) / 1024.0
    value += ((columns // 11 + rows + index) % 17) / 2048.0
    return np.ascontiguousarray(value, dtype=np.float32)


def scores_for(np, scan_index):
    if scan_index == 0:
        values = [[20., 18., 16., 10., 9.], [25., 15., 14., 11., 9.]]
    elif scan_index == 2:
        values = [[19., 18., 12., 10., 9.], [9., 8., 7., 6., 5.]]
    else:
        values = [[9., 8., 7., 6., 5.], [9., 8., 7., 6., 5.]]
    return np.asarray(values, dtype=np.float64)


def controlled_maps(np, metadata, corefirst, grid, tables, *, producer_tables):
    """Two declared carriers per scan; controlled values, never searched maps."""
    result = []
    zero = int(np.flatnonzero(grid == 0.)[0])
    refs = np.asarray([corefirst + 100, corefirst + 2000], dtype=np.int64)
    starts = np.tile(np.asarray([0, 0, 2, 0, 4], dtype=np.int16), (2, 1))
    widths = np.tile(np.asarray([1, 3, 9, 33, 1], dtype=np.int16), (2, 1))
    for si, meta in enumerate(metadata):
        source = tables[meta["scan_id"]] if producer_tables else tables[si]
        mapping = {"scan_id": meta["scan_id"], "role": meta["role"],
                   "reference_source_channels": refs.copy(), "scores": scores_for(np, si),
                   "widths": widths.copy(), "window_starts": starts.copy(),
                   "drift_grid_indices": np.full((2, 5), zero, dtype=np.int32),
                   "native4_centers": np.empty((2, 5, 4), dtype=np.int64),
                   "drift_alias_first_index": np.empty((2, 5), dtype=np.int32),
                   "drift_alias_last_index": np.empty((2, 5), dtype=np.int32),
                   "retained_valid": np.ones((2, 5), dtype=bool)}
        for ci, ref in enumerate(refs):
            for rank in range(5):
                table = source[(int(starts[ci, rank]), int(ref % 2))]
                inverse = table["drift_to_unique_path"] if producer_tables else table["inverse"]
                group = int(inverse[zero])
                relative = table["relative_centers"] if producer_tables else table["relative"]
                first = table["alias_first_index"] if producer_tables else table["first"]
                last = table["alias_last_index"] if producer_tables else table["last"]
                mapping["native4_centers"][ci, rank] = ref + relative[group]
                mapping["drift_alias_first_index"][ci, rank] = first[group]
                mapping["drift_alias_last_index"][ci, rank] = last[group]
        result.append(mapping)
    return result


def controlled_records(np, metadata, corefirst, grid, tables, *, producer_tables):
    zero = int(np.flatnonzero(grid == 0.)[0]); reference = corefirst + 2000
    records = {}
    for si, meta in enumerate(metadata):
        if meta["role"] != "OFF":
            records[si] = []
            continue
        table = (tables[meta["scan_id"]] if producer_tables else tables[si])[(0, reference % 2)]
        inverse = table["drift_to_unique_path"] if producer_tables else table["inverse"]
        group = int(inverse[zero])
        first = table["alias_first_index"] if producer_tables else table["first"]
        last = table["alias_last_index"] if producer_tables else table["last"]
        relative = table["relative_centers"] if producer_tables else table["relative"]
        records[si] = [(1, reference, 1, 0, zero, int(first[group]), int(last[group]), 8.,
                        (reference + relative[group]).tolist())]
    return records


def make_hits(np, detector, scans, maps, inventories, certificates, geometry, cfg):
    hits = []
    for scan, mapping, times in zip(scans, maps, geometry["times_from_tref_s"]):
        if scan.role != "ON":
            continue
        for ci, rank in zip(*np.nonzero(mapping["scores"] >= 10.)):
            ci, rank = int(ci), int(rank)
            start = int(mapping["window_starts"][ci, rank]); donor = int(mapping["drift_grid_indices"][ci, rank])
            hit = {"scan_id": scan.scan_id, "reference_carrier_index": ci,
                   "reference_source_channel": int(mapping["reference_source_channels"][ci]),
                   "hit_id": f"{scan.scan_id}:carrier{ci:04d}:rank{rank + 1}",
                   "retained_rank": rank + 1, "width_channels": int(mapping["widths"][ci, rank]),
                   "window_start": start, "window_start_row": start, "window_source_rows": list(range(start, start + 4)),
                   "representative_drift_grid_index": donor,
                   "representative_drift_hz_s": float(geometry["drift_grid_hz_s"][donor]),
                   "drift_alias_first_index": int(mapping["drift_alias_first_index"][ci, rank]),
                   "drift_alias_last_index": int(mapping["drift_alias_last_index"][ci, rank]),
                   "native4_centers": mapping["native4_centers"][ci, rank].tolist(),
                   "ON_score": float(mapping["scores"][ci, rank])}
            hit["OFF_comparisons"] = [detector.off_witness(hit, off, inventories[off.scan_id],
                                        certificates[off.scan_id], times, geometry, cfg)
                                      for off in scans if off.role == "OFF"]
            hit["disposition"] = "OFF_MATCHED" if any(x["veto"] for x in hit["OFF_comparisons"]) else "SURVIVOR_EXPLORATORY"
            hits.append(hit)
    return hits


def produce(folder):
    folder = Path(folder); folder.mkdir()
    np, worker, detector, _, _ = modules()
    transport = import_transport()
    contract = json.loads((LEGACY / "contract.json").read_text())
    metadata = contract["geometry"]["scan_metadata"]
    raw = [deterministic_raw(np, i) for i in range(6)]
    geometry_input = contract["geometry"]
    require(geometry_input["loaded_source_channel_interval"][1] - geometry_input["loaded_source_channel_interval"][0] == 12096,
            "Frozen raw fixture shape changed")
    authenticated = worker.authenticate_arrays(raw, metadata, geometry_input, np)
    scans, corefirst = worker.scan_inputs(raw, metadata, geometry_input, detector, np)
    cfg = detector.Config(); geometry, tables = detector.search_geometry(scans, corefirst, cfg)
    maps = controlled_maps(np, metadata, corefirst, geometry["drift_grid_hz_s"], tables, producer_tables=True)
    preprocessed = []
    for scan, mapping in zip(scans, maps):
        z, mask, normal = detector.preprocess(scan, cfg)
        mapping["normalization"] = normal
        preprocessed.append(z)
        require(mask.all(), "Unmasked deterministic fixture required")
        require(all(isinstance(x, list) for x in normal.values()), "Legacy normalization lists required")
    records = controlled_records(np, metadata, corefirst, geometry["drift_grid_hz_s"], tables, producer_tables=True)
    inventories, certificates = {}, {}
    for si, meta in enumerate(metadata):
        if meta["role"] != "OFF":
            continue
        inventory = detector._inventory(list(records[si])); inventories[meta["scan_id"]] = inventory
        inventory_sha = hashlib.sha256(b"".join(inventory[k].tobytes(order="C") for k in sorted(inventory))).hexdigest()
        certificates[meta["scan_id"]] = {"complete": True, "inventory_rows": len(records[si]), "score_threshold": 8.,
              "inventory_sha256": inventory_sha, "inventory_domain": "ONE_DECLARED_ENGINEERING_RECORD_ONLY_NOT_FULL_SEARCH"}
    hits = make_hits(np, detector, scans, maps, inventories, certificates, geometry, cfg)
    admission = {"status": "ENGINEERING_ONLY_NOT_SCIENTIFIC_ADMISSION", "mode": MODE,
                 "scientific_admission": False, "fixture_identity": IDENTITY,
                 "legacy_code_pins": pins(), "original_A_B": "FAIL_CLOSED", "original_pilot_admitted": False,
                 "qualified_SETI_detection": False, "new_observation": False}
    truth = worker.canonical_truth({"case_id": IDENTITY, "synthetic_injection": False,
        "controlled_truth_for_format_test_only": True,
        "active_ON_scan_ids": [metadata[i]["scan_id"] for i in (0, 2)],
        "reference_source_channel": corefirst + 100, "drift_hz_s": 0.,
        "flux_by_scan": {metadata[i]["scan_id"]: {"truth_window_source_rows": [0, 1, 2, 3],
                           "injection_oracle_width_channels": 1} for i in (0, 2)},
        "authenticated_input_arrays": authenticated})
    output = {"schema": "ENGINEERING_CONTROLLED_RETAINED_MAP_FIXTURE_V1", "case_id": IDENTITY,
        "case_index": 0, "exposed": False, "status": "ENGINEERING_FIXTURE_ONLY", "admission": admission,
        "geometry": geometry, "alias_geometry": tables, "scan_maps": maps,
        "OFF_threshold_inventories": inventories, "OFF_inventory_certificates": certificates,
        "all_ON_threshold_hypotheses": hits,
        "surviving_ON_threshold_hypothesis_count": sum(h["disposition"] == "SURVIVOR_EXPLORATORY" for h in hits),
        "maximum_pre_OFF_ON_score": 25., "calibrationglobal_ON_max": 25.,
        "qualified_SETI_detection": False, "original_A_B": "FAIL_CLOSED"}
    output["recovery"] = detector.recovery(output, truth)
    encoded, arrays, descriptors = worker.json_and_array_store(output, np)
    # Transport the actual legacy serializer boundary, including unchanged keys,
    # descriptors and JSON list values; the verifier uses unchanged qa.decode.
    payload = {"worker_json": encoded, "worker_arrays": arrays, "legacy_descriptors": descriptors,
               "truth": truth, "admission": admission,
               "case": {"case_id": IDENTITY, "family": "engineering_fixture"},
               "inputs": {s["scan_id"]: a for s, a in zip(metadata, raw)},
               "preprocessed_z": preprocessed, "calibration_values": [19.] * 63}
    receipt = transport.write_payload(folder / "payload", payload, cap=PAYLOAD_CAP)
    save(folder / "PRODUCER.json", {"status": "PRODUCED_ENGINEERING_FIXTURE_ONLY", "identity": IDENTITY,
       "legacy_code_pins": pins(), "legacy_array_count": len(arrays), "legacy_descriptors": descriptors,
       "raw_shapes": [list(a.shape) for a in raw], "raw_hashes": authenticated,
       "retained_map_carriers_per_scan": 2, "actual_full_search_performed": False,
       "old_scientific_main_called": False, "RNG_called": False,
       "payload_receipt": receipt, "qualified_SETI_detection": False})
    print(json.dumps({"status": "PRODUCED_ENGINEERING_FIXTURE_ONLY", "arrays": len(arrays)}), flush=True)


class WorkerArrayStore:
    """Read one transported legacy array lazily for the original QA decoder."""
    def __init__(self, archive):
        self.archive = archive

    def __getitem__(self, key):
        return self.archive.load(("worker_arrays", key))


def verify(folder, report_path):
    np, _, _, qa, summary = modules()
    producer = json.loads((Path(folder) / "PRODUCER.json").read_text())
    archive = import_transport().verify_payload(Path(folder) / "payload", cap=PAYLOAD_CAP,
                 expected_semantic_sha256=producer["payload_receipt"]["semantic_sha256"])
    require(producer["identity"] == IDENTITY and producer["legacy_code_pins"] == pins(), "Producer identity/code pins differ")
    require(producer["actual_full_search_performed"] is False, "Engineering provenance differs")
    encoded = archive.load(("worker_json",)); descriptors = archive.load(("legacy_descriptors",))
    require(descriptors == producer["legacy_descriptors"], "Original complete descriptor inventory differs")
    found = {}
    def descriptor_visit(value):
        if isinstance(value, dict) and set(value) == {"array_descriptor"}:
            d = value["array_descriptor"]; require(d["npz_key"] not in found, "Duplicate legacy descriptor")
            found[d["npz_key"]] = d
        elif isinstance(value, dict):
            for child in value.values(): descriptor_visit(child)
        elif isinstance(value, list):
            for child in value: descriptor_visit(child)
    descriptor_visit(encoded)
    require(found == descriptors, "All original array descriptors/path/dtype/shape/hash/nbytes preserved")
    audit = qa.Audit(); output = qa.decode(encoded, WorkerArrayStore(archive), audit)
    truth = archive.load(("truth",)); admission = archive.load(("admission",)); case = archive.load(("case",))
    audit.eq(output["admission"], admission, "Original complete admission structure")
    audit.eq(admission["scientific_admission"], False, "Transport cannot grant scientific admission")
    audit.eq(output["case_id"], case["case_id"], "Controlled case/output identity")
    audit.eq(truth["case_id"], IDENTITY, "Controlled truth identity")
    contract = json.loads((LEGACY / "contract.json").read_text())
    metadata = contract["geometry"]["scan_metadata"]
    corefirst = contract["geometry"]["reference_source_channel_interval"][0]
    times, grid, halo, tables = qa.geometry(contract, corefirst)
    audit.eq(output["geometry"]["OFF_reference_halo_channels"], halo, "Independent metadata-only OFF halo")
    audit.close(output["geometry"]["drift_grid_hz_s"], grid, "Independent full global drift grid", 0.)
    for si, meta in enumerate(metadata):
        raw = archive.load(("inputs", meta["scan_id"]))
        audit.eq(list(raw.shape), [16, 12096], "Complete raw preprocessing fixture shape")
        audit.eq(str(raw.dtype), "float32", "Complete raw fixture dtype")
        audit.eq(qa.array_sha(raw), producer["raw_hashes"][meta["scan_id"]]["C_order_bytes_sha256"], "Complete raw fixture byte hash")
        # Independent source is prescribed integer arithmetic, never another draw.
        audit.eq(qa.array_sha(raw), qa.array_sha(deterministic_raw(np, si)), "Independent deterministic raw fixture reproduction")
        z, normal, _ = qa.preprocess(raw)
        audit.close(archive.load(("preprocessed_z", si)), z, "Independent complete raw501 normalized z", 1e-10)
        saved_normal = output["scan_maps"][si]["normalization"]
        audit.eq({k: type(v).__name__ for k, v in saved_normal.items()},
                 {k: "list" for k in saved_normal}, "Original normalization values remain lists")
        for j, name in enumerate(qa.NORMAL):
            audit.close(saved_normal[name], normal[j], "Independent original normalization " + name, 1e-10)
        audit.eq(saved_normal["normalization_source_channels"], list(range(corefirst, corefirst + 4096)), "Full normalization coordinate LIST")
        audit.eq(saved_normal["normalization_unmasked_counts"], [4096] * 16, "Full normalization counts LIST")
        audit.close(output["geometry"]["times_from_tref_s"][si], times[si], "Independent actual midpoint coordinates", 0.)
        for key, table in tables[si].items():
            saved = output["alias_geometry"][meta["scan_id"]][str(key)]
            order = np.argsort(table["first"]); renumber = np.empty(len(order), dtype=np.int32)
            renumber[order] = np.arange(len(order), dtype=np.int32)
            for field, expected in (("relative_centers", table["relative"][order]),
                    ("alias_first_index", table["first"][order]), ("alias_last_index", table["last"][order]),
                    ("drift_to_unique_path", renumber[table["inverse"]])):
                audit.eq(saved[field].tolist(), expected.tolist(), "Independent complete alias geometry " + field)
    own_maps = controlled_maps(np, metadata, corefirst, grid, tables, producer_tables=False)
    own_records = controlled_records(np, metadata, corefirst, grid, tables, producer_tables=False)
    for saved, expected in zip(output["scan_maps"], own_maps):
        for field, value in expected.items():
            if isinstance(value, np.ndarray):
                audit.eq(saved[field].tolist(), value.tolist(), "Independent controlled retained map " + field)
            else: audit.eq(saved[field], value, "Independent controlled retained map " + field)
    qa.verify_hits(output, own_maps, own_records, times, grid, metadata, tables, audit)
    independent_recovery = qa.verify_recovery(output, truth, times, grid, metadata, audit)
    calibration = archive.load(("calibration_values",))
    audit.eq(calibration, [19.] * 63, "Controlled63 rank reference values")
    ranked = summary.rank_hits(0, case, output, calibration)
    for row in ranked:
        score = row["ON_score"]
        audit.eq(row["reference_equal_or_greater"], 0 if score > 19. else 63, "Independent inclusive rank census")
        audit.eq(row["model_rank_p"], 1. / 64 if score > 19. else 1., "Independent inclusive rank arithmetic")
        audit.eq(row["rank_cut_pass"], score > 19., "Independent rank boundary/tie semantics")
        audit.eq(row["final_candidate"], score > 19. and row["OFF_disposition"] == "SURVIVOR_EXPLORATORY", "OFF decision separate from rank")
        audit.eq(row["telescope_FAP_interpretation_allowed"], False, "No telescope FAP from format fixture")
    metrics = {}; summary.recovery_metrics(metrics, output, truth, ranked)
    expected_metrics = {"after_rank_survivor_count": 1, "pre_OFF_all_active_recovered": True,
         "pre_OFF_any_active_recovered": True, "after_OFF_all_active_recovered": True,
         "after_rank_all_active_recovered": False, "after_rank_any_active_recovered": True}
    audit.eq(metrics, expected_metrics, "Real summary preserves pre/OFF/rank/any/all distinctions")
    audit.eq(len(output["all_ON_threshold_hypotheses"]), 12, "All controlled ON threshold hits retained")
    audit.eq(output["surviving_ON_threshold_hypothesis_count"], 8, "Controlled after-OFF survivor census")
    audit.eq(output["maximum_pre_OFF_ON_score"], 25., "Controlled pre-OFF maximum preserved separately")
    # Empty activity is a separate semantic branch, not a measured nonrecovery.
    empty_output = {"all_ON_threshold_hypotheses": [], "recovery": {"recovery_applicable": False}}
    empty_truth = {"active_ON_scan_ids": []}
    empty_metrics = {}; empty_ranked = summary.rank_hits(1, case, empty_output, calibration)
    summary.recovery_metrics(empty_metrics, empty_output, empty_truth, empty_ranked)
    audit.eq(empty_metrics, {"after_rank_survivor_count": 0}, "Empty activity does not invent recovery outcomes")
    qa.verify_recovery(empty_output, empty_truth, times, grid, metadata, audit)
    report = {"schema": "SETI_WORKER_PAYLOAD_QA_SUMMARIZER_ENGINEERING_INTEGRATION_V1", "status": "PASS_ENGINEERING_SEMANTICS_ONLY",
      "identity": IDENTITY, "mode": MODE, "legacy_code_pins": pins(), "checks": audit.checks,
      "max_absolute_errors": dict(audit.errors), "legacy_array_count": len(descriptors),
      "full_shape_raw_arrays": 6, "raw_shape": [16, 12096], "controlled_retained_carriers_per_scan": 2,
      "legacy_functions_exercised": ["worker.authenticate_arrays", "worker.scan_inputs", "worker.canonical_truth",
        "worker.json_and_array_store", "detector.preprocess", "detector.search_geometry", "detector._inventory",
        "detector.off_witness", "detector.recovery", "qa.decode", "qa.preprocess", "qa.geometry",
        "qa.verify_hits", "qa.verify_recovery", "summarize.rank_hits", "summarize.recovery_metrics"],
      "descriptor_fields_preserved": ["npz_key", "shape", "dtype", "C_order_bytes_sha256", "nbytes", "original_field_path"],
      "normalization_types_preserved": "all six original fields remain Python lists",
      "summary_metrics": metrics, "ranked_controlled_hits": ranked, "independent_recovery": independent_recovery,
      "covered": {"actual_full_shape_preprocessing": True, "actual_complete_metadata_geometry": True,
         "actual_legacy_serializer_to_unchanged_QA_decode": True, "actual_controlled_OFF_witnesses_and_recovery": True,
         "actual_rank_and_recovery_summary_functions": True, "truth_and_admission_structures": True},
      "not_established": {"full498_array_case_shape_compatibility": True, "complete_scientific_search": True,
         "complete_family_OFF_inventories": True, "full_study_summary_or_case_record_admission": True,
         "scientific_QA_admission": True, "sensitivity_or_telescope_FAP": True},
      "RNG_called": False, "old_scientific_mains_called": False, "scientific_admission": False,
      "qualified_SETI_detection": False, "original_A_B": "FAIL_CLOSED", "new_observation": False}
    save(report_path, report)
    print(json.dumps({"status": report["status"], "checks": audit.checks, "summary_metrics": metrics}), flush=True)


def main():
    stdout, stderr = BoundedText(sys.stdout), BoundedText(sys.stderr)
    sys.stdout, sys.stderr = stdout, stderr
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("produce"); p.add_argument("--folder", type=Path, required=True)
    p = sub.add_parser("verify"); p.add_argument("--folder", type=Path, required=True); p.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    try:
        if args.command == "produce": produce(args.folder)
        else: verify(args.folder, args.report)
    except BaseException:
        traceback.print_exc()
        raise
    if stdout.overflow or stderr.overflow:
        raise RuntimeError("Controlled engineering child log bound exceeded")


if __name__ == "__main__":
    main()
