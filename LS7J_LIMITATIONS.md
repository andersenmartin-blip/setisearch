# LS7J: the motion response is the measured limitation

Completed 14 September 2026. This is retrospective bookkeeping of the sealed,
audited LS7J result. No new correction, fitted gain, sign, delay, detector cut,
source profile or observing sector is evaluated.

**The fixed motion-plus-plane correction increases native residual energy by
45.74% in sector 29 and 34.51% in sector 32.** Every one of the twenty background
aggregates becomes worse. Missing motion fields and pulse self-subtraction do
not explain this failure: all required motion values are available, and every
predeclared pulse-protection requirement passes.

## Which component accounts for the failure?

The predeclared motion-only ablation is almost as poor as the combined method.
The outside-aperture plane changes the native metric only slightly. It improves
five of ten backgrounds in each sector, below the required six, and is not
adopted as a replacement.

| Sector | Motion-only energy ratio | Plane-only ratio | Combined ratio | Combined backgrounds improved |
|---|---:|---:|---:|---:|
| 29 | 1.459807 | 0.995610 | 1.457369 | 0/10 |
| 32 | 1.345963 | 0.999325 | 1.345143 | 0/10 |

These ratios use the same static baseline and covariance. They describe the
fixed closed-context comparison, not a calibrated probability of failure.

Let r be the original native residual and c the recorded correction after the
common whitening and uniform-component projection. The exact identity

\[
\|r-c\|^2-\|r\|^2=-2\,r^T c+\|c\|^2
\]

separates the correction's alignment with the residual from its own squared
size. Summing the existing vectors gives the following terms as percentages
of total static energy. Their sum is the observed percentage change; no
regression or alternative correction is fitted.

| Sector | Method | Alignment term | Correction-size term | Net change |
|---|---|---:|---:|---:|
| 29 | Motion | −14.38% | +60.36% | +45.98% |
| 29 | Plane | −0.785% | +0.346% | −0.439% |
| 29 | Combined | −15.17% | +60.91% | +45.74% |
| 32 | Motion | −17.98% | +52.58% | +34.60% |
| 32 | Plane | −0.308% | +0.240% | −0.0675% |
| 32 | Combined | −18.30% | +52.81% | +34.51% |

Motion has positive aggregate alignment with the residual, but its correction
size overwhelms that benefit. Its aggregate directional cosines are only
0.0925 and 0.1240. This identifies a poor match between this unit-gain shifted
reference and the measured fluctuation. It does not identify whether motion
measurement noise, timing, the response approximation or other fluctuations
are responsible. These are weighted geometric summaries, not independent
significance estimates or proof that all motion information is useless.

## Signal protection and availability are established within scope

| Check | Sector 29 | Sector 32 |
|---|---:|---:|
| Available POS_CORR pairs | 4,010/4,010 | 4,010/4,010 |
| Valid protected operators | 290/290 | 304/304 |
| Historical aperture-limited stellar pulses | 1,320/1,320; exactly unchanged | 1,320/1,320; exactly unchanged |
| Full-stamp pulse maximum distortion | 0.0710%, against 1% allowed | 0.0288%, against 1% allowed |
| Broadened pulse maximum distortion | 0.312%, against 5% allowed | 0.365%, against 5% allowed |

The unavailable PSF centroid/error values were inventory fields, not inputs.
Mission moment centroids are available but are not independent of target flux.
Holding POS_CORR fixed under digital injections tests only the downstream
correction. The empirical wing profiles are also not an independent target-PRF
calibration. Those qualifications remain even though all 5,040 gated stellar
response rows pass. The full 9,480-row ledger also contains controls and nulls;
none are new detector decisions.

## Concrete next information requirement

Close LS7J and keep its numerical specification and result unchanged. The next
useful step is an **instrument-response provenance assessment** for the same
closed sectors. Establish a documented mapping from the available motion
quantity to changes in these processed 20-second pixels: coordinate convention,
reference frame, effective time averaging, response uncertainty, and possible
dependence on the target signal. The existing field labels alone do not supply
that validated mapping.

The assessment should identify a usable independent motion/engineering source
or a calibrated pixel-response description, with product identities and an
explicit account of missing information. Availability of such an input has
not been established here. Do not select a sign, gain or time lag by improving
these LS7J outcomes. A later calibration study would need its own prospective
specification, entire-background exclusions and consistent pixel-plus-motion
controls. The protected outside-pixel operator can be retained as a tested
building block, but has not qualified a detector.

If that response information cannot be established, record the absence and
reconsider the optical data/method choice instead of appending another local
correction search. Unused sectors and M43 held-out panels remain closed.

## Reproduction and evidence

`python scripts/ls7j_limitations.py` verifies every sealed result hash, checks
the identity against each existing window/method energy and writes
[LS7J_LIMITATIONS.json](LS7J_LIMITATIONS.json), including all 1,260
window/method records. The largest absolute identity discrepancy is
6.82e-13. This bookkeeping reuses the independent audit and does not rerun the
scientific evaluation.

Audited result commit: `52ef2780a374e1314252f8fe9f37d8fcae4d985f`.
[Complete result and figure](results_ls7j_auxiliary/REPORT.md),
[independent audit](results_ls7j_auxiliary/AUDIT.json),
[current continuation](LS7J_CONTINUATION.md).
