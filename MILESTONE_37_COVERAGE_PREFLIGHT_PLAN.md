# Milestone 37 metadata-only coverage preflight plan

Status: **FROZEN BEFORE M37 SPECTRAL CONTACT**.

This preflight uses the official HD 156668 b composite record and the six
already published rank-37 HDF5 headers. It must not refresh the cadence
catalogue, open a telescope object, index the HDF5 `data` dataset, or read a
spectral value. Its result is an extraction-support proof, not a detection or
sensitivity result.

## Boundary and normative question

The source boundary is selected-metadata result commit
`269c213f256a48bc7f76ae042b98eaa85bf76008`. The unique eligible cadence is
`--85168`, with three HIP84607 ON scans alternating with three HIP84607_OFF
scans. The composite eccentricity is exactly zero, so the supplied nominal
periastron epoch and angle do not define a unique physical phase.

The normative question is therefore phase independent:

> Do the frozen 2.6 MHz extraction windows contain the complete central
> 1 MHz rest-frequency grid, the maximum 129-channel spectral-support guard,
> and the dedoppler shifts for every projected circular-orbit scale in
> `[0, 1]` and every phase modulo one, for all 16 integrations of all six
> scans?

There are 30 normative scan-by-window checks and 480 scan-by-window
integration evaluations (16 integrations are evaluated in each check).

## Analytic envelope

For each integration, let `A_i = 1 + v_observer,i/c`, let `K = 2πa/P`, and
let `Δθ_i` be the circular phase advance from the first integration. Maximizing
over a single common phase and projected scale from zero through one gives the
exact coefficient-disk bound

```text
max |F_i - F_0|
  = |A_i - A_0|
    + (K/c) hypot(A_i cos Δθ_i - A_0, A_i sin Δθ_i).
```

The implementation evaluates the norm in this cancellation-stable form,
rounds factor and frequency endpoints outward, and uses a tie-safe integer
bound for NumPy nearest-even channel mapping. For a positive real displacement
`d`, that bound is `floor(nextafter(d, +∞)) + 1`; it is zero when `d` is zero.

The expected conservative envelope is:

| Window | Minimum lower headroom | Minimum upper headroom | Maximum motion margin |
|---|---:|---:|---:|
| m37_1400p5 | 116,776 ch | 59,816 ch | 822 ch |
| m37_1406p5 | 116,067 ch | 58,864 ch | 826 ch |
| m37_1412p5 | 115,360 ch | 57,913 ch | 829 ch |
| m37_1418p5 | 114,650 ch | 56,960 ch | 833 ch |
| m37_1425p0 | 113,883 ch | 55,929 ch | 837 ch |

The smallest expected edge reserve is 55,929 channels, about 158.587 kHz.
Any negative headroom, source mismatch, geometry mismatch, nonzero
eccentricity, reduced phase/scale domain, or dependency drift invalidates the
preflight.

## Width, controls, and historical regression

The circular speed derived from the official orbit is
117,092.49980661187 m/s and the maximum acceleration is
1.8330011579451448 m/s². At 1425 MHz this is 8.712783061646705 Hz/s. One
17.986224128-second integration spans 156.71006892541968 Hz, or
55.26710632954757 raw channels. Width 65 is the first member of the historical
eight-width bank at least this large. Width 129 has 64 rest-grid neighbours on
each side; full-phase Doppler mapping can spread those neighbours over 65 raw
channels, which is the normative extraction-support guard used above.

The preflight also replays the old 21-template extension bank over all six
scans and five windows. Its 630 checks are explicitly a non-normative software
regression. Passing them does not prove full-phase search sensitivity and does
not freeze the M37 detector-v0.6 bank.

If that historical bank were reused unchanged, it would imply 672 hypotheses
and 236,994,912 nominal tensor cells per window, or 1,184,974,560 total. These
are conditional resource figures, not retained-record limits. The detector
and complete-retention capacity gates will be frozen separately.

The three OFF scans revisit one sky direction approximately two degrees north
of the ON target. They are three temporal control measurements but only one
independent spatial control direction. This limitation must remain explicit in
the final interpretation.

## Required non-claims and v0.6 gate

This preflight does not:

- claim that the old 21-template bank covers every orbital phase;
- select or freeze the M37 v0.6 template bank;
- prove Fourier-leakage or S/N completeness;
- propagate uncertainty in period, semimajor axis, or the other composite
  orbital fields beyond their exact frozen working values;
- define the complete retained-record set or any adaptive report cap;
- establish that every width has finite scores at every 1 MHz rest-grid bin.

The last point matters because detector v0.5 maps directly to the 1 MHz rest
grid and then applies its boxcar. A width-129 vector consequently has 64 NaN
bins at each rest-grid edge even though the source extraction has ample guard.
Detector v0.6 must prospectively freeze either expanded-grid filtering followed
by cropping or an explicitly narrower finite search domain.

Likewise, any later finite-bank proof that absorbs track mismatch into a common
carrier-frequency offset must separately freeze the carrier coordinate and
show that its recentering remains inside the searched physical band. The
continuous exact-track extraction proof here does not settle that bank-specific
question.

## Reproducibility and publication

The workflow pins Python 3.12.14, NumPy 2.5.2, Astropy 8.0.1,
astropy-IERS-data 0.2026.8.24.0.24.29, and pyerfa 2.0.1.5. It verifies every
upstream hash, the exact official target fields, all six URLs/sizes/ETags and
headers, the five window geometries, mutation tests, and the absence of prior
preflight outputs.

Only after every check passes may the workflow atomically publish:

- `results_m37_preflight/coverage.json`;
- `RESULTS_MANIFEST_M37_COVERAGE_PREFLIGHT.sha256`;
- `MILESTONE_37_COVERAGE_PREFLIGHT_PROVENANCE.json`.

The publication must preserve false values for spectral payload inspection,
spectral dataset reads, remote file opens, and telescope requests. A failure
publishes no scientific result and authorizes no spectral contact.
