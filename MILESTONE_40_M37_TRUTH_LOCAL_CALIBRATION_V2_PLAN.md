# Milestone 40 v2 coverage-repaired conditional truth-local calibration plan

Status: **PRE-EXECUTION FREEZE — POST-V1-ABORT; NO V2 INJECTION EXECUTED**.

## Purpose and lineage

M40 v2 is a separately labelled corrective execution after the immutable v1
native-coverage abort. It retains all 512 continuous motion truths, every
spectral width and activity subset, and all 12 exact ideal single-epoch S/N
levels. The M39-qualified truth-local adapter, exact source products,
randomized-background construction, two-pass mask, threshold, output endpoint,
and claim boundary remain unchanged.

V2 changes only the allocation of proxy carrier indices. No v1 score receipt
is adopted, copied, or included in the v2 aggregate.

## Metadata-only carrier repair

For each of the 512 base truths, the preflight intersects the exact native
coverage allowed by every integration in every active epoch, including the
truth's spectral half-width. The common intersection across all truths is the
inclusive proxy-index interval:

| Boundary | Value |
|---|---:|
| First safe proxy index | 78,748 |
| Last safe proxy index | 611,204 |
| Safe index count | 532,457 |
| First rest frequency | 1411.6632883092693 MHz |
| Last rest frequency | 1413.173069117445 MHz |

The original master seed and coprime carrier step are applied inside that
common interval:

```text
index(ordinal) = 78,748
  + ((372,120,260,827 mod 532,457) + ordinal * 104,729) mod 532,457
```

The step and interval size have greatest common divisor one, so the 512
assigned indices are unique. The complete repaired inventory is then checked
again with the injection implementation's exact rounded-center comparison.
The selection reads factor and frequency geometry metadata only; it does not
inspect background values or any v1 score.

## Frozen inventory and execution

The repaired plan contains exactly 6,144 trials in level-major, then
truth-ordinal order. Each trial uses a newly derived truth identity, trial
identity, and deterministic noise selection under the repaired allocation
contract. Execution remains restartable through immutable canonical JSON
receipts and deterministic modulo shards. Filter caches remain ephemeral, one
epoch and width at a time.

The aggregate is forbidden unless exactly one valid receipt exists for every
repaired trial and no extra receipt is present. Missing, duplicate, expanded,
over-capacity, identity-mismatched, or coverage-invalid state stops without an
estimate.

## Permitted result

V2 may report only the 12 pointwise conditional truth-local score-recovery
fractions and predeclared Wilson 95% intervals. It may not interpolate between
levels or claim calibrated physical-veto survival, replay of the global
false-positive field, end-to-end detector completeness, sensitivity transport,
an occurrence-rate constraint, or a technosignature.

This correction is explicitly post-v1 contact. The v1 start, 156 partial
receipts, coverage audit, and abort evidence remain separate immutable
history.
