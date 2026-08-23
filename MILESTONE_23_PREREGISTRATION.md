# Milestone 23 preregistration: HD 33564 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`c36f73c812d4d863e059979573775aac20ef5a2ec38aafc30b9c2abe2629edf7`.

## Purpose and boundary

Milestone 23 is a new held-out application of detector v0.5.0. The target is
**HD 33564 / HIP 25110**, with HD 33564 b used only as the motion template.
The primary data are the earliest of its two complete compatible GBT L-band
alternating ON/OFF cadences, beginning 2016-05-18 18:10:05 UTC, archive
cadence `--71505`.

Before this commit, only catalogue records, official orbit/host metadata, HTTP
object identities, HDF5 attributes and geometry, timestamps, and locally
calculated extraction geometry were read. No HD 33564 HDF5 `data` value was
indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header-screen rule were published before ranks 16-20 were
opened. Rank 16, BD-06 1339, is technically ineligible because its complete
fine cadence is S-band. HD 33564 at rank 17 has two complete L-band cadences,
so it advances mechanically and its earliest qualifying cadence is the blind
primary search.

Selection provenance is preserved in `MILESTONE_23_TARGET_SELECTION.md`. The
official metadata query is GitHub Actions run `32648986429`, artifact
`9495643442`, digest
`sha256:5d5e75b5062a5b68069e6aa64fb6805ff1dce91b9468848c4331acc789eef01b`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP25110 | 57526.757002314815 | 16 | 287.779586048 |
| 2 | OFF | HIP24440 | 57526.760914351850 | 16 | 287.779586048 |
| 3 | ON | HIP25110 | 57526.764803240740 | 16 | 287.779586048 |
| 4 | OFF | HIP25714 | 57526.768599537034 | 16 | 287.779586048 |
| 5 | ON | HIP25110 | 57526.772395833330 | 16 | 287.779586048 |
| 6 | OFF | HIP26097 | 57526.776273148150 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 318230528]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1023.925784086 to
1926.269531250 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/hd33564b_heldout_m23.json`.

## Reserved independent cadence

Cadence `--71747`, beginning 2016-05-24 18:34:10 UTC, is a second complete
L-band A-B-A-C-A-D observation six days after the primary. Its HDF5 headers
were read in the frozen screen, but no spectral value has been opened. It is
not part of the primary search and must remain spectrally untouched unless a
primary case survives the global threshold and all automatic v0.5 physical
vetoes.

If that trigger fires, candidate frequencies and a recurrence protocol must
be committed before any reserved-cadence spectral value is read. If no case
survives, the reserved cadence remains unopened. The third HD 33564 cadence,
`--81065`, is S-band and cannot cover these windows.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six primary scan times in all
five windows. All **630** checks passed without opening a remote file. The
smallest edge headroom is 214,952 channels, approximately 609.497 kHz.

The proof is run `32649155230`, artifact `9495693255`, verified digest
`sha256:84a398559aa82c21fc242ce90ec34815f864d091861bf778bb1cee4245f0166c`.
The result SHA-256 is
`977df9fd4615245fcad9206ce611c78c228b00a05eca308f2339027e15acee52`.

## Target and orbital template

The official composite record supplies RA 05h22m33.10s, Dec +79d13m54.66s,
parallax 47.6977 mas, proper motion (-78.3856, +162.118) mas/yr, and radial
velocity +0.107 km/s. The HD 33564 b working orbit has period 388 days,
semimajor axis 1.1 au, eccentricity 0.34, periastron epoch BJD 2452603.0,
and longitude of periastron 205 degrees. Its conservative full-projection
periastron drift proxy is 0.0630802 Hz/s at 1425 MHz. The orbit remains only a
coordinate-transform template and does not establish an emitter on the
planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, candidate reduction, v0.5 OFF/receiver vetoes, 256 complete
scrambles, and the completeness grid are unchanged. The new fixed seeds are
`2320260823` for scrambles and `232120260823` for completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m23_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m23_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m23_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m23_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m23_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, and completeness may not
change in response to the data. A primary cluster above the empirical global
threshold survives only if none of the frozen matched-OFF, single-adjacent-OFF,
local-OFF, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 23 as a primary null result and leaves the
reserved cadence unopened. Any survivor triggers a separately frozen
candidate-local morphology protocol. A case remaining unresolved after that
review triggers a separately frozen targeted recurrence test on `--71747`.
Only a compatible redetection there may be described as independently
recurrent. A null applies only to this frozen scope and its measured
completeness.
