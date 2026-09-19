# LS8B exact metadata freeze

All four fixed visits passed header-only preflight. Zero table bytes have been read.

| File key | Rows | Row bytes | Table offset | Table bytes | Header bytes | Cadence (s) |
|---|---:|---:|---:|---:|---:|---:|
| CH_PR100006_TG000302_V0300 | 1171 | 138 | 20160 | 161598 | 20160 | 44.220001221 |
| CH_PR100006_TG000303_V0300 | 1189 | 138 | 20160 | 164082 | 20160 | 44.220001221 |
| CH_PR100006_TG000304_V0300 | 1194 | 138 | 20160 | 164772 | 20160 | 44.220001221 |
| CH_PR100006_TG000305_V0300 | 1200 | 138 | 20160 | 165600 | 20160 | 44.220001221 |

The original 80-character FITS cards, exact Content-Disposition filenames, ETags,
sizes, columns, version numbers, aperture and exposure metadata are retained in
[the metadata package](results_ls8b_l2_metadata/summary.json). Every byte-range receipt
is retained and all metadata files are SHA-256 sealed.

Run the already published [protocol](LS8B_FOUR_VISIT_PROTOCOL.md) and implementation
at the commit that publishes this metadata freeze. All four table reads must match
these exact identities. No threshold or rule was changed after metadata inspection.

Source code and 10 passing preparation tests preceded this preflight at
`6bc7ce6c6ffa5b1ee34a50387ae670019063164c`. Header transfer totaled
80,640 bytes; scientific table transfer is still zero.
