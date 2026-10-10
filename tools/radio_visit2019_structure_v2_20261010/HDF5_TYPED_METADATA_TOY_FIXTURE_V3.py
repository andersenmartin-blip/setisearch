"""V3 source-only prepared fixtures: in-memory synthetic HDF5 metadata, no file data.

Root owns the single later invocation after exact source PASS. This runner
reads only this script and the explicitly pinned pure structure.py source;
it never opens a source HDF5 file, native module, array, URL or remote cache.
Every expected address/range is hand-built below, rather than produced by
the parser being checked. No fixture has been executed by its author.
"""
import argparse
import ast
import hashlib
import json
import pathlib
import resource
import signal
import time

SIZE = 32768
ROOT = 256
DATA = 512
CONT = 1024
HEAP = 8192
UNDEFINED = (1 << 64) - 1


def require(ok, explanation):
    if not ok:
        raise AssertionError(explanation)


def u(value, width):
    return value.to_bytes(width, "little")


def padded(raw):
    return raw + bytes((-len(raw)) % 8)


def message(kind, body=b"", flags=0):
    body = padded(body)
    return u(kind, 2) + u(len(body), 2) + bytes([flags]) + bytes(3) + body


def object_header(messages, count=None):
    raw = b"".join(messages)
    return b"\x01\0" + u(len(messages) if count is None else count, 2) + u(1, 4) + u(len(raw), 4) + bytes(4) + raw


def superblock(root=ROOT):
    raw = bytearray(96)
    raw[:8] = b"\x89HDF\r\n\x1a\n"
    raw[13:15] = b"\x08\x08"
    raw[16:20] = u(4, 2) + u(16, 2)
    raw[32:40] = u(UNDEFINED, 8)
    raw[40:48] = u(SIZE, 8)
    raw[48:56] = u(UNDEFINED, 8)
    raw[64:72] = u(root, 8)
    return bytes(raw)


def link(flags=0, name=b"data", target=DATA):
    raw = b"\x01" + bytes([flags])
    if flags & 4:
        raw += u(7, 8)  # arbitrary toy creation order
    if flags & 16:
        raw += b"\x01"  # UTF-8
    return message(6, raw + u(len(name), 1 << (flags & 3)) + name + u(target, 8))


def datatype_vlen(parent_version=1):
    parent = bytes([parent_version << 4]) + bytes(3) + u(1, 4) + u(0, 2) + u(8, 2)
    return b"\x19\x01\0\0" + u(16, 4) + parent


def descriptor(length=5, address=HEAP, index=1):
    return u(length, 4) + u(address, 8) + u(index, 4)


def attribute(datatype, data, version=1):
    name, space = b"meta\0", b"\x01" + bytes(7)
    head = bytes([version, 0]) + u(len(name), 2) + u(len(datatype), 2) + u(len(space), 2)
    if version == 1:
        return message(12, head + padded(name) + padded(datatype) + padded(space) + data)
    return message(12, head + name + datatype + space + data)


def heap_header():
    return b"GCOL\x01" + bytes(3) + u(4096, 8)


def heap_object(index, size, references=1):
    return u(index, 2) + u(references, 2) + bytes(4) + u(size, 8)


def ordinary_spans(data_messages=None, root_messages=None, root_count=None):
    return [(0, superblock()),
            (ROOT, object_header(root_messages or [link()], root_count)),
            (DATA, object_header(data_messages or [message(0)]))]


