# Separate receiver subprocess v2 candidate

This version corrects two reproduced v1 gaps: destination-based replay and
acceptance of an empty per-load clock. V1 and all historical evidence remain
unchanged. V2 is engineering-only and categorically refuses public scientific
execution. Its fixed isolated child runs the maintained validators and receiver
over complete synthetic metadata and 96 tiny pinned rows, rather than printing
a caller-authored envelope or constructing private verification tokens.

`runner_v2.py` reserves a durable dispatch-identity directory in an independently
pinned external registry before child work. Changing the output destination
cannot bypass this local identity claim. A parent crash, failure or success
spends it permanently in that registry. It records exact stdout/stderr and
preserves capture on post-run validation failure. Child row calls and all twelve
clock observations are checked individually. The claimed result does not imply
actual global CAS, runtime/native/transport, memory or descendant qualification.

`synthetic_receiver_child.py` has no telescope loader, remote acquisition or
scientific RNG. `fixture_scope.py` uses the preserved maintained test fixture;
its simulated publications/outcomes remain synthetic and cannot authorize science.
`smoke_entry.py` executes only an externally pinned scope with an independently
retained local registry identity. The [prospective protocol](../RADIO_RECEIVER_RUNNER_V2_2026-10-04_PROTOCOL.md)
freezes exactly one integration invocation; its result is pending publication.

The 21 targeted tests passed in 6.033 seconds, zero failures/errors/skips, in
`development_test_02.log`. The first development failure is retained separately:
the selected 30,894,944-byte Python executable exceeded the initial 16 MiB
bound before child dispatch. The explicit executable-only bound is now 64 MiB;
the metadata/stream limits are unchanged. The exact packet is losslessly archived
as gzip/base64 with both compressed and raw SHA256/counts. Restoration grants
no continuity of its original absolute input or claim registry.

No old code, preparation contract, scientific identity, acquisition ledger,
allocation, spectrum, holdout or terminal disposition was altered. The active
plan still ends with consolidation on 9 October 2026.
