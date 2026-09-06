# M43G: synthetic numerical transfer qualification

**The separately frozen numerical adapter passes every prescribed synthetic comparison.**

The separately named adapter normalizes and natively filters full-size synthetic sources, then gathers the fixed M43E tracks using the wider M43F geometries and repeat-permitting channel mapping. The legacy M37 source factory and detector remain unchanged. This closes the numerical prerequisite; it does not attest a widened telescope source or validate detection sensitivity.

## Integrity failure and public repair

The initial freeze `0165b67ec77992ac291d7d49914165dc24bec574` failed an additional adversarial fixture: an immutable float32 cache reinterpreted as uint32 retained the same byte hash but produced incorrect scores. The initial full-size run was interrupted. Its sealed counterexample and partial progress log remain published. Version 2 checks dtype, shape and layout and revalidates source metadata/payload before use. Its regression test covers same-byte reinterpretation/reshaping and altered source geometry. The amended contract was public before the completed rerun; all seeds and numerical selections stayed fixed. This is an implementation repair, not a passed initial gate or independent fresh confirmation.

## What was checked

| Comparison | Exact scope | Result |
|---|---|---|
| Normalization vs independent sorted median/MAD | 30 full-size synthetic scan/window sources; 480 complete integration rows | Bit-for-bit equal |
| Native filtering and integration vs direct per-center native windows | All 1,701 templates, 30 scan/window pairs, 8 widths, 53 prescribed carrier cells each | 21,636,720 score cells equal |
| Complete support-grid comparison | 1412.5 MHz, all 6 scans, widths 1 and 129, minimum- and maximum-factor templates | 24 vectors / 17,947,032 score cells equal |
| Gather chunk invariance and local/full agreement | Same complete vectors; chunks 4096 and 32768; common local slices | Bit-for-bit equal |
| ON/OFF epoch-stack arithmetic and active >=3 cut | All windows/widths, 4 activity subsets, all templates, 51 common diagnostic carriers | 320 vectors / 27,760,320 cells equal |

All 44 M43-family development tests pass, including 11 new adapter tests. These cover nearest-even ties, repeat preservation, chunk boundaries/halos, terminal normalization blocks, archive orientation, legacy injective-domain agreement, altered identities/payloads and fail-closed input, coverage and capacity checks. No full repository test run is claimed.

The local carrier selection is fixed: 17 at each support end, 17 at its center, and the 2 carriers in each previously published M43F collision witness. The full-grid templates are selected by the first minimum and maximum in each fixed scan factor matrix. They are diagnostic extremes, not random or independent signal trials. The complete grid is exhausted only for those selected templates, one window and two widths. The 1,701-template bank is checked locally across all windows/widths; this is not a full-bank exhaustive search.

## Numerical and source changes

Descending input rows reverse before normalization. Every 4096-channel normalization block starts from the ascending zero of the new, wider extraction. Native filters retain their full windows across filter chunks. Nearest-even mapping permits steps 0, 1 and 2 while preserving every proxy carrier. Integration uses the original ascending row order and float32 arithmetic. No deduplication, interpolation, carrier exclusion or repeat reweighting is applied.

The new source and cache identities bind the numerical contract, extraction geometry/scope, raw and normalized synthetic payloads, bank, factors, grid and filtered payload. Payloads are immutable and changed metadata/payloads are rejected. The adapter accepts only explicitly synthetic source scope; a hash does not convert synthetic data or an arbitrary row callback into attested telescope data.

The conservative adapter-owned ndarray bound for one source plus a width cache is 314.09–315.92 MiB before the separately checked gather output/mapping allowance, below the new 512 MiB cap. This is static allocation accounting, not a measured process-RSS ceiling. It excludes caller-held matrices/previous caches, transport and OS caches. Production transport needs separate accounting and validation.

## Interpretation and next step

The oracle uses full sorting for normalization and independently constructs each requested native filter window for scores. It shares the fixed mathematics, input factors and NumPy arithmetic with the adapter, so this is numerical cross-checking, not an independent scientific replication. Synthetic Gaussian arrays are arithmetic fixtures, not a validated null model. The active-epoch cut in the stack comparison is an arithmetic exercise; it is not a newly calibrated detection threshold.

Repeated native channels introduce correlations that must remain in later null calibration. No telescope spectra were read, no recovery rate was measured, no old threshold was transferred and no technosignature inference follows. M43E remains a geometric qualification; M43F remains the published incompatibility of the old adapter.

Next: implement and qualify the separately attested widened telescope extractor/source factory, including remote identity, exact extraction ancestry, new normalization scope, restartable payloads and bounded transport memory. Then run predetermined exhaustive real-data anchors and renewed null calibration before interpreting new-bank detections.

## Reproduction and audit

Public freeze: `3d3123b5ae1c1ed861b93c8f55a0b08c204bd29b`, verified before the full-size synthetic evaluation. Result identity: `a8724c7efcce6a51a09d2b8f69e8a8b339f54119cf88ca98fea335012aedb849`. Numerical contract: `89b89cd739808a39a88e4e5228b56f67f5663c55fccff8e60e2a1de7b36abe68`. The manifest identifies the plan, configuration, implementation, oracle, tests and derived results.

The primary executable requires exact equality and aborts at the first discrepancy. Its sealed inventories record every source, width and full-grid/stack comparison. The separate result audit rechecks pinned inputs, bank/factor ancestry, complete inventory coverage, extremum-template selection, memory bounds and denominators. It does not rerun all numerical comparisons or claim a second full numerical replay.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p 'test_m43*.py' -q
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43g_synthetic_qualification.py
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43g_result_report.py
```
