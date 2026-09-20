# LS8Q — HD 136352 two-visit DEFAULT-L2 screen

Completed 20 September 2026. Result: **COMPLETE_AUDITED**.

The unchanged symmetric screen evaluated **1,125 table rows** and
**1,923 eligible, overlapping windows**. It retained
**0 positive and 3 negative clusters**.
These are L2 screening outcomes, with no SETI-candidate or detector-qualification claim.

| Visit | Table rows | Eligible windows | Positive / negative windows | Positive / negative clusters |
|---|---:|---:|---:|---:|
| CH_PR100041_TG000901_V0300 | 558 | 960 | 0 / 7 | 0 / 2 |
| CH_PR100041_TG000101_V0300 | 567 | 963 | 0 / 6 | 0 / 1 |

![Retained light curves and all eligible signed scores](hd136352_screen.png)

The upper panels use visit-median normalization only for display. The screen
uses the unchanged local sideband baseline in electron units. Flagged rows are
shown for context and excluded according to the frozen rule. Gaps are not bridged.

## Selection and fixed method

HD 136352 was rank 3 of the metadata-only first-1,000-public-row CHEOPS census:
452 eligible visits and 107 cohorts with at least two eligible visits. It was
selected by the time of its second eligible visit, then first visit and archive
target name. It was not selected for known variability or SETI interest.
LS8J's original discarded full product responses remain a historical limitation;
the separately dated full-inventory reconciliation preserves fresh responses
and verifies unchanged summaries and complete cohort order before this screen.

The public header preflight recorded both exact products, their ETags and
schemas without reading table values. The science freeze is
`0a5957d68ca61d0c7a18da9b2b0ef4e8ed1c6c26`. Both products have TEXPTIME approximately
44.2 seconds (26 coadded exposures of approximately 1.7 seconds each).
Durations are 1–3 stacked rows (approximately 44.2–132.6 seconds),
with 12 sideband rows on each side, two-row guards and endpoints +/-8.5.
The flux-centered local-linear scorer and all eligibility/cluster rules remain
unchanged from LS8K; no thresholds are chosen from these outcomes.

Exactly **155,250 science-table bytes** were acquired.
Image bytes are zero; no alternative aperture, raw imagette or later HD 136352
visit was opened.

## Independent verification and interpretation

Audit status: **PASS**, with
**23,076 numerical and discrete comparisons**
and **0 numerical disagreements**. It independently
decodes big-endian 138-byte rows, enumerates eligible windows, solves scalar
normal equations and checks both signed cluster sets and summary counts.
The unchanged tolerances are relative 2e-8 and absolute 2e-10.

Overlapping windows are not independent statistical trials. The score is not
a calibrated Gaussian significance or a false-alarm probability. This screen
does not establish completeness, sensitivity to short glints, population limits,
or additional qualified observing coverage. A threshold excursion requires
image-level assessment before physical interpretation.

## All fixed cluster representatives

| Visit | Sign | Cluster | Start row (zero-based) | Duration (rows) | Score |
|---|---|---:|---:|---:|---:|
| CH_PR100041_TG000901_V0300 | negative | 0 | 46 | 1 | -13.440986490 |
| CH_PR100041_TG000901_V0300 | negative | 1 | 196 | 1 | -29.560654017 |
| CH_PR100041_TG000101_V0300 | negative | 0 | 432 | 2 | -15.244649337 |

## Next action

Freeze one bounded CAL/COR metadata-and-image diagnostic for every positive and negative representative below. Establish exact exposure joins and byte ranges before image access. Do not select only the strongest positive event.
