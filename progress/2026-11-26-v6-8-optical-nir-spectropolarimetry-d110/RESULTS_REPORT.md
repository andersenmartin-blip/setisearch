# Phase D110 (`V6.8`) Optical & NIR Spectropolarimetric Laser SETI Results Report

**Phase ID:** `D110` (`V6.8`)  
**Detector:** `TECHNOSIGNATURE_V6_8_OPTICAL_NIR_SPECTROPOLARIMETRY_ESPADONS_NARVAL_SPIROU`  
**Stage-1 Seal (`locked_utc`):** `2026-11-26T04:43:12.420824+00:00` (`METHOD_LOCK.json` SHA-256 `1b59261081e1c2eb472975325fdbd09275c0e6b2fd99b3d9dd6a97f6d49b8eb4`, `chronology_lag = +10.650s`)  
**Survey Closure:** `32/32` campaigns (`D079–D110`), `1,012` unique stars (`760` SCIENCE, `252` CONTROL), `67` spectrographs / `97` spectral arms (adding `TBL_NARVAL`), `36` companion archives (`A–AJ`), `verified_eti_detections_total = 0`.

---

## 1. Executive Summary & Headline Outcomes

Phase `D110` (`V6.8`) executes the survey's first dedicated **high-resolution dual-beam Stokes ($I, Q, U, V$) + diagnostic Null ($N_1, N_2$) optical and near-infrared spectropolarimetric technosignature search** across **87 archival polarimetric spectra** (`28.8928 h` integration time, `1,458.597 MiB` raw FITS/PolarBase inputs, `49` targets = `41` prior bridges + `8` brand-new magnetic/exoplanet-host stars):

- **Three complementary polarimetric facilities (`87/87` valid spectra, `0` failures):**
  - `CFHT_ESPADONS_POL`: `40` optical spectra (`R = 65,000`, `11 Q`, `11 U`, `18 V`; `370–1048 nm`)
  - `TBL_NARVAL` (**67th spectrograph / 97th spectral arm**): `28` optical spectra (`R = 65,000`, `5 Q`, `4 U`, `19 V`; `370–1048 nm`)
  - `CFHT_SPIROU_POL`: `19` NIR YJHK APERO spectra (`R = 70,000`, `2 Q`, `1 U`, `16 V`; `980–2515 nm`)
- **Zero-overlap prior exclusion & Penta-Regime Closure:** `0` `dp_id` overlap across `4,349` prior archival exposures (`+ 46` format-check IDs) and `1,077` excluded sky coordinates (`min_new_sep = 850.15"` >> `600"` floor). `16CYGB` achieves **Penta-Regime Closure** with `TBL_NARVAL` (`NARVAL_39493_V`, `D079–D110`), yielding best optical `P_10m = 7.956 kW`.
- **Physics-grounded Stokes & Null Triage (`0` Verified ETI):**
  - `POL_V68`: `10,408` raw $|z_P| \ge 7$ peaks $\to$ `4,023` passing `P2` ($N_1/N_2$ null veto) $\to$ `2,834` passing `P3` (Zeeman antisymmetric S-curve veto) $\to$ `14` passing `P4` (unpolarized emission excess) $\to$ `12` pre-Stage-2 `P5` triggers $\to$ **`0` Stage-2 survivors (`verified_eti = 0`)**.
  - `POL_COMB_V68`: `13,317` polarized comb teeth across `4,857` evaluated frequency-comb spacings $\to$ `479` pre-Stage-2 qualified combs $\to$ **`0` Stage-2 survivors** (vetoed as photospheric Zeeman forests / order-boundary artifacts).
- **Paired Linear Polarization $(Q, U)$ Bounds (`16` Pairs):** Median $99\%$ Minimum Detectable Polarization **`MDP99 = 0.4072%`**, spanning `0.1222%` (`SIRIUS`, `TBL_NARVAL`) to `9.5135%` (`HD209458`, `CFHT_ESPADONS_POL`).
- **Exact C12 Planck-Anchored Polarized Radiometry (`c12_max_rel_err = 0.0`):**
  - `CFHT_ESPADONS_POL` best: `GJ729` (Stokes `V`, `POL_OPT_5320`) = **`0.0521856 kW` (`52.2 W`)**
  - `CFHT_SPIROU_POL` best: `WOLF359` (Stokes `V`, `POL_NIR_15500`) = **`0.09028018 kW` (`90.3 W`)**
  - `TBL_NARVAL` best: `HD36395` (Stokes `V`, `POL_OPT_5320`) = **`0.64020845 kW` (`640.2 W`)**

