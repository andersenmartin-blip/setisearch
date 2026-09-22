# LS8AC–LS8AE — PG1303-114 complete result and exact continuation

22 September 2026. The predetermined rank-9 pair and its single bounded
retained-data follow-up are **complete and closed**. No positive L2 threshold
crossing was found. The negative TG006402_N0 retains
**UNRESOLVED_WITHIN_FIXED_SCOPE**; no qualified SETI candidate, detector,
sensitivity or observing coverage is added.

## Complete prospective L2 result

Both visits have verified NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2. The unchanged signed screen uses 60/120/180-second events, 12-row
sidebands, two-row guards, original eligibility and symmetric +/-8.5 endpoints.

| Visit | Rows | Eligible overlapping windows | Minimum score | Maximum score | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR100002_TG006401_V0300 | 78 | 63 | -4.338240 | +4.219964 | 0 / 0 |
| CH_PR100002_TG006402_V0300 | 87 | 159 | -10.531571 | +2.624740 | 0 / 1 |
| Total | 165 | 222 | — | — | 0 / 1 |

Two negative threshold crossings form one cluster. Its original representative
is zero-based row 21, one 60-second exposure, score **-10.531570808271077**,
approximately **3.00335% below** its local L2 baseline. The two-row member at
row 20 has score -9.277026148235445. Every eligible window and both complete
signed cluster sets are retained. Scores are not Gaussian significances and
overlapping windows are not independent trials.

Exactly **22,770 table bytes** were acquired after a separate public science
freeze. The first visit has no triggered image follow-up.

## Fixed paired-image diagnostic

The complete signed representative set was frozen before image metadata.
All 29 L2 context rows 7:36 have unique CAL/COR exposure matches:
58 joins, <=1 ms MJD/BJD differences, exact UTC and agreeing exposure
counters/integrity. A separate payload freeze fixed **18,560,000 image bytes
and 46,400 smearing bytes**. CAL/COR are native ADU products; their sums are
not directly compared as equal units with L2 electron fluxes.

| Quantity | C0 | C1 |
|---|---:|---:|
| CAL residual aperture sum [ADU] | -7,636.281 | -7,376.196 |
| COR residual aperture sum [ADU] | -10,983.862 | -10,721.399 |
| DELTA=COR-CAL aperture sum [ADU] | -3,347.581 | -3,345.203 |
| DELTA / COR | 0.304773 | 0.312012 |
| Column-projected DELTA / COR | 0.280911 | 0.285973 |
| COR brightness explained energy | 2.97072% | 2.83196% |
| COR displacement explained energy | 58.94296% | 58.67740% |

Both original apertures are complete and retain the negative L2 sign.
Neither correction ratio meets the 0.5 requirement; displacement explained
energy stays below 80% in both conventions. The unchanged outcome is
**UNRESOLVED_WITHIN_FIXED_SCOPE**. Rank-deficient smearing fits remain
unavailable. No aperture, coordinate convention, threshold or label is changed.

## Single retained-data residual/noise study

LS8AE prospectively fixed one transfer of the existing LS8U duration-aware
method to this one 60-second context. It reused the saved cubes without new
archive bytes. Both products and both conventions are retained: four native
cases, 96 duration-matched held cases and 64 signed signal controls.

The fixed weighted combined model leaves the following COR residuals:

| Quantity | C0 | C1 |
|---|---:|---:|
| Residual/reference energy, correlated model | 0.878666 | 0.876726 |
| Residual/reference energy, IID model | 0.903129 | 0.901111 |
| Held single-row controls at least as large | 20/24 | 19/24 |
| Correlated/IID variance factor | 1.027841 | 1.027814 |
| Top ten pixels' share of weighted residual energy | 5.28021% | 5.23821% |
| Hypothetical displacement-subtraction brightness flux loss | 38.23385% | 38.17069% |

The residual is not unusually large relative to this fixed local comparison.
These few dependent controls and modeled energy ratios are not calibrated
probabilities. A ratio below one does not prove ordinary noise, identify a
physical cause or justify relabeling the event. The original negative stays
unresolved under LS8AD; its bounded follow-up is nonetheless closed.

Temporal covariance raises estimated event variance by about 2.78%.
The hypothetical gradients-plus-constant subtraction loses about 38.2% of
injected COR brightness flux. It is not adopted as a correction or veto.
Both injection signs pass the unchanged coefficient and linearity requirements.

Exact C0/C1 boundary accounting gives COR aperture-sum difference
+262.463394 ADU and DELTA difference +2.377580 ADU, fully retained with signed
boundary pixels. The paired residual decomposition keeps its negative cross
term; its parts are not independent physical-cause fractions. No new masks,
cuts, extra pixels or visits follow from these descriptive findings.

## Verification and publication

All five workflows succeed at their recorded public freezes. The five
transport tests, two L2 tests, nine image tests and 18 residual tests pass.
The independent L2 audit passes **2,664 comparisons**. Before pixels, the
image metadata audit passes **58 unique joins and 269 exact checks**.
The image audit passes **94,537 numerical and 160,581 exact checks**;
the retained-data audit passes **305,356 numerical and 320,126 exact checks**.
No disagreement or scientific rerun occurs. All three figures were visually
inspected.

The ten scientific commits add **180 files**, changing no earlier file.
Exactly 178 are additionally verified against local Git blob identities.
All 28 header, 22 L2, 57 image-metadata and 18 residual manifest entries are
locally SHA256-verified. Of 22 image-result entries, 20 are locally verified.
The two larger compressed CAL/COR cubes remain verified by the successful
image and residual workflows, including raw/compressed digests and independent
decoding; they were not additionally copied locally. Exact identities and
verification scope are in the publication record.

## Exact next action

Keep the PG1303-114 pair closed, including its three later eligible visits.
Prepare **LS8AF**, the next independent metadata-first transfer to
**rank-10 PG 1207-033** in the unchanged reconciled LS8J chronology:

| Chronological visit | Exact product key | Ledger start MJD | Existing exposure tuple |
|---|---|---:|---|
| First | CH_PR100002_TG000901_V0300 | 58957.7949015956 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100002_TG000902_V0300 | 58968.5942060594 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are the cohort's only two eligible visits. Verify the ledger exposure
values against their own headers. First freeze the exact pair and header-only
budget; verify identities, schema, row counts and exposures. Only after a
passing public result freeze exact DEFAULT-L2 ranges and transfer the
unchanged signed screen and independent audit. Its science values remain
unopened. Any triggered images need the complete signed representative set,
unique exposure joins and a separate exact payload freeze.

Do not adopt LS8AE residual ranks, covariance ratios, concentrations or signal
losses as new screening cuts. The original 1,000-row census, 452 eligible visits
and 107-cohort chronology remain unchanged. The prior TESS_260647166 positive
remains unresolved and its bounded study closed. WASP-43, PG 1245-042, GJ 436
and other closed studies are unchanged. Reserved TESS/M43 panels stay closed.
Calibration remains NOT_READY and its technical request unsent. Standing
research/publication authorization continues; delegation remains deferred.

[L2 report](results_ls8ac_l2_screen/REPORT.md) ·
[Image report](results_ls8ad_images/REPORT.md) ·
[Residual report and figure](results_ls8ae_residuals/REPORT.md) ·
[Frozen residual method](LS8AE_RESIDUAL_NOISE_PROTOCOL.md) ·
[Publication and verification](PUBLICATION_2026-09-22_LS8AC_LS8AE.md).
