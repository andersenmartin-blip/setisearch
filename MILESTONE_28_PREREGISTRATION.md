# Milestone 28 preregistration: psi1 Dra B b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`a0c118cf0589d1edd23b550574dd22a5cfad1f8db9a3d5507aa4437085b16e79`.

## Purpose and boundary

Milestone 28 is a new held-out application of detector v0.5.0. The target is
**psi1 Dra B / HIP 86620**, with psi1 Dra B b used only as the motion template.
The primary data are its sole complete compatible GBT L-band alternating
ON/control cadence, archive cadence `--84027`, beginning 2016-01-18 19:36:33
UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and calculated extraction geometry were read. No psi1 Dra B HDF5 `data` value
was indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header qualification rule were committed before ranks
21-25 were opened. psi1 Dra B at rank 24 is the next compatible host after
ranks 21-23 completed in Milestones 25-27. Its other cadence, `--80213`, is
S-band. Rank 25 has no compatible cadence.

Selection provenance is in `MILESTONE_28_TARGET_SELECTION.md`. The official
metadata query is GitHub Actions run `32751708237`, artifact `9529259712`,
digest
`sha256:72cbb486aeb0940f01f69ce284035077ebba75ca29ad2ffe68976a02be05c1e4`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP86620 | 57405.817048611110 | 16 | 287.779586048 |
| 2 | control | HIP86620_OFF | 57405.820879629630 | 16 | 287.779586048 |
| 3 | ON | HIP86620 | 57405.824710648150 | 16 | 287.779586048 |
| 4 | control | HIP86620_OFF | 57405.828541666670 | 16 | 287.779586048 |
| 5 | ON | HIP86620 | 57405.832372685190 | 16 | 287.779586048 |
| 6 | control | HIP86620_OFF | 57405.836203703700 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 264503296]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1126.464846586 to
1876.464843750 MHz. Identities, sizes, ETags, sources, times, and geometry are
frozen in `config/psi1drabb_heldout_m28.json`.

## Mandatory extraction-coverage proof

`scripts/m14_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows. All **630**
checks passed without opening a remote file. The smallest edge headroom is
263,566 channels, approximately 747.342 kHz.

The proof is run `32752075221`, artifact `9529413195`, verified digest
`sha256:ec73f089308e75680d52a57e96f525e280b3b0e8da0016c868cd8c36f0f7893b`.
The result SHA-256 is
`0a67dbd2cad1b40b23bb965a4e0f7161f014f49de862306dcc33a55405e32fc2`.

## Target and orbital template

The official composite record supplies RA 17h41m58.22s, Dec +72d09m20.56s,
parallax 43.9875 mas, proper motion (+33.7856, -275.856) mas/yr, and radial
velocity -11.0 km/s. The psi1 Dra B b working orbit has period 3117 days,
semimajor axis 4.43 au, eccentricity 0.4, periastron epoch BJD 2449344, and
longitude of periastron 64 degrees. Its conservative full-projection
periastron drift proxy is 0.00476299 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, clustering, v0.5 OFF/receiver vetoes, 256 complete scrambles,
and the completeness grid are unchanged. Fixed seeds are `2820260824` for
scrambles and `282120260824` for completeness. The 1200-cluster report cap
exceeds the finite maximum of 1008 retained peaks per window and therefore
cannot truncate the complete disposition record.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m28_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m28_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m28_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m28_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m28_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, seeds, completeness, and report retention
may not change in response to data. A cluster above the empirical global
threshold survives only if none of the frozen matched-control,
single-adjacent-control, local-control, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 28 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying psi1 Dra B L-band cadence exists in the frozen screen, so
this milestone cannot perform or claim independent recurrence. Any conclusion
is limited to the frozen scope and measured completeness.
