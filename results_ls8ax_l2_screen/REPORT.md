# LS8AX — GJ 536 two-visit DEFAULT-L2 screen

Completed 23 September 2026. Result: **COMPLETE_AUDITED**.

The unchanged symmetric screen evaluated **4,254 table rows** and
**10,215 eligible, overlapping windows**. It retained
**8 positive and 1 negative clusters**.
These are L2 screening outcomes, with no SETI-candidate or detector-qualification claim.

| Visit | Table rows | Eligible windows | Positive / negative windows | Positive / negative clusters |
|---|---:|---:|---:|---:|
| CH_PR100011_TG023501_V0300 | 4,133 | 10,032 | 32 / 5 | 7 / 1 |
| CH_PR100018_TG007801_V0300 | 121 | 183 | 6 / 0 | 1 / 0 |

![Retained light curves and all eligible signed scores](gj536_screen.png)

The upper panels use visit-median normalization only for display. The screen
uses the unchanged local sideband baseline in electron units. Flagged rows are
shown for context and excluded according to the frozen rule. Gaps are not bridged.
A null, if obtained, refers only to eligible windows; edge rows or incomplete
contexts can contain changes that this fixed screen cannot test as events.

## Selection and fixed method

GJ 536 was rank 20 of the metadata-only first-1,000-public-row CHEOPS census:
452 eligible visits and 107 cohorts with at least two eligible visits. It was
selected by the time of its second eligible visit, then first visit and archive
target name. It was not selected for known variability or SETI interest.
LS8J's original discarded full product responses remain a historical limitation;
the separately dated full-inventory reconciliation preserves fresh responses
and verifies unchanged summaries and complete cohort order before this screen.

The public header preflight recorded both exact products, their ETags and
schemas without reading table values. The science freeze is
`2d7eaf36c801f52bfc0d247b40adeba601660e74`. Both products have NEXP=1. Their verified
TEXPTIME values are 40.1699981689453 and
40.2000007629395 seconds respectively. Durations
are one/two/three rows (CH_PR100011_TG023501_V0300: 40.169998/80.339996/120.50999 seconds; CH_PR100018_TG007801_V0300: 40.200001/80.400002/120.6 seconds), with 12 sideband rows on each side, two-row guards
and endpoints +/-8.5. Each visit uses its own verified cadence.
Reserved TESS sectors remain unopened.
The flux-centered local-linear scorer and all eligibility/cluster rules remain
unchanged from LS8K; no thresholds are chosen from these outcomes.

Exactly **587,052 science-table bytes** were acquired.
The separately logged bounded URL-resolution timeout policy does not change
the table requests, source identities or scientific arithmetic.
Image bytes are zero; no alternative aperture, raw imagette or other
visit was opened.

## Independent verification and interpretation

Audit status: **PASS**, with
**122,580 numerical and discrete comparisons**
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
| CH_PR100011_TG023501_V0300 | positive | 0 | 1816 | 1 | 18.968233631 |
| CH_PR100011_TG023501_V0300 | positive | 1 | 1849 | 1 | 9.877824202 |
| CH_PR100011_TG023501_V0300 | positive | 2 | 2573 | 1 | 13.572894444 |
| CH_PR100011_TG023501_V0300 | positive | 3 | 2770 | 1 | 31.864099485 |
| CH_PR100011_TG023501_V0300 | positive | 4 | 3082 | 1 | 20.039903364 |
| CH_PR100011_TG023501_V0300 | positive | 5 | 3323 | 1 | 15.723832565 |
| CH_PR100011_TG023501_V0300 | positive | 6 | 3408 | 1 | 2923.687794815 |
| CH_PR100011_TG023501_V0300 | negative | 0 | 802 | 1 | -14.861686434 |
| CH_PR100018_TG007801_V0300 | positive | 0 | 17 | 1 | 47.629871839 |

## Next action

Freeze one bounded CAL/COR metadata-and-image diagnostic for every positive and negative representative below. Establish exact exposure joins and byte ranges before image access. Do not select only the strongest positive event.
