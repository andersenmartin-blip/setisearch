# Milestone 32 preregistration: HD 99492 b higher-smearing held-out validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`7f0f20f6e76f4182c9c9b94bb7ccca34c2d5345a459085362e480ef546732cf7`.

## Purpose and boundary

Milestone 32 is the second held-out application of detector v0.5.0 in the
prospectively frozen higher-smearing extension. The target is **HD 99492 /
HIP 55848**, with HD 99492 b used only as the motion template. The primary
data are its sole complete compatible GBT L-band alternating ON/control
cadence, archive cadence `--70969`, beginning 2016-05-13 01:47:38 UTC.

Before this commit, only the frozen discovery and header-screen records,
official orbit and host metadata, HTTP object identities, HDF5 attributes and
geometry, timestamps, and calculated extraction geometry were read. No
HD 99492 HDF5 `data` value was indexed, extracted, plotted, summarized, or
searched.

## Fixed extension and selection

Milestone 31 consumed extension rank 31, and rank 32 had no qualifying L-band
cadence. HD 99492 at frozen rank 33 is therefore the next eligible untouched
host. HD 3651 at rank 34 retains one qualifying cadence for later work; rank
35 does not qualify. Selection provenance is in
`MILESTONE_32_TARGET_SELECTION.md` and the immutable Milestone 31 header
screen, workflow run `32867230503`, artifact `9570603163`, digest
`sha256:2535ae0c218bb6418f6001374445b620ad8d808c6ab51e8fa9ecb85cae7e1ce0`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP55848 | 57521.074745370370 | 16 | 287.779586048 |
| 2 | control | HIP54998 | 57521.078715277780 | 16 | 287.779586048 |
| 3 | ON | HIP55848 | 57521.082685185180 | 16 | 287.779586048 |
| 4 | control | HIP55211 | 57521.086620370370 | 16 | 287.779586048 |
| 5 | ON | HIP55848 | 57521.090555555560 | 16 | 287.779586048 |
| 6 | control | HIP55321 | 57521.094479166670 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 318230528]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1023.925784086 to
1926.269531250 MHz. URLs, sizes, ETags, sources, times, and geometry are frozen
in `config/hd99492b_heldout_m32.json`.

## Mandatory motion-plus-width coverage proof

`scripts/m32_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows, adding the
16-channel half-width required by the widest 33-channel boxcar. All **630**
checks passed without opening a remote file. The largest within-scan
dedoppler margin is 166 channels. After motion and width margins, the smallest
extraction-edge headroom is 202,076 channels, approximately 572.987 kHz.

The proof is run `32873302196`, artifact `9572910087`, verified digest
`sha256:53266a2119cf10ec3bfe4ddb12f1237c904735b96af08cfef4580b560ad9ddbb`.
The result SHA-256 is
`623874e1fdeac79308956186cfb056397b3f4c238743ffba9b55049c971dfe13`.

## Target and orbital template

The official composite record supplies RA 11h26m45.52s, Dec +03d00m25.68s,
parallax 54.9057 mas, proper motion (-728.277, +188.526) mas/yr, and radial
velocity +3.1 km/s. The HD 99492 b working orbit has period 17.0503 days,
semimajor axis 0.12 au, eccentricity 0.034, periastron epoch BJD 2450468.7,
and longitude of periastron 154.3 degrees. Its conservative full-projection
periastron drift proxy is 1.66346922 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

The exact official metadata query is workflow run `32872852427`, artifact
`9572740806`, digest
`sha256:e83a9859ca0349c16ca91e71c1858bc1c00cf27b841cde1b89617dd9d7789d7e`.
Its preserved record SHA-256 is
`d17ebed8f9c0a5676a2140b36ba35424489acdd98fa9e936d80f23aa53c7f95b`.

## Frozen detector and higher-smearing method

Detector software v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, clustering,
physical OFF/receiver vetoes, 256 complete scrambles, and the completeness
procedure are unchanged from Milestone 31.

The prospectively frozen boxcar bank remains `[1, 3, 5, 9, 17, 33]` channels.
The report cap is 1600, exceeding the finite maximum of 1512 retained
pre-clustering peaks per window, so the disposition record cannot be
truncated. Fresh fixed seeds are `3220260825` for scrambles and
`322120260825` for completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m32_1400p5` | 1399.2--1401.8 | 1400.5 | 500 |
| `m32_1406p5` | 1405.2--1407.8 | 1406.5 | 500 |
| `m32_1412p5` | 1411.2--1413.8 | 1412.5 | 500 |
| `m32_1418p5` | 1417.2--1419.8 | 1418.5 | 500 |
| `m32_1425p0` | 1423.7--1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, widths, seeds, completeness, and report
retention may not change in response to data. A cluster above the empirical
global threshold survives only if none of the frozen matched-control,
single-adjacent-control, local-control, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 32 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying HD 99492 cadence exists, so this milestone cannot perform
or claim independent recurrence. Any conclusion is limited to the frozen
scope and measured completeness.
