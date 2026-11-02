This is a prospective, bounded **metadata-only search for wider temporal coverage of HD122640 and HD135204**, in that order. It continues the ten existing unresolved `FRAME_BASELINE_CONTEXT` records, starting with V2E2-0229. The earlier 300 spectra provide BERV spans of only 2.237910 and 1.714121 km/s. New dates alone cannot establish a wider BERV span or a physical origin.

`PLAN.json`, `HD122640.adql`, `HD135204.adql`, `TARGETS.json` and `EXISTING_300.json` specify the exact requests and identity constraints. No target query has run at preparation time. Three public documentation/schema GETs are recorded in `sources/RETRIEVAL.json`; these are distinct from the two prospective target requests.

The official [ESO programmatic-access documentation](https://www.eso.org/cms/eso-data/programmatic-access.html) identifies `tap_obs`, ADQL, synchronous queries, the reduced-product ObsCore table and DataLink relationships. The [live TAP table schema](https://archive.eso.org/tap_obs/tables) defines every selected/joined column; its saved snapshot and extracted `SCHEMA_CONTRACT.json` make the contract reviewable. The [ESO demonstration page](https://archive.eso.org/programmatic/) supplies standard TAP request examples. The science/ancillary category and archive/provenance relationships are taken from this schema, not inferred from a product filename.

| Guard | Frozen rule |
| --- | --- |
| Targets | HD122640, then HD135204; no other scientific targets added |
| Requests | Two synchronous HTTPS POSTs at most, one attempt per target |
| Limits | 30 seconds, 1,000 joined rows, 4 MiB per target; no redirects, retries or pagination |
| Exposure dates | Entire exposure outside UTC `[2023-02-19, 2023-03-02)`, equivalent MJD `[59994,60005)`; `t_max <= 59994 OR t_min >= 60005` |
| Public cutoff | `obs_release_date <= 2026-11-02T00:00:00Z` |
| Product | HARPS instrument and collection, spectrum, `n_obs=1`, `multi_ob='S'`, positive exposure time |
| Query identity | Recorded HD-name aliases OR a 120-arcsecond cone around recorded intended FK5/J2000 coordinates |
| Offline identity | Exact canonical HD name AND position inside that cone; preserve all other returned rows with reasons |
| Existing observations | Exclude all 300 known DP IDs in ADQL and recheck locally; reject a whole product if any joined progenitor is one of the 300 known raw IDs |
| Missing provenance | Preserve but exclude products without exactly one unique HARPS raw progenitor; require the main SCIENCE.SPECTRUM product association |
| Duplicate new products | One raw exposure is one metadata candidate; retain the lexicographically first qualifying DP identity |
| Stop | Any transfer/HTTP/parse/contract/cap failure stops subsequent requests; an empty valid first response permits the second frozen request |
| Science payload | Zero bytes; no URL from the response is opened |

The 120-arcsecond cone is a bounded inventory guard. It includes the existing primary-header pointing spread (about 111 arcseconds at its largest), but does not establish absolute target identity. The telescope headers contain some suspicious shared proper-motion entries across these two targets; they are not propagated or treated as verified physical proper motions. `TARGETS.json` preserves the source product, manifest hash, original intended header, and all 29 historical positions so this limitation remains visible.

The two LEFT JOINs retain all returned progenitors before offline exclusions. Filtering individual raw progenitors in the server-side WHERE clause could hide a disqualifying old progenitor and is deliberately avoided. `MAXREC=1000` applies to joined rows, not distinct observations. Overflow, missing/non-OK `QUERY_STATUS`, or exactly 1,000 returned rows is treated as incomplete; it cannot support a complete inventory claim. Raw responses, HTTP headers, curl diagnostics, request receipts and normalized metadata will be preserved.

`search_metadata.py` verifies the frozen file hashes, the historical input hashes, the root's exact remote-publication receipt and curl version before network access. Curl 8.4 or newer is required for its documented streaming size cap; the installed version is 8.5. `--disable` ignores curl configuration, `--retry 0` prevents retries, `--max-time 30` bounds the full transfer, and no redirect-following option is enabled. Exclusive run/attempt markers prevent accidental repeat queries. An interrupted or failed run is a recorded stop, not permission to restart.

The root must write `ROOT_RELEASE.json` containing `freeze_sha256`, a 40-character `prospective_commit`, and `remote_bytes_verified: true` after verifying the published bytes. Only then run `python3 search_metadata.py --execute`. Running without `--execute` performs no network operation. Reproduction of completed responses must be offline; never rerun acquisition merely to restore evidence.

`CANDIDATES.json` will contain only **metadata candidates pending separately frozen header identity/BERV checks**. It will not admit spectra scientifically, change a classifier or relabel any of the 185 U / 35 M records. No SNR, flux or morphology ranking is used. A useful later header result would still leave stellar radial velocity, wavelength calibration, photon origin and the limitations of a short baseline unresolved.
