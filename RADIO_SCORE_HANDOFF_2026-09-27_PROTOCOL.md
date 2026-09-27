# Receipt-bound score handoff and local checkpoint protocol

Prospective engineering scope from science commit
`c2cc41e3b27b2de9bc6b1111a4b7a10a33943ab9`, 27 September 2026.
The closed motion investigations and old acquisition demonstrations stay closed.

## Concrete risk and scope

Code inspection identifies a missing reconciliation at the direct score-store
boundary. `ScoreStore` computes its expected vector IDs from the arrays supplied
to its constructor. `NativeRun.validate_store` compares context/source metadata,
but does not compare those arrays with the per-scan, per-width native-cache
score hashes already retained in that metadata. A reconstructed store may thus
have self-consistent fresh IDs and stale native ancestry. Reproduce this with
one changed finite cell before deciding whether a repair is qualified. This is
an in-process/reconstruction integrity risk, not evidence that any published
science result was corrupted or that a detector outcome changed.

Add a separate guarded handoff; preserve every pinned legacy module. At native
production, reconcile all six scans and all eight widths in template order,
pin the complete context, source IDs, native cache inventory and vector bytes,
and create an immutable snapshot. Restoration requires an independently
retained receipt hash supplied by the caller; never trust a hash found beside
the payload. A fully rewritten payload and receipt must fail under the old pin.
Hashes establish identity relative to that pin, not independent proof of
correct numerical production or protection against a privileged process.

No numerical detector, normalization, width, threshold or factor arithmetic is
changed. The new consumer must reject an ordinary self-attesting `ScoreStore`.
Test downstream entry-point checks with detector/calibration calls forbidden.
No calibration or recovery/RFI/null evaluation is authorized.

## Durable local boundary

Use one bounded, explicit binary checkpoint: magic/version, bounded canonical
JSON receipt, followed by ordered C-layout little-endian float32 vectors. Require
exact dimensions, exact key coverage, finite values, exact length, all vector
hashes and full native-cache reconciliation before returning a usable snapshot.
No pickle, compressed archive, path chosen by metadata or array-file autodetection.
Reject oversized lengths before reading/allocating payloads, nonregular files,
symlinks, truncation, trailing data, wrong context/source/receipt and changed bytes.

Write through a same-directory exclusive temporary file, flush/fsync it, install
the final immutable name without replacement, and fsync the directory. A lost
acknowledgement or crash is not success; recovery inspects the final file with
the separately retained pin. Existing final files are never overwritten, even
when their content appears identical. Test before-install and after-install
failure, independent reopen, two competing writers and recovery validation.
Do not claim power-loss survival from simulated process failures or qualify a
remote backend. Local checkpointing grants no telescope admission or budget.

## Frozen evidence and resource limits

`config/radio_score_handoff_20260927.json` fixes one fresh local six-scan fixture
(98,304 generated native values maximum), the already published three-template
codec interface bank, 32 new tests maximum, three retained qualification
attempts maximum, one initial baseline probe and 180 seconds per attempt.
At most four constructions of that same fixture (393,216 generated native
values cumulatively) are permitted; reconstruction does not create independent
control identities. The fixture is neither a new
physical bank nor a scientific control identity. The distinct 3-calibration /
24-case / one-evaluation / zero-remedy panel remains entirely unexecuted.
Checkpoint ceilings are 32 MiB payload and 2 MiB receipt. Also honor the existing
context's modeled array cap; neither bound is a process-RSS guarantee.

Socket creation and actual detector/calibration calls are forbidden during
qualification. Keep every failed attempt, code snapshot, baseline acceptance,
new rejection, hashes and limitation. Do not tune a science outcome. Verify all
old input hashes before and after work. Record the same five execution blockers,
zero telescope requests/reservations/trials and unchanged exhausted synthetic
ledger. HD1461/HIP1499 and its pointing discrepancy remain unchanged; primary
is `neighbor9`, prior M15/M33/M43/LS/CHEOPS dispositions remain, and the plan
still closes on 9 October. Finish by publishing evidence and a precise next step.
