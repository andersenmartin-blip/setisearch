# Independent C021 joint arithmetic verification

C021 contains five **HD114783** records and fixed discovery references:

| Record | Discovery product | Catalog barycentric center (Å) |
| --- | --- | ---: |
| V2E2-0116 | ADP.2022-01-22T01:09:14.958 | 4309.827499999999 |
| V2E2-0121 | ADP.2022-02-06T01:07:28.382 | 4309.827499999999 |
| V2E2-0126 | ADP.2022-05-06T01:04:00.123 | 4309.825 |
| V2E2-0130 | ADP.2023-01-17T01:07:48.581 | 4309.825 |
| V2E2-0139 | ADP.2023-07-02T01:01:43.311 | 4309.827499999999 |

The fixed common center is the midpoint of the exact minimum and maximum catalog centers, **4309.82625 Å**. The first original-queue discovery, V2E2-0116 observed on **21 January 2022**, anchors the common topocentric coordinate with BERV **29.658729150824 km/s**, giving **4309.39991731037 Å**. The exact seven HD114783 products span January 2022–July 2023 and **59.073251754930496 km/s** in BERV. This group's July reference replaces the preceding C019 group's May 2023 reference; equal reference counts do not make the identities interchangeable.

The common core remains ±0.25 Å about the fixed midpoint, **4309.57625–4310.07625 Å**. Its relevant edges differ from the original member cores by about **0.00125 Å**. Every exact member center, original core boundary and discovery marker remains separate. The comparison mask is not widened, and no center, shift, width, continuum or background is fitted.

`independent_math.py` implements scalar binary-search interpolation, a signed pooled-flank median, first-difference MAD, common-support Pearson correlation and normalized RMS. It imports no production code. The 601-point grid has 51 common-core points and 550 surrounding points, with exact minimum common support of 41 and 440. Fixed flanks lie 1.5–3 Å from the frame center and require at least 20 finite samples each. Missing coverage, insufficient finite support, nonpositive pooled references and low positive references retain distinct outcomes.

`audit_prospective.py` checks all five reference identities, the exact seven-epoch cohort, common anchor and midpoint rules, original member coordinates/markers, source bindings, unchanged estimators and all **360 native header rows**. Cubic monotonicity and covering-order selection are independently checked using each member's original coordinate and own BERV. Analytic flux on every selected native polynomial tests common-frame geometry without observed flux. Other fixtures exercise gaps, nonfinite values, zero variance, support boundaries and signed-reference edge cases, including positive pooled reference with a negative individual flank and negative available flux with missing opposite coverage. Only this synthetic harness imports production functions as test subjects.

Fresh native headers select **order 19 for every discovery product**. All ten native frame contexts geometrically cover the complete common core, window and both flanks. This does not establish finite flux, positive references or comparison quality. Historical mapping flags remain distinct:

| Record | Global grid | Original local | Original baseline | Later support |
| --- | --- | --- | --- | --- |
| V2E2-0116 | true | false | false | true |
| V2E2-0121 | true | true | true | true |
| V2E2-0126 | true | false | false | true |
| V2E2-0130 | true | false | false | true |
| V2E2-0139 | true | true | true | true |

Registration remains unchanged. Later support does not retroactively repair the original false stages. Four batch03 members have original primary/secondary/adopted **U/U/U**. Older **V2E2-0130** instead retains original primary **I**, original secondary **M** normalized to **I**, and adopted baseline **I**. Completed wider reference support and separate later reviews at unchanged coordinates retain **U/U/current U**. Original baseline panel containers are preserved rather than substituted with distinct later wider containers. C019/0129's unknown later fields and all-U original history are not transferred. These stages do not assign a physical origin.

Every merged epoch is compared with **all five fixed references**, in both frames and regions: **140 merged rows**. Each of the five native contexts is compared only with its own same-exposure merged product, adding **20 rows**. Totals are **24 profiles, 160 comparisons, 12 bounded input windows, five original raw copies and twenty labelled identical-product self comparisons**.

For any one frame and region, five references each compare with six other epochs. The **30 directed nonself rows** represent **20 unordered observation pairs**, including **ten reciprocal reference pairs**, on seven observing epochs. Neither rows nor pairs are independent detections or additional observing time. All directed source/reference identities and per-reference accounting remain explicit.

After explicit root public release and a completed run with a stable numerical ledger, `audit_actual.py --authorized-after-root-run` independently reconstructs every bounded input, profile and pair. It verifies source/output hashes, five original raw byte identities, reference/reciprocal accounting, mixed original mapping/history stages and exact prospectively frozen audit sources. It imports no production functions. Partial, raw-only, negative-reference, low-positive-reference and support failures remain explicit if measured. Reports are one-shot outputs; failures are retained rather than replaced by adjusted analysis.

C021 reuses seven observing products and some identical native products at a disjoint newly bounded spectral window from C018/C019. No independence of complete historical raw cutouts is inferred. Numeric overlaps with older C006/C007 use another target and share no observing products or source pixels. Original C021 epoch/profile/raw evidence and the completed wider 0130 mapping diagnosis already exist. This audit verifies arithmetic and lineage without adding blind validation, independent observations, calibrated uncertainty, a qualified survey null, origin assignments, mapping/normalization replay or classification changes.
