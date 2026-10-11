# Original OFF adjacent-band search: reproduction and data availability

This document describes the frozen method and its inputs. Completion and numerical QA are established by the terminal receipts in the delivered package, not by this README, static reviews, or publication records. No final QA success is asserted here.

## Search domain and interpretation

The primaries are `epoch1_off` / HIP97319, `epoch2_off` / HIP97461, and `epoch3_off` / HIP97663, from the historical 2017-04-28 observation. Original acquisition roles remain OFF. Each star has one scan in this family.

Each primary searches exactly 512 new reference cores: native170 q1–255, native171 q0 and q255, and native172 q0–254. Each core contains 4,096 carriers, has a contiguous 4,000-channel halo on each side, and searches 785 drifts from −4 to +4 Hz/s with widths 1 and 3. Native chunks contain 1,048,576 channels each:

| Native | Absolute source channels, half-open |
|---|---|
| 170 | [178257920, 179306496) |
| 171 | [179306496, 180355072) |
| 172 | [180355072, 181403648) |

The reference epoch is each primary's own first integration midpoint. The unchanged detector rounds the complete absolute carrier-plus-drift mapping with `np.rint` before subtracting a crop offset. It normalizes on all 4,096 declared core channels with float64 median/MAD/winsorized-location arithmetic. There are no masks or data-selected exclusions.

All 4,096 carrier maxima are retained in every map. One TOP20 is selected per target from all 512 cores by descending score, then ascending absolute channel, using greedy carrier distance strictly greater than three channels. TOP3 is the first three entries of that target-global TOP20. There are 1,536 maps, 6,291,456 carrier maxima and 9,877,585,920 correlated drift/width hypothesis records; these are not independent tests.

The 54 later profiles follow the nine fixed TOP3 tuples in all six original pointings, retaining the selected carrier, drift, width, reference epoch and normalization core. Actual scan starts and gaps are used. Other pointings are descriptive context, not independent repeated visits to an OFF-primary star. Reference2300 line diagnostics describe rounded-channel geometry and positive-row contribution arithmetic; they do not establish an interference mechanism.

Scores are empirical robust box-track scores, not calibrated SNR, false-alarm probabilities, flux or sensitivity. No OFF veto, sky-origin qualification, new observing visit, or independent blind replication is claimed. Original A/B failures remain unchanged.

## External raw data

The final result archive does not duplicate the 18 full compact HDF5 sources. Their exact bytes come from previously retained canonical raw packages:

| Canonical package | Bytes | SHA256 |
|---|---:|---|
| `SETI_S2017_NATIVE171_RAW_2026-10-10.zip` | 466351822 | `6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786` |
| `SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip` | 604399781 | `b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f` |

The second package was retained as three ordered parts. Concatenate `.zip.part01`, `.zip.part02`, and `.zip.part03` in that order and verify the complete archive hash before extracting:

| Part | Bytes | SHA256 |
|---|---:|---|
| 01 | 209715200 | `ad4be599d3e7da809df1d473c8fa677e0c2581d251fb65d9cc01d90849dd8dbb` |
| 02 | 209715200 | `2ad6609f4984c536fc4dbee2223975f756459d681b8c9e1f5c6b8731f149a97f` |
| 03 | 184969381 | `d585965102de3ac3cbc9864a92249e0fb660ed6968540249c34e650b880b15ca` |

Restore six native171 compact files to `analysis/new_visit_recovery/results/acquire/<scan_id>.compact.h5`, and twelve native170/native172 compacts to `analysis/s2017_next_native/results/acquire/native<native>_<scan_id>.compact.h5`. Each scan ID is one of `epoch1_on`, `epoch1_off`, `epoch2_on`, `epoch2_off`, `epoch3_on`, `epoch3_off`.

Restore original compact bytes instead of repacking equivalent HDF5 arrays: whole-file identity is required. Original acquisition JSONs contain every compact SHA256 and all 288 decoded float32 row SHA256s. `analysis/RESTORATION_RECEIPT_20261011.json` records the 18 restored identities and archive hashes; its SHA256 is `14780c7e48e4ce1335e3dd337553d4c7dd5b72e777514008f88c2046141bae33`. It preserves an initial assembly mistake and correction before source extraction or scientific execution.

No new telescope request or paid service is required. Result raw503 capsules support local audits but do not replace the full-source compacts needed for search reproduction and decoded-row checks.

## Runtime and frozen identities

