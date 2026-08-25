# Milestone 30 preregistration: bet UMi b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`b08e820bb55cc0d1b946890f93cb7a15742825df97274392cb44d97058b989d3`.

## Purpose and boundary

Milestone 30 is a new held-out application of detector v0.5.0. The target is
**bet UMi / HIP 72607**, with bet UMi b used only as the motion template. The
primary data are its sole complete compatible GBT L-band alternating
ON/control cadence, archive cadence `--74586`, beginning 2016-07-15 02:22:28
UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and calculated extraction geometry were read. No bet UMi HDF5 `data` value
was indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The rank 26--30 target order and header qualification rule were committed
before those products were opened. HD 11964 at rank 28 was consumed by
Milestone 29. bet UMi at rank 29 is the next and last compatible host in that
five-target block; ranks 26, 27, and 30 are S-band. bet UMi cadence `--77497`
is also S-band and is excluded mechanically.

Selection provenance is in `MILESTONE_30_TARGET_SELECTION.md`. The header
screen is GitHub Actions run `32755739577`, artifact `9530790490`, digest
`sha256:9c888d3ef27e622385ded9fd51ad1b3e238910923ee2758f09b9aa84f163fdfd`.
The official metadata query is run `32804981595`, artifact `9547815063`,
digest
`sha256:74e71428f9a75ae1dd91f68736ecab381b8bacb3ed48482d6001f3bd483fa184`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | Hip72607 | 57584.098935185180 | 16 | 292.057776128 |
| 2 | control | Hip72307 | 57584.102754629630 | 16 | 292.057776128 |
| 3 | ON | Hip72607 | 57584.106574074074 | 16 | 292.057776128 |
| 4 | control | Hip73047 | 57584.110439814816 | 16 | 292.057776128 |
| 5 | ON | Hip72607 | 57584.114305555560 | 16 | 292.057776128 |
| 6 | control | Hip73715 | 57584.118252314816 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. Identities, sizes, ETags, sources, times, and geometry are
frozen in `config/betumib_heldout_m30.json`.

## Mandatory extraction-coverage proof

`scripts/m14_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows. All **630**
checks passed without opening a remote file. The smallest edge headroom is
238,473 channels, approximately 666.286 kHz.

The proof is run `32805205023`, artifact `9547895841`, verified digest
`sha256:327bc1000b36ce2ea503e48824373418f773171ac035c1b03ff879ca823d4217`.
The result SHA-256 is
`280a997f712b5d3e39e677bf7c036671ac2b24861250b4f41c30502aaff82658`.

## Target and orbital template

The official composite record supplies RA 14h50m42.36s, Dec +74d09m19.97s,
parallax 25.79 mas, proper motion (-32.29, +11.91) mas/yr, and radial velocity
+16.9 km/s. The bet UMi b working orbit has period 522.3 days, semimajor axis
1.4 au, eccentricity 0.19, periastron epoch BJD 2453175.3, and longitude of
periastron 307.4 degrees. Its conservative full-projection periastron drift
proxy is 0.0294151 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, clustering, v0.5 OFF/receiver vetoes, 256 complete scrambles,
and the completeness grid are unchanged. New fixed seeds are `3020260825` for
scrambles and `302120260825` for completeness. The 1200-cluster report cap
exceeds the finite maximum of 1008 retained peaks per window and therefore
cannot truncate the complete disposition record.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m30_1400p5` | 1399.2--1401.8 | 1400.5 | 500 |
| `m30_1406p5` | 1405.2--1407.8 | 1406.5 | 500 |
| `m30_1412p5` | 1411.2--1413.8 | 1412.5 | 500 |
| `m30_1418p5` | 1417.2--1419.8 | 1418.5 | 500 |
| `m30_1425p0` | 1423.7--1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, seeds, completeness, and report retention
may not change in response to data. A cluster above the empirical global
threshold survives only if none of the frozen matched-control,
single-adjacent-control, local-control, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 30 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying bet UMi L-band cadence exists in the frozen screen, so this
milestone cannot perform or claim independent recurrence. Any conclusion is
limited to the frozen scope and measured completeness.
