# Milestone 29 selected metadata: HD 11964 b

Status: **OFFICIAL TARGET RECORD ACQUIRED WITHOUT SPECTRAL CONTACT**.

GitHub Actions run `32756178424` queried the NASA Exoplanet Archive
`pscomppars` composite table for exactly `HD 11964 b`. Artifact
`9530921366`, named `milestone-29-selected-metadata`, has verified digest
`sha256:6285221d1d73a544843c7749b859b08b4cb3227f97b515bcfaf537a6e01bde1f`.

The returned host record is HD 11964 / HIP 9094 at RA 01h57m09.22s, Dec
-10d14m36.49s, distance 33.5369 pc, and parallax 29.789 mas. Proper motion is
(-366.957, -242.431) mas/yr and stellar radial velocity is -9.31811 km/s.

The composite HD 11964 b orbit has period 1945 days, semimajor axis 3.16 au,
eccentricity 0.041, periastron epoch BJD 2454170, and longitude of periastron
26 degrees. These values define only a working motion template.

The exact query, API URL, record, and explicit `spectral_payload_inspected:
false` boundary are preserved in
`results_m29_selected_metadata/hd11964b.json`, SHA-256
`7e115168f1e6e02cef24b64a88b17c3b96b346d1c365d7b9bc0bd5a0990897e3`.

The next permitted step is a target-specific metadata-only proof that all
frozen orbital templates and five guarded search windows fit inside every
scan. No HDF5 `data` value may be opened until that proof passes and the full
held-out search is separately preregistered.
