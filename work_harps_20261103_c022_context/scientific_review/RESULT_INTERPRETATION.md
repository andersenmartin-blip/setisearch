# C022: three-reference dependent spectral context on HD114783

All three fixed discovery references favor barycentric raw Pearson and normalized RMS against every one of their six other epochs, in both the common core and surrounding window. This supports a recurrent barycentric spectral pattern in seven existing observations. Per frame/region, 18 directed nonself records represent 15 unordered pairs plus three reciprocal duplicates; they are dependent comparisons, not added observations or calibrated physical-origin evidence. All three current C022 labels remain U, with original and later stages kept separate.

The single frozen execution completed at 21:16:53 UTC on 3 November 2026 after exact public method readback at commit `d1ad1e0e8aa6e29c20236929ffb78cbdb0e4667c` and root release. It retained 20 profiles, 96 comparisons, 12 identical-product self rows, ten bounded source windows and three byte-exact original raw copies. No profile is raw-only, blocked or excluded. All 96 Pearson and 96 RMS values are evaluable. The 43 numerical ledger files include 33 NPZs totaling 384,410 bytes. No method, earlier output, original stage or classification was changed.

## Every fixed reference and both frames

All 18 dependent directed nonself records per frame/region are included; medians and ranges are descriptive.

| Region / frame | Pearson min | Pearson median | Pearson max | RMS min | RMS median | RMS max |
|---|---:|---:|---:|---:|---:|---:|
| Common core / barycentric | 0.997392 | 0.998190 | 0.998969 | 0.021174 | 0.027803 | 0.033810 |
| Common core / topocentric | -0.667257 | 0.079693 | 0.989918 | 0.064004 | 0.597288 | 0.843402 |
| Surroundings / barycentric | 0.998705 | 0.999129 | 0.999359 | 0.024106 | 0.028677 | 0.033975 |
| Surroundings / topocentric | -0.047713 | 0.223315 | 0.995462 | 0.063780 | 0.796342 | 0.957523 |

Each reference retains six other epochs. February 5 2022 and March 22, May 15 and July 1 2023 remain measured non-reference cohort epochs. Separate median correlations preserve all three identities; the complete six-row families and RMS values are in [the report](../analysis/RESULTS_REPORT.md).

| Discovery reference | Core B median r | Core T median r | Surrounding B median r | Surrounding T median r |
|---|---:|---:|---:|---:|
| 0117 / 2022-01-21 | 0.998019 | 0.094269 | 0.999177 | 0.268225 |
| 0127 / 2022-05-05 | 0.998035 | 0.106367 | 0.999066 | 0.175580 |
| 0131 / 2023-01-16 | 0.998242 | 0.049953 | 0.999187 | 0.278842 |

The seven barycentric curves retain a rounded multi-sample central crest, a negative-side bump and trough, a positive-side depression and neighboring rise. The broader context has repeated peaks/troughs and substantial high positive-side structure. Unscaled flux levels differ while the flank-scaled barycentric profiles align closely with small remaining shape and height differences. Both fixed reference flanks contain spectral structure; no epoch subset, fitted continuum, mask or moved boundary was selected.

Topocentric agreement remains strong for the close-BERV January 21 2022 versus January 16 2023 pair: core r 0.989918/RMS 0.064004 and surrounding r 0.995462/RMS 0.063780. Barycentric agreement remains better for that pair and every other directed row. In this fixed sample the barycentric minima exceed the topocentric maxima in both correlation regions. That descriptive separation does not establish an origin threshold, significance or a qualified candidate. Four common-center predictions leave the fixed topocentric core, where neighboring structure can enter; no measured peak center, lag, linewidth, stellar velocity or physical model is fitted.

## Actual finite, signed and reference quality

All 20 profiles have 601 finite raw and normalized grid values, valid positive pooled two-flank references and false low-reference flags. Every original window and flank sample is positive. Gap and outside-coverage masks are zero, and no profile has positive finite ERR support. These actual results remain separate from prospective header coverage and failed original raw-mapping stages.

