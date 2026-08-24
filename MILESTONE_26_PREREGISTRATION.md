# Milestone 26 preregistration: HD 19994 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`4ae3587e7c75835e72298a22dffcb5887d711b0b7720977b6c1384e9277a6047`.

## Purpose and boundary

Milestone 26 is a new held-out application of detector v0.5.0. The target is
**HD 19994 / HIP 14954**, with HD 19994 b used only as the motion template.
The primary data are its sole complete compatible GBT L-band alternating
ON/OFF cadence, archive cadence `--84358`, beginning 2016-02-18 23:32:42 UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and calculated extraction geometry were read. No HD 19994 HDF5 `data` value
was indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header qualification rule were committed before ranks
21-25 were opened. HD 19994 at rank 22 is the next compatible host after rank
21 completed in Milestone 25. Its other cadence, `--63712`, is S-band. Ranks
23-24 each have one compatible L-band cadence and remain spectrally untouched
for later milestones.

Selection provenance is in `MILESTONE_26_TARGET_SELECTION.md`. The official
metadata query is GitHub Actions run `32694932956`, artifact `9508496319`,
digest
`sha256:c22ea74fb3dc77dcfe46c7fa0da7d0657edfe0a4843db53d9f85980519c3b0c1`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP14954 | 57436.981041666666 | 16 | 287.779586048 |
| 2 | OFF | HIP14954_OFF | 57436.984849537040 | 16 | 287.779586048 |
| 3 | ON | HIP14954 | 57436.988657407404 | 16 | 287.779586048 |
| 4 | OFF | HIP14954_OFF | 57436.992465277780 | 16 | 287.779586048 |
| 5 | ON | HIP14954 | 57436.996261574070 | 16 | 287.779586048 |
| 6 | OFF | HIP14954_OFF | 57437.000057870370 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 264503296]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1126.464846586 to
1876.464843750 MHz. Identities, sizes, ETags, sources, times, and geometry are
frozen in `config/hd19994b_heldout_m26.json`.

## Mandatory extraction-coverage proof

`scripts/m14_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows. All **630**
checks passed without opening a remote file. The smallest edge headroom is
205,273 channels, approximately 582.052 kHz.

The proof is run `32695228112`, artifact `9508597939`, verified digest
`sha256:40230f361bedbaef49f3682871292fb239d551953acdc13f4c5dc5e10a8fea0d`.
The result SHA-256 is
`e8630f1275df3a3e1116a4a734c0666a387cdb9b3477cc0ad0e0cc5cb318dea9`.

## Target and orbital template

The official composite record supplies RA 03h12m46.64s, Dec -01d11m47.02s,
parallax 44.3695 mas, proper motion (+193.25, -69.2932) mas/yr, and radial
velocity +19.0 km/s. The HD 19994 b working orbit has period 466.2 days,
semimajor axis 1.305 au, eccentricity 0.063, periastron epoch BJD 2453757.0,
and longitude of periastron 346 degrees. Its conservative full-projection
periastron drift proxy is 0.0257181 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, clustering, v0.5 OFF/receiver vetoes, 256 complete scrambles,
and the completeness grid are unchanged. Fixed seeds are `2620260824` for
scrambles and `262120260824` for completeness. The 1200-cluster report cap
exceeds the finite maximum of 1008 retained peaks per window and therefore
cannot truncate the complete disposition record.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m26_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m26_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m26_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m26_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m26_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, seeds, completeness, and report retention
may not change in response to data. A cluster above the empirical global
threshold survives only if none of the frozen matched-OFF,
single-adjacent-OFF, local-OFF, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 26 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying HD 19994 L-band cadence exists in the frozen screen, so this
milestone cannot perform or claim independent recurrence. Any conclusion is
limited to the frozen scope and measured completeness.
