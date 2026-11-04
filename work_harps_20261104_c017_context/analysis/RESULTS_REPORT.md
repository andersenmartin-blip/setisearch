# C017 / HD114783 at 3868.175 air Angstrom

**Complete fixed context: seven existing observations, one February5 discovery, eighteen profiles and thirty-six comparisons. V2E2-0118 remains U.**

All six other epochs have higher raw Pearson correlation and lower normalized RMS in the barycentric frame, in both the original core and surrounding spectrum. The central rounded, multi-sample peak and neighboring structure recur with retained amplitude differences. These descriptive comparisons do not identify a physical line or origin, establish a laser candidate or calibrate significance, sensitivity or a survey null.

The original center is3868.175 Å, original core[3867.925,3868.425] Å and broad window[3865.175,3871.175] Å. The fixed601-point grid has51core and550surrounding centers. Own discovery ADP.2022-02-06T01:07:28.382 was observed2022-02-05T07:45:49.762; BERV26.6810328154809km/s fixes topocentric anchor3867.830769460069 Å. No epoch was recentered, and no center, width, lag, stellar velocity, drift, continuum, background or mask was fitted.

## All six nonself epoch comparisons

Each cell is **barycentric / topocentric**. The six rows use one fixed reference and six other observations; the total cohort is seven observations. Four identical-product self-comparison records are separately labelled and supply no recurrence evidence.

| Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2022-01-21 | 0.988183 / 0.478916 | 0.992139 / 0.690452 | 0.112047 / 0.698153 | 0.101311 / 0.638031 |
| 2022-05-05 | 0.990463 / 0.326021 | 0.989693 / 0.080587 | 0.113239 / 0.811416 | 0.119197 / 1.061189 |
| 2023-01-16 | 0.988997 / 0.346733 | 0.991901 / 0.628297 | 0.101927 / 0.776435 | 0.102674 / 0.698091 |
| 2023-03-22 | 0.991023 / -0.446533 | 0.991934 / 0.032505 | 0.102752 / 1.107617 | 0.118496 / 1.082691 |
| 2023-05-15 | 0.987308 / -0.271934 | 0.989412 / 0.061240 | 0.121048 / 1.216456 | 0.119492 / 1.044161 |
| 2023-07-01 | 0.984106 / 0.066595 | 0.987934 / -0.165652 | 0.166841 / 1.083407 | 0.143207 / 1.145356 |

[All seven epochs, original core](results/figures/MERGED_CORE_CONTEXT.png) · [Full surrounding spectrum](results/figures/MERGED_BROAD_CONTEXT.png)

The broad view retains many recurring peaks and troughs, rather than reducing the spectrum to an isolated central emission line. Native raw and flank-scaled curves retain their original signs. Same-quantity merged y limits match across frames.

## Both native covering orders and partial support

The new header-only scan considered all72 native orders and selected orders2 and3 at the exact own discovery center. Order2 ends about+2.1765 Å from the fixed center: it covers518 of601 grid points, including all51core points and467surrounding points. It has163 finite negative-flank and77finite positive-flank source points. Although the full positive-flank wavelength interval is absent, both finite counts exceed the unchanged20-per-side requirement, and467 common surrounding points exceed the unchanged440 gate. Its valid positive normalization does **not** mean full wavelength coverage.

Order3 and all fourteen merged frame profiles have601finite raw/scaled grid values. All eighteen profiles have usable positive references; none is raw-only, blocked or marked low-reference. All36 Pearson and36 normalized RMS values are evaluable. Order2 contains five preserved nonpositive original window samples in each frame (the same source values reused); no sign clipping occurs. Native ERR is unavailable and no profile has positive finite ERR support. False low-reference flags and first-difference proxies are not formal SNR or general quality certificates.

| Native order | Frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS | Surrounding common points |
|---:|---|---:|---:|---:|---:|---:|
| 2 | barycentric | 0.942144 | 0.846154 | 0.506411 | 0.564762 | 467 |
| 2 | topocentric | 0.942117 | 0.846233 | 0.506421 | 0.564655 | 467 |
| 3 | barycentric | 0.998613 | 0.984482 | 0.054872 | 0.158976 | 550 |
| 3 | topocentric | 0.998614 | 0.984471 | 0.054870 | 0.159028 | 550 |

