# LS7L engineering source and schema inspection

Four previously specified engineering/quaternion products are restored.
All original file sizes, repeated source hashes and physical FITS header chains pass verification.
No engineering sample rows or native pixel-response outcomes are evaluated at this stage.

| Sector | Product | Bytes | HDUs |
|---|---|---:|---:|
| 29 | eng | 284,840,640 | 588 |
| 29 | quat | 417,271,680 | 5 |
| 32 | eng | 292,800,960 | 588 |
| 32 | quat | 415,068,480 | 5 |

The source hashes identify the downloaded originals; they are not a previously known mission hash.
Missing FITS checksum keywords are recorded explicitly in schema.json.
The full original files are a reproducible cache, excluded from the Git result payload.
Complete original header cards, offsets and header hashes are published.

Next: freeze exact fields, time conventions and row windows before extracting closed-context samples.
No detector is adopted, unused sector opened, or old result changed.
