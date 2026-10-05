# Independent review of the original bootstrap outcome

Verdict: **CLOSED_FAILED_OUTCOME_LOSSLESSLY_PRESERVED_AND_INDEPENDENTLY_VERIFIED**.

The one original invocation failed while resolving the first pinned NumPy URL:
`[Errno -3] Temporary failure in name resolution`. It received no HTTP status,
header or body bytes. The exclusive NumPy output is an exact zero-byte regular
file. Both other wheels were unattempted. Static ZIP inspection, installation
preflight and pip were never reached. No pip child existed to attribute or reap;
`pip_child: null` is preserved. There are no child streams or process-sample
artifacts, and the owned `site` and `tmp` directories are empty.

The caller's CLI exit code was zero because the gate returned its complete
failure report. The semantic result is `CLOSED_FAILED`, not a successful package
materialization. The complete caller stdout is 89,206 bytes, SHA256
`526c9cc4fb9b8c7fa29b7a63d56f1f94e82e4fad127b611f1a4c1da7b0d836e8`;
stderr is empty. Their retained copies equal the original external streams in
full bytes, Git blobs and stable identities. The isolated gate command and all
six externally pinned inputs match the one-invocation receipt. Report elapsed
time before the final report is 5.561721345 seconds; the returned complete
selected interval is 5.57743641 seconds. Provider and administrative elapsed
time are separate.

## Independent verification

`actual-independent-review.json` records 63 independent checks; this is a count
of administrative assertions, **not** native-library custodies. There are zero
verified native member custodies or installed package metadata rows in this
failed outcome. No HDF5 runtime version was observed.

The reviewer waited for the explicit finished/no-child signal before reading the
original root. Every original regular file was independently opened with
no-follow guards, sole-link/type/size checks and full raw SHA256/Git hashing.
Every original directory and file identity matched the lossless preservation
manifest, and a second complete original inventory remained exactly equal.
Original inode, mode, size, timestamps and allocated-byte metadata are retained;
access times are outside the stability comparison. The reviewer changed no
original root member.

The root has **488 regular files and 80 directories**: 17,075,597 raw file bytes,
17,403,277 logical bytes including directories, and 18,526,208 allocated bytes.
The operational custody manifest covers all original objects preceding its own
and the final report's creation. Its only cycle exclusions are
`artifact-manifest.json` and `supervisor-result.json`; both were separately
hashed in full. `selected-runtime-after.json` is included in operational
custody. No original object is excluded from lossless publication preservation.

All 488 files have independently verified representations: 479 decoded frozen
installer-basis references, seven exact UTF-8 copies, and two part payloads.
The retained 10,431,170-byte admission witness reconstructs exactly from all 28
canonical base64 parts. The empty wheel has zero parts and the exact empty-file
hashes. Raw versus encoded hashes/Git blobs remain distinct. All three manifest
transport parts reconstruct the exact 837,280-byte preservation manifest.
There are no archive-member references on this outcome because acquisition
never completed; no member, native package or installer was executed by review.

The complete 1,736 selected before/after source/runtime pin rows equal the frozen
contract, and all their current raw hashes and modes were independently checked.
All 492 detached source-witness bodies decode to their pinned full raw bytes and
match the immutable preparation tree's Git blobs/modes. All 479 copied installer
seed files equal their frozen raw bytes and modes. The inherited original plan
was independently fetched at the immutable preparation commit and matched in
full.

Preparation `504651472f649a4bba1c0dbd5b1e0b99c8431e0b`, tree
`7153f90aa7385276f692484799d79721a2e079c1`, is bound to activation
`c1ff02e8da9dae07b5711595df6d57fd7857e67c`, tree
`6023d788555862b9616298dfb2eef44817ef5faa`. Independently retrieved complete root
and config trees show only the new activation-marker delta, with activation's
sole parent equal to preparation. The marker's full immutable body, contract
blob, original plan body, source bodies, proof, spent entry and report bindings
agree. These are administrative publication checks and grant no scientific CAS
qualification.

## Retained administrative diagnostics

The first review pass used an overly strict assumption that every preparation
blob had Git mode `100644`; the frozen pip source includes an intentional
`0755` file. The guard was corrected to require each exact frozen mode. That
failed review source and log are retained.

The second pass found rounded nanosecond integers in the unpublished caller
invocation receipt. JavaScript number serialization had changed stdout's
timestamp `1791167395511769142` to `1791167395511769000`, and stderr's
`1791167389899647119` to `1791167389899647200`. The root corrected only that
administrative representation using exact Python integers and retained its
pre-repair receipt. Bodies, inodes, modes and original timestamps did not change.
The third review pass verified the correction and completed successfully.
These administrative repairs and repeated review reads did not rerun acquisition,
pip or the gate. `logs/actual-review-verification-03.txt` is the final success log;
the earlier sources/logs remain available.

The successful review pass precharged 178,844,422 explicit requested bytes and
received 178,840,648 bytes through 3,774 opened files. These are separate
post-outcome administrative reads. Preliminary reads and failed review passes
are not claimed to have a complete combined I/O certificate. Neither review
accounting nor implicit loader/filesystem metadata activity is added to observed
bootstrap child/joined I/O.

## Scope and permanent disposition

The report retains 167,892,370 parent precharged bytes and the full unobserved
1,073,741,824-byte child reserve: 1,241,634,194 conservatively charged joined
bytes. No observed child/joined read total or full joined-scope certificate is
invented, even though no pip child started. The new 300-second/1,536-MiB
allocation remains permanently spent, giving the selected engineering subtotal
1,330 seconds and 1,592 MiB. There is no refund, retry, reactivation or automatic
successor.

All eleven scientific fields remain `PENDING`; scientific authority is false.
No successful HTTP GET-on-wire, TLS closure, aggregate/provider peak, native
dependency closure, installed package version, loaded HDF5 version, receiver
trial, CAS law or telescope-data analysis was qualified. Immutable result
publication/readback follows this review and is recorded separately. The
existing target, cadence, holdouts and 9 October consolidation remain as planned.
