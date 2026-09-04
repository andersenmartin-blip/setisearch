# LS2 plan: candidate-system and public-archive inventory

## Scientific question

LS2 asks which of the predeclared nearby multi-transiting systems has both the
ephemeris metadata and public radio cadence metadata needed for a second,
conjunction-conditioned light-sail leakage analysis. It is a metadata-only
selection milestone and is not itself a signal search.

The frozen priority order is:

1. LTT 1445 A
2. L 98-59
3. HD 260655
4. GJ 9827
5. TRAPPIST-1

These systems extend LS1 beyond HD 219134 while retaining the motivating
features of the Guillochon--Loeb scenario: nearby systems, multiple transiting
planets, and planet-pair geometries that can be ranked at actual observation
times.

## Prospective boundary

The target order, aliases, API endpoints, ephemeris fields, retention limits,
eligibility rule and output schema are committed before the LS2 inventory is
executed. LS2 may read only:

- NASA Exoplanet Archive JSON for default planet solutions;
- the Breakthrough Listen public target list and file-listing JSON; and
- public cadence-listing JSON linked by those records.

LS2 must not open a linked HDF5 or filterbank product. It reads no spectral
dataset value and evaluates no signal statistic. Archive URLs may be catalogued
as metadata, but the linked payloads remain closed.

## Geometry gate

A system is geometry-ready only if at least two planets are flagged as
transiting and each has a finite positive orbital period, a finite transit
midpoint and a finite positive semimajor axis in the current default NASA
solution. All adjacent planet pairs ordered by semimajor axis are retained.
LS2 does not choose a pair or propagate a conjunction yet; those choices depend
on the observation times verified by the next header-only milestone.

This remains an approximate planning geometry. Unknown mutual nodes,
eccentricity assumptions and ephemeris propagation uncertainty must be carried
into any later cadence ranking.

## Archive gate and selection

Archive target names are accepted only when they exactly match a predeclared
alias after case, whitespace and punctuation normalization. Substring and
coordinate matching are forbidden in this milestone.

In priority order, the first geometry-ready system with a public cadence
listing containing at least six distinct scan MJDs and a
`gpuspec.0002.h5` medium-resolution product becomes eligible for a separately
frozen HDF5-header-only preflight. This gate is intentionally provisional: API
file listings cannot prove source alternation, compatible scan geometry,
frequency coverage or byte-range access.

Selection in LS2 authorizes only that later header preflight. It does not
authorize spectral access or an LS2 signal search.

## Next decision

- If a target passes both gates, freeze and run a header-only preflight for all
  of its listed cadences, then rank qualifying cadences over all adjacent
  planet pairs using the LS1 projected-separation model with explicit
  ephemeris-uncertainty diagnostics.
- If no target passes, close LS2 as a technical no-selection and leave all
  spectral products unopened. The weekly monitor can reopen the opportunity
  only through a new, separately documented inventory version.

## Claim boundary

LS2 cannot support a technosignature, null, sensitivity, false-alarm or
occurrence-rate claim. A future signal search must separately freeze its target,
cadence, band, broadband templates, ON/OFF vetoes, retention limits and
high-time-resolution follow-up rule before reading spectral values.
