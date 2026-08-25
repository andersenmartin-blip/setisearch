# Milestone 31 target and cadence selection

Status: **FROZEN BEFORE HD 192263 SPECTRAL CONTACT**.

Milestone 31 applied the preregistered header-only rule to the first five
higher-smearing hosts preserved in the Milestone 16 discovery result. The
screen read identities, timing, HDF5 attributes, and geometry, but no spectral
dataset values.

## Mechanical target selection

| Extension rank | Host | Header-screen result | Milestone 31 status |
|---:|---|---|---|
| 31 | HD 192263 | one complete L-band cadence | **selected** |
| 32 | GJ 338 B | no qualifying L-band cadence | ineligible |
| 33 | HD 99492 | one complete L-band cadence | retained for later |
| 34 | HD 3651 | one complete L-band cadence | retained for later |
| 35 | Gl 49 | no qualifying L-band cadence | ineligible |

HD 192263 b supplies the motion template. The archive target is HIP 99711 at
19.6359 pc. Its frozen discovery record has period 24.3556 days, semimajor
axis 0.15 au, eccentricity 0.05, periastron epoch BJD 2451979.28, and
longitude of periastron 20 degrees. The conservative periastron drift proxy is
1.05365446 Hz/s at 1425 MHz.

## Fixed primary cadence

The sole qualifying HD 192263 cadence is archive cadence `--66435`, beginning
at MJD 57683.92162037037 (2016-10-22 22:07:08 UTC). It contains three HIP99711
ON scans alternating with controls HIP100159, HIP100786, and HIP98698.

All six products share shape `[16, 1, 322961408]`, float32 dtype,
18.253611008 s integration time, 2.793967724 Hz channel spacing, and coverage
from 1023.925784044 to 1926.269531250 MHz. Public URLs, sizes, ETags, sources,
times, and geometry are preserved in
`results_m31_header_screen/header_screen.json`.

## Frozen provenance and boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 31 header-screen result SHA-256:
  `ee169decd0ec0309a274295579241013fa95dc3f088bf4405724f5261b9710f8`
- header-screen workflow run: `32867230503`
- artifact: `9570603163`, verified digest
  `sha256:2535ae0c218bb6418f6001374445b620ad8d808c6ab51e8fa9ecb85cae7e1ce0`
- no HD 192263 spectral dataset value has been read or indexed.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected HD 192263 b orbit and host astrometry. The later target-specific
preregistration must use the already frozen higher-smearing width bank
`[1, 3, 5, 9, 17, 33]`, a non-truncating report cap, fresh seeds, and a
coverage proof before spectral contact. No second qualifying HD 192263 cadence
exists, so Milestone 31 cannot establish independent recurrence.

