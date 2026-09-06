# M43P — combined detector component controls

Martin requested fewer, larger steps after M43O. Combine the outstanding
mask/scramble wiring and sparse paired-OFF transfer checks in one run. Reuse
M43J/L/N/O results instead of repeating the full 1,701-template score census.
This is a component qualification, not a full search or renewed calibration.

## Concrete implementation gap

The inherited adjacent-OFF gather requires an M37 native cache and a strictly
injective {1,2} channel mapping. M43F already demonstrated that the new bank
needs {0,1,2} mappings. M43I supplies these for contiguous intervals but has
no sparse score-index entry point. Add `adjacent_m43p.gather_score_indices`,
which reuses unchanged M43I source/cache validation, preserves arbitrary query
order and duplicates, and applies native filtering before gathering. Its
separate paired-OFF decision retains the exact same q/template/width and the
inclusive 5.5 floor on active epochs only. No mask or neighborhood is applied.
Do not relabel this adapter as an M37 cache or bypass M37 attestation checks.
Connecting it to the final retention/evidence pipeline remains separate work.

## Frozen scope

- Six existing M43H/M sources at m37_1412p5; no downloads. The unchanged
  source loader verifies native and normalized row receipts.
- All eight widths, all 1,701 templates at nine frozen score-index queries
  per source. Seven queries are shared: end, start, middle twice, near each
  edge, and middle+1. Two source-specific queries are the first duplicate
  pair inside the score grid for that source's minimum factor. These are
  selected from geometry alone, before any new spectral evaluation.
- Compare sparse outputs against independently summed native windows. For
  OFF, compare all four subset decisions at the seven shared query indices
  against a scalar inclusive-floor reference; duplicated queries stay duplicated.
- Replay full support for ancestor batches 0 and 53: templates 0–31 and
  1696–1700, exactly 37. Require full-batch M43J/L/N score hashes and source/
  cache identities before accepting the arrays. Compare their sparse cells
  to their full replay. This is deterministic anchor sampling, not a claim
  to cover all template-dependent masks.
- For each of those 37 templates, separately for ON and OFF, combine all
  widths using the unchanged isolated-epoch mask. Compare to an independent
  per-epoch Boolean reference and prefix-count dilation. Build masks on the
  full support grid; crop to the score grid only after clipped dilation.
- Compare every masked sum/active>=3 score for all widths and four subsets.
- Four explicitly frozen scramble rows exercise the minimum shift, opposite
  edge, half-range and unequal shifts. Rotate each epoch's mask with its
  scores on the score grid only. Compare unchanged `update_calibration`
  per-template maxima across all widths/subsets with independent modular
  indexing and reference sums. Assert observed/null cell inventories too.
  These four scrambles qualify wiring; no p-value or threshold is produced.

Run six focused new synthetic tests, all existing M43 tests, and inherited
mask/calibration, retention/OFF association, adjacent-OFF, alias, significance
and sparse physical-disposition tests as one regression gate. Their original
synthetic fixtures are retained; passing them does not attest the complete
M43 detector or a measured native injection recovery rate. The synthetic
score additions in the new tests are logic fixtures, not sensitivity trials.

## Execution and interpretation

Freeze plan, configuration, code and test evidence publicly before the new
real-data evaluation. At most seven ordinary source subprocesses and two
logic subprocesses; no AI delegation. Store disposable full anchor arrays
outside git, with hashes in durable source checkpoints. Each source/width
job seals its complete evidence; each logic job seals every template. On a
child failure stop queued jobs and running peers at the next source/template
boundary, retain failure evidence, and refuse an aggregate success. Publish
the completed package together rather than requesting per-checkpoint approvals.

Scope is one window. The original astronomical track association and physical
veto semantics are unchanged. No full-bank masked search, new threshold,
fresh native injection/recovery calibration, candidate selection or scientific
nondetection is established here. Next work should integrate the qualified
components into a bank-bound detector entry point, then freeze a combined
null and native-injection calibration. Existing geometric matching limits
and all earlier scientific denominators remain intact.
