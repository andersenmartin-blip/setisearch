# Milestone 37 detector-v0.6 sparse-retention phase-2 checkpoint

Status: **NON-FROZEN SYNTHETIC CHECKPOINT — RETENTION, OFF AND RANK-P
REFERENCE PASSED — PRODUCTION GATE BLOCKED — NO SPECTRAL ACCESS**.

This checkpoint extends the phase-1 sparse/local numerical reference through
bounded synthetic exhaustive retention, retained-OFF disposition and global
rank-p. It was implemented and tested without opening, requesting or
inspecting an HD 156668 / HIP 84607 telescope spectral payload. It is not a
detector release, preregistration, search, completeness result, null result or
signal claim.

## Closed synthetic gates

- A mandatory dense-score oracle covers all 3,936 cells in the three-template,
  eight-width and four-activity-subset fixture. The oracle is capped at
  1,000,000 cells, which prevents this KAT API from being applied to the M37
  production grid.
- The ON reference evaluates 352 selected cells and proves all 3,584 omitted
  cells are strictly below the inclusive S/N 50 retention threshold. It emits
  160 records that are byte-identical to `ExhaustiveRetentionLedger`.
- The OFF reference evaluates 288 selected cells, proves 3,648 omitted cells
  are below threshold and emits 128 byte-identical records.
- Recomputed retained-OFF matching covers all three frozen branches: 96 exact
  same-hypothesis vetoes, 32 local-track vetoes and 32 unmatched records.
- Recomputed inclusive global rank-p evidence covers 154 values below the
  scientific ceiling, three exactly equal to it and three above it. Equality
  remains scientifically eligible.
- Dense/local retention, OFF and rank products are bound to the pinned phase-1
  receipt and independently reproduced from their complete synthetic inputs.

## Known-answer identities

| Artifact | SHA-256 |
|---|---|
| Phase-2 ON retention product | `f0ed4bf233173bb4d783b40281776c83c3300443596183b4449268674a8a2915` |
| Phase-2 OFF retention product | `2361c65ec692c6f32316283e599856ee55e9c76331f613c3319298adad52dbc2` |
| Retained-OFF result | `1127508775f50ab653c64d8bcaf22321125591709e972c42088eacb9a4405c02` |
| Global rank-p result | `6a63edfbac0bf41df01f49afa0f64d5555ea83b8ad103204dba06dfb9b0fa286` |
| Phase-2 receipt | `1d70d05ac7b7888cf8071bcbe894bd67bae24fba87636c6c17945b982cf0ca09` |

## Verification

| Check | Result |
|---|---|
| Targeted phase-1, phase-2, retention and rank-p suite | 72 passed, 0 skipped, 0 failed |
| Full repository suite | 256 run, 255 passed, 1 expected benchmark skip, 0 failed |
| Omitted cell exactly at inclusive threshold | Rejected |
| Local score bit/value mutation | Rejected |
| Rehashed claim expansion | Rejected |
| Rehashed dense/local OFF or rank divergence | Rejected |
| Dense-oracle cap expansion | Rejected |
| HD 156668 spectral files contacted | No |
| Spectral dataset values read | No |

## Claim boundary and remaining blockers

The dense oracle makes this a reference proof for one synthetic fixture, not
a production sparse-retention algorithm. The M37 feasibility status therefore
remains `mandatory-full-replay-benchmark-not-yet-passed`, and the production
wrapper still hard-fails.

The next completeness increment must extend the reference through
single-adjacent-OFF evidence, receiver-frame alias dependencies and connected
components. Production receipt ancestry and the complete resource envelope
then remain mandatory before the feasibility gate can change. The streaming
stages must also be integrated into the restartable runner, and the final
runtime must be pinned before a preregistration can be frozen.

The machine-readable checkpoint is
`results_m37_v0p6_sparse_retention/progress.json`.

## Subsequent checkpoint

The later phase-3 physical-reference checkpoint now closes the synthetic
single-adjacent-OFF and receiver-alias dependency gates identified above. It
does not alter this phase-2 receipt or its production-blocked claim boundary.
See `MILESTONE_37_DETECTOR_V0P6_PHYSICAL_REFERENCE_CHECKPOINT.md`.
