# Milestone 29 target and cadence selection

Status: **FROZEN BEFORE HD 11964 SPECTRAL CONTACT**.

Milestone 29 applied the unchanged five-target rule to the final ranks in the
Milestone 16 low-smearing discovery result. The header screen read public
identities, timing, HDF5 attributes, and geometry but no spectral dataset
values.

## Mechanical target selection

| Frozen rank | Host | Header-screen result | Milestone 29 status |
|---:|---|---|---|
| 26 | BD-11 4672 | one S-band cadence | ineligible |
| 27 | 51 Eri | one S-band cadence | ineligible |
| 28 | HD 11964 | one complete L-band cadence | **selected** |
| 29 | bet UMi | one complete L-band cadence; one S-band cadence | retained for later |
| 30 | HD 1690 | one S-band cadence | ineligible |

HD 11964 b supplies the motion template. The archive target is HIP 9094 at
33.5369 pc. Its frozen discovery record has period 1945 days, semimajor axis
3.16 au, eccentricity 0.041, periastron epoch BJD 2454170, and longitude of
periastron 26 degrees. The conservative periastron drift proxy is
0.00341556 Hz/s at 1425 MHz.

## Fixed primary cadence

The sole qualifying HD 11964 cadence is archive cadence `--66653`, beginning
at MJD 57746.02050925926 (2016-12-24 00:29:32 UTC). It contains three HIP9094
ON scans alternating with controls HIP10172, HIP8092, and HIP8144.

All six qualifying products share shape `[16, 1, 322961408]`, float32 dtype,
18.253611008 s integration time, 2.793967724 Hz channel spacing, and coverage
from 1023.925784044 to 1926.269531250 MHz. Public URLs, sizes, ETags, sources,
times, and geometry are preserved in
`results_m29_header_screen/header_screen.json`.

## Frozen provenance and boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 29 header-screen result SHA-256:
  `81d6df50f94f6970494b57e414a091d234600f9ee04daf76772919412bbed592`
- header-screen workflow run: `32755739577`
- artifact: `9530790490`, verified digest
  `sha256:9c888d3ef27e622385ded9fd51ad1b3e238910923ee2758f09b9aa84f163fdfd`
- no HD 11964 spectral dataset value has been read or indexed.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected HD 11964 b orbit and host astrometry. Search bands, extraction
geometry, seeds, thresholds, report retention, and detector settings must
then be frozen with a target-specific coverage proof before spectral contact.
No second qualifying HD 11964 cadence exists in the frozen screen, so
Milestone 29 cannot establish independent recurrence.
