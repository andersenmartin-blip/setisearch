# K administrative runtime recovery

[Prospective contract](PROTOCOL.md) and [source freeze](SOURCE_FREEZE.json).

`recovery.py` performs contained copy-only recovery against immutable original
C byte pins. `run_recovery.py` is the bounded administrative controller. Native
dispatch always refuses. Neither component grants runtime/codec/science
authority. The independent review checks new current files without claiming
old custody.

All 36 new manufactured source/filesystem tests pass in `tests-final.log`.
`tests-wrapper-first-failure.log` retains two test-harness errors: the isolated
driver imports a distinct Refusal class, and the two assertions initially
expected the parent component's class. Assertions now check the documented
ValueError base and message; recovery semantics and failing-input disposition
were unchanged. The suite uses fabricated bytes and paths only; none are target
packages or scientific validation cases.

The archive transfer attempts failed with HTTP 502 and materialized no archive.
The failures are retained; no unchanged transfer or installation is retried.
Actual recovery result will be appended only after public source readback.
