# Milestone 26 target and cadence selection

Status: **FROZEN BEFORE HD 19994 SPECTRAL CONTACT**.

Milestone 26 advances the unchanged rank 21-25 rule committed before the
Milestone 25 header screen. That screen read public identities, timing, HDF5
attributes, and geometry but no spectral dataset values.

## Mechanical target selection

| Frozen rank | Host | Header-screen result | Milestone 26 status |
|---:|---|---|---|
| 21 | HD 164922 | one complete L-band cadence; one S-band cadence | completed in Milestone 25 |
| 22 | HD 19994 | one complete L-band cadence; one S-band cadence | **selected** |
| 23 | HD 127506 | one complete L-band cadence; one S-band cadence | retained for later |
| 24 | psi1 Dra B | one complete L-band cadence; one S-band cadence | retained for later |
| 25 | AF Lep | two S-band cadences | ineligible |

HD 19994 b supplies the motion template. The archive target is HIP 14954 at
22.5242 pc. Its frozen discovery record has period 466.2 days, semimajor axis
1.305 au, eccentricity 0.063, periastron epoch BJD 2453757.0, and longitude
of periastron 346 degrees. The conservative periastron drift proxy is
0.0257181 Hz/s at 1425 MHz.

## Fixed primary cadence

The sole qualifying cadence is archive cadence `--84358`, beginning at MJD
57436.981041666666 (2016-02-18 23:32:42 UTC). It contains three HIP14954 ON
scans alternating with three `HIP14954_OFF` controls. Cadence `--63712` is
S-band and does not cover the established L-band windows.

All six qualifying products share shape `[16, 1, 264503296]`, float32 dtype,
17.986224128 s integration time, 2.835503418 Hz channel spacing, and coverage
from 1126.464846586 to 1876.464843750 MHz. Public URLs, sizes, ETags, sources,
times, and geometry are preserved in
`results_m25_header_screen/header_screen.json`.

## Frozen provenance and boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 25 header-screen result SHA-256:
  `f9d3b2b75cb6bb49a278b7b97f1d2163d03f054282b0e5904ed6fffe15756748`
- header-screen workflow run: `32655523963`
- artifact: `9497345233`, verified digest
  `sha256:9b899ee399619198b7da8d552220a2499f6c8726a73e85653ae862b35402ed2d`
- no HD 19994 spectral dataset value has been read or indexed.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected HD 19994 b orbit and host astrometry. Search bands, extraction
geometry, seeds, thresholds, report retention, and detector settings must
then be frozen with a target-specific coverage proof before spectral contact.
No second qualifying HD 19994 L-band cadence exists in the frozen screen, so
Milestone 26 cannot establish independent recurrence.
