# LS8F — frozen two-visit GJ 514 DEFAULT-L2 screen

Status: **FROZEN BEFORE GJ 514 TABLE VALUES**.

The GJ 514 pair was selected mechanically from the already frozen LS8E
metadata ledger, before GJ 514 science access. Header-only preflight then
established the same 18-field DEFAULT-L2 schema as LS8E, with 138-byte rows,
PIPE 14.1.2 and zero table bytes acquired.

Exact products:

1. `CH_PR100018_TG007501_V0300` — 90 rows, table start 20160,
   table bytes 12420, cadence TEXPTIME=44 s.
2. `CH_PR100018_TG007502_V0300` — 62 rows, table start 20160,
   table bytes 8556, cadence TEXPTIME=44 s.

The saved ETags and Content-Disposition identities in
`results_ls8f_l2_metadata/` are binding.

## Statistic and numerical implementation

Use exactly the same prospective rule frozen for LS8E:

- durations 1, 2 and 3 rows;
- 12-row sideband on each side;
- 2-row guards;
- finite BJD/FLUX/FLUXERR, positive FLUXERR and STATUS=0 across the complete
  context;
- adjacent time steps within 0.5–1.5 times the 44-second cadence;
- sideband-only local linear baseline;
- scale=max(1.4826*MAD, median FLUXERR, 1e-12*absolute median sideband flux,
  1e-12);
- event-sum prediction leverage in the denominator;
- score endpoints **+8.5** and **-8.5**;
- signed overlapping/adjacent windows clustered separately;
- representative by largest signed score, then shortest duration, then
  earliest start.

Use the flux-centered stable OLS implementation
`seti_repeater.cheops_l2_stable.stable_score_window`. This is the same
mathematical rule and numerical implementation frozen before LS8E table access.

## Acquisition and audit

Read only the two declared first-table ranges with `If-Match` using the saved
ETags. Exact permitted new table bytes: **20,976**. No other aperture, visit,
image or raw imagette may be opened.

The independent audit must directly decode the 138-byte big-endian rows and
recompute the centered scalar normal equations, eligibility, signed thresholds,
clusters, representatives, extrema and row unions without importing the
producer scorer. Established numeric tolerances remain 2e-8 relative and
2e-10 absolute.

Publish both visits regardless of outcome. A crossing is only an L2 excursion,
not a candidate or Gaussian significance. Any CAL/COR image follow-up requires
a new predeclared scope after the complete two-visit result is public.

[Selection](LS8F_TARGET_SELECTION.md)
[Header freeze](LS8F_L2_HEADER_PROTOCOL.md)