Every merged window contains 600 original finite samples and 150 in each flank. Native order-19 windows contain 512–515 original samples, with 126–127 left and 130–131 right flank samples. These source counts are distinct from the 601 interpolated grid centers. The pooled signed medians retain all flank structure and are descriptive spectral levels, not demonstrated line-free continua. A positive reference and false low flag supply no formal uncertainty, general quality certificate or calibrated SNR. No clipping, sign change, alternative flank or new mask was introduced.

Same-exposure native comparisons retain all three identities and both frames. Each core comparison uses 51 common samples and each surrounding comparison 550; every displayed value is rounded separately.

| Event / order 19 | Core B r | Core T r | Core B RMS | Core T RMS | Surrounding B r | Surrounding T r | Surrounding B RMS | Surrounding T RMS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0117 | 0.999928 | 0.999928 | 0.013499 | 0.013503 | 0.999336 | 0.999338 | 0.039036 | 0.038986 |
| 0127 | 0.999959 | 0.999975 | 0.018058 | 0.011363 | 0.998810 | 0.999360 | 0.052685 | 0.037374 |
| 0131 | 0.999958 | 0.999966 | 0.037698 | 0.037834 | 0.999324 | 0.999302 | 0.065480 | 0.065662 |

The native page shows close same-exposure multi-peak agreement, with small remaining scaled differences, including the January 2023 surroundings. For that source, surrounding RMS is 0.065480/0.065662 despite raw r 0.999324/0.999302. Its native pooled levels are 4256.796875/4258.820801, compared with merged 3528.156250 in both frames, in their respective extracted-unit conventions. Positive scalar division preserves raw Pearson; reference levels affect heights and normalized RMS. Native BUNIT is absent and extracted units remain unspecified; merged ADU is uncalibrated. Shared exposure/extraction cannot supply independent observing confirmation, registration proof, a physical flux ratio or origin validation.

## Exact original geometry, failed gates and three raw panels

Original centers are 4312.245 Å for 0117/0127 and 4312.237499999999 Å for 0131. Their exact extrema midpoint is 4312.241249999999 Å, with fixed common core [4311.991249999999,4312.491249999999] and context [4309.241249999999,4315.241249999999]. The 0.01 Å grid and 41/440 support gates are unchanged. Common edges differ from individual original edges by up to 0.00375 Å, so the metric core is not their complete union or a measured linewidth. All original cores and markers remain separate within the broad context without expansion or recentering.

First-queue January 21 2022 BERV 29.658729150824 km/s fixes this wavelength's common topocentric anchor 4311.814678415948 Å. The same seven observations span 59.073251754930496 km/s. Frozen common-center offsets are inside for January 21 zero, February 5 +0.042823399 and January 16 2023 −0.005036379 Å, and outside on the positive side for May 5 2022 +0.613896441, March 22 +0.296158757, May 15 +0.673971252 and July 1 +0.844675834 Å. Seven center predictions therefore have three inside/four outside. The three original event markers instead have two inside/one outside: only May 5 at +0.617646604 Å is outside. Each marker uses its own catalog center/discovery BERV. Predictions and markers are metadata, not fitted peaks or complete finite-width feature coverage.

Fresh 216-header scans selected only order 19 in each discovery, with complete common-window/core/both-flank geometry in all six native frames. All three original local/baseline stages remain **false**, and global/later support remains **true** separately. Batch03 `baseline_mapping_verified` and original 0131 `mapping_verified` sources retain their exact original coordinates and distinct basis; later support and current finite-quality outcomes do not rewrite failed gates.

Two batch03 events retain original primary/secondary/adopted U/U/U. **0131 originally has primary I, secondary M normalized to I and adopted baseline I, then later U/U/current U** after its completed unchanged-coordinate wider diagnosis. No 0130 or 0129 history is transferred; no mapping replay or new pixel-preservation test occurred.

