# Prospective content-addressed v2 archive batch — 30 September 2026

This is a new engineering-only transport scope for the already published,
closed v2 terminal archive. It does not reopen the failed 900-second publisher,
retry any call, resume an execution, create a receiver measurement, read a
telescope spectrum or alter a scientific budget. The source files and their
Git blob, SHA256 and byte identities remain exact.

## Frozen transport

The source is the complete 130-file archive below
`results_radio_v2_parent_2026-09-30/live01`. A separate public freeze must bind
the exact science-branch parent and tree, source commit, all source and fresh
target paths, every blob/SHA256/length, deterministic batches, final expected
tree and the limits below. It is published and independently read back before
the live writer opens. The target is the unused immutable namespace
`results_radio_v2_batch_2026-09-30/live01`.

Existing content-addressed Git blobs are reused; no byte is transcoded and no
per-file blob upload is needed. At most 32 path/blob entries form each logical
batch. The complete target is staged against the exact parent, its tree must
equal the independently predicted tree, and exactly one commit plus one
non-forced fast-forward ref update may expose it. A changed parent, occupied
target, blob/tree mismatch, resource excess or ambiguous push acknowledgement
stops the scope permanently without retry or alternate namespace.

| Fixed limit | Value |
|---|---:|
| Files | 160 |
| Stored source bytes | 6 MiB |
| Entries per logical batch | 32 |
| Mutation commits / ref updates | 1 / 1 |
| Publication wall time | 300 s |
| Independent audit wall time | 120 s |
| Peak process RSS | 512 MiB |

After publication, one fresh fetch and one `git cat-file --batch` operation
must independently read every target at the immutable candidate commit. The
audit checks commit tree, file count, total bytes, Git blob and SHA256 for every
file. Publication and audit clocks, push output, exact parent/candidate/tree and
resource measurements are retained. Readback cannot reverse a publication
failure.

## Preserved disposition

This scope only qualifies a terminal archive transport. It does not qualify
publication during native execution, full physical/resource feasibility,
127/24 or telescope acquisition. The original parent and physical source stay
FAILED/incomplete, the serial live scope stays CLOSED FAILED, and its 900-second
cap is not raised. HD189733/85030 remains selected, HD1461/71139 remains on
pointing-provenance HOLD, GJ724/73005 remains reserve; spectra and old holdouts
stay unopened. LS remains paused and CHEOPS UNSENT. No external messages,
delegation, new RNG values or plan extension.

On PASS, continue with one fresh complete native physical/resource
qualification that integrates receiver batching, full stage timings, complete
failure evidence and publication during execution. It requires its own public
freeze and identities; this archive scope grants no activation.
