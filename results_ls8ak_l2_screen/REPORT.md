# LS8AK — PG 1343-102 two-visit DEFAULT-L2 screen

Completed 22 September 2026. Result: **COMPLETE_AUDITED**.

The unchanged symmetric screen evaluated **176 table rows** and
**231 eligible, overlapping windows**. It retained
**0 positive and 0 negative clusters**.
These are L2 screening outcomes, with no SETI-candidate or detector-qualification claim.

| Visit | Table rows | Eligible windows | Positive / negative windows | Positive / negative clusters |
|---|---:|---:|---:|---:|
| CH_PR100002_TG008701_V0300 | 86 | 99 | 0 / 0 | 0 / 0 |
| CH_PR100002_TG008702_V0300 | 90 | 132 | 0 / 0 | 0 / 0 |

![Retained light curves and all eligible signed scores](pg1343102_screen.png)

The upper panels use visit-median normalization only for display. The screen
uses the unchanged local sideband baseline in electron units. Flagged rows are
shown for context and excluded according to the frozen rule. Gaps are not bridged.

## Selection and fixed method

PG 1343-102 was rank 12 of the metadata-only first-1,000-public-row CHEOPS census:
452 eligible visits and 107 cohorts with at least two eligible visits. It was
selected by the time of its second eligible visit, then first visit and archive
target name. It was not selected for known variability or SETI interest.
LS8J's original discarded full product responses remain a historical limitation;
the separately dated full-inventory reconciliation preserves fresh responses
and verifies unchanged summaries and complete cohort order before this screen.

The public header preflight recorded both exact products, their ETags and
schemas without reading table values. The science freeze is
`be392f4b2c81ab8536d0e76ae37db618601e0018`. Both products have NEXP=1. Their verified
TEXPTIME values are 60.0 and
60.0 seconds respectively. Durations
are one/two/three rows (60/120/180 seconds in both visits), with 12 sideband rows on each side, two-row guards
and endpoints +/-8.5. Each visit uses its own verified cadence.
Reserved TESS sectors remain unopened.
The flux-centered local-linear scorer and all eligibility/cluster rules remain
unchanged from LS8K; no thresholds are chosen from these outcomes.

Exactly **24,288 science-table bytes** were acquired.
The separately logged bounded URL-resolution timeout policy does not change
the table requests, source identities or scientific arithmetic.
Image bytes are zero; no alternative aperture, raw imagette or other
visit was opened.

## Independent verification and interpretation

Audit status: **PASS**, with
**2,772 numerical and discrete comparisons**
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

Close this two-visit PG 1343-102 screen as a descriptive null. The next independent cohort is rank 13 of the unchanged reconciled LS8J ledger, HD 106315. Freeze its exact pair and header preflight before accessing that cohort. Do not widen or retune the closed PG 1343-102 pair.
