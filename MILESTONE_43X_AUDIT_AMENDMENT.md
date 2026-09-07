# M43X audit-only correction: member activity versus injected truth activity

During the running, publicly frozen M43X panel, case 169 exposed an incorrect
assumption in the prospective artifact validator. Its injected truth uses
active epochs [0,2], but retained hypotheses may use other activity subsets.
The aggregate endpoint admitted 30 additional members using [0,1,2], which is
consistent with the detector definition. The two-epoch identity theorem only
applies to members whose own declared activity subset has two epochs.

The original `scripts/m43x_audit_report.py` incorrectly asserts equality of
whole-case final sets whenever the injected truth has two active epochs. It
remains unchanged and pinned, and its audit failure will be retained. The
replacement `scripts/m43x_audit_report_v2.py` checks the equality of passing
flags for each actual two-epoch member, with exact record-ID and length checks.
The general hard-floor subset of aggregate subset of neighbor9 checks remain.
All complete-panel associations, losses, controls and development gates are
recomputed identically. A focused mixed-activity regression test passes and
also rejects a corrupted two-epoch decision or missing record.

This changes only an artifact-validation assertion and its report wording.
No detector code, input, threshold, null row, calibration, association rule,
scientific gate or frozen configuration changes. Existing case checkpoints
remain bound to public freeze 0d4406c5a6a7106f49a71d809fc7c79731ccc238.
The correction is disclosed after data contact and is not new independent
scientific evidence. The v1 file and every original result remain preserved.
