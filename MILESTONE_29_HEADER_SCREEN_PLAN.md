# Milestone 29 target extension and HDF5-header-only screen

Status: **FIXED BEFORE ANY RANK 26-30 TELESCOPE PRODUCT IS OPENED**.

Milestones 16-28 have resolved the first twenty-five unique hosts in the
frozen Milestone 16 low-smearing discovery ranking. Eleven qualifying hosts
were searched; the other fourteen lacked a complete compatible GBT L-band
cadence. Milestone 29 advances mechanically to the final five unique hosts in
that unchanged public result.

## Frozen extension

| Global rank | Archive target | Planet template | Frozen cadence IDs |
|---:|---|---|---|
| 26 | HIP90979 | BD-11 4672 b | `-67873` |
| 27 | HIP21547 | 51 Eri b | `-81141` |
| 28 | HIP9094 | HD 11964 b | `-66653` |
| 29 | HIP72607 | bet UMi b | `-74586`, `-77497` |
| 30 | HIP1692 | HD 1690 b | `-77897` |

The source is `results_m16_discovery/discovery.json`, whose SHA-256 digest is
`0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`.
Targets are not reranked, and no new planet or telescope catalogue may alter
their order. Rank 30 is the last unique host below the frozen 1 Hz/s
acceleration-smearing bound.

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
selected. If it has several, its earliest qualifying cadence becomes the blind
primary search; later qualifying cadences remain spectrally untouched and may
only be used under a separately frozen recurrence rule. All five hosts are
screened so the complete technical outcome is preserved. If none qualifies,
Milestone 29 stops without spectral contact.

## Boundary after the screen

A selection is only permission to retrieve one official target record and
construct a target-specific 630-case extraction-coverage proof. The exact
search, thresholds, controls, report retention, and stopping rules must be
separately committed before any spectral dataset value is read. Public
artifacts may contain metadata, hashes, validation evidence, and derived
results, but never raw spectral slices.