def safe_structure_namespace(raw, filename):
    """Verify a pure module before compilation; execute no CLI/import side effect."""
    tree = ast.parse(raw, filename=filename)
    for node in tree.body:
        if isinstance(node, ast.Import):
            require(all(alias.name in {"hashlib", "math"} for alias in node.names), "Unexpected target import")
        elif isinstance(node, ast.Assign):
            require(all(isinstance(item, (ast.Constant, ast.BinOp, ast.UnaryOp,
                                         ast.Add, ast.Sub, ast.Mult, ast.Pow,
                                         ast.FloorDiv, ast.LShift, ast.RShift,
                                         ast.UAdd, ast.USub))
                        for item in ast.walk(node.value)), "Target assignment is not a literal arithmetic constant")
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            require(not node.decorator_list, "Target decorator can execute at admission")
            if isinstance(node, ast.FunctionDef):
                for value in node.args.defaults + node.args.kw_defaults:
                    if value is not None:
                        ast.literal_eval(value)
            else:
                require(all(isinstance(base, ast.Name) and base.id in {"ValueError", "Exception"} for base in node.bases), "Unexpected target class base")
                require(all(isinstance(item, (ast.FunctionDef, ast.Pass)) or
                            (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str))
                            for item in node.body), "Target class body can execute I/O")
        else:
            require(isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str), "Target top-level statement can execute I/O")
    forbidden_calls = {"open", "__import__", "eval", "exec", "compile", "input", "read_bytes", "read_text", "write_bytes", "write_text", "urlopen", "request", "get", "post", "socket", "connect", "system", "popen"}
    for node in ast.walk(tree):
        require(not isinstance(node, ast.ImportFrom), "Unexpected from-import in target")
        if isinstance(node, ast.Import):
            require(node in tree.body, "Nested target imports are not admitted")
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            require(name not in forbidden_calls, "Target has forbidden I/O/import/dynamic call: " + name)
    namespace = {"__name__": "pure_synthetic_structure_fixture", "__file__": filename}
    exec(compile(tree, filename, "exec"), namespace)
    return namespace


