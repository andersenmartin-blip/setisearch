# LS8K — exact WASP-189 DEFAULT-L2 header preflight

Status: **FROZEN BEFORE HEADER ACCESS; SCIENCE VALUES CLOSED**.

The LS8J first-1,000-row archive census selects rank 1, WASP-189. This is a
chronological archive selection, without an astrophysical-interest filter.
The first two eligible visits, in their unchanged order, are:

- `CH_PR100041_TG000201_V0300`
- `CH_PR100041_TG000202_V0300`

The separately acquired LS8J full-inventory reconciliation must be public and
PASS, with unchanged full cohort ranking, before this preflight is run.

Read only the primary and first SCI_COR_Lightcurve BINTABLE headers of each
exact DEFAULT product. Use 2880-byte ranges with HTTP 206, exact range lengths,
stable size/ETag/Content-Disposition and at most 64 KiB per product. Require a
zero-axis primary HDU, no table heap, exact requested file-key prefix, DEFAULT
aperture/version suffix, PIPE 14.1.2, and the unchanged 18-column/138-byte schema
recorded in the LS8I header preflight. Stop before the first table-data byte.

Both visits must retain their selection metadata: NEXP=7, EXPTIME=
4.80000019073486 seconds and TEXPTIME=33.6000022888184 seconds, with absolute
header-comparison tolerance 1e-6 seconds.

Save all header bytes and range receipts, exact row counts and table ranges,
full schemas and object identities. Stop on a mismatch without substitution.
No table values, images, raw imagettes or additional visit may be read.
Publish a passing result before freezing the exact science-table screen.
