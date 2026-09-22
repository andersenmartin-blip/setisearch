# LS8AF–LS8AH — PG 1207-033 complete result and exact continuation

22 September 2026. The predetermined rank-10 pair and its single bounded
retained-data follow-up are **complete and closed**. Its positive TG000901_P0
retains **UNRESOLVED_WITHIN_FIXED_SCOPE**. The dominant visible feature is an
extended stripe near the aperture edge; its physical cause remains unassigned.
No qualified SETI candidate, detector, sensitivity or observing coverage is added.

## Complete prospective L2 result

Both visits have verified NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2. The unchanged signed screen uses 60/120/180-second events, 12-row
sidebands, two-row guards, original eligibility and symmetric +/-8.5 endpoints.
The 153 retained rows provide 165 eligible overlapping windows.

| Visit | Rows | Eligible overlapping windows | Minimum score | Maximum score | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR100002_TG000901_V0300 | 81 | 117 | -4.169607 | +141.105459 | 1 / 0 |
| CH_PR100002_TG000902_V0300 | 72 | 48 | -1.174327 | +1.591033 | 0 / 0 |
| Total | 153 | 165 | — | — | 1 / 0 |

Six positive threshold crossings form one cluster; no negative crossing occurs.
Its original representative is zero-based row 60, one 60-second exposure,
score **+141.1054591837304**, approximately **43.12658% above** its local L2
baseline. Every eligible window and both complete signed cluster sets are
retained. Scores are not Gaussian significances and overlapping windows are
not independent trials. Exact science acquisition is **21,114 table bytes**,
after a separate public science freeze. The second visit triggers no image
follow-up; all its retained rows remain visible in the L2 figure.

## Fixed paired-image diagnostic

The complete signed representative set was frozen before image metadata.
All 29 L2 context rows 46:75 have unique CAL/COR exposure matches:
58 joins, <=1 ms MJD/BJD differences, exact UTC and agreeing exposure
counters/integrity. A separate payload freeze fixed **18,560,000 image bytes
and 46,400 smearing bytes**. CAL/COR are native ADU products; their sums are
not directly equated with L2 electron fluxes.

| Quantity | C0 | C1 |
|---|---:|---:|
| CAL residual aperture sum [ADU] | 118,461.357296 | 72,091.340334 |
| COR residual aperture sum [ADU] | 151,526.034455 | 105,156.046974 |
| DELTA=COR-CAL aperture sum [ADU] | 33,064.677159 | 33,064.706640 |
| DELTA / COR | 0.218211 | 0.314435 |
| Column-projected DELTA / COR | 0.215029 | 0.309622 |
| COR brightness explained energy [%] | 7.950563 | 7.200159 |
| COR displacement explained energy [%] | 11.404837 | 16.229217 |

Both original apertures are complete and retain the positive L2 sign.
Neither correction ratio reaches 0.5; displacement explained energy stays
below 80% in both conventions. The unchanged outcome is
**UNRESOLVED_WITHIN_FIXED_SCOPE**. Rank-deficient smearing fits remain
unavailable. No aperture, convention, threshold or label is changed.

The CAL/COR figure shows an extended stripe crossing the upper aperture
edge. This is a morphological observation, not an assignment of physical
cause. The fixed SPATIALLY_STRUCTURED gate specifically tests the displacement
model; visible extended structure alone does not satisfy or replace that gate.

## Single retained-data residual/noise study

LS8AH prospectively fixed one transfer of the existing LS8U duration-aware
method to this one 60-second context. It reused the saved cubes without new
archive bytes. Both products and both conventions are retained: four native
cases, 96 duration-matched held cases and 64 signed signal controls.
The unchanged weighted combined model gives:

| Product / convention | Residual/reference, correlated | Residual/reference, IID | Held single-row controls >= native | Top ten weighted residual pixels |
|---|---:|---:|---:|---:|
| CAL / C0 | 175.274115 | 186.757858 | 0/24 | 35.3047% |
| COR / C0 | 278.663206 | 283.052164 | 0/24 | 36.7278% |
| CAL / C1 | 80.463731 | 85.719383 | 1/24 | 47.2243% |
| COR / C1 | 124.118239 | 126.205858 | 0/24 | 49.7609% |

