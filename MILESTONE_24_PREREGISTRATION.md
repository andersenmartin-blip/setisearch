# Milestone 24 preregistration: 16 Cyg B b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`73cee229fc1696a895444168902f7ae2eb1be5ccced41689206a93f5df4730ca`.

## Purpose and boundary

Milestone 24 is a new held-out application of detector v0.5.0. The target is
**16 Cyg B / HIP 96901**, with 16 Cyg B b used only as the motion template.
The primary data are its sole complete compatible GBT L-band alternating
ON/OFF cadence, archive cadence `--67109`, beginning 2017-01-02 21:37:11 UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and locally calculated extraction geometry were read. No 16 Cyg B HDF5
`data` value was indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header-screen rule were published before ranks 16-20
were opened. Rank 17, HD 33564, was searched in Milestone 23 and left no
survivor. Rank 18, HD 114783, is S-band-only. The next host in unchanged rank
order with a compatible L-band cadence is 16 Cyg B at rank 19.

Selection provenance is preserved in `MILESTONE_24_TARGET_SELECTION.md`. The
official metadata query is GitHub Actions run `32653431103`, artifact
`9496803850`, digest
`sha256:89468ac6a15369cc50162b90b701ca433b5391e72520a6c3dc7e875a162b0054`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP96901 | 57755.900821759256 | 16 | 292.057776128 |
| 2 | OFF | HIP95737 | 57755.904803240740 | 16 | 292.057776128 |
| 3 | ON | HIP96901 | 57755.908773148150 | 16 | 292.057776128 |
| 4 | OFF | HIP95853 | 57755.912615740740 | 16 | 292.057776128 |
| 5 | ON | HIP96901 | 57755.916458333330 | 16 | 292.057776128 |
| 6 | OFF | HIP95872 | 57755.920358796300 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/16cygbb_heldout_m24.json`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows. All **630** checks passed without opening a remote file. The smallest
edge headroom is 230,372 channels, approximately 643.652 kHz.

The proof is run `32653640215`, artifact `9496858641`, verified digest
`sha256:f4004039c45c9a75deca1a80bfe30df8140221a53f7d5c8957e5ed0311a5ff1c`.
The result SHA-256 is
`c167ccb6c1f9e5218a2c761767d9bfeec211e26115fa16954b76360b0fcce5f4`.

## Target and orbital template

The official composite record supplies RA 19h41m51.75s, Dec +50d31m00.57s,
parallax 47.2754 mas, proper motion (-134.791, -162.493) mas/yr, and radial
velocity -28.1 km/s. The 16 Cyg B b working orbit has period 798.5 days,
semimajor axis 1.66 au, eccentricity 0.68, periastron epoch BJD 2450539.3,
and longitude of periastron 82.74 degrees. Its conservative full-projection
periastron drift proxy is 0.0956115 Hz/s at 1425 MHz. The orbit remains only a
coordinate-transform template and does not establish an emitter on the
planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, candidate clustering, v0.5 OFF/receiver vetoes, 256 complete
scrambles, and the completeness grid are unchanged. The new fixed seeds are
`2420260823` for scrambles and `242120260823` for completeness.

The candidate-report cap is prospectively raised from 50 to 1200. This is an
output-retention change motivated by Milestone 23's separately audited cap;
it exceeds the finite maximum of 1008 pre-clustering peak reports per window
and therefore preserves every cluster without altering scores, thresholds,
clustering, vetoes, or trial accounting.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m24_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m24_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m24_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m24_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m24_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, completeness, and the
complete-report cap may not change in response to the data. A cluster above
the empirical global threshold survives only if none of the frozen
matched-OFF, single-adjacent-OFF, local-OFF, or receiver-frame-alias vetoes
applies.

No survivor closes Milestone 24 as a primary-cadence null result. Any survivor
must be reported as an unresolved candidate requiring genuinely independent
observations. The frozen header screen contains no second qualifying 16 Cyg B
cadence, so this milestone cannot perform or claim independent recurrence.
A null or candidate applies only to this frozen scope and its measured
completeness.
