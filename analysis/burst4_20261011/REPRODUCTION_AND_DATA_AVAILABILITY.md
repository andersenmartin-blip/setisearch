# Four-row Burst4 pilot: reproduction and data availability

This prospective document describes the method and exact input availability. Completion is established by terminal production receipts and two independent numerical QA receipts in the delivered result package. This document and static reviews do not assert a numerical result or a QA success before execution.

## Search family and interpretation

The primary targets are `epoch1_off` / HIP97319, `epoch2_off` / HIP97461 and `epoch3_off` / HIP97663 from the original 2017-04-28 observation. Each star has one scan in this family. Original OFF acquisition labels are retained. The other original scans point to HIP98505; they are fixed descriptive context and are not further visits to an OFF-primary star.

The pilot samples native170, native171 and native172 at 32 fixed cores per native: `q = 4 + 8*k`, `k = 0..31`. Thus it has 96 cores per target and 288 combined maps, with 4,096 carrier records per map. A 4,000-channel halo on each side supports unchanged preprocessing and drift rounding. Each native contains 1,048,576 source channels.

| Native | Absolute source channels, half-open |
|---|---|
| 170 | [178257920, 179306496) |
| 171 | [179306496, 180355072) |
| 172 | [180355072, 181403648) |

There are seven overlapping four-row windows starting at rows 0, 2, 4, 6, 8, 10 and 12. A window contains 73.014444032 seconds of integration; its first-to-last midpoint span is 54.760833024 seconds. Each candidate uses its own window's first integration midpoint as its reference epoch. The 159-point drift grid spans −4 to +4 Hz/s and has exact zero at index 79. Widths are one and three channels. The half-grid endpoint displacement is bounded by about half a source channel over the four-row midpoint span.

Full sixteen-row preprocessing runs once per core using the unchanged detector: row power medians, 501-channel running medians, full-core residual MAD scales and winsorized locations. The new score sums the selected four standardized width-box terms and divides by `sqrt(4*width)`. This is a new duration/window hypothesis family in previously exposed historical observations. It does not add observed bandwidth or telescope exposure.

One combined maximum is retained for each carrier over all seven windows, two widths and 159 drifts: 2,226 correlated hypotheses per carrier, 1,179,648 retained carrier maxima and 2,625,896,448 scored hypotheses in total. These are not independent trials. Winning ties use ascending window start, width one before three and ascending drift index, with strict-greater updates. Target-global TOP20 pools all 96 cores, sorts by descending score then ascending absolute carrier channel, and greedily retains carrier separation greater than three channels. TOP3 is the first three entries.

The fixed core geometry omits the known q128 stationary-line cores. This is stated openly; the observations have already been examined. The producer applies no signal mask, geometric veto, injection, data-selected exclusion or protected 2016 data opening. Scores are empirical robust box-track scores, not calibrated SNR, false-alarm probabilities, flux or sensitivity. Maxima from this seven-window family are not significance-calibrated comparisons to the previous sixteen-row family.

## Fixed follow-up and independent checks

The nine target-global TOP3 tuples are followed without refitting in all six original scans, for 54 profiles. Each retains its carrier, drift, width, winning local row indices, reference MJD and normalization core. Real scan starts and gaps determine the absolute rounded channels. Both the same local four-row score and a separately normalized sixteen-row descriptive score are saved. The own-primary four-row score must match the search result; the sixteen-row score is a different quantity.

Other stars' scores are descriptive context. The four-row grid's cadence extrapolation is coarser than a full-cadence search and cannot prove absence or origin in another scan. Neither cross-pointing arithmetic nor a common-frequency feature alone establishes a physical interference mechanism or extraterrestrial origin.

Primary outputs retain every combined carrier maximum, winning window/drift/width, and valid hypothesis count. There are 96 compact full-sixteen-row normalization records per target and 387 raw503 queries per target: first, midpoint, last and maximum carrier in every core plus the three global selections. Each query retains its exact four absolute row indices and a 4×503 float32 raw capsule.

Independent primary QA checks map geometry, saved winners, pooled ranking, source file and decoded-row identities, raw-core row power medians, and all 1,161 local501 four-row score queries. The local501 score reconstruction is conditional on the saved authenticated full-core MAD/location parameters; it does not independently refilter all full cores or remaximize every drift/window hypothesis. Context QA independently checks all source identities, timestamps, absolute rounding, raw503 row terms, four-row and sixteen-row arithmetic, and the nine own-primary matches. Exact limitations and tolerances are recorded in the frozen QA code and receipts.

## External raw observations

The result ZIP excludes the 18 full compact HDF5 sources. Restore their original bytes from the previously retained canonical raw packages; equivalent repacked arrays do not satisfy whole-file pins.

| Canonical package | Bytes | SHA256 |
|---|---:|---|
| `SETI_S2017_NATIVE171_RAW_2026-10-10.zip` | 466351822 | `6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786` |
| `SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip` | 604399781 | `b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f` |

The second archive is stored as three ordered parts. Concatenate `.zip.part01`, `.zip.part02` and `.zip.part03` in that order, check the full archive hash, then extract.

| Part | Bytes | SHA256 |
|---|---:|---|
| 01 | 209715200 | `ad4be599d3e7da809df1d473c8fa677e0c2581d251fb65d9cc01d90849dd8dbb` |
| 02 | 209715200 | `2ad6609f4984c536fc4dbee2223975f756459d681b8c9e1f5c6b8731f149a97f` |
| 03 | 184969381 | `d585965102de3ac3cbc9864a92249e0fb660ed6968540249c34e650b880b15ca` |

