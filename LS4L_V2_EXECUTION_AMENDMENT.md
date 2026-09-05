# LS4L v2: representation-only replay correction

The frozen v1 execution verified both complete A1/B1 HTR sources, processed
all 36 Stage-1 trial handoffs, and then stopped at fixed-window replay with
`LS4I fixed-window diagnostic replay differs`. Preserve the v1 abort receipt,
source receipts, selection, code, configuration and freeze unchanged. V1
supports no complete numerical-result claim.

## Reproduced programming defect

The LS4I evaluator returns `band_indices` as a Python tuple. JSON persistence
represents those indices as a list. The imported strict `numeric_agreement`
requires an actual list when the expected value is a list, so it rejects
identical channel indices in a live tuple. V1 compared live evaluator output
with a loaded JSON ledger and therefore necessarily failed this check.
The initial result had not yet been checkpointed, and raw files had already
been deleted. Its numerical outputs cannot be recovered from the receipt.
No assertion of full numerical replay equality follows until v2 verifies it.

## Narrow correction and independent checks

V2 canonicalizes actual replay values through the existing lossless JSON
encoder/decoder before applying the **same** strict comparison and numerical
tolerances. This converts tuple containers into their persisted list form;
it does not change channel indices, numbers, event windows, pulse thresholds,
control vetoes, selection, injections or scientific endpoints. Tests reproduce
the old tuple/list failure, accept identical persisted values, and continue
to reject changed numeric values, missing fields and different index counts.

V2 additionally checkpoints the complete derived evaluator output immediately
after computation and before replay validation, so a later validation failure
does not discard its measurement ledger. The checkpoint remains explicitly
prevalidation evidence and cannot be reported as a successful run by itself.
Use separate v2 result paths and a separate freeze; never overwrite v1.

## Remaining download envelope

V1 consumed one full attempt per source: 18,870,174,378 charged bytes. V2
permits exactly one additional full attempt per source and starts its budget
accounting at that prior charge. The combined ceiling remains the original
37,740,348,756 bytes. Both sources must again pass their original full SHA256
and header checks. The original one-raw-file, disk-headroom, deletion,
reserved-data and no-array-publication rules remain unchanged.

Commit and publish this correction, test evidence and the v1 abort receipt
before repeating spectral access. This is a disclosed software execution
amendment after an aborted run, not a new preregistration or a retuned
scientific analysis. All LS4L diagnostic-versus-scientific claim boundaries
remain in effect.
