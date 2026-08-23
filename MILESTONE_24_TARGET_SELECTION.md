# Milestone 24 target and cadence selection

Status: **FROZEN BEFORE 16 CYG B SPECTRAL CONTACT**.

Milestone 24 advances mechanically within the rank 16-20 extension that was
committed and screened, using HDF5 headers only, before Milestone 23 inspected
any spectral values. Milestone 23 searched the qualifying rank-17 host HD
33564 and left no survivor. Its later independent cadence remains reserved for
HD 33564 and is not repurposed.

## Mechanical target selection

| Frozen rank | Host | Header-screen result | Status after Milestone 23 |
|---:|---|---|---|
| 16 | BD-06 1339 | complete fine cadence, but S-band only | ineligible |
| 17 | HD 33564 | two complete L-band cadences | searched in Milestone 23; no survivor |
| 18 | HD 114783 | complete fine cadence, but S-band only | ineligible |
| 19 | 16 Cyg B | one complete L-band cadence | **selected for Milestone 24** |
| 20 | HD 210277 | complete fine cadence, but S-band only | ineligible |

No target is reranked and no telescope or planet catalogue is consulted to
alter this order. The frozen discovery result is
`results_m16_discovery/discovery.json` with SHA-256
`0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`.
The header-only screen is `results_m23_header_screen/header_screen.json` with
SHA-256
`1df2df247e77747a297e4df2ff0c7d77339275b4fa15dddf007080859ae7fce7`.

## Fixed primary cadence

The sole qualifying cadence is archive cadence `--67109`, beginning at MJD
57755.900821759256 (2017-01-02 21:37:11 UTC). It is a complete A-B-A-C-A-D
sequence with three HIP 96901 ON scans interleaved with HIP 95737, HIP 95853,
and HIP 95872 OFF scans.

All six products have shape `[16, 1, 322961408]`, float32 dtype,
18.253611008 s integrations, 2.793967724 Hz channel spacing, and frequency
coverage from 1023.925784044 to 1926.269531250 MHz. Public URLs, sizes, ETags,
sources, timestamps, and HDF5 attributes were preserved by the prior screen.
Every screen record states that no spectral dataset value was read.

16 Cyg B b supplies only the motion template. The search does not assume that
an emitter is located on the planet or aimed at Earth.

## Boundary

The next permitted action is an exact official NASA Exoplanet Archive query
for the 16 Cyg B b composite orbit and host astrometry. After that, a
target-specific 630-case extraction-coverage proof must pass and the complete
search configuration, thresholds, controls, seeds, and stopping rules must be
committed before any HDF5 `data` value is indexed or read.

There is no second qualifying 16 Cyg B cadence in the frozen screen. Therefore
Milestone 24 can produce a primary-cadence result but cannot claim independent
recurrence from this archive selection. Any surviving case must stop at
candidate status pending genuinely independent data.
