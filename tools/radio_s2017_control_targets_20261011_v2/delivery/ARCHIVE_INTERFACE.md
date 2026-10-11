The archive builder is standard-library source code. It has not run during
preparation. No observations, saved numerical arrays or ZIPs are opened to
prepare it. Root supplies the final byte manifest only after all three
primary jobs, primary QA, context execution and context QA are complete.

The manifest is JSON with these fields:

```text
schema: SETI_S2017_CONTROL_RESULTS_MANIFEST_V1
status: CLOSED_ROOT_SELECTED_BYTE_MANIFEST_AFTER_ALL_QA_PASS
science_public_freeze_commit: <40 hexadecimal commit>
gates:
  primary_receipts: {<three primary IDs>: {path,bytes,sha256}}
  primary_QA: {path,bytes,sha256}
  context_execution: {path,bytes,sha256}
  context_QA: {path,bytes,sha256}
  primary_scope: {path,bytes,sha256}
  context_scope: {path,bytes,sha256}
  primary_driver: {path,bytes,sha256}
  context_driver: {path,bytes,sha256}
  primary_QA_script: {path,bytes,sha256}
  context_QA_script: {path,bytes,sha256}
  primary_QA_scope: {path,bytes,sha256}
  context_QA_scope: {path,bytes,sha256}
members: [{source_path,archive_path,bytes,sha256}, ...]
required_report_paths: [<final Markdown report>, <reviewable PNG>, ...]
```

All paths are relative to the workspace. Gate paths use the existing new
phase namespace: primary `results/<primary_id>/EXECUTION_RECEIPT.json`,
primary QA `results/review/QA_RECEIPT.json`, context execution
`results/context/EXECUTION_RECEIPT.json`, and context QA
`results/context_review/QA_RECEIPT.json`. Code/scope gate names map to
driver.py, context_profiles.py, qa_saved.py, qa_context.py, scope.json,
context_scope.json, qa_scope.json and qa_context_scope.json.

The exact selected member list must include every declared primary and
context output, both QA output namespaces, the actual gate files, final
report/PNG and the root-selected source reference metadata/code/scopes and
review records. Any additional regular file in the results namespace makes
actual packaging fail until root closes its explicit manifest membership.
Scientific NPZ members must be from this new phase and authenticated in an
actual QA receipt. HDF5, raw bins, locks, caches and prior preparations are
excluded. No original source payload is duplicated. The root manifest is
automatically added as the reserved ZIP member MANIFEST.json.

The exact final report PNG at
`analysis/s2017_control_targets_20261011_v2/delivery/SETI_CONTROL_TARGETS_2026-10-11.png`
is allowed when root lists it in required_report_paths and pins it in the
manifest. Other scientific NPZ/PNG artifacts belong to the results namespace.

The create-only output is
`deliverables/SETI_CONTROL_TARGET_RESULTS_2026-10-11.zip`, with terminal
`deliverables/SETI_CONTROL_TARGET_RESULTS_2026-10-11_ARCHIVE_RECEIPT.json`.
Root archive GO at `delivery/ARCHIVE_ROOT_GO.json` contains:

```json
{
  "status": "GO_SERIALIZED_CLOSED_CONTROL_RESULTS_ARCHIVE",
  "manifest_sha256": "<closed manifest SHA256>",
  "builder_sha256": "<reviewed builder SHA256>",
  "all_filesystem_actors_paused": true,
  "CPU_cap_s": 300,
  "wall_cap_s": 600,
  "memory_cap_bytes": 536870912,
  "archive_cap_bytes": 524288000,
  "workspace_cap_bytes": 8589934592
}
```

CLI (root executes later):

```text
build_archive.py --root <workspace> --manifest <root manifest path>
                 --manifest-sha256 <SHA> --builder-sha256 <SHA>
                 --root-go-sha256 <SHA>
```

`--check-only` validates the closed metadata gates and declared manifest,
without reading scientific NPZ bytes or constructing an archive. Actual
archive creation uses the retained family EX lock and archive EX lock;
root serializes all filesystem actors. It verifies selected whole-file
pins before writing, streams and authenticates every member, validates the
fresh O_NOFOLLOW pathname FD (regular inode/size match) and all ZIP member
CRCs/SHA256s on that same reader, reopens O_NOFOLLOW for a final whole SHA
check, rechecks every source pin,
fsyncs its terminal receipt and parent directory while the original writer
FD remains open, then closes that original FD. Incomplete outputs are
preserved without automatic retry.
