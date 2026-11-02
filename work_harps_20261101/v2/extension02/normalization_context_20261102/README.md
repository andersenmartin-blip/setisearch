# HD114386 normalization context — two unresolved records

**The weak-continuum flags belong to a later reference exposure, not either discovery profile.** Both V2E2-0092 and V2E2-0104 retain their original **U** classifications. The flag marks lower unnormalized flux relative to a descriptive noise proxy. Division by a small positive normalization amplifies displayed amplitudes and noise together; **it does not by itself increase or change Pearson correlation**.

This study follows exactly the two `NORMALIZATION_CONTEXT` records in the [existing action queue](../unresolved_context_20261102/ACTION_QUEUE.csv). [The protocol](PLAN.json) and [code/input freeze](FREEZE.json) precede profile/FITS array reads. It uses **28 preserved profiles** (two events × seven epochs × two frames), focuses on **eight discovery-or-flagged profiles in three exposures**, and inspects **all 12 corresponding native-order/raw contexts**. No exposure, candidate, origin label or observing time was added. The completed 4,370-profile epoch pipeline was not rerun.

## Why the low flag occurs

Both events' flagged profiles come from archive exposure `ADP.2023-08-29T01:02:07.487`, actually observed **2023-08-27 at 23:33:30 UTC**. Each has one low reference epoch in both frames. Neither discovery has the merged-profile low flag. Archive product timestamps differ from observation dates; figures use `DATE-OBS`.

The table shows the **barycentric** windows. Both frames remain in the exact output tables.

| Record / observation | Median merged flux (ADU) | Difference noise proxy (ADU) | Median / noise | Existing low flag |
|---|---:|---:|---:|---|
| V2E2-0092 discovery, 2022-01-06 | 96.490 | 18.841 | 5.121 | No |
| V2E2-0092 reference, 2023-08-27 | 42.478 | 16.124 | 2.634 | Yes |
| V2E2-0104 discovery, 2023-07-01 | 84.096 | 17.934 | 4.689 | No |
| V2E2-0104 reference, 2023-08-27 | 31.648 | 18.409 | 1.719 | Yes |

The original rule is median ≤ three times the noise proxy. All 28 normalizers are **positive**; there is no zero-division or invalid-normalization failure. The later medians fall to about **44% and 38%** of their respective discovery values while absolute difference-noise proxies remain similar. Both later windows therefore have much larger relative noise. The ±2 Å windows also contain more nonpositive extracted samples: **21/400** and **29/400** in the later barycentric windows, versus **2/400** and **3/400** at discovery.

These are uncalibrated **ADU**, not physical photon flux. The median is a local normalization scale over a structured ±2 Å spectrum, not an independently measured line-free physical continuum. The noise estimate is `1.4826 × MAD(adjacent flux differences) / sqrt(2)`; it is not a calibrated error or line-detection significance. Spectral structure, resampling and correlated pixels can affect it. All focused pipeline `ERR` arrays lack finite positive uncertainties. This diagnosis establishes why the numerical flag fires; it does not establish why the telescope/pipeline recorded lower blue flux on that date.

[Epoch normalization figure](figures/EPOCH_NORMALIZATION.png) · [all 28 profile diagnostics](PROFILE_DIAGNOSTICS.csv) · [all eight merged-window checks](MERGED_WINDOW_DIAGNOSTICS.csv).

## Native orders and raw-background context

The unnormalized native products confirm that the weak scale is present before plotting normalized profiles:

- **V2E2-0092** has one covering order, **order 1**. Its local native median drops from **94.292 ADU** at discovery to **42.582 ADU** in the later barycentric window, while the native difference-noise proxy stays near **20.97 → 20.52 ADU**.
- **V2E2-0104** has overlapping **orders 2 and 3**. Their medians drop from **50.343 / 34.252 ADU** to **21.727 / 13.016 ADU**. Noise proxies remain approximately **15.09 / 14.53 → 15.63 / 14.74 ADU**. The later barycentric windows contain **57/412** and **68/343** nonpositive extracted samples.
- V2E2-0104's discovery merged-profile flag is false, but its separate order 3 already has median/noise about **2.36**. A merged-spectrum flag does not certify that every overlapping order has strong continuum. Order amplitudes and merged amplitudes have different extraction/scaling and must not be equated.

Raw source counts and side backgrounds are retained independently of native extracted flux. For V2E2-0104, the fixed central median raw excess is **12.75 / 7.50 ADU** in discovery orders 2/3 and **−0.50 / 1.25 ADU** in the later barycentric context. These small residuals sit on raw count levels around **250–270 ADU**. They describe weak contrast under the specified side subtraction; they are not calibrated sky-subtracted photon rates.

