# LS4L: measured diagnostics behind the preserved Stage-1 veto

LS4K supports an additional diagnostic path but not automatic scientific
acceptance. LS4L therefore evaluates the 64 previously selected, OFF-vetoed
LS4J injection fragments in the real archived A1/B1 HTR backgrounds. It is a
new, separately frozen review study. LS4J's conditional rule remains intact:
LS4J did not perform this review, and its result is not relabelled.

## Exact selection and original decisions

Use the hash-pinned complete LS4J Stage-1 ledger: 36 medium injection cases,
18 with associations, 64 associated fragments, all vetoed by the original
Stage-1 OFF rule. Preserve each actual detected event's time and frequency
extent and every original OFF evidence record. No fragments are merged,
newly selected or promoted. The twelve original uninjected Stage-1 baseline
records have no associated events; do not treat those empty records as
measurements of the selected-event HTR background.

Cross the same four independent HTR digital levels 0/4/8/16 with the 36
medium cases, giving 144 labelled configurations and **256 selected-fragment
HTR evaluations**. For each selected fragment, level zero is its own
uninjected HTR comparison at the same detected band/window. Compare a positive
review pass with that same fragment's zero-level truth-associated result.
This conditions on the already injected medium selection; it is not a
zero-injection complete-pipeline false-alarm calibration.

## Unchanged measured-data processing

Reuse LS4I's exact HTR extractor/evaluator: actual detected windows, 0.5 MHz
frequency padding, corrected channel-center inclusion, and the original
LS4E residual detrending, thresholds, pulse association and both control
vetoes. The original digital interventions, fractional time-bin integrals,
reference MAD scales and channel dilution remain unchanged. A review pass
requires at least three of the same injected pulses at two supporting scales
and survival of the HTR OFF/reference vetoes. Keep the Stage-1 rejection
attached. The original joint pass remains false for every configuration.

Also reproduce all 48 fixed-truth-window LS4I diagnostics within its frozen
rtol 1e-10/atol 1e-8 tolerances. These are a replay control, never a replacement
for the selected-event result. Retain all outcomes, including empty selections,
unsupported pulses and vetoed diagnostics. Do not relax or retune settings.

The ten unique extraction bands include both truth bands and the selected
padded fragment bands. Download only the two existing A1/B1 HTR sources,
18,870,174,378 bytes total, and verify complete frozen SHA256 identities and
headers before numerical use. Keep one raw file at a time in a unique `/tmp`
directory outside the synchronized workspace, with 4 GB extra disk headroom.
At most two full attempts per source are allowed, charging up to
37,740,348,756 bytes. Preserve receipts and attempt errors; delete raw and
partial files on completion or failure. Publish only derived decision records,
not scan arrays or collapsed time series. No reserved A3/C1/D1 data are read.

## Freeze, validation and reporting

Before spectral access, test handoff geometry, complete grid accounting,
preserved Stage-1 vetoes, same-window zero comparisons and resource inventory.
Freeze and publish the plan/configuration/implementation/tests with dependency
identities. A partial run is incomplete and cannot overwrite retained evidence.

Report the 256 fragment-level evaluations, configuration-level any-fragment
review passes, same-fragment changes from zero level, HTR support and each
veto separately by band, width and amplitude. Report original joint passes
and promoted sky candidates separately, both remaining zero. Distinguish
reused configurations from independent observations, and keep medium and HTR
amplitude units separate. No physical transfer calibration, completeness,
false-alarm probability, source-origin identification or new sky candidate
follows from a successful digital review.
