"""Reproducible, bounded checkpoints of the completed batch02 acquisition.

No network or publishing operations. Requires the final acquisition manifest.
Each ZIP contains at most 12 consecutive exposures and at most 300 MB. If a
12-exposure archive exceeds the byte bound, its final exposure is deferred to
the next archive. All successful input bytes and every product receipt are
included exactly once; shared acquisition metadata are repeated in each ZIP.
"""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import zipfile

OUT = Path(__file__).resolve().parent
BASE = OUT.parents[1]
DELIVERY = BASE.parents[1] / "harps_b02_delivery"
MAX_SPECTRA = 12
MAX_ZIP_BYTES = 300_000_000
STAMP = (2026, 11, 1, 0, 0, 0)


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def member_record(path):
    return dict(path=str(path.relative_to(BASE)), bytes=path.stat().st_size,
                sha256=sha(path))


def write_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for source in members:
            info = zipfile.ZipInfo(str(source.relative_to(BASE)), date_time=STAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info._compresslevel = 6
            with source.open("rb") as src, archive.open(info, "w") as dst:
                shutil.copyfileobj(src, dst, length=1_048_576)


def main():
    manifest_path = OUT / "products/MANIFEST.json"
    if not manifest_path.is_file():
        raise RuntimeError("Final acquisition MANIFEST.json does not exist yet")
    manifest = json.loads(manifest_path.read_text())
    products = manifest["products"]
    jobs = json.loads((OUT / "JOBS.json").read_text())
    plan = json.loads((OUT / "PLAN.json").read_text())
    selected = list(csv.DictReader((OUT / "SELECTED_HITS.csv").open()))
    ids = list(dict.fromkeys(row["dp_id"] for row in selected))
    key = lambda row: (row["dp_id"], row["kind"], row["filename"])
    assert len(products) == len(jobs) == plan["raw_products"] + plan["ancillary_products"] == 136
    assert len(set(map(key, products))) == len(products)
    assert set(map(key, products)) == set(map(key, jobs))
    assert len(ids) == plan["spectra"] == 68 and len(selected) == plan["hits"] == 237
    assert sha(BASE / "v2/review/REVIEW_INDEX.csv") == plan["input_index_sha256"]
    assert sha(BASE / "v2/production/V2_HITS.csv") == plan["hits_sha256"]
    assert sha(BASE / "v2/production/V2_DISPOSITIONS.csv") == plan["original_dispositions_sha256"]

    common = [OUT / name for name in (
        "PLAN.json", "SELECTED_HITS.csv", "JOBS.json", "ANCILLARY_QUERY.json",
        "ANCILLARY_METADATA.csv", "products/MANIFEST.json", "acquire.py",
        "package_inputs.py")]
    grouped = {}
    failed = []
    successful = []
    for dp_id in ids:
        entries = [row for row in products if row["dp_id"] == dp_id]
        assert len(entries) == 2 and {row["kind"] for row in entries} == {"RAW", "ANCILLARY"}
        paths = []
        for row in entries:
            receipt = OUT / "products" / (row["filename"] + ".json")
            assert json.loads(receipt.read_text()) == row
            if row["status"] == "DOWNLOADED":
                source = BASE / row["relative_path"]
                assert source.resolve().is_relative_to((OUT / "products").resolve())
                assert source.name == row["filename"]
                assert source.stat().st_size == row["bytes"]
                assert sha(source) == row["sha256"]
                paths.append(source)
                successful.append(row)
            else:
                assert row["status"] == "FAILED"
                failed.append(row)
            paths.append(receipt)
        grouped[dp_id] = paths

    DELIVERY.mkdir(parents=True, exist_ok=True)
    inventory_path = DELIVERY / "INPUT_CHECKPOINTS.json"
    if inventory_path.exists() or any(DELIVERY.glob("SETI_HARPS_V2_TRIAGE02_INPUTS_PART*_2026-11-01.zip")):
        raise RuntimeError("Checkpoint outputs already exist; inspect rather than overwrite")
    inventory = []
    all_archived_products = []
    offset = 0
    while offset < len(ids):
        part = len(inventory) + 1
        filename = f"SETI_HARPS_V2_TRIAGE02_INPUTS_PART{part}_2026-11-01.zip"
        dest = DELIVERY / filename
        temporary = DELIVERY / (filename + ".partial")
        count = min(MAX_SPECTRA, len(ids) - offset)
        while True:
            chosen = ids[offset:offset + count]
            members = [p for dp_id in chosen for p in grouped[dp_id]] + common
            assert len(members) == len(set(members))
            write_zip(temporary, members)
            if temporary.stat().st_size <= MAX_ZIP_BYTES:
                break
            if count == 1:
                raise RuntimeError("One exposure and shared metadata exceed ZIP byte bound")
            count -= 1

        records = [member_record(p) for p in members]
        with zipfile.ZipFile(temporary) as archive:
            assert archive.testzip() is None
            assert archive.namelist() == [r["path"] for r in records]
            for record in records:
                with archive.open(record["path"]) as handle:
                    assert hashlib.file_digest(handle, "sha256").hexdigest() == record["sha256"]
                assert archive.getinfo(record["path"]).file_size == record["bytes"]
        temporary.replace(dest)
        part_products = [r for r in successful if r["dp_id"] in chosen]
        all_archived_products.extend(r["relative_path"] for r in part_products)
        record = dict(filename=filename, local_path=str(dest), bytes=dest.stat().st_size,
                      sha256=sha(dest), files=len(records), spectra=len(chosen),
                      successful_products=len(part_products),
                      failed_products=sum(r["dp_id"] in chosen for r in failed),
                      exposure_ids=chosen, members=records)
        inventory.append(record)
        # A progressive record preserves successfully verified parts on interruption.
        (DELIVERY / "INPUT_CHECKPOINTS_PROGRESS.json").write_text(json.dumps(
            dict(complete=False, exposures_packaged=offset + count, parts=inventory), indent=2) + "\n")
        print(json.dumps({k: record[k] for k in ("filename", "bytes", "sha256", "files", "spectra")}), flush=True)
        offset += count

    assert len(all_archived_products) == len(set(all_archived_products)) == len(successful)
    assert set(all_archived_products) == {row["relative_path"] for row in successful}
    assert sum(row["spectra"] for row in inventory) == len(ids)
    summary = dict(complete=True, acquisition_manifest_sha256=sha(manifest_path),
                   packaging_script_sha256=sha(Path(__file__)),
                   spectra=len(ids), events=len(selected), successful_products=len(successful),
                   failed_products=len(failed),
                   max_spectra_per_archive=MAX_SPECTRA, max_archive_bytes=MAX_ZIP_BYTES,
                   archive_timestamp=list(STAMP),
                   reproducibility="Fixed ZIP timestamp, permissions, compression level and member order; input bytes preserved.",
                   parts=inventory)
    inventory_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(dict(inventory=str(inventory_path), parts=len(inventory),
                          bytes=sum(row["bytes"] for row in inventory),
                          successful_products=len(successful), failed_products=len(failed))), flush=True)


if __name__ == "__main__":
    main()
