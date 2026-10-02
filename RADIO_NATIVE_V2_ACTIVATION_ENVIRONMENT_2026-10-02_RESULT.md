# Radio native v2 — exact activation parent environment

**Result: EXACT_PARENT_ENVIRONMENT_VERIFIED_EXECUTION_BLOCKED.** A new standalone
checker derives a secret-free parent environment only from executable paths pinned
by the prospective plan and complete local runtime freeze. It requires exact equality
before protected admission: missing, changed or additional variables all refuse.

The contract contains ten public values: a PATH built from the pinned Python, Node
and Git directories plus `/usr/bin` and `/bin`; `LANG=C`; `LC_ALL=C`;
`HOME=/nonexistent`; Python safe-path/no-user-site controls; and four Git controls
that disable system/global configuration, prompting and lazy fetch. It deliberately
does not inherit the automation parent's proxy, session or credential variables.

## Actual control and freeze

The checker ran as the plan-pinned absolute Python executable with `-I -S -B` and
the exact derived environment. It verified its complete `os.environ`, the blocked
plan and fresh freeze, and returned a 2,000-byte receipt with empty stderr. The
fresh freeze pins **922 repository code files**, **8 input files** and **1,366 runtime
files**; SHA256 `2c756a55cf6f629661a1154a1902732c2a8568114978c4aa505a5f512f6f9ac5`.

The adjacent eight-module regression suite passes **204 tests in 80.657 s**. These
are preparation and negative controls. No full-size source, eight-input resource
control, native case or telescope spectrum was opened.

- [Prospective plan revision g](config/radio_native_v2_compact_eight_input_control_20261002g.plan.json)
- [Fresh runtime freeze](config/radio_native_v2_activation_environment_20261002a.runtime.json)
- [Exact parent receipt](results_radio_native_v2_activation_environment_20261002a/parent-check-stdout.json)
- [Verification summary](results_radio_native_v2_activation_environment_20261002a/verification-summary.json)
- [Test summary](results_radio_native_v2_activation_environment_20261002a/final-test-summary.json)
- [Passing test log](results_radio_native_v2_activation_environment_20261002a/final-tests-stderr.log)
- [Public preparation readback](results_radio_native_v2_activation_environment_20261002a/publication-readback.json)
- [Reproduction scripts](results_radio_native_v2_activation_environment_20261002a/)

## Boundaries and continuation

Science commit `918e7e3eaf1890338fbb74c8e263f8d9e71a8184` and main commit
`5cc62c40755e790bb810e07b431eb29c785008c4` were read back; the plan, freeze,
parent receipt, report and README blob identities match. This is immutable public
**preparation** readback, not the still-future execution-qualified preread.

This verifies the prospective parent-environment contract and an actual isolated
check. It does not turn the local file freeze into complete runtime qualification:
kernel/platform closure, activation-time integrated recheck, immutable public
execution preread and the outer final-report fsync/termination boundary remain open.
Plan revision `20261002g` therefore remains `BLOCKED_PREPARATION_REVIEW`; every
execution, reservation and scientific authority remains false.

**Exact continuation:** close the remaining activation-time runtime/platform and
outer final-report lifetime joins, then publish and read back a distinct
execution-qualified preread. Only after that may one fresh eight-input engineering
resource control be considered. HD189733 remains selected, HD1461 HOLD and GJ724
reserve. 127/24 is NOT ACTIVATED; spectra and holdouts remain unopened, LS paused,
CHEOPS UNSENT. Consolidate 9 October without extension. No external messages.
