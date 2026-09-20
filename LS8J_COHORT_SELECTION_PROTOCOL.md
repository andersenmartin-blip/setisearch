# LS8J — archive-wide CHEOPS metadata-only cohort selection

Status: **FROZEN BEFORE NEW-COHORT SCIENCE VALUES**.

LS8E–LS8I exhausted the previously published ten-host order under its unchanged
two-eligible-visit rule. LS8J starts a new independent CHEOPS cohort without
selecting a target from any prospective light-curve, score or image outcome.

## Frozen population source

Use only the public CHEOPS/DACE visit database and product-name browser.
The target-name authority is the archive's own `obj_id_catname`; no external
astrophysical ranking, SETI plausibility score or prior excursion history is
used to order targets.

Query a bounded chronological census of the **first 1000 public CHEOPS visit
rows** returned in ascending `date_mjd_start` order. Retain the complete raw
metadata result. If the archive API cannot return this exact bounded census,
stop and publish the obstruction rather than substitute a different query.

Exclude systems already used for science-value screening in this optical
sequence: 55 Cnc, GJ 876, GJ 514, GJ 849 and GJ 649, using only normalized
archive target names. Do not exclude a target because of expected variability,
stellar type, planet properties or SETI interest.

## Visit eligibility

Apply the same delivered-product requirements as LS8E–LS8I:

- published/public visit;
- exact V0300 file key;
- PIPE 14.1.2;
- public corrected light curve available;
- finite positive exposure metadata;
- stacked exposure >0 and <=60 seconds;
- exact product inventory contains DEFAULT `SCI_COR_Lightcurve`,
  `SCI_CAL_SubArray` and `SCI_COR_SubArray`.

Product browsing is metadata only; no product download endpoint is permitted.

Group eligible visits by normalized archive `obj_id_catname`. A cohort is
eligible only with at least **two distinct eligible visits**.

## Deterministic ranking

For every eligible cohort, sort its eligible visits by
`(date_mjd_start, file_key)`. Rank cohorts by:

1. MJD start of their **second** eligible visit (the time at which the cohort
   first satisfies the two-visit requirement);
2. MJD start of the first eligible visit;
3. normalized archive target name.

Select rank 1 and choose its two chronologically earliest eligible visits.
This makes the selection a purely metadata/chronology decision.

## Hard boundary and outputs

Save:

- the complete bounded database census;
- every product inventory consulted;
- the complete eligible/ineligible visit ledger and reasons;
- all eligible cohort rankings;
- the mechanically selected target and pair, or an explicit no-selection
  result.

Record and require:

- science product bytes read = 0;
- FITS table rows read = 0;
- light-curve values read = 0;
- image pixels read = 0;
- product download calls = 0.

Only after this metadata result is public may a header-only preflight for the
selected pair be frozen. Do not reuse a closed host or alter the 1000-row
census bound if the result is inconvenient.
