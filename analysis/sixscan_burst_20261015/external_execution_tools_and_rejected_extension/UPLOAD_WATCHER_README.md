# Separate checkpoint upload watcher

This external transport helper is separate from the frozen scientific stage and
numerical scheduler. Its development test invoked only a temporary local stub;
no Library uploads and no numerical trials were performed.

After any currently running manual upload batch has succeeded and the existing
recorder has written every checkpoint ACK, launch once:

```bash
python /workspace/scratch/b83cfe20d6e1/external_sixscan_20261015/checkpoint_upload_watcher.py \
  --batch-root /workspace/scratch/b83cfe20d6e1/checkpoints_sixscan_20261015 \
  --scheduler-state /workspace/scratch/b83cfe20d6e1/checkpoints_sixscan_20261015/SCHEDULER_STATE.json \
  --helper /workspace/scratch/b83cfe20d6e1/library_helpers_sixscan_20261015/library_upload.py \
  --record-script /workspace/scratch/b83cfe20d6e1/record_sixscan_checkpoint_upload.py \
  --directory-id 6ad06e44d9348191921c450ee339942f
```

The watcher derives the next archive batch number from existing batch filenames,
with a minimum starting number of 2. If manual batch 2 already exists, its next
new batch is 3. Completed manual batches are accepted only when every ordered
successful result matches an existing exact checkpoint ACK. An unknown request,
missing result/ACK, failed item or unknown earlier index save halts the watcher;
it does not replay an upload.

The ready receipt census is checked every five seconds. At most twenty pending
archives are hash-checked and sent as one ordered helper stdin request. The
watcher records REQUEST, RESULT, STDERR and LAUNCH/PID files for each upload.
After all items succeed, it calls the existing recorder, verifies all ACKs, then
saves the cumulative index. Archive and index results remain distinct.

All checkpoint receipt sequences must be contiguous from 1 through N before an
archive or index upload starts. A hole halts transport for review. A JSON read
that catches the brief empty/partial write of an exclusively created receipt
retries only that read for at most one second; Library mutations are never
retried.

The existing cumulative index is saved first when there are earlier checkpoint
ACKs but the index has not yet acquired a saved identity. The first index save
uses `create_library_file`; subsequent saves use `replace_library_file` with the
same Library id and the exact expected current version. Its durable local
identity receipt is `SAVED_CHECKPOINT_INDEX_IDENTITY.json`.

`UPLOAD_WATCHER_STATE.json` is an exclusive once-only start marker. Do not launch
a second watcher or perform concurrent manual archive/index uploads. Failed or
uncertain attempts preserve all request/result/error evidence and stop without
an automatic retry. The helper never removes checkpoint archives or edits the
scientific stage, claims, numerical outputs or resource accounting.

When the scheduler is terminal and every ready checkpoint has an ACK, the
watcher closes with `ALL_READY_CHECKPOINTS_SAVED`. This status reports transport
completion; the scheduler's separate terminal status identifies scientific
completion or a retained numerical stop.

The transport-only fixture is:

```bash
python /workspace/scratch/b83cfe20d6e1/external_sixscan_20261015/checkpoint_upload_watcher.py --self-test
```

Its final JSON result is recorded in `UPLOAD_WATCHER_SELFTEST.json`. The full log
also contains expected fixture failure messages used to verify fail-closed
behavior.
