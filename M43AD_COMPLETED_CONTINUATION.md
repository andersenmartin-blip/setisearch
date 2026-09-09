# Continue after the completed M43AD experiment

M43AD is closed. Read `MILESTONE_43AD_GEOMETRY_RESULT.md` and
`PROJECT_DIRECTION.md`. All three new policies fail the predeclared gates on
both panels; no production change is qualified. The result contains 150 base
executions and 1,500 policy endpoints, with 142 distinct native payloads on
one existing observing sequence. No new sky coverage or candidate is claimed.

The preparation is public, but the completed result upload was subsequently
blocked by the automatic reviewer's context limit. See
`M43AD_RESULTS_PUBLICATION_PENDING.md` for the exact rejection and restart
instructions. Complete publication before beginning another scientific stage.

## Publication and frozen evidence

The owner's explicit approval of publication of all documents resolved the
earlier automatic review block. The full preparation was published and its
tree verified before evaluation at scientific commit
`f2467ee06deb1391af3643ebedcbddf276dc1ef2`, tree
`13dd3706075ae02f271a360f30ba31e67d57c5ec`. The matching preparation README
was published on main at `76eb65c0a632426d641643f3d0fdfff4dacf52c7`.
The sealed receipt is `results_m43ad_geometry/public_freeze.json`.

`M43AD_PUBLICATION_PENDING.md` and `M43AD_CONTINUATION.md` preserve the earlier
preparation state. Their statements that publication/evaluation has not yet
happened are superseded by this completed package and the verified public
freeze. They remain unchanged to preserve the preparation manifest.

The evaluator completed without an endpoint repair, resume or numerical
retuning. Its frozen audit passed: 348 dependency hashes, all 38 old/baseline
exact replays, 128,360 policy-member decisions, 1,611 direct comparisons,
2,758,914 exhaustive cross-identity pair comparisons and 205 complete aligned
profiles. No requested profile was incomplete. Eight focused preparation tests
pass. All six source receipts, 96 anchor arrays and 48 native gathers match.

The archive, report writer and selected evidence excerpts were added after
evaluation for packaging and interpretation. They do not alter frozen scientific
code, configurations, thresholds, input seals or endpoint results.

## Findings that the next design must preserve

Geometry with the original OFF rule restores two historical mixed signals
(`ab_z171`, `ab_z281`) without adding control leaks relative to `combined`,
but gives the same 55/64 signal recovery and 3/48 leaking control labels on
the additional panel. The three labels share one native interference payload.

The aligned combination removes the known broad `ab_z138` and near-boundary
`ab_fresh032` controls but admits other ON/OFF controls. It also rejects the
previously recovered width-17 `new038` signal: the qualifying OFF maximum and
aligned shape comparison refer to different coordinates. The report and
`mechanism_examples.json` preserve the exact values and record identities.
The weak unequal-epoch `ab_z260/261/265` losses remain unresolved.

Next, jointly specify how OFF amplitude, shape and track identify the same
physical response, retaining stationary-receiver and moving-track hypotheses
explicitly. Preserve narrow mixed-signal gains and measure the loss caused by
every additional veto. Treat background-supported weak-epoch confirmation as
a separate requirement; do not raise the 5.5 floor to remove a known control.
All M43AD inputs are now historical. Freeze any new rule and additional panel
publicly before evaluation. Any future new null inventory must exclude all
1,792 previous rows. No new endpoint or null calibration was run after M43AD.

## Restore and resume

```bash
python scripts/m43z_restore_ledger.py
python scripts/m43ab_archive.py restore
python scripts/m43ad_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ad_audit.py
```

The new archive restores all 150 input gzip files, the complete result and
paired signal costs byte for byte. See `results_m43ad_geometry/ARCHIVE_README.md`.
These commands restore/audit completed evidence; do not rerun the experiment
merely to obtain its ledgers.

The current checkout is `/workspace/scratch/69269edb2f83/setisearch` and native
runtime is `/workspace/scratch/69269edb2f83/m43ad_runtime`. If the runtime is
lost, use `scripts/m43ab_restore_runtime.py` with a new receipt directory;
preserve the closed M43AD receipts. Reuse unchanged arithmetic evidence unless
a concrete new implementation risk requires further verification.

Ongoing publication on `m43-support-qualification` and README updates on `main`
remain authorized. No delegation or unattended-execution promise.
