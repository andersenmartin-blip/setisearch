# Milestone 27 preregistration: HD 127506 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`7eba3bba8a29676e7f251c2a2fc74b03baec1a7e76d698349255019a9c20d563`.

## Purpose and boundary

Milestone 27 is a new held-out application of detector v0.5.0. The target is
**HD 127506 / HIP 70950**, with HD 127506 b used only as the motion template.
The primary data are its sole complete compatible GBT L-band alternating
ON/control cadence, archive cadence `--83509`, beginning 2017-06-23 02:34:57
UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and calculated extraction geometry were read. No HD 127506 HDF5 `data` value
was indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header qualification rule were committed before ranks
21-25 were opened. HD 127506 at rank 23 is the next compatible host after
ranks 21-22 completed in Milestones 25-26. Its other cadence, `--69234`, is
S-band. Rank 24 has one compatible L-band cadence and remains spectrally
untouched for a later milestone.

Selection provenance is in `MILESTONE_27_TARGET_SELECTION.md`. The official
metadata query is GitHub Actions run `32722863857`, artifact `9518386109`,
digest
`sha256:5910678964dd586c495b8ed00e3af801398bc8986054ef801f99e2d412da2faa`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP70950 | 57927.107604166670 | 16 | 292.057776128 |
| 2 | control | HIP70142 | 57927.111747685190 | 16 | 292.057776128 |
| 3 | ON | HIP70950 | 57927.115844907410 | 16 | 292.057776128 |
| 4 | control | HIP70297 | 57927.120046296295 | 16 | 292.057776128 |
| 5 | ON | HIP70950 | 57927.124236111114 | 16 | 292.057776128 |
| 6 | control | HIP70334 | 57927.128229166665 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. Identities, sizes, ETags, sources, times, and geometry are
frozen in `config/hd127506b_heldout_m27.json`. The archival controls are three
different sky sources, not source labels formed as `HIP70950_OFF`; the frozen
detector still treats the alternating control positions as its OFF inputs.

## Mandatory extraction-coverage proof

`scripts/m14_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows. All **630**
checks passed without opening a remote file. The smallest edge headroom is
184,201 channels, approximately 514.652 kHz.

The proof is run `32723162146`, artifact `9518507815`, verified digest
`sha256:ba2e9171aba7be93b4780ac364a3486a22abfc3a19df362b56fcb40212bc7daf`.
The result SHA-256 is
`6e806e13aace98cdafa730c7448efd7f75e5235fd4c08fd7abb9f7bead04ffad`.

## Target and orbital template

The official composite record supplies RA 14h30m44.37s, Dec +35d27m16.58s,
parallax 44.3605 mas, proper motion (-481.116, +203.115) mas/yr, and radial
velocity -19.2 km/s. The HD 127506 b working orbit has period 65.78395 days,
semimajor axis 0.287 au, eccentricity 0.24, periastron epoch BJD 2456787.645,
and longitude of periastron 56.147 degrees. Its conservative full-projection
periastron drift proxy is 0.431784 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, clustering, v0.5 OFF/receiver vetoes, 256 complete scrambles,
and the completeness grid are unchanged. Fixed seeds are `2720260824` for
scrambles and `272120260824` for completeness. The 1200-cluster report cap
exceeds the finite maximum of 1008 retained peaks per window and therefore
cannot truncate the complete disposition record.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m27_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m27_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m27_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m27_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m27_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, seeds, completeness, and report retention
may not change in response to data. A cluster above the empirical global
threshold survives only if none of the frozen matched-control,
single-adjacent-control, local-control, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 27 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying HD 127506 L-band cadence exists in the frozen screen, so
this milestone cannot perform or claim independent recurrence. Any conclusion
is limited to the frozen scope and measured completeness.
