# Validation B closed: scientific failure, exploratory fallback

All 142 frozen, once-only fresh B cases completed with intact recorded outputs and no redraw. The coordinator exited 1 and durably recorded `CLOSED_FAIL` / `FAIL_CLOSED`; no telescope pilot is admitted. The detector, generator, contract, thresholds and original nine qualification checks were unchanged after the single operational development correction.

| Check or diagnostic | Actual result | Meaning |
|---|---:|---|
| Complete and intact cases |142/142| Computational completion; independent retained-output audit is separate |
| Strong signal, all active ONs |14/14| Pass |
| Operating level, all active ONs |45/48| Overall count passes44; subgroup failures remain binding |
| Third ON only |6/8| FAIL: requires7/8 |
| Intrinsic width3 |21/24| FAIL: requires22/24 |
| Other activity, drift and width groups |All declared minima met| Does not override failed groups |
| Primary RFI truth initially localized in every ON |24/24| Pass |
| RFI cadences with any surviving candidate |2/24| FAIL: requires zero |
| Noise cadences with any surviving candidate |0/32| Pass within these synthetic realizations; no sky false-alarm calibration |
| Single-row transient diagnostics |12/12 survive| Complete diagnostic, not a qualification recovery threshold |
| Near-OFF contamination diagnostics |11/12 all-active before OFF;0/12 after| Complete; OFF rejection also removes true ON signals |

Operating019/021/045 lose a required originating ON before the frozen threshold 10: retained ON maxima9.683702761,9.792757617 and9.859521556. Two losses in the third-ON-only subgroup do not establish a general causal last-visit bias. The selected committed-case interpretation and hashes are in `pilot_method_study_20261008/METHOD_STUDY_MOTIVATING_EVIDENCE.md/.json`.

RFI002/003 correctly reject all truth-localized primary-track hits, but leave13/1 other first-ON carriers. Those carriers have broad width 33 responses at displaced drift paths; their complete compatible OFF searches remain below 8. A broad-box drift alias interpretation is an inference from the saved geometry, not a proven universal mechanism. The predeclared zero-any-survivor requirement still fails.

Whole-panel accounting conservatively charges 11676.036546 CPU seconds, taking the maximum retained child meters and maximum controller snapshots. This leaves 12019.932131981004 seconds under the 43200-second period cap after prior charges and the unchanged 1200-second preparation planning reservation. The original 19,500-second B allocation is not treated as actual expenditure. Historical missing measurements remain identified; the planning reservation is not described as measured work.

The approved immediate fallback is a 64-cell descriptive method study: ideal input levels 10/12/16/24, drifts−4/−1.25/+1.25/+4 Hz/s, widths 1/3, and third-ON-only versus all-three-ON activity, with balanced deterministic frequency placement and fresh disjoint seeds. Allocate at most 6000 CPU seconds in rolling 250-second whole-child partitions while preserving at least 2000 for report/reproduction. Complete B independent integrity review, publish and verify all fixed prerequisites and the actual post-B ledger, then admit the study before its first draw.

This is exploratory evidence selected after failed validation; it cannot repair A/B or qualify a sky pilot. No second correction, new qualification panel, exposure of old112+128 holdouts, or new telescope value acquisition is authorized. Source metadata remains qualified, but its 305133821-byte spectrum payload and codec compatibility with those values remain unopened/unproved. The plan continues 7–20 October; it is not finished early.

Original closure evidence: `results/radio_pilot_val_b_20261008/{outcomes.json,summary.json,resource_receipt.json,rolling_cpu_ledger.json,COMMITTED_PANEL.json}`. New resource binding: `pilot_method_study_20261008/post_b_ledger.json`. All original case maps, truth, raw hits, OFF dispositions, logs, claims and failures are preserved by the deterministic B archival package.
