# LS8G — frozen two-visit GJ 849 DEFAULT-L2 screen

Status: **FROZEN BEFORE GJ 849 TABLE VALUES**.

The GJ 849 pair was selected mechanically from the host order fixed before
LS8E science access. Header-only preflight then established a compatible
18-field DEFAULT-L2 schema with 138-byte rows, PIPE 14.1.2 and zero table-data
bytes acquired.

Exact products:

1. `CH_PR100018_TG032401_V0300` — 127 rows, table start 20160,
   table bytes 17526, cadence TEXPTIME=42 s.
2. `CH_PR100018_TG032402_V0300` — 83 rows, table start 20160,
   table bytes 11454, cadence TEXPTIME=42 s.

The saved ETags and Content-Disposition identities in
`results_ls8g_l2_metadata/` are binding.

## Statistic and numerical implementation

Use exactly the same prospective rule frozen for LS8E and LS8F:

- durations 1, 2 and 3 rows;
- 12-row sideband on each side;
- 2-row guards;
- finite BJD/FLUX/FLUXERR, positive FLUXERR and STATUS=0 across the complete
  context;
- adjacent time steps within 0.5–1.5 times the 42-second cadence;
- sideband-only local linear baseline;
- scale=max(1.4826*MAD, median FLUXERR, 1e-12*absolute median sideband flux,
  1e-12);
- event-sum prediction leverage in the denominator;
- score endpoints **+8.5** and **-8.5**;
- signed overlapping/adjacent windows clustered separately;
- representative by largest signed score, then shortest duration, then
  earliest start.

Use `seti_repeater.cheops_l2_stable.stable_score_window`. No threshold,
aperture, duration, context or numerical rule is selected from GJ 849 values.

## Acquisition and audit

Read only the two declared first-table ranges with `If-Match` using the saved
ETags. Exact permitted new science-table bytes: **28,980**. No other aperture,
visit, image or raw imagette may be opened.

The independent audit must directly decode the 138-byte big-endian rows and
recompute the centered scalar normal equations, eligibility, signed thresholds,
clusters, representatives, extrema and row unions without importing the
producer scorer. Established tolerances remain 2e-8 relative and 2e-10
absolute. A visit with zero eligible windows is a valid frozen outcome and
must remain zero rather than trigger a rule change.

Publish both visits regardless of outcome. A crossing is only an L2 excursion,
not a SETI candidate or Gaussian significance. Any CAL/COR image follow-up
requires a new predeclared scope after the complete two-visit result is public.

[Selection](LS8G_SELECTION_FREEZE.md)
[Header freeze](LS8G_L2_HEADER_PROTOCOL.md)
