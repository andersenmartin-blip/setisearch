# M43D: coefficient-disk bank coverage result

**Completed: the preselected 889-template bank does not pass the frozen held-out geometric gate.**

All 512 historical M43B plan hashes and every baseline template/carrier pair reproduce exactly. The original 167/512 supported truths are preserved. Adding fixed, nested grids across the two-dimensional coefficient disk improves geometric coverage at the unchanged 20 Hz tolerance.

## Coverage comparison

Each cell below is supported tracks / 512. New tracks are reused under the four activity patterns, allowing paired comparisons. Epoch numbers in this table are one-based.

| Templates | Historical | New: epochs 1+2 | New: 1+3 | New: 2+3 | New: all three |
|---:|---:|---:|---:|---:|---:|
| 93 | 167/512 (32.6%) | 214/512 (41.8%) | 108/512 (21.1%) | 199/512 (38.9%) | 98/512 (19.1%) |
| 289 | 356/512 (69.5%) | 404/512 (78.9%) | 257/512 (50.2%) | 413/512 (80.7%) | 231/512 (45.1%) |
| 889 | 506/512 (98.8%) | 502/512 (98.0%) | 486/512 (94.9%) | 501/512 (97.9%) | 470/512 (91.8%) |
| 3301 | 512/512 (100.0%) | 511/512 (99.8%) | 511/512 (99.8%) | 511/512 (99.8%) | 511/512 (99.8%) |

The frozen development rule nominated **disk16 (889 templates)** from the historical inventory before evaluating new tracks. The nomination identity is `f1e53b7270995c783c5b2d492ca66e36079ef8002eea9f92de45f741763c1264`. The new-track gate requires at least 95% coverage in each activity group; it **fails**. No bank was substituted after viewing the held-out results.

The 512 new tracks use separate, predetermined SHA-256 jitters in equal-area disk strata and continuous off-grid carriers. They do not coincide with historical coefficient pairs or template points. Their carriers span the historical allowed proxy interval, while historical carriers were on the grid. Historical and new rates therefore differ in carrier sampling and are not interchangeable estimates. These are 512 new parameter draws on the same cadence, not independent telescope observations, sky signals, or 2,048 independent trials.

## Computational cost

| Templates | Score cells per window | Five-window arithmetic total | Relative cells | Factor table bytes, six scans |
|---:|---:|---:|---:|---:|
| 93 | 2,225,051,040 | 11,125,255,200 | 1.00× | 71,424 |
| 289 | 6,914,405,920 | 34,572,029,600 | 3.11× | 221,952 |
| 889 | 21,269,573,920 | 106,347,869,600 | 9.56× | 682,752 |
| 3,301 | 78,977,349,280 | 394,886,746,400 | 35.49× | 2,535,168 |

The joint geometry calculations evaluated 13,526,704 distance cells in 6.33 measured seconds, excluding basis reconstruction, historical plan replay and disk checkpoints. The largest factor table occupies 2,535,168 bytes. This is a metadata computation; the cell ratios are not measured detector runtime ratios. Spectral reads, filtering, caches, masks and calibration are absent from this timing.

## Interpretation and next step

This result removes much of the tested geometric limitation. It does **not** measure signal recovery, sensitivity, false-alarm rates or physical completeness. An associated template can still fail masking, threshold, OFF/control or other scientific acceptance gates. No telescope candidate is promoted, and M37/M41/LS results remain unchanged.

The preselected 889-template bank fails in two new activity groups (486/512 and 470/512). The 3,301-template bank has a descriptive 511/512 result in each group, but was not the preselected confirmation candidate. Do not promote it by switching banks after this check. No bank is qualified for adoption by this gate. Diagnose remaining coverage and computational tradeoffs before a separately frozen next study; any new confirmation must use previously unevaluated tracks.

Even a passed 95% sample gate is not a full-domain guarantee. Boundary coverage, other cadences, orbital uncertainty and other physical windows remain outside this study.

## Reproducibility and verification

Public freeze: `191f3b4d7182adc6c82e3dcc5c006f2fb29382cb`; tree `4203d597ecf58c794b47139ca7f64ed8d5321f7d`, verified before execution. Result identity: `9566e72981a696e18abffefa71c356a805d7a8043d17d269b41c1c78fc1d905b`.

All 21 M43/M43B/M43C/M43D tests pass. This report checks all 2,560 row identities and group counts, bank identities and nested candidate counts; it independently re-evaluates all 7,468 published support witnesses from the coefficient/basis formula. Each witness satisfies the original literal <=20 Hz rule. Historical plans and all baseline pairs were replayed during execution. This is not a new full-repository test run or a formal real-arithmetic certificate.

The sealed combined `geometry.json` (published as lossless `geometry.json.gz`, automatically unpacked by the report command) retains every restart row, per-bank candidate-pair hashes and witnesses. Pair lists are regenerable from the frozen metadata and code. `historical_selection.json` preserves the nomination; CSV files support review. Restart copies are omitted from Git because the combined result contains them. Runtime values are observational and will differ on a fresh run; they are not scientific thresholds.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43d_bank_coverage.py
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43d_result_report.py
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_m43*.py' -v
```
