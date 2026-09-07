# M43V baseline identity amendment

The initial public execution freeze `277e3315d2c5250cbbb58852b334b5896636c353`
reproduced all three calibration certificates and native anchors, then stopped
at the first baseline audit equality check. No selected two-component or
component-only input was evaluated.

M43U resets the overlay with `overlay.trial([])` but passes the original
`baseline` ScoreStore to the baseline execution. M43V instead passed the empty
overlay's returned ScoreStore, whose provenance differs. The one-line amendment
passes `baseline` exactly as M43U does. The exact audit equality remains required;
no mask, score, threshold, association, veto, selected input or denominator changes.

The initial log is preserved in
`results_m43v_component_diagnostic/initial_baseline_identity_failure.log`.
The amended script and pin inventory are published before any component input.
The successful run must still reproduce all three baseline and 30 historical
endpoint audits exactly. Previously qualified unchanged numerical tests are reused.
