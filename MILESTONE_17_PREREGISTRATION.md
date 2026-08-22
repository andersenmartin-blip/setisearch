# Milestone 17 preregistration: GJ 849 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`87372243bc6f8eec0b9cdf4f80d3a3c37fbffdd13bddd6efeafdfd5f383b2e76`.

## Purpose and boundary

Milestone 17 is a new held-out application of detector v0.5.0. The target is
**GJ 849 / HIP 109388**, with GJ 849 b used only as the motion template. The
primary data are the complete GBT L-band ABACAD cadence beginning 2016-07-05
10:22:51 UTC, archive cadence `--73890`.

The second complete cadence, `--74424`, begins 5.958 days later and is reserved
untouched. It may be opened spectrally only after any primary cases and a
targeted recurrence protocol are separately frozen.

Before this commit, only catalogue records, official orbit/host metadata, HTTP
object identities, HDF5 attributes and geometry, timestamps, and locally
calculated extraction geometry were read. No GJ 849 HDF5 `data` value was
indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The preregistered Milestone 16 low-smearing ranking and corrected header screen
placed GJ 849 behind GJ 876, HD 219134, and GJ 514. GJ 876 and GJ 514 had only
S-band products, and HD 219134 was completed in Milestone 16. GJ 849 is
therefore the nearest still-unsearched compatible L-band host. Its earliest of
two qualifying cadences is the primary held-out data set.

Selection provenance is preserved in `MILESTONE_17_TARGET_SELECTION.md`. The
official metadata query is GitHub Actions run `32571608488`, artifact
`9475456047`, digest
`sha256:88c2a0941f0e4232461a7ce077d987f7d57044543444d979f24e47c72861d79e`.

## Frozen cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP109388 | 57574.432534722226 | 16 | 292.057776128 |
| 2 | OFF | HIP108459 | 57574.436469907410 | 16 | 292.057776128 |
| 3 | ON | HIP109388 | 57574.440405092595 | 16 | 292.057776128 |
| 4 | OFF | HIP108460 | 57574.444363425920 | 16 | 292.057776128 |
| 5 | ON | HIP109388 | 57574.448321759260 | 16 | 292.057776128 |
| 6 | OFF | HIP108550 | 57574.452280092590 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/gj849b_heldout_m17.json`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows. All **630** checks passed without opening a remote file. The smallest
edge headroom is 229,501 channels, approximately 641.218 kHz.

The proof is run `32571783837`, artifact `9475499922`, digest
`sha256:b0c80088256f4a8e6896a3fec8322a57e5477b95046bf5b9eac43ae950375650`.
The result SHA-256 is
`a95742d359791e6e5b0152d563fbd1c759d7bb921b230c8c25093ebf4e0c6586`.

## Target and orbital template

The official composite record supplies RA 22h09m41.52s, Dec -04d38m26.99s,
parallax 113.6 mas, proper motion (+1132.53, -22.1255) mas/yr, and radial
velocity -15.3 km/s. The GJ 849 b working orbit has period 1925.31 days,
semimajor axis 2.32 au, eccentricity 0.029, periastron epoch BJD 2453770.0,
and longitude of periastron 111 degrees. Its conservative full-projection
periastron drift proxy is 0.00250 Hz/s at 1425 MHz. The orbit remains only a
coordinate-transform template and does not establish an emitter on the planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
activity subsets, S/N rules, moving RFI mask, widths `[1, 3, 5, 9]`, candidate
reduction, v0.5 vetoes, 256 scrambles, and the completeness grid are unchanged.
The new fixed seeds are `1720260822` for scrambles and `171720260822` for
completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m17_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m17_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m17_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m17_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m17_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, and completeness may not
change in response to the data. A retained candidate is only a trigger for a
separately frozen morphology review and, if still unresolved, the reserved
independent cadence. A null applies only to the frozen scope and measured
completeness.
