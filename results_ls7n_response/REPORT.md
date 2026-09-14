# LS7N cadence-level calibrated response — joint requirement FAIL

Completed and independently audited 14 September 2026. Source freeze:
`07c6040715b8425a2051bfdbeb2806974f85d6c7`.

**The new calibrated response does not improve native prediction.**
All 420 original windows are available under both coordinate conventions
(840 paired model/window rows), and all 12,600 downstream pulse responses
pass their fixed protection limits. Both sectors fail the native requirement.
No detector is adopted, new candidate selected or observing coverage added.

## Native result on the unchanged metric

All rows below use the same original static baseline, aperture and covariance.
Changes are percentages of static residual energy; positive means worse.
Coordinate alternatives are separate sensitivity outputs, not two observing samples.

| Sector | Field-column offset | Motion only | Protected plane only | Combined | Combined backgrounds improved |
|---|---:|---:|---:|---:|---:|
| 29 | 0 | +11.6807% | +0.5327% | +12.1389% | 0/10 |
| 29 | -44 | +11.9028% | +0.5327% | +12.3646% | 0/10 |
| 32 | 0 | +12.9165% | -0.3740% | +12.4918% | 2/10 |
| 32 | -44 | +12.8004% | -0.3740% | +12.3729% | 2/10 |

Combined response improves zero of ten sector-29 backgrounds and two of ten
sector-32 backgrounds, against six required. No background is doubled, but
the aggregate and improvement-count gates fail in all four cells. Plane
alone passes in sector 32 and fails in sector 29; it is not selected as a
replacement. The separately closed LS7J combined increases were 45.74% and
34.51%. The new increases are smaller, but the fixed static baseline remains
better. That historical comparison is descriptive and adds no validation sample.

## Why the correction loses on this metric

For static residual r and correction c under the fixed projected covariance
metric Q, the energy change is -2 r^T Q c + c^T Q c. The two terms below
sum to the reported combined change. No gain or alternative correction was fitted.

| Sector | Offset | Alignment term / static energy | Correction size / static energy |
|---|---:|---:|---:|
| 29 | 0 | -8.9310% | +21.0698% |
| 29 | -44 | -8.9450% | +21.3097% |
| 32 | 0 | -11.8662% | +24.3579% |
| 32 | -44 | -11.5397% | +23.9126% |

The correction has useful aggregate alignment, but its squared size exceeds
that benefit. This establishes a mismatch for this fixed cadence response.
It does not distinguish motion-estimator noise, response derivative error,
reference astrometry, crowding or other scene changes. Availability and
downstream pulse self-subtraction do not explain the observed failure.

## Pulse protection and calibration-entry stress

| Sector | Offset | Maximum nominal distortion | Maximum entry-stress distortion | Failed pulse cases |
|---|---:|---:|---:|---:|
| 29 | 0 | 0.013685% | 0.141511% | 0/3150 |
| 29 | -44 | 0.015353% | 0.141227% | 0/3150 |
| 32 | 0 | 0.011274% | 0.224724% | 0/3150 |
| 32 | -44 | 0.011577% | 0.226796% | 0/3150 |

Limits are 1% for nominal PRFs and 5% for the two entry-stress profiles.
The 12,600 rows cover five source offsets, three profile variants and all
840 model/window combinations. Pulses are constant over the fixed windows
of 2, 3 or 5 cadences (40, 60 or 100 seconds); these are not millisecond
pulse timing tests. Positional metadata and outside-event samples stay fixed.
This demonstrates downstream protection only; unknown upstream target
participation remains unbounded. Entry stresses are not statistical draws.

## Physical scope and uncertainty

The model translates an effective commissioning PRF using supplied 20-second
POS_CORR displacements. It adds no quaternion jitter or second exposure blur.
Its source amplitude and reference are estimated only from protected sidebands.
The background plane protects the 18 declared calibrated source profiles.
All fits and operators are available; every protected span has rank 18.
The fixed 110-pixel support retains both original science apertures.

The exact fast motion kernel, reference astrometry, focus/color response and
upstream target exclusion remain unestablished. The two column conventions
produce the same failure; that sensitivity does not solve the absolute origin.
There is no tested quaternion-to-detector or subcadence response in LS7N.

Calibration entries are transported into a conservative image envelope,
without interpreting their covariance or including amplitude-fit error.
Its median aperture norm divided by the motion-prediction norm is:

| Sector | Offset | Median envelope norm / motion norm |
|---|---:|---:|
| 29 | 0 | 18.3197 |
| 29 | -44 | 18.4396 |
| 32 | 0 | 28.3522 |
| 32 | -44 | 29.0896 |

These deliberately broad entry envelopes do not calibrate small-motion
derivative uncertainty. Their size is not a measured probability of an error
or proof that the actual derivative is inaccurate by that factor.

## Independent audit and decision

The audit rebuilt all native and pulse rows with **108,604 numerical comparisons**.
It uses raw FITS image bytes, SciPy interpolation, normal equations for
source flux, a different SVD driver/QR solve for the plane, and explicit
quadratic forms. It imports none of the new producer or response operators.
Maximum aperture-correction difference is 1.98e-12 electrons/second;
maximum individual energy difference is 3.19e-12 and pulse-distortion
difference is 7.27e-14. All 146 inherited manifest entries remain unchanged.
Five analytic/known-answer tests also pass, including exclusion of event
photons from source amplitude and noise estimation.

**Close this exact cadence-level calibrated correction as a negative result.**
No empirical gain/sign/lag/profile retry or unused-data opening follows.
The next useful information is an independent astrometric/reference-star
measurement and response uncertainty on the same pointing, with explicit
target exclusion and time sampling. An availability/geometry assessment must
precede any bounded acquisition; no such new input is claimed to exist here.
If it cannot be established, reassess the optical data/product choice rather
than append another locally adjusted correction.

[Current continuation](../LS7N_CONTINUATION.md), [frozen specification](../LS7N_SPEC.md).

## Reproduction

[Native records](native.jsonl.gz), [pulse responses](pulses.jsonl.gz),
[summary](summary.json), [independent audit](audit.json),
[descriptive accounting](diagnostics.json), [evaluation log](evaluation.log),
[audit log](audit.log), [provenance](provenance.json), [checksums](SHA256SUMS).

Execution was local Python 3.12.14 with requirements_ls7g.txt. No GitHub
Actions run is claimed. Source and audit scripts refuse to overwrite results.
Reproduce in an isolated checkout of the source freeze before the result
directory existed. No additional raw engineering download is needed.
