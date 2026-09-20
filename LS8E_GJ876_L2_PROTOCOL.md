# LS8E — frozen two-visit GJ 876 DEFAULT-L2 screen

Status: **FROZEN BEFORE GJ 876 TABLE VALUES**.

The LS8E metadata selection chose GJ 876 and the two chronologically earliest
eligible visits without reading science-product bytes. The subsequent header
preflight found a common 18-field DEFAULT-L2 schema, 138-byte rows, PIPE 14.1.2,
NEXP=14 and TEXPTIME=42 s in both products, again with zero table-data bytes.

Exact evaluation products:

1. `CH_PR100018_TG032801_V0300` — 115 rows, table bytes 15870,
   table start 20160.
2. `CH_PR100018_TG032802_V0300` — 112 rows, table bytes 15456,
   table start 20160.

The saved ETags and Content-Disposition values in
`results_ls8e_l2_metadata/` are binding. No substitute visit is allowed.

## Frozen statistic

Reuse the LS7X/LS8A/LS8B DEFAULT-aperture cadence-unit method unchanged:

- event durations: **1, 2, 3 rows**;
- sidebands: **12 rows on each side**;
- guard interval: **2 rows on each side**;
- require finite BJD/FLUX/FLUXERR, positive FLUXERR and STATUS=0 through the
  complete event+guard+sideband context;
- require every adjacent time step in context to be 0.5–1.5 times the
  visit's 42-second cadence;
- fit a sideband-only local linear baseline in time;
- noise scale is max(1.4826*MAD, median FLUXERR, 1e-12*absolute median
  sideband flux, 1e-12);
- include the event-sum baseline-prediction leverage in the denominator;
- positive endpoint: score >= **+8.5**;
- symmetric negative-control endpoint: score <= **-8.5**;
- cluster overlapping/adjacent signed threshold windows separately by sign;
- representative is greatest signed score, then shortest duration, then
  earliest start.

Scores are screening statistics, **not Gaussian significances**. Overlapping
windows are not independent trials.

## Prospective numerical implementation

Use `seti_repeater.cheops_l2_stable.stable_score_window`, which applies the
same OLS/statistic after subtracting the sideband median flux before the normal
equations. This is the numerical repair already verified retrospectively on
closed LS8B data against a high-precision Decimal reference, where it changed
zero signed +/-8.5 decisions.

This choice is made **before any GJ 876 table byte is read**. The original
uncentered LS8B implementation and its audit FAIL remain historical evidence
and are not rewritten.

## Acquisition boundary

For each exact selected DEFAULT product, acquire only the declared first-table
range using the saved ETag with `If-Match`. Require HTTP 206, exact
Content-Range, Content-Length, ETag and Content-Disposition. Do not read another
extension, aperture or visit.

Total permitted new science-table bytes are exactly **31,326 bytes**
(15,870 + 15,456). Image bytes permitted in this stage: **0**.

## Independent audit and stopping rule

An independent auditor must:

- decode all rows directly with a fixed big-endian 138-byte struct;
- re-enumerate every attempted and eligible 1/2/3-row window;
- recompute the flux-centered scalar normal equations without importing the
  producer scorer;
- compare score, excess, sigma and denominator at the established
  2e-8 relative / 2e-10 absolute tolerances;
- verify eligibility, event/context indices and bitwise EVENT values;
- independently reconstruct positive and negative clusters, representatives,
  per-duration counts, extrema and event-row unions;
- verify source receipts and the frozen header identities.

Publish both visits even if one has no threshold crossing or unfavorable
controls. Audit failure is a result; do not replace a visit or retune.

Any signed crossing is an **L2 excursion only**. No candidate claim follows.
A positive excursion may receive CAL/COR image follow-up only under a new
predeclared byte/range/diagnostic scope after this complete two-visit result is
published. No raw imagette access is authorized here.

[Selection](results_ls8e_selection/REPORT.md)
[Header preflight](LS8E_L2_HEADER_PROTOCOL.md)
