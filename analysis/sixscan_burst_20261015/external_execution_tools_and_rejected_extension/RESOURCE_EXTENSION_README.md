# Prospective storage-only continuation

This dispatcher is outside the original frozen scientific stage. Its metadata
fixtures create no scientific trials and read no production scientific outcomes.
It has not performed an admission capture, publication, Library upload or
production launch during development.

The permitted change raises the total results cap from 3 GiB to 4 GiB while
retaining the 8 GiB workspace cap and 512 MiB guard margin. Eight workers retain
their original 600 CPU-second, 1800 wall-second and 1 GiB address-space caps.
The current study's 260000 CPU-second envelope includes every original and new
wait4 child charge, the unreleased 1000 CPU-second metadata reservation and all
live 600 CPU-second reservations. The historical unknown 90000 CPU-second
envelope and older 43200 ledger remain preserved without refund or reset.

Admission is only possible after the original calibration is complete and the
original validation coordinator stopped specifically for its storage capacity
margin, with every submitted child successfully reaped and no running children.
The original external scheduler must also be closed. Its final original SUMMARY
must explicitly retain false integrity/joint gates and FAIL_CLOSED status.

Capture the closed metadata **only after independent code review**:

```bash
python /workspace/scratch/b83cfe20d6e1/external_sixscan_20261015/resource_extension_dispatcher.py \
  --stage /workspace/scratch/b83cfe20d6e1/sixscan_burst_20261015 \
  --extension-root /workspace/scratch/b83cfe20d6e1/resource_extension_sixscan_20261015 \
  --original-scheduler-state /workspace/scratch/b83cfe20d6e1/checkpoints_sixscan_20261015/SCHEDULER_STATE.json \
  --capture-admission
```

`ADMISSION_SNAPSHOT.json` pins the original sources, scope/GO, terminal scheduler,
calibration and stopped validation states, original false SUMMARY, every closed
claim/commit/manifest, original case identities and the exact unsubmitted list.
Every remaining primary identity must lack both a global claim and any case
folder, including partial folders. Every independent QA identity must also be
unclaimed, with no earlier QA receipt.

Copy `RESOURCE_AMENDMENT_TEMPLATE.json` to the extension root as `AMENDMENT.json`,
fill the exact snapshot/dispatcher/checkpoint-helper hashes and original scope
hash, and set status `FROZEN_RESOURCE_ONLY_CONTINUATION`. Publish the immutable
amendment, admission snapshot, final dispatcher and inherited checkpoint helper,
with independent reviews. Verify exact public bytes before writing a separate
extension `GO.json` containing:

```json
{
  "status": "ADMITTED_AFTER_EXACT_PUBLIC_AMENDMENT_READBACK",
  "amendment_sha256": "EXACT_FINAL_AMENDMENT_SHA256",
  "public_exact_readback_verified": true,
  "public_freeze_commit": "EXACT_IMMUTABLE_40_CHARACTER_GIT_COMMIT"
}
```

Only then may the root agent launch once:

```bash
python /workspace/scratch/b83cfe20d6e1/external_sixscan_20261015/resource_extension_dispatcher.py \
  --stage /workspace/scratch/b83cfe20d6e1/sixscan_burst_20261015 \
  --extension-root /workspace/scratch/b83cfe20d6e1/resource_extension_sixscan_20261015 \
  --original-scheduler-state /workspace/scratch/b83cfe20d6e1/checkpoints_sixscan_20261015/SCHEDULER_STATE.json \
  --checkpoint-helper /workspace/scratch/b83cfe20d6e1/external_sixscan_20261015/durable_scheduler.py
```

The dispatcher executes only the original stopped validation ledger's untouched
unsubmitted identities, using the unchanged original worker/GO/pins and seeds.
It never reruns a claimed primary identity. After all 205 original primary
identities have verified complete commits, it executes unchanged independent QA
once for each of the 205 unclaimed QA identities. Every launched child receives
its own wait4 resource receipt. Unexpected dispatch errors stop submissions and
drain already launched children before closing; no failed or interrupted identity
is retried. SIGTERM/SIGINT request the same bounded drain.

The two separate phase ledgers are
`PRIMARY_VALIDATION_EXTENSION_RUN_STATE.json` and `QA_EXTENSION_RUN_STATE.json`.
Each has status COMPLETE or STOPPED_RETAINED_NO_RETRY, jobs, running, unsubmitted,
whole-child resources, original-scope/amendment hashes and completed_UTC.
Original phase ledgers and original SUMMARY are never rewritten.

The terminal external state is `checkpoints/SCHEDULER_STATE.json`, with status
ALL_RESOURCE_EXTENSION_PHASES_CLOSED or RESOURCE_EXTENSION_STOPPED_RETAINED_NO_RETRY.
Its command rows contain action, status CLOSED, exit_code and phase_ledger.

`UNION_LEDGER_GATE.json` is a separate metadata gate. Positive closure requires
the disjoint exact 142-identity validation union, all 205 primary commits and all
205 bound independent PASS receipts/claims, complete wait4/resource accounting,
unchanged original evidence and amended capacity limits. It records actual
closed results/workspace byte counts. This gate does not compute or certify a
scientific joint PASS. A separately reviewed derivative report may use the union
receipts while retaining original_execution_gate false and original_qualification
FAIL_CLOSED.

There is no exposed dispatch command. The nine original exposed bands remain
NOT_RUN_BLOCKED, since the unchanged original validation/SUMMARY prerequisites
remain false. The extension does not fabricate replacement original phase
states, unlock original holdouts or claim a SETI detection.

Producer and QA checkpoints reuse the reviewed external checkpoint function.
They go to the extension's separate `checkpoints/` directory and include the
extension admission, amendment/GO, phase states, per-job external logs and final
union metadata gate. QA checkpoints refer to original and extended producer
checkpoints without duplicating arrays. Every four closed results and each phase
closure generate a verified archive. The already closed original uploader cannot
be resumed: launch a fresh **separate** `extension_checkpoint_upload_watcher.py`
instance, pointing to this new checkpoint directory and a separate destination
folder. The copied watcher only adds the explicit extension terminal labels; the
original uploader and Library helper scripts remain unchanged.

The protocol and code remain prospective until public amendment admission. The
code contains no automatic scope amendment, publication, deployment or permission
bypass.
