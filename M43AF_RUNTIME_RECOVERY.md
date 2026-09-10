# M43AF bounded runtime recovery

The scientific study remains frozen at
`75b271b4b92819783692375687586d6df4f40c57`.
Its configuration SHA256 is
`a2c39320fd4e7a4972d989108282a2ac1f5887069c990dcb8df079e5eff7a9a3`.
This recovery changes storage and transport scheduling only. It does not
change the detector, source normalization, null operator, training grid,
validation gates, or any of the 940 pinned scientific files.

On 10 September, a fresh checkout restored the M43Z ledger and the AB/AD/AE
archives byte for byte. The original 55 focused tests passed. The initial
sparse-mirror recovery reproduced two sources and 32 anchor arrays. Automatic
approval review stopped the continuing download because temporary copies of
the telescope-sized sparse files had pushed disk use toward the capacity of
the 32 GB filesystem. This was an operational interruption, not a scientific
failure or a training outcome.

Both completed sources and all 32 arrays were reverified before redundant
temporary download copies were discarded. Recovery now uses
`scripts/m43af_recover_bounded.py`. Each invocation handles one named source.
It stores the original 96 published segments as ordinary files with their
original SHA256 values. A read-only random-access adapter exposes only those
verified spans to HDF5; requests for missing spans fail. It never writes a
telescope-sized file or fills gaps with invented data.

| Resource | Enforced bound |
|---|---:|
| One downloaded segment file | 8 MiB |
| Sum of downloaded segments per source | 512 MiB |
| Simultaneous requests | 4 |
| One HDF5 read | 32 MiB |
| Free disk reserve | 2 GiB |

For the four remaining sources, actual published segment totals are about
457 MB each. The preflight additionally budgets all missing anchor arrays
and raw/normalized source rows before it permits a download. Verified download
parts are removed before anchor generation. The original live URL, ETag,
Content-Range and payload length checks remain mandatory. Native row extraction
and anchor generation call the existing frozen functions. The reconstructed
source receipt must equal the independently pinned original; every array must
match its original score hash.

Six focused recovery tests cover HDF5 reconstruction, missing spans, corrupt
segments, read limits, overlapping ranges and the published disk budget.
The real source and array hashes provide the required scientific equivalence
check; the synthetic tests alone do not establish that equivalence.

## Reproduction

Use Python 3.12.14 with NumPy 2.3.5, Astropy 8.0.1, h5py 3.16.0 and
hdf5plugin 7.1.0. First restore the original archived AB/AD/AE inputs and M43Z
ledger using their published restore scripts. Keep earlier closed recovery
receipts intact.

For each missing source, inspect its disk budget and then run that same source:

```bash
PYTHONPATH=src:scripts python scripts/m43af_recover_bounded.py \
  --runtime-root ../m43af_runtime --output results_m43af_recovery_bounded \
  --scan epoch2_on --check-only
PYTHONPATH=src:scripts python scripts/m43af_recover_bounded.py \
  --runtime-root ../m43af_runtime --output results_m43af_recovery_bounded \
  --scan epoch2_on
```

Use `epoch2_off`, `epoch3_on` and `epoch3_off` for the remaining original scans.
Do not start concurrent source recoveries or run the obsolete sparse download
and cleanup processes alongside this helper. An existing completed recovery
receipt is preserved; select a new receipt directory if another verification
run is needed.

The separately built `setisearch_M43AF_native_sources.zip` contained all 300
original source files for the six scans, including the independently trusted
source receipts and exact raw/normalized rows. Its complete byte reconstruction
was verified. It excludes the approximately 5 GiB of regenerable anchor arrays.
Extract it into the runtime root so that `sources/epoch1_on/...` and the other
five scan directories are restored. The bounded helper then verifies the
existing sources and reconstructs missing anchors without downloading telescope
data. Trust still comes from the unchanged repository's pinned source-receipt
hashes, not solely from the archive's own manifest. This native-source backup is
separate from the proposed GitHub code and derived-result publication.

The complete ZIP and two byte-exact parts were verified locally before saving.
**The saved backup is incomplete:** only `.zip.part002` could subsequently be
located. The complete ZIP and `.zip.part001` are no longer available at their
temporary paths, nor are the original checkout, Python environment or native
runtime. The extraction route above applies only if both exact parts are
later recovered; `.zip.part002` alone cannot reconstruct the ZIP. The full ZIP's
SHA256 was
`9d2f0637f8967775e780e57a3106d7d446f1d3c0a6d959ad2dfba76a2631ceff`.
The checkpoint package's `NATIVE_SOURCE_PARTS.json` records each part's exact
size and SHA256. Both parts had been read back and verified against the full
ZIP before the incomplete save. Current availability is recorded separately.

For the current restart, recreate the pinned environment and prior archived
inputs, then recover all six sources with the bounded helper, including
`epoch1_on` and `epoch1_off`. Use a new recovery receipt directory so the closed
receipts in this checkpoint remain intact.

After all six sources and 96 arrays are present, run the unchanged M43AF native
preflight, requiring exact replay of all stored score bits and 432 direct native
checks. Restore the already closed training from its archive; do not rerun it.
Publish and verify its model decision before the remaining historical phase.
No boundary qualified, so the validation inputs remain unopened.
The old preparation continuation predates the executable freeze; it is not the
current scientific entry point.
