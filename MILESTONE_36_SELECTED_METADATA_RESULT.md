# Milestone 36 selected-target metadata result

Status: **OFFICIAL METADATA COMPLETE; NO SPECTRAL CONTACT**.

The exact frozen NASA Exoplanet Archive `pscomppars` query returned one
complete required-field record for HIP 48714 b. The absent HD alias was
prospectively optional because the discovery record also has no HD name. No
telescope spectral payload was opened, indexed, or read.

## Frozen official record

| Field | Value |
|---|---:|
| Planet / host | HIP 48714 b / HIP 48714 |
| Archive aliases | HIP 48714 / no HD alias |
| ICRS coordinates | 09h56m07.98s, +62d47m09.42s |
| Distance / parallax | 10.5298 pc / 94.9397 mas |
| Proper motion | -304.046, -583.599 mas/yr |
| Stellar radial velocity | +14.98726 km/s |
| Orbital period | 17.818 d |
| Semimajor axis | 0.112 au |
| Eccentricity | 0.5 |
| Periastron epoch | BJD 2451539.8 |
| Longitude of periastron | 202 deg |

The identity, distance, and all five orbital values exactly match the frozen
discovery record. The official query additionally supplies the host
astrometry and radial velocity needed by the coordinate transform.

The record is preserved verbatim in
`results_m36_selected_metadata/hip48714b.json` with SHA-256
`787f0d5a905e0f6f54aaffea6cb4c2af68183888bbdb4a5a026b5899fe81bc04`.

## Provenance and boundary

- source commit: `7ec1b5b91830527676ba2847687acf2aa30a14f3`
- result publication commit: `81e09794a92434beed8c9f0a5c81121a11f20417`
- workflow run: `32990388450`
- artifact: `9614371861`
- artifact digest:
  `sha256:50bd1089a37713b30a74d3235a6a269a98c033ff8e179e4f60a4909a19382c71`
- result count: one exact named planet record
- `spectral_payload_inspected`: false

The next permitted action is the metadata-only motion-plus-width coverage
proof for all 21 motion templates, four activity subsets, eight spectral
widths, six scans, and five retained L-band windows on cadence `--76348`.
The proof must also confirm that the 2200-cluster cap exceeds the exact 2016
hypothesis-peak maximum before preregistration.
