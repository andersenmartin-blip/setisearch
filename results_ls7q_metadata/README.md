# LS7Q saved metadata and reproduction

This package contains **metadata only**. No HiPERCAM science pixels, calibrated
arrays, per-frame timestamp records or native light curves are included.
[Findings and readiness decision](../LS7Q_OPTICAL_METADATA.md).

## Contents

- `acquisition_context.json`: observed browser state, query limits and selection
  rationale. The catalogue's result-page URL uses server session state; recreate
  the filters on the public search form rather than relying on that URL alone.
- `gtc_first100_rows.json`: the first 100 rendered catalogue rows and their
  actual links. Cells retain archive display text, including rounded exposure
  values and acquisition/calibration objects. These are not 100 qualified
  observations or the complete 1,035-product query result.
- Six `*header.html` files: original bytes from public FITS-header displays.
  They are HTML representations, not original binary FITS headers.
- `xo2b_calibration_list.html` and `xo2b_qc.txt`: calibration listing and the
  small observatory quality-control document. The QC log lists more calibration
  inputs than the calibration webpage. Only the explicitly saved headers were
  examined; no calibration pixel arrays were retrieved.
- `http_acquisition.json`: response URLs, status, type and size for the metadata
  requests, plus HEAD and the single bounded science-file range attempt.
  Session-cookie headers are intentionally omitted. The negative raw-file
  Content-Length is preserved as an invalid response field, not a file size.
- `summary.json`: parsed fields, exact decimal timing, dimensions, calibration
  discrepancies and the NOT_READY decision.
- `timing_audit.json` and `verification.log`: arithmetic comparison with the
  pinned official reader, input checks and reproduction scope.
- `ls7p_public_tree_check.json`: the science-branch snapshot used to reconcile
  the earlier LS7P publication claim. This is separate from LS7Q's data result.
- `SHA256SUMS`: file identities for the released LS7Q code, reports and evidence.

## Reproduce offline

From the science repository root, using Python 3.10 or later:

```bash
python scripts/ls7q_metadata.py
sha256sum -c results_ls7q_metadata/SHA256SUMS
```

The script regenerates `summary.json` solely from the included metadata.
It requires no network, science files or third-party Python packages.

To repeat the independent arithmetic check, obtain `hipercam/hcam.py` from the
[official source at commit 6a0b9a9](https://github.com/HiPERCAM/hipercam/blob/6a0b9a9d9053b831517a0aa4f8935e8878c3fc13/hipercam/hcam.py)
and retain its exact UTF-8 bytes in a temporary local file. Then run:

```bash
python scripts/ls7q_metadata.py --reference /absolute/path/to/hcam.py
```

Expected source SHA256:
`b73eb3001503ac62c7d97b083490a15e33b9e8222a6b0df86755b66b6ae9a6fb`.
Expected source Git blob: `2d56c9f37d54e2a1fb00d7563e877c05f21e67de`.
The script rejects a different source before executing the extracted timing
block. It neither imports the instrument package nor opens any science data.
The original HiPERCAM software is credited to its authors and remains in its
own repository under that repository's license; it is not redistributed here.

## Source map

All metadata were inspected on 14 September 2026. Request-level identities
and preserved bytes are listed in `http_acquisition.json`.

| Input | Public source |
|---|---|
| Catalogue query | [GTC search form](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/searchform.jsp) |
| Science 5070352 | [Header](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/viewprodheader.jsp?prod_id=GTC70-24B..0004A..5070352) |
| Acquisition 5070347 | [Header](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/viewprodheader.jsp?prod_id=GTC70-24B..0004A..5070347) |
| Acquisition 5070345 | [Header](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/viewprodheader.jsp?prod_id=GTC70-24B..0004A..5070345) |
| Flat 5070341 | [Header](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/viewprodheader.jsp?prod_id=GTC70-24B..0004A..5070341) |
| Bias 5070335 | [Header](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/viewprodheader.jsp?prod_id=GTC70-24B..0004A..5070335) |
| Standard 5070343 | [Header](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/viewprodheader.jsp?prod_id=GTC70-24B..0004A..5070343) |
| Associated calibrations | [Listing](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/viewprod.jsp?prod_id=GTC70-24B..0004A..5070352&modtype=CAL) |
| Observatory QC | [Text](https://gtc.sdc.cab.inta-csic.es/gtc/servlet/FetchProd?prog_id=GTC70-24B&obl_id=0004A&log_filename=GTC70-24B_0004a_qc.txt) |
| Timing convention | [Instrument manual](https://cygnus.astro.warwick.ac.uk/phsaap/hipercam/docs/html/timing/timing.html) |
| Calibration procedure | [Reduction manual](https://cygnus.astro.warwick.ac.uk/phsaap/hipercam/docs/html/reduction.html) |

The code's verification uses independent algebra for the exposure start/end
and the official scalar reader for timestamp offsets. Passing that check does
not demonstrate empirical GPS accuracy, scene calibration, pulse recovery,
an operational false-alarm rate or a physical light-sail sensitivity limit.
