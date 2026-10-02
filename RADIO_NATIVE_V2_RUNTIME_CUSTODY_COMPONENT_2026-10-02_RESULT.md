# Radio native v2 — runtime-custody proof component

**Result: PASSED_COMPONENT_ONLY_NOT_INTEGRATED.** A new read-only component builds a
portable custody manifest from the frozen runtime inventory. It hashes through
`O_NOFOLLOW` descriptors with before/after/named identity equality, requires every
post-activation runtime file to be sole-link, and closes allowed activation-only Git
hardlink groups by exact alias roots and `st_nlink` count. Device and inode numbers
are used only during observation and are not published as portable identity.

- [Component](scripts/radio_native_v2_runtime_custody.py)
- [Eight tests](tests/test_radio_native_v2_runtime_custody.py)
- [Verification summary](results_radio_native_v2_runtime_custody_component_20261002a/verification-summary.json)
- [Test log](results_radio_native_v2_runtime_custody_component_20261002a/tests.log)
- [Retained discovery failure](results_radio_native_v2_runtime_custody_component_20261002a/failed-first-invocation.json)
- [Adjacent suite](results_radio_native_v2_runtime_custody_component_20261002a/adjacent-suite-summary.json)
- [Retained adjacent discovery failures](results_radio_native_v2_runtime_custody_component_20261002a/failed-adjacent-suite-first.json)
  and [second failure](results_radio_native_v2_runtime_custody_component_20261002a/failed-adjacent-suite-second.json)
- [Public science/main readback](results_radio_native_v2_runtime_custody_component_20261002a/publication-readback.json)

All eight tests pass in 5.067 seconds, including hidden/added aliases, unexpected
material hardlinks, same-byte relinking, hash drift and symlinks. The real 1,366-path
freeze reproduces the six groups and 157-alias closure. The ten-module adjacent suite
passes **223 tests in 94.093 seconds**. Two incomplete import-path suite invocations
and the initial isolated discovery failure are retained rather than hidden.
Science commit `49a23b83...` and main commit `ce1b9bab...` have matching independent
parent, tree and material-blob readback.

The component is deliberately not integrated into the freezer, marker receipt,
workers or runner yet. It grants no new activation/control, and the failed marker and
invocation remain spent. Next is pre-write integration plus fresh plan/freeze only
after the adjacent suite passes; this is not a retry of the failed evaluation.
