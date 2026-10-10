# Actual completion admission for RESULTS

Create this JSON only after all eight jobs and both empirical QA receipts have
actually completed. It is a new engineering admission, not a replacement for any
scientific receipt. Pass its path/SHA and the actual source acquisition/QA SHAs to
`build_results_package.py`, with the root GO flag.

Required fields:

- `schema`: `SETI_ADJACENT170_172_RESULTS_ACTUAL_COMPLETION_ADMISSION_V1`.
- `acquisition_receipt_sha256`, `source_QA_receipt_sha256`, and
  `source_manifest_sha256`: actual pinned receipt/metadata hashes; corrected V2
  manifest is `2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909`.
- `code_pins`: exact three delivery scripts `build_results_package.py`,
  `archive_common.py`, `reconstruct_raw_sidecars.py`, keyed by analysis-relative
  path, each value `{bytes, sha256}`. Freeze after static review.
- `safe_receipts`: ordered six `{path, sha256}` records beneath
  `results/search/{native170_batch01,native170_batch02,native170_batch03,
  native172_batch01,native172_batch02,native172_batch03}/EXECUTION_RECEIPT.json`.
- `boundary_receipts`: ordered two `{path, sha256}` records beneath
  `boundaries/results/{pair170_171,pair171_172}/measurement/EXECUTION_RECEIPT.json`.
- `actual_QA_receipts`: ordered `{kind, path, sha256, expected_status}` records,
  `interior` followed by `boundary`. The builder checks actual `counts.maps`,
  `counts.patches`, `counts.scan_profiles`, `counts.raw_cells_bitwise_checked`:
  interior1524/54/324/668736 and boundary12/18/108/222912, plus
  the complete respective QA count dictionaries, zero HTTP/BODY,
  `detector_or_score_rerun: false`, `fixed_track_optimization_applied: false`,
  and exact PASS status. Each QA must bind the exact six/two execution and scope
  SHA dictionaries, searched driver/freeze, source/acquisition prerequisites,
  current QA script SHA, and its actual public QA freeze. Both root-relative
  `all_input_byte_pins` inventories are authenticated byte for byte before
  packaging and afterward. Copied ZIP member pins must equal those empirical
  QA pins; changed maps/profiles/code cannot be repinned as a completed PASS.
- `raw_package_receipt`: `{path, sha256}` for the actual new RAW package receipt.
- `root_retention_receipt`: `{path, sha256}` for root's actual durability/removal
  record. The builder requires status
  `COMPLETE_ROOT_ONLY192_REDUNDANT_SIDECARS_REMOVED_AFTER_DURABLE_RAW_SAVE`, actual
  `raw_archive_sha256`, `acquisition_receipt_sha256`, `source_QA_receipt_sha256`,
  `sidecars_removed: 192`, `durable_RAW_save_confirmed: true`, and
  `compressed_H5_chunks_verified: 192`. This interface gives no agent deletion
  authority. Root writes this record only after the actual save/removal.
- `external_reference_file_pins`: analysis-relative `{bytes, sha256}` pins for
  external text-only references. Must include original171
  `analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json` and
  `analysis/runtime/EXACT_DEPENDENCY_RESTORATION.json`; preferably also prior171
  actual QA and unchanged scientific dependency source references. No H5,
  sidecars,wheels or ZIPs are accepted here.
  Also include every retained `.py/.json/.md/.txt/.csv/.log` file under sibling
  `analysis/s2017_next_native_execution/`: both control scripts, actual
  preflight receipt/logs, and every completed/failed wave's receipt/logs. The
  builder requires their explicit final pins; caches and flock files are omitted.
- `archive_filename`: one ZIP basename, recommended
  `SETI_S2017_ADJACENT170_172_RESULTS_2026-10-10.zip`.

Keep the admission JSON within the new phase tree so it enters the payload. The
builder writes a create-only archive below `delivery/packages/results/` and
`delivery/RESULTS_PACKAGE_RECEIPT.json` only after CRC/all-member SHA verification.
All original receipts, files and old archives remain untouched. Final ZIP
identity belongs in an external `DATA_PACKAGES.json`, excluded from its own ZIP.

The source-QA gate matches RAW's full schema/count/code/scope/freeze/compact pin
contract and its three canonical acquisition-record hashes. Source-QA's old
192 sidecar pins are not re-read after root's separately receipted removal;
saved-output QA's complete inventories and the surviving H5 compressed chunks
are authenticated without decoding power. All non-H5 new phase outputs and
external text/code provenance authenticated by either saved-output QA are
included. The exact cached HDF5 metadata `.bin` files listed in the immutable
V2 source manifest are authenticated before and after assembly but omitted from
RESULTS because RAW already preserves them. Their explicit pin dictionary,
count, byte total and canonical digest are recorded in package context/receipt.
Any other binary member or raw-range entry fails admission. No source H5,
compressed sidecar, wheels or prior ZIP are copied.

Include `review/AUXILIARY_FILE_QUARANTINE_RECEIPT.json` in the new phase payload.
It documents one preserved 44,826,624-byte unreferenced copy; its origin is
unknown. The `.bin` payload remains preserved separately, is excluded from both
scientific input inventories and RESULTS, and receives no deletion authority.

The RESULTS CLI also requires `--freeze-commit` with the actual40-hex public
builder freeze/readback commit. It is recorded in the archive context and final
receipt; it does not replace actual job/QA receipt identity.