The raw context uses the **previously recorded global orientation** and the unchanged header trace polynomial, without fitting a new local mapping gate. In V2E2-0092's later barycentric panel, the stronger visible trace is displaced roughly **four columns** from the predicted crosshair. That discrepancy is preserved explicitly: these new windows are **not independently mapping-certified**, and their cutout statistics must not be used as a precise on-trace photometric measurement or origin decision. It does not affect the independently extracted native and merged spectra or the algebraic normalization result. Any subsequent detector-image interpretation needs a separately specified local registration investigation.

[0092 profiles](figures/V2E2-0092_FOCUSED_PROFILES.png) · [0104 profiles](figures/V2E2-0104_FOCUSED_PROFILES.png) · [all native-order measurements](NATIVE_ORDER_DIAGNOSTICS.csv) · [raw pages 1](figures/RAW_CONTEXT_01.png), [2](figures/RAW_CONTEXT_02.png), [3](figures/RAW_CONTEXT_03.png).

## What correlation does and does not imply

For positive constant normalization `n`, the stored residual has the form `(f − linear_background_raw) / n`. Fitting a linear background is homogeneous under this scaling, and Pearson correlation is invariant under positive scaling of either vector. Independently reconstructed unnormalized residual correlations match the stored normalized correlations; the production diagnostic's maximum difference is **2.22 × 10⁻¹⁶**. Halving or doubling the positive divisor likewise leaves correlation unchanged. The original correlation values reproduce to **3.33 × 10⁻¹⁶**.

A large normalized peak can therefore reflect a smaller denominator, but a frame-to-frame correlation difference is **not explained by that scalar division alone**. The two frames sample different wavelength locations in other epochs, with their corresponding fitted side backgrounds. Low flux relative to noise, correlated structure, the fixed wavelength window and background choice limit how much a correlation says about a repeatable physical feature. The current data do not provide calibrated correlation significance. A low flag neither vetoes an origin nor demonstrates an artificial normalization artefact.

The frames are alternative views of the same exposure, not independent observations. The four low-profile rows are two wavelength windows in one reference exposure. The original U labels remain unchanged.

## Verification and reproducibility

[The independent audit](independent_audit/AUDIT.json) passes **496 scalar comparisons**, verifies all **nine original source products**, all **28 preserved profiles**, all **eight focused windows**, **12 native/raw contexts**, and all **20 derived arrays**. It uses independent closed-form background/correlation calculations and direct-power wavelength polynomials, without importing production analysis functions. Maximum scalar discrepancy is **2.22 × 10⁻¹⁶**; wavelength evaluation differs by at most **4.55 × 10⁻¹³ Å**. Shared NumPy/Astropy primitives are not independent physical validation. [Separate visual QA](secondary_visual/REVIEW.json) inspected all six final figures and all 12 raw contexts, including the date correction and displaced-trace caveat.

The **412,231-byte** evidence ZIP preserves **48 exact arrays: 28 original selected profiles and 20 derived merged/native/raw arrays**. SHA-256: `d72e395f96dd6f0c617eeb7b6d79ff3c674c53151b486f955eced0fa8f2d6c46`. [Member hashes](EVIDENCE_ARCHIVE.json), [one ordered binary part](EVIDENCE_PARTS.json) and [seven passing restoration checks](EVIDENCE_RESTORE_VALIDATION.json) cover deterministic packaging, fresh exact restoration, identical-file retention and refusal of changed files, symlinks and corrupt parts.

```bash
python3 restore_evidence.py --verify-only
python3 restore_evidence.py --destination /absolute/separate/normalization-evidence
```

For a fresh numerical reproduction, use a **separate copy** of this directory, restore the original nine source products using [the recorded input identities](SOURCE_PRODUCTS.json) and [input restoration instructions](INPUTS_RESTORE.md), and retain the published outputs separately. `analyze_context.py` refuses to overwrite a completed `SUMMARY.json`. `restore_profiles.py` can reconstruct the original 28-profile subset from existing epoch archive parts when needed; the small evidence package already preserves the same bytes. Audits rewrite their own reports, so run them in a separate reproduction copy.

No original catalog, current classification or prior evidence file was changed. This normalization-context item is complete for both selected IDs. Their **physical interpretation remains open**, including the later 0092 raw-window registration discrepancy. The 185 U and 35 M records remain unchanged; this diagnostic is neither a new detection nor a calibrated null result.
