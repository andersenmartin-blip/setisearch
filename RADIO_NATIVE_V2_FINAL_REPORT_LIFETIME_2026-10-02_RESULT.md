# Radio native v2 — independently observed final-report lifetime

**Result: FINAL_REPORT_WRITER_LIFETIME_COMPONENT_VERIFIED_EXECUTION_BLOCKED.**
The whole-control path no longer asks the process that writes the final resource
report to certify its own future termination. A fixed isolated child now writes the
report exclusively, fsyncs the file and containing directory, and returns. Its
parent binds the launched process identity, observes the complete lifetime through
kernel `wait4`, persists that observation, and performs a read-only join of the
pinned input, report, writer identity and observation.

The durable report remains truthful before the join: it records that writer
termination still requires observation. Only the later read-only join marks final
report fsync and termination covered. The observation receipt explicitly does not
claim proof of its own writer's future termination; that is not part of the measured
report-writer lifetime. All terminal files share the existing 256-KiB metadata
reservation, and the integrated control rechecks actual storage, elapsed time and RSS
after the observation exists.

## Actual control and regression evidence

A fresh tiny control ran the plan-pinned Python with `-I -S -B` and the exact
three-variable child environment. The report writer completed in **0.047 s**;
the maximum individual writer/observer RSS was **15,646,720 bytes (14.92 MiB)**.
The persisted report is 1,189 bytes and its independently joined SHA256 is
`5a4ea255c4d82b4289b3a3e619a433035284e9d09f9b9c2efd8e8529fcfb05f0`.

The adjacent eight-module suite passes **206 tests in 79.216 s**, including an
actual isolated report-writer process and negative byte-pin, identity, argv,
environment, filesystem and resource-bound controls. No full-size source,
eight-input control, reservation, RNG, native case or telescope spectrum ran.

- [Prospective plan revision h](config/radio_native_v2_compact_eight_input_control_20261002h.plan.json)
- [Verification summary](results_radio_native_v2_final_report_lifetime_20261002a/verification-summary.json)
- [Writer observation](results_radio_native_v2_final_report_lifetime_20261002a/final-report-control/final-report-writer-observation.json)
- [Persisted report](results_radio_native_v2_final_report_lifetime_20261002a/final-report-control/resource-final-disposition.json)
- [Test summary](results_radio_native_v2_final_report_lifetime_20261002a/final-test-summary.json)
- [Passing test log](results_radio_native_v2_final_report_lifetime_20261002a/final-tests-stderr.log)
- [Reproduction script](results_radio_native_v2_final_report_lifetime_20261002a/verify_final_report_lifetime.py)

## Refreshed runtime evidence and continuation

The code change has a fresh current-code runtime freeze rather than reusing the
earlier one. It pins **922 repository code files**, **9 inputs** and **1,366 runtime
files**; SHA256
`7508ad76e7fad69ce31b718ab3b10be88a2194072d2239d2319dd5ad83248843`.
The isolated ten-variable parent-environment check again passes with empty stderr.

- [Refreshed runtime freeze](config/radio_native_v2_activation_environment_20261002b.runtime.json)
- [Runtime refresh summary](results_radio_native_v2_runtime_refresh_20261002b/verification-summary.json)
- [Exact parent receipt](results_radio_native_v2_runtime_refresh_20261002b/parent-check-stdout.json)
- [Runtime refresh script](results_radio_native_v2_runtime_refresh_20261002b/capture_runtime_refresh.py)
- [Public preparation readback](results_radio_native_v2_final_report_lifetime_20261002a/publication-readback.json)

Science commit `37b938c31e12647d8193ec3fcdb95d1e1378f385` is a
fast-forward child of `04d13f1a6caae2c1669dbdcd0a3bb79d1f693c2c`; its public
tree exactly matches the local candidate tree. Main commit
`df4c71563b8cfda68d75a00850563c4e75863fd3` is a fast-forward child of
`81c11052504a92128f602a291214e7b924be44d2`; the public README blob matches
the local bytes. This is verified public **preparation** readback, not the still
future execution-qualified preread.

Revision `20261002h` remains **BLOCKED_PREPARATION_REVIEW**. The report-writer
lifetime component is closed, but the published freeze still states that the
operating-system kernel is not frozen. Exact activation-time platform closure and a
distinct execution-qualified public preread remain required before one fresh
eight-input engineering resource control may be considered.

**Exact continuation:** define and verify the bounded activation platform contract,
then publish and read back a distinct execution-qualified preread. Do not open the
large inputs before those gates. HD189733 remains selected, HD1461 HOLD and GJ724
reserve. 127/24 is NOT ACTIVATED; spectra and original holdouts remain unopened; LS
paused; CHEOPS UNSENT. Consolidate 9 October without extension. No external messages.