Runtime: Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, h5py 3.15.1, hdf5plugin 7.1.0 and HDF5 1.14.6. Numerical receipts record actual versions. Use a matching installed environment or previously supplied trusted wheels; this workflow used offline `--no-index` installation. Dependencies may be exposed through `PYTHONPATH=analysis/deps`. Numerical tools set BLAS/OpenMP thread counts to one.

| File | SHA256 |
|---|---|
| `analysis/off_adjacent_20261011/driver.py` | `64a1e962c7db15973340fcfb8ba2da1c1c2e5ce0b2bf73585dd0e3a343e74b02` |
| `analysis/off_adjacent_20261011/prepare_scope.py` | `60f8e277a0cffbb65deb53345aa277741cfc66d131df3e009f5ed4ae812abe91` |
| `analysis/off_adjacent_20261011/scope.json` | `b5a026ce05477d32633539d3c144aad2b44ac60dee211d34bbec139b2afaa54e` |
| `analysis/off_adjacent_20261011_qa/qa_saved.py` | `4af6828f03f9b307766e3ec5fb4bdc56ba5e011d1fb75c36330645543353b770` |
| `analysis/off_adjacent_20261011_context/context_profiles.py` | `e4124488f366bff9089de067210cc16bcd9169b7d16a95f29adf3ff0fe4b9e76` |
| `analysis/off_adjacent_20261011_context/qa_context.py` | `8946737258574857ff09b3fb6866ffe8e5cc48ab7a4a99642b5ea17df38ce842` |
| `analysis/off_adjacent_20261011_context/make_report.py` | `3462e2dddf2a8d5d5ae6dba6bd4781cbc39ac1ee28459d846be52d55aa418baf` |
| `analysis/new_visit_search/dependencies/detector.py` | `1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45` |
| `analysis/new_visit_search/dependencies/standard_reader.py` | `329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0` |

Primary code/scope public readback commit: `27cfd5c5d4fb6497f8fccb9e47a206a84b2f43c3`. Independent primary QA/context/report code commit: `2fd1d7b7b08bdcfeeab4f4a4ec4103b09013b2cd`. Revised context QA freeze/readback commit: `124392eb1c037db7043dab42b970c3026ba5f539`. These identify code/provenance, not numerical results.

## Resource limits

| Phase | CPU seconds | Wall seconds | Process RAM bound | Concurrency / output |
|---|---:|---:|---:|---|
| Primary, per target | 1800 | 1800 | 2 GiB | At most two jobs / 4 GiB aggregate; 200 MiB per job / 600 MiB total output |
| Independent primary QA | 1800 | 1800 | 3 GiB | Exclusive primary slot locks; 8 MiB QA output |
| Fixed context production | 300 | 600 | 2 GiB | One process |
| Independent context QA | 300 | 600 | 2 GiB | One process; small JSON receipt |

RAM is bounded by process address space; receipts also record peak RSS. Primary CPU limits were frozen before maps: earlier complete 251-map target receipts used about 479–483 CPU seconds, giving a 512-core linear projection of about 985 seconds before conservative triplet verification overhead.

## Fresh reproduction sequence

Create a separate fresh project directory. Do not execute this recipe in the delivered completed tree. Copy frozen code, original scientific metadata, every file in the primary scope's `text_code_pins`, and public admission/provenance records. Restore the external sources at the relative paths above. Keep historical receipts, including prior native171 251-map target receipts required by the scope: they are dependencies, not reproduction output destinations.

Exclude the new primary `results/`, primary-QA `results/`, context `results/`, context `delivery/`, generated `context_scope.json`, generated context `ROOT_GO.json`, primary-QA `ROOT_GO.json`, and `CONTEXT_QA_RECEIPT.json` from the fresh destinations. Preserve delivered outputs elsewhere. Retain original primary `ROOT_GO.json` / `PUBLIC_FREEZE.json` as byte-pinned historical admission provenance. Review restored exact inputs before executing each phase once. A reproduction is not another blind first opening.

Run from the fresh project root. For an offline dependency directory:

```bash
export PYTHONPATH="$PWD/analysis/deps${PYTHONPATH:+:$PYTHONPATH}"
```

1. Validate the delivered primary scope without opening numerical arrays. Do not rerun the create-only preparer over an existing scope.

```bash
python analysis/off_adjacent_20261011/driver.py --root . \
  --job primary20170428_HIP97319 --check-only
```

2. Execute every primary exactly once. Sequential execution respects the two-job cap; optional parallel execution must retain that cap.

```bash
for SETI_JOB in primary20170428_HIP97319 primary20170428_HIP97461 primary20170428_HIP97663
do
  python analysis/off_adjacent_20261011/driver.py --root . --job "$SETI_JOB" --run \
    --scope-sha256 b5a026ce05477d32633539d3c144aad2b44ac60dee211d34bbec139b2afaa54e
done
```

