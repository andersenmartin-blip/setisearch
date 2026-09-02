# Milestone 39 M37 truth-local qualification result

Status: **COMPLETE — REAL-DATA ANCHORS PASSED; FROZEN CALIBRATION
AUTHORIZED**.

## Result

Milestone 39 completed the gated engineering qualification selected by M38.
The six frozen 1412.5 MHz source products were rehydrated under explicit read
authorization, and all 48 required width-specific cache entries were built.
Deep verification passed for both source and cache inventories.

The three predeclared real-data anchors were then injected under explicit
anchor authorization. Each truth-local adapter result was compared with an
exhaustive operational replay over the complete M37 1412.5 MHz window. All
three anchors passed every required comparison.

| Anchor | Truth-local candidate cells | Result |
|---|---:|---|
| Low S/N, upper carrier, width 1, epochs 0–1 | 0 | Passed |
| Mid S/N, lower carrier, width 129, epochs 0–2 | 2 | Passed |
| High S/N, interior carrier, width 129, all epochs | 11 | Passed |

The comparison covers exact float32 best-score bits, best template, spectral
width, activity subset and proxy carrier, two-pass mask candidate bits,
candidate score-cell count, and the complete local-score inventory. The
zero-cell anchor is a deliberate fail-closed boundary case and reproduced the
exhaustive zero result.

## Gate status

| Gate | Status |
|---|---|
| Compact factor ancestry | Passed |
| Adapter source and output schema freeze | Passed |
| Six source products deeply verified | Passed (6 / 6) |
| Width-specific caches deeply verified | Passed (48 / 48) |
| Restartable real-anchor runner | Passed |
| Exhaustive real-M37 anchor equivalence | Passed (3 / 3) |
| Frozen 6,144 calibration trials authorized | Yes |
| Frozen 6,144 calibration trials executed | No (0 / 6,144) |

## Runtime ancestry refresh

The transient execution workspace was lost after the initial checkpoint, so
the source products, caches, and compact factor bundle were reconstructed from
their immutable upstream inputs. This refresh changed runtime/source-metadata
container identities. It did not change the scientific factor table or the
analysis contract: their SHA-256 identities remain
`a4d87d8813ec63ff7f3392f5073038f3dc47a9707796a745dd4e752588255fa4`
and
`726571e7b56b684f06ff69bbd6ae70b4c191268d25db8eadfcb8b6e841dc9f2e`.
The rebuilt bundle and every downstream receipt are separately hash-pinned in
the published result.

The complete local regression suite ran 332 tests with no failures and one
expected exact-grid benchmark skip.

## Reproducible certificate

The deterministic qualification record is
`results_m39_m37_truth_local_qualification/qualification.json`. Compact
rehydration, aggregate, and per-anchor receipts are published alongside it;
large spectral and cache payloads are intentionally excluded from Git.

| Item | SHA-256 |
|---|---|
| Qualification certificate | `68da73b539b02210ebd3923b61bace3d07158ea7fce434602be44aff98acaaa5` |
| Configuration | `5c5fbdbff5b096a9ebbfb6f7e3bb6edcfe0880987f64ea4157a1e4a96d7681e9` |
| Input inventory | `0a005a05f195a6ef49c2282b909a69907cf02e5cddb12439c7e0f246193a40dd` |
| Source/cache completion | `e99da4c94f85cbebf5146b19aeea63fcfd73f68adbc5be55a183365055c39b47` |
| Anchor aggregate | `504291fce04d9665c024e5de27f09b400ee0667c4e2934e6d3cc1dba39ef1fb2` |

## Claim boundary and next stage

Anchor success is evidence for these three predeclared comparisons, not a
global equivalence proof. The anchor runner executed three engineering
injections, but the 6,144 calibration injections remain unexecuted. M39 does
not report a recovery fraction, completeness, sensitivity, physical-veto
survival, global false-positive calibration, occurrence rate, or
technosignature claim.

The next stage is the explicitly authorized, restartable execution of the
frozen 6,144-trial conditional truth-local calibration. No trial may be
silently removed, truncated, or promoted into an end-to-end completeness
claim.
