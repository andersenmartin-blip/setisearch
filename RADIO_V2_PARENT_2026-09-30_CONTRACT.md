# Prospective v2 event-parent and archive integration — 30 September 2026

This is an engineering integration of the separately qualified v2 compressed
evidence format. The old v1 writer, reader and parent adapter remain unchanged.
No native attempt, random values, receiver measurement or telescope access is
authorized by this contract. Old outcomes, allocations and scientific limits
retain their original meanings.

## Parent and evidence bindings

The new `physical_case_v2_radio` adapter admits only a newly consumed local
`EventDirectoryStore` engineering lease. Configuration case and plan identities
must match the parent's binding, including when a mismatched configuration has
an otherwise self-consistent policy hash. All seven original base files are
byte-verified and registered before the first physical write. Base filenames
cannot overlap the physical prefix or reserved closure files.

The whole parent case is capped at **18,874,368 stored bytes (18 MiB)**, including
base files, every physical part/checkpoint, physical footer, group seal and outer
outcome. Before physical writing, **262,144 bytes** for the seal and **65,536 bytes**
for the outer outcome are withheld from the physical budget. The physical
writer additionally protects its unchanged **65,536-byte failure footer**.
Every new checkpoint batch must fit the prospective parent group file limit
(at most 1,024 files) before its first part is written. No reservation is raised.

The exact original event and pointer versions are retained by the existing
event store under its unchanged **8-MiB cumulative journal allocation**. The
complete dynamic archive seal and parent artifact receipts bind all bytes.
Integrity/inventory errors poison the v2 writer permanently, including errors
thrown while enumerating the directory. Removing an offending file does not
restore execution rights. Lost acknowledgements stop the writer and lease;
recovery is read-only. Scientific manifests and remote leases remain refused.

## One fixed archived-byte parent allocation

`scripts/radio_v2_parent_qualification.py --freeze` writes the exact prospective
source, code, runtime, manifest, configuration and recipe. It must be publicly
committed and independently read back before the one exclusive
`radio-v2-event-parent-20260930a` parent is consumed. The local worker has a
240-second whole-worker alarm, 180-second parent active allocation and 512-MiB
peak RSS cap. Failure closes the scope; there is no retry or smaller substitute.

It preserves the same original incomplete physical report and both original
deterministic software receiver profile files as exact UTF-8 strings, including
all whitespace/newlines. Three prospective views contain 1, 20 and 20 ordered
copies of the archived 2,048 software pairs. These copies are serialization
stress data, never independent members or receiver measurements. All three
snapshot lengths and hashes and every original journal revision must restore
exactly. The physical footer, group seal and parent outcome remain **FAILED**.
A storage PASS cannot relabel the source physical failure or complete the
missing native report.

## Separate bounded remote archive protocol

`event_archive_remote_radio` is a new versioned engineering snapshot publisher;
the old 4-KiB/64-KiB/16-event incremental scope remains unchanged. Before a live
publication, a separate public freeze pins the concrete complete bundle,
independent parent/tree identities, namespace, file/hash/length inventory,
code and resource limits. Publication only proceeds after independent freeze
readback. All exact physical, base, seal/outcome, event and pointer bytes are
retained. Content blobs may be staged, but one fast-forward commit exposes the
complete bound snapshot and its archive manifest/HEAD. Existing namespace
content cannot be overwritten. Every artifact must be read back at the immutable
new commit with original Git and SHA256 identities checked. All requests,
responses, errors and actual resource counters are retained.

Original files larger than 262,144 bytes use ordered transport pieces, with
their complete original filenames, lengths, SHA256 and Git blob identities
bound by the manifest. Exact reconstruction is checked after all piece
readbacks. The tool broker separately limits each request to 600,000 bytes,
each reply frame to 4 MiB, all complete tool frames to 64 MiB, 512 underlying
Git calls and 3,000 local handoff commands. Its measured elapsed time is capped
at 900 seconds; full wrapper frames and handoff counts are retained alongside
the publisher's normalized-response budget and timings. Administrative package
publication and future result publication are outside this timed archive scope.

This qualifies a terminal engineering archive publication, **not automatic
remote publication during native execution**, not a remote scientific lease,
and not an 80-second scientific evaluation. Snapshot publication and local
case closure are separate timed regions and must be reported separately.
An ambiguous result or conflicting parent permanently stops the publisher;
no branch force-update, rebase/retry, alternate namespace or execution resume
is permitted within the scope. The live resource freeze governs the exact
concrete bundle; any later different workload needs its own allocation.

## Continuation

Once these components pass, freeze a fresh complete native physical/resource
qualification, with receiver batching, exact complete receiver/alias/cluster
evidence, all stage timings and bounded interruption accounting. Remote
publication during that execution must still be explicitly integrated and
measured; the terminal archive alone cannot establish it. Actual scientific
127/24 validation and a separate telescope protocol remain subsequent gates.

127/24 stays NOT ACTIVATED. HD189733/85030 remains selected, HD1461 on HOLD,
GJ724 reserve; spectra and old holdouts stay unopened. LS paused, CHEOPS UNSENT.
No external messages, scheduled-task changes or plan extension. Review around
2 October and consolidate 9 October. The parallel software reviews in this
session do not delegate experiments, identities, RNG, scores or measurements.