def main():
    start = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (10, 12))
    resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("Toy wall cap")))
    signal.alarm(30)
    parser = argparse.ArgumentParser()
    parser.add_argument("--structure-source", required=True)
    parser.add_argument("--expected-structure-sha256", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    source = pathlib.Path(args.structure_source).resolve(strict=True)
    require(source.name == "structure.py" and source.suffix == ".py", "Only pure parser source is admitted")
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    require(digest == args.expected_structure_sha256 and len(raw) <= 65536, "Exact source pin/size differs")
    receipt_path = pathlib.Path(args.receipt)
    require(not receipt_path.exists() and receipt_path.suffix == ".json", "Existing receipt preserved")
    module = safe_structure_namespace(raw, str(source))
    results = []

    def run_case(name, spans, expected_status, expected_missing=None, expected_error=None):
        cached = [(offset, body, {"path": "synthetic://" + name + "/" + str(offset),
                                 "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
                  for offset, body in spans]
        cache = module["MetadataCache"](cached, SIZE)
        result = module["plan_source"]("synthetic_2019_metadata_only", cache, SIZE)
        require(result["status"] == expected_status, name + ": wrong status " + str(result))
        require(result["HTTP_requests"] == 0 and result["spectral_values_read"] is False and result["payload_ranges_proposed"] == 0, name + ": raw/network work leaked")
        if expected_missing is not None:
            actual = [(x["offset"], x["length"], x["object_kind"]) for x in result["missing_metadata_fragments"]]
            require(actual == expected_missing, name + ": range is not hand-expected " + str(actual))
            for miss in result["missing_metadata_fragments"]:
                require(miss["HTTP_authorized"] is False and miss["payload_pointer"] is False and
                        bool(miss["typed_parent_evidence"]), name + ": parent provenance absent")
        if expected_error:
            require(any(expected_error in x for x in result["invalid"] + result["unsupported"]), name + ": wrong fail-closed reason")
        results.append({"case": name, "passed": True, "actual_status": result["status"],
                        "missing_fragments": result["missing_metadata_fragments"],
                        "errors": result["invalid"] + result["unsupported"]})
        return result

    complete = "COMPLETE_SUPPORTED_HEADER_STRUCTURE"
    missing = "INCOMPLETE_TYPED_METADATA_FRAGMENTS"
    invalid = "INVALID_METADATA"
    unsupported = "UNSUPPORTED_FORMAT"
    basic = run_case("v0_root_entry_v1_data_hardlink", ordinary_spans(), complete, [])
    require(basic["superblock"]["root_object_header_relative_address"] == ROOT and basic["counts"]["object_headers"] == 2, "Root address/objects differ")
    continuation = message(16, u(CONT, 8) + u(len(link()), 8))
    run_case("v1_continuation_without_OCHK", ordinary_spans(root_messages=[continuation], root_count=2) + [(CONT, link())], complete, [])
    run_case("typed_continuation_missing_exact24bytes", ordinary_spans(root_messages=[continuation], root_count=2), missing, [(CONT, 24, "v1_object_header_messages")])
    cyclic = message(16, u(ROOT + 16, 8) + u(24, 8))
    run_case("v1_continuation_cycle", ordinary_spans(root_messages=[cyclic]), invalid, [], "cycle")
    run_case("v1_total_message_count_mismatch", ordinary_spans(root_count=2), invalid, [], "message count")
    fixed_string = b"\x13" + bytes(3) + u(16, 4)
    run_case("fixed_string_descriptor_lookalike_no_GCOL_edge", ordinary_spans([attribute(fixed_string, descriptor())]), complete, [])
    vl = datatype_vlen()
    # V2 adds two unsupported-format cases; the original twenty expectations are unchanged.
    compound = b"\x16" + bytes(3) + u(16, 4)
    run_case("unsupported_compound_attribute_no_GCOL_edge", ordinary_spans([attribute(compound, descriptor())]), unsupported, [], "Compound/reference")
    unsupported_space = bytearray(attribute(vl, descriptor()))
    # Eight-byte message envelope + eight-byte attribute header + v1 padded name/datatype.
    space_offset = 8 + 8 + len(padded(b"meta\0")) + len(padded(vl))
    unsupported_space[space_offset] = 2
    run_case("unsupported_VL_dataspace_version_no_GCOL_edge", ordinary_spans([bytes(unsupported_space)]), unsupported, [], "dataspace version")
    # Complete cached collection; free-object size includes its own header.
    gh = [(HEAP, heap_header()), (HEAP + 16, heap_object(1, 5)),
          (HEAP + 32, b"hello" + bytes(3)),
          (HEAP + 40, heap_object(0, 4056, 0) + bytes(4040))]
    for version in (1, 2):
        version_heap = [(offset, heap_object(1, 5, 0) if offset == HEAP + 16 and version == 1 else body)
                        for offset, body in gh]
        run_case("typed_vlen_attribute_v" + str(version) + ("_live_refs0" if version == 1 else "_refs1"),
                 ordinary_spans([attribute(vl, descriptor(), version)]) + version_heap, complete, [])
    zero_refs = [(offset, heap_object(1, 5, 0) if offset == HEAP + 16 else body) for offset, body in gh]
    run_case("live_refs0_still_rejects_attribute_length_mismatch",
             ordinary_spans([attribute(vl, descriptor(length=6))]) + zero_refs,
             invalid, [], "length differs")
    run_case("typed_GCOL_header_missing_exact16bytes", ordinary_spans([attribute(vl, descriptor())]), missing, [(HEAP, 16, "global_heap_collection_header")])
    run_case("typed_string_data_missing_exact5bytes", ordinary_spans([attribute(vl, descriptor())]) + gh[:2] + [(HEAP + 37, bytes(3))] + gh[3:], missing, [(HEAP + 32, 5, "referenced_string_attribute_heap_bytes")])
    skipped = [(HEAP, heap_header()), (HEAP + 16, heap_object(1, 13)),
               (HEAP + 48, heap_object(2, 5)), (HEAP + 64, b"hello" + bytes(3)),
               (HEAP + 72, heap_object(0, 4024, 0) + bytes(4008))]
    blocked = run_case("uncached_untyped_live_data13bytes_blocks_whole_collection",
                      ordinary_spans([attribute(vl, descriptor(index=2))]) + skipped,
                      unsupported, [], "untyped live data")
    require(blocked["global_heap_collection_coverage"][0]["uncovered_untyped_live_intervals"] ==
            [[HEAP + 32, HEAP + 48]], "Unknown live body/alignment hole differs")
    # Root attribute heap remains independently provable while the data OH
    # continuation is missing. No raw dataset chunk pointer participates.
    dual_spans = [(0, superblock()),
        (ROOT, object_header([attribute(vl, descriptor()), link()])),
        (DATA, object_header([continuation], count=2))] + gh[:3] + [(HEAP + 40, heap_object(0, 4056, 0))]
    dual = run_case("typed_free_tail_plus_missing_data_OH_continuation",
        dual_spans, missing, [(CONT, 24, "v1_object_header_messages"),
                             (HEAP + 56, 4040, "global_heap_proven_free_space")])
    require(dual["global_heap_collection_coverage"][0]["free_space_interval_half_open"] ==
            [HEAP + 40, HEAP + 4096], "Free extent proof differs")
    free = [(HEAP, heap_header()), (HEAP + 16, heap_object(0, 4080, 0) + bytes(4064))]
    run_case("free_object_size_includes_header", ordinary_spans([attribute(vl, descriptor())]) + free, invalid, [], "index absent")
    badfree = [(HEAP, heap_header()), (HEAP + 16, heap_object(0, 4064, 0))]
    run_case("free_object_data_only_size_rejected", ordinary_spans([attribute(vl, descriptor())]) + badfree, invalid, [], "free object size")
    run_case("unsupported_parent_datatype_version", ordinary_spans([attribute(datatype_vlen(15), descriptor())]), unsupported, [])
    run_case("typed_reference_outside_file_rejected", ordinary_spans([attribute(vl, descriptor(address=SIZE - 8))]), invalid, [], "outside")
    # Hand-built legacy metadata; local names are deliberately relocated.
    tree, snod, local, names_at = 2048, 3072, 4096, 12288
    names = b"\0data\0" + bytes(10)
    tree_bytes = b"TREE\0\0" + u(1, 2) + u(UNDEFINED, 8) * 2 + u(0, 8) + u(snod, 8) + u(1, 8)
    heap_bytes = b"HEAP\0" + bytes(3) + u(16, 8) + u(UNDEFINED, 8) + u(names_at, 8)
    entry = u(1, 8) + u(DATA, 8) + bytes(24)
    symbol_bytes = b"SNOD\x01\0" + u(1, 2) + entry
    legacy = ordinary_spans(root_messages=[message(17, u(tree, 8) + u(local, 8))]) + [(tree, tree_bytes), (snod, symbol_bytes), (local, heap_bytes), (names_at, names)]
    run_case("legacy_TREE0_relocated_HEAP_SNOD_data_only", legacy, complete, [])
    raw_tree = [(offset, (body[:4] + b"\x01" + body[5:]) if offset == tree else body) for offset, body in legacy]
    run_case("TREE1_chunk_storage_not_followed", raw_tree, unsupported, [], "group TREE type 0")
    run_case("compact_hardlink_width4_corder_utf8", ordinary_spans(root_messages=[link(2 | 4 | 16)]), complete, [])
    layout = message(8, b"\x03\x02\x04" + u(24576, 8) + u(1, 4) + u(1, 4) + u(8, 4) + u(4, 4))
    run_case("raw_layout_pointer_never_queued", ordinary_spans([layout]), complete, [])
    partial = module["plan_source"]("synthetic_2019_metadata_only", module["MetadataCache"]([(0, superblock()[:8], {"bytes": 8, "sha256": hashlib.sha256(superblock()[:8]).hexdigest()})], SIZE), SIZE)
    require(partial["status"] != complete, "Partial superblock falsely COMPLETE")
    results.append({"case": "partial_superblock_no_false_COMPLETE", "passed": True, "actual_status": partial["status"]})
    require(len(results) == 24, "Exact finite synthetic inventory differs")
    require(source.read_bytes() == raw, "Source changed during toys")
    cpu, elapsed = time.process_time(), time.monotonic() - start
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    require(cpu <= 10 and elapsed <= 30 and rss <= 1073741824, "Synthetic resource cap exceeded")
    receipt = {"status": "PASS_SYNTHETIC_ONLY_HDF5_TYPED_METADATA_FIXTURES_V3", "structure_source_pin": {"path": str(source), "sha256": digest, "bytes": len(raw)},
               "fixture_source_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
               "preserved_original_fixture_source_sha256": "93ded18d7a7436765a1bb7a57de8c84ce823173dcc058f367c18ed334f3e77a9",
               "new_V2_policy": "live_refs0_implementation_compatibility_and_proven_GCOL_metadata_coverage",
               "fixture_cases": results, "passed_cases": len(results), "source_end_pin_exact": True,
               "actual_HDF5_source_or_cached_telescope_bytes_opened": False, "arrays_or_h5py_imported": False,
               "network_or_source_GET": False, "pure_target_definitions_executed_only_with_handmade_metadata_bytes": True,
               "no_scientific_detector_or_profiles_or_medians_or_matching": True,
               "CPU_cap_s": 10, "wall_cap_s": 30, "memory_cap_bytes": 1073741824,
               "process_CPU_seconds_including_imports": cpu, "wall_seconds": elapsed, "peak_RSS_bytes": rss}
    with receipt_path.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    signal.alarm(0)
    print(json.dumps({"status": receipt["status"], "passed_cases": len(results), "CPU_seconds": cpu, "receipt": str(receipt_path)}))


if __name__ == "__main__":
    main()
