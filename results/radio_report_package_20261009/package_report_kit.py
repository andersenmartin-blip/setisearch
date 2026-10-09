"""Copy and authenticate retained text/figures; never import scientific code."""
from pathlib import Path
import hashlib
import json
import os
import resource
import shutil
import time
import zipfile

started = time.perf_counter()
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
root = Path.cwd()
out = root / "results/radio_report_package_20261009"
stage = out / "_kit"
zip_path = out / "SETI_RADIO_REPORT_KIT_2026-10-09.zip"
assert not stage.exists() and not zip_path.exists(), "exclusive package already exists"
selection = json.loads((out / "_selection.json").read_text())
metadata = json.loads((out / "_source_metadata.json").read_text())
inputs = json.loads((root / selection["prerequisites_from"]).read_text())
prerequisites = {x["path"]: x for x in inputs["prerequisites"]}
coordinator = {x["path"]: x for x in inputs["coordinator_selected_members"]}
remote = {x["path"]: x for x in selection["remote_staged"]}
new = set(selection["new_payload"])
new.add("results/radio_report_package_20261009/REVIEW_REPORT_DELIVERY.md")
paths = sorted(set(prerequisites) | set(selection["local_extra"]) | new | set(remote))
stage.mkdir()
records = []


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def add(member, source, origin, source_path=None):
    assert not member.startswith("/") and ".." not in Path(member).parts
    assert not member.endswith((".npz", ".npy", ".fil", ".h5", ".tar.gz"))
    data = source.read_bytes()
    digest, blob = sha256(data), git_sha(data)
    if member in prerequisites:
        expected = prerequisites[member]
        assert len(data) == expected["bytes"]
        assert digest == expected["frozen_sha256"]
        assert blob == expected["git_blob_sha1"]
    if member in coordinator:
        expected = coordinator[member]
        assert len(data) == expected["bytes"] and digest == expected["sha256"]
    if member in metadata:
        expected = metadata[member]
        assert blob == expected["sha"], (member, blob, expected["sha"])
        if "bytes" in expected:
            assert len(data) == expected["bytes"]
    destination = stage / member
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    records.append({"path": member, "bytes": len(data), "SHA256": digest,
                    "git_blob_sha1": blob, "origin": origin,
                    "source_path": source_path or member})


for path in paths:
    if path in remote:
        add(path, out / "_kit_source" / path, remote[path]["origin"])
    elif path in new:
        add(path, root / path, "CREATED_AND_REVIEWED_2026_10_09")
    elif path in coordinator:
        add(path, root / path, "ORIGINAL_ARCHIVE_MEMBER_RESTORED_AND_VERIFIED_2026_10_08")
    else:
        add(path, root / path, "FROZEN_PREREQUISITE_OR_IMMUTABLE_GIT_TEXT")

readme = out / "_README.md"
readme.write_text("# SETI-radio: rapportkit 9. oktober 2026\n\n"
                  "Start med [rapporten](RADIO_REPORT_PACKAGE_2026-10-09.md) og "
                  "[vejledningen](results/radio_report_package_20261009/KIT_GUIDE.md).\n\n"
                  "sha256sum -c SHA256SUMS kontrollerer transportintegritet. "
                  "Udpakning starter ingen analyse. Scorekort/casearkiver er eksterne; "
                  "pakken indeholder metadata og seks originale PDF-figurer.\n")
add("README.md", readme, "PACKAGE_ENTRY_POINT_CREATED_2026_10_09")
add("EXTERNAL_BINDINGS.json", out / "EXTERNAL_BINDINGS.json", "EXTERNAL_REFERENCE_INDEX_CREATED_2026_10_09",
    "results/radio_report_package_20261009/EXTERNAL_BINDINGS.json")
records.sort(key=lambda x: x["path"])
manifest = {"status": "AUTHENTICATED_REPORT_KIT_PAYLOAD_ASOF_2026_10_09",
            "source_commit": "76405d84b096f1dea4ce9aded0e9aeb792bef220",
            "payload_file_count": len(records), "payload_bytes": sum(x["bytes"] for x in records),
            "original_prerequisite_hashes_checked": len(prerequisites),
            "score_maps_or_raw_power_included": False, "scientific_invocations": 0,
            "all_cases_offline_verifier_layout": False, "original_PDFs_included": 6,
            "manifest_and_SHA256SUMS_are_non_self_referential_control_files": True,
            "files": records}
manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
(stage / "KIT_MANIFEST.json").write_bytes(manifest_data)
(out / "KIT_MANIFEST.json").write_bytes(manifest_data)
sums = "".join(x["SHA256"] + "  " + x["path"] + "\n" for x in records)
sums += sha256(manifest_data) + "  KIT_MANIFEST.json\n"
(stage / "SHA256SUMS").write_text(sums)
(out / "SHA256SUMS").write_text(sums)

with zipfile.ZipFile(zip_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            info = zipfile.ZipInfo(path.relative_to(stage).as_posix(), (2026, 10, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
with zipfile.ZipFile(zip_path) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist()) == len(records) + 2
    assert len(set(archive.namelist())) == len(archive.namelist())
    for record in records:
        data = archive.read(record["path"])
        assert len(data) == record["bytes"] and sha256(data) == record["SHA256"]
    assert archive.read("KIT_MANIFEST.json") == manifest_data
    assert archive.read("SHA256SUMS") == sums.encode()
data = zip_path.read_bytes()
usage = resource.getrusage(resource.RUSAGE_SELF)
receipt = {"status": "PASS_AUTHENTICATED_KIT_PACKAGING_AND_ROUNDTRIP",
           "actual_date": "2026-10-09", "zip_path": str(zip_path.relative_to(root)),
           "zip_bytes": len(data), "zip_SHA256": sha256(data), "zip_git_blob_sha1": git_sha(data),
           "payload_files": len(records), "payload_bytes": manifest["payload_bytes"],
           "zip_members_including_two_control_files": len(records) + 2,
           "all_payload_hashes_and_ZIP_CRC_checked": True,
           "original_prerequisites_checked": len(prerequisites),
           "original_PDFs_copied_without_rendering": 6,
           "new_detector_generator_renderer_verifier_invocations": 0,
           "original_case_archives_or_score_maps_opened": False,
           "CPU_s_through_packaging_measurement": usage.ru_utime + usage.ru_stime,
           "wall_s_through_packaging_measurement": time.perf_counter() - started,
           "peak_RSS_bytes": usage.ru_maxrss * 1024,
           "metered_component_of_conservative100_CPU_s_reservation": True,
           "receipt_serialization_API_setup_and_publication_not_fully_metered": True,
           "no_refund_or_extra_component_debit": True}
(out / "PACKAGING_RECEIPT.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(receipt))
