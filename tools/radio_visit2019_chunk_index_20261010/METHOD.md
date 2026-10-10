# Cache-only legacy chunk-index planning

This prospective component accepts authenticated metadata bytes and a future
actual qualified header record. It makes no HTTP requests and reads no raw chunk
payload. It does not import h5py, NumPy or a decoder. Production use, scope
generation and toy execution remain separate root-authorized steps.

The supported format is the official HDF5 version-1 `TREE` node of type 1, with
8-byte addresses and rank-4 chunk-coordinate keys for a three-dimensional
little-endian float32 dataset. Section III.A.1 of the official HDF5 file-format
specification defines a 24-byte node header, `n` child pointers and `n+1` keys.
Each supported key has a 4-byte stored size, a 4-byte filter mask and four 8-byte
coordinates. The fourth coordinate is the zero element placeholder. Thus the
used node extent is `24 + 40*(n+1) + 8*n = 64 + 48*n` bytes. This is derived from
the actual cached used-entry count. The supported finite count is 1 through 64.

Primary reference:
https://support.hdfgroup.org/documentation/hdf5/latest/_f_m_t4.html
Sections III.A.1 and IV.A.3.i. Observed 2026-10-10. The final key is an interval
boundary, may lie beyond the real dataset extent and is never a chunk descriptor.
Addresses are interpreted relative to the qualified superblock base.

`plan_source(source, cache)` validates the actual qualified version-3/class-2
data-layout message again from authenticated cache bytes. The supplied layout
pointer and its parent evidence must agree byte for byte. The caller composes
the header record with its typed-plan `superblock` record; it must pin the actual
qualification result, typed plan, scopes, execution evidence and cache history.
This pure core does not replace those provenance or six-source eligibility gates.

The native ordinal is fixed before amplitudes as
`floor(ceil(nfrequency/native_chunk_channels)/2)`. The target origin for each
actual time row is `(row, 0, ordinal*native_chunk_channels, 0)`. Neither channel
count nor time-row count is borrowed from a prior visit. Supported time rows are
1 through 512; unsupported dimensions or formats fail closed. A partially filled
last frequency chunk retains its actual logical channel count and nominal full
decoded chunk length separately.

Traversal follows exactly one interval at every level. Coordinates must be
strictly sorted, real lower keys must be inside the dataset and aligned to its
chunks, child levels must decrease by one, and child key bounds must remain
inside the parent's interval. Cycles, conflicting parent intervals, overlapping
node extents and invalid lengths are rejected. A leaf origin must equal the exact
target. Siblings are bounds-checked but never followed. The maximum level is 15,
the maximum distinct node count 1,024, and the maximum metadata proposals 256
fragments with at most 1 MiB total missing bytes. These are prospective resource
limits, not assertions about the future files.

If a typed node is missing, the parser records only the unavailable portions of
its header or count-derived used extent after subtracting every admitted cache
span. A proposal includes the cached parent pointer, relevant key/header evidence
and a `payload_pointer:false` flag. There is no fetch callback or automatic
completion. A later separately frozen transport round may admit only clean
INCOMPLETE plans; INVALID or UNSUPPORTED plans cannot authorize requests.

Leaf compressed offsets, sizes and filter masks are recorded without accessing
their bytes. Masks are checked against the actual admitted pipeline count;
skipped filters remain explicit for a later codec admission. Positive stored
sizes and file bounds are required. Selected different-row payload intervals
must not overlap each other or the admitted TREE metadata. No score, profile,
amplitude, raw median or statistical calculation occurs.

The hand-built fixture contains 20 prospective cases: dynamic rows and node
lengths, a two-level tree, a relocated base, a partial native chunk, preserved
filter masks, exact cache-subtracted misses, unsupported formats and widths,
invalid counts/order/alignment/cycles/levels/bounds, frozen midpoint/parent
evidence mismatch, and repeated raw ranges. Its independent toy cache rejects
any attempted payload read. It remains unexecuted until root source review and
one bounded synthetic invocation.

