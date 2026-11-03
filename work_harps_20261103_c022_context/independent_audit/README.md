# Independent C022 joint arithmetic verification

C022 contains three **HD114783** records and fixed discovery references:

| Record | Discovery product | Catalog barycentric center (Å) |
| --- | --- | ---: |
| V2E2-0117 | ADP.2022-01-22T01:09:14.958 | 4312.245 |
| V2E2-0127 | ADP.2022-05-06T01:04:00.123 | 4312.245 |
| V2E2-0131 | ADP.2023-01-17T01:07:48.581 | 4312.237499999999 |

The fixed common center is the midpoint of the exact minimum and maximum catalog centers, **4312.241249999999 Å**. V2E2-0117, the first original-queue discovery observed on **21 January 2022**, anchors the common topocentric coordinate with BERV **29.658729150824 km/s**, giving **4311.814678415948 Å**. The same seven HD114783 products span January 2022–July 2023 and **59.073251754930496 km/s** in BERV. The three reference identities remain explicit alongside the four cohort nonreferences.

The common ±0.25 Å core is **4311.991249999999–4312.491249999999 Å**. Its relevant edges differ from the original member cores by about **0.00375 Å**. Every exact member center, original core boundary and discovery marker remains separate. The common comparison mask is not widened, and no center, shift, width, continuum or background is fitted.

This context directly reuses C021 spectral evidence. The barycentric ±3 Å windows overlap over **4309.241249999999–4312.82625 Å**, a width of **3.585000000000946 Å**, on the same observing products and native extraction lineage. The whole C022 common core lies inside C021's positive reference flank; the whole C021 common core lies inside C022's negative reference flank. Central C022 evidence was already exposed in the earlier context. Structured reference flanks retain these features without masks or a line-free claim.

| Interval relationship | Barycentric bounds (Å) |
| --- | --- |
| C021 positive reference flank containing C022 core | 4311.32625–4312.82625 |
| C022 common core | 4311.991249999999–4312.491249999999 |
| C022 negative reference flank containing C021 core | 4309.241249999999–4310.741249999999 |
| C021 common core | 4309.57625–4310.07625 |

`independent_math.py` implements scalar binary-search interpolation, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 common-core points and 550 surrounding points, with exact minimum common support of 41 and 440. Fixed flanks lie 1.5–3 Å from the frame center and require at least 20 finite samples each. Missing coverage, insufficient finite support, nonpositive pooled references and low positive references remain distinct outcomes.

`audit_prospective.py` checks all three reference identities, the exact seven-epoch cohort, midpoint/anchor rules, original member coordinates/markers, source bindings, unchanged numerical estimators and all **216 native header rows**. It independently checks cubic monotonicity and covering-order selection using each member's original coordinate and own BERV. Analytic flux on every selected native polynomial checks common-frame geometry without observed flux. Other fixtures exercise gaps, nonfinite values, zero variance, support boundaries and signed-reference edge cases, including a positive pooled median with a negative individual flank and a negative available flank with missing opposite coverage. Only this synthetic harness imports production functions as test subjects.

Fresh native headers select **order 19 for all three discovery products**. All six native frame contexts geometrically cover the complete common core, window and both flanks. Geometry does not establish finite flux, positive references or comparison quality. For every member, original global support is **true**, original local usability and baseline verification are **false**, and later five-window support is **true**, without changed registration. Later support does not repair the original false stages.

Two batch03 members have original primary/secondary/adopted **U/U/U**. Older **V2E2-0131** retains original primary **I**, original secondary **M** normalized to **I**, and adopted baseline **I**. Completed wider support and separate later visual reviews at unchanged coordinates retain **U/U/current U**. Original baseline panel containers are preserved rather than substituted with distinct later wider containers. These original stages remain distinct from other candidates' histories and do not assign a physical origin.

Every merged epoch is compared with **all three fixed references**, in both frames and regions: **84 merged rows**. Each of the three native contexts is compared only with its own same-exposure merged product, adding **12 rows**. Totals are **20 profiles, 96 comparisons, ten bounded input windows, three original raw copies and twelve labelled identical-product self comparisons**.

For any one frame and region, three references each compare with six other epochs. The **18 directed nonself rows** represent **15 unordered observation pairs**, including **three reciprocal reference pairs**, on seven observing epochs. Rows and pairs are dependent; neither count represents independent detections or additional observing time. All directed source/reference identities remain explicit.

After explicit root public release and a completed run with a stable numerical ledger, `audit_actual.py --authorized-after-root-run` independently reconstructs every bounded input, profile and pair. It verifies source/output hashes, three original raw byte identities, reference/reciprocal accounting, original mapping/history stages and exact prospectively frozen audit sources. It also intersects the exact source-index bounds with the frozen C021 bounded-input index for each of the seven merged and three native source windows, documenting reused spectral samples without rerunning C021 or opening its saved arrays. It imports no production functions. Partial, raw-only, negative-reference, low-positive-reference and support failures remain explicit if measured. Reports are one-shot outputs; failures are retained rather than replaced by adjusted analysis.

Original C022 epoch/profile/raw evidence and the completed wider 0131 mapping diagnosis already exist. Direct C021 pixel reuse and reciprocal reference-flank exposure make this dependent post-detection work. No equality or independence of complete historical raw crops is inferred. Numeric overlaps on other targets share no observing products or source pixels. The audit adds no blind validation, independent observations, calibrated uncertainty, qualified survey null, origin assignments, diagnostic replay or classification changes.
