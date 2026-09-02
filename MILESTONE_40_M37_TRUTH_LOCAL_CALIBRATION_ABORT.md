# Milestone 40 v1 conditional truth-local calibration: technical abort

Status: **M40_V1_ABORTED_NO_CALIBRATION_CURVE — PARTIAL RECEIPTS ARE
DIAGNOSTIC ONLY**.

The frozen M40 v1 execution stopped fail-closed before producing a
calibration aggregate. Two independent modulo shards reached truth ordinals
143 and 150 and raised `V0P6CoverageError` because the continuous injected
track left the exact native 1412.5 MHz background in an active epoch. The
remaining workers were then stopped without deleting or rewriting a completed
receipt.

## Sealed partial execution

| Item | Result |
|---|---:|
| Scheduled trials | 6,144 |
| Completed immutable receipts | 156 |
| Completed S/N levels | 0 |
| Recovered scores in partial receipts | 0 |
| Missing receipts at stop | 5,988 |
| Calibration aggregate permitted | no |
| Calibration curve produced | no |

All 156 receipts belong to S/N level 4. They cannot be treated as a recovery
fraction because the frozen per-level inventory is incomplete. Their zero
recovery count is recorded only to bind the partial ledger; it is not a
scientific result and is not adopted by the corrective execution.

## Metadata-only coverage audit

After the stop, the diagnostic evaluated all 512 truth tracks against the
three exact ON geometries and factor rows. It opened no spectral payload and
executed no injection. For every active integration it applied the same
native-center rounding and width guard as the injection implementation.

The audit found 496 covered truths and 16 uncovered truths:

`143, 150, 193, 207, 214, 293, 307, 371, 386, 407, 435, 450, 464, 471, 486, 499`.

Because each truth occurs at all 12 S/N levels, 192 of the 6,144 v1 trials are
structurally non-injectable in the selected background. The carrier margin in
the inherited prospective allocation guarded the proxy score grid, but it did
not prove the continuous `q * F` tracks against every active native scan and
spectral half-width.

## Immutable evidence and interpretation

- v1 start certificate SHA-256:
  `17c578e3bcc09565c76adee509607f2bd82c663c56015e5c5cdde91170e9d1a9`;
- abort evidence SHA-256:
  `bb73e7c9144f5da4ea4c1d99e7c4ef635306a2d1cd31bc2356cba61b5d9720ed`;
- native coverage audit SHA-256:
  `3ab0cfe3371ffbc7b5931bd9545ddfcb36486e1fd691bddb9ba2f6c1e211ec1c`;
- partial record inventory SHA-256:
  `85dab886367fc9bc5b8ee5ebdd3245852c37444fd9b1a1eed64e213a4638f88b`.

This is a preflight failure discovered during execution, not evidence for or
against score recovery, detector completeness, sensitivity, an occurrence
rate, or a technosignature. V1 is immutable and cannot be repaired by silently
dropping 16 truths or aggregating the 496 covered cases.

Continuation requires a separately frozen protocol and output root. The
coverage-repaired v2 plan reallocates all 512 carrier indices from metadata
alone and adopts none of the 156 v1 score receipts.

