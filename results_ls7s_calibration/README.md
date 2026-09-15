# Reproduce LS7S

The result is an electronic-input and calibration-contract assessment of the
same LS7R CHEOPS visit. It is **NOT_READY** for native evaluation. See
[findings](../LS7S_CALIBRATION_FINDINGS.md), [scope](../LS7S_SCOPE.md), and
[continuation](../LS7S_CONTINUATION.md).

## Evidence

- `reference_rows.json`: the fifteen exact filename queries against the live
  mission reference UI, following a query of all fifteen required families
  with 792 returned records. Fourteen matched; aperture V0300 did not. Rows
  retain the archive's size strings and Obs Start/Stop columns. The shared
  results-page URL is not a permanent encoding of the query state.
- `reference_inventory.json`: exact association to LS7R's logged filenames,
  archive interval checks and the separate file-content verification flag.
- `access_record.json`: the unsuccessful mission download and the distinct
  successful small package acquisition. No archived download bytes are
  counted as acquired.
- `package_provenance.json`: official PyPI wheel URL, size, SHA-256, and
  the three extracted members. The wheel was not installed or executed.
- `calibration/`: exact gain V0109, the packaged `nonlin.txt` (not used as
  calibration), and the original GPL v3+ licence. No PSF pickle was read.
- `source_identities.json`, `sources/`: unmodified upstream PIPE `read.py`
  and `psf_phot.py`, with their Git identities. These preserve the source
  of the formula and raw calibration order discussed in the report. Their
  licence is retained under `calibration/LICENSE.rst`.
- `gain_reference_header.txt`, `gain_coefficients.csv.gz`: exact header
  and readable table extraction from the verified reference file.
- `exposure_calibration_ledger.csv.gz`: all 6,048 time/CE/electronic rows,
  missing onboard fields and both **conditional** calculated gains. `nan`
  means absent data, not a numerical substitute. MJD is TT; UTC is separate.
- `subarray_calibration_ledger.csv.gz`: all 432 matching HK/readout rows
  and recorded CAL bias/RON. No photometric field is included.
- `summary.json`, `verification.log`, `release_verification.json`: outcome,
  arithmetic checks, clean reconstruction result and inherited file checks.
- `SHA256SUMS`: release file hashes, excluding this checksum list itself.

## Offline reconstruction

Python with numpy and astropy is required. No PIPE installation is required.
Use the LS7R README to unpack its saved range evidence and reconstruct the
metadata-only FITS files. In a fresh checkout:

```bash
tar -xzf results_ls7r_metadata/metadata_evidence.tar.gz -C results_ls7r_metadata
python scripts/ls7r_acquire.py --offline SCI_RAW_Imagette SCI_RAW_SubArray SCI_CAL_SubArray SCI_COR_SubArray PIP_COR_PixelFlagMapSubArray
sha256sum -c results_ls7s_calibration/SHA256SUMS
python scripts/ls7s_assess_calibration.py
```

The assessor verifies original table-range SHA-256s, metadata HDU checksums,
the exact gain Git blob, hardware/UTC validity and all selected fields through
a scalar byte decoder. It evaluates the two declared polynomials separately
with a vector calculation and scalar `math.fsum`. The native image arrays are
never opened. No gain convention is adopted by a passed numerical check.

The source-level gain convention comparison is **not** an actual PIPE run.
Applying the literal expression to the available degree-C values is explicitly
an unverified adapter; native HK equivalence and the signed offset remain
physical questions. The scalar audit checks arithmetic, not that adaptation.

Optional reproduction of the small software-package extraction:

```bash
python scripts/ls7s_fetch_gain_reference.py
```

This uses the frozen official PyPI HTTPS wheel with a two-megabyte cap and
verifies the pinned wheel and gain identities. It does not request the blocked
mission archive download or obtain the missing large reference set.

## Primary sources

- [CHEOPS Mission Archive](https://cheops.unige.ch/archive_browser/):
  Reference Data Query; select the fifteen types from the saved LS7R log,
  then filter each exact name. This requires live UI interaction.
- [PIPE repository at the inspected commit](https://github.com/alphapsa/PIPE/tree/da15a87348e2657eac8dd08623ac258e6ac59df8):
  original code and the matching gain file. Local exact source copies and
  its licence are retained.
- [pipe-cheops 1.1 on PyPI](https://pypi.org/project/pipe-cheops/1.1/):
  the selected public package, linked by its metadata to the upstream repo.
- [PIPE installation documentation](https://pipe-cheops.readthedocs.io/en/latest/pipe/installation.html):
  separate gain, flat, nonlinearity and PSF inputs. The online documentation
  alone does not establish compatibility with the selected native visit.

CHEOPS is an ESA mission in partnership with Switzerland and a European
consortium. The upstream PIPE code is by Alexis Brandeker and distributed
under GNU GPL v3+. Its inclusion here is for reproducible source inspection.
