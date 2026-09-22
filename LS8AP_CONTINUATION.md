# LS8AO–LS8AP — WASP-103 result and exact continuation

22 September 2026. The rank-14 pair's signed screen and complete image
follow-up are **COMPLETE_AUDITED and closed**. The one positive representative
is **CORRECTION_LINKED** under the unchanged paired-image rule. No residual
study is triggered by this outcome.

## Complete L2 result

Both exact visits independently verify NEXP=1, EXPTIME=TEXPTIME=60 seconds
and pipeline 14.1.2. The unchanged LS8K method uses one/two/three-row events,
12-row sidebands, two-row guards and symmetric +/-8.5 endpoints. Original
finite/positive-error/STATUS=0 requirements apply throughout the required
context; cadence steps must lie within 0.5–1.5 times the verified cadence.
Gaps are not bridged. EVENT remains metadata rather than a new veto.

| Visit | Rows | STATUS=0 finite rows | Eligible windows | Minimum score | Maximum score | Positive / negative crossings | Positive / negative clusters |
|---|---:|---:|---:|---:|---:|---:|---:|
| CH_PR100013_TG000101_V0300 | 269 | 264 | 384 | -5.255496 | +2.796073 | 0 / 0 | 0 / 0 |
| CH_PR100013_TG000102_V0300 | 296 | 291 | 420 | -5.268930 | +13.672258 | 3 / 0 | 1 / 0 |

| Event duration | TG000101 eligible windows | TG000102 eligible windows | Positive / negative crossings across both visits |
|---|---:|---:|---:|
| 1 row(s) / 60 s | 132 | 145 | 1 / 0 |
| 2 row(s) / 120 s | 128 | 140 | 2 / 0 |
| 3 row(s) / 180 s | 124 | 135 | 0 / 0 |

All 565 rows remain retained, including 555 STATUS=0 finite rows. Event
eligibility also requires the complete surrounding context. The three crossing
windows overlap: (start 273, duration 2, score +9.717872910533),
(274, 1, +13.672258341090) and (274, 2, +8.542309834465).
They form one positive cluster; the stronger one-row representative is
TG000102_P0, with the fixed native context **260:289** and event row 274.
Its local-baseline L2 excess is **1.301370855855%**, integrated over 60 seconds.
That exposure duration does not establish the duration of a shorter physical pulse.

The retained-table figure shows large flagged points. The largest are row 201
of TG000101 (flux/visit median 1.264140343592157) and row 185 of TG000102
(3.414630527539594), both STATUS=1. They remain visible and are excluded by
the original context rule. Visit-median normalization is for display, separate
from the local screening baseline. The first visit's null concerns its
384 eligible windows, not every visible variation in every retained row.
No flagged or below-threshold point is substituted for the representative.
Windows overlap and scores are not Gaussian sigma or false-alarm probabilities.

## Complete signed image diagnostic

Both visits' positive and negative cluster lists are verified. Only
CH_PR100013_TG000102_V0300 has a representative, so the first visit has no
image acquisition. All 29 original context rows have unique CAL/COR exposure
joins: **58 joins and 269 exact independent checks**, with <=1 ms MJD/BJD
differences, exact UTC and agreeing exposure counters/integrity before pixels.
Both 296-frame products independently match the L2 60-second exposure tuple,
200x200 unscaled float64 arrays, native ADU units and detector offsets (157,759).

The original finite mask, both C0/C1 conventions, radius-25 apertures and
30–40 background annuli are retained. All 1,970 aperture pixels are valid in
each convention, and COR retains the positive L2 sign. Native image sums are
in ADU; the L2 table is in electrons. No numeric unit equivalence is assumed.

| Convention | CAL residual sum, ADU | COR residual sum, ADU | DELTA=COR-CAL, ADU | DELTA/COR | Column DELTA/COR |
|---|---:|---:|---:|---:|---:|
| C0 | -91089.199543 | 18566.602703 | 109655.802246 | 5.906077919 | 6.087909211 |
| C1 | -91109.008264 | 18534.730879 | 109643.739142 | 5.915583013 | 6.093572065 |

The correction gate is evaluated first. Both DELTA/COR and the column ratios
exceed its original 0.5 magnitude threshold in both conventions. The resulting
label is **CORRECTION_LINKED**: the positive COR event sum is strongly coupled
to the delivered processing difference and has the opposite sign to CAL's
event-residual sum. Negative residual sums do not mean negative total flux.
This is not a unique physical cause, a quantified fraction attributable to
one correction, or proof that source variability is absent.

