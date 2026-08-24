# Milestone 27 selected metadata: HD 127506 b

Status: **OFFICIAL TARGET RECORD ACQUIRED WITHOUT SPECTRAL CONTACT**.

GitHub Actions run `32722863857` queried the NASA Exoplanet Archive
`pscomppars` composite table for exactly `HD 127506 b`. Artifact `9518386109`,
named `milestone-27-selected-metadata`, has verified digest
`sha256:5910678964dd586c495b8ed00e3af801398bc8986054ef801f99e2d412da2faa`.

The returned host record is HD 127506 / HIP 70950 at RA 14h30m44.37s, Dec
+35d27m16.58s, distance 22.5279 pc, and parallax 44.3605 mas. Proper motion is
(-481.116, +203.115) mas/yr and stellar radial velocity is -19.2 km/s.

The composite HD 127506 b orbit has period 65.78395 days, semimajor axis
0.287 au, eccentricity 0.24, periastron epoch BJD 2456787.645, and longitude
of periastron 56.147 degrees. These values define only a working motion
template.

The exact query, API URL, record, and explicit `spectral_payload_inspected:
false` boundary are preserved in
`results_m27_selected_metadata/hd127506b.json`, SHA-256
`b96c03ec870dc3db716cdbf47c643c45f18f5683222dc859eee1f27cb4d27e35`.

The next permitted step is a target-specific metadata-only proof that all
frozen orbital templates and five guarded search windows fit inside every
scan. No HDF5 `data` value may be opened until that proof passes and the full
held-out search is separately preregistered.
