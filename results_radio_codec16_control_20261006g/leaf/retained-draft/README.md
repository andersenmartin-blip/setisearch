# Codec16: inert controlled producer preparation

Status: **NO_DISPATCHED**. This prepares one new engineering control: the original
HD189733/HIP98505 cadence85030 **calibration window, epoch1_on, rows0–15**. It
does not open archive or holdout spectra, activate127/24, reserve a pilot, or
complete a scientific codec certificate. No freeze, activation, control child,
installed scientific package native import, HDF5 operation, selected-normalizer execution or deterministic
fixture payload was created during preparation.

The implementation is a draft for a future independently bounded leaf. Directly
invoking `codec16_control.py` exits with `NO_DISPATCHED`. Its effectful `produce`
function requires separate externally pinned engineering dispatch evidence and
outer supervisor/runtime integrity integration, which are absent here. Draft
inputs remain `execution_enabled:false`; the draft is not a ready-to-run scope.

## Exact maintained inputs

All eleven original source/metadata inputs were freshly retrieved at immutable
`andersenmartin-blip/setisearch` commit
`6da771e78667f0746e87d05915c6feb683541a25`. `GITHUB_RETRIEVAL.json` records paths
and Git blobs. `INPUT_MANIFEST.json` binds the exact whole raw UTF-8 bytes by
byte count, SHA256 and independently retrieved Git blob SHA1. The pure builder
reproduces the Git blob hash before accepting each input. It also checks the
four original receiver metadata pins independently from retained original
qualification values. The fifth metadata input is the complete original
`preserved-basis.json`, with its actual whole-file pin and preserved-only domain.
Original files are copied under `authoritative/`; none is altered or executed.

Zero native imports means no installed scientific NumPy/h5py/hdf5plugin import.
Base Python's ordinary stdlib native extensions are expected during hashing,
JSON and source-only administration; no installed C/E interpreter was launched.

`PLAN.json` binds the input manifest and selected-code manifest without a
self-hash cycle. The selected nodes have original full-file pins, names, types,
line boundaries and exact inclusive segment hashes. Selection is inspected by
`ast.parse`; this preparation does not compile or execute the selected code.

| Controlled geometry | Fixed value |
|---|---|
| Dataset shape / chunks / dtype | `[16,1,264503296]` / `[1,1,1048576]` / `<f4` |
| Calibration chunk | 159 |
| Selected archive interval | `[167215104,167280640]` |
| Selected channels per row | 65,536 |
| Exact legacy pipeline | `[[32008,1,[0,3,4,0,2]]]` |
| Normalization | reverse archive-descending row; float32 median/MAD in4096-channel blocks from the new ascending extraction origin |
| Receiver context | `8899f84c7e9721e79627a4ec7166b7c941127a50f6ed5cb2d771f2c8518feb13` |
| Receiver bank | `bbbc484c2de5c6d27f311a72d86271087fa82baf164c4776421217ac462f0d6c` |
| Window identity | `b4f75b0920287630579c0e51e5e43c2ead2c9f4313ed802b50df607f91f1ee16` |

## Maintained arithmetic and import boundary

Ordinary `source_m43h` import would load NumPy, detector implementation
`search_v0p6`, `source_v0p6` and HTTP/thread/file transport `http_range_v0p6`.
`source_v0p6` performs import-time `inspect.getsource` and runtime identity
calculations. NumPy itself loads native extensions. These broad imports are
not performed by the draft or its source-only checks.

The future implementation instead compiles only the pinned original
`source_m43h.normalize_native_row`, `source_v0p6._float32_median_rows`,
`source_v0p6.normalize_float32_blocks_v0p6`, their original constants and the
two original `search_v0p6` exception classes. Minimal namespaces connect those
unchanged functions. It does not import the detector, transport, transfer,
RNG, Astropy or scientific-admission modules. Exact original whole source
bytes and selected segment witnesses are retained for review. This is a new
controlled algorithm binding, not a replacement scientific authority API.

The original pure receiver module's `validate_receiver_metadata` reproduces
the four raw metadata/basis inputs and context/bank; the future producer invokes
that method only, from pinned in-memory source bytes. It never invokes its
closure, session or telescope loader entry points. The tiny
`qualify_synthetic_fixture` API has a4096-byte row cap and is unsuitable for
these262,144-byte selected rows; `from_telescope` requires completed pilot
admission and cannot produce its prerequisites.

