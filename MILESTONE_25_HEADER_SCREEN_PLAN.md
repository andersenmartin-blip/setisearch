# Milestone 25 target extension and HDF5-header-only screen

Status: **FIXED BEFORE ANY RANK 21-25 TELESCOPE PRODUCT IS OPENED**.

Milestones 16-24 have now resolved the first twenty unique hosts in the frozen
Milestone 16 low-smearing discovery ranking. Seven qualifying hosts were
searched; the others lacked a complete compatible GBT L-band cadence.
Milestone 25 advances mechanically to the next five unique hosts in that
unchanged public result.

## Frozen extension

| Global rank | Archive target | Planet template | Frozen cadence IDs |
|---:|---|---|---|
| 21 | HIP88348 | HD 164922 b | `-82207`, `-84744` |
| 22 | HIP14954 | HD 19994 b | `-63712`, `-84358` |
| 23 | HIP70950 | HD 127506 b | `-69234`, `-83509` |
| 24 | HIP86620 | psi1 Dra B b | `-80213`, `-84027` |
| 25 | HIP25486 | AF Lep b | `-67639`, `-67651` |

The source is `results_m16_discovery/discovery.json`, whose SHA-256 digest is
`0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`.
Targets are not reranked, and no new planet or telescope catalogue may alter
their order.

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
Milestone 25 stops without spectral contact.

## Boundary after the screen

A selection is only permission to retrieve one official target record and
construct a target-specific 630-case extraction-coverage proof. The exact
search, thresholds, controls, report retention, and stopping rules must be
separately committed before any spectral dataset value is read. Public
artifacts may contain metadata, hashes, validation evidence, and derived
results, but never raw spectral slices.
