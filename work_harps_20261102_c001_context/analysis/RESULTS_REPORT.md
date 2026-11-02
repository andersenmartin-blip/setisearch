# C001: HD103991 joint spectral context

The six existing cohort spectra show different frame behavior in the central core and its surroundings. Between the two discovery exposures, core correlation is higher in the topocentric frame, while the surrounding pattern correlates better in the barycentric frame. This contrast is descriptive and reference-dependent; it does not establish an origin. **V2E2-0001 and V2E2-0016 remain U**, together in the same overlapping group.

The released run completed on **2026-11-02 at 14:06:17 UTC**: all 20 profile slots and 64 comparison slots were retained, with no blocked source profiles. Four native order 3 profiles are raw-only because their left normalization flank is outside the order. Scope is all six HD103991 spectra in the original extension02 cohort, not an archive-wide sample. No original epoch pipeline was rerun.

## Fixed comparison

Both discoveries use the same barycentric air-wavelength center, **3852.3925 Å**, and the same topocentric anchor, **3852.17509132224 Å**, derived from the first discovery’s recorded BERV. The display spans ±3 Å on a 0.01 Å grid. The core contains 53 grid centers from −0.26 to +0.26 Å, within the fixed nominal ±0.265 Å union; the surrounding region contains the other 548 centers.

Signed flux is retained. Each profile is separately divided by the positive pooled native-sample median in the fixed 1.5–3 Å flanks only when both sides have at least 20 finite samples. These flanks contain spectral structure and are not established quiet continuum. No background, width, center, lag or velocity was fitted. B and T below mean barycentric and topocentric. Correlations are unshifted raw Pearson values; normalized RMS compares shapes after each profile’s own flank scaling.

## Both discovery references retained

Reference **0001** is the 2023-02-22 observation, ADP.2023-02-23T01:01:36.783; **0016** is the 2023-02-28 observation, ADP.2023-03-01T01:01:30.551. Observation dates differ from product-ID dates. Identical-product self-pairs are explicit; the two cross-discovery directions duplicate one relationship.

| Observation (UTC) | Reference | Core r B | Core r T | Surroundings r B | Surroundings r T |
|---|---|---:|---:|---:|---:|
| 2023-02-22 | 0001 (self) | 1.000 | 1.000 | 1.000 | 1.000 |
| 2023-02-22 | 0016 | 0.492 | 0.795 | 0.937 | 0.844 |
| 2023-02-23 | 0001 | 0.867 | 0.916 | 0.933 | 0.934 |
| 2023-02-23 | 0016 | 0.608 | 0.833 | 0.923 | 0.867 |
| 2023-02-26 | 0001 | 0.607 | 0.867 | 0.937 | 0.881 |
| 2023-02-26 | 0016 | 0.904 | 0.885 | 0.939 | 0.918 |
| 2023-02-27 | 0001 | 0.505 | 0.742 | 0.909 | 0.864 |
| 2023-02-27 | 0016 | 0.840 | 0.838 | 0.915 | 0.910 |
| 2023-02-28 | 0001 | 0.492 | 0.795 | 0.937 | 0.844 |
| 2023-02-28 | 0016 (self) | 1.000 | 1.000 | 1.000 | 1.000 |
| 2023-03-01 | 0001 | 0.180 | 0.774 | 0.919 | 0.799 |
| 2023-03-01 | 0016 | 0.868 | 0.915 | 0.934 | 0.911 |

The discovery-to-discovery contrast is core **r = 0.492 B / 0.795 T**, versus surroundings **0.937 B / 0.844 T**. Corresponding normalized RMS values are **0.713 / 0.572** in the core and **0.220 / 0.341** in the surroundings. The core crest appears more tightly aligned in the topocentric plot, but its height and nearby structure vary. Core correlation is not uniformly higher there: the February 26 and 27 spectra correlate slightly better barycentrically against reference 0016. Surrounding-pattern correlation is generally higher barycentrically; February 23 against 0001 is a small exception (0.933 B / 0.934 T). Both references and all epochs remain in the comparison.

All merged profiles have complete 601-point coverage and usable positive flank references (about 74–124 ADU); their descriptive first-difference noise proxies are about 14–18 ADU. Their low-reference flags are false. This supports displaying the signed and flank-scaled morphology, not treating the flank median as a fitted continuum.

- [Full ±3 Å merged context](results/figures/MERGED_BROAD_CONTEXT.png): six epochs, signed ADU and separate flank scaling, matched scales across frames.
- [Fixed core context](results/figures/MERGED_CORE_CONTEXT.png): the same profiles and colors, with no refit or resampling for the close-up.