---

## 2. Calibration, Anchor Regression & Dual-Mode Reproducibility

- **Synthetic Calibration Suites (`37/37` suites >= 97.5%):** `7,873 / 7,911` trials passed (`99.52%`) in `D110`, bringing cumulative `D079–D110` calibration volume to **`96,345` trials**. New `V6.8` suites:
  - `CALIBRATION_V68_OPTICAL_POLARIMETRY_240`: `240/240 (1.0000)`
  - `CALIBRATION_V68_NIR_SPIROU_POLARIMETRY_180`: `180/180 (1.0000)`
  - `CALIBRATION_V68_POLARIZED_COMB_180`: `179/180 (0.9944)`
- **Archive `AH` Bit-Exact Regression Anchors:** `GJ317 (traj=1406, comb=329, eti=0)` and `7CMA (traj=1412, comb=292, eti=0)` match Archive `AH` bit-for-bit.
- **Compact Bounded Bundle & Dual-Mode Zero-Diff Verification:** Noise-scaled byte-shuffled `spol16l` packing produces `bounded_inputs/d110_bounded_bundle.json.gz` at **`35,602,755 B` (`33.953 MiB <= 35.0 MiB`**, SHA-256 `8b893de1798a0c5b03777cd364d02854e993dceca9cc5c7a94394c513ad4752a`). Execution via `--from-full-inputs` vs. `--from-bounded-inputs` yields **`0` byte diffs across all `57` result files** (`DUAL_MODE_ZERO_DIFF_PASS`).

---

## 3. Unified `1,012`-Star Panchromatic Synthesis (`D079–D110`)

| Metric | Value (`D110` / `V6.8`) |
| --- | --- |
| Total Unique Stars / Science / Control | **`1,012`** (`760` SCIENCE / `252` CONTROL) |
| Exoplanet Hosts / Confirmed Exoplanets | **`300`** hosts / **`545`** planets |
| Solar Neighborhood ($\le 10\ \mathrm{pc}$) Cohort | **`267`** unique stars (median beamed `0.78810 kW`, opt/IR `0.8363 kW`) |
| Panchromatic Bridge Science Stars / Total Multi-Phase | **`179`** SCIENCE (`48` revisited CONTROL $\to$ `227` multi-phase targets) |
| Panchromatic Bridge Cells (`PANCHROMATIC_BRIDGE_179STARS_V68.csv`) | **`2,635`** cells (`126` IceCube zero-EM bridge rows preserved) |
| IceCube-Only Zero-EM Stars Preserved | **`33`** (never backfilled with synthetic/EM limits) |
| Cumulative Exposures / Integration Time / Comb Stacks | **`4,150`** exposures / **`121,545.3006 h`** / **`719`** comb stacks |
| Spectrographs / Spectral Arms / Companion Archives | **`67`** spectrographs / **`97`** arms / **`36`** archives (`A–AJ`) |
| Total Electromagnetic/Messenger Span | **`60.845` octaves** (`4.1328e-15` to `8556.41831 um`; strict Lyman–mm `13.935` oct; HE unbroken `43.945` oct) |
| Bayesian `f95_uniform` (`eta=1.0`) Highlights | `ALL_SCIENCE_EM` = **`0.529%`**; `EXOPLANET_HOSTS_300` = **`1.1153%`**; `SOLAR_10PC_SCI (<=1 kW)` = **`2.8807%`**; `OPT_NIR_POLARIMETRY_V68` = **`5.8703%`** |
| CWTFM Benchmark (`median P_10m` / `CWTFM`) | `OPT_NIR_POLARIMETRY_V68`: `4.12155 kW` / `4.7846e+06`; `SOLAR_10PC_SCIENCE`: `0.67782 kW` / `2.5726e+05`; `ALL_SCIENCE_EM`: `22.39614 kW` / `8.6485e+05` |

All six 240-DPI publication figures (`fig151`–`fig156`) in `results/figures/` were visually inspected and logged in `results/VISUAL_REVIEW.json`.
