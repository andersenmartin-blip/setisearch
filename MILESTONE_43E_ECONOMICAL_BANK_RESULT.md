# M43E: economical bank and remaining coverage

**Completed: the preselected 1,701-template bank passes its fresh geometric confirmation.**

## Fresh confirmation

Every row below tests the same 1,024 new parameter draws under one activity pattern. These are paired groups, not 4,096 independent astronomical trials. Epoch labels are one-based.

| Group | Tracks | 93 templates | 889 | 1,701 | 3,301 |
|---|---:|---:|---:|---:|---:|
| epochs 1+2 | 1024 | 399 (38.96%) | 1011 (98.73%) | 1016 (99.22%) | 1021 (99.71%) |
| epochs 1+3 | 1024 | 196 (19.14%) | 975 (95.21%) | 1011 (98.73%) | 1020 (99.61%) |
| epochs 2+3 | 1024 | 409 (39.94%) | 1005 (98.14%) | 1014 (99.02%) | 1021 (99.71%) |
| epochs 1+2+3 | 1024 | 175 (17.09%) | 950 (92.77%) | 1011 (98.73%) | 1020 (99.61%) |

The required minimum is 973/1024 in every group. Only **checker32** was nominated for confirmation; reference-bank results are descriptive. The nomination was public at `03ca1b867e8a5d9b10331d3e16fec10c24a9bb22` before any fresh evaluation. No post-confirmation substitution occurred.

## Why the previous banks missed tracks

All 2,560 M43D associations reproduce their four original bank pair hashes, counts and witnesses exactly. Diagnosis covers every failed association in disk16 and disk32. An association is one track/activity combination; repeated activities are not distinct tracks.

| Bank | Failed associations | Distinct truth IDs | Track shape | Outside carrier range | Between carrier cells | Unresolved |
|---|---:|---:|---:|---:|---:|---:|
| disk16 | 95 | 48 | 20 | 59 | 16 | 0 |
| disk32 | 4 | 1 | 0 | 4 | 0 | 0 |

The largest bank’s four failed associations belong to one track; each has a continuous template/carrier solution outside the current carrier range. They are not four independent missed sources. The range remains unchanged and all failures remain in their denominators. The minimax calculation uses longdouble and the frozen 0.001 Hz ambiguity guard; exact acceptance still requires <=20 Hz.

## Development and bank choice

The checkerboard construction keeps all 889 existing templates and adds 812 odd/odd grid points, giving 1,701 total. It places no templates at known truth coordinates. Nomination uses all five exposed M43D groups below. M43D’s former fresh groups are now development data for M43E, not its independent confirmation. Activity suffixes in these source labels are zero-based.

| Group | Tracks | 93 templates | 889 | 1,701 | 3,301 |
|---|---:|---:|---:|---:|---:|
| historical | 512 | 167 (32.62%) | 506 (98.83%) | 512 (100.00%) | 512 (100.00%) |
| m43d-known-01 | 512 | 214 (41.80%) | 502 (98.05%) | 504 (98.44%) | 511 (99.80%) |
| m43d-known-02 | 512 | 108 (21.09%) | 486 (94.92%) | 501 (97.85%) | 511 (99.80%) |
| m43d-known-12 | 512 | 199 (38.87%) | 501 (97.85%) | 501 (97.85%) | 511 (99.80%) |
| m43d-known-012 | 512 | 98 (19.14%) | 470 (91.80%) | 501 (97.85%) | 511 (99.80%) |

The fixed rule nominates **checker32**, the first of checker32/disk32 with >=95% coverage in every development group. Nomination hash: `5b372ede05c90a5336a5005ffcdf02fec508575b5967ee3541e6391f9ce505de`.

## Computational cost

| Bank | Templates | Score cells per window | Relative to original 93 | Relative to 3,301 | Factor table bytes |
|---|---:|---:|---:|---:|---:|
| baseline | 93 | 2,225,051,040 | 1.00× | 2.82% | 71,424 |
| disk16 | 889 | 21,269,573,920 | 9.56× | 26.93% | 682,752 |
| checker32 | 1,701 | 40,696,901,280 | 18.29× | 51.53% | 1,306,368 |
| disk32 | 3,301 | 78,977,349,280 | 35.49× | 100.00% | 2,535,168 |

The 1,701-template bank has **48.47% fewer score cells than the 3,301-template bank**, while retaining 18.29 times the original 93-template cell count. These are exact hypothesis-count ratios, not measured detector speedups. Full scoring also requires new filtering, cache, mask and null-calibration work.

Fresh geometry evaluation took 10.45 measured seconds for 21,408,416 interval-prefilter distance cells. This excludes basis construction, checkpoint I/O and all spectral processing. The calculation uses one full factor table and derives the checkerboard subset from it; it is not a separate wall-time comparison of operational banks.

## Decision and limitations

Carry the **fixed 1,701-template checkerboard bank** forward to source/extraction/cache coverage checks, score and false-association validation, and deterministic exhaustive real-data anchors. Renew threshold calibration before scientific use. This is a geometric engineering qualification; no production detector is changed or approved by this result.

No telescope samples, injected spectra, masks or scores were evaluated. Geometric support is not measured recovery, sensitivity, a false-alarm rate or evidence of a technosignature. The fresh tracks share the same cadence and orbital assumptions. Carrier edges remain in scope; no result proves coverage of every coefficient, other physical windows, other cadences or orbital-parameter uncertainties. The original M43D failed gate and all M37/M41/LS results remain unchanged.

## Verification and restart

Frozen code/config publication: `6464c914ee9e5643f17483c91c8c1ea410c639cd`, tree `0c13e07eb4a74c7cf9df3d0db8fa4ec8ac6d0c2e`. Development result: `97886836096bc8b16ca557de2c7eebbbcd9566bbd1cf799773b3c5dd9b6ba64d`.

All 26 M43-family tests pass. The report verifies every development row identity, all group counts, bank identities, 8,326 development support witnesses directly from physical coefficients, and the 99 best diagnostic fits. All-template diagnosis inventories are hashed and reproducible from frozen code; they are numerical diagnoses, not formal real-arithmetic certificates.

Fresh result: `41d0a61648d877710aef1549b63e30f66e1220fdd91bd31bd1e8061ca8c27198`. All 4,096 fresh row identities and 13,254 fresh witnesses are verified. No broader repository test run is claimed.

Lossless `development.json.gz` and, after execution, `confirmation.json.gz` contain the complete per-association restart rows. `selection.json` binds the nominated bank to the development result. CSV summaries ease review; per-template/carrier pairs can be regenerated from their hashes. Elapsed times vary on a fresh run.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43e_economical_bank.py --stage development
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43e_result_report.py --stage development
# Publish and verify the sealed nomination before continuing.
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43e_economical_bank.py --stage confirmation
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43e_result_report.py --stage final --nomination-commit 03ca1b867e8a5d9b10331d3e16fec10c24a9bb22
```
