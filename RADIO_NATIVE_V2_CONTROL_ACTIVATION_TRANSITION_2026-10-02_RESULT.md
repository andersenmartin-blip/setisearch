# Radio native v2 — one-control activation transition

**Result: TRANSITION_PROTOCOL_VERIFIED_EXECUTION_STILL_BLOCKED.** The exact public
preparation, execution-preread and readback-closure parent/tree chain now verifies,
as do the current plan, freeze, preread, material runner and worker-admission pins.
The 5,319-byte prospective protocol has SHA256
`722aca034d799eda6bfd2785a7885f7739486d018618d564e38fc0fa78444150`.

## Blocker isolated

The published preread correctly carries `engineering_control_admitted=true`, but it
cannot activate the current frozen runner. The runner calls its constant
`require_execution_ready()` refusal as the first executable statement in the outer
activation validator, run, control worker, verifier worker, command worker and
exec-command child. It therefore refuses before any preread or role bundle can be
validated. This is fail-closed and no scope or source was created.

Simply changing that runner would invalidate the existing plan/freeze/preread pins.
Simply adding a marker would not help because the current runner has no marker
interface. The protocol closes that pin cycle with seven ordered phases: prepare a
fail-closed activation-proof interface; freeze it in a new still-blocked plan; publish
and read back the preparation; publish and read back a fresh preread; add exactly one
marker in a marker-only direct-child commit; run one fresh control; preserve the final
pass/fail disposition without tuning.

- [Frozen transition protocol](config/radio_native_v2_control_activation_transition_20261002a.protocol.json)
- [Verification receipt](results_radio_native_v2_control_activation_transition_20261002a/verification-summary.json)
- [Verifier](results_radio_native_v2_control_activation_transition_20261002a/verify_transition_protocol.py)
- [Retained raw/canonical digest failure](results_radio_native_v2_control_activation_transition_20261002a/failed-first-attempt.json)
- [Retained AST-docstring failure](results_radio_native_v2_control_activation_transition_20261002a/failed-second-attempt.json)

The two verifier failures occurred before any execution. The first confused raw-file
SHA256 with canonical-JSON SHA256; the second counted function docstrings as
executable statements. Both corrections are explicit and both failures are retained.

## Authority and continuation

The protocol does not activate anything. The historical plan remains
`BLOCKED_PREPARATION_REVIEW`; no existing plan or preread was rewritten. No large
input, eight-input control, reservation, RNG, telescope read, native case or science
case occurred, and no retry is authorized.

**Exact continuation:** implement phase 1 only: add the fail-closed activation-proof
input to the outer invocation and every independently admitted worker, with refusal
tests proving that missing, malformed, stale, non-marker-only and unverified proofs
fail before a scope or source write. Then generate a new still-blocked plan/freeze;
do not reuse the current preread. HD189733 remains selected, HD1461 HOLD and GJ724
reserve. 127/24 is NOT ACTIVATED; spectra and original holdouts remain unopened; LS
paused; CHEOPS UNSENT. Consolidate 9 October without extension. No external messages.
