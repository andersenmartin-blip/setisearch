# Milestone 17 selected-target metadata result

Status: **COMPLETE — GJ 849 CONFIGURATION MAY PROCEED**.

GitHub Actions run `32571608488` returned exactly one NASA Exoplanet Archive
composite record for GJ 849 b. Artifact `9475456047`, named
`milestone-17-selected-metadata`, has digest
`sha256:88c2a0941f0e4232461a7ce077d987f7d57044543444d979f24e47c72861d79e`.

The official record supplies:

- position: RA 332.4229938 degrees, Dec -4.6408317 degrees;
- distance and parallax: 8.80058 pc and 113.6 mas;
- proper motion: +1132.53 mas/yr in RA and -22.1255 mas/yr in Dec;
- radial velocity: -15.3 km/s; and
- orbit: period 1925.31 days, semimajor axis 2.32 au, eccentricity 0.029,
  periastron epoch BJD 2453770.0, and longitude of periastron 111 degrees.

The record has HIP identity `HIP 109388` and no HD alias. The initial workflow
attempt failed closed because it incorrectly required `hd_name`; run
`32571508763` is documented separately. The successful correction permits
only that optional alias to be null and leaves every required physical field
mandatory.

The machine-readable record is
`results_m17_selected_metadata/gj849b.json`, SHA-256
`ee8b5316613e5de08e6ca206dfee0865e58ce89c13a2c1d0c8aa817eb660d849`.
No telescope product or spectral dataset value was inspected.
