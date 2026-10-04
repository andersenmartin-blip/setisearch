# Prospective bounded scientific runner (4 October 2026)

This package closes one specific preparation gap left by control F: it joins
the maintained scientific admission/closure types, the receiver adapter's
per-load clock record and the bounded raw failure-output utility around one
exclusive child dispatch. It does **not** open telescope values, manufacture
an admission, qualify a host runtime or activate a scientific allocation.

`bounded_scientific_runner.py` requires all of the following before launch:

- a maintained `VerifiedAdmission` bound byte-for-byte to a maintained
  `VerifiedClosure`;
- the exact executable-freeze document authenticated by that closure;
- every launcher/retention/receiver file bound to a distinct identity in the
  freeze inventory, with exact path, mode, size and SHA256 read before launch
  and stable held/visible identity after launch;
- one explicit finite environment, argv, stream caps and timeout no longer
  than the authenticated current source session;
- an exclusive outside-repository destination. Reuse is refused.

The child must return one canonical JSON envelope bound to the dispatch,
admission, session and receiver-adapter identities. Synthetic results can only
qualify the interface with both `scientific_execution_authorized` and
`telescope_values_opened` false. Nonzero exit, timeout, output overflow,
malformed/noncanonical output, wrong binding, missing per-load clock evidence,
clock regression/expiry or persistence failure closes the dispatch without a
retry. Exact retained raw stdout/stderr remain available in the capture result.

## Qualification result

The new 25-test suite passes with zero failures, errors or skips. It exercises
real child processes for zero/nonzero exit, timeout, output overflow and
exclusive destination reuse. It also tests explicit-environment isolation,
closure/inventory substitution, admission/session/result binding, canonical
encoding and synthetic telescope/authority refusals. The independently
selected adjacent regressions also pass: 148 admission/runtime/store/receiver
tests and 24 failure-retention tests.

This is a synthetic interface qualification only. It is not a sandbox or a
whole-host lifetime certificate. The real hosted-native/public-runtime and
atomic-CAS qualifications, new actual executable freeze, fresh source session,
irrevocable allocation/ledger and real child implementation remain missing.
No actual runner dispatch, CAS mutation, telescope read, native case, source
request or reserved 127/24 trial occurred.

See `qualification-evidence.json` and
`RADIO_BOUNDED_SCIENTIFIC_RUNNER_2026-10-04_RESULT.md` in the repository root.
