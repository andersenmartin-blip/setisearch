# Milestone 16 preregistration: HD 219134 h held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`8f2da40aaa1b80fbbc4d34087dde5ef2cd565d7d7da7319fa52264e94d38919f`.

## Purpose and boundary

Milestone 16 is a new held-out application of detector v0.5.0. The target is
**HD 219134**, with HD 219134 h used only as the motion template. The data are
the complete GBT L-band ABACAD cadence beginning 2016-08-22 08:00:53 UTC,
archive cadence `--63424`.

Before this commit, only catalogue records, official orbit/host metadata, HTTP
object identities, HDF5 attributes and geometry, timestamps, and locally
calculated extraction geometry were read. No selected HDF5 `data` value was
indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The Milestone 16 discovery plan was committed before the catalogue run. Of 68
matched non-excluded planet/target pairs, 42 satisfied the conservative
1 Hz/s acceleration-smearing limit. The first five unique hosts were frozen by
distance. The corrected header-only screen found:

- GJ 876 and GJ 514 had only S-band products at the required cadence IDs;
- HD 219134 supplied five qualifying L-band cadences;
- GJ 849 supplied two; and
- GJ 649 supplied one.

HD 219134 is therefore the nearest qualifying host. Its earliest qualifying
cadence, `--63424`, is selected. Discovery is run `32506360670`; the corrected
header screen is run `32507313007`; the exact official selected-target query is
run `32507828944`. Their artifact identities and hashes are frozen in the
configuration and published reports.

## Frozen cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | Hip114622 | 57622.333946759260 | 16 | 292.057776128 |
| 2 | OFF | Hip113498 | 57622.337847222225 | 16 | 292.057776128 |
| 3 | ON | Hip114622 | 57622.341747685180 | 16 | 292.057776128 |
| 4 | OFF | Hip113772 | 57622.345648148150 | 16 | 292.057776128 |
| 5 | ON | Hip114622 | 57622.349548611110 | 16 | 292.057776128 |
| 6 | OFF | Hip113789 | 57622.353402777780 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/hd219134h_heldout_m16.json`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows. All **630** checks passed without opening a remote file. The smallest
edge headroom is 260,459 channels, approximately 727.714 kHz.

The proof is run `32508284183`, artifact `9456069961`, digest
`sha256:7f7b3d3e9d0b1a8a68d24599d243a7b1c99590180349ffa202355ba012b493c3`.
The result SHA-256 is
`b8864a7c1d2d25ab696a69ff9e05beab61f1ee9447eefc12640855a13d4e51a0`.

## Target and orbital template

The official composite HD 219134 h record supplies period 2247 days,
semimajor axis 3.11 au, eccentricity 0.06, periastron epoch BJD 2448725.0, and
longitude of periastron 215 degrees. Its conservative full-projection
periastron drift proxy is 0.00262 Hz/s at 1425 MHz. The orbit remains only a
coordinate-transform template and does not establish an emitter on the
planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
activity subsets, S/N rules, moving RFI mask, widths `[1, 3, 5, 9]`, candidate
reduction, v0.5 vetoes, 256 scrambles, and the completeness grid are unchanged.
The new fixed seeds are `1620260821` for scrambles and `161620260821` for
completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m16_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m16_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m16_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m16_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m16_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, and completeness may not
change in response to the data. A retained candidate is only a follow-up
trigger requiring an independent cadence; a null applies only to the frozen
scope and measured completeness.
