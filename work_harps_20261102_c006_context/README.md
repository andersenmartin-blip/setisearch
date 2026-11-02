# C006 / HD106515A: joint context complete, all three records unresolved

C006 covers all seven existing HD106515A epochs, three wavelength records and **two unique discovery products**. All **18 profiles and 64 comparisons** are measured. All three records remain U; no physical-origin assignment, qualified laser candidate or calibrated null follows.

The joint core has nonself barycentric Pearson r = 0.960276–0.996426; the surrounding pattern has r = 0.973347–0.997366. All profiles have full 601-point coverage and positive reference normalization, with no low-reference flags under the fixed rule. Positive finite ERR support is absent throughout.

The method and exact input identities were public in `e495c9fa6e59af1c3927a0b8a57767556eb30eff`; all 25 published files were read back before calculation. The fixed barycentric-air midpoint is 4310.455 Å, the first-discovery topocentric anchor is 4310.021714958131 Å, the full window is ±3 Å and the union core is ±0.400 Å. The BERV span is 59.609813 km/s. No center, lag, linewidth, stellar velocity or continuum was fitted.

Median raw Pearson over the six other epochs, preserving both unique references separately:

| Discovery observation (UTC) | Region | Barycentric | Topocentric |
|---|---|---:|---:|
| 2022-01-05 | core | 0.962104 | 0.292278 |
| 2022-01-05 | broad_pattern | 0.976806 | 0.027037 |
| 2022-12-31 | core | 0.994759 | 0.333513 |
| 2022-12-31 | broad_pattern | 0.996878 | 0.013124 |

For the near-BERV discovery pair, topocentric correlations are higher: core r = 0.978027 versus barycentric 0.960276, and broad r = 0.985120 versus 0.976356. There is no universal pairwise frame ranking. The first discovery reference gives lower barycentric agreement than the later reference; both remain fixed and fully reported.

The eight identical-product self-comparisons are explicitly labelled. 0042 and 0043 share the 2022-12-31 product and overlapping raw pixels, so they are not two independent observations. The joint-window metric does not separately establish the origin of its neighboring features. The two discovery BERVs are close; later fixed topocentric-core comparisons can sample neighboring structure after features leave the anchor window.

Both unique native order 19 contexts and all three event-specific raw panels are retained. 0025's original local/baseline mapping failures remain explicit alongside later global/five-window support. Same-exposure native/merged agreement does not erase that historical limitation or provide independent confirmation. 0042's separate off-trace feature remains unclassified.

Fixed flank medians are reference levels, not a proven line-free continuum. In particular C007 at 4312.700 Å lies within the positive normalization flank. Positive scalar normalization leaves Pearson unchanged but affects heights and normalized RMS. Native units are unspecified; merged ADU are uncalibrated, and the descriptive noise proxy is not a formal error model.

[Full report and four figures](analysis/RESULTS_REPORT.md) · [Scientific interpretation](scientific_review/RESULT_INTERPRETATION.md) · [All comparisons](analysis/results/COMPARISONS.csv) · [Profile quality](analysis/results/PROFILE_METRICS.csv) · [Closure](GROUP_CLOSURE.json)

[Independent numerical reconstruction](independent_audit/NUMERICAL_AUDIT.json) passes **488 checks and 71,701 scalar comparisons**, covering all nine bounded source windows, 18 profiles, 64 comparisons and three preserved raw panels. This verifies arithmetic, not physical origin or independent observing time. [Input audit](input_audit/INPUT_AUDIT.json) verifies 14 exact files from two existing archives, including all 144 native-order headers. No new acquisition was made.

[Preservation](preservation/README.md) retains 30 NPZs totaling 341,668 bytes: nine source windows, 18 profiles and three raw-panel copies. Preserve the published results and reproduce in a separate directory.

The next fixed queue item is [C007 / V2E2-0026](NEXT_ACTION.json), selected by original row 6 before C006 results. Its 4312.700 Å core is already visible inside this phase's wider window and positive reference flank; future context must acknowledge those shared pixels and observations. [Detailed handoff](scientific_review/NEXT_STEP.md).

[Current checkpoint](CONTINUATION_STATE.json) · [Project continuation](../CONTINUE_SETI.md). Original coverage remains 300 exposures, 20 stars and 70.874650833 hours, with 403 A / 46 O / 185 U / 35 M. Rubin's current route remains stopped as limited feasibility, with minimum 50 evaluable objects unmet.