3. After all three new receipts are COMPLETE, create fresh primary-QA `ROOT_GO.json` using the exact contract in `analysis/off_adjacent_20261011_qa/README.md`. Use newly generated receipt hashes, frozen code/scope hashes above, actual byte pins of copied primary admission records, and documented caps. Then execute:

```bash
python analysis/off_adjacent_20261011_qa/qa_saved.py --root . \
  --scope-sha256 b5a026ce05477d32633539d3c144aad2b44ac60dee211d34bbec139b2afaa54e \
  --qa-sha256 4af6828f03f9b307766e3ec5fb4bdc56ba5e011d1fb75c36330645543353b770 \
  --root-go-sha256 <fresh-QA-ROOT_GO-SHA256> \
  --primary-receipt primary20170428_HIP97319=<fresh-receipt-SHA256> \
  --primary-receipt primary20170428_HIP97461=<fresh-receipt-SHA256> \
  --primary-receipt primary20170428_HIP97663=<fresh-receipt-SHA256>
```

4. After independent primary QA passes, prepare a fresh context scope from actual new primary outputs:

```bash
python analysis/off_adjacent_20261011_context/context_profiles.py --root . --prepare \
  --producer-driver analysis/off_adjacent_20261011/driver.py \
  --producer-scope analysis/off_adjacent_20261011/scope.json \
  --primary-dirs analysis/off_adjacent_20261011/results/primary20170428_HIP97319 \
                 analysis/off_adjacent_20261011/results/primary20170428_HIP97461 \
                 analysis/off_adjacent_20261011/results/primary20170428_HIP97663
```

Review that scope. Create fresh context `ROOT_GO.json` with a status beginning with `GO` and `context_scope_sha256` equal to its actual SHA256. Run once:

```bash
python analysis/off_adjacent_20261011_context/context_profiles.py --root . \
  --scope-sha256 <fresh-context-scope-SHA256> \
  --root-go analysis/off_adjacent_20261011_context/ROOT_GO.json
```

5. After context execution is COMPLETE, run independent context QA once with the actual new context receipt hash:

```bash
python analysis/off_adjacent_20261011_context/qa_context.py --root . --run \
  --contextreceipt-sha <fresh-context-EXECUTION_RECEIPT-SHA256> \
  --qa-sha 8946737258574857ff09b3fb6866ffe8e5cc48ab7a4a99642b5ea17df38ce842
```

6. Check both fresh QA receipts for PASS before generating the report once in the absent `delivery/` directory:

```bash
python analysis/off_adjacent_20261011_context/make_report.py --root .
```

Angle-bracket placeholders require actual measured hashes and are not executable values. Metadata-only checks import no numerical modules or source arrays. These execution steps describe optional future reproduction, not a rerun of completed delivered science.

## Outputs and independent-check limits

Each primary output directory contains 512 map NPZs, 512 compact normalization JSONs, 2,051 raw503 capsules, `MAPS.json`, `SCORE_AUDITS.json`, `TOP20.json`, `TOP3.json`, and a terminal `EXECUTION_RECEIPT.json`. Four audit tuples per core are first/midpoint/last carrier and core maximum, plus three target-global TOP3 audits. Normalization JSON stores a contiguous channel interval and 16 values per parameter field, not a repeated 4,096-channel list.

Independent primary QA checks all map shapes, precision, coordinates, valid counts, pooled ranking and source hashes. It independently recomputes raw-core row power medians and local501 arithmetic for 6,153 raw503 queries at absolute tolerance `1e-7` and relative tolerance `1e-10`. It does not independently refilter every full-core residual MAD and winsorized location: score audits are conditional on those saved authenticated parameters. It also does not independently remaximize every drift/width hypothesis.

Context output contains 54 capsules and normalizations, `CONTEXT_PROFILES.json`, and a terminal receipt. Independent context QA checks original bits/hashes, timestamp gaps and absolute rounding, 864 row-box sums, 54 scores, nine own-primary score/normalization matches, and contribution/overlap diagnostics. Local501 score arithmetic has the same conditional full-core MAD/location limitation. Zero-positive fractions and dominant row are null, not zero-valued measurements.

Production and QA destinations are create-only. Report generation creates a fresh delivery directory. Preserve partial files and failure/terminal records if any phase fails. Do not delete them, overwrite completed output, resume within its namespace, or silently rerun maps. A reviewed correction or later reproduction requires a separate fresh destination and its own receipts; historical outputs and failures remain preserved.
