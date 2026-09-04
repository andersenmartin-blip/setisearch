# LS2B plan: dedicated cadence-view discovery

## Trigger

The completed LS2 inventory found no `cadence_url` values in ordinary target
queries, but it exposed two concrete radio-data opportunities:

- HD 260655 (`HIP31635`) has three L-band and three S-band GBT ON scans with
  medium-resolution `.0002` products and corresponding high-time-resolution
  products.
- GJ 9827 (`HIP115752`) has one S-band GBT ON scan with both product classes.

This follow-up is conditioned only on that published metadata. It does not
revise or overwrite LS2's technical no-selection result.

## Frozen query

For the two LS2-resolved aliases, query the same public Breakthrough Listen
file API with the explicit parameters `telescope=GBT`, `cadence=True` and
`primaryTarget=True`. Inspect every returned cadence-listing JSON up to the
frozen retention cap.

LS2B may read API JSON only. Linked HDF5/filterbank URLs remain closed; no
headers or spectral dataset values may be read.

## Selection rule

Preserve the original LS2 priority, so HD 260655 precedes GJ 9827. A cadence is
eligible only if its listing has at least six distinct scan MJDs and at least
six medium-resolution `gpuspec.0002.h5` products. Within the first eligible
system, select the earliest cadence, breaking ties by URL.

This conservative gate is intended to locate a possible six-scan sequence. It
does not yet prove ABACAD source alternation, compatible scan dimensions,
frequency coverage, byte-range access, or conjunction quality.

## Next decision

An eligible cadence may proceed only to a separately frozen HDF5-header-only
preflight. That later step must verify ON/OFF ordering, exact observation times,
sampling, band coverage and all adjacent planet-pair conjunction scores before
any spectral access is authorized.

If no cadence passes, LS2B closes without opening radio data and the weekly
archive monitor remains the route for detecting a new opportunity.

## Claim boundary

LS2B is an archive-discovery result, not a signal search. It cannot support a
technosignature, null, sensitivity, false-alarm or occurrence-rate claim.
