# Fixed Burst4 temporal-order diagnostics: reproduction and data availability

This prospective document describes the fixed diagnostic and its exact source availability. Actual completion is established by three terminal COMPLETE receipts, the independent PASS numerical QA receipt and the completed report receipt. No result or QA success is asserted before execution.

## Scientific scope

This phase follows all 1,161 previously saved score-audit tuples from the completed Burst4 pilot: 387 for each original OFF scan of HIP97319, HIP97461 and HIP97663 on 28 April 2017. It does not repeat the original carrier/window/drift/width maximization. Every tuple's selected carrier, four source rows, rounded track centers, width and saved full-sixteen-row normalization remain fixed. The nine target-global TOP3 tuples are already part of the complete audit set, not additional independent measurements.

For each tuple the new diagnostic evaluates a four-by-four row/center matrix, using each of the selected four original time rows at each of the four already fixed track centers. The 24 assignments are every permutation of four elements. Each assignment uses one matrix element from each row and column with the original four-row score denominator. The original diagonal corresponds to the retained winner. All 24 scores remain retained; distinct assignments are deduplicated by the actual integer center vector, using its first lexicographic representative. Exact best/worst ranks use greater/equal counts among these distinct assignments, with zero tie epsilon. An alternative-order statistic is undefined when all centers are identical and only the identity vector remains.

There are 18,576 row/center box terms and 27,864 assignment scores. These are deterministic dependent comparisons from selected, exposed data. A count of assignments at least as large as the observed diagonal is not a calibrated p-value, sky false-alarm probability or an independent null realization. Original winner selection and normalization conditioning remain. No new search grid, parameter fit, threshold, noise law, blind validation, telescope observation or source classification is introduced.

A row/center matrix requires local raw neighborhoods around every fixed center in every selected row. New capsules retain the exact source bits covering those neighborhoods, matrix terms and all permutation scores. The prior four-row raw503 capsules are included as pinned bit-identity anchors. Whole-sixteen-row normalization JSONs are included for all 288 old cores. Independent numerical QA reconstructs local501 arithmetic, assignment scores, the original diagonal match and retained raw-bit identities without importing the detector or rerunning its grid. The local score arithmetic remains conditional on the authenticated saved full-core residual MAD/location; no new calibration is claimed.

Original A/B remains FAIL_CLOSED. Protected 2016 arrays and banks, the old closed observations, and blocked 2019 value access are not reopened. Each of the three primary stars still has one original scan. This engineering diagnostic does not qualify a SETI detection or prove signal origin.

## Package contents and external source bytes

The new ZIP includes all new phase code, scope, admissions, reviews, query matrices/raw neighborhoods, numerical QA and report/table/figure evidence. It also includes only declared prior byte pins: old SCORE_AUDITS/TOP3/receipts/scopes, the 288 compact normalization JSONs, the 1,161 old raw503 anchors, exact detector/reader code, source manifests/acquisition receipts and restoration metadata. It omits old full carrier-map arrays and all full HDF5 compacts.

The exact compact bytes are available from the previously retained canonical raw archives:

| Canonical package | Bytes | SHA256 |
|---|---:|---|
| `SETI_S2017_NATIVE171_RAW_2026-10-10.zip` | 466351822 | `6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786` |
| `SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip` | 604399781 | `b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f` |

The second archive is retained in three ordered parts. Concatenate `.zip.part01`, `.zip.part02` and `.zip.part03` in that order, verify the complete archive hash, then extract.

| Part | Bytes | SHA256 |
|---|---:|---|
| 01 | 209715200 | `ad4be599d3e7da809df1d473c8fa677e0c2581d251fb65d9cc01d90849dd8dbb` |
| 02 | 209715200 | `2ad6609f4984c536fc4dbee2223975f756459d681b8c9e1f5c6b8731f149a97f` |
| 03 | 184969381 | `d585965102de3ac3cbc9864a92249e0fb660ed6968540249c34e650b880b15ca` |

These packages supply 18 compact sources. This phase uses only the nine OFF compacts across native170/171/172. The frozen scope's `source_compacts` records are authoritative for their exact paths, bytes, SHA256, original metadata and decoded-row identities. Restore native171 files at `analysis/new_visit_recovery/results/acquire/<scan_id>.compact.h5` and native170/native172 files at `analysis/s2017_next_native/results/acquire/native<native>_<scan_id>.compact.h5`. Required OFF scan IDs are `epoch1_off`, `epoch2_off`, `epoch3_off`. Restore original HDF5 bytes rather than repacking equivalent arrays.

