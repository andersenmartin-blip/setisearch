# Milestone 19 target extension and HDF5-header-only screen

Status: **FIXED BEFORE ANY RANK 6-10 TELESCOPE PRODUCT IS OPENED**.

Milestones 16-18 resolved the first five unique hosts in the frozen Milestone
16 low-smearing discovery ranking: ranks 1 and 3 were technically ineligible,
while ranks 2, 4, and 5 were searched. Milestone 19 now advances mechanically
to the next five unique hosts in that unchanged public result.

## Frozen extension

| Global rank | Archive target | Planet template | Frozen cadence IDs |
|---:|---|---|---|
| 6 | HIP79755 | HD 147379 b | `-77605` |
| 7 | HIP43587 | 55 Cnc d | `-64578`, `-69774` |
| 8 | HIP53721 | 47 UMa d | `-73992` |
| 9 | HIP32769 | HD 48948 d | `-83329` |
| 10 | HIP78459 | rho CrB c | `-71771` |

The source is `results_m16_discovery/discovery.json`, whose SHA-256 digest is
`0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`.
The five targets are not reranked and no new planet or telescope catalogue is
used to alter their order.

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
selected. If it has several, its earliest qualifying cadence is selected. All
five hosts are still screened so the complete technical outcome is preserved.
If none qualifies, Milestone 19 stops without spectral contact.

## Boundary after the screen

A selection is only permission to retrieve an official target record and
construct a target-specific 630-case extraction-coverage proof. The exact
search, thresholds, controls, and stopping rules must be separately committed
before any spectral dataset value is read. Public artifacts may contain
metadata, hashes, validation evidence, and derived results, but never raw
spectral slices.
