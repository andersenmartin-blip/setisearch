# Closed method-study report helper

`build_method_report.py` and `method_figures.py` are inert preparation. No
plotting, signals, detector, numeric pipeline imports, retained numeric maps,
source reads, or network requests are performed while preparing these files.
The helper never changes scientific definitions, admissions, protocol records,
claims, either failed validation gate, or the telescope-value restriction.

After all 64 method outcomes durably close and independent output audit passes,
root may invoke:

```bash
python pilot_method_study_20261008/build_method_report.py \
  --method-output results/radio_pilot_method_study_20261008 \
  --b-output results/radio_pilot_val_b_20261008 \
  --audit pilot_protocol_20261008/review/COMPLETE_METHOD_STUDY_OUTPUT_REVIEW.json \
  --output results/radio_pilot_method_report_20261008
```

The output must be new and separate from both retained panel directories. The
first three arguments have those exact project-absolute defaults, so only
`--output` is required. No execution is authorized by this preparation.

## Required closed metadata

Only JSON metadata is read. The method output's `COMMITTED_PANEL.json` must
have `COMPLETE_EXPLORATORY_METHOD_STUDY_ONLY`, `panel: METHOD_STUDY`, counts
64/64, `all_children_reaped: true`, `cpu_budget_passed: true`,
`no_retry_or_redraw: true`, `scientific_gate: EXPLORATORY_METHOD_STUDY_ONLY`,
and `qualification: false`. The original B marker must have `CLOSED_FAIL`,
`panel: VAL_B`, counts142/142, all children reaped, and no retry/redraw.

Both marker checks and a successful independent audit precede even hashing or
reading outcomes. The independent audit schema, agreed with CI, is:

| Field | Required value |
|---|---|
| `status` | `PASS_INDEPENDENT_METHOD_STUDY_OUTPUT_AUDIT` |
| `panel` | `METHOD_STUDY` |
| `independent_audit`, `complete` | true |
| `case_count_expected`, `case_count_observed` | 64 each |
| `qualification` | false |
| `sha256` | Actual complete file digests for all ten inputs listed below |

The `sha256` keys are `method_cases`, `method_outcomes`, `method_summary`,
`method_resource_receipt`, `method_completion`, `b_cases`, `b_outcomes`,
`b_summary`, `b_resource_receipt`, and `b_completion`. Panel markers must
also bind their exact aggregate outcome/summary/resource digests. The helper
checks the frozen METHOD64/B case-bank digests, exact distinct identities,
the complete 4 x 4 x 2 x 2 method grid, all64 integrity-valid outcomes, and
recomputes descriptive method total/group counts before importing matplotlib.
An incomplete or failed method audit refuses figure creation rather than
treating missing cells as measured nonrecovery.

## Planned deliverables

Six figure pairs have vector PDF and 300-dpi PNG outputs. Four show discrete
recovery counts versus nominal input level or injected drift, with final
all-active and final any-active responses in separate figures. Four panels per
figure separate third-ON-only/all-three-ON activity and intrinsic widths1/3.
Each marker is a count out of four distinct cells at the opposite factor's
four values, with activity/width fixed. There are no connected curves,
smoothing, error bars, calibrated probabilities, confidence bounds, or FAP.
Two exact binary response figures retain all64 cells at n=1 each, without
interpolation. Every figure explains nominal ideal input score, independent
activity draws, and the difference between all-active and any-active recovery.

The Markdown report includes the figures, all32 strength/drift aggregate rows,
both final-response totals, all marginal factor counts with their16/32 valid
denominators, retained originating-ON loss-stage counts, and
complete B RFI/noise/diagnostic tables plus strong/operating context and all
original B checks. B counts use integrity-valid denominators; any invalid
attempts remain separate. Noise has no active-ON recovery truth and is labeled
accordingly. Neither retained noise/RFI counts nor the method responses are
interpreted as calibrated sky false-alarm or recovery probabilities.

CSV outputs retain all64 cells, all32 aggregate rows, closed B family counts,
all marginal group counts, and originating-ON stage counts. JSON retains exact
data, original closed method and B
summary/checks, independent audit, input/source SHA256 provenance, figure
metadata, and code hashes. Originating-ON loss labels and robust-score maxima
are copied from the original audited method outcomes; no search or classification
is run to derive them. A report resource receipt and artifact manifest are saved.

Execution remains deferred until root closes all64 outputs, CI completes the
independent audit, and root runs the helper. Root publishes all commits.
