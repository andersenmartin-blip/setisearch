The localized, near-trace mismatch for V2E2-0235 persists under both prespecified background estimators. It is robust to this bounded estimator choice, but its physical origin remains unresolved. **Close this follow-up with the event still U; perform no further variants in this continuation.**

Both variants used all 232 training rows and all eight held-out controls: eighteen window records and 198 row records were completed from the same 8,275 saved native pixels. No new detector pixels or observations were added, and the original result was preserved.

| Target diagnostic | Original two-sided median | Negative-side median | Positive-side median |
|---|---:|---:|---:|
| Residual L1, ADU | 8,633.12 | 8,817.70 | 8,922.85 |
| Residual L1 outside ±3 pixels | 15.70% | 16.24% | 19.21% |
| Largest pixel / residual L1 | 6.52% | 6.43% | 6.29% |
| Mean absolute residual inside ±3 pixels, ADU/pixel | 110.27 | 111.90 | 109.23 |
| Median estimated background, ADU | 198 | 190 | 211 |

For the negative-side variant, control residual L1 ranges from 2,068–4,108 ADU and maximum-pixel share from 2.07–2.93%. For the positive-side variant, the respective ranges are 3,179–4,890 ADU and 1.88–2.37%. The target exceeds every control on both metrics in both variants. Conversely, its off-band share remains **below every control**: control ranges are 29.38–35.18% and 34.64–56.08%, respectively. The result continues to describe concentrated mismatch mainly inside the declared trace band, not dominant remote off-trace support.

The background choice changes details without removing the mismatch. In particular, the positive-side pooled template has nine negative grid samples after signed background subtraction, whereas the negative-side template has none. The target's positive-residual sum changes from 2,809 to 3,493 ADU. These differences demonstrate estimator dependence and reinforce that fitted templates and residual sums are not physical photon or charge fractions. Neither background is selected as preferred.

This test does not identify fiber-B light, a charge deposit, a photon/charge mixture or another physical cause. Three-pixel background medians are not calibrated noise models; eight controls from one exposure/order are neither independent replication nor a false-alarm distribution. Trace-profile variation and interpolation remain limitations. A robust model discrepancy is the bounded conclusion.

Archive the original adjudication, temporal comparisons, spatial result and both sensitivity outcomes together under unchanged **U**. The concrete next handoff remains C001/R001, HD103991, as already frozen in `NEXT_STEP.md`; no additional 0235 background, template, aperture, registration or May-epoch search follows from these results.

Reviewed saved outputs from method commit `2cb8e31a3764c25a01af7a95c1ee4126ed264d2a`, completed 2026-11-02 at 12:54:15 UTC. Source hashes:

- `background_sensitivity/results/SUMMARY.json`: `70829b5f28e61edc128a5348cd3798b7467961b1da02eb7ead508eef98aba487`
- `background_sensitivity/results/WINDOW_METRICS.json`: `351b7fe33803a62b1818e69d534816bca11477fd5d3ea303b807ae03c5a4ff3d`
- `background_sensitivity/results/TEMPLATES.json`: `a245577cc22271a15bb541560e3d47da97b51b5100ca6826997407fb09be78ae`
- `background_sensitivity/results/EMPIRICAL_CONTEXT.json`: `2c585d060725ea1ea4c5415f8c3038f8727d5c6c521973131f5aa57c0fb3840b`

This scientific reading made no requests, changed no labels and did not alter the frozen next step, contract or original interpretation.
