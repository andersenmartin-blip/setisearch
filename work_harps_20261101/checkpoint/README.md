# HARPS optical SETI input checkpoint — 1 November 2026

This archive preserves the exact public input bytes used for the project's
initial HARPS week: 100 main sample spectra (20 selected target groups × 5
epochs), two HD100508 development spectra, three reserved validation background
spectra, and the HD203608 development spectrum plus its compressed raw control.
There are 107 FITS/FITS.Z files in total. These roles describe input selection,
not completion or scientific validation of a technosignature search.

The inputs were obtained from the ESO Science Archive Facility:
https://archive.eso.org/ . They are HARPS observations from the ESO 3.6-m
telescope at La Silla. Individual public source URLs, product IDs, raw progenitor
IDs, download timestamps and SHA-256 values are retained in the acquisition
manifest and receipts. Original programme attribution and reduction provenance
remain in the unmodified FITS headers. When using these observations, retain
the ESO archive and original observing-programme acknowledgements.

Selection CSVs and the bounded 5,000-row catalogue metadata snapshot are included
to preserve the actual selection inputs. Literature ID inventories, source
metadata and the upstream review are factual provenance, not upstream software.
No third-party source code, result arrays, candidate tables, or production
analysis outputs are included. Absence from a referenced-ID inventory is not
proof that an observation has never previously been searched.

All archive member paths are relative to work_harps_20261101. Historical absolute
paths inside original JSON receipts identify the original workspace only; use
the archive-relative paths when restoring. The raw .fits.Z control stays in its
original compression. No FITS array was decoded or interpreted while packaging.

Restore by extracting the ZIP into an empty work_harps_20261101 directory. Check
the archive's external SHA-256 first, then run `sha256sum -c SHA256SUMS` from the
extracted directory. INPUTS_MANIFEST.json supplies exact sizes and SHA-256 values
for every original payload file. The manifest and this README are also covered
by SHA256SUMS; SHA256SUMS intentionally does not hash itself.

Packaging is deterministic for a fixed Python/zlib implementation: sorted
relative paths, ZIP DEFLATED level 1, timestamp 2026-11-01 00:00:00, Unix mode
0644, UTF-8 generated metadata with LF line endings. The build verifies original
download receipt hashes for all 107 binary inputs, validates all ZIP CRCs, and
recomputes each member SHA-256 from the archived bytes. The ZIP and delivery
receipt are stored outside the Git repository.
