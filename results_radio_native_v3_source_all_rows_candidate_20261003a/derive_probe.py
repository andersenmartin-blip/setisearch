"""Derive a fresh all-row codec probe without modifying the retained probe."""
import hashlib
from pathlib import Path

BASE = Path('/workspace/scratch/8fcd6bf45392/setisearch-20261003-archive/results_radio_native_v3_hdf5_runtime_candidate_20261003a/source_profile_probe.py')
DEST = Path('/workspace/scratch/fa2e54995e11/source-candidate/all-rows-probe-20261003c')
raw = BASE.read_bytes()
if hashlib.sha256(raw).hexdigest() != 'ca339a21fc2c2e3e318d4ef97b2e63a98fb97877dcd4d3d63e55eb1c6733c8f9':
    raise ValueError('retained probe pin differs')
source = raw.decode()
replacements = [
    ('import resource\n', 'import resource\nimport struct\n'),
    ('OUT = ROOT / "results_radio_native_v3_hdf5_runtime_candidate_20261003a"', 'OUT = Path("/workspace/scratch/fa2e54995e11/source-candidate/all-rows-probe-20261003c")'),
    ('WORK = CANDIDATE / "exact-source-profile-probe-20261003a"', 'WORK = OUT / "generated"'),
    ('"generated_file_bytes": 32 * 1024**2', '"generated_file_bytes": 96 * 1024**2'),
    ('offsets = [(row, window) for row in (0, 15) for window in windows]', 'offsets = [(row, window) for row in range(16) for window in windows]'),
    ('dataset.id.get_num_chunks() != 6', 'dataset.id.get_num_chunks() != 48'),
    ('"row_indices_exercised": [0, 15], "rows_1_through_14_exercised": False', '"row_indices_exercised": list(range(16)), "rows_1_through_14_exercised": True'),
    ('"radio-native-v3-candidate-exact-source-profile-v1"', '"radio-native-v3-candidate-all-rows-source-profile-v2"'),
    ('"six full chunks, rows 0 and 15; synthetic only"', '"48 full chunks, all 16 rows and three declared windows; synthetic only"'),
    ('"source-profile-probe.json"', '"all-rows-probe.json"'),
    ('"source-profile-probe-error.json"', '"all-rows-probe-error.json"'),
    ('"radio-native-v3-candidate-source-profile-probe-failure-v1"', '"radio-native-v3-candidate-all-rows-profile-failure-v2"'),
]
for old, new in replacements:
    # The chunk-count assertion appears at both the encoder and decoder.
    expected = 2 if old in ('dataset.id.get_num_chunks() != 6', '"source-profile-probe.json"') else 1
    if source.count(old) != expected:
        raise ValueError('derivation anchor differs: ' + repr(old))
    source = source.replace(old, new)

