# Codec16 G leaf integration

This fresh namespace copies the complete published codec16 preparation into
`retained-draft/` without changing any retained byte, including original failed
and successful source-only validation logs. Its PLAN remains an inert draft.
The new wrapper receives independently pinned fresh engineering dispatch
evidence from the outer supervisor. No native operation has been performed in
creating this leaf integration.

The only dispatching CLI is:

```
EXACT_RUNTIME_PREFIX/bin/python -I -B ABS_LEAF/run_codec16.py \
  --dispatch ABS_DISPATCH --dispatch-bytes N --dispatch-sha256 HEX \
  --leaf-manifest ABS_LEAF/LEAF_FILES.json \
  --leaf-manifest-bytes N --leaf-manifest-sha256 HEX --output ABS_NEW_OUTPUT
```

`ABS_NEW_OUTPUT` must not exist; its ordinary parent must exist. It is outside
the leaf tree. The producer creates it itself. Three retained output files are
expected: `controlled-encoder.h5`, `controlled-legacy.h5`, and
`codec16-receipt.json`. The leaf makes no subprocess or network request. Outer
publication, immutable readback, allocation, complete pinned runtime-byte
snapshots before and after the leaf,
wall/CPU/AS/RSS/IO/output bounds, process lifetime and terminal cleanup remain
the outer supervisor's responsibility. The wrapper supplies no standalone
scientific authority or complete codec certificate.

The dispatch JSON has exactly these eight keys:

| Key | Required value |
|---|---|
| schema | codec16-fresh-engineering-dispatch-v1 |
| scope_id | Fresh codec16-[a-z0-9-]{1,80} identity |
| plan_sha256 | 8c08a43b6a3b20792585e327b85d98caf04fc523f7ecd153b3165703ece4464f |
| input_manifest_sha256 | f37b59cec67e2fc4bcbf6006b67661ee630505aa7ad0703ec3949cf4d3a71fb0 |
| selection_sha256 | 3f66b1724165be840357cb61c1e2dfba9e259f74eb96ddc53c5c2974f0777d55 |
| runtime_prefix | Absolute exact interpreter prefix |
| outer_supervisor_scope_sha256 | Fresh outer scope's raw SHA256 |
| engineering_execution_authorized | true |

The runtime tuple remains exactly NumPy 2.3.5, h5py 3.16.0, HDF5 2.0.0 and
hdf5plugin 7.1.0. Version text alone does not establish runtime integrity.
The wrapper hashes the complete ordinary leaf artifact tree before loading its
helpers from those already authenticated in-memory bytes. Original authority
inputs are verified before and after the control. Zero-byte passive retained
logs are accepted; execution documents must be nonempty.

The one prospective control builds sixteen deterministic calibration chunks,
transfers mask-zero compressed bytes into a distinct exact-legacy-declared
dataset, rereads compressed bytes, verifies full decode and an independent
selected-row construction, and executes only selected original normalization
arithmetic. It emits one partial calibration/epoch1_on handoff. Raw descending,
ascending and normalized row SHA256s remain separate. It exercises no detector,
archive spectra, pilot, holdout, telescope reads or scientific allocation.

Source-only tests inspect malformed dispatch, pins, complete input inventory,
oversized/symlink inputs and output separation. They call neither `produce` nor
selected normalization and import no installed scientific package. These
tests do not establish native API behavior or observed codec success.

After final review, create the manifest once with isolated base Python:

```
python3 -I -B ABS_LEAF/build_leaf_manifest.py
```

The manifest excludes its own hash and includes all other leaf artifacts.
Its whole bytes/SHA256 must be pinned externally with the dispatcher and fresh
outer evidence. No source or document may change after its creation.