COR brightness fits explain about 1.141% of unweighted event-map energy;
displacement fits explain 54.840% / 54.853%. The smearing regressions are
rank deficient and unavailable. They are not used to select another label or
assign a particular processing component. The figure shows signed structure
around the source in CAL and COR; the DELTA panel is much less prominent on
the shared full-frame scale. A visually faint distributed difference can still
have a substantial signed aperture sum. Visual inspection changes no mask,
aperture, fit or gate. No hypothetical subtraction or residual study is adopted.

## Verification and publication

The header preflight acquired 20,160 bytes per product within its frozen
64-KiB limit, with no table values or images. The later exact L2 ranges are
20160–57281 (37,122 bytes) and 20160–61007 (40,848 bytes): **77,970 bytes**.
Image metadata acquired **205,392 bytes across two products**, with zero pixels
and the original 20,000,000-byte per-product bound. The separate image freeze
acquired **18,560,000 CAL/COR bytes plus 46,400 smearing bytes** in three ranges.
No alternative aperture, additional visit or raw imagette is included.

All four workflows complete successfully. The five transport tests pass before
headers, the two stable L2 tests before table access and the nine inherited
image tests before pixels. The independent L2 audit passes **9,648 comparisons**
(4,608 + 5,040), with zero disagreements. Relative tolerance stays 2e-8 and
absolute tolerance 2e-10; maximum score difference is 1.7763568394002505e-14.
The metadata audit passes 269 exact checks. The image audit passes **94,537
numerical and 160,581 exact checks**, with zero disagreements under unchanged
relative 2e-8, native absolute 1e-6 and dimensionless absolute 1e-8 tolerances.
All eight archive URL resolutions and all three image ranges succeed on their
first attempts. No archive substitution, science rerun or tolerance change occurs.

Eight scientific commits add **155 files**, changing or removing no earlier
file. **153** match locally recomputed Git identities. The two larger compressed
CAL/COR inputs are public and independently hash-verified and decoded by the
successful image workflow; their identities and the local-copy limitation are
recorded in the publication record. Both complete figures were visually reviewed.
All code, retained inputs, receipts, diagnostics, audits, reports, logs,
environment and checksums are public. No candidate, detector, sensitivity or
qualified observing coverage is established.

## Exact next action

Keep the WASP-103 pair closed under CORRECTION_LINKED. The nine later visits
remain outside it. Prepare **LS8AQ** for **rank-15 GJ 581** in the unchanged
reconciled LS8J chronology:

| Chronological visit | Exact product key | Ledger start MJD | Ledger exposure tuple |
|---|---|---:|---|
| First | CH_PR100011_TG023701_V0300 | 58963.4726309752 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |
| Second | CH_PR100018_TG008301_V0300 | 58973.2698706032 | NEXP=1; EXPTIME=TEXPTIME=60 s; pipeline 14.1.2 |

These are the first two of seven eligible GJ 581 visits; the other five stay
outside the transfer. Science values remain unopened. Freeze the exact keys
and header budget, verify each identity, schema, row count and exposure tuple,
then separately freeze exact DEFAULT-L2 ranges before values. Transfer the
unchanged signed one/two/three-row scorer and independent audit with the
verified cadence (60/120/180 seconds if confirmed). Any image follow-up must
retain every signed representative, verify unique joins and separately freeze
exact image/smearing ranges before pixels. No WASP-103 outcome becomes a new cut.

The original 1,000-row census, 452 eligible visits and 107-cohort ordering
remain fixed. HD 106315 retains all three unresolved labels and its closed
bounded study. TESS_260647166's positive, PG1303-114's negative and
PG 1207-033's positive retain their unresolved labels and closed bounded
studies. EC13080-1508, WASP-43, GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED; PG 1343-102 remains a closed descriptive null. Other closed
optical studies and M33 HD 3651 are unchanged. Reserved TESS/M43 panels stay
closed. Calibration is NOT_READY and its technical request remains unsent.
Standing research/publication authorization continues; delegation is deferred.

[Scientific interpretation and exact continuation](LS8AP_CONTINUATION.md),
[L2 report and figure](results_ls8ao_l2_screen/REPORT.md),
[paired-image report and figure](results_ls8ap_images/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AO_LS8AP.md).
