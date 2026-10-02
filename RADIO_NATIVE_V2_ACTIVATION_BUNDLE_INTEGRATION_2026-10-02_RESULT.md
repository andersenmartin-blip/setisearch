# Radio native v2 — activation receipt bundle integration

**Result: ACTIVATION_RECEIPT_INTEGRATED_NEW_PREPARATION_BLOCKED.** The marker-proof
receipt is now threaded through the outer invocation, versioned preparation and role
bundles, every Python/Node worker entry, the subreaper supervisor and the independent
measurement driver. Every worker rechecks the receipt's exact plan, freeze and preread
canonical pins plus its false authority fields before any material write.

The plan remains **BLOCKED_PREPARATION_REVIEW** and `activation_guard_complete=false`.
The historical contract was not rewritten. The outer CLI can only derive a receipt by
verifying the future marker checkout and a separate public activation-readback receipt;
missing marker/readback evidence exits nonzero without creating the requested scope.

## Tests and fresh freeze

The nine-module adjacent suite passes **215 tests in 84.413 s**. A fresh current-code
plan revision `20261002j` and runtime freeze bind **923 repository code files**, **9
inputs** and **1,366 runtime files**:

- plan: 64,726 bytes, SHA256
  `c74f448db2f652708dfca3c3093605d53d43dc3c2d632ef973c2f29a7cead932`
- freeze: 509,776 bytes, SHA256
  `525cab518137de79e5331380ef64b71fe46036a86090cdb92fa88fb1579ddb56`

The exact isolated parent/platform check passes with the activation guard false. The
pre-marker CLI control exits 1; neither its scope nor readback path exists afterward.

- [Still-blocked plan j](config/radio_native_v2_compact_eight_input_control_20261002j.plan.json)
- [Fresh complete runtime freeze d](config/radio_native_v2_activation_environment_20261002d.runtime.json)
- [Integration receipt](results_radio_native_v2_activation_bundle_integration_20261002a/verification-summary.json)
- [Passing test log](results_radio_native_v2_activation_bundle_integration_20261002a/tests-stderr.log)
- [Pre-marker refusal](results_radio_native_v2_activation_bundle_integration_20261002a/pre-marker-stderr.log)
- [Retained first targeted-suite failure](results_radio_native_v2_activation_bundle_integration_20261002a/failed-first-targeted-suite.json)
- [Retained isolated verifier-import failure](results_radio_native_v2_activation_bundle_integration_20261002a/failed-second-verifier-invocation.json)
- [Verifier](results_radio_native_v2_activation_bundle_integration_20261002a/verify_bundle_integration.py)
- [Publication readback](results_radio_native_v2_activation_bundle_integration_20261002a/publication-readback.json)

The first targeted suite retained 10 failures and 7 errors because obsolete tests
expected the unconditional gate even when a valid synthetic receipt should now pass to
later tiny checks; tests were changed to inject invalid receipts for gate refusals. The
first orchestration invocation used `-I -S`, which intentionally hid installed NumPy
from the runtime-freeze collector. Both failures occurred before large input or control
execution and remain preserved.

Science commit `25e9df222af79c677adc1ad247104fd6b0c4d68e` has the expected
parent/tree and all changed material blobs match, including the plan, freeze, runner,
worker admission, report and summary. Main commit
`bb20e468aa6fd8b816c4a5a51bf0d755d01a787f` has the expected parent/tree
and README blob. The new preparation therefore has independent public readback.

## Disposition and continuation

No activation marker exists. This new plan/freeze now has public preparation readback
but no fresh execution preread, so it cannot run. The old preread is not reused. No
large input, eight-input control, reservation, RNG, telescope read, native case or
science case occurred.

**Exact continuation:** create a new distinct preread bound to public preparation
commit `25e9df222af79c677adc1ad247104fd6b0c4d68e`, publish it and
independently read it back. Do not add the marker until that new preread is
public and read back, and do not place an intervening science-branch commit between
the preread and its future marker-only child. HD189733 remains selected, HD1461 HOLD
and GJ724 reserve. 127/24 is NOT ACTIVATED; spectra and original holdouts remain
unopened; LS paused; CHEOPS UNSENT. Consolidate 9 October. No external messages.
