# Milestone 23 target and cadence selection

Status: **FROZEN BEFORE HD 33564 SPECTRAL CONTACT**.

Milestone 23 applies the target-extension rule committed before the rank 16-20
header screen. That screen read no spectral dataset values.

## Mechanical target selection

| Frozen rank | Host | Header-screen result | Milestone 23 status |
|---:|---|---|---|
| 16 | BD-06 1339 | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible for the established L-band windows |
| 17 | HD 33564 | two complete L-band cadences; third cadence is S-band | **selected** |
| 18 | HD 114783 | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible |
| 19 | 16 Cyg B | one complete L-band cadence | retained for a later milestone |
| 20 | HD 210277 | complete fine cadence, but 1797.949-2802.832 MHz only | ineligible |

HD 33564 b supplies the motion template. The archive target is HIP 25110 at
20.9531 pc. Its frozen discovery record has period 388 days, semimajor axis
1.1 au, eccentricity 0.34, periastron epoch BJD 2452603.0, and longitude of
periastron 205 degrees. The conservative periastron drift proxy is
0.0630802 Hz/s at 1425 MHz.

## Fixed cadences

The earliest qualifying cadence is the blind primary search. The later
qualifying cadence remains spectrally untouched and may be opened only under a
separately frozen recurrence rule after a primary survivor.

| Role | Archive cadence | Start MJD | UTC start | Sequence |
|---|---|---:|---|---|
| Primary held-out search | `--71505` | 57526.757002314815 | 2016-05-18 18:10:05 | A-B-A-C-A-D |
| Reserved independent recurrence | `--71747` | 57532.773726851854 | 2016-05-24 18:34:10 | A-B-A-C-A-D |

Both contain three HIP 25110 ON scans interleaved with HIP 24440, HIP 25714,
and HIP 26097 OFF scans. All products share shape 16 x 1 x 318,230,528,
float32 dtype, 17.986224128 s integration time, 2.835503418 Hz channel
spacing, and coverage from 1023.925784086 to 1926.269531250 MHz. Header
geometry, public object identities, URLs, sizes, ETags, and timing are
preserved in `results_m23_header_screen/header_screen.json`.

The third frozen HD 33564 cadence, `--81065`, is S-band and does not cover the
established L-band windows. The reserved cadence is six days later and can
provide a genuine independent-night recurrence test if the primary search
leaves an unresolved survivor.

## Frozen provenance and next boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 23 header-screen result SHA-256:
  `1df2df247e77747a297e4df2ff0c7d77339275b4fa15dddf007080859ae7fce7`
- header-screen workflow run: `32648728539`
- artifact: `9495587116`, verified digest
  `sha256:0235063cbc3d72beb6e836bdfeb451fdf979c123752b5e9c2981365c23fc1bec`
- no HD 33564 spectral dataset value has been read, extracted, plotted,
  summarized, or searched.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected HD 33564 b orbit and host astrometry. Search bands, extraction
geometry, seeds, thresholds, and detector settings remain unchanged and will
be frozen with the target-specific coverage proof before any spectral
extraction.