helper = '''
def closure_snapshot():
    # Candidate package files, shared base stdlib (excluding site-packages),
    # loaded Python sources and all file-backed process mappings. This is a
    # bounded observed closure, not a complete runtime/lifetime certificate.
    paths = set()
    links = []
    candidate_root = CANDIDATE / "venv"
    for path in candidate_root.rglob("*"):
        if path.is_symlink():
            target = path.resolve(strict=True)
            if not target.is_relative_to(candidate_root):
                raise ValueError("candidate runtime link leaves candidate root")
            links.append({"path": str(path), "link_text": os.readlink(path),
                          "resolved_target": str(target), "target_is_directory": target.is_dir()})
            continue
        if path.is_file():
            paths.add(path.resolve())
    stdlib = Path(sys.base_prefix) / "lib/python3.12"
    for directory, subdirs, names in os.walk(stdlib):
        subdirs[:] = [name for name in subdirs if name != "site-packages"]
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                target = path.resolve(strict=True)
                if not target.is_relative_to(stdlib):
                    raise ValueError("base stdlib link leaves stdlib root")
                links.append({"path": str(path), "link_text": os.readlink(path),
                              "resolved_target": str(target), "target_is_directory": target.is_dir()})
                if target.is_file():
                    paths.add(target)
                continue
            if path.is_file():
                paths.add(path.resolve())
    modules = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).is_file():
            path = Path(filename).resolve()
            paths.add(path)
            modules[name] = str(path)
    mapped = set()
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[-1].startswith("/"):
            path = Path(fields[-1])
            if not path.is_file():
                raise ValueError("mapped runtime path unavailable")
            paths.add(path.resolve())
            mapped.add(str(path.resolve()))
    paths.add(Path(sys.executable).resolve())
    records = [file_pin(path) for path in sorted(paths)]
    return {"schema": "radio-candidate-observed-runtime-file-closure-v1",
            "files": records, "file_count": len(records), "links": links,
            "raw_bytes": sum(item["bytes"] for item in records),
            "loaded_module_paths": modules, "mapped_runtime_paths": sorted(mapped),
            "interpreter": str(Path(sys.executable).resolve()),
            "prefix": sys.prefix, "base_prefix": sys.base_prefix,
            "sys_path": sys.path, "isolated": bool(sys.flags.isolated),
            "dont_write_bytecode": sys.dont_write_bytecode,
            "complete_execution_runtime_freeze": False,
            "externally_observed_complete_lifetime": False}


def closure_payload(value):
    return {item["path"]: (item["bytes"], item["sha256"], item["allocated_bytes"])
            for item in value["files"]}


def independent_selected_bytes(chunk_index, row, start, stop):
    # Binary-exact integer arithmetic + stdlib IEEE-float packing independently
    # validates every selected synthetic value, without NumPy arithmetic.
    return b"".join(struct.pack("<f", 100 + ((i * 17 + chunk_index * 31 + row * 13) % 4093) / 4096
                               + ((i // 4096) % 17) / 32) for i in range(start, stop))

'''
source = source.replace('def main():\n', helper + 'def main():\n', 1)
source = source.replace('    WORK.mkdir(exist_ok=False)\n', '''    frozen_runtime = closure_snapshot()
    write(OUT / "runtime-closure-before.json", frozen_runtime)
    WORK.mkdir(exist_ok=False)
''', 1)
source = source.replace('    decoded = []\n', '''    decoded = []
    independent_cells = 0
''', 1)
source = source.replace('            if full.tobytes() != expected.tobytes() or selected.tobytes() != wanted.tobytes():\n', '''            independent = independent_selected_bytes(ci, row, lo - ci * CHUNKS[2], hi - ci * CHUNKS[2])
            if wanted.tobytes() != independent:
                raise ValueError("independent stdlib construction disagrees with NumPy")
            independent_cells += len(independent) // 4
            if full.tobytes() != expected.tobytes() or selected.tobytes() != wanted.tobytes():
''', 1)
source = source.replace('    result = {"schema":', '''    final_runtime = closure_snapshot()
    write(OUT / "runtime-closure-after.json", final_runtime)
    if closure_payload(frozen_runtime) != closure_payload(final_runtime):
        raise ValueError("runtime file bytes or complete candidate inventory changed during probe")
    if frozen_runtime["links"] != final_runtime["links"]:
        raise ValueError("observed runtime symlink topology changed during probe")
    if frozen_runtime["mapped_runtime_paths"] != final_runtime["mapped_runtime_paths"]:
        raise ValueError("runtime mapped-file closure changed during probe")
    if any(name == "seti_repeater" or name.startswith("seti_repeater.") for name in sys.modules):
        raise ValueError("source/scientific module unexpectedly loaded")
    budget()
    result = {"schema":''', 1)
source = source.replace('              "script_pin": file_pin(Path(__file__)),', '''              "script_pin": file_pin(Path(__file__)),
              "derived_from_retained_probe": file_pin(ROOT / "results_radio_native_v3_hdf5_runtime_candidate_20261003a/source_profile_probe.py"),
              "runtime_closure_before": file_pin(OUT / "runtime-closure-before.json"),
              "runtime_closure_after": file_pin(OUT / "runtime-closure-after.json"),
              "runtime_file_payloads_unchanged": True,
              "runtime_mapping_paths_unchanged": True,
              "runtime_closure_file_count": frozen_runtime["file_count"],
              "runtime_closure_raw_bytes": frozen_runtime["raw_bytes"],
              "complete_execution_runtime_freeze": False,
              "externally_observed_complete_lifetime": False,
              "independent_struct_verified_selected_cells": independent_cells,
              "maximum_sparse_chunk_population": 48,''', 1)
DEST.mkdir(exist_ok=False)
with (DEST / 'all_rows_probe.py').open('xb') as output:
    output.write(source.encode())
print(DEST / 'all_rows_probe.py')
