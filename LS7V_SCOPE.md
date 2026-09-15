# LS7V: reconcile CAL electronics with the actual reduction log

Prepared 15 September 2026 after inspecting the calibration messages in the
already retained 60,868-byte reduction log for OBSID 1015522. This is a
forensic source-contract reconciliation, not a new blind detector experiment.
Continue science commit `61766763abdbdef06a347ec6676bc228a4719088`.

Use only the original log with SHA-256
`28170dd5716e5cfaf0f6cfa67c2de9d6324be880a82379e08e4043f7b84bbd9a`,
its saved LS7R acquisition provenance, the already verified raw/CAL headers,
and the existing LS7S/LS7T/LS7U numerical summaries. No new astronomical product
or electronic margin is acquired or evaluated. Preserve the whole original
log losslessly for provenance, but restrict analysis to calibration messages
on lines 75–96; do not inspect source photometry, light curves or corrections.

Extract the observation ID, calibration-module version, read mode/frequency/
channel/script, stacking label, default-vs-measured electronics policy,
reported temperature and rounding, default bias/RON and units, spatial bias
frame decision, rounded gain, linearization step, dark mode/file and flat
step. Verify observation and readout identity against the saved native header.

Compare the two decimal defaults with the previously verified constant CAL/
COR numbers, including an explicit IEEE-754 binary32 representation check.
This check tests whether the recorded numbers match the logged defaults; it
does not establish the internal numeric type or complete DRP implementation.
Reuse LS7U's measurements and intervals unchanged. Do not refit a margin,
change a threshold, repeat the row census, or select a gain formula from an
approximately printed gain.

Distinguish a named input reference from an applied correction. A skipped
spatial bias frame need not be reconstructed to reproduce this recorded DRP
path. That fact alone does not establish negligible physical pixel-dependent
bias for a different estimator. The explicitly applied dark MAP remains a
required physical input; do not waive its early-visit applicability question.

Save selected log lines, the lossless original, source/provenance identities,
an executable reconciliation, its verification, findings and the revised
physical contract. Publish under the standing SETI authorization. Preserve
earlier LS7U numerical results and historical reports. No target-image bytes,
native source trials, pulse recoveries, candidates or qualified observing
seconds are added. No external message, blocked reference-bundle download or
unused TESS/M43 data access is authorized by this scope.
