# LS8AL — HD 106315 two-visit DEFAULT-L2 screen

Completed 22 September 2026. Result: **COMPLETE_AUDITED**.

The unchanged symmetric screen evaluated **2,382 table rows** and
**4,698 eligible, overlapping windows**. It retained
**3 positive and 0 negative clusters**.
These are L2 screening outcomes, with no SETI-candidate or detector-qualification claim.

| Visit | Table rows | Eligible windows | Positive / negative windows | Positive / negative clusters |
|---|---:|---:|---:|---:|
| CH_PR100041_TG000801_V0300 | 872 | 2,079 | 7 / 0 | 2 / 0 |
| CH_PR100041_TG001401_V0300 | 1,510 | 2,619 | 6 / 0 | 1 / 0 |

![Retained light curves and all eligible signed scores](hd106315_screen.png)

The upper panels use visit-median normalization only for display. The screen
uses the unchanged local sideband baseline in electron units. Flagged rows are
shown for context and excluded according to the frozen rule. Gaps are not bridged.
A null, if obtained, refers only to eligible windows; edge rows or incomplete
contexts can contain changes that this fixed screen cannot test as events.

## Selection and fixed method

HD 106315 was rank 13 of the metadata-only first-1,000-public-row CHEOPS census:
452 eligible visits and 107 cohorts with at least two eligible visits. It was
selected by the time of its second eligible visit, then first visit and archive
target name. It was not selected for known variability or SETI interest.
LS8J's original discarded full product responses remain a historical limitation;
the separately dated full-inventory reconciliation preserves fresh responses
and verifies unchanged summaries and complete cohort order before this screen.

The public header preflight recorded both exact products, their ETags and
schemas without reading table values. The science freeze is
`cb8adaf38d69bba75928cd2572d34b0e6df2b53f`. Both products have NEXP=1. Their verified
TEXPTIME values are 41.0 and
41.0 seconds respectively. Durations
are one/two/three rows (41/82/123 seconds in both visits), with 12 sideband rows on each side, two-row guards
and endpoints +/-8.5. Each visit uses its own verified cadence.
Reserved TESS sectors remain unopened.
The flux-centered local-linear scorer and all eligibility/cluster rules remain
unchanged from LS8K; no thresholds are chosen from these outcomes.

Exactly **328,716 science-table bytes** were acquired.
The separately logged bounded URL-resolution timeout policy does not change
the table requests, source identities or scientific arithmetic.
Image bytes are zero; no alternative aperture, raw imagette or other
visit was opened.

## Independent verification and interpretation

Audit status: **PASS**, with
**56,376 numerical and discrete comparisons**
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
| CH_PR100041_TG000801_V0300 | positive | 0 | 223 | 1 | 44.503884095 |
| CH_PR100041_TG000801_V0300 | positive | 1 | 363 | 1 | 9.691535552 |
| CH_PR100041_TG001401_V0300 | positive | 0 | 178 | 1 | 28.143188663 |

## Next action

Freeze one bounded CAL/COR metadata-and-image diagnostic for every positive and negative representative below. Establish exact exposure joins and byte ranges before image access. Do not select only the strongest positive event.
