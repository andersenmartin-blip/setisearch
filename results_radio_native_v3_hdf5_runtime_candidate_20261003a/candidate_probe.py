"""Candidate-only deterministic codec probe; does not import SETI source code."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import struct
import sys

import h5py
import hdf5plugin
import numpy as np

CANDIDATE = Path("/workspace/scratch/8fcd6bf45392/seti-hdf5-runtime-candidate-20261003a")
REPOSITORY = Path("/workspace/scratch/8fcd6bf45392/setisearch-20261003-archive")
OUTPUT = REPOSITORY / "results_radio_native_v3_hdf5_runtime_candidate_20261003a"
PROBES = CANDIDATE / "synthetic-probes"


def pin(path):
    raw = path.read_bytes()
    st = path.stat()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "allocated_bytes": st.st_blocks * 512}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def write_exclusive(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


if Path(sys.prefix).resolve() != (CANDIDATE / "venv").resolve():
    raise RuntimeError("probe requires the isolated candidate Python")
if not sys.dont_write_bytecode or not sys.flags.isolated:
    raise RuntimeError("probe requires -I -B")
PROBES.mkdir(exist_ok=False)
source = (np.arange(2048, dtype=np.int64) % 257).astype("<f4") * np.float32(0.125)
source = source.reshape(32, 64)
expected = b"".join(struct.pack("<f", (i % 257) * 0.125) for i in range(2048))
if source.tobytes(order="C") != expected:
    raise RuntimeError("NumPy deterministic construction differs from independent struct construction")
source_hash = hashlib.sha256(expected).hexdigest()
cases = [("plain", {}), ("gzip-shuffle-fletcher32", {"compression": "gzip", "compression_opts": 4,
          "shuffle": True, "fletcher32": True}),
         ("bitshuffle-lz4", dict(hdf5plugin.Bitshuffle(nelems=0, cname="lz4")))]
rows = []
for name, options in cases:
    path = PROBES / (name + ".h5")
    with h5py.File(path, "x") as file:
        dataset = file.create_dataset("synthetic_values", data=source, chunks=(8, 64), **options)
        file.flush()
    with path.open("rb") as handle:
        os.fsync(handle.fileno())
    with h5py.File(path, "r") as file:
        dataset = file["synthetic_values"]
        actual = dataset[...]
        dcpl = dataset.id.get_create_plist()
        filters = []
        for index in range(dcpl.get_nfilters()):
            identifier, flags, parameters, label = dcpl.get_filter(index)
            filters.append({"id": identifier, "flags": flags, "parameters": list(parameters),
                            "label": label.decode("ascii", "replace")})
        if actual.shape != (32, 64) or actual.dtype.str != "<f4" or actual.tobytes(order="C") != expected:
            raise RuntimeError("synthetic round-trip differs: " + name)
        rows.append({"case": name, "file": pin(path), "shape": list(actual.shape), "dtype": actual.dtype.str,
                     "decoded_bytes": actual.nbytes, "decoded_sha256": hashlib.sha256(actual.tobytes()).hexdigest(),
                     "filters": filters, "round_trip_exact": True})

site = Path(h5py.__file__).parent.parent.resolve()
binaries = []
for package in ("h5py", "h5py.libs", "hdf5plugin", "numpy", "numpy.libs"):
    for path in sorted((site / package).rglob("*")):
        if path.is_file() and ".so" in path.name:
            item = pin(path)
            item["site_relative_path"] = path.relative_to(site).as_posix()
            binaries.append(item)
historical = REPOSITORY / "results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json"
old = json.loads(historical.read_bytes())
by_relative = {item["site_relative_path"]: item for item in binaries}
matches = []
missing = []
mismatched = []
for relative, digest in sorted(old["binary_sha256s"].items()):
    current = by_relative.get(relative)
    if current is None:
        missing.append(relative)
    elif current["sha256"] != digest:
        mismatched.append({"path": relative, "historical_sha256": digest, "candidate_sha256": current["sha256"]})
    else:
        matches.append(relative)

mapped = set()
for line in Path("/proc/self/maps").read_text().splitlines():
    fields = line.split(maxsplit=5)
    if len(fields) == 6 and fields[-1].startswith("/") and ".so" in fields[-1]:
        mapped.add(fields[-1])
loaded = [pin(Path(path)) for path in sorted(mapped) if Path(path).is_file()]
result = {"schema": "radio-native-v3-hdf5-runtime-candidate-probe-v1", "authority": "candidate-only",
          "project_module_invocations": 0, "source_analysis_invocations": 0, "rng_invocations": 0,
          "telescope_or_holdout_inputs_opened": 0, "synthetic_source": {"construction": "float32((i % 257) * 0.125), i=0..2047",
          "independent_struct_agreement": True, "bytes": len(expected), "sha256": source_hash},
          "runtime": {"python": platform.python_version(), "python_binary": pin(Path(sys.executable)),
          "prefix": sys.prefix, "base_prefix": sys.base_prefix, "isolated": bool(sys.flags.isolated),
          "dont_write_bytecode": sys.dont_write_bytecode, "sys_path": sys.path,
          "pyvenv_configuration": (CANDIDATE / "venv/pyvenv.cfg").read_text(),
          "machine": platform.machine(), "byteorder": sys.byteorder, "libc": list(platform.libc_ver()),
          "numpy": np.__version__, "h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version,
          "hdf5plugin": importlib.metadata.version("hdf5plugin")},
          "codec_probes": rows, "candidate_native_binaries": binaries, "loaded_native_mappings": loaded,
          "historical_binary_comparison": {"historical_metadata": pin(historical), "expected_count": len(old["binary_sha256s"]),
          "matching_count": len(matches), "matching_paths": matches, "missing_paths": missing, "mismatches": mismatched,
          "identity_continuity_established": False, "historical_storage_or_inode_recovery_established": False},
          "source_specific_codec_runtime_certificate": False, "complete_execution_runtime_freeze": False,
          "scientific_trial_admission": False, "historical_original_runtime_restored": False}
target = OUTPUT / "candidate-probe.json"
write_exclusive(target, canonical(result))
print(json.dumps({"status": "pass", "report": pin(target), "runtime_versions": {key: result["runtime"][key]
      for key in ("python", "numpy", "h5py", "hdf5", "hdf5plugin")}, "probes": len(rows),
      "historical_binary_byte_matches": len(matches), "historical_expected": len(old["binary_sha256s"]),
      "candidate_only": True}, sort_keys=True))
