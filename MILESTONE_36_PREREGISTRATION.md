# Milestone 36 preregistration: HIP 48714 b high-smearing held-out validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`b2c483a9db4075524319a0cd8e336969de4556bd0f9e5b66266a0b687f84b43c`.

## Purpose and boundary

Milestone 36 is a held-out application of detector software v0.5.0 to the
first compatible target in the prospectively frozen ranks 36--40
high-smearing extension. The target is **HIP 48714**, with HIP 48714 b used
only as the motion template. The primary data are its sole complete compatible
GBT L-band alternating ON/control cadence, archive cadence `--76348`,
beginning 2016-08-19 17:20:12 UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and calculated extraction geometry were read. No HIP 48714 HDF5 `data` value
was indexed, extracted, plotted, summarized, or searched.

## Fixed extension and mechanical selection

Milestones 16--33 exhausted or retained the eligible hosts through rank 35.
Milestone 36 screened the unchanged discovery extension ranks 36--40 without
reading spectral values. Ranks 36, 37, and 38 each have one qualifying
cadence; ranks 39 and 40 have none. The fixed first-eligible rule therefore
selects HIP 48714 at rank 36. The rank-37 HD 156668 and rank-38 HD 1461
cadences remain unopened and retained for later work.

Selection provenance is in `MILESTONE_36_TARGET_SELECTION.md`. The checked
header screen is GitHub Actions run `32987209536`, artifact `9613347814`,
digest
`sha256:6082faeb54f41b2ee45b00a8c7c8637fcd1e56854ed21272f739026253f9d5ba`.
The official metadata query is run `32990388450`, artifact `9614371861`,
digest
`sha256:50bd1089a37713b30a74d3235a6a269a98c033ff8e179e4f60a4909a19382c71`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | Hip48714 | 57619.722361111110 | 16 | 292.057776128 |
| 2 | control | Hip47655 | 57619.726388888890 | 16 | 292.057776128 |
| 3 | ON | Hip48714 | 57619.730416666665 | 16 | 292.057776128 |
| 4 | control | Hip47791 | 57619.734386574080 | 16 | 292.057776128 |
| 5 | ON | Hip48714 | 57619.738368055560 | 16 | 292.057776128 |
| 6 | control | Hip48132 | 57619.742337962960 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. Identities, sizes, ETags, sources, times, and geometry are
frozen in `config/hip48714b_heldout_m36.json`.

## Mandatory motion, width, and report-cap proof

`scripts/m36_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows, adding the
64-channel half-width required by the widest 129-channel boxcar. All **630**
motion/edge checks passed without opening a remote file. The largest
within-scan dedoppler margin is 362 channels. After that motion and width
margin, the smallest extraction-edge headroom is 200,607 channels,
approximately 560.489 kHz.

The same proof independently derives four allowed activity subsets. With
eight widths and three retained peaks per motion/activity/width hypothesis,
the exact finite maximum is `21 * 4 * 8 * 3 = 2016` peak records per window.
The frozen cap of 2200 therefore cannot truncate the cluster disposition
record.

The proof is run `32992060938`, artifact `9615002490`, digest
`sha256:122de623a7d80774e89583df67c95215684d6d853ec4baf19088b937dd98a784`.
Its result SHA-256 is
`a6bc77011756f47ca139a933c5eba64c2858dce6b0351eb2f2659f376ec541c0`,
and its publication commit is
`fb5249e331606fd54f1f51a2cfc75dc189542c88`.

## Target and orbital template

The official composite record supplies RA 09h56m07.98s, Dec +62d47m09.42s,
parallax 94.9397 mas, proper motion (-304.046, -583.599) mas/yr, and radial
velocity +14.98726 km/s. The HIP 48714 b working orbit has period 17.818 days,
semimajor axis 0.112 au, eccentricity 0.5, periastron epoch BJD 2451539.8,
and longitude of periastron 202 degrees. Its conservative full-projection
periastron drift proxy is 5.30654596 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

## Frozen detector and high-smearing adaptation

Detector software v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, clustering,
physical OFF/receiver vetoes, 256 complete scrambles, and the completeness
procedure are unchanged.

Before any rank 36--40 telescope product was opened, the boxcar bank was
prospectively expanded to `[1, 3, 5, 9, 17, 33, 65, 129]` channels. At the
selected drift proxy, one integration spans approximately 34.669 channels;
the broader bank also preserves the rank-40 design envelope of approximately
112.171 channels. Fresh fixed seeds are `3620260826` for scrambles and
`362120260826` for completeness.

Detector v0.5.0 has one known presentation-only limitation: its generic
`interpretation_limits` sentence names the legacy `[1, 3, 5, 9]` subset. It
does not control computation. The normative M36 bank is the eight-entry
configuration value and emitted `search_dimensions` field, both verified by
workflow. The frozen detector code will not be changed post hoc to edit that
sentence.

Before extraction, the execution workflow must also pass prospective
known-answer checks showing that a 129-channel rectangular signal selects the
129-channel filter and a 35-channel signal, representative of the selected
drift proxy, selects the neighboring 33-channel filter.

The detector will evaluate approximately **1,202,587,680 nominal trials**:
five windows of 357,913 rest-frequency bins, 21 motion templates, four
activity subsets, and eight widths. The empirical 256-scramble calibration
uses the identical complete search, so the added look-elsewhere burden is
included in the operational threshold.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m36_1400p5` | 1399.2--1401.8 | 1400.5 | 500 |
| `m36_1406p5` | 1405.2--1407.8 | 1406.5 | 500 |
| `m36_1412p5` | 1411.2--1413.8 | 1412.5 | 500 |
| `m36_1418p5` | 1417.2--1419.8 | 1418.5 | 500 |
| `m36_1425p0` | 1423.7--1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, widths, seeds, completeness, and report
retention may not change in response to data. A cluster above the empirical
global threshold survives only if none of the frozen matched-control,
single-adjacent-control, local-control, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 36 as a primary-cadence null result. Any survivor
must remain an unresolved case requiring genuinely independent data. No second
qualifying HIP 48714 cadence exists, so this milestone cannot perform or claim
independent recurrence. Any conclusion is limited to the frozen scope and
measured completeness.

Milestone 33 remains independently unresolved and is not changed by this run.
Milestone 35's end-to-end calibration limitations also remain: M36 alone does
not justify a new population occurrence bound or an EIRP statement.
