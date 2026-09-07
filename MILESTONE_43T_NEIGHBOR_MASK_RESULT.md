# M43T: neighboring-support mask results

The new rule recovers 4 additional injected signals and loses 0 previously recovered signals in the 32-case comparison. This is a targeted repair regression on the previously inspected M43S panel. Original M43R/S outcomes remain unchanged.

| Injected profile | Strength | Historical legacy recovered | Neighbor2 recovered | Gained | Lost |
|---|---:|---:|---:|---:|---:|
| ideal-native-bin | 12 | 8/8 | 8/8 | 0 | 0 |
| ideal-native-bin | 32 | 8/8 | 8/8 | 0 | 0 |
| fractional-off-template-smear | 12 | 4/8 | 4/8 | 0 | 0 |
| fractional-off-template-smear | 32 | 4/8 | 8/8 | 4 | 0 |

The named rule accepts support >=3 within two neighboring proxy bins when deciding whether an epoch peak >=10 is isolated. Eight-width OR and nine-bin final mask dilation remain unchanged. Support windows do not wrap. Both strengths use the unchanged native profiles, exact activity subset and <=20 Hz maximum track residual over every active ON row, followed by all physical vetoes and diagnostic rank eligibility. The strengths describe added profile power, not measured recovered SNR.

## Calibration and the limits of the noise comparison

| Policy | Training maximum (128) | Fixed threshold | Held-out maximum (128) | Held-out >= threshold |
|---|---:|---:|---:|---:|
| legacy | 8.262487 | 10.000000 | 8.284749 | 0/128 |
| neighbor2 | 8.262487 | 10.000000 | 8.284749 | 0/128 |

There are 256 distinct new shift rows, excluded from M43R, evaluated once per policy (512 policy/row evaluations). The policies use the same shifts. Their training and held-out vectors are exactly equal: **True**. The original uninjected data has 0 legacy and 0 neighbor2 masked bits. Consequently this panel provides no direct measurement of the change in rejection of strong real interference. Zero exceedances here cannot establish general noise safety. Shifts share one observing sequence; these are correlated pre-veto scores, not independent sequences or physical false-alarm probabilities.

Fresh legacy calibration has the historical threshold: **True**. All 1053 historical member rank-eligibility decisions agree: **True**. The 32 historical legacy runs retain their original M43R certificate and were not rerun or relabelled. Every new injected score inventory exactly matches the paired M43S inventory.

The new uninjected full-detector execution retains 0 ON and 0 OFF members, with 0 physical survivors. This diagnostic baseline is not an astronomical nondetection.

## Validation, scope and next step

All ten focused tests pass. Both mask implementations match an independent reference on all 937,950 full-support bits per policy; the neighbor2 mask is a subset of the legacy mask. Those real baseline anchors are all zero; nonempty isolation, displaced support, threshold boundaries and width-OR behavior are exercised by the known-answer tests. All 24 reused native-cache identities match. The package contains 1,186 compact new member decisions and 32 exact-input paired native trials.

The grouped numerical run took 264.2 seconds. There were no new downloads or telescope requests. The scope remains 37 templates and 4,097 central carriers (about 11.6 kHz) in six scans from one observing sequence, with all eight widths and four activity subsets. The finite smeared profile is a defined model, not an instrument measurement.

The radius was chosen after the M43S loss diagnosis, then frozen before M43T evaluation. Any recovery improvement is evidence for this specific repair on a known panel, not independent astrophysical completeness. The next useful experiment is a jointly frozen panel of nearby true-signal tracks and strong interference controls on additional carrier locations, with both policies and fresh calibration. General adoption remains premature. No astronomical candidate is claimed.

## Reproduction and artifacts

- Public prospective freeze: `0bfa205d3f0671de661b6555c42a4763dcba0165`.
- Configuration SHA-256: `6b4f42d9ffbb49140c8adaa1c17fc10d4733a346503d56bdc2c3782bb5991098` (272 pinned dependencies).
- Result seal: `64065eec6e8982972c8bd13f4a5616ff8bee9ae57db185446ce48aa9772fd78e`.
- [Frozen plan](MILESTONE_43T_NEIGHBOR_MASK_PLAN.md) and [configuration](config/m43t_neighbor_mask.json).
- [Full paired results](results_m43t_neighbor_mask/result.json), [run log](results_m43t_neighbor_mask/live_run.log), [artifact validation](results_m43t_neighbor_mask/artifact_validation.json), and [checksum manifest](RESULTS_MANIFEST_M43T_NEIGHBOR_MASK.sha256).
- All 32 per-trial audits, both calibration and held-out arrays, mask/native anchors and baseline are in `results_m43t_neighbor_mask/`.

With the original verified source and M43P anchors available, use Python 3.12.13 and NumPy 2.3.5 in a clean results directory:
```bash
PYTHONPATH=src:scripts:tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/m43t_neighbor_mask.py \
  --freeze-commit 0bfa205d3f0671de661b6555c42a4763dcba0165 \
  --anchor-root /path/to/m43p_work --source-root /path/to/m43h_work/live
```

Completed results are protected from overwrite. Sealed trial checkpoints can only resume with matching freeze/configuration and native input identities.
