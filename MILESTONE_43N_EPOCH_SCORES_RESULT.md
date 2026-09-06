# M43N — all additional-epoch native and integrated scores pass

All **40,703,868,576 prescribed integrated score cells** exactly match the
separately constructed factorized reference on the four M43M telescope
sources: epoch2_on, epoch2_off, epoch3_on and epoch3_off at **1412.5 MHz**.
Every source covers all **1,701 templates × 747,793 support carriers × eight
native filter widths**. All **1,728 batches / 54,432 full vectors** pass.
The complete valid native-filter domain also passes direct comparison:
**579,705,984 native values in 512 row/width checks**.

| Native width | Compared native values, four sources | Batches | Compared integrated cells | Reference |
| --- | --- | --- | --- | --- |
| 1 | 72,465,280 | 216 | 5,087,983,572 | Exact |
| 3 | 72,465,152 | 216 | 5,087,983,572 | Exact |
| 5 | 72,465,024 | 216 | 5,087,983,572 | Exact |
| 9 | 72,464,768 | 216 | 5,087,983,572 | Exact |
| 17 | 72,464,256 | 216 | 5,087,983,572 | Exact |
| 33 | 72,463,232 | 216 | 5,087,983,572 | Exact |
| 65 | 72,461,184 | 216 | 5,087,983,572 | Exact |
| 129 | 72,457,088 | 216 | 5,087,983,572 | Exact |
| **Total** | **579,705,984** | **1,728** | **40,703,868,576** | **Exact** |

Together with M43J/L's unchanged first-pair results, exhaustive numerical
integrated coverage now includes **all six sources at all eight widths**:
**61,055,802,864 compared cells across the three milestones**. All grids include
747,665 score carriers and 64 support guards per side. The three ON/OFF pairs
are repeated scans in one observing sequence, not independent dates. These
are correlated numerical comparison counts, not independent trials, sky
candidates or measured sensitivity. No multi-epoch stack has yet been qualified.

## Numerical checks and provenance

The production path is the unchanged M43I telescope adapter: receipt-bound
source loading, native filtering, nearest-even binary64 affine mapping and
ascending-row float32 integration. The reference is unchanged M43L code,
which builds native filters from explicitly indexed channel windows and gathers
using absolute native positions. It shares the intended formula, NumPy runtime
and factors with production, while using separate indexing and array storage.
This is numerical cross-validation rather than independent scientific replication.

Before scoring, every valid native reference value is compared directly to the
production cache, including dtype; row and full payload hashes must also agree.
The M43K monotonic endpoint bound verifies that all bank mappings fit within the
audited native domain. Each 32-template batch compares every support carrier,
in 4,096-carrier chunks. The final batch has five templates. Cache identity binds
the telescope receipt, normalized payload, bank, scan factors, grid and width.
Every completed checkpoint includes 16 native row hashes and all 54 batch digests.

The public freeze `3602b0be51e7f98f508243ea46869846cd6db528` preceded numerical evaluation on these
new inputs. Source receipts come from the retained M43M result
`bce9b6c487c0af46c33669c30132135df83a9d048d45188d5aa24758757fb840`. There are no old M43I/K score digests for these four
sources; M43N establishes their first exhaustive numerical anchors and makes
no invented overlap claim. The final audit rehydrates all four sources against
those retained receipt hashes, checks every cache identity and row count,
recomputes geometric bounds, validates all ordered batch inventories and
verifies the exact 32 completed source/width products.

All **81 M43-family tests pass**. Three new tests check all eight widths against
the original direct-window oracle on small mocked-provenance fixtures, reject
native scope/interior/digest corruption, and reject missing, duplicate or
reordered source/width inventories. These fixtures are not telescope evidence.
The additional real seven-child runtime probe verifies file-based cooperative
stops without loading telescope sources or evaluating scores.

## Execution and retained evidence

At most seven ordinary numerical subprocesses ran concurrently under the
available eight-CPU/20-GiB environment. Source/width jobs were scheduled in
descending width order and frozen source order. Each job retained one source,
one native cache, one independent reference and one 32-template output batch.
The inherited 512-MiB adapter limit excludes caller/reference/process/OS memory;
it is not a combined-job RSS measurement. No AI agents or delegation were used.
Successful wall time was **1720.759 seconds**, including source
rehydration and reference work; this is not calibrated detector throughput.

No new remote requests or telescope downloads were needed. No run failure
occurred. Native and batch checkpoints were sealed atomically, and completion
required every prescribed batch. The runner would stop peers at their next
batch boundary on an error and reject a partial inventory. It recomputes on a
rerun rather than accepting arbitrary self-sealed files as authority to skip
checks. Runtime and final enclosing seals can differ on reproduction; numerical
payload/batch/source/cache identities must reproduce. Large score matrices are
not retained; the complete batch digests, source/width checkpoints and audit are
published with a SHA-256 manifest. The first seven completed products were
publicly checkpointed during the run in commit
`c0707c545fe7d380efa057044ee5ccffcf2fa4b8`. All 28 wider-width products were
public by `461bd9e94da0967e9b5268fcad10be53d7ba8d1b`, while the final
width-one comparisons continued.

## Reproduction and next gate

- Configuration SHA-256: `041cf5d7574f45e866e31738b22c9113051c7a8f23cd6665b2e5b7815286be29`.
- Sealed M43N result: `53f45868f51b2f4b7dacafc438569d2dd095f193fa1a722aac525b79f0ea47ec`.
- Bank SHA-256: `84524f7e129c0b414bde5004fe64bfb3ff94877357a7bb4dce399562d945d873`.
- Factor table SHA-256: `bc5c9e1f7a2db63074be30a946b2e1bd68963966f6c6b11cc5ad30f4e173edcd`.
- Support grid SHA-256: `18739188d199ffeaf1854911efc590c2cb2c5a0817704ed7f9f9bb86358c6429`.
- NumPy: `2.3.5`.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43n_epoch_scores.py --work-root /path/to/m43h_work/live --freeze-commit 3602b0be51e7f98f508243ea46869846cd6db528
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43n_result_report.py --work-root /path/to/m43h_work/live
sha256sum -c RESULTS_MANIFEST_M43N_EPOCH_SCORES.sha256
```

The next gate is the real multi-epoch stack and detection logic, followed by
separately frozen null and injection/recovery calibration. M43N does not select
candidates, estimate recovery, calibrate thresholds or establish a scientific
nondetection. It supplies the fully checked per-epoch score foundation needed
for that next stage.
