# Reproduce LS7R

The selected public CHEOPS visit is `CH_PR300024_TG000301_V0300`, OBSID 1015522.
[Findings](../LS7R_CHEOPS_INPUT.md) and [continuation](../LS7R_CONTINUATION.md)
state the scientific scope. No image data body was acquired or evaluated.

## Evidence

- `archive_visits.json`: all 31 rows from the public/latest mission-browser
  cone query at RA 133.149200, Dec 28.33083, radius 0.01 degrees, resolved from
  55 Cnc. The earliest row was chosen before acquisition. `archive_products.json`
  contains all 49 product rows displayed for that visit.
- `dace_visit.json` and `dace_products.json`: the public API result for that
  visit, including both returned versions and all 81 revision-3 product paths.
- `metadata_evidence.tar.gz`: the original 82 byte-range bodies and their
  per-product HTTP provenance, plus the exact 60,868-byte public pipeline log.
  It contains no image bodies. Metadata includes unanalysed onboard
  PHOTOMETRY_1/2/3 columns; they are not inputs to the timing calculation.
- `range_manifests.json` and `hdu_inventory.json`: readable consolidated range
  provenance and 25-HDU byte layout. Five primary image-extension header text
  files expose geometry, timing and correction/reference cards directly.
- `calibration_log_extract.json`: selected reference-related log lines and
  complete REF_APP filenames, with source-log hash and HTTP identity.
- `timing_rows.csv.gz`: an explicit whitelist of time/counter/integrity fields
  from 10,368 metadata rows. No photometric or centroid value is exported.
- `pulse_ledger.csv.gz`: every timestamp-only rectangular-pulse onset on the
  one-second grid for each duration, including onsets in gaps. These are model
  evaluations, not recovered native events or independent observations.
- `summary.json`, `verification.log`, `offline_verification.log`: numerical
  result and verification output. `SHA256SUMS` binds the complete release.

## Offline reconstruction

From the repository root, with Python 3.12, numpy and astropy installed:

```bash
sha256sum -c results_ls7r_metadata/SHA256SUMS
tar -xzf results_ls7r_metadata/metadata_evidence.tar.gz -C results_ls7r_metadata
python scripts/ls7r_acquire.py --offline SCI_RAW_Imagette SCI_RAW_SubArray SCI_CAL_SubArray SCI_COR_SubArray PIP_COR_PixelFlagMapSubArray
python scripts/ls7r_assess.py
```

The acquisition script recreates header text, metadata-only FITS containers
and HDU inventories from verified saved ranges. Each metadata-only container
has a new empty primary header; its original extension header and table body
are preserved, with FITS padding. These are not full original science files.
All five extension CHECKSUM/DATASUM checks pass.

The assessor independently decodes scalar FITS fields using Python `struct`,
checks UTC-to-TT agreement, exposure grouping and the three subarray versions,
and proves that every retained byte range is within a header or an allowed
metadata table. The pulse weights use the actual individual UTC midpoints and
EXPTIME, not a uniform cadence approximation. The complete outcome is
reproduced without a network request or access to pixel arrays.

The recorded runtime used numpy 2.5.3, astropy 8.0.1 and dace-query 3.0.1.
Only the latter is needed for optional re-fetching of API catalogue metadata.

## Optional fresh acquisition

Use a separate checkout/output directory to preserve this historical record.

```bash
python scripts/ls7r_fetch_metadata.py
python scripts/ls7r_acquire.py SCI_RAW_Imagette SCI_RAW_SubArray SCI_CAL_SubArray SCI_COR_SubArray PIP_COR_PixelFlagMapSubArray
```

The public service contract comes from
[dace-query's CHEOPS API](https://dace-query.readthedocs.io/en/latest/dace_query.cheops.html),
specifically the installed 3.0.1 download implementation. Downloads are scoped
to the exact file key and product type. Generated transport keys are not
credentials and are not needed in this record; fresh requests regenerate them.
The range reader rejects anything other than an exact 206 response with
consistent length/object identity. It never falls back to a full image transfer.
Five product reads are capped at 20 MB each, stricter than the original scope.

The first successful 2,880-byte probe is recorded in `initial_access.json`;
its bytes duplicate the final imagette primary-header range. Unique retained
bytes exclude repeated header requests during development and interrupted
acquisition. No exact total network-byte count is claimed.

The mission browser selection used its normal public search/resolve controls;
the DACE client explicitly used public mode. No sign-in, archive email or
message to a person was used. The public release excludes session cookies,
transient download URLs and environment dependencies.
