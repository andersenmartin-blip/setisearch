# Milestone 16 selected-target metadata completion

Status: **FIXED BEFORE TARGET CONFIGURATION**.

The corrected header screen selected HD 219134 h / HIP114622 cadence `--63424`.
This step queries exactly one official NASA Exoplanet Archive `pscomppars`
record for `HD 219134 h` and records only the orbit and host astrometric fields
required by the frozen detector. It does not contact a telescope product or
inspect a spectral value.

The result may be combined with the already published selected-cadence HDF5
headers to construct a target-specific preflight configuration. No field may
be substituted from another planet row or inferred from the spectral data.
