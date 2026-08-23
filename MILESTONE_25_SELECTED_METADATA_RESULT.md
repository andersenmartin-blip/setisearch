# Milestone 25 selected metadata: HD 164922 b

Status: **OFFICIAL TARGET RECORD ACQUIRED WITHOUT SPECTRAL CONTACT**.

GitHub Actions run `32655763537` queried the NASA Exoplanet Archive
`pscomppars` composite table for exactly `HD 164922 b`. Artifact `9497391729`,
named `milestone-25-selected-metadata`, has verified digest
`sha256:5872014e58b7f8e2010711e44a9c983be0315dcee31dc76692e4548ea22f893c`.

The returned host record is HD 164922 / HIP 88348 at RA 18h02m31.31s, Dec
+26d18m37.47s, distance 22.0016 pc, and parallax 45.4222 mas. Proper motion is
(+389.653, -602.314) mas/yr and stellar radial velocity is +20.3634 km/s.

The composite HD 164922 b orbit has period 1207 days, semimajor axis 2.16 au,
eccentricity 0.08, periastron epoch BJD 2457978.0, and longitude of periastron
116 degrees. These values define only a working motion template.

The exact query, API URL, record, and explicit `spectral_payload_inspected:
false` boundary are preserved in
`results_m25_selected_metadata/hd164922b.json`, SHA-256
`d826ef7192f68194440e31cec7fe1bd701d60187e60fff48605f50b7d88dde52`.

The next permitted step is a target-specific metadata-only proof that all
frozen orbital templates and five guarded search windows fit inside every
scan. No HDF5 `data` value may be opened until that proof passes and the full
held-out search is separately preregistered.
