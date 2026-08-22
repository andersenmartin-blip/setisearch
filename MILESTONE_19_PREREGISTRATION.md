# Milestone 19 preregistration: 47 UMa d held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`48b82d339409bc62f05fdbab1f4f3427bb7d0c73d8d1a29064527a210aba9823`.

## Purpose and boundary

Milestone 19 is a new held-out application of detector v0.5.0. The target is
**47 UMa / HIP 53721**, with 47 UMa d used only as the motion template. The
primary data are its sole complete compatible GBT L-band ABACAD cadence,
beginning 2016-07-09 00:31:28 UTC, archive cadence `--73992`.

Before this commit, only catalogue records, official orbit/host metadata, HTTP
object identities, HDF5 attributes and geometry, timestamps, and locally
calculated extraction geometry were read. No 47 UMa HDF5 `data` value was
indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target extension and header-screen rule were published before ranks 6-10
were opened. HD 147379 and HD 48948 had only S-band products. The available
55 Cnc L-band cadence had an incomplete sixth scan, so it failed the fixed
matching-geometry rule. 47 UMa at rank 8 was the first complete compatible
L-band host and is therefore selected; the later qualifying rho CrB cadence
was not substituted.

Selection provenance is preserved in `MILESTONE_19_TARGET_SELECTION.md`. The
official metadata query is GitHub Actions run `32584505527`, artifact
`9478673523`, digest
`sha256:9bd152d8d339b5c83aff3222982f177ce89a35fe2a69614eaf5624c321e3d837`.

## Frozen cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | Hip53721 | 57578.021851851850 | 16 | 292.057776128 |
| 2 | OFF | Hip52647 | 57578.025891203700 | 16 | 292.057776128 |
| 3 | ON | Hip53721 | 57578.029930555550 | 16 | 292.057776128 |
| 4 | OFF | Hip52881 | 57578.034039351850 | 16 | 292.057776128 |
| 5 | ON | Hip53721 | 57578.038136574076 | 16 | 292.057776128 |
| 6 | OFF | Hip53076 | 57578.042175925926 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/47umad_heldout_m19.json`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows. All **630** checks passed without opening a remote file. The smallest
edge headroom is 242,687 channels, approximately 678.060 kHz.

The proof is run `32584725105`, artifact `9478738608`, digest
`sha256:cff158fe88808749177e030062ac76b2168ccf05d4c54e2c084e9adfd20dfd19`.
The result SHA-256 is
`27ed208f09319a75d744ca47188b4aaf94f0b0373978909e6139f5908afdf5fe`.

## Target and orbital template

The official composite record supplies RA 10h59m27.54s, Dec +40d25m49.78s,
parallax 72.4528 mas, proper motion (-317.642, +55.0139) mas/yr, and radial
velocity +11.22 km/s. The 47 UMa d working orbit has period 14,002 days,
semimajor axis 11.6 au, eccentricity 0.16, periastron epoch BJD 2451736.0,
and longitude of periastron 110 degrees. Its conservative full-projection
periastron drift proxy is 0.00031534 Hz/s at 1425 MHz. The orbit remains only
a coordinate-transform template and does not establish an emitter on the
planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
activity subsets, S/N rules, moving RFI mask, widths `[1, 3, 5, 9]`, candidate
reduction, v0.5 vetoes, 256 scrambles, and the completeness grid are unchanged.
The new fixed seeds are `1920260822` for scrambles and `191920260822` for
completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m19_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m19_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m19_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m19_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m19_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, and completeness may not
change in response to the data. A retained candidate is only a trigger for a
separately frozen within-cadence morphology review. With no second qualifying
47 UMa cadence in the frozen screen, it cannot be called independently
recurrent without later public data. A null applies only to this frozen scope
and its measured completeness.
