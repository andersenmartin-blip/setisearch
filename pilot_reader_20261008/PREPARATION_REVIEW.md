# Static reader preparation review — 8 October 2026

Disposition: **PREPARATION_ONLY; VALUE_FETCH_CLOSED**. No invocation of the
reader, codec import, controlled encode/decode, source payload GET or pilot
array read occurred while preparing this directory. Source metadata and
official documentation were read; the Python source was reviewed statically.
The source has not been AST-parsed or executed by this preparer.

The existing source qualification supplies exactly 96 compressed chunk ranges,
305,133,821 bytes, with all 16 rows in each of six ON/OFF scans. The ordinary
reader is plausible within the proposed limits: only one roughly 3.2 MiB
compressed buffer and a small returned selection are needed at a time; six
local compact files retain the compressed source chunks. This is a prospective
size argument, not a measured native-memory/performance result.

Required frozen inputs at admitted invocation:

- Source metadata:
  `pilot_source_20261008/primary/source_manifest.json`, SHA256
  `6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec`.
- Spent metadata ledger:
  `pilot_source_20261008/primary/SOURCE_BYTES_LEDGER.json`, SHA256
  `fc605b01c3069d0daf28db643c6fe0f8e4c45c221669ddbda6bcf5d898a2b226`.
  It records 1,158,240 received source metadata bytes; these precede the
  prospective 305,133,821-byte payload within the 2 GiB cadence ceiling.
- A newly generated independent VAL_A or VAL_B PASS summary, with its actual
  SHA256 pinned after validation. Such a PASS summary does not yet exist in
  this preparation. DEV outcomes cannot substitute for it.
- The actual admitted source/config/detector/control freeze and job command.
  This prepared reader does not grant an invocation by itself.

Metadata-only dependency observations:

- NumPy 2.3.5 METADATA is present in the primary runtime's site-packages.
- h5py 3.15.1 METADATA is present at
  `/root/.local/lib/python3.12/site-packages/h5py-3.15.1.dist-info/METADATA`.
  Its declared dependency is NumPy >=1.21.2; its metadata requires Python
  >=3.10. The existing source installation receipt reports that same h5py
  version and a public prebuilt wheel.
- No `hdf5plugin` or `bitshuffle` distribution METADATA was found in those
  inspected package locations. This is a scoped metadata observation, not
  proof that no plugin exists anywhere or that h5py is currently importable.
- Official current-supported bitshuffle registration and decoding remain
  unverified. A separately bounded, reproducible dependency setup may be
  needed before any admitted GET; no installation was performed here.

Official documentation supports direct compressed chunk writes and mask
readback, hdf5plugin's ordinary filter registration, and its stored-filter
option converter. The original bitshuffle set-local code shows why the first
three stored option fields are not creation user options. The supported
current prefix can differ from the historical prefix; original compressed
bytes, masks and element-size/block-size/compressor semantics remain explicit.
No private decompression or legacy-runtime certification is introduced.

Next: root may publish this preparation. Before scientific value admission,
independently review the source, perform ordinary source syntax checks, bind
actual dependencies and PASS validation, and freeze the concrete invocation.
Any failed acquisition preserves consumption and evidence; it does not select
a new band, resume the failed request or become a zero-hit search result.
