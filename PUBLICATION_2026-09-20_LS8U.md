# LS8U publication record — 20 September 2026

Published under the standing authorization for SETI code, data, protocols,
reports and logs in `andersenmartin-blip/setisearch`, science branch
`m43-support-qualification`, with the current overview on main. No messages
were sent to people. Scope: one bounded residual/noise study of the two
previously retained TESS_260647166 CHEOPS contexts, with zero new archive bytes.

| Checkpoint | Immutable commit |
|---|---|
| Original LS8S L2 screen and all signed outcomes | `cc05ba9a55a98bcfe6e1c747820ec4dd3265617f` |
| Original LS8T retained images and audit | `3e0bd85cee4b191f4bbe82b499977976c1b1484a` |
| LS8T continuation authorizing this bounded next step | `7e76ab3a8d3b3e0870a7963bf921b22655e45d6f` |
| LS8U protocol, complete code, tests and workflow freeze | `4de69b42f8e0982a1964a4378c87c9ba9e6cf745` |
| LS8U complete audited result and both figures | `6cff907b742f862094131cb6ea4f5499821cba24` |

Workflow [35531218961](https://github.com/andersenmartin-blip/setisearch/actions/runs/35531218961)
concludes **success**. The independently checked scientific status is
**COMPLETE_AUDITED_DESCRIPTIVE_ONLY**; the audit is **PASS**. The result records
the exact freeze SHA, environment, complete execution logs and SHA-256 manifest.

All **18 pre-analysis tests** pass: eight inherited spatial tests and ten new
duration/cadence, leakage, known-answer, independent reconstruction, boundary
serialization and legacy-compatibility tests. The new method preserves the
validated LS8P three-row/60-second arithmetic on the corresponding synthetic
input, while using the actual 42-/49-second context cadences in LS8U. The known
NumPy-coordinate serialization fix was included before freezing; no repair,
scientific retry or changed tolerance was required after native execution.

All eight native CAL/COR × C0/C1 cases, **128 duration-matched held cases** and
**128 signed controls** are preserved. Independent struct decoding, long-double
temporal normal equations, scalar covariance propagation, independent spatial
normal equations and coordinate-set accounting pass **583,488 numerical
comparisons and 625,868 exact checks**, with zero disagreements. The largest
discrepancy is **0.0001068384 of the allowed numerical tolerance**. All 48
known-template controls, 80 compact controls and 128 additive checks pass.

The 22 manifest-listed result files comprise all four native array archives,
both per-context diagnostics, global diagnostics, independent references and
controls, injection controls, audit, summary, next action, report, both figures,
environment, execution status and four logs. All 22 were downloaded from the
immutable result commit and their SHA-256 values verified before interpretation.
Manifest SHA-256:
`5ab368a2438310413fb2bee2dafc60c99af00c6345ba22b303d43f215e62c050`.
Both six-panel figures were visually inspected; no visualization change or
scientific rerun was required during review.

The positive has COR residual/reference energy **3.765108–3.797390**, with
**1/24** held controls at least as large and **6.4683–7.0340%** of weighted
residual energy in its top ten pixels. The negative has residual/reference
energy **0.705153–0.723441**, with **6/8** held controls at least as large.
These estimated and dependent comparisons are descriptive, not calibrated
significances. The positive remains **UNRESOLVED_WITHIN_FIXED_SCOPE** and the
negative remains **SPATIALLY_STRUCTURED**. Original scores, labels and gates
are preserved; no qualified candidate, detector or observing coverage is added.

Hypothetical displacement subtraction loses **12.79–13.09%** of injected
brightness flux in the positive context and **7.31–7.84%** in the negative.
No correction or veto is adopted. The fixed study closes regardless of its
outcome. Rank-5 EC 12578-2107 remains next for its own metadata-first freeze
and unchanged L2 transfer; its science values remain unopened. Earlier closed
studies, reserved data, the NOT_READY calibration gate and unsent request are
preserved. The accompanying continuation and project updates give the exact
restart point, without creating a new approval stop.

[Immutable complete report](https://github.com/andersenmartin-blip/setisearch/blob/6cff907b742f862094131cb6ea4f5499821cba24/results_ls8u_residuals/REPORT.md) ·
[Immutable frozen protocol](https://github.com/andersenmartin-blip/setisearch/blob/4de69b42f8e0982a1964a4378c87c9ba9e6cf745/LS8U_RESIDUAL_NOISE_PROTOCOL.md) ·
[Scientific interpretation and exact next action](LS8U_CONTINUATION.md) ·
[Current project status](PROJECT_STATUS.md).
