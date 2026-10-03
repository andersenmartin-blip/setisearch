"""Independent read-only verification of a bound synthetic session checkpoint.

Replays original journal bytes through the pinned strict reader, compares every
retained generated file, parses fixed-size NPY headers/payloads independently,
and joins row/receipt hashes to the previously pinned synthetic evidence. It
does not import the execution driver or create/resume any source session.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import time

sys.dont_write_bytecode = True
START = time.monotonic()
MAX_SECONDS = 60
MAX_INVENTORY_BYTES = 384 * 1024**2
MAX_JSON_BYTES = 8 * 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def pin(path, maximum=MAX_INVENTORY_BYTES):
    path = Path(path)
    before = path.stat()
    if path.is_symlink() or not path.is_file() or not 0 <= before.st_size <= maximum:
        raise ValueError("bounded regular audit input required")
    h, count = hashlib.sha256(), 0
    with path.open("rb") as handle:
        while data := handle.read(1024**2):
            count += len(data)
            if count > before.st_size or time.monotonic() - START > MAX_SECONDS:
                raise ValueError("audit byte/time bound exceeded")
            h.update(data)
    if count != before.st_size:
        raise ValueError("audit input size changed")
    return {"path": str(path.resolve()), "bytes": count, "sha256": h.hexdigest()}


def bound(stated, maximum=MAX_JSON_BYTES):
    actual = pin(stated["path"], maximum)
    if actual != stated:
        raise ValueError("audit file differs from externally retained pin: " + stated["path"])
    return json.loads(Path(stated["path"]).read_bytes())


def seal(record):
    actual = hashlib.sha256(canonical({key: value for key, value in record.items()
                                     if key != "receipt_sha256"}) + b"\n").hexdigest()
    if record["receipt_sha256"] != actual:
        raise ValueError("independent canonical receipt digest differs")


def npy_payload(path, channels, expected_file, expected_payload):
    actual = pin(path, channels * 4 + 4096)
    if actual["sha256"] != expected_file:
        raise ValueError("row file hash differs")
    with Path(path).open("rb") as handle:
        magic = handle.read(8)
        if magic[:6] != b"\x93NUMPY" or magic[6:] not in (b"\x01\x00", b"\x02\x00"):
            raise ValueError("row NPY magic/version differs")
        length_format = "<H" if magic[6:] == b"\x01\x00" else "<I"
        length_bytes = handle.read(struct.calcsize(length_format))
        length = struct.unpack(length_format, length_bytes)[0]
        if not 0 < length <= 4096:
            raise ValueError("row header exceeds independent bound")
        header = ast.literal_eval(handle.read(length).decode("latin1"))
        if (header != {"descr": "<f4", "fortran_order": False, "shape": (channels,)}
                or type(header["fortran_order"]) is not bool
                or any(type(value) is not int for value in header["shape"])):
            raise ValueError("row fixed NPY shape/dtype differs")
        payload = handle.read(channels * 4)
        if len(payload) != channels * 4 or handle.read(1):
            raise ValueError("row fixed payload length differs")
    if hashlib.sha256(payload).hexdigest() != expected_payload:
        raise ValueError("row payload hash differs from independently retained prior oracle")
    return actual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True)
    parser.add_argument("--trusted-index-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    index_path = Path(args.index).resolve()
    index_pin = pin(index_path, MAX_JSON_BYTES)
    if index_pin["sha256"] != args.trusted_index_sha256:
        raise ValueError("actual attempt index differs from independent checkpoint")
    index = json.loads(index_path.read_bytes())
    if (index["status"] != "PASS" or index["scan_window_products"] != 18
            or index["row_products"] != 288 or index["positive_sessions"] != 18
            or index["negative_sessions"] != 1 or index["source_or_scientific_admission"] is not False):
        raise ValueError("bound complete synthetic checkpoint required")
    store_pin, driver_pin = index["store_pin"], index["driver_pin"]
    if pin(store_pin["path"], 64 * 1024) != store_pin or pin(driver_pin["path"], 64 * 1024) != driver_pin:
        raise ValueError("candidate module bytes differ from actual executed checkpoint")
    socket_attempts = []

    def deny_socket(event, arguments):
        if event.startswith("socket."):
            socket_attempts.append(event)
            raise RuntimeError("socket denied in actual-attempt audit")

    sys.addaudithook(deny_socket)
    spec = importlib.util.spec_from_file_location("actual_attempt_pinned_store", store_pin["path"])
    store = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = store
    spec.loader.exec_module(store)
    acquisition = store.acquisition
    original_pin = pin(acquisition.__file__, 64 * 1024)
    checked_files, checked_bytes = 0, 0
    inventory_paths = set()
    for stated in index["generated_files"]:
        actual = pin(stated["path"])
        if actual != stated or not Path(actual["path"]).is_relative_to(index_path.parent):
            raise ValueError("generated inventory identity/namespace differs")
        if actual["path"] in inventory_paths:
            raise ValueError("duplicate generated inventory path")
        inventory_paths.add(actual["path"])
        checked_files += 1
        checked_bytes += actual["bytes"]
        if checked_bytes > MAX_INVENTORY_BYTES:
            raise ValueError("generated inventory byte bound exceeded")
    actual_inventory = {str(path.resolve()) for path in index_path.parent.rglob("*") if path.is_file()}
    if actual_inventory != inventory_paths | {str(index_path)}:
        raise ValueError("actual attempt contains unregistered or missing files")
    if checked_bytes != index["generated_file_bytes_before_index"]:
        raise ValueError("generated inventory total differs")
    prior = bound(index["prior_acquisition_index_pin"])
    prior_by_key = {(p["role"], p["label"]): p for p in prior["products"]}
    final = bound(index["final_checkpoint_pin"])
    final_checkpoint = acquisition.Checkpoint(**final)
    final_summary = acquisition.validate_ledger(final_checkpoint.document, final_checkpoint.sha256)
    if final_summary != index["final_ledger_summary"] or final_summary["sessions"] != 19:
        raise ValueError("final complete cumulative ledger differs")
    current = store.EngineeringSqliteStore(final_checkpoint.location["path"]).read()
    if canonical({"document": current.document, "revision": current.revision,
                  "location": current.location}) != canonical(final):
        raise ValueError("current durable SQLite history differs from retained final checkpoint")
    negative = bound(index["negative_session_evidence_pin"])
    sessions = index["sessions"] + [negative]
    replayed, reserved, accepted, previous, ids = [], 0, 0, [], set()
    for ordinal, session in enumerate(sessions):
        checkpoint = acquisition.Checkpoint(**session["checkpoint"])
        history = checkpoint.document["reservations"]
        if (len(history) != ordinal + 1
                or canonical(history[:-1]) != canonical(previous)
                or canonical(history) != canonical(final_checkpoint.document["reservations"][:ordinal+1])
                or canonical(checkpoint.location) != canonical(final_checkpoint.location)
                or canonical(history[-1]) != canonical(session["reservation"])
                or session["reservation"]["session_id"] in ids):
            raise ValueError("session histories are not unique exact prefixes of one final ledger")
        previous = history
        ids.add(session["reservation"]["session_id"])
        bound(session["checkpoint_file"])
        bound(session["reservation_file"])
        if pin(session["journal"]["path"], store.MAX_JOURNAL_BYTES) != session["journal"]:
            raise ValueError("original journal bytes differ")
        replay = store.strict_read_journal(session["journal"]["path"],
            expected_checkpoint=checkpoint, expected_reservation=session["reservation"],
            expected_head=session["final_head"], ordered_scopes=[session["scope"]], require_closed=True)
        if canonical(replay) != canonical(bound(session["strict_receipt_file"])):
            raise ValueError("retained strict replay differs from independent replay")
        if replay["outcome"] != ("completed" if ordinal < 18 else "error"):
            raise ValueError("positive/negative closure differs")
        reserved += replay["reserved_bytes"]
        accepted += replay["accepted_bytes"]
        replayed.append({"ordinal": ordinal, "session_id": session["reservation"]["session_id"],
                         "outcome": replay["outcome"], "attempts": replay["reserved_attempts"],
                         "reserved_bytes": replay["reserved_bytes"], "accepted_bytes": replay["accepted_bytes"],
                         "unaccepted_get_attempts": replay["unaccepted_get_attempts"]})
    if replayed[-1]["accepted_bytes"] != 0 or replayed[-1]["attempts"] != 1:
        raise ValueError("negative bad ETag session did not remain a single charged HEAD")
    checked_rows, checked_npy_files, row_records = 0, 0, {}
    for product in index["products"]:
        receipt = bound(product["source_file"], 128 * 1024)
        seal(receipt)
        if receipt["receipt_sha256"] != product["receipt_sha256"] or receipt["complete"] is not True:
            raise ValueError("fresh source receipt differs")
        prior_product = prior_by_key[product["role"], product["label"]]
        if canonical(product["row_oracles"]) != canonical(prior_product["row_oracles"]):
            raise ValueError("fresh row oracle ancestry differs from pinned previous evidence")
        channels = receipt["scope"]["geometry"]["channel_count"]
        if channels != 65536 or len(receipt["rows"]) != 16:
            raise ValueError("row geometry differs from bounded synthetic inventory")
        row_hashes = []
        for row, oracle in zip(receipt["rows"], prior_product["row_oracles"], strict=True):
            seal(row)
            ordinal = row["row"]
            if type(ordinal) is not int or ordinal != oracle["row"]:
                raise ValueError("ordered row identity differs")
            for name in ("native", "normalized"):
                npy_payload(Path(product["directory"]) / f"row{ordinal:02d}.{name}.npy", channels,
                            row[name + "_file_sha256"], oracle[name + "_sha256"])
                checked_npy_files += 1
            if row["native_sha256"] != oracle["native_sha256"] or row["normalized_sha256"] != oracle["normalized_sha256"]:
                raise ValueError("fresh row receipt payload identity differs")
            checked_rows += 1
            row_hashes.append(row["normalized_sha256"])
        row_records[product["role"], product["label"]] = (receipt["receipt_sha256"], row_hashes)
    for role in index["roles"]:
        handoff = bound(role["handoff_file"])
        seal(handoff)
        if handoff["receipt_sha256"] != role["handoff_receipt_sha256"]:
            raise ValueError("receiver handoff identity differs")
        joined = bound(role["joined_manifest"])
        joined_replay = bound(role["joined_replay"])
        if joined_replay["joined_manifest_file"] != role["joined_manifest"] or len(joined_replay["sessions"]) != 6:
            raise ValueError("receiver joined replay ancestry differs")
        for session in joined["sessions"]:
            expected_receipt, expected_rows = row_records[role["role"], session["label"]]
            if handoff["codec_receipt_sha256s"][session["label"]] != expected_receipt:
                raise ValueError("receiver source receipt binding differs")
            if handoff["normalized_row_sha256s"][session["label"]] != expected_rows:
                raise ValueError("receiver normalized rows differ from independently parsed actual bytes")
        if any(handoff[key] is not False for key in (
                "controls_invoked", "reduction_invoked", "rng_invoked", "scoring_invoked",
                "scientific_allocation_charged", "scientific_candidate_selection_authorized",
                "telescope_provenance_established", "independent_draws_established")):
            raise ValueError("handoff authority differs")
    if checked_rows != 288 or checked_npy_files != 576:
        raise ValueError("actual row inventory was not fully verified")
    if pin(store_pin["path"], 64 * 1024) != store_pin or pin(driver_pin["path"], 64 * 1024) != driver_pin:
        raise ValueError("reviewed code bytes changed during read-only audit")
    if pin(acquisition.__file__, 64 * 1024) != original_pin or socket_attempts:
        raise ValueError("source bytes or socket capability changed")
    report = {"schema": "radio-source-session-independent-actual-attempt-review-v1", "status": "PASS",
        "probe": pin(__file__, 64 * 1024), "trusted_actual_index": index_pin,
        "driver": driver_pin, "store": store_pin, "original_acquisition": original_pin,
        "generated_files_verified": checked_files, "generated_bytes_verified": checked_bytes,
        "actual_inventory_exact": True, "sessions_replayed": replayed,
        "session_count": len(replayed), "one_cumulative_store_and_exact_prefixes_verified": True,
        "reserved_bytes_accounted": reserved, "accepted_bytes_accounted": accepted,
        "rows_independently_parsed": checked_rows, "npy_files_independently_parsed": checked_npy_files,
        "receiver_context_receipts_joined": len(index["roles"]),
        "prior_synthetic_evidence_pin": index["prior_acquisition_index_pin"],
        "checked_module_bytes_unchanged": True, "seconds": time.monotonic() - START,
        "source_session_created_or_resumed": False, "reservation_published": False,
        "socket_attempts": socket_attempts, "controls_invoked": False,
        "telescope_reads": 0, "scientific_admission": False,
        "limitations": ["This independently reproduces hashes of existing synthetic evidence, not a new oracle or independent draw.",
                        "Driver publication occurred after execution; this review verifies current bytes against the retained executed-code pin.",
                        "No hosted store, hostile concurrent filesystem custody, complete runtime or resource lifetime is qualified."]}
    destination = Path(args.output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical(report) + b"\n"
    with destination.open("xb") as handle:
        if handle.write(payload) != len(payload):
            raise OSError("short independent review report write")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"status": "PASS", "generated_files": checked_files, "generated_bytes": checked_bytes,
                      "sessions": len(replayed), "rows": checked_rows, "npy_files": checked_npy_files,
                      "seconds": report["seconds"], "output": str(destination)}))


if __name__ == "__main__":
    main()
