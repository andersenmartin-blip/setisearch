# Milestone 33 target and cadence selection

Status: **FROZEN BEFORE HD 3651 SPECTRAL CONTACT**.

Milestone 33 advances the already frozen Milestone 31 higher-smearing screen.
Milestones 31 and 32 consumed extension ranks 31 and 33, while rank 32 had no
qualifying L-band cadence. **HD 3651 / HIP 3093 at rank 34 is therefore the
next eligible untouched host**. This selection reads only the committed header
screen; it performs no new telescope access and reads no spectral value.

## Mechanical target selection

| Extension rank | Host | Frozen header-screen result | Milestone 33 status |
|---:|---|---|---|
| 31 | HD 192263 | one complete L-band cadence | consumed by Milestone 31 |
| 32 | GJ 338 B | no qualifying L-band cadence | ineligible |
| 33 | HD 99492 | one complete L-band cadence | consumed by Milestone 32 |
| 34 | HD 3651 | one complete L-band cadence | **selected** |
| 35 | Gl 49 | no qualifying L-band cadence | ineligible |

HD 3651 b supplies only the motion template. The frozen discovery record has
period 62.25 days, semimajor axis 0.295 au, eccentricity 0.645, periastron
epoch BJD 2453932.2, and longitude of periastron 243.0 degrees. Its
conservative full-projection periastron drift proxy is 2.27163433 Hz/s at
1425 MHz.

## Fixed primary cadence

The sole qualifying cadence is archive cadence `--73274`, beginning at MJD
57557.577152777776 (2016-06-18 13:51:06 UTC). It contains the sequence:

`HIP3093 -- HIP2023 -- HIP3093 -- HIP2206 -- HIP3093 -- HIP2360`.

All six products have shape `[16, 1, 322961408]`, float32 dtype,
18.253611008 s integrations, 2.793967724 Hz channel spacing, and coverage from
1023.925784044 to 1926.269531250 MHz. Exact URLs, byte sizes, ETags, source
names, times, and HDF5 geometry are already preserved in
`results_m31_header_screen/header_screen.json`.

## Frozen method and boundary

The six-width higher-smearing bank `[1, 3, 5, 9, 17, 33]` remains frozen.
At the conservative drift proxy, one integration traverses approximately
14.84 native channels, so the pre-data bank covers the expected smearing
without a target-responsive extension. Detector v0.5.0, the 21 motion
templates, four activity subsets, five 1 MHz windows, physical control-field
vetoes, complete scrambles, and the completeness procedure remain unchanged.

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- higher-smearing header-screen SHA-256:
  `ee169decd0ec0309a274295579241013fa95dc3f088bf4405724f5261b9710f8`
- header-screen workflow run: `32867230503`
- artifact: `9570603163`, digest
  `sha256:2535ae0c218bb6418f6001374445b620ad8d808c6ab51e8fa9ecb85cae7e1ce0`
- `spectral_payload_inspected`: false
- `spectral_dataset_values_read`: false

The next permitted action is the exact NASA Exoplanet Archive composite query
for HD 3651 b and its host. A target-specific motion-plus-width coverage proof
and a new preregistration must pass before cadence `--73274` is opened.
