# Milestone 31 preregistration: HD 192263 b higher-smearing held-out validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`4037921bc5fabd38e606455f1d515b97da8ffcf1aab2a993553ab114929ee986`.

## Purpose and boundary

Milestone 31 is a held-out application of detector software v0.5.0 to the
first target beyond the original 1 Hz/s conservative smearing group. The
target is **HD 192263 / HIP 99711**, with HD 192263 b used only as the motion
template. The primary data are its sole complete compatible GBT L-band
alternating ON/control cadence, archive cadence `--66435`, beginning
2016-10-22 22:07:08 UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and calculated extraction geometry were read. No HD 192263 HDF5 `data` value
was indexed, extracted, plotted, summarized, or searched.

## Fixed extension and selection

Milestones 16--30 exhausted the thirty unique hosts below the original 1 Hz/s
bound. Milestone 31 froze the next five hosts already preserved in the
unchanged Milestone 16 `all_matches` order. HD 192263 at extension rank 31 is
the first compatible host. HD 99492 and HD 3651 at ranks 33 and 34 retain one
qualifying cadence each for later work; ranks 32 and 35 do not qualify.

Selection provenance is in `MILESTONE_31_TARGET_SELECTION.md`. The header
screen is GitHub Actions run `32867230503`, artifact `9570603163`, digest
`sha256:2535ae0c218bb6418f6001374445b620ad8d808c6ab51e8fa9ecb85cae7e1ce0`.
The official metadata query is run `32867610122`, artifact `9570724506`,
digest
`sha256:6298c10ff0ab080e91874f3224571d6c690e09980ba907da1cfefd89313a776a`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP99711 | 57683.921620370370 | 16 | 292.057776128 |
| 2 | control | HIP100159 | 57683.925486111110 | 16 | 292.057776128 |
| 3 | ON | HIP99711 | 57683.929351851850 | 16 | 292.057776128 |
| 4 | control | HIP100786 | 57683.933356481480 | 16 | 292.057776128 |
| 5 | ON | HIP99711 | 57683.937361111110 | 16 | 292.057776128 |
| 6 | control | HIP98698 | 57683.941261574070 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. Identities, sizes, ETags, sources, times, and geometry are
frozen in `config/hd192263b_heldout_m31.json`.

## Mandatory motion-plus-width coverage proof

`scripts/m31_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows, adding the
16-channel half-width required by the widest 33-channel boxcar. All **630**
checks passed without opening a remote file. The largest within-scan
dedoppler margin is 109 channels. After that motion and width margin, the
smallest extraction-edge headroom is 129,682 channels, approximately
362.327 kHz.

The proof is run `32868009650`, artifact `9570893753`, verified digest
`sha256:b61a9bebba77348154a8cf39d7f51c48c545d08c6792bd095b863cb8fa63a372`.
The result SHA-256 is
`4f38c6d0fda2d007705e038ada063169533b74cc1e4ec4ee636f8e7671164cca`.

## Target and orbital template

The official composite record supplies RA 20h13m59.78s, Dec -00d51m56.73s,
parallax 50.8982 mas, proper motion (-62.6708, +260.961) mas/yr, and radial
velocity -10.686 km/s. The HD 192263 b working orbit has period 24.3556 days,
semimajor axis 0.15 au, eccentricity 0.05, periastron epoch BJD 2451979.28,
and longitude of periastron 20 degrees. Its conservative full-projection
periastron drift proxy is 1.05365446 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

## Frozen detector and higher-smearing adaptation

Detector software v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, clustering,
physical OFF/receiver vetoes, 256 complete scrambles, and the completeness
procedure are unchanged.

Before any rank 31--35 telescope product was opened, the boxcar bank was
prospectively expanded from `[1, 3, 5, 9]` to
`[1, 3, 5, 9, 17, 33]` channels. The report cap is 1600, exceeding the finite
maximum of 1512 retained pre-clustering peaks per window, so the disposition
record cannot be truncated. Fresh fixed seeds are `3120260825` for scrambles
and `312120260825` for completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m31_1400p5` | 1399.2--1401.8 | 1400.5 | 500 |
| `m31_1406p5` | 1405.2--1407.8 | 1406.5 | 500 |
| `m31_1412p5` | 1411.2--1413.8 | 1412.5 | 500 |
| `m31_1418p5` | 1417.2--1419.8 | 1418.5 | 500 |
| `m31_1425p0` | 1423.7--1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, widths, seeds, completeness, and report
retention may not change in response to data. A cluster above the empirical
global threshold survives only if none of the frozen matched-control,
single-adjacent-control, local-control, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 31 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying HD 192263 cadence exists, so this milestone cannot perform
or claim independent recurrence. Any conclusion is limited to the frozen
scope and measured completeness.
