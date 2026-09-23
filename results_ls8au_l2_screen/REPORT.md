# LS8AU — LS IV +09 2 two-visit DEFAULT-L2 screen

Completed 23 September 2026. Result: **COMPLETE_AUDITED**.

The unchanged symmetric screen evaluated **212 table rows** and
**123 eligible, overlapping windows**. It retained
**0 positive and 0 negative clusters**.
These are L2 screening outcomes, with no SETI-candidate or detector-qualification claim.

| Visit | Table rows | Eligible windows | Positive / negative windows | Positive / negative clusters |
|---|---:|---:|---:|---:|
| CH_PR100002_TG009301_V0300 | 98 | 21 | 0 / 0 | 0 / 0 |
| CH_PR100002_TG009302_V0300 | 114 | 102 | 0 / 0 | 0 / 0 |

![Retained light curves and all eligible signed scores](lsiv092_screen.png)

The upper panels use visit-median normalization only for display. The screen
uses the unchanged local sideband baseline in electron units. Flagged rows are
shown for context and excluded according to the frozen rule. Gaps are not bridged.
A null, if obtained, refers only to eligible windows; edge rows or incomplete
contexts can contain changes that this fixed screen cannot test as events.

## Selection and fixed method

LS IV +09 2 was rank 17 of the metadata-only first-1,000-public-row CHEOPS census:
452 eligible visits and 107 cohorts with at least two eligible visits. It was
selected by the time of its second eligible visit, then first visit and archive
target name. It was not selected for known variability or SETI interest.
LS8J's original discarded full product responses remain a historical limitation;
the separately dated full-inventory reconciliation preserves fresh responses
and verifies unchanged summaries and complete cohort order before this screen.

The public header preflight recorded both exact products, their ETags and
schemas without reading table values. The science freeze is
`469e3fe55365cb84b6dafd14a098ec2edbd37f90`. Both products have NEXP=1. Their verified
TEXPTIME values are 60.0 and
60.0 seconds respectively. Durations
are one/two/three rows (60/120/180 seconds in both visits), with 12 sideband rows on each side, two-row guards
and endpoints +/-8.5. Each visit uses its own verified cadence.
Reserved TESS sectors remain unopened.
The flux-centered local-linear scorer and all eligibility/cluster rules remain
unchanged from LS8K; no thresholds are chosen from these outcomes.

Exactly **29,256 science-table bytes** were acquired.
The separately logged bounded URL-resolution timeout policy does not change
the table requests, source identities or scientific arithmetic.
Image bytes are zero; no alternative aperture, raw imagette or other
visit was opened.

## Independent verification and interpretation

Audit status: **PASS**, with
**1,476 numerical and discrete comparisons**
and **0 numerical disagreements**. It independently
decodes big-endian 138-byte rows, enumerates eligible windows, solves scalar
normal equations and checks both signed cluster sets and summary counts.
The unchanged tolerances are relative 2e-8 and absolute 2e-10.

Overlapping windows are not independent statistical trials. The score is not
a calibrated Gaussian significance or a false-alarm probability. This screen
does not establish completeness, sensitivity to short glints, population limits,
or additional qualified observing coverage. A threshold excursion requires
image-level assessment before physical interpretation.

## Next action

Close this two-visit LS IV +09 2 screen as a descriptive null. The next independent cohort is rank 18 of the unchanged reconciled LS8J ledger, GJ 9404. Freeze its exact pair and header preflight before accessing that cohort. Do not widen or retune the closed LS IV +09 2 pair.
