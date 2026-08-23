# Milestone 21 target extension and HDF5-header-only screen

Status: **FIXED BEFORE ANY RANK 11-15 TELESCOPE PRODUCT IS OPENED**.

Milestones 16-20 resolved the first ten unique hosts in the frozen Milestone
16 low-smearing discovery ranking. Five qualifying hosts were searched and the
remaining five were technically ineligible for the established GBT L-band
search. Milestone 21 now advances mechanically to the next five unique hosts
in that unchanged public result.

## Frozen extension

| Global rank | Archive target | Planet template | Frozen cadence IDs |
|---:|---|---|---|
| 11 | HIP79248 | HD 145675 c | `-78733` |
| 12 | HIP83389 | HD 154345 b | `-85132` |
| 13 | HIP49699 | HD 87883 b | `-70933`, `-78853` |
| 14 | HIP113421 | HD 217107 c | `-69190` |
| 15 | HIP9884 | alf Ari b | `-82737` |

The source is `results_m16_discovery/discovery.json`, whose SHA-256 digest is
`0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`.
The targets are not reranked, and no new planet or telescope catalogue is used
to alter their order.

## Qualification and selection rule

This stage may read public catalogue records, HTTP object identity, HDF5
attributes, dataset geometry, timing, and frequency coverage. It may not index
or read any HDF5 `data` value.

A cadence qualifies only if all six current fine HDF5 products:

- form a time-ordered three-ON/three-OFF alternating sequence within 0.04 day;
- have compatible shape, dtype, integration time, and channel width;
- respond without header errors and support HTTP byte ranges; and
- cover 1399.65-1425.85 MHz, containing all five established one-megahertz
  search windows and their guards.

The first host in frozen rank order with at least one qualifying cadence is
selected. If it has several, its earliest qualifying cadence is selected as
the blind primary search; later qualifying cadences remain spectrally
untouched and may only be used under a separately frozen recurrence rule. All
five hosts are screened so the complete technical outcome is preserved. If
none qualifies, Milestone 21 stops without spectral contact.

## Boundary after the screen

A selection is only permission to retrieve an official target record and
construct a target-specific 630-case extraction-coverage proof. The exact
search, thresholds, controls, and stopping rules must be separately committed
before any spectral dataset value is read. Public artifacts may contain
metadata, hashes, validation evidence, and derived results, but never raw
spectral slices.
