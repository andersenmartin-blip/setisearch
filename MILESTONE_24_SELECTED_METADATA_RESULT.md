# Milestone 24 selected metadata: 16 Cyg B b

Status: **OFFICIAL TARGET RECORD ACQUIRED WITHOUT SPECTRAL CONTACT**.

GitHub Actions run `32653431103` queried the NASA Exoplanet Archive
`pscomppars` composite table for exactly `16 Cyg B b`. Artifact
`9496803850`, named `milestone-24-selected-metadata`, has verified digest
`sha256:89468ac6a15369cc50162b90b701ca433b5391e72520a6c3dc7e875a162b0054`.

The returned host record is 16 Cyg B / HIP 96901 / HD 186427 at RA
19h41m51.75s, Dec +50d31m00.57s, distance 21.1397 pc, and parallax
47.2754 mas. Proper motion is (-134.791, -162.493) mas/yr and the stellar
radial velocity is -28.1 km/s.

The composite 16 Cyg B b orbit has period 798.5 days, semimajor axis 1.66 au,
eccentricity 0.68, periastron epoch BJD 2450539.3, and longitude of periastron
82.74 degrees. These values define a working coordinate-transform hypothesis;
they do not establish that an emitter is located on the planet.

The exact query, API URL, record, and explicit `spectral_payload_inspected:
false` boundary are preserved in
`results_m24_selected_metadata/16cygbb.json`, SHA-256
`00ae76135eafd8d685efa2e3dae773d434b9f4510faa96971a70ffe4226654b4`.

The next permitted step is a target-specific metadata-only proof that all
frozen orbital templates and five guarded search windows fit inside every
scan. No HDF5 `data` value may be opened until that proof passes and the full
held-out search is separately preregistered.
