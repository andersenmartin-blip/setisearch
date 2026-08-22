# Milestone 20 target and cadence selection

Status: **FROZEN BEFORE RHO CRB SPECTRAL CONTACT**.

Milestone 20 advances mechanically from the target order and header evidence
published in Milestone 19. That screen read no spectral dataset values.

## Fixed target rule

| Frozen rank | Host | Header-screen result | Status after Milestone 19 |
|---:|---|---|---|
| 6 | HD 147379 | S-band only | ineligible for the established L-band windows |
| 7 | 55 Cnc | incomplete L-band cadence; second cadence S-band | ineligible |
| 8 | 47 UMa | one complete L-band cadence | searched in Milestone 19 |
| 9 | HD 48948 | S-band only | ineligible |
| 10 | rho CrB | one complete L-band cadence | **selected** |

rho CrB c supplies the motion template. The archive target is HIP 78459 at
17.4671 pc. Its frozen discovery record has period 102.036 days, semimajor
axis 0.4206 au, eccentricity 0.048, periastron epoch BJD 2455480.216, and
longitude of periastron 244.4 degrees. The conservative periastron drift proxy
is 0.16763 Hz/s at 1425 MHz.

## Fixed cadence

The sole qualifying cadence is the primary held-out search:

| Role | Archive cadence | Start MJD | UTC start | Sequence |
|---|---|---:|---|---|
| Primary held-out search | `--71771` | 57533.22770833333 | 2016-05-25 05:27:54 | A-B-A-C-A-D |

It contains three HIP 78459 ON scans interleaved with HIP 78859, HIP 78931,
and HIP 79053 OFF scans. All six products have matching shape, dtype,
integration time, and channel width and cover the complete guarded range.
Their public identities, URLs, sizes, ETags, timing, and headers are preserved
in `results_m19_header_screen/header_screen.json`.

No second complete compatible rho CrB cadence appears in the frozen screen.
A primary-cadence survivor may receive only a separately frozen within-cadence
morphology review; it cannot be described as independently recurrent without
a distinct later public observation.

## Frozen provenance and next boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 19 header-screen result SHA-256:
  `20ced66ce1b0200d18df3c1a473c57f4a594b5367db5a1448889999cfe02bec1`
- no rho CrB spectral dataset value has been read, extracted, plotted,
  summarized, or searched.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected rho CrB c orbit and host astrometry. Search bands, extraction
geometry, detector settings, thresholds, controls, and stopping rules remain
unchanged and must be frozen with a successful coverage proof before any
spectral extraction.