Restore the six native171 files to `analysis/new_visit_recovery/results/acquire/<scan_id>.compact.h5` and twelve native170/native172 files to `analysis/s2017_next_native/results/acquire/native<native>_<scan_id>.compact.h5`. The scan IDs are `epoch1_on`, `epoch1_off`, `epoch2_on`, `epoch2_off`, `epoch3_on` and `epoch3_off`.

Included source manifests and acquisition receipts pin all exact compact files and all 288 decoded float32 rows. `analysis/RESTORATION_RECEIPT_20261011.json` preserves the original restoration identity and an initial assembly correction. Raw503 result capsules support local audits but do not replace full compacts for reproduction or independent full decoded-row checks.

## Runtime, identities and resources

The original runtime uses Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, h5py 3.15.1, hdf5plugin 7.1.0, HDF5 1.14.6 and Matplotlib 3.10.8. Actual numerical receipts are authoritative for versions. The archive includes retained h5py and hdf5plugin decoder wheels, not a complete operating environment. Installation in the original session was offline with `--no-index`; the local dependency directory was exposed with `PYTHONPATH=analysis/deps`. Numerical executables limit BLAS/OpenMP threads to one.

The primary `scope.json` contains exact byte counts and SHA256s for source metadata, original completed dependencies and all frozen producer/QA/context/report/package code. Each phase has public freeze/admission provenance and root GO records. The unchanged detector has SHA256 `1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45`; the standard reader has SHA256 `329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0`. New file identities are read from the delivered scope and result-package manifest, avoiding a circular self-hash in this document.

Primary limits are 600 CPU seconds, 900 wall seconds, 2 GiB process address space, 50 MiB output per target, at most two simultaneous jobs and 4 GiB aggregate primary memory. The complete primary output cap is 150 MiB and the project workspace cap is 8 GiB. QA/context limits and execution counts are frozen in their code/scopes/GO records and measured in terminal receipts. The delivery ZIP has a strict 200 MiB cap. No paid service or new telescope request is part of this workflow; cost is 0 DKK.

## Fresh reproduction sequence

Reproduction is optional future work in a separate fresh project directory, not execution in the delivered completed namespace and not another blind first opening. Preserve all original outputs, terminal receipts and failures. Copy the exact frozen code and metadata pins, including prior completed adjacent-search receipts needed by the scope contract, then restore the external original raw bytes at the paths above.

Keep historical byte-pinned admission provenance, but leave new-phase output destinations absent: primary `results/`, QA `results/`, context `results/`, context `delivery/`, generated context `context_scope.json`, and generated QA/context GO/QA receipt destinations. Review each phase's actual executable CLI and its frozen GO schema before a once-only run. Newly generated result receipts require newly measured pins; do not substitute the original execution receipts into future admission.

From the fresh project root, use a matching runtime and optional offline dependency path:

```bash
export PYTHONPATH="$PWD/analysis/deps${PYTHONPATH:+:$PYTHONPATH}"
python analysis/burst4_20261011/driver.py --root . \
  --job primary20170428_HIP97319 --check-only
```

The metadata-only check reads no source arrays. Do not rerun a create-only scope preparer over an existing scope. Execute the three primaries once, sequentially or within the two-job cap, with explicit `--run`, the exact delivered `--scope-sha256`, and a reviewed compatible GO record at its actual `--root-go-sha256`. Each primary must terminate COMPLETE before primary numerical QA. QA receives the actual fresh primary receipt pins and its own reviewed GO. After PASS, prepare and pin a fresh context scope from the fresh target-global TOP3 outputs, review and admit it, then run the fixed 54 contexts once. Run independent context QA after COMPLETE. Generate and visually verify the report only after both QA receipts pass. Each executable's argument parser and included admission records supply the precise current schema.

Finally, root may archive completed evidence once:

```bash
python analysis/burst4_20261011/build_delivery.py --root . --build \
  --scope-sha256 <actual-primary-scope-SHA256> \
  --script-sha256 <actual-frozen-build_delivery.py-SHA256>
```

Angle-bracket values are placeholders for actual verified hashes, not executable values. Omitting `--build` performs only completed-evidence readiness and byte-pin checks. It does not create an archive or read numerical arrays.

## Delivery integrity and publication

The ZIP includes the three new phase trees, exact text/code input pins, original source manifests/acquisition/restoration records, decoder wheels, all maps/normalizations/raw503 capsules, complete numerical receipts, report figures and tabular summaries. Prior huge map trees and full compact observations remain external. Cache bytecode and lock files are omitted; useful logs and provenance records are retained.

`RESULT_PACKAGE_MANIFEST.json` records every payload member's exact bytes and SHA256. Archive creation verifies every ZIP CRC, every member's size/SHA256, the embedded manifest bytes, and unchanged source snapshot pins. The external immutable `BURST4_ARCHIVE_RECEIPT.json` records the archive SHA256, manifest SHA256, member count and measured resource use. ZIP integrity checks establish byte delivery, not scientific qualification.

`BURST4_PUBLICATION_FILE_PLAN.json` is a separate metadata-only list of reviewable text/CSV/PNG files and exact Git blob identities. The packager performs no Git or network operation. The complete numerical NPZ outputs and decoder wheels stay in the evidence ZIP. Public repository publication is a separately reviewed root operation.

Every archive, receipt and publication-plan destination is create-only. A failure leaves partial bytes and an immutable failure receipt. Do not overwrite, delete, resume inside the failed namespace or silently rerun; any reviewed correction uses a separate new destination with its own preserved history.