[Both native orders](results/figures/NATIVE_ORDERS_1.png)

Order2 has visibly weaker extraction agreement and a different scaled shape; order3 tracks the same-exposure merged structure more closely. Native divisors are63.717245 for order2 and227.462486 for order3, versus244.846443ADU in the discovery merged spectrum. Native BUNIT is absent, so native units remain unspecified; these are not physical flux ratios. Same-exposure extraction agreement supplies no independent observation or origin confirmation.

## Original raw containers and mapping history

| Order | Original global | Original local | Original baseline | Later reference support |
|---:|---|---|---|---|
| 2 | true | false | false | true |
| 3 | true | true | true | true |

[Both complete original raw/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain every stored pixel at separate full scales. Both show central vertical/trace-associated enhancements with surrounding variations; order3 also retains a bright right-edge structure. These original stored excess arrays were not newly subtracted. No new crop, contrast variant, registration, detector statistic or model was introduced. Later support leaves original order2 local/baseline failures unchanged. Original primary/secondary/adopted U/U/U remains separate from numerical profile quality and physical origin.

## Fixed topocentric geometry and reused evidence

| Observation | Predicted coherent center offset (Å) | Within fixed±0.25core |
|---|---:|---|
| 2022-01-21 | -0.038413529 | yes |
| 2022-02-05 | +0.000000000 | yes |
| 2022-05-05 | +0.512265046 | no |
| 2023-01-16 | -0.042931271 | yes |
| 2023-03-22 | +0.227247373 | yes |
| 2023-05-15 | +0.566153469 | no |
| 2023-07-01 | +0.719279224 | no |

Four predicted centers remain within the fixed February-reference core and three lie outside. These are metadata predictions under a coherence assumption, not fitted centers or proof of full finite-feature coverage. Fixed topocentric comparisons may sample neighboring structure; they are descriptive rather than calibrated origin tests.

C017 directly reuses the same seven January2022–July2023 HD114783 observing products as completed C018/C019/C021/C022. It overlaps C018 source spectral pixels over[3866.33375,3871.175] Å, width4.8412500000004 Å. The disjoint central cores lie in each other surrounding context; neither intersects the other fixed reference flanks. This core was already exposed in C018. No blind, untouched or independent-data validation and no new observing time is claimed. C019/C021/C022 bounded windows are disjoint but share observing lineage. Other-target numerical wavelength overlaps share no observations or source pixels.

## Exact method freeze, arithmetic and delivery

The method, input custody, source-only review,94synthetic checks and1,449 separate scalar checks over73,016synthetic values were public before current observed array access. Exact public readback covered23files at commit`d3cadc9d3a4d63287231bc6785b9fc1880ee7fe5`.

The separate scalar reconstruction passes **469 checks / 71,603 scalar comparisons**, reconstructing all9bounded source windows,18profiles,36comparisons and both byte-exact historical raw containers. Source signed flux,ERR and indices agree exactly. Maximum native wavelength difference is4.547e-13 Å, raw interpolation difference2.027e-09native units, normalized difference3.181e-11 and comparison difference5.847e-13. Arithmetic agrees within fixed tolerances; floating-point wavelength/interpolation values are not asserted bitwise identical.

All four PNGs were visually inspected and fully decoded. The numerical files and44source bindings remained unchanged. Separate formulas and fresh processes were executed by the same assistant; no separate-agent or human review is claimed.

[Fixed plan](PLAN.json) · [Released method](ROOT_RELEASE.json) · [Numerical audit](../independent_audit/NUMERICAL_AUDIT.json) · [All profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json)

## Next original-queue route

**C023/R024, V2E2-0122 on HD114783 at5944.965 Å**, original queue row41, was selected before C017 values. It precedes C020row53. The own February5 discovery and same seven existing epochs are explicit in [the next metadata handoff](../scientific_review/NEXT_GROUP_METADATA.json). Freshly scan its own72native headers and preserve its own raw/mapping/review history; do not transfer C017 order scope or quality. Freeze that separate analysis before its observed values. Completed mapping, normalization and profile routes are not repeated merely because physical U remains. Rubin remains limited feasibility with minimum50unmet.
