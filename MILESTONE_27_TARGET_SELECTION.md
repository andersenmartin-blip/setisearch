# Milestone 27 target and cadence selection

Status: **FROZEN BEFORE HD 127506 SPECTRAL CONTACT**.

Milestone 27 advances the unchanged rank 21-25 rule committed before the
Milestone 25 header screen. That screen read public identities, timing, HDF5
attributes, and geometry but no spectral dataset values.

## Mechanical target selection

| Frozen rank | Host | Header-screen result | Milestone 27 status |
|---:|---|---|---|
| 21 | HD 164922 | one complete L-band cadence; one S-band cadence | completed in Milestone 25 |
| 22 | HD 19994 | one complete L-band cadence; one S-band cadence | completed in Milestone 26 |
| 23 | HD 127506 | one complete L-band cadence; one S-band cadence | **selected** |
| 24 | psi1 Dra B | one complete L-band cadence; one S-band cadence | retained for later |
| 25 | AF Lep | two S-band cadences | ineligible |

HD 127506 b supplies the motion template. The archive target is HIP 70950 at
22.5279 pc. Its frozen discovery record has period 65.78395 days, semimajor
axis 0.287 au, eccentricity 0.24, periastron epoch BJD 2456787.645, and
longitude of periastron 56.147 degrees. The conservative periastron drift
proxy is 0.431784 Hz/s at 1425 MHz.

## Fixed primary cadence

The sole qualifying cadence is archive cadence `--83509`, beginning at MJD
57927.10760416667 (2017-06-23 02:34:57 UTC). It contains three HIP70950 ON
scans alternating with archival controls HIP70142, HIP70297, and HIP70334.
Cadence `--69234` is S-band and does not cover the established L-band windows.

All six qualifying products share shape `[16, 1, 322961408]`, float32 dtype,
18.253611008 s integration time, 2.793967724 Hz channel spacing, and coverage
from 1023.925784044 to 1926.269531250 MHz. Public URLs, sizes, ETags, sources,
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
- no HD 127506 spectral dataset value has been read or indexed.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected HD 127506 b orbit and host astrometry. Search bands, extraction
geometry, seeds, thresholds, report retention, and detector settings must
then be frozen with a target-specific coverage proof before spectral contact.
No second qualifying HD 127506 L-band cadence exists in the frozen screen, so
Milestone 27 cannot establish independent recurrence.
