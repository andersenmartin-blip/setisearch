# LS8N — GJ 1132 two-visit DEFAULT-L2 screen

Completed 20 September 2026. Result: **COMPLETE_AUDITED**.

The unchanged symmetric screen evaluated **615 table rows** and
**699 eligible, overlapping windows**. It retained
**0 positive and 5 negative clusters**.
These are L2 screening outcomes, with no SETI-candidate or detector-qualification claim.

| Visit | Table rows | Eligible windows | Positive / negative windows | Positive / negative clusters |
|---|---:|---:|---:|---:|
| CH_PR100041_TG000401_V0300 | 301 | 381 | 0 / 1 | 0 / 1 |
| CH_PR100041_TG000403_V0300 | 314 | 318 | 0 / 11 | 0 / 4 |

![Retained light curves and all eligible signed scores](gj1132_screen.png)

The upper panels use visit-median normalization only for display. The screen
uses the unchanged local sideband baseline in electron units. Flagged rows are
shown for context and excluded according to the frozen rule. Gaps are not bridged.

## Selection and fixed method

GJ 1132 was rank 2 of the metadata-only first-1,000-public-row CHEOPS census:
452 eligible visits and 107 cohorts with at least two eligible visits. It was
selected by the time of its second eligible visit, then first visit and archive
target name. It was not selected for known variability or SETI interest.
LS8J's original discarded full product responses remain a historical limitation;
the separately dated full-inventory reconciliation preserves fresh responses
and verifies unchanged summaries and complete cohort order before this screen.

The public header preflight recorded both exact products, their ETags and
schemas without reading table values. The science freeze is
`0bfa962b8456efd82868e69b4cf5f4d7a30a382c`. Both products have TEXPTIME approximately
60 seconds. Durations are 1–3 rows (approximately 60–180 seconds),
with 12 sideband rows on each side, two-row guards and endpoints +/-8.5.
The flux-centered local-linear scorer and all eligibility/cluster rules remain
unchanged from LS8K; no thresholds are chosen from these outcomes.

Exactly **84,870 science-table bytes** were acquired.
Image bytes are zero; no alternative aperture, raw imagette or later GJ 1132
visit was opened.

## Independent verification and interpretation

Audit status: **PASS**, with
**8,388 numerical and discrete comparisons**
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
| CH_PR100041_TG000401_V0300 | negative | 0 | 88 | 3 | -8.529277829 |
| CH_PR100041_TG000403_V0300 | negative | 0 | 69 | 3 | -17.739594988 |
| CH_PR100041_TG000403_V0300 | negative | 1 | 132 | 3 | -9.164247856 |
| CH_PR100041_TG000403_V0300 | negative | 2 | 191 | 3 | -9.124594182 |
| CH_PR100041_TG000403_V0300 | negative | 3 | 297 | 3 | -8.838439333 |

## Next action

Freeze one bounded CAL/COR metadata-and-image diagnostic for every positive and negative representative below. Establish exact exposure joins and byte ranges before image access. Do not select only the strongest positive event.
