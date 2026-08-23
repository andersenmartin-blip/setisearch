# Milestone 25 preregistration: HD 164922 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`3ab7ea6e4a73f4ecbb024690148c2419de42df69fba461442972d0733af09868`.

## Purpose and boundary

Milestone 25 is a new held-out application of detector v0.5.0. The target is
**HD 164922 / HIP 88348**, with HD 164922 b used only as the motion template.
The primary data are its sole complete compatible GBT L-band alternating
ON/OFF cadence, archive cadence `--84744`, beginning 2016-03-10 13:53:38 UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and calculated extraction geometry were read. No HD 164922 HDF5 `data` value
was indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header qualification rule were committed before ranks
21-25 were opened. HD 164922 at rank 21 is the first host in that unchanged
extension with a complete compatible L-band cadence. Its other cadence,
`--82207`, is S-band. Ranks 22-24 each have one compatible L-band cadence and
remain spectrally untouched for later milestones.

Selection provenance is in `MILESTONE_25_TARGET_SELECTION.md`. The official
metadata query is GitHub Actions run `32655763537`, artifact `9497391729`,
digest
`sha256:5872014e58b7f8e2010711e44a9c983be0315dcee31dc76692e4548ea22f893c`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP88348 | 57457.578912037040 | 16 | 287.779586048 |
| 2 | OFF | HIP88348_OFF | 57457.582789351850 | 16 | 287.779586048 |
| 3 | ON | HIP88348 | 57457.586655092590 | 16 | 287.779586048 |
| 4 | OFF | HIP88348_OFF | 57457.590520833335 | 16 | 287.779586048 |
| 5 | ON | HIP88348 | 57457.594386574080 | 16 | 287.779586048 |
| 6 | OFF | HIP87938 | 57457.602881944450 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 264503296]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1126.464846586 to
1876.464843750 MHz. Identities, sizes, ETags, sources, times, and geometry are
frozen in `config/hd164922b_heldout_m25.json`.

## Mandatory extraction-coverage proof

`scripts/m14_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows. All **630**
checks passed without opening a remote file. The smallest edge headroom is
219,489 channels, approximately 622.362 kHz.

The proof is run `32655898967`, artifact `9497428405`, verified digest
`sha256:5fa0c40ceb8de2ba7d07a0009fddbb223b87bedb9d44d10d5b74b25a4faa4f24`.
The result SHA-256 is
`b04834e2dfd3097d329096380520e41b6ee10e7d06992e3bf8c63b1d2f1b4837`.

## Target and orbital template

The official composite record supplies RA 18h02m31.31s, Dec +26d18m37.47s,
parallax 45.4222 mas, proper motion (+389.653, -602.314) mas/yr, and radial
velocity +20.3634 km/s. The HD 164922 b working orbit has period 1207 days,
semimajor axis 2.16 au, eccentricity 0.08, periastron epoch BJD 2457978.0,
and longitude of periastron 116 degrees. Its conservative full-projection
periastron drift proxy is 0.00658742 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, clustering, v0.5 OFF/receiver vetoes, 256 complete scrambles,
and the completeness grid are unchanged. Fixed seeds are `2520260823` for
scrambles and `252120260823` for completeness. The 1200-cluster report cap
exceeds the finite maximum of 1008 retained peaks per window and therefore
cannot truncate the complete disposition record.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m25_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m25_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m25_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m25_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m25_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, seeds, completeness, and report retention
may not change in response to data. A cluster above the empirical global
threshold survives only if none of the frozen matched-OFF,
single-adjacent-OFF, local-OFF, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 25 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying HD 164922 L-band cadence exists in the frozen screen, so this
milestone cannot perform or claim independent recurrence. Any conclusion is
limited to the frozen scope and measured completeness.
