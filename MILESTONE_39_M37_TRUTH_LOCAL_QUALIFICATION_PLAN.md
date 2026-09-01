# Milestone 39 M37 truth-local qualification plan

Status: **QUALIFICATION STARTED — SOURCE REHYDRATION AND REAL-ANCHOR
EQUIVALENCE PENDING; NO CALIBRATION RESULT**.

## Purpose

Milestone 39 implements the first gated stage selected by M38: qualify a
resource-bounded truth-local score adapter for the frozen M37
`m37_1412p5` background. It does not change the M37 detector, threshold,
truth allocation, trial allocation, candidate outcome, or Run 004/006
history.

The eventual analysis remains retrospective and retains all 512 physical
truths at all 12 exact ideal-S/N levels (6,144 trials). Its only permitted
endpoint is conditional pointwise score recovery after native-domain
injection and recomputation of the two-pass mask. Physical-veto survival and
the global false-positive field are outside this endpoint.

## Frozen adapter boundary

`src/seti_repeater/truth_local_v0p6.py` provides two bounded operations:

1. intersect positive-factor carrier intervals and verify only their bounded
   candidates with the exact binary64 track-distance expression; and
2. open one native cache width and epoch at a time, gather the required local
   mask closure, recompute the two-pass mask, and evaluate the unchanged
   float32 stack statistic.

The adapter is capped at 1,000,000 distance cells, 64 MiB of retained local
arrays, and 512 MiB of mapped cache payload. It fails closed when source
hashes, scan identities, cache ancestry, grid identity, widths, factors, or
resource limits differ. It cannot run physical disposition or report global
significance, completeness, sensitivity, or occurrence.

Synthetic tests require the interval planner to reproduce the older
materialized planner and require the local score/hypothesis to be bit-identical
to a complete dense synthetic replay. These tests are necessary but are not
real-M37 production-equivalence evidence.

## Predeclared real-M37 anchors

The anchor inventory was frozen before source rehydration or injection. It
exercises a structural zero-candidate truth, both pairwise activity choices,
the all-epoch activity choice, width 1, width 129, low/mid/high S/N, and widely
separated carrier locations.

| Anchor | Level / S/N | Truth | Width | Epochs | Planned local q cells |
|---|---:|---:|---:|---|---:|
| `no-local-cell-low-snr-upper-carrier-width-1-pair-01` | 0 / 4 | 0 | 1 | `[0,1]` | 0 |
| `mid-snr-lower-carrier-width-129-pair-02` | 5 / 10 | 15 | 129 | `[0,2]` | 2 |
| `high-snr-interior-carrier-width-129-all-epochs` | 11 / 40 | 31 | 129 | `[0,1,2]` | 11 |

For each anchor, the truth-local adapter must match an exhaustive operational
replay of the complete 1412.5 MHz window in score float32 bits, best template,
width, activity subset, carrier index, and candidate mask bits. All three must
pass. Any mismatch stops M39 before calibration. Success is evidence for these
anchors only and is not a global proof by itself.

## Execution gates

1. Hash-verify the compact Run 006 factor bundle and its basis, labels, table,
   analysis contract, and source-metadata ancestry.
2. Rehydrate and independently hash-verify all six 1412.5 MHz native source
   products and all 48 scan/width cache sidecars.
3. Complete restartable real-anchor orchestration with crash/restart receipts.
4. Execute all three exhaustive anchor comparisons and require exact success.
5. Freeze the adapter, result schema, and 6,144-entry ledger before any
   calibration trial.
6. Account for every trial exactly once and publish only pointwise conditional
   score recovery, without interpolation or downstream-survival claims.

The current checkpoint completes the compact factor gate and freezes the
adapter source, output schema, and anchor inventory. It stops at gate 2 because
the prior large spectral products and caches are no longer present locally.

## Deterministic checkpoint

The frozen configuration is
`config/m39_m37_truth_local_qualification.json`. Running
`scripts/m39_m37_truth_local_qualification.py` against a Run 006 directory
writes `qualification.json`, `INPUT_MANIFEST.sha256`, and
`RESULTS_MANIFEST.sha256`. This qualification command never opens spectral
values and executes zero injections.

