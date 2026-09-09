# Continue from the M43AF integrated design checkpoint

**Latest status, 9 September 2026: development code and inventories are prepared;
the native runtime went offline. M43AF has not been scientifically evaluated.**

Read MILESTONE_43AF_INTEGRATED_DESIGN_DRAFT.md and
results_m43af_design_checkpoint/status.json. The draft is not an executable
scientific freeze. Do not start measurements from its publication alone.

## Public completed science

M43AE publication is complete: scientific result c875ff8548111b558cef0dec67a941b81454e97c,
initial M43AF measurement preparation 2b7350adb8e20197fa927f75a8ba046f292319c2,
publication receipt ae1ceb358d133797949a728bcce77053fd826b96. The original main
README update is 3adb241f8f24c1b3e5468893aad00966b09b8264.
All 14 M43AE archive parts and all 314 release-manifest entries were verified.
The M43AE result seal remains
03095e2406baf20dea5db707437d08d4bd4b57176146913c31068eaf9866cd37.
Read M43AE_PUBLICATION_COMPLETED.md. No further upload permission is pending.

M43AE's 262 inputs are historical, not validation: one baseline; 83 signals /
66 controls; and 64 signals / 48 controls. Keep all failed gates, 246 distinct
native payloads and the one-sequence limitation. Do not rerun the 262-case
experiment, old endpoint arithmetic or exhaustive alias census to resume.

## Additional concrete preparation

- acquisition_m43af.py collects full responses before old weak-epoch rejection,
  verifies retained centers, matches reused profiles and supports native checks.
- boundary_m43af.py specifies a two-coordinate joint rule and deterministic
  training with an explicit no-feasible-model outcome.
- m43af_scalar_audit.py independently checks scalar measurements and reuses the
  independently implemented M43AE coordinate oracle.
- Two new test files cover acquisition, corrupt evidence, joint selection and
  failure behavior. These new Python tests have NOT run. The original 28-test
  preparation receipt remains valid only for its original, unchanged scope.
- config/m43af_prospective_design_draft.json enumerates 112 training and 112
  unopened validation inputs (each 64 signals / 48 controls), and 128 training /
  128 held-out shift rows excluding all 1,792 prior rows.
- Metadata-only JavaScript checks confirm these counts and exact shift/spec
  separation. They are not Python/native tests or payload-novelty certificates.
  scripts/m43af_verify_design.py supplies the pending local metadata check.

The full consistent selected-null adapter and independent release/boundary
auditor remain required. A pre-veto empty-retention bound cannot replace
conditional response calibration. Do not shift scores while silently retaining
unshifted native receiver provenance.

## Runtime recovery

The local branch was m43af-integrated-study, with a sibling m43af_runtime
directory for native data. Locate or recreate a runtime; availability must
be checked afresh.

The M43Z/AB/AD/AE archives were restored and verified before the disconnection.
Python 3.12.14, numpy 2.3.5, astropy 8.0.1, h5py 3.16.0 and hdf5plugin 7.1.0
matched the frozen M43AE scientific dependencies in that session.

Native restoration was started with:
    PYTHONPATH=src:scripts python scripts/m43ab_restore_runtime.py --runtime-root ../m43af_runtime --output results_m43af_runtime_recovery

Its last verified progress had epoch 1 ON/OFF arrays complete and epoch 2 sparse
downloads in progress. The session later returned exec-server transport
disconnected, then 409 environment_offline. Completion is unknown. Do not
declare source restoration complete or infer a failed scientific result.
Use a fresh recovery receipt directory when resuming; preserve closed receipts
and reuse only checksum-verified native bytes.

## Next authorized work

Restore a working runtime, verify the native prerequisites, and run the focused
tests and metadata verifier. Finish the consistent null adapter and release
audit; publicly freeze the complete executable protocol before any new M43AF
measurement. Train only on its designated panel, then publish the boundary or
explicit failure before conditionally opening validation. Publish exact gains,
costs and failed gates. Do not tune on M43AE examples. No delegation or
unattended execution.