COR residual/reference energy is **278.663206 in C0 and 124.118239 in C1**.
No held COR control reaches its native value in either convention. These
large residuals establish a mismatch with the fixed local sideband model;
0/24 is not a calibrated probability, significance or evidence of artificial
origin. CAL/C1 has one held value at least as large, also fully retained.
The covariance model increases COR variance by only 1.57500%/1.68196%.

The fixed 16–25-pixel ring contains **98.38791%/97.83721%** of COR weighted
residual energy. The residual figure places its strongest positive feature
at the upper aperture edge, consistent with the stripe already visible in
CAL/COR. This spatial description uses the original partition and does not
introduce a mask, stripe model, recentering or a new selection rule.

Exact C0/C1 accounting gives 1,892 common pixels and 71 unique pixels in
each convention. COR C1 minus C0 is **-46,369.987482 ADU**, exactly the sum
of its C1-only pixels minus its C0-only pixels. DELTA changes by only
**+0.029480 ADU**. This accounts for the aperture-sum difference; it does
not assign a unique cause or attribute every fitted-model difference to
boundary pixels.

With the same COR residual projector, CAL/COR residual energy ratios are
1.001958/1.003085, DELTA/COR 0.001267/0.002826 and the signed twice-cross
terms -0.003225/-0.005911. These components add to the COR result but are
not independent physical-cause fractions.

Hypothetical gradients-plus-constant subtraction loses **42.99296%/43.53491%**
of injected COR brightness flux. It is not adopted. Both injection signs
pass unchanged coefficient and linearity checks. The original positive stays
unresolved under LS8AG; this one bounded study nevertheless closes as specified.

## Verification and publication

All five workflows succeed at their recorded public freezes. The five
transport tests, two L2 tests, nine image tests and 18 residual tests pass.
The independent L2 audit passes **1,980 comparisons**. Before pixels, image
metadata passes **58 unique joins and 269 exact checks**. The image audit
passes **94,537 numerical and 160,581 exact checks**; the residual audit
passes **305,224 numerical and 320,118 exact checks**. No disagreement or
scientific rerun occurs. All three figures were visually inspected.

The ten scientific commits add **180 files**, changing no earlier file.
Exactly 178 also match local Git blob identities. All 28 header, 22 L2,
57 image-metadata and 18 residual manifest entries are locally SHA256-verified.
Of 22 image-result entries, 20 are locally verified. The two larger compressed
CAL/COR cubes remain verified by both successful image and residual workflows,
including raw/compressed digests and independent decoding; they were not
additionally copied locally. The publication record states their exact identities.

## Exact next action

Keep the PG 1207-033 pair closed. Prepare **LS8AI**, the next independent
metadata-first transfer to **rank-11 EC13080-1508** in the unchanged reconciled
LS8J chronology:

| Chronological visit | Exact product key | Ledger start MJD | Existing exposure tuple |
|---|---|---:|---|
| First | CH_PR100002_TG005201_V0300 | 58966.6032335509 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100002_TG005202_V0300 | 58969.4900390951 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

The third eligible visit, CH_PR100002_TG005203_V0300, remains outside the
fixed two-visit transfer. Verify ledger exposures against each selected
product's own header. First freeze the exact pair and header-only budget;
verify identities, schema, row counts and exposure values. Only after a
passing public result freeze exact DEFAULT-L2 ranges and transfer the
unchanged signed screen and independent audit. These science values remain
unopened. Any triggered images require the complete signed representative
set, unique exposure joins and a separate exact payload freeze.

Do not adopt LS8AH residual ranks, spatial concentrations, covariance ratios
or signal losses as screening cuts. The original 1,000-row census, 452 eligible
visits and 107-cohort chronology remain unchanged. The prior TESS_260647166
positive and PG1303-114 negative retain their unresolved labels and closed
bounded studies. Other closed studies and reserved TESS/M43 panels remain
closed. Calibration is NOT_READY and its request unsent. Standing research
and publication authorization continues; delegation remains deferred.

[L2 report](results_ls8af_l2_screen/REPORT.md) ·
[Image report and figure](results_ls8ag_images/REPORT.md) ·
[Residual report and figure](results_ls8ah_residuals/REPORT.md) ·
[Frozen residual method](LS8AH_RESIDUAL_NOISE_PROTOCOL.md) ·
[Publication and verification](PUBLICATION_2026-09-22_LS8AF_LS8AH.md).
