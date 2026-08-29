# Milestone 37 detector-v0.6 resource run-manifest checkpoint

Status: **NON-FROZEN SYNTHETIC CHECKPOINT — RESTARTABLE RESOURCE RUN
INVENTORY PASSED — FIVE-WINDOW M37 GATE BLOCKED — NO SPECTRAL ACCESS**.

This checkpoint adds the run-level inventory required between a per-window
physical-resource artifact and the restartable M37 journal. It was implemented
and tested without opening, requesting or inspecting an HD 156668 / HIP 84607
telescope spectral payload. It is not a detector release, preregistration,
search, completeness result, null result or signal claim.

## Why this intermediate artifact is required

The physical resource envelope and its persisted artifact are scoped to one
frequency window. The run journal describes the complete five-window M37 run.
Advancing that journal from one window would incorrectly present a partial
inventory as a complete physical stage.

The new run manifest therefore requires a caller-supplied ordered window
inventory, one unique canonical child path per window, a common run ID,
cache-run manifest and factor bundle, plus an independently supplied ordered
ON-retention inventory identity. It does not advance the journal.

## Closed bounded gates

- Every entry is created from an already opened physical-resource artifact and
  binds its file, envelope, window, ON-retention and resource-accounting
  values.
- Publication reopens every child from its canonical path under the run root
  before creating the manifest. Absolute paths, traversal and duplicate paths
  fail closed.
- Missing, duplicated or reordered windows fail before publication. All
  windows must share one run, cache-run manifest, factor bundle and mapped-byte
  cap.
- The read-only canonical manifest has a 4,194,304-byte cap, no-replace atomic
  publication, file fsync and parent-directory fsync.
- Restart opening requires independent file, manifest, run, cache-manifest,
  factor-bundle and ON-retention-inventory identities, then fully reopens every
  child artifact.
- The M37 wrappers require all five `M37_WINDOW_IDS` in exact order and apply
  the exact M37 validator to every child before publication or acceptance.

## Synthetic known answers

The bounded fixture contains one synthetic window and one real read-only child
artifact. It proves the generic inventory and restart contract; it is not a
five-window M37 run.

| Artifact | Value |
|---|---|
| Run-manifest file SHA-256 | `4f9f8fad548afb51aabede5703b3a77ee99f48a89e2b1ea4b8d83add3e29fa11` |
| Run-manifest identity | `76e751f689c74e17f6abac2be3e855a32387bd0d07000664b199abe220d9e6ea` |
| Resource-artifact inventory | `266932487d92bb814740b9ff89254f758e652b5912f25c1518ff4a14caf599e7` |
| ON-retention inventory | `9d1a971a13fab595ba60caa46ca072dca348db2d24aa514a2d1db23ef88f665a` |
| Run-manifest canonical bytes | `1,468` |
| Child resource-artifact bytes | `8,474` |
| Offline wheel SHA-256 | `b33dd51b2c131ab9f8ebc44bcbae0b1ed04a90d1cb2578e08ca50362a0d48696` |

The manifest reproduces the child's measured peak of 81,600 mapped bytes and
three handles, with two batches and six cache opens. These values are bounded
synthetic contract facts, not production resource measurements.

## Verification

| Check | Result |
|---|---|
| Targeted cache-stream, receiver, adjacent and resource suite | 33 passed, 0 skipped, 0 failed |
| All Astropy-independent repository tests | 207 run, 206 passed, 1 expected benchmark skip, 0 failed |
| Dependency-complete repository suite | Blocked in this runtime: declared `astropy>=6.0` is absent |
| Offline wheel build, isolated install and manifest-module import | Passed |
| Missing window or wrong external retention root | Rejected before publication |
| Path traversal or mutated child file | Rejected |
| Synthetic inventory expanded into M37 | Rejected before publication |
| HD 156668 spectral files contacted | No |
| Spectral dataset values read | No |

The full discovery attempt produced no test assertion failures, but four test
modules could not import without Astropy and two additional Astropy-dependent
classes were skipped. Those tests are not counted as passed. The previously
published dependency-complete baseline remains 266 tests; this change adds
three tests and requires a later pinned-environment rerun of all 269.

## Claim boundary and remaining blockers

This closes only the generic run-inventory and restart contract using a
one-window synthetic fixture. No exact five-window M37 resource run manifest
exists, because no authorized production extraction, cache run, retention
inventory or physical evidence artifact exists.

The manifest still binds compact resource envelopes rather than the complete
receiver and adjacent evidence payloads. It is not joined to the phase-3 alias
disposition result and is not attached to a journal transition. The next
honest integration step is to define that join without treating resource
accounting alone as completed physical disposition.

The machine-readable checkpoint is
`results_m37_v0p6_resource_run_manifest/progress.json`.
