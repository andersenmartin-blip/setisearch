"""Package existing results byte-exactly; never open science array formats.

Run only after saved-output and claims QA have finished. Public Git exports
large JSON as lossless gzip; the ZIP retains both original JSON and gzip.
"""
from pathlib import Path
import gzip
import hashlib
import json
import resource
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/radio_gap_static_context_20261010"
ARCHIVE = ROOT.parent / "SETI_GAP_STATIC_CONTEXT_2026-10-10.zip"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def save(p, value):
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n")

def main():
    start = time.process_time()
    original = OUT / "measurement/STATIC_CONTEXT_PROFILES.json"
    raw = original.read_bytes()
    packed = gzip.compress(raw, compresslevel=6, mtime=0)
    assert gzip.decompress(packed) == raw
    (original.with_suffix(".json.gz")).write_bytes(packed)
    # Every new code/evidence file, plus the unchanged fifteen pinned inputs.
    paths = set()
    for folder in (OUT, ROOT / "tools/radio_gap_static_context_20261010"):
        paths.update(p for p in folder.rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts
                     and p.name not in {"BUNDLE_MANIFEST.json", "BUNDLE_RECEIPT.json",
                         "PUBLICATION_PLAN.json", "DELIVERY_RECEIPT.json"})
    paths.add(ROOT / "RADIO_GAP_STATIC_CONTEXT_REPORT_2026-10-10.md")
    # The executed restoration code reads two saved prior PyPI receipts.
    previous_evidence = ROOT / "results/radio_gap_drift_20261010/environment_evidence"
    paths.update(p for p in previous_evidence.rglob("*") if p.is_file()
                 and p.suffix in {".py", ".json", ".log"})
    recovery_source = ROOT.parent / "seti_gap_static_work/recover_saved_inputs.py"
    recovery_copy = ROOT / "tools/radio_gap_static_context_20261010/recover_saved_inputs.py"
    recovery_copy.write_bytes(recovery_source.read_bytes())
    paths.add(recovery_copy)
    scope = json.loads((ROOT / "tools/radio_gap_static_context_20261010/scope.json").read_text())
    for name, expected in scope["pinned_dependency_files"].items():
        p = ROOT / name
        assert sha(p.read_bytes()) == expected, name
        paths.add(p)
    names = {p.relative_to(ROOT).as_posix(): p for p in paths}
    manifest = {"schema": "SETI_GAP_STATIC_CONTEXT_BYTE_EXACT_BUNDLE_V1",
        "public_freeze_commit": "1fbb2fcf328581a7ceffda97d6db36850c4ba8ea",
        "scientific_reruns": 0, "new_telescope_requests": 0,
        "external_compact_input_archive": {
            "filename": "SETI_FRESH_BAND151_RAW_2026-10-09.zip",
            "bytes": 305428707,
            "sha256": "6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d"},
        "large_original_telescope_files_and_dependency_wheels_included": False,
        "six_compact_H5_files_included": False,
        "all_fifteen_pinned_dependencies_except_external_compact_H5_present": True,
        "CSV_byte_preservation": "Original CRLF and float round-trip text retained",
        "gzip_original_JSON_roundtrip_verified": True,
        "files": [{"path": n, "bytes": p.stat().st_size,
            "sha256": sha(p.read_bytes())} for n,p in sorted(names.items())]}
    manifest_path = OUT / "BUNDLE_MANIFEST.json"
    save(manifest_path, manifest)
    names[manifest_path.relative_to(ROOT).as_posix()] = manifest_path
    assert not ARCHIVE.exists(), "No bundle overwrite"
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as z:
        for name,p in sorted(names.items()):
            z.write(p, name)
    with zipfile.ZipFile(ARCHIVE) as z:
        assert len(z.namelist()) == len(names)
        assert z.testzip() is None
        for name,p in names.items():
            assert z.read(name) == p.read_bytes(), name
    elapsed = time.process_time()-start
    assert elapsed < 3, "Packaging component exceeds 3 CPU-seconds"
    receipt = {"status": "PASS_BYTE_EXACT_ZIP_ALL_MEMBERS_AND_CRC",
        "archive_filename": ARCHIVE.name, "archive_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha(ARCHIVE.read_bytes()), "member_count": len(names),
        "manifest_sha256": sha(manifest_path.read_bytes()),
        "member_bytes_and_hashes_verified": True, "all_ZIP_CRC_verified": True,
        "gzip_lossless_original_JSON_verified": True, "CSV_CRLF_preserved": True,
        "process_CPU_s": time.process_time(), "packaging_interval_CPU_s": elapsed,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        "science_arrays_decoded_or_remeasured": False,
        "archive_save_state": "LOCAL_COMPLETE_PENDING_DURABLE_SAVE"}
    save(OUT / "BUNDLE_RECEIPT.json", receipt)
    # Git already retains source code and old inputs. Export only new results,
    # scripts and the report; binary array bundle is delivered through ZIP.
    publication = []
    new_paths = set(p for folder in (OUT, ROOT / "tools/radio_gap_static_context_20261010")
                    for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    new_paths.add(ROOT / "RADIO_GAP_STATIC_CONTEXT_REPORT_2026-10-10.md")
    for p in sorted(new_paths):
        if p.suffix == ".npz" or p == original or p.name == "PUBLICATION_PLAN.json":
            continue
        b = p.read_bytes()
        binary = p.suffix in {".png", ".gz", ".csv"}
        publication.append({"path": p.relative_to(ROOT).as_posix(),
            "encoding": "base64" if binary else "utf-8", "bytes": len(b),
            "sha256": sha(b),
            "git_blob_sha": hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()})
    save(OUT / "PUBLICATION_PLAN.json", {"files": publication})
    print(json.dumps(receipt))

if __name__ == "__main__":
    main()
