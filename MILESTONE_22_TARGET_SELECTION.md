# Milestone 22 target and cadence selection

Status: **FROZEN BEFORE HD 87883 SPECTRAL CONTACT**.

Milestone 22 advances mechanically from the target order and header evidence
published in Milestone 21. That screen read no spectral dataset values.

## Fixed target rule

| Frozen rank | Host | Header-screen result | Status after Milestone 21 |
|---:|---|---|---|
| 11 | 14 Her | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible for the established L-band windows |
| 12 | HD 154345 | one complete L-band cadence | searched in Milestone 21 |
| 13 | HD 87883 | one complete L-band cadence; second cadence is S-band | **selected** |
| 14 | HD 217107 | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible |
| 15 | alf Ari | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible |

HD 87883 b supplies the motion template. The archive target is HIP 49699 at
18.2912 pc. Its frozen discovery record has period 3,006 days, semimajor axis
3.77 au, eccentricity 0.72, periastron epoch BJD 2456913.0, and longitude of
periastron 282.1 degrees. The conservative periastron drift proxy is
0.0200124 Hz/s at 1425 MHz.

## Fixed cadence

The sole qualifying HD 87883 cadence is the primary held-out search:

| Role | Archive cadence | Start MJD | UTC start | Sequence |
|---|---|---:|---|---|
| Primary held-out search | `--70933` | 57521.024351851855 | 2016-05-13 00:35:04 | A-B-A-C-A-D |

It contains three HIP 49699 ON scans interleaved with HIP 48952, HIP 49056,
and HIP 49066 OFF scans. All six products share shape 16 x 1 x 318,230,528,
float32 dtype, 17.986224128 s integration time, 2.835503418 Hz channel
spacing, and coverage from 1023.925784086 to 1926.269531250 MHz. Header
geometry, public object identities, URLs, sizes, ETags, and timing are
preserved in `results_m21_header_screen/header_screen.json`.

The other frozen HD 87883 cadence, `--78853`, is S-band and does not cover the
established L-band windows. A primary-cadence survivor may therefore receive
only a separately frozen within-cadence morphology review; it cannot be
described as independently recurrent without a distinct later public
observation.

## Frozen provenance and next boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 21 header-screen result SHA-256:
  `f15f1718dfcd82c868478e489257a2127c5584bbd8bb62178e4e4a1cffc2831a`
- no HD 87883 spectral dataset value has been read, extracted, plotted,
  summarized, or searched.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected HD 87883 b orbit and host astrometry. Search bands, extraction
geometry, detector settings, thresholds, controls, and stopping rules remain
unchanged and must be frozen with a successful coverage proof before any
spectral extraction.