## Same-exposure native orders

These comparisons pair each native order with its own exposure’s merged spectrum. They are not independent observations or physical flux-ratio measurements. Merged FLUX is explicitly ADU; native e2ds BUNIT is absent, so native flux units remain unspecified.

| Discovery | Order | Core r B / T | Surroundings r B / T | Core normalized RMS B / T | Surroundings normalized RMS B / T |
|---|---:|---:|---:|---:|---:|
| 0001 | 2 | 0.990 / 0.990 | 0.986 / 0.986 | 0.136 / 0.136 | 0.108 / 0.107 |
| 0001 | 3 | 0.181 / 0.181 | blocked / blocked | blocked / blocked | blocked / blocked |
| 0016 | 2 | 0.989 / 0.992 | 0.985 / 0.985 | 0.106 / 0.096 | 0.104 / 0.102 |
| 0016 | 3 | 0.199 / 0.225 | blocked / blocked | blocked / blocked | blocked / blocked |

Order 2 has full coverage and valid normalization in both discoveries and frames. Its core shape closely agrees with the merged product (r = 0.989–0.992), with surrounding correlation about 0.985–0.986. The merged product and native extraction share the same exposure and extraction lineage; this agreement is internal consistency rather than an independent repetition.

Order 3 has **zero left-flank samples**, while its right flank has 124 finite native samples. Its common core still contains all 53 grid points, allowing the descriptive raw correlations shown above. Broad coverage is only **338/548 points** for 0001 and **341 B / 338 T** for 0016, below the fixed 439-point gate. Thus broad raw correlation is blocked, and every order 3 normalized RMS is blocked. The reason for normalization failure here is **missing coverage**, distinct from the earlier small-window low/nonpositive-continuum finding.

Its retained signed values also have limited contrast: right-flank median versus first-difference noise proxy is **11.70 / 13.11** for 0001, and **16.91 / 14.55 B; 17.14 / 14.73 T** for 0016, in unspecified native units. Nonpositive samples make up **23.60%** of the 0001 window and **18.21% B / 18.32% T** for 0016. The native curves are visibly jagged and lack a clean matching central crest. Core r = 0.181–0.225 must be read with these noise and coverage limits; it is not independent corroboration.

- [All native order profiles](results/figures/ALL_NATIVE_ORDERS.png): both orders, both discoveries and both frames; missing normalization remains visibly raw-only.
- [All preserved raw-order contexts](results/figures/PRESERVED_RAW_ORDER_CONTEXT.png): four original cutouts and their historical stored excess maps, copied exactly. Order 2 shows a trace-column enhancement; order 3 appears mottled at its separate lower-contrast scale. Panel scales are independent. No new registration, subtraction or detector-space statistic was applied.

## Verification and limits

The [independent numerical audit](../independent_audit/NUMERICAL_AUDIT.json) passed **504 checks across 76,086 scalar values**, reconstructing all 20 profiles and 64 comparisons without importing production functions. Maximum comparison difference was 4.27×10⁻¹³; signed interpolated-flux difference was 2.95×10⁻⁹. All 39 frozen source hashes and four preserved raw files were verified. [Bounded pre-interpolation inputs](results/BOUNDED_INPUT_INDEX.json), including wavelength, signed flux, available ERR and original indices, permit reproduction without restoring every full FITS file. Full profile and pair metrics are in [PROFILE_METRICS.json](results/PROFILE_METRICS.json) and [COMPARISONS.json](results/COMPARISONS.json).

All 20 measured profiles have **zero finite positive ERR samples**. The noise proxy supplies no formal uncertainty or significance. The recorded BERV span is only **3.193 km/s**, about **1.225 nominal resolution elements**; no stellar-RV or instrumental-drift correction was fitted. Two correlated discovery records, selected after detection, do not become independent evidence through multiple frames, orders or references. No origin, linewidth classification, calibrated false-alarm rate or completeness claim follows from this comparison.

The method was published before execution at commit `c7e53d0180887618817923cfb1bec4b5b300ad53`. [PLAN.json](PLAN.json), [ROOT_RELEASE.json](ROOT_RELEASE.json), [SUMMARY.json](results/SUMMARY.json) and [OUTPUT_HASHES.json](results/OUTPUT_HASHES.json) bind the calculation. All four frozen-script figures were visually inspected, including full saved-image title and legend margins; no layout amendment was needed. [PLOT_INDEX.json](results/PLOT_INDEX.json) records their hashes and confirms unchanged numerical outputs.
