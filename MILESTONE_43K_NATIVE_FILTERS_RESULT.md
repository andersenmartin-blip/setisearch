# M43K — every wider native-filter value matches

All **253,620,352 native filter values** match the separately accessed window
reference exactly. The complete valid native-channel domain is now checked for
widths 3,5,9,17,33,65,129, in every integration of both first-epoch ON/OFF telescope
sources at 1412.5 MHz. All 14 source/width checks and 224 row/width checks pass.

| Width in native channels | Valid centers per row | Values across both sources and all 32 rows | Reference |
| --- | --- | --- | --- |
| 3 | 1,132,268 | 36,232,576 | Exact |
| 5 | 1,132,266 | 36,232,512 | Exact |
| 9 | 1,132,262 | 36,232,384 | Exact |
| 17 | 1,132,254 | 36,232,128 | Exact |
| 33 | 1,132,238 | 36,231,616 | Exact |
| 65 | 1,132,206 | 36,230,592 | Exact |
| 129 | 1,132,142 | 36,228,544 | Exact |
| **Total** | — | **253,620,352** | **Exact** |

The separate oracle materializes integer-indexed channel windows in chunks of
2,048 centers. Production uses sliding-window views in chunks of 16,384 centers.
Both follow the frozen float32 sum, binary64 square-root divisor and float32
output rule. Every valid center, including first/last and processing boundaries,
is checked with zero tolerance. Each complete reference row digest equals the
corresponding native-cache row digest.

## Coverage and connection to previous results

All regenerated source/cache identities and payload digests equal M43I. The
full 1,701-template bank has positive finite factors, and the proxy carrier grid
is strictly increasing. Endpoint bounds under the fixed nearest-even binary64
mapping show that every interior native center lies in the audited domain at
every width, including repeated mappings. This is a monotonic coverage argument,
not an additional exhaustive integrated-score calculation.

Separately, **1,262,142 prescribed local integrated cells** reproduce M43I's
published digests exactly (1,701 templates × 53 carriers × 2 sources × 7 widths).
These checks also run the unchanged gather's source/cache integrity validation.
They reproduce earlier score evidence; they are not newly independent oracle
comparisons over the whole integrated-score domain.

| Evidence | What is exhaustive | Remaining scope limit |
| --- | --- | --- |
| M43J | All template/carrier integrated scores at width one on these two sources | One filter width, one epoch pair and one window |
| M43K | Every valid native filter value at all seven wider widths | Does not enumerate all wider integrated-score vectors |
| M43I | Full carrier grid for two selected templates at all eight widths; prescribed local carriers for the full bank | Wider integrated scores for other template/carrier combinations remain unenumerated |

These complementary checks reduce the untested numerical components. They do
not silently widen any earlier endpoint or assert that a complete calibrated
detector has passed. All three keep their original denominators and limitations.
The reference shares the formula and NumPy runtime with production, so exact
agreement is not independent scientific replication.

## Integrity, freeze and reproduction

All **72 M43-family tests pass**, including four new M43K tests. They exercise
all widths and two different oracle chunk sizes, production block halos, single
float32-ULP changes at edges and block boundaries, dtype/shape/row-order changes,
and the endpoint bound against every mapping in a small synthetic grid. The
unit inputs are explicitly synthetic; the real run uses actual M43H receipt
rehydration and independently retained source hashes.

- Public pre-evaluation freeze: `c3a52884221ae11fff20bfc2458a51d117b94b53`.
- Config SHA-256: `7a6afdfe451d74571b6a62a9f4d676a9836893c7d7490b52ff9a77710d8505ad`.
- M43K sealed result: `dd4f1e66666f2e30e011f2efacf322fa62c324d919fcd6f3fc9fcd2a0b920127`.
- M43I result: `b2f9be7ed22848aaca3d0eab15a1535ee12a5643a06c47a593b15e31db72c41a`.
- M43J result: `3e9ef51c89d4b8d97a4223adb2bcdd3adc0cedbbac08fe3506a546949b098179`.
- Fixed M43E bank: `84524f7e129c0b414bde5004fe64bfb3ff94877357a7bb4dce399562d945d873`.
- Fixed factor table: `bc5c9e1f7a2db63074be30a946b2e1bd68963966f6c6b11cc5ad30f4e173edcd`.
- NumPy: `2.3.5`.

Protocol, source/reference code, exact configuration and tests were public
before the run. No endpoint amendment or failed comparison occurred. Fourteen
sealed per-source/width checkpoints accompany the complete result. This report
checks all seals, parent identities, exact row/width inventory, coverage bounds
and denominators before writing the result manifest.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -p 'test_m43*.py'
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43k_native_filters.py --work-root /path/to/m43h/live --freeze-commit c3a52884221ae11fff20bfc2458a51d117b94b53
PYTHONPATH=src:scripts .venv/bin/python scripts/m43k_result_report.py
sha256sum -c RESULTS_MANIFEST_M43K_NATIVE_FILTERS.sha256
```

Reproduction requires the two M43H source directories, or reconstruction under
that protocol with identical retained receipt hashes. A rerun recomputes the
comparisons. Source/cache, reference-row and local-score digests must reproduce;
elapsed time and the final enclosing result seal may differ. The manifest checks
the published run's file bytes.

## Runtime and next gate

The observed job took **71.239 seconds**, including native
cache recreation, all direct reference windows and the local score comparisons.
This is descriptive timing, not detector throughput or measured sensitivity.
No new remote requests were made. One source/cache and one reference row/chunk
are handled at a time; the inherited 512 MiB adapter-owned ndarray bound excludes
reference/caller arrays, process RSS and OS caches.

The next gate must resolve the remaining wider integrated-score qualification
and extend real source/epoch coverage before validating the full stack/detection
endpoint and running newly frozen null and injection/recovery calibration.
No candidates were ranked, no threshold was calibrated and no recovery rate was
measured. These are numerical qualification results, not an astrophysical finding
or scientific nondetection.
