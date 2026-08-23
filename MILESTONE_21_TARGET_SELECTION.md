# Milestone 21 target and cadence selection

Status: **FROZEN BEFORE HD 154345 SPECTRAL CONTACT**.

Milestone 21 applies the target-extension rule committed before the rank 11-15
header screen. That screen read no spectral dataset values.

## Mechanical target selection

| Frozen rank | Host | Header-screen result | Milestone 21 status |
|---:|---|---|---|
| 11 | 14 Her | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible for the established L-band windows |
| 12 | HD 154345 | one complete L-band cadence | **selected** |
| 13 | HD 87883 | one complete L-band cadence; second cadence is S-band | retained for a later milestone |
| 14 | HD 217107 | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible |
| 15 | alf Ari | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible |

HD 154345 b supplies the motion template. The archive target is HIP 83389 at
18.284 pc. Its frozen discovery record has period 3,280 days, semimajor axis
4.158 au, eccentricity 0.058, periastron epoch BJD 2458230.0, and longitude of
periastron 309 degrees. The conservative periastron drift proxy is
0.00163790 Hz/s at 1425 MHz.

## Fixed cadence

The sole qualifying HD 154345 cadence is the primary held-out search:

| Role | Archive cadence | Start MJD | UTC start | Sequence |
|---|---|---:|---|---|
| Primary held-out search | `--85132` | 57470.51048611111 | 2016-03-23 12:15:06 | A-B-A-B-A-B |

It contains three HIP 83389 ON scans interleaved with three `HIP83389_OFF`
scans. All six products share shape 16 x 1 x 264,503,296, float32 dtype,
17.986224128 s integration time, 2.835503418 Hz channel spacing, and coverage
from 1126.464846586 to 1876.464843750 MHz. Header geometry, URLs, sizes, ETags,
and timing are preserved in
`results_m21_header_screen/header_screen.json`.

No second complete compatible cadence for HD 154345 appears in the frozen
screen. A primary-cadence survivor may therefore receive only a separately
frozen within-cadence morphology review; it cannot be described as
independently recurrent without a distinct later public observation.

## Frozen provenance and next boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 21 header-screen result SHA-256:
  `f15f1718dfcd82c868478e489257a2127c5584bbd8bb62178e4e4a1cffc2831a`
- header-screen workflow run: `32622460973`
- artifact: `9488785797`, verified digest
  `sha256:1230c69d9c12a9ae62b6296691c5a7a9096867bc04a762928288b5a0cf341c19`
- no HD 154345 spectral dataset value has been read, extracted, plotted,
  summarized, or searched.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected HD 154345 b orbit and host astrometry. Search bands, extraction
geometry, seeds, thresholds, and detector settings remain unchanged and will
be frozen with the target-specific coverage proof before any spectral
extraction.
