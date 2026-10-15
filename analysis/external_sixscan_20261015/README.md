# External once-only SETI runner

The helper orchestrates the frozen study without implementing numerical work.
It must be pinned and reviewed before the new study's public freeze and GO.
It has not launched any scientific job during development or the fixture test.

Launch once, after the exact public freeze readback and GO:

```bash
python /workspace/scratch/b83cfe20d6e1/external_sixscan_20261015/durable_scheduler.py \
  --root /workspace/scratch/b83cfe20d6e1/sixscan_burst_20261015 \
  --checkpoints /workspace/scratch/b83cfe20d6e1/checkpoints_sixscan_20261015 \
  --workers 8
```

The worker count must not exceed the frozen scope. The helper's default is 8;
the fixture verifies acceptance at a scope cap of 8 and rejection at 9.
The frozen coordinator owns all numerical worker creation and resource charges.
The helper does not change budgets, claims, seeds, detector settings or science
code. In particular it does not refund or reconcile the unresolved previous
study's resource reservation.

The exact action order is:

1. `coordinator.py --phase primary_calibration` (63).
2. `summarize.py --calibration-only`.
3. `coordinator.py --phase primary_validation` (142).
4. `coordinator.py --phase qa` (205).
5. `summarize.py`; require `SUMMARY.json.integrity_gate` true.
6. `coordinator.py --phase exposed` (9).
7. `coordinator.py --phase qa_exposed` (9).
8. `summarize.py --exposed`; require exposed integrity true.

Every action is recorded before launching its one subprocess. Existing scheduler
state, numerical phase state, claims or results prevent starting a second run.
The helper offers no automatic retry or resume. Any nonzero action halts further
phases. A joint scientific gate failure with integrity true is still a completed
study and permits the declared descriptive exposed searches, as frozen.

During a numerical phase the helper polls state every five seconds and emits
progress approximately every thirty seconds. Every four successfully reaped
jobs, and at phase closure, it makes a verified delta ZIP. Each delta contains at
most four new cases. Separate small checkpoints preserve each summarizer closure.

Producer checkpoints contain only complete `COMMITTED.json` cases. Each case's
manifest must match the commit; every manifest file's size and SHA-256 is verified
by reading back the complete ZIP payload. Live partial case arrays are excluded.
Checkpoint snapshots also include frozen sources and admission, all available
coordinator states, claim snapshots, completed child logs, available summaries,
and the external runner source and state. Live claims and state/log snapshots
are explicitly classified as snapshots rather than completion assertions.

QA checkpoints contain new QA receipts and metadata, with hashes referencing
the earlier producer checkpoint, COMMITTED record, artifact manifest and payload
pins. They never duplicate the producer arrays. Receipt bindings to producer
output and truth are checked. A verified producer checkpoint ZIP may be removed
locally after the root agent saves it durably; later QA checkpoints only need its
saved receipt/index and the original producer result files. The helper never
rebuilds a removed archive or deletes source/results.

Each completed checkpoint emits one `DURABLE_UPLOAD_REQUEST` JSON line with its
absolute path, size and SHA-256. A local ZIP is not a durable remote save. The
root agent owns uploads and remote readback verification and should save each
checkpoint promptly. Upload acknowledgments should be separate records; do not
edit the active `SCHEDULER_STATE.json` concurrently. Its historical receipts
deliberately record that this helper did not verify remote persistence.

If a checkpoint operation fails while its coordinator is running, the helper
allows that already launched coordinator to close, retains the failure and
launches no further phase. Failed or partial scientific outputs remain on disk
for the root agent's separately labelled failure-evidence package; checkpoints
never relabel those outputs as complete measurements.

The runner is a local process, not a guaranteed process that survives a runtime
loss. The durable checkpoint series preserves completed chunks when uploaded;
it does not create permission to retry any interrupted identity.

Transport-only static fixture check:

```bash
python /workspace/scratch/b83cfe20d6e1/external_sixscan_20261015/durable_scheduler.py --self-test
```

`SELFTEST.json` records the PASS result and the exact helper SHA-256. The fixture
uses labelled text bytes rather than scientific arrays and starts no coordinator,
worker, random generator or scientific trial.
