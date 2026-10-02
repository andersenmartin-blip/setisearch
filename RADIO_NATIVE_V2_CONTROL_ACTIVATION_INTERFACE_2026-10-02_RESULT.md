# Radio native v2 — marker-proof component

**Result: MARKER_PROOF_COMPONENT_VERIFIED_NOT_INTEGRATED_EXECUTION_BLOCKED.** A new
stdlib-only component verifies the future one-control marker without importing or
running the material fixture. It grants no current authority and is deliberately not
yet threaded into the outer runner or worker bundles.

The component requires an exact single-parent activation checkout whose only tree
change is the addition of the unique marker. It binds the direct preread parent/tree,
canonical plan/freeze/preread hashes, their parent-commit Git blobs, a separate public
activation-readback receipt, one invocation, and all false reservation/RNG/native/
science/restart/retry flags. Workers can independently recheck the bounded receipt
against their embedded plan, freeze and preread before a future write.

## Verification

Four isolated synthetic-Git tests pass in **0.355 s**. They cover the exact marker-only
path, changed receipt pins/authority, a non-marker-only successor and changed public
readback. The adjacent nine-module blocked suite passes **211 tests in 81.898 s**.

- [Marker-proof component](scripts/radio_native_v2_control_activation.py)
- [Synthetic Git tests](tests/test_radio_native_v2_control_activation.py)
- [Verification receipt](results_radio_native_v2_control_activation_interface_20261002a/verification-summary.json)
- [Adjacent test log](results_radio_native_v2_control_activation_interface_20261002a/adjacent-tests-stderr.log)
- [Retained first test-invocation failure](results_radio_native_v2_control_activation_interface_20261002a/failed-first-test-invocation.json)
- [Verifier](results_radio_native_v2_control_activation_interface_20261002a/verify_activation_interface.py)
- [Publication readback](results_radio_native_v2_control_activation_interface_20261002a/publication-readback.json)

The retained failure used `python -I -m unittest` with repository module discovery;
isolated mode correctly removed that import path. Direct isolated component execution
and the established explicit-PYTHONPATH adjacent harness then passed. No test failure
was tuned into a pass.

Science commit `96e4ad65fb9353b43027a101009b5d0a4479d822` has the expected
parent and tree, and its component, test, report and verification-summary blobs match.
Main commit `9887b0b07fb0f594325b2c8e822b4725b4251f7f` has the expected
parent, tree and README blob. This public readback freezes the proof component; it is
not the future activation marker.

## Boundary and continuation

This is only phase 1's proof component. `outer_runner_integration_complete=false`,
`worker_bundle_integration_complete=false`, and `activation_marker_created=false`.
It is not in a new material plan/freeze yet; therefore the old preread cannot cover it
and the current runner remains hard closed. No large input, control, reservation, RNG,
telescope read, native case or science case occurred.

**Exact continuation:** version the worker bundle to carry this exact receipt, thread
it through every role and the outer invocation, and require validation before any
scope/source write. Add missing/malformed/stale/wrong-parent/wrong-tree/reused-marker
pre-write refusal tests. Only then create a fresh still-blocked plan and complete
runtime freeze; never reuse the current preread. HD189733 remains selected, HD1461
HOLD and GJ724 reserve. 127/24 is NOT ACTIVATED; spectra and original holdouts remain
unopened; LS paused; CHEOPS UNSENT. Consolidate 9 October. No external messages.
