# LS8J — reconciled chronological CHEOPS cohort selection

Completed 20 September 2026. **PASS**, with the original evidence gap preserved.

The public run at `81692343a774b19d26c28dd9596ad1dd1a31ef01` selected
WASP-189 from a bounded census of the first 1,000 public CHEOPS archive rows.
It retained 452 eligible visits and 107 cohorts with at least two eligible
visits. This is a bounded chronological sample, not a census of the entire
current CHEOPS archive or a selection by SETI plausibility.

The independently implemented saved-census audit passes 17,000 field and
decision checks and reproduces every cohort ranking. Each of the 452 eligible
visits has a distinct archive visit ID. The selected pair remains:

| Order | Exact file key | Exposure count | Individual exposure | Stacked exposure |
|---|---|---:|---:|---:|
| 1 | CH_PR100041_TG000201_V0300 | 7 | 4.80000019073486 s | 33.6000022888184 s |
| 2 | CH_PR100041_TG000202_V0300 | 7 | 4.80000019073486 s | 33.6000022888184 s |

The original producer retained derived product summaries rather than the full
browser responses promised by its protocol. Those original responses remain
unrecovered. No original file or claim of historical completeness is rewritten.

The separately frozen reconciliation at
`c46eadf99fa37c7a15e073f36fb668fe5561662e` acquired complete, newly dated
product-browser responses for exactly the same 452 file keys. **All 452
summaries match**, with zero disagreements, and the complete 107-cohort order
is unchanged. The fresh responses, query keys, timestamps and hashes are
retained under `products/`; the audit and complete decision ledger are in
`saved_selection_audit.json` and `reconciliation.json`.

The result was published at
`f50fae88ba4f52b2d288a13feaaef2e8a069be29`.
Science-product bytes, FITS table rows, light-curve values, image pixels and
product-download calls are all zero. No candidate, detector qualification,
sensitivity or qualified observing coverage is added by this metadata stage.

Next: the separately frozen LS8K header preflight for the unchanged WASP-189
pair, followed only after compatible headers are public by an exact-range
DEFAULT-L2 screen. Keep both positive and negative controls and the existing
closed-host, raw-imagette, TESS and M43 boundaries.
