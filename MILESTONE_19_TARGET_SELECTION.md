# Milestone 19 target and cadence selection

Status: **FROZEN BEFORE 47 UMa SPECTRAL CONTACT**.

Milestone 19 applies the target-extension rule committed before the rank 6-10
header screen. That screen read no spectral dataset values.

## Mechanical target selection

| Frozen rank | Host | Header-screen result | Milestone 19 status |
|---:|---|---|---|
| 6 | HD 147379 | S-band only | ineligible for the established L-band windows |
| 7 | 55 Cnc | L-band cadence incomplete; second cadence S-band | ineligible |
| 8 | 47 UMa | one complete L-band cadence | **selected** |
| 9 | HD 48948 | S-band only | ineligible |
| 10 | rho CrB | one complete L-band cadence | retained for a later milestone |

47 UMa d supplies the motion template. The archive target is HIP 53721 at
13.7967 pc. Its frozen discovery record has period 14,002 days, semimajor axis
11.6 au, eccentricity 0.16, periastron epoch BJD 2451736.0, and longitude of
periastron 110 degrees. The conservative periastron drift proxy is
0.00031534 Hz/s at 1425 MHz.

## Fixed cadence

The sole qualifying cadence is the primary held-out search:

| Role | Archive cadence | Start MJD | UTC start | Sequence |
|---|---|---:|---|---|
| Primary held-out search | `--73992` | 57578.02185185185 | 2016-07-09 00:31:28 | A-B-A-C-A-D |

It contains three HIP 53721 ON scans interleaved with HIP 52647, HIP 52881,
and HIP 53076 OFF scans. Header geometry, public object identities, URLs,
sizes, ETags, and timing are preserved in
`results_m19_header_screen/header_screen.json`.

No second complete compatible cadence for 47 UMa appears in the frozen
screen. A primary-cadence survivor may therefore receive only a separately
frozen within-cadence morphology review; it cannot be described as
independently recurrent without a distinct later public observation.

## Frozen provenance and next boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 19 header-screen result SHA-256:
  `20ced66ce1b0200d18df3c1a473c57f4a594b5367db5a1448889999cfe02bec1`
- no 47 UMa spectral dataset value has been read, extracted, plotted,
  summarized, or searched.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected 47 UMa d orbit and host astrometry. Search bands, extraction geometry,
seeds, thresholds, and detector settings remain unchanged and will be frozen
with the target-specific coverage proof before any spectral extraction.
