# M43 support-contract qualification: first checkpoint

M42 reproduced a 98/512 geometric support ceiling. This stage tests whether
an implementation repair can change that outcome while preserving the frozen
meaning of a candidate. It does not assume an implementation bug exists.

## Contract

For a candidate there must be ONE bank template and ONE carrier grid cell
whose track differs from the truth by at most 20 Hz at EVERY integration of
ALL three ON epochs. The same template and carrier apply throughout. This is
the existing M39/M41 rule, including inactive epochs of pairwise injections.
Having a different fitting template or carrier at each integration is not
sufficient. A nonempty continuous interval without a carrier grid point is
also not sufficient. Spectral width and signal amplitude do not enter this
geometric rule. Subsequent masking and score thresholds are separate stages.

## Fixed checks

1. Reassemble all 6,144 M41 ledger records and reproduce the published M42
   diagnostic byte for byte using the unchanged M42 validator.
2. Use small, explicit synthetic fixtures: aligned tracks; incompatible
   carrier intervals; different templates fitting different epochs; an
   inactive-epoch mismatch; a continuous intersection between grid points;
   and exact inclusive-distance boundaries.
3. Compare the bounded interval planner with both the existing materialized
   planner and a separate exhaustive Boolean support calculation. Record
   per-template/per-integration support, continuous intervals and joint cells.
4. Require exact plan records and candidate indices for the legacy planners.
5. Run the complete repository suite and report its actual result. Failures
   must be distinguished from a demonstrated support-rule error.

This is a retrospective engineering diagnosis. The fixture inventory is fixed
in source before its first execution. No telescope data or injections are
needed to test these logical boundaries. The synthetic inactive-epoch example
may illustrate a DIFFERENT support definition; it is not adopted as a repair.

## Decision and next gate

If a mismatch is demonstrated, preserve its fixture and implement an isolated
correction. If the planners agree, do not manufacture a bug fix by broadening
tolerance, dropping inactive epochs, changing the bank, or changing quantifiers.
Record the semantics boundary and keep production unchanged. A future endpoint
redesign must separately specify association across activity, width, template
and carrier, then pass exhaustive real-data anchors before calibration.

Existing M39 anchor receipts are historical evidence only. They do not count
as a new real-data replay or validate a future changed endpoint. M43's full
repair/real-data qualification remains open if this first stage finds no
contract-preserving repair to validate.
