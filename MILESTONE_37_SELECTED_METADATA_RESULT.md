# Milestone 37 selected-target metadata result

Status: **OFFICIAL METADATA COMPLETE; NO SPECTRAL CONTACT**.

The exact frozen NASA Exoplanet Archive `pscomppars` query returned one
complete required-field record for HD 156668 b. Its identity, distance, and
five orbital fields exactly equal the previously published discovery values.
No telescope product was requested, and no HDF5 spectral dataset value was
indexed or read.

## Frozen official record

| Field | Value |
|---|---:|
| Planet / host | HD 156668 b / HD 156668 |
| Archive aliases | HIP 84607 / HD 156668 |
| ICRS coordinates | 17h17m40.40s, +29d13m41.38s |
| Decimal coordinates | 259.4183491 deg, +29.228161 deg |
| Distance / parallax | 24.3323 pc / 41.0687 mas |
| Proper motion | -72.6271, +216.769 mas/yr |
| Stellar radial velocity | -44.57335 km/s |
| Orbital period | 4.6455 d |
| Semimajor axis | 0.05 au |
| Eccentricity | 0.0 |
| Nominal periastron epoch | BJD 2454718.57 |
| Nominal periastron angle | 36 deg |

The composite record supplies the host astrometry and radial velocity required
by the coordinate transform. Because the composite eccentricity is zero, the
periastron epoch and angle do not define a physically unique orbital phase and
orientation. They may be used only as a reproducible parameterization of an
explicitly frozen template bank. The Milestone 37 motion design must therefore
either certify a phase-independent track cover or limit every result to its
exact discrete template bank.

The record is preserved verbatim in
`results_m37_selected_metadata/hd156668b.json` with SHA-256
`b4429646af5ca076778e052666868353eccd5f43def3c456da889378bd3f1ee4`.

## Provenance and boundary

- selection source commit: `c37c828a88ddc7a30a49a3f8d5c5d93371f2ad34`
- result publication commit: `269c213f256a48bc7f76ae042b98eaa85bf76008`
- workflow run: `33007853035`
- artifact: `9621276239`
- artifact digest:
  `sha256:785fb05c22c20777d26a5367a3a8e9ceb9c135cd1b3c306b57462df67eed1d61`
- result count: one exact named planet record
- metadata-result manifest SHA-256:
  `fa8009bbc16a269691a75cd8d45518992114c3e094a5fcda134fc2fff89cd280`
- provenance-record SHA-256:
  `4b79c3adf60c59306b630b6f851672a7471bda2e44ca6e22735b0badafc5fb56`
- `spectral_payload_inspected`: false
- `spectral_dataset_values_read`: false
- `telescope_remote_request_made`: false

The next permitted action is a metadata-only phase, motion, spectral-width,
and extraction-coverage proof using the six already published HDF5 headers.
It must not refresh the cadence catalogue or open a telescope product. The
detector v0.6.0 protocol, software, capacity limits, configuration, and
stopping rules must then be frozen separately before any spectral value is
read.
