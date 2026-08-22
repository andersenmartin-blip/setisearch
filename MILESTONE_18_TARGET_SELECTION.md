# Milestone 18 target and cadence selection

**FROZEN BEFORE GJ 649 SPECTRAL CONTACT**

Milestone 18 advances the next eligible unsearched host from the preregistered
Milestone 16 catalogue and HDF5-header screens. Those screens were performed
without reading any telescope spectral dataset value.

## Fixed target rule

The Milestone 16 ranking retained low-smearing exoplanet hosts in increasing
distance order and screened the first five unique hosts. After completion of
the HD 219134 and GJ 849 searches, the first still-unsearched host with a
complete compatible GBT L-band ABACAD cadence is selected:

| Ranked host | Screen result | Milestone 18 status |
|---|---|---|
| GJ 876 | only S-band products | ineligible for the established L-band windows |
| HD 219134 | five L-band cadences | searched in Milestone 16 |
| GJ 514 | only S-band products | ineligible for the established L-band windows |
| GJ 849 | two complete L-band cadences | searched in Milestone 17 |
| GJ 649 | one complete L-band cadence | **selected** |

GJ 649 b supplies the motion template. The archive target is HIP 83043 at
10.3796 pc. Its frozen discovery record has period 600.1 days, semimajor axis
1.112 au, eccentricity 0.083, periastron epoch BJD 2412876.0, and longitude of
periastron 3 degrees. The conservative periastron drift proxy is only
0.01381 Hz/s at 1425 MHz.

## Fixed cadence

The sole qualifying cadence is the primary held-out search:

| Role | Archive cadence | Start MJD | UTC date | Sequence |
|---|---|---:|---|---|
| Primary held-out search | `--70291` | 57513.354618055560 | 2016-05-05 | A-B-A-C-A-D |

It contains three HIP 83043 ON scans interleaved with HIP 82185, HIP 82240,
and HIP 82354 OFF scans. Header geometry, object identities, URLs, sizes,
ETags, and timing are already preserved in
`results_m16_header_screen_corrected/header_screen.json`.

No second complete compatible public cadence exists in the frozen screen.
Consequently, a primary-cadence survivor may receive only a separately frozen
within-cadence morphology review; it cannot be described as independently
recurrent unless later public data provide a distinct observation.

## Frozen provenance

- Discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Corrected header-screen result SHA-256:
  `c441713192397b1e7cbf4565a8ef26c57406c436f8cac1833f7cb54ca6342333`
- No GJ 649 spectral dataset value has been read, extracted, plotted,
  summarized, or searched.

The next permitted action is an exact official NASA Exoplanet Archive query
for the selected GJ 649 b orbit and host astrometry. Search bands, seeds,
extraction geometry, and detector settings will be frozen only after that
record is published and before any primary-cadence spectral extraction.