I inspected all four exact frozen PNGs: merged broad/core, the complete three-row native page and complete three-pair raw/excess page. Two 31×33 batch03 raw panels show a faint central extended trace/excess and much stronger alternating positive/negative right-edge bands dominating their separate full scales. The distinct 21×25 original 0131 panel shows an extended central positive patch/vertical trace with negative excess structure above it. The remote edge bands do not classify the central feature, and differing original crops/scales do not demonstrate morphology equality. Original 0131's 3,602-byte five-array panel remains distinct from its completed later wider 5,497-byte container. Every saved extent is retained, without new crops, contrast variants, smoothing, subtraction, detector statistics, background models or origin assignment.

## Direct C021 shared-pixel and structured-flank dependence

Current C022 and completed C021 reuse the same seven source observations and native lineage. Their bounded barycentric overlap is **[4309.241249999999,4312.82625] Å**, width **3.585000000000946 Å**. The entire current C022 core was already exposed within C021's fixed positive reference flank [4311.32625,4312.82625]. The entire C021 core [4309.57625,4310.07625] lies inside current C022's fixed negative reference flank [4309.241249999999,4310.741249999999]. Every structured signed sample remains under the fixed rules, without a line-free reference claim, mask or method retuning. Original queue selection and dependencies were fixed before C021 values, but this is already-exposed dependent spectral evidence.

The independent actual audit verifies **ten source-index intersections** against the bound C021 source metadata: seven merged windows share 360,365,422,361,390,428,445 source samples in cohort order; the three native windows share 306,358,306. These counts describe the union of both fixed-frame source windows plus interpolation brackets, not merely the nominal barycentric overlap interval or independent samples. Exact original input hashes and source-index lineage establish reuse without reading saved C021 arrays, rerunning C021 or claiming equality of complete historical raw crops.

C018/C019 bounded blue windows are disjoint while their observations/native lineage remain shared. C006/C007 numeric overlaps use HD106515A, with no shared observing products or spectral pixels. Original C022 epoch/raw evidence and completed 0131 mapping already existed; no observing time, blind test, archive completeness or independent validation was added. The independent reconstruction passes 698 checks over 79,403 scalar values, retaining all 20 profiles, 96 comparisons, ten source windows, three original raw copies and 12 self rows; metrics, source flux and ERR agree exactly. This validates reproduction of the descriptive method, not physical origin, a qualified laser candidate or a calibrated survey null.

## Next fixed original-queue route

The pre-value handoff remains [C017/R018](NEXT_STEP.md), original row 37, singleton **V2E2-0118**, route **INDIVIDUAL_PROFILE_CONTEXT**. Group numbers do not set queue order. Its own February 5 2022 discovery is ADP.2022-02-06T01:07:28.382, exact center 3868.175 Å/original core [3867.925,3868.425], BERV 26.6810328154809 km/s and own anchor 3867.830769460069 Å. Restore one reference and one marker across the same seven observations, with six other epochs.

Future C017 directly overlaps completed C018 over [3866.33375,3871.175] Å, width 4.8412500000004 Å on the same source spectral pixels. The disjoint cores lie in each other's broad surroundings but neither intersects the other's fixed reference flanks. Its future central spectrum has already been exposed by C018; it is not untouched or independent validation. Numeric overlaps with other targets share no pixels/products. Historical order 2 retains original local/baseline false versus order 3 all true, with global/later true for both and original U/U/U. Fresh future headers determine actual scope/partial flanks, and future runtime quality is assessed separately. No current sole-order-19 quality, C018 missing-right-flank outcome or distinct 0131 stages transfer. Completed mapping and C013/0092+C014/0104 normalization routes stay complete and are skipped. No new C017 analysis or future array query was executed here. Rubin remains at limited feasibility/minimum-50 unmet.

[The numerical ledger](../analysis/results/OUTPUT_HASHES.json) remains SHA256 `3241c6be3bb3fd51a7c6bc99da96d4b47c91ee2ae236380edd2921450eff372b`. [All comparisons](../analysis/results/COMPARISONS.json), [plot index](../analysis/results/PLOT_INDEX.json), [independent actual audit](../independent_audit/NUMERICAL_AUDIT.json), [pre-array review](PRE_ARRAY_SCIENTIFIC_REVIEW.json) and [final method review](FINAL_METHOD_REVIEW.json) retain evidence and limits.