Prospective synthetic CLI:

```sh
python /ABS_REPO/tools/radio_visit2019_chunk_index_20261010/TREE1_TOY_FIXTURE.py \
  --source /ABS_REPO/tools/radio_visit2019_chunk_index_20261010/tree_index.py \
  --expected-source-sha256 REVIEWED_SHA \
  --receipt /ABS_PRIVATE/TREE1_TOY_RESULT.json
```

The future aggregate manifest is
`SETI_VISIT2019_ONE_NATIVE_RAW_DESCRIPTOR_MANIFEST_V1`, with status
`PASS_CLEAN_EXACT_SIX_NATIVE_ROW_DESCRIPTORS_METADATA_ONLY`, an exact
`qualification_result_pin`, `typed_index_evidence_pins`, source-worker pins and
six ordered source records carrying the pure per-source results. All descriptor
counts must equal each source's actual `shape[0]`. Payload acquisition and
compact-file creation are separate finite scopes, with no hidden HEAD, index,
cache or repeated-range requests.

The small `planner.py` caller authenticates the actual successful six-header
qualification scope, result, execution and worker pins. It reuses the frozen
generic header-cache loader and a separately pinned TREE-cache admission
extension. Header completion history and TREE completion history remain separate.
The caller uses only the pure structure cache and this pure TREE core; it imports
no HDF5, NumPy or decoder. It captures six-source results even when clean typed
metadata is incomplete. Its successful capture is not payload admission.

The caller limits are 20 CPU seconds (22 hard), 300 wall seconds, 512 MiB memory,
32 MiB output and 12 GiB shared workspace. It reserves output space, creates and
fsyncs a once-only marker, authenticates all inputs again at the end and publishes
a prepared execution receipt exclusively. Each later metadata round needs its
own frozen scope and new output directory. No automatic retry is implemented.

`prepare_scope.py` remains uninvolved in binary interpretation: it opens only
UTF8 code/JSON and checks binary file sizes. It requires the actual source peer
binding all four Python sources, the exact 20-case toy PASS, and the actual
qualification pins. A root-created JSON configuration declares
`metadata_qualification`, `tree_metadata_rounds`,
`tree_cache_admission_worker_pin`, `source_review_pin`, `toy_result_pin` and the
new `output_directory`. Its schema is
`SETI_TREE1_SCOPE_PREPARATION_CONFIGURATION_V1`. The preparer has one marker per
new scope, 5 CPU seconds, 30 wall seconds and 256 MiB memory. It has not run.

Prospective actual metadata scope and caller CLIs:

```sh
python /ABS_REPO/tools/radio_visit2019_chunk_index_20261010/prepare_scope.py \
  --configuration /ABS_REPO/results/radio_visit2019_chunk_index_20261010/CONFIG.json \
  --expected-configuration-sha256 ROOT_CONFIG_SHA \
  --scope-output /ABS_REPO/tools/radio_visit2019_chunk_index_20261010/scope_round_0001.json \
  --root-go-metadata-only-after-qualification-closed

PYTHONDONTWRITEBYTECODE=1 python -B \
  /ABS_REPO/tools/radio_visit2019_chunk_index_20261010/planner.py \
  --scope /ABS_REPO/tools/radio_visit2019_chunk_index_20261010/scope_round_0001.json \
  --expected-scope-sha256 ROOT_SCOPE_SHA \
  --public-freeze-commit ROOT_FREEZE \
  --root-go-metadata-only
```

Aggregate planning schema is
`SETI_VISIT2019_PURE_TREE1_METADATA_PLAN_RESULT_V1`; clean incompleteness is
`INCOMPLETE_TYPED_CHUNK_INDEX_METADATA`. The execution status is
`COMPLETE_PURE_TREE1_METADATA_PLAN_CAPTURE_NO_VALUES_ADMISSION`, with actual
`structure_status`, result SHA and a standard typed-structure input-pin manifest.
The actual acquisition manifest can be assembled only after all six per-source
descriptor sets are complete and later finite payload admission passes.
