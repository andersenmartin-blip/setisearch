# Milestone 36 target and cadence selection

Status: **FROZEN BEFORE HIP 48714 SPECTRAL CONTACT**.

Milestone 36 applied the preregistered HDF5-header-only rule to discovery
extension ranks 36--40. The screen read archive records, object identities,
HTTP metadata, HDF5 attributes, timing, and geometry. It did not index or read
any HDF5 spectral dataset value.

## Mechanical target selection

| Extension rank | Host | Header-screen result | Milestone 36 status |
|---:|---|---|---|
| 36 | HIP 48714 | one complete compatible L-band cadence | **selected** |
| 37 | HD 156668 | one complete compatible L-band cadence | retained for later |
| 38 | HD 1461 | one complete compatible L-band cadence | retained for later |
| 39 | 51 Peg | no qualifying cadence | ineligible |
| 40 | tau Boo | no qualifying cadence | ineligible |

HIP 48714 b supplies the motion template. The archive target is `HIP48714` at
10.5298 pc. Its frozen discovery record has period 17.818 days, semimajor axis
0.112 au, eccentricity 0.5, periastron epoch BJD 2451539.8, and longitude of
periastron 202 degrees. The conservative periastron drift proxy is
5.30654596 Hz/s at 1425 MHz.

Rank 36 has two catalogue cadence references. Cadence `--68360` covers about
1797.949--2802.832 MHz and therefore does not cover the established guarded
L-band search windows. Cadence `--76348` is the sole qualifying rank-36
cadence and is selected without inspecting spectral values.

## Fixed primary cadence

The primary cadence is archive cadence `--76348`, beginning at MJD
57619.72236111111 (2016-08-19 17:20:12 UTC). It contains three HIP 48714 ON
scans alternating with controls HIP 47655, HIP 47791, and HIP 48132.

All six products have shape `[16, 1, 322961408]`, float32 dtype,
18.253611008 s integrations, 2.793967724 Hz channel spacing, and coverage from
1023.925784044 to 1926.269531250 MHz. Public URLs, sizes, ETags, sources,
times, and geometry are preserved in
`results_m36_header_screen/header_screen.json`.

At the selected drift proxy, one integration spans approximately 34.669
channels. The prospectively frozen higher-smearing boxcar bank
`[1, 3, 5, 9, 17, 33, 65, 129]` therefore includes the next wider template.
The frozen report cap is 2200, above the exact finite maximum of 2016 retained
pre-clustering hypothesis peaks per window.

## Frozen provenance and boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 36 header-screen result SHA-256:
  `45bd84cad0c83e8079ad3fe204ca827c7213954f43121599fbeac893252db19b`
- protocol commit: `71d2e032f12b63c7d66bf4400663c403bfc8511d`
- checked header-screen workflow run: `32987209536`
- artifact: `9613347814`, verified digest
  `6082faeb54f41b2ee45b00a8c7c8637fcd1e56854ed21272f739026253f9d5ba`
- canonical result commit: `ee24e87944c27d7b47e7b6fccc764b958945318a`
- no HIP 48714 spectral dataset value has been read, extracted, plotted,
  summarized, or searched.

The next permitted action is the exact selected-record query against the NASA
Exoplanet Archive. A target-specific coverage proof and preregistration must
then be frozen before any spectral contact. No second qualifying HIP 48714
cadence exists, so Milestone 36 cannot establish independent recurrence.
