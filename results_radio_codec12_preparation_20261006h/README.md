# Codec12 H source-only preparation

Status: `SOURCE_ONLY_NO_DISPATCH`.

This checkpoint fixes the complete controlled codec evidence shape required by
the published scientific admission validator without opening archive spectra.
It binds, in order, the six calibration scans followed by the six validation
scans, all 16 rows per handoff, and the 22 original metadata laws.

The preparation does not issue a codec certificate.  It creates no activation,
allocation, HDF5 file, native import, controlled payload, RNG draw, network
request, telescope read or scientific case.  The pure metadata control executes
the exact pinned 1,651-byte filter guard and observes 22/22 expected outcomes
with zero payload indexing.

Files:

- `INPUT_MANIFEST.json`: 14 original raw source/evidence pins at authority commit
  `505b2adc210c11701a3762383d2bfb8eb8986ec1`.
- `SELECTED_CODE.json`: exact maintained normalizer AST selections, inspected but
  not compiled here.
- `PLAN.json`: ordered handoffs, law order, deterministic controlled-row formula,
  future resource proposal and closed gates.
- `METADATA_LAW_OBSERVATION.json`: the 22 pure metadata outcomes.
- `SOURCE_ONLY_REVIEW.json`: source-only disposition and exact continuation.
- `PROTOCOL.md`: future freeze/activation boundary.
- `preparation.py`, `metadata_law_control.py`, `test_source_preparation.py`: the
  reproducible stdlib-only builders and nine regression tests.

The prior G output is closed design evidence only.  No G HDF5 output or row hash
is reused.  A future control needs a distinct immutable outer freeze, fresh
runtime inventory, complete native lifetime accounting, one-shot activation and
independent result review before it may create these 12 controlled handoffs.
