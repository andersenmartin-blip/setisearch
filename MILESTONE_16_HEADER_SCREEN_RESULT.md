# Milestone 16 corrected header-screen result

Status: **HD 219134 h / HIP114622 CADENCE `--63424` SELECTED**.

GitHub Actions run `32507313007` completed the corrected header-only screen.
Artifact `9455750075` (`milestone-16-header-screen-corrected`) has digest
`sha256:de05645e9a12313f538e9979b0a4b97450e2b24a9f8c7fc1c7025aa49b41e261`.
No HDF5 spectral dataset value was read.

## Screen outcome

| Rank | Target | Qualifying L-band HDF5 cadences | Outcome |
|---:|---|---:|---|
| 1 | GJ876 / GJ 876 e | 0 | S-band only: 1797.949-2802.832 MHz |
| 2 | HIP114622 / HD 219134 h | 5 | Selected; earliest qualifying cadence `--63424` |
| 3 | HIP65859 / GJ 514 b | 0 | S-band only: 1797.949-2802.832 MHz |
| 4 | HIP109388 / GJ 849 b | 2 | Qualifies but loses distance ranking |
| 5 | HIP83043 / GJ 649 b | 1 | Qualifies but loses distance ranking |

## Selected cadence

- archive target: `HIP114622`
- planet working template: HD 219134 h
- cadence: `http://seti.berkeley.edu/opendata/api/get-cadence/--63424`
- first scan: 2016-08-22 08:00:53 UTC, MJD 57622.33394675926
- sequence: Hip114622, Hip113498, Hip114622, Hip113772, Hip114622,
  Hip113789
- common HDF5 shape: 16 x 1 x 322,961,408 float32 values
- integration time: 18.253611008 s
- channel width: 2.793967724 Hz
- header frequency coverage: 1023.925784-1926.269531 MHz
- conservative full-projection periastron drift bound at 1425 MHz:
  0.00262 Hz/s

All six products responded without header errors, supported byte ranges, had
compatible geometry, and covered every established search band with the
required guard.

## Next boundary

The selected official planet/host record must be completed with the astrometric
fields already required by discovery, then a target-specific configuration and
630-case extraction-coverage proof must be published. Only after a separate
preregistration may the six selected HDF5 products be contacted spectrally.
