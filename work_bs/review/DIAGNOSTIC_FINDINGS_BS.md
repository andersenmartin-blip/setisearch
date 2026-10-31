# Independent BS diagnostic findings

The three fixed file-only trials are complete. BQ serial passed, BR serial
failed, and BR with the read-only overlapping witness passed. The independent
review confirms all six final fixture streams: each contains exactly 45,000
expected records and 90,183,890 bytes with the prospectively fixed SHA256.
This does **not** turn the failed BR serial trial into PASS.

| Trial | Actual child exit | Retained trial result | Final fixture content |
| --- | ---: | --- | --- |
| BQ serial | 0 | PASS | Both exact and complete |
| BR serial | 2 | FAIL | Both exact and complete; directory integrity failed |
| BR overlap | 0 | PASS | Both exact and complete |

All three recorded natural stdout EOF, exact child wait, no forced kill, and
complete owned-process cleanup. Runtime and source/historical bindings remain
unchanged. The review rehashed 769,954,673 retained bytes and independently
checked 270,000 records in the six final streams. Additional orphan/prefix
files were also inspected without changing them.

## The observed BR serial anomaly

The BR publisher created its first pending file with inode 1441934, linked it
to the final name, then removed the pending name normally. The monitor recorded
that deletion at elapsed 2.3404 seconds. The original inode remained visible as
`fixture_0.jsonl` and remained open through the monitor's held descriptor.

At 3.8209 seconds, inotify began reporting creation and writes to
`.fixture_0.jsonl.pending.BnKheI`. Around 5.3256 seconds, it recorded close/write,
attribute, move events, and creation/removal of a directory named `.rsync-tmp`.
The pending name then reappeared with a **different inode, 1441936**, while the
original final inode 1441934 was still present. The recreated pending file has
the complete expected stream-0 content. This is a recreated pathname after
normal unlink, not ordinary changes in hard-link count.

These events are consistent with copying or workspace reconciliation. They do
not identify a responsible process or prove a particular platform mechanism.
Python audit logs show the expected publisher operations and no corresponding
unexpected creation/rename, but those logs cannot observe native or external
process syscalls. Absence from that log is not proof of attribution.

## Changes after terminal publication

The strict first independent review failed because the BR serial directory no
longer matched its terminal inventory. The missing declared temporary file
`.fixture_0.jsonl.Ii8zAe.zs1rZb` had been recorded as 30,146,560 bytes. Its missing
bytes were not reconstructed or substituted.

The bounded final review retained the following additional current files:

| Retained extra file | Bytes | Independent content check |
| --- | ---: | --- |
| `.fixture_0.jsonl.pending` | 90,183,890 | Complete stream 0, different inode from final |
| `.fixture_1.jsonl.pending` | 90,183,890 | Complete stream 1, different inode from final |
| `.fixture_0.jsonl.Ii8zAe` | 47,972,352 | Exact stream-0 prefix: 23,939 complete records and 1,728 bytes of the next record |

BR serial retained storage was 408,880,521 bytes at final review, above the
384 MiB trial cap. The historical capture receipt recorded 288,023,246 bytes,
below the cap. Both observations are preserved; the later growth is an
additional final-evidence failure. The second strict review failure is retained
separately. No retained file changed during the final bounded 5.94-second review,
which does not guarantee stability afterward.

The descriptive review status is
`RETAINED_BYTES_VERIFIED_POST_TERMINAL_INVENTORY_FAILED`. It deliberately does
not certify an unchanged terminal inventory. The two earlier failed review
attempts, their source snapshots, and their exit codes are preserved.

## Implication for the next step

The serial BR failure and successful overlap trial do not support concurrent
tool execution as a necessary or sufficient cause. Pacing, yielding/polling,
load, and workspace synchronization remain possible factors. No single factor
was isolated by these three observations.

A separately frozen engineering stage can reasonably test an isolated tmpfs
working directory in one uninterrupted execution. It should verify the actual
filesystem and capacity first, retain strict input and output identities, keep
all writer/verification work inside that execution, and export only closed
artifacts with source/destination byte/hash checks. Such a trial would test a
mitigation; it would not establish the historical cause or retroactively repair
BQ, BR, or BS. Limited tmpfs capacity must remain an explicit resource bound.

The SETI status remains 23 qualified controls with A04 unqualified. No new A04
execution, score computation, RNG generation, or astronomical data access was
performed by this review.
