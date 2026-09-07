# M43T neighbor9: paired isolation-mask comparison

The saved nine-bin support alternative produces **4 paired recovery gains and 0 losses** across 64 distinct nonzero injected inputs. Both policies were executed on every input under their own prospectively frozen calibration. The predeclared development gate is **passed**. General adoption remains unqualified; no astronomical candidate is claimed.

This is the `neighbor9` experiment on `m43-support-qualification`. The separate [M43T neighbor2 result](https://github.com/andersenmartin-blip/setisearch/blob/m43t-neighbor-mask/MILESTONE_43T_NEIGHBOR_MASK_RESULT.md) uses a different support radius and narrower signal-strength panel. Its original history is preserved. See [branch and continuation scope](MILESTONE_43T_BRANCH_SCOPE.md). The neighbor2 results were read after this saved plan was publicly frozen and before this numerical evaluation; no parameter was changed. Neither study is blind validation or a radius optimization study.

## Recovery and failure stages

Every row below has **eight truth endpoints per policy**. The three counts separate retention, passage through physical vetoes, and final rank-qualified recovery. Strength denotes added profile power, not measured recovered SNR.

| Profile | Added strength | Legacy retained / physical / recovered | Neighbor9 retained / physical / recovered |
|---|---:|---:|---:|
| ideal-native-bin | 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| ideal-native-bin | 6 | 1 / 1 / 1 | 1 / 1 / 1 |
| ideal-native-bin | 8 | 8 / 8 / 8 | 8 / 8 / 8 |
| ideal-native-bin | 12 | 8 / 8 / 8 | 8 / 8 / 8 |
| ideal-native-bin | 32 | 8 / 8 / 8 | 8 / 8 / 8 |
| fractional-off-template-smear | 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| fractional-off-template-smear | 6 | 0 / 0 / 0 | 0 / 0 / 0 |
| fractional-off-template-smear | 8 | 0 / 0 / 0 | 0 / 0 / 0 |
| fractional-off-template-smear | 12 | 4 / 4 / 4 | 4 / 4 / 4 |
| fractional-off-template-smear | 32 | 4 / 4 / 4 | 8 / 8 / 8 |

There are 160 endpoints: 128 nonzero endpoints from 64 input pairs and 32 explicitly reused zero-level endpoints from two unmodified-background executions. The baseline reuses are not independent noise trials. The ledger contains 2,271 compact nonzero-trial member decisions.

| Truth index | Profile | Strength | Change |
|---:|---|---:|---|
| 1 | fractional-off-template-smear | 32 | gain |
| 5 | fractional-off-template-smear | 32 | gain |
| 9 | fractional-off-template-smear | 32 | gain |
| 13 | fractional-off-template-smear | 32 | gain |

All four previously missed strongest combined-profile cases are shown explicitly:

| Previously missed truth | Legacy at 32 | Neighbor9 at 32 |
|---:|---|---|
| 1 | False | True |
| 5 | False | True |
| 9 | False | True |
| 13 | False | True |

Adjacent tested-strength recovery reversals: **legacy truth 9: 12 -> 32; legacy truth 13: 12 -> 32**. The original M43S results are unchanged. New legacy recovery differs from M43S at **0 shared endpoints**; the full difference list is in `result.json`.

## Calibration and development decision

| Policy | Training maximum (128) | Threshold | Held-out maximum (128) | Held-out >= threshold |
|---|---:|---:|---:|---:|
| legacy | 8.585220 | 10.000000 | 8.352145 | 0/128 |
| neighbor9 | 8.585220 | 10.000000 | 8.352145 | 0/128 |

Both thresholds were sealed before either held-out or injected evaluation. There are 256 unique new shift rows relative to M43R, with the same 128 training and 128 held-out rows used for both arms: 512 arm-specific maxima, not 512 independent realizations. The shift inventory also has zero overlap with the separate neighbor2 experiment. All shifts still use one observing sequence. Masks are formed on the unmodified full-support baseline, cropped, then co-rolled with scores; masks are not regenerated after scrambling. These conditional, correlated pre-veto maxima do not measure physical false-alarm probability.

All 74 cropped baseline masks are exactly zero in each policy: **True**. Consequently this background does not directly measure the change in rejection of strong interference. Equal or small held-out exceedance counts do not establish general interference safety.

The prospectively specified development conditions are:

- all four previous strong misses recovered: **True**.
- no additional heldout exceedances: **True**.
- no paired nonzero recovery losses: **True**.

These conditions permit broader validation only. The next useful programme is a jointly frozen signal-and-interference panel at additional carrier locations, separately varying fractional placement, template offset and smearing, followed by additional observing sequences. Keep both masks' physical dispositions and threshold exceedances visible. Do not tune this completed panel or interpret known-truth recovery as general completeness.

## Scope, restoration and reproducibility

The comparison uses 37 templates, 4,097 central score carriers (about 11.6 kHz), eight widths and four activity subsets in three ON/OFF pairs from one observing sequence. It is not a full 1,701-template search. Carrier position and anchor identity remain confounded, and the combined profile does not isolate its three effects. Association requires the exact activity subset and <=20 Hz maximum center-track error at every active ON integration, followed by unchanged physical vetoes and inclusive rank p <=0.01. No detector record cap was exhausted in the completed run.

The original scratch inputs were lost before continuation. Recovery verified all 576 published HTTP segments (2,742,987,099 accepted segment bytes in the historical indexes), then reproduced all six complete source receipt identities and all 96 full-support score-array hashes. That byte total describes the indexed historical segments; interrupted attempts and retries mean it is not total network traffic. Fresh recovery proofs and logs describe the completed download stages, while earlier interrupted attempts are retained separately. These were downloads of old observations, with no added observing coverage. The numerical experiment itself issued zero telescope requests after restoration.

The six focused tests passed in the restored runtime. Artifact validation checks all 241 pinned dependencies, result seals, 64 full sealed trial records, 160 endpoints, paired score/overlay identities, original input hashes, summary counts and threshold diagnostics. All 64 injected score inventories also exactly match their historical M43S counterparts. The grouped numerical run took **810.6 seconds**, excluding restoration. Python and NumPy remain 3.12.13 and 2.3.5, respectively; the qualified HDF5 source runtime is retained.

- Public freeze: `4f3c86de46a3920e595856fa7315560ff20723c3`.
- Configuration SHA-256: `0def57566cfe9a21d88e7d285e8f98e5832561a4f5f1809604ea585780d3f7d6`.
- Result seal: `7912db7457555c94dd44cbbdec090e9935551253959bdec16d6e39ef0afe27d7`.
- Compressed trial-ledger SHA-256: `e0e8678adb681715dc78809df31afea4f8a624c5617cf7442b4a415746b14bd1`.
- Uncompressed trial-ledger SHA-256: `5ccc3c4716b9231c96919124a0965b89f5b2d8aa314bc40763ab862cbec69e66`.
- [Frozen plan](MILESTONE_43T_MASK_COMPARISON_PLAN.md), [complete result](results_m43t_mask_comparison/result.json), [artifact validation](results_m43t_mask_comparison/artifact_validation.json), [numerical log](results_m43t_mask_comparison/live_run.log), and [complete lossless paired ledger](results_m43t_mask_comparison/paired_trial_audits.jsonl.gz).
- [Checksum manifest](RESULTS_MANIFEST_M43T_MASK_COMPARISON.sha256) covers the complete published package. Original M43R/S artifacts are retained intact.

With verified source and anchor roots available, use a clean output location at the public freeze, then run:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/m43t_mask_comparison.py \
  --freeze-commit 4f3c86de46a3920e595856fa7315560ff20723c3 \
  --anchor-root /path/to/anchors --source-root /path/to/sources \
  --checkpoint-root /path/to/paired-trial-checkpoints
```

Completed results are protected from overwrite. Restart checkpoints must match the public freeze, exact configuration, truths and both calibration bindings. Operational restoration helpers are published alongside their logs; they do not modify any frozen scientific dependency.
