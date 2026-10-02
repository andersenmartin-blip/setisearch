# Radio native v2 — bounded activation platform contract

**Result: BOUNDED_ACTIVATION_PLATFORM_VERIFIED_EXECUTION_BLOCKED.** The prospective
plan now carries a secret-free platform identity that is recomputed inside the same
isolated process that verifies the exact parent environment and runtime paths.
Any changed or missing top-level platform field closes validation.

The contract binds the exact uname/kernel release and boot identity, selected public
kernel controls, capability masks, `NoNewPrivs`, seccomp mode/filter count, page size,
clock ticks, byte order, filesystem encoding, Python implementation/version/cache tag,
glibc identity and the current LSM label bytes. Missing optional sysctls are represented
explicitly as `null`; no environment secrets, credentials or network configuration are
included.

This is deliberately a **bounded activation identity**. It does not claim that the
operating-system kernel binary or every kernel state byte is frozen. The inherited
pre-exec no-new-privileges/seccomp guard and terminal subreaper evidence remain the
separate process-tree controls.

## Actual check and freeze

The plan-pinned Python ran with `-I -S -B`, the exact ten-variable parent environment
and empty stderr. It reproduced platform-contract SHA256
`139d0e9533aa22069d848d4731e40ef20b0360a46a4f0536d04ffcbdf3563b20`.
The fresh current-code freeze pins **922 repository code files**, **8 inputs** and
**1,366 runtime files**; SHA256
`ee5f8f4c3fc8bc55749b4fdbe09a1eabc64d7bb948ac4d20d6f8bf8ea952cc0e`.

The adjacent eight-module suite passes **207 tests in 90.987 s**. These are blocked
preparation, refusal and tiny process controls. No large source, eight-input resource
control, native case, reservation, RNG or telescope spectrum was opened.

- [Prospective plan revision i](config/radio_native_v2_compact_eight_input_control_20261002i.plan.json)
- [Current runtime freeze](config/radio_native_v2_activation_environment_20261002c.runtime.json)
- [Exact parent/platform receipt](results_radio_native_v2_activation_platform_20261002a/parent-check-stdout.json)
- [Verification summary](results_radio_native_v2_activation_platform_20261002a/verification-summary.json)
- [Test summary](results_radio_native_v2_activation_platform_20261002a/final-test-summary.json)
- [Passing test log](results_radio_native_v2_activation_platform_20261002a/final-tests-stderr.log)
- [Reproduction script](results_radio_native_v2_activation_platform_20261002a/verify_activation_platform.py)
- [Public preparation readback](results_radio_native_v2_activation_platform_20261002a/publication-readback.json)

Science commit `e3f1cb8ac10805a2268f861b3c133844afe7b3d4` is a
fast-forward child of `fd230e7cdf0cf512c3c6342c22309c9d5886a536`; its public
tree is byte-identical to the local candidate. Main commit
`eef3e74fea466e69f42227fa839948091beb9185` is a fast-forward child of
`df4c71563b8cfda68d75a00850563c4e75863fd3`, and its README blob matches.
This is public **preparation** readback, not the distinct execution preread.

## Disposition and continuation

Plan revision `20261002i` remains **BLOCKED_PREPARATION_REVIEW** and the historical
preparation contract is not rewritten to ready. The runtime files, exact parent
environment, bounded platform and outer final-report lifetime components are now
prepared and actually checked, but this new plan/freeze has not yet received a
distinct immutable public execution preread. All execution, reservation and science
authority remains false.

**Exact continuation:** construct and independently verify the separate
execution-qualified preread without changing the historical preparation contract.
Do not open large inputs until that distinct gate is verified. HD189733
remains selected, HD1461 HOLD and GJ724 reserve. 127/24 is NOT ACTIVATED; spectra and
original holdouts remain unopened; LS paused; CHEOPS UNSENT. Consolidate 9 October
without extension. No external messages.