Installed scientific NumPy/h5py/hdf5plugin imports are deferred to a future separately
admitted leaf. The existing E metadata SHA is bound as a retained runtime
observation; the future control still needs its own whole runtime/source/input
integrity checks and terminal supervision. F counter observations, if available,
do not qualify a codec or establish this leaf's future measurements.

## What the future control measures

Adapt the retained deterministic binary-fraction pattern with no PRNG. Create
one local current-encoder file and one distinct exact-legacy-declared file,
transfer sixteen mask-zero raw compressed chunks, then decode and compare
every full chunk and selected row. The current encoder pipeline is separately
recorded; it is never called the original archive encoder.

The selected-row witness independently uses stdlib integer arithmetic and
little-endian float32 packing:

`(409600 + ((i*17+chunk*31+row*13)%4093) + 128*((i//4096)%17))/4096`.

This is exactly representable for the declared construction. No such payload
was generated here. The future receipt records compressed/full-decoded,
native-descending, ascending-raw and normalized hashes separately. It produces
**one partial engineering handoff**, with sixteen raw and normalized row hashes,
linked to the original calibration receiver metadata. It executes only the
exact-profile accepting guard in this minimal control and claims no complete
22-law qualification.

The original public codec validator needs twelve ordered calibration/validation
by six-scan handoffs, all sixteen row hashes per handoff and all22 laws.
Its handoff schema does not require archive payload receipts. A truthful
controlled producer is therefore a legitimate earlier component; no old
candidate is relabelled. Later physical telescope admission separately requires
authentic archive identity/transport/row receipts and full current authority.

## Prospective bounds, not observations

| Draft envelope | Meaning |
|---|---|
| One90 s wall /80 s CPU leaf | Suggested new engineering ceilings; no allocation exists here. |
|512 MiB AS and RSS ceilings | Suggested outer limits; incremental workspace96 MiB is a forecast, not measured RSS. |
|5 MiB per compressed payload | Fail-closed cap; no claim every compressor result fits. |
|84 MiB each HDF5 file |16×5 MiB payload allowance plus4 MiB metadata; enforce logical and allocated snapshots. |
|192 MiB total artifact envelope | Leaf checks184 MiB aggregate logical/allocated snapshots; separate8 MiB outer terminal reserve. Hash-only rows, no row NPY files. |
|512 MiB opaque child-read reservation | Prospective coverage, not measured complete native IO. Parent pre/post integrity/output read charges must be frozen separately. |

The96 MiB forecast describes incremental array/codec/cache **memory**; the
two84 MiB per-file caps describe retained **storage**. They are distinct bounds.
The input reader checks ordinary file size before a bounded maximum-plus-one
read. Raw compressed size/mask is checked through chunk metadata before
`read_direct_chunk` allocates the payload, and checked again afterward.

The full dataspace represents16,928,210,944 decoded bytes and must never be
materialized. Keep only one row/chunk's arrays live; use bounded8 MiB HDF5
caches, with two caches during raw transfer. A selected-path read model is
roughly320 MiB (up to168 MiB file hashing,80 MiB raw transfer,64 MiB full decode,
4 MiB selected windows and bounded metadata); library/kernel IO remains opaque.
The old32 MiB six-chunk fixture ceiling is not reused. Parent/supervisor native
mapping, loader custody, IO, process lifetime and terminal cleanup remain
future integration duties. No original scientific quota is enlarged.

## Source-only validation

The isolated base Python, never the installed C/E interpreter, built the pure
input/selection/plan documents. Ten stdlib/source-only tests passed. They check
exact original segment/raw hashes, metadata geometry, manifest dependency
direction, duplicate/missing source definitions, malformed JSON, lazy native
imports and direct-CLI refusal. Negative calls with absent or incorrectly
pinned future dispatch evidence stop before native import, compilation or
output creation. These tests do not validate any HDF5 or normalization runtime
operation. Initial seven-test transcription and raw nine-/ten-test logs are
retained. The ten-test suite adds a meaningful oversized-input rejection check
after independent source review identified read bounds that required tightening.

Before actual execution, a new namespace, immutable complete publication/readback,
fresh irreversible engineering allocation, exact outer integration and source
review are still needed. All scientific outcomes and the fixed pilot remain
pending. C/D/E, historical candidates, closed controls, targets and the9 October
project boundary are unchanged.
