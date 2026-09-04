# LS3 expanded candidate inventory plan

Status: **PROSPECTIVELY FROZEN; METADATA ONLY; NO SPECTRAL ACCESS OR SIGNAL
SEARCH AUTHORIZED**.

LS3 asks whether there are useful light-sail leakage targets beyond the five
systems screened in LS2. It carries forward the four unresolved LS2 systems
and adds nine nearby systems with at least two reported transiting planets:
AU Mic, HD 136352 (nu2 Lupi), LHS 1140, TOI-270, HD 63433, LP 791-18,
TOI-700, Kepler-444 and K2-3.

The scientific target remains the LS1/LS2 morphology: short broadband excess
power on seconds-to-tens-of-seconds scales, potentially produced by leakage
from a directed interplanetary light-sail propulsion beam. The inventory is
not itself a signal search.

## Frozen procedure

1. Query the NASA Exoplanet Archive `ps` table for the default solution of
   each named host.
2. Retain only confirmed transiting planets with finite positive period and
   semimajor axis plus a finite transit midpoint.
3. Resolve only exact normalized aliases against the public Breakthrough
   Listen target catalogue.
4. For every resolved alias, query the dedicated GBT, cadence-only,
   primary-target view and enumerate its cadence-listing JSON.
5. Advance every system—not merely the first—with at least two geometry-ready
   planets and a cadence containing at least six distinct scan MJDs and six
   medium-resolution `.gpuspec.0002.h5` products.

All advancing systems compete later in a separately frozen header-only phase.
That phase will verify ON/OFF order, frequency coverage, sampling, HTR
availability and conjunction geometry at the actual scan midpoint before any
single target is chosen.

## Data and claim boundary

LS3 may read catalogue JSON, archive-query JSON and cadence-listing JSON. It
must not issue HTTP requests to linked HDF5 or filterbank URLs, inspect HDF5
structure, or read spectral values. It cannot authorize a signal search or
support a technosignature, sensitivity, occurrence-rate or general light-sail
claim.

The machine-readable frozen protocol is
`config/ls3_expanded_candidate_inventory.json`.