`INPUT_RESTORATION_RECEIPT.json` retains all 18 original source file checks and the authenticated previous evidence restoration. Search reproduction would require the separately retained complete Burst4 result archive; this diagnostic's included exact prior pins and external nine source compacts suffice for its declared computation. New matrix capsules support local auditing and do not replace full-source row identity verification.

## Runtime, resource limits and identities

Use a matching Python 3.12 environment with NumPy 2.3.5, SciPy 1.17.0, h5py 3.15.1, hdf5plugin 7.1.0 and Matplotlib 3.10.8; actual terminal receipts record the executed versions. Trusted decoder wheels are retained with the previous Burst4 package. This source-only ZIP is not a complete runtime image. The original setup used offline installation and `PYTHONPATH=analysis/deps`. Numerical drivers limit BLAS/OpenMP threads to one.

Every new code/document and prior evidence dependency is bound by the scope's `text_code_pins` and `prior_data_pins`. The package manifest preserves the scope's scientific/resource dictionary keys without renaming them. Diagnostic jobs are bounded at 600 CPU seconds, 900 wall seconds and 2 GiB address space each; at most two run together, with 4 GiB aggregate memory. Output caps are 50 MiB per target and 150 MiB for all three. Independent QA and report processes each have 600 CPU/900 wall/2 GiB caps; QA output is at most 4 MiB. Read actual scope, GO and resource ledger caps before any run. New stage accounting preserves earlier reservations and failures without refund; it is not a reset of historic A/B or a subscription-usage measurement. Workspace remains bounded at 8 GiB and the new ZIP at 100 MiB. Source recovery bytes are accounted separately; new telescope requests and cost are zero.

## Fresh reproduction

Use a separate fresh directory. Preserve the delivered completed tree, all prior outputs and failures elsewhere. Copy the exact new code and declared prior pins from the ZIP, then restore the nine original OFF compacts. Keep historical public freeze/admission evidence as provenance. Leave new job result directories, QA receipt/output destinations and `delivery/` absent. Review copied inputs and actual hashes before admitting each once-only phase.

Do not recreate or overwrite an existing scope. Metadata/check-only commands read only the declared metadata and saved JSON. Run each new diagnostic job once with the driver's explicit execution flag, exact scope/code/GO pins and reviewed root admission. Preserve every terminal receipt. After all three jobs are COMPLETE, run independent QA once against their actual fresh receipt hashes and the fixed QA code. Generate and visually verify the saved-JSON report only after PASS. Executable argument parsers and included GO records provide the exact current admission schema; newly generated evidence requires newly measured pins. Reproduction is not blind validation.

After complete QA-gated results, root may create the archive once:

```bash
python analysis/burst_order_20261011/build_delivery.py --root . --build \
  --scope-sha256 <actual-frozen-scope-SHA256> \
  --script-sha256 <actual-frozen-build_delivery.py-SHA256>
```

Angle-bracket values are actual-hash placeholders, not executable values. Omitting `--build` performs completed-evidence readiness and byte-pin checks only; it writes no archive and decodes no arrays.

## Byte verification and publication

The archive includes `RESULT_PACKAGE_MANIFEST.json` with exact bytes/SHA256 for every payload member, original-key scientific/resource scope contract, external raw archive identities and exact external compact pins. Creation checks every ZIP CRC, member size and SHA256, the embedded manifest bytes, and unchanged snapshot pins. `BURST_ORDER_ARCHIVE_RECEIPT.json` is an immutable external receipt with archive and manifest SHA256, member count and measured package CPU/wall/RSS. These are delivery-integrity checks, not scientific qualification.

`BURST_ORDER_PUBLICATION_FILE_PLAN.json` separately lists exact source/evidence text, CSV and PNG identities and Git blob SHA values. Numerical NPZ capsules remain in the complete ZIP. The script makes no network or Git call. Bytecode, lock files and logs are omitted; durable JSON admissions, terminal failures and reviews remain included.

ZIP, receipt and publication-plan destinations are exclusive-create. Failures preserve partial bytes and an immutable failure receipt. Do not overwrite, delete, silently rerun or resume inside a failed namespace. A reviewed correction uses a separate prospective destination and retains the original history.
