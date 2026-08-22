# Milestone 17 target and cadence selection

**FROZEN BEFORE GJ 849 SPECTRAL CONTACT**

Milestone 17 advances the next eligible unsearched host from the preregistered
Milestone 16 catalogue and HDF5-header screens. Those screens were performed
without reading any telescope spectral dataset value.

## Fixed target rule

The Milestone 16 ranking retained low-smearing exoplanet hosts in increasing
distance order and screened the first five unique hosts. After completion of
the HD 219134 search, the first still-unsearched host with a complete compatible
GBT L-band ABACAD cadence is selected:

| Ranked host | Screen result | Milestone 17 status |
|---|---|---|
| GJ 876 | only S-band products | ineligible for the established L-band windows |
| HD 219134 | five L-band cadences | searched in Milestone 16 |
| GJ 514 | only S-band products | ineligible for the established L-band windows |
| GJ 849 | two complete L-band cadences | **selected** |
| GJ 649 | one complete L-band cadence | retained for a later milestone |

GJ 849 b supplies the motion template. The archive target is HIP 109388 at
8.80058 pc. Its catalogue orbit has period 1925.31 days, semimajor axis
2.32 au, eccentricity 0.029, periastron epoch BJD 2453770.0, and longitude of
periastron 111 degrees. The conservative periastron drift proxy is only
0.00250 Hz/s at 1425 MHz.

## Fixed cadence split

The earliest qualifying cadence is the primary held-out search. The second is
reserved and may not be opened spectrally unless a separately frozen targeted
recurrence protocol is triggered by the primary result.

| Role | Archive cadence | Start MJD | UTC date | Sequence |
|---|---|---:|---|---|
| Primary held-out search | `--73890` | 57574.432534722226 | 2016-07-05 | A-B-A-C-A-D |
| Reserved independent cadence | `--74424` | 57580.390266203710 | 2016-07-11 | A-B-A-C-A-D |

The cadence starts are separated by approximately 5.958 days. Both contain
three HIP 109388 ON scans interleaved with the same three distinct OFF-source
identities. Header geometry, object identities, URLs, sizes, ETags, and timing
are already preserved in
`results_m16_header_screen_corrected/header_screen.json`.

## Frozen provenance

- Discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Corrected header-screen result SHA-256:
  `c441713192397b1e7cbf4565a8ef26c57406c436f8cac1833f7cb54ca6342333`
- No GJ 849 spectral dataset value has been read, extracted, plotted,
  summarized, or searched.

The next permitted action is an exact official NASA Exoplanet Archive query
for the selected GJ 849 b orbit and host astrometry. Search bands, seeds,
extraction geometry, and detector settings will be frozen only after that
record is published and before any primary-cadence spectral extraction.
