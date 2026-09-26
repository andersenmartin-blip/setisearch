# HD1461 same-scan provenance: retrieval specification

**Unsent information specification. No contact or retrieval request has been sent.**
This identifies the smallest useful evidence needed to resolve the active radio
pilot's pointing hold. It does not request telescope time or full spectra.

## Exact observation identity

GBT project/session **AGBT16A_999_189**, 14 May 2016, archive target
**HIP1499 / HD1461**, selected cadence 71139. The three ON scans are:

| Scan | Catalogue ID | Header start UTC, rounded to second | Fine-resolution filename |
|---|---:|---|---|
| 0015 | 71139 | 2016-05-14 16:36:09 | `spliced_blc0001020304050607_guppi_57522_59769_HIP1499_0015.gpuspec.0000.h5` |
| 0017 | 71145 | 2016-05-14 16:47:23 | `spliced_blc0001020304050607_guppi_57522_60443_HIP1499_0017.gpuspec.0000.h5` |
| 0019 | 71151 | 2016-05-14 16:58:37 | `spliced_blc0001020304050607_guppi_57522_61117_HIP1499_0019.gpuspec.0000.h5` |

The complete URLs, exact MJD values, sizes, ETags and retained HDF5 attributes
are pinned in `config/radio_hd1461_source_preparation_20260926.json`, SHA-256
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`.

## Minimum useful response

Provide an original header or observing record identifying the same session,
scan, source and UTC time, and preserving the original pointing fields and their
units, coordinate frame/equinox/epoch, and sign/sexagesimal representation.
An original same-scan GUPPI RAW header, original SIGPROC FIL header, or telescope
pointing/GO/observing-log record may supply this. A metadata-only extract with
its original file identity, provenance and checksum is sufficient if its link
to the specified scan can be verified. Record commanded and measured pointing
separately if both exist.

If the HDF5 coordinates resulted from a format conversion, the useful alternative
is the exact deployed conversion version/command and original coordinate bytes
for these files, with enough information to reproduce the transformation.
Source code from a possible converter without its deployment and input provenance
does not establish what happened to these observations.

The discrepancy to explain is ON RA about **4.67625 degrees** and declination
about **−8.62416 degrees** in the retained HDF5 headers, compared with the retained
catalogue direction **4.6762645, −8.0536206 degrees**. These values differ by
about **34.23 arcminutes**. This is a question about provenance; it is not an
assertion that the telescope was physically mispointed. Neither coordinate set
should be changed merely to agree with the other.

## Newly checked access route

The official [GBT support page](https://www.greenbankobservatory.org/~dfrayer/gbtsupport.html)
links an operator-log search and [archive retrieval instructions](https://www.gb.nrao.edu/scienceDocs/Archive/).
On 26 September 2026 the operator-log route redirected to NRAO single sign-on;
no log was retrieved and no login attempted. The retrieval document describes
staff/internal archive retrieval and subsequent staging for outside users. Its
background is historical, so it does not establish current availability of this
particular session. It is not evidence that the required record is absent.

This route lookup supplies an access requirement, **not a new same-scan pointing
observable**. It does not reopen the completed BL catalogue/public-converter
diagnoses. Spectral access remains `HOLD_POINTING_PROVENANCE_UNRESOLVED`.

Receipt summaries and official documentation links are retained in
`results_radio_motion_2026-09-26/reference_sources.json`. Authorized preparation
can continue while an independently verifiable same-scan record is unavailable.
