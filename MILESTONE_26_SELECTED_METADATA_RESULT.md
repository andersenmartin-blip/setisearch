# Milestone 26 selected metadata: HD 19994 b

Status: **OFFICIAL TARGET RECORD ACQUIRED WITHOUT SPECTRAL CONTACT**.

GitHub Actions run `32694932956` queried the NASA Exoplanet Archive
`pscomppars` composite table for exactly `HD 19994 b`. Artifact `9508496319`,
named `milestone-26-selected-metadata`, has verified digest
`sha256:c22ea74fb3dc77dcfe46c7fa0da7d0657edfe0a4843db53d9f85980519c3b0c1`.

The returned host record is HD 19994 / HIP 14954 at RA 03h12m46.64s, Dec
-01d11m47.02s, distance 22.5242 pc, and parallax 44.3695 mas. Proper motion is
(+193.25, -69.2932) mas/yr and stellar radial velocity is +19.0 km/s.

The composite HD 19994 b orbit has period 466.2 days, semimajor axis 1.305 au,
eccentricity 0.063, periastron epoch BJD 2453757.0, and longitude of periastron
346 degrees. These values define only a working motion template.

The exact query, API URL, record, and explicit `spectral_payload_inspected:
false` boundary are preserved in
`results_m26_selected_metadata/hd19994b.json`, SHA-256
`0d522301a5774ad8232d0bb3f12ffc7052bf00a7868d9ef7303c2ba5209229fe`.

The next permitted step is a target-specific metadata-only proof that all
frozen orbital templates and five guarded search windows fit inside every
scan. No HDF5 `data` value may be opened until that proof passes and the full
held-out search is separately preregistered.
