# BS independent read-only review of the BQ/BR file failures

Review date: 2026-10-31. Scope: code and preserved execution records only. No
association computations, synthetic input generation, or astronomical reads were
performed. Historical sources and execution files were not edited.

## Finding

The inspected source does not support an ordinary missing-flush or
read-before-close explanation. The root cause remains **UNESTABLISHED**.
The BR traceback proves that its first pending-file read passed the expected
size check, but the file identity changed before that read finished. A fresh
read-only metadata observation additionally finds the retained BR pending file
at mode `0600`, although the path to the recorded exception necessarily called
`fchmod(0444)` successfully. This warrants investigation of file replacement,
metadata/content rollback, or another writer, rather than relaxing verification.

## Source evidence

- `work_bq/stream_association.py:101` opens the stream exclusively in binary mode
  with a 1 MiB Python buffer. Lines 118–124 explicitly flush, fsync, close, check
  the saved length, and check the whole-file SHA against the incremental digest.
  A successful close receipt is returned only after those checks.
- That module processes `current` and `legacy` sequentially at lines 145–158.
  It does not launch a worker or leave either writer open after close. Its
  exception cleanup at lines 128–133 only flushes/fsyncs/closes an open stream.
- `work_br/stream_closure.py:256–261` flushes, changes the open file to mode
  `0444`, fsyncs, closes it, and then verifies the pending pathname.
- The recorded BR traceback ends at that pending verification call, before the
  hard link at line 264 and unlink at line 271. Therefore hard-link creation or
  unlink-induced ctime changes cannot explain this recorded failure.
- `_verify_named_stream` opens read-only at lines 114–116. It checks initial
  fd/path identity at lines 120–124 and the declared byte count at line 125.
  The recorded failure is the final identity comparison at lines 149–152.
  The identity includes device, inode, size, mtime, ctime, and file type, but not
  atime (`_identity`, lines 72–73). An ordinary access-time update alone cannot
  trigger this guard.
- The BR writer sets `closed=True` before verification (line 260). Its finalizer
  and BQ exception cleanup therefore do not write the stream after this failure
  (lines 278–295; `closed_association.py:57–58`).
- `work_bo/src/capture.py:234–260` monitors size/resource usage and reads the
  child pipe; it does not truncate payload files. Its only `ftruncate` belongs
  to the separate exclusively-created failure reserve at lines 168–175. The
  recorded BQ and BR receipts both say `killed=false`, with natural EOF and exact
  child exits 0 and 2 respectively.
- BQ did have a confirmed qualification defect: its parent adopted capture PASS
  and inventoried files without comparing the final stream inventory with the
  child-declared stream receipts (`work_bq/run_postprocessing.py:77–85`). This
  explains why BQ initially reported PASS despite the shorter artifact, but it
  does not explain why the file shortened. BR correctly rejected its failure.
- Mutation tests in `work_br/tests/test_stream_closure.py` use isolated
  `TemporaryDirectory` fixtures. No production pathname is used for their
  deliberate mutations. Those tests do not explain this historical failure.

## Fresh metadata observations

These metadata are observations at review time, not a recovered historical
before/after trace. Existing audits separately established retained content as
the exact ordered prefixes. The mode observation is not cryptographically bound
by those previous byte-hash manifests.

| Artifact | Bytes | Mode | mtime UTC | ctime UTC |
| --- | ---: | --- | --- | --- |
| BQ current | 71,236,624 | 0644 | 08:09:04.016802 | 08:09:06.345119 |
| BQ legacy | 83,501,000 | 0644 | 08:09:07.260780 | 08:09:07.260780 |
| BR current | 82,645,873 | 0444 | 08:21:15.573513 | 08:21:19.181500 |
| BR legacy pending | 64,961,914 | 0600 | 08:21:23.221487 | 08:21:25.553460 |

The damaged files' ctime exceeds mtime by approximately 2.33 seconds in each
case. This is a lead, not proof of a common writer or filesystem mechanism.
The repository resides on the container's overlay mount. That observation
alone neither explains nor excuses a failed content-integrity check.

The prior independent reviews establish BQ current as 36,857 of 43,306 records
and BR legacy as 33,743 of 43,845 records, with both tails ending on complete
JSONL record boundaries. Missing tails greatly exceed the 1 MiB Python buffer.
Those facts, plus the explicit close checks, make simple buffered-tail loss an
inadequate explanation of the observed sequence.

## Next investigation

Use separate deterministic engineering fixtures; do not read saved A04 scores
or rerun A04 as a diagnostic. Preserve every fixture attempt and its metadata.

1. Record device, inode, size, mode, mtime_ns, ctime_ns, link count, and digest at
   writer creation, after flush, after chmod, after fsync, after close, and at
   verifier entry and exit. Log the exact mismatch, expected bytes, bytes read,
   and expected/observed record counts on failure.
2. Keep a read-only descriptor open across close/publication and compare its
   identity with the pathname. That distinguishes pathname replacement from
   modification of the same inode. Retain observations of both names.
3. Monitor directory/file events for modify, close-write, attribute changes,
   move, delete, and creation while the fixture runs. Ordinary inotify does not
   identify the responsible process, so do not claim attribution from masks.
4. Include controlled fault fixtures for same-inode truncation, pathname
   replacement with an earlier prefix, and metadata-only changes. These should
   demonstrate that the instrumentation distinguishes the mechanisms.
5. Keep strict final byte/hash/count checks. A small unrelated fixture passing
   cannot retroactively qualify BQ/BR or establish that large-file stability is
   solved. Any new A04 work requires a separately frozen identity after the
   engineering evidence supports it.

No corrected historical PASS is warranted. BP remains 23 qualified cases with
A04 incomplete; BQ remains evidence failure; BR remains failed closure.
