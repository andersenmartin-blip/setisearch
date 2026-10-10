# Cache-only 2019 metadata structure plan

This prospective phase uses the six retained 4,096-byte prefixes from
`radio_visit2019_blc66_headers_20261010`. It parses metadata already present in
those exact caches and records bounded missing metadata fragments. It performs
zero HTTP requests and has no fetch callback. Initial h5py missing-read hints
are evidence from the initial capture only; they are never adopted as range
proposals by this planner.

The source is prepared for independent review and synthetic format fixtures.
The actual cached prefixes must remain unopened by this phase until its code,
scope and input pins are publicly frozen and root explicitly authorizes the
one invocation. No structural result has yet been produced by these tools.

## Supported subset

`structure.py` is a pure standard-library module. `MetadataCache` accepts
authenticated `(offset, bytes, pin)` spans, checks bounds and overlapping byte
equality, and exposes only cache-backed reads. `plan_source` returns a plan
without filesystem or network access.

The first scope supports a version-0 superblock with offset and length widths
both eight bytes, a signature already cached at a permitted offset
0/512/1,024/2,048, and version-1 object headers. A partially cached signature or
header yields an explicit missing typed extent. Other versions, widths,
relocated base semantics or external driver metadata fail closed.

The planner follows the superblock's root hard-link address, version-1 object
header continuation messages, and the named root hard link `data`. Hard links
can come from a compact link message or the legacy group TREE-type-0, local
HEAP and SNOD structures. These are group-name metadata paths. TREE-type-1
dataset chunk indexes are never traversed.

Attribute heap references are recognized only inside a supported attribute
message with an actual class-9 variable-length string datatype, a verified
unsigned-byte parent datatype and a scalar or bounded simple dataspace.
Admitted primitive fixed datatype classes 0–5 containing pointer-looking bytes
generate no heap proposals. Compound, reference, enum and array attribute
schemas are unsupported; they are not assumed to be fixed. A
typed string descriptor permits a GCOL header, sequential object headers, and
the referenced string-attribute bytes. Other live heap data is skipped using
its declared padded size; the entire arbitrary collection is not requested.

Version-3 chunked data-layout envelopes are admitted only to verify their
bounded layout extent. Their index/storage addresses are not decoded,
reported or followed. Compact, contiguous, virtual and other layout versions
are outside this scope. Recognized non-pointer messages are recorded by type,
length and data hash; their values are not decoded. This is a structural
traversal, not a general HDF5 validator or a reconstruction of dataset shape,
filters, frequencies, times or amplitudes.

## Typed missing fragments

Every missing extent has an authenticated parent field or format-origin
record: source offset, byte count, SHA256, cache pin and field interpretation.
Pointer records also retain the encoded bytes and enclosing message/header
evidence. The planner subtracts existing cached coverage, yielding exact
uncovered fragments of the declared typed object. Each proposal states
`payload_pointer=false` and `HTTP_authorized=false`.

Addresses are derived from each file's verified fields. No address, chunk
count, channel geometry or observation result from 2017 is reused. No scan for
GCOL signatures or interpretation of arbitrary 16-byte sequences is used.
Unknown supported-subset formats return `UNSUPPORTED_FORMAT`; malformed
bounds, cycles, counts or reserved fields return `INVALID_METADATA`.

These fragments can inform a later separately frozen metadata-acquisition
phase. They authorize no request now, and this phase extracts no raw chunk
descriptors or payload queue.

## Finite limits and admission

The pure parser has per-source limits of 4 MiB cached bytes, 64 KiB per typed
object read, 128 object headers, 2,048 messages, eight traversal levels, 128
missing fragments and 1 MiB summed missing bytes. Any cap failure returns an
invalid plan rather than silently expanding the subset.

The CLI consumes exactly six complete authenticated HEAD/prefix pairs, even
when their initial h5py header interpretation was incomplete. It verifies the
initial source manifest, code, scope, public freeze, root admission, terminal
and per-source receipt joins. Prefix identity requires exact 206/range/ETag
provenance and the retained file SHA256. Successful execution only means that
the six bounded plans were captured; each plan retains its structural status.

One output directory and durable `PLAN_STARTED_ONCE.json` marker forbid an
automatic retry. Input byte pins are checked again before an exclusive atomic
terminal is published. Planned bounds are 20 process CPU seconds, 300 wall
seconds, 512 MiB address space/RSS, 4 MiB output and 12 GiB across the two
declared workspaces. Terminal publication is included in disk reservation;
the receipt labels its timing boundary. Root must meter the full command too.

The future absolute CLI, after root generates and freezes the concrete scope,
is:

```bash
python /workspace/scratch/a8d1e29996d0/setisearch_fullpower/tools/radio_visit2019_blc66_structure_20261010/planner.py \
  --scope /workspace/scratch/a8d1e29996d0/setisearch_fullpower/tools/radio_visit2019_blc66_structure_20261010/scope.json \
  --expected-scope-sha256 ACTUAL_FROZEN_SCOPE_SHA256 \
  --freeze-commit ACTUAL_PUBLIC_FREEZE_COMMIT \
  --root-go-after-public-freeze
```

No six-source geometry, midpoint, pointing eligibility, independent visit or
scientific signal admission is established by this phase. Whole original
source-file authentication is not inferred from HEAD and cached range pins.

## Official format provenance

The only format authority used is The HDF Group's official
[HDF5 File Format Specification 4.0](https://support.hdfgroup.org/documentation/hdf5/latest/_f_m_t4.html),
read on 2026-10-10. The independent official-format review is recorded
separately. Field definitions come from these sections:

| Section | Implemented interpretation |
| --- | --- |
| II.A | v0 signature, widths, base, absolute EOF and root symbol entry |
| III.A.1 / III.B / III.C / III.D | legacy group TREE, SNOD, symbol entries and local name HEAP |
| III.E | GCOL v1 headers, object index/reference count/size and global-heap ID |
| IV.A.1.a / IV.A.3.q | v1 object-header envelopes and continuation offset/length; no v2 OCHK prefix |
| IV.A.3.g / IV.A.3.r | compact hard links and legacy symbol-table pointers |
| IV.A.3.d / IV.A.3.m / IV.B | typed VL string attributes and the u32 sequence count preceding a global-heap ID |
| IV.A.3.i | admitted v3 chunked layout envelope; storage/index traversal excluded |

The distinction between length width L and offset width O is preserved even
though this first scope requires both to equal eight. In that subset, a VL
string descriptor is 16 bytes; a live GCOL object's size counts its data only,
while free object zero's size includes its own header. These distinctions are
covered by handmade fixtures and are not inferred from cached file patterns.
