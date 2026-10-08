# Single permitted operational development correction, 8 October 2026

The approved 7–20 October plan permits one development correction followed
by entirely fresh validation. Full A remains FAIL_CLOSED: required diagnostics
128/129 timed out; excluding or replaying either would invalidate the gate.
Telescope values and all B realizations remain closed.

The only correction is operational allocation: a bounded child may use up to
1800 CPU seconds, still <=1800 wall seconds and 4GiB, with rolling exclusive
reservations instead of reserving all142 child maxima simultaneously.
Unused reservation is refunded only after a child is reaped and whole
resource use is charged. A failure or absent receipt never receives a refund
based on an assumed zero. Concurrent reservations cannot spend the same
remaining CPU capacity. The controller must preserve any failure and stop
when another full partition cannot fit; no redraw, retry or seed replacement.

Scientific detector, generator, contract, summarizer, thresholds, source
geometry, recovery tolerances and all existing frozen case banks are unchanged.
Two freshly declared DEV_RUNTIME cases use the parameters of the two dense
late-ON transient geometries, with unique new SHA256 identities/PCG64 seeds.
They are development evidence, never fresh scientific validation. Both must
complete the original entire search, maps, OFF dispositions, truth/recovery,
hashes and resource accounting before any B RNG draw is admitted.

B is the existing once-only, unchanged 142-case frozen VAL_B manifest.
Its full original nine checks must pass; completed diagnostics remain
required for integrity even though they carry no recovery threshold.
If correction DEV or B fails, the study switches to the approved method
investigation. No second correction, third engineering route, replacement
panel or reopening of historical holdouts is authorized.

Known remaining capacity after closed A is25492.071999981CPU-s. Root retains
an additional1200CPU-s conservative planning reservation for unmeasured
preparation/orchestration; it is not a claimed measured total or proved bound
on every historical action. Two development partitions reserve1800CPU-s each.
Fresh B's precise aggregate allocation follows the two actual development
receipts and reviewed ledger. All failures count; the global43200CPU-s,
4.25GiB source aggregate,2GiB per pilot,4GiB job memory,8GiB local artifacts,
zero-cost and1800wall-s constraints stay unchanged.

Publication is separate from analysis and never authorizes a control rerun.
