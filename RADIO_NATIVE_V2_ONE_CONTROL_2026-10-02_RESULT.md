# Radio native v2 — one-control final disposition

**Result: CLOSED_FAILED_RUNTIME_CUSTODY_POLICY_MISMATCH.** The unique marker-only
activation commit `ba1b6c918931a02a84cd23e0e14057bd9f700e40` passed independent
readback and produced a valid bounded receipt. The single permitted control invocation
then exited 1 before scope creation with `Sole-link regular pinned file required`.

Post-failure diagnosis identified `/usr/local/bin/git`: its 19,135,768 bytes and
SHA256 `2dae8066...c3e974f` exactly match the published freeze, but its link count is
145. The freezer hashes regular runtime files without a sole-link requirement, while
activation passes every runtime inventory member through the general `pin()` helper,
which requires `st_nlink == 1`. The published preparation therefore admitted a
runtime topology that its final activation gate refuses.

- [Activation readback](results_radio_native_v2_one_control_20261002a/activation-public-readback.json)
- [Single invocation](results_radio_native_v2_one_control_20261002a/invocation.json)
- [Retained stderr](results_radio_native_v2_one_control_20261002a/stderr.log)
- [Runtime diagnosis](results_radio_native_v2_one_control_20261002a/runtime-inventory-diagnosis.json)
- [Final disposition](results_radio_native_v2_one_control_20261002a/disposition.json)
- [Structural verifier](results_radio_native_v2_one_control_20261002a/verify_closed_failure.py)

No scope or large input was created. There were zero reservations, native/scientific
cases, RNG draws and telescope reads. The invocation is spent and was not retried;
the marker must not be reused. The next engineering step is to specify and test one
consistent runtime-file custody policy across freeze construction and activation,
without tuning this failed evaluation to pass or opening telescope data.
