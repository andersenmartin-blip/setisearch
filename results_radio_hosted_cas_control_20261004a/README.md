# Hosted exact-CAS service control 20261004a

See the [prospective protocol](../RADIO_HOSTED_CAS_CONTROL_2026-10-04_PROTOCOL.md).
Code and local synthetic tests are inert preparation until the immutable source
freeze is published and read back and its separate marker-only activation occurs.

The one hosted child may add `service-state.json`, prepare an unreachable
`conflict-test-state.json` candidate and attempt a stale-before comparison. A
separate bounded publisher may add `evidence.json` only after reaping. Every
outcome spends the original attempt. No rerun, scientific data or authority.

Retained development logs include source hashes and complete test output. Any
failures and their available source snapshots remain historical evidence; final
source identities come from the immutable freeze manifest.

Final preparation: **90 focused synthetic tests pass** (gate20, control21,
supervisor23, publisher26). `integration-tests02.log` retains the complete output
and matching before/after inventory of all ten selected files. No actual service
result is inferred. The execution-source set totals179,599bytes.

Development failures retained: command-line exit handling, source token-pattern
collision, procfs PID namespace mapping, initial publication URL construction and
publication fixture newline modeling. Preserved source snapshots cover the named
failures; early passing development logs do not all have separate source snapshots.
The immutable manifest identifies final execution sources.
