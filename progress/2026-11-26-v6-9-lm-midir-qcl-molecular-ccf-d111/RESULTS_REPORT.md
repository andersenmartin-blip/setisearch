# Phase D111 (`V6.9`) K/L/M & Mid-IR QCL Laser and Molecular Technosignature CCF Results Report

**Phase ID:** `D111` (`V6.9`)  
**Detector:** `TECHNOSIGNATURE_V6_9_LM_MIDIR_QCL_LASER_AND_MOLECULAR_CCF`  
**Stage-1 Seal (`locked_utc`):** `2026-11-26T07:33:00.294842+00:00` (`METHOD_LOCK.json` SHA-256 verified, `chronology_lag = +10.650s`)  
**Survey Closure:** `33/33` campaigns (`D079–D111`), `1,039` unique stars (`787` SCIENCE, `252` CONTROL), `67` spectrographs / `98` spectral arms (adding `JWST_NIRSPEC_G395M`), `37` companion archives (`A–AK`), `verified_eti_detections_total = 0`.

---

## 1. Executive Summary & Headline Outcomes

Phase `D111` (`V6.9`) executes a multi-regime **`1.95–18.0 µm` ($K/L/M/N$-band) narrowband QCL/laser emission search, ground-based $K$-band frequency-comb search, and 14-species joint confounder-regressed molecular technosignature CCF** across **111 validated archival 1D FITS spectra** (`173.2505 h` integration time, `95.161 MiB` raw FITS inputs, `73` targets = `46` prior bridges + `27` brand-new confirmed exoplanet hosts at separation $\ge 650.96^{\prime\prime}$ from all `1,085` prior coordinates):

- **Four complementary IR spectroscopic arms (`111/111` valid physical FITS, `0` failures, `0` `dp_id` overlap across `4,482` prior IDs):**
  - `ESO_CRIRES_PLUS`: `34` high-resolution $K$-band spectra (`1.95–2.49 µm`, $R = 43,000\text{–}86,000$, ESO Phase 3)
  - `JWST_NIRSPEC_G395H`: `31` space $L/M$-band spectra (`2.87–5.27 µm`, $R = 2,700$, non-timeseries Level-3 `x1d.fits`)
  - `JWST_NIRSPEC_G395M` (**98th spectral arm**): `6` space $L/M$-band spectra (`2.87–5.27 µm`, $R = 1,000$, non-timeseries Level-3 `x1d.fits`)
  - `JWST_MIRI_MRS`: `40` space mid-IR IFU sub-band spectra (`4.90–18.0 µm`, $R \approx 2,500$, Level-3 `x1d.fits`)
- **Physics-grounded Narrowband QCL & Comb Triage (`0` Verified ETI):**
  - `QCL_LM_V69`: `1,536` raw `z >= 7` `Q1` peaks $\to$ `1,087` passing `Q2` (detector-edge & single-px CR/hot-pixel veto) $\to$ `1,051` passing `Q3` (IR astrophysical `HI`/`H2`/`[Fe II]`/`[Ar II]`/`[Ne II]`/`CO` atlas veto) $\to$ `850` passing `Q4` ($K$-band ground telluric/OH airglow veto) $\to$ `531` pre-Stage-2 `Q5` triggers (`238` CRIRES+ CO/H2O residuals, `65` MIRI/MRS `0.0085 µm` dichroic fringe/disk residuals, `228` NIRSpec IFU/SLIT photospheric/nebular features) $\to$ **`0` Stage-2 survivors (`verified_eti = 0`)**.
  - `CRIRES_K_COMB_V69`: `1,010` clean $K$-band teeth across `1,669` trial comb spacings $\to$ `541` pre-Stage-2 comb solutions (dense stellar CO rovibrational / telluric line forests) $\to$ **`0` verified ETI combs**.
- **14-Species Molecular Technosignature CCF (`MOL_CCF_V69`):**
  - Evaluated across all `77` space-based JWST exposures (`277` species-exposure evaluations across `NO2`, `CH4_C2H6`, `PH3`, `N2O`, `CO_13CO`, `OCS_PF3`, `CF4`, `CFC12`, `SF6`, `NF3`, `PF3`, `CFC11`), reaching a median 5-sigma band-depth sensitivity **`10.9584%`** (down to `< 1–3%` on bright hosts like `51 Eri`, `HD 131835`, `P 330E`, `AF Lep`, `HD 206893`, `GJ 504`, `CT Cha`, `GQ Lup`).
  - Only `3` pre-Stage-2 CCF hits occurred (`GJ 504` `CH3-SHORT` `CFC11` [edge/fringe/NH$_3$], `HIP 65426` `PH3` [`CO2`/`CO` blend], `Red Rectangle` `N2O` [`PAH`/`CO` proto-PN plateau]) — all cleanly vetoed in Stage-2 (`0` verified ETI).
- **Exact `C12` Planck/Jy-Anchored QCL EIRP Limits (`c12_max_rel_err = 0.0`):**
  - `JWST_NIRSPEC_G395M` (98th arm) best: `WISE0855` (`QCL_L_31000`, `3.1 µm`) = **`0.001733 kW` (`1.73 W`)**
  - `JWST_NIRSPEC_G395H` best: `SIMP0136` (`QCL_L_35000`, `3.5 µm`) = **`0.005359 kW` (`5.36 W`)**
  - `ESO_CRIRES_PLUS` best: `WISE1049AB` (`QCL_K_21500`, `2.15 µm`) = **`0.130608 kW` (`130.6 W`)**
  - `JWST_MIRI_MRS` best: `WISE0855` (`QCL_N_106000`, `10.6 µm`) = **`0.517902 kW` (`517.9 W`)**

---

## 2. Calibration, Anchor Regression & Dual-Mode Reproducibility

- **Synthetic Calibration Suites (`40/40` suites >= 97.5%):** `8,473 / 8,511` trials passed (`99.55%`) in `D111`, bringing cumulative `D079–D111` calibration volume to **`104,856` trials**. New `V6.9` suites:
  - `CALIBRATION_V69_QCL_LM_LASER_240`: **`240/240 (1.0000)`**
  - `CALIBRATION_V69_MOLECULAR_CCF_240`: **`240/240 (1.0000)`**
  - `CALIBRATION_V69_CRIRES_KBAND_COMB_120`: **`120/120 (1.0000)`**
- **Archive `AH` Bit-Exact Regression Anchors:** `GJ317(traj=1406,comb=329,eti=0)` and `7CMA(traj=1412,comb=292,eti=0)`.
- **Lossless Bounded Bundle & Dual-Mode Zero-Diff Verification:** Lossless `f32l_ieee754` packing produces `bounded_inputs/d111_bounded_bundle.json.gz` at **`10,448,848 B` (`9.965 MiB <= 35.0 MiB`**, SHA-256 `6b3c42e3aa11f436c9b7495e942feedc690e1a74e9d6c1994a5b9518fe0f7283`). Execution via `--from-full-inputs` vs. `--from-bounded-inputs` yields **`0` byte diffs across all `60` CSV/JSON files** (`DUAL_MODE_ZERO_DIFF_PASS`).

---

## 3. Unified `1,039`-Star Panchromatic Synthesis (`D079–D111`)

| Metric | Value (`D111` / `V6.9`) |
| --- | --- |
| Total Unique Stars / Science / Control | **`1,039`** (`787` SCIENCE / `252` CONTROL) |
| Exoplanet Hosts / Confirmed Exoplanets | **`327`** hosts / **`576`** planets |
| Solar Neighborhood ($\le 10\ \mathrm{pc}$) Cohort | **`267`** unique stars (median beamed `0.78810 kW`, opt/IR `0.8290 kW`) |
| Panchromatic Bridge Science Stars / Multi-Phase Targets | **`197`** SCIENCE (`53` revisited CONTROL $\to$ `250` multi-phase targets) |
| Panchromatic Bridge Cells (`PANCHROMATIC_BRIDGE_197STARS_V69.csv`) | **`2,693`** cells (`126` IceCube zero-EM bridge rows preserved) |
| IceCube-Only Zero-EM Stars Preserved | **`33`** (never backfilled with synthetic/EM limits) |
| Cumulative Exposures / Integration Time / Comb Stacks | **`4,261`** exposures / **`121,718.5511 h`** / **`753`** comb stacks |
| Spectrographs / Spectral Arms / Companion Archives | **`67`** spectrographs / **`98`** arms / **`37`** archives (`A–AK`) |
| Total Electromagnetic Span | **`60.845` octaves** (`4.1328e-15` to `8556.41831 um`; strict Lyman–mm `13.935` oct) |
| Bayesian `f95_uniform` (`eta=1.0`) Highlights | `ALL_SCIENCE_EM` = **`0.5044%`**; `EXOPLANET_HOSTS_327` = **`1.0114%`**; `SOLAR_10PC_SCI (<=1 kW)` = **`2.8271%`**; `LM_MIDIR_QCL_V69` = **`3.9847%`**; `JWST_MOL_CCF_V69` = **`6.0768%`** |
| CWTFM Benchmark (`median P_10m` / `CWTFM`) | `LM_MIDIR_QCL_V69`: `132.57632 kW` / `4.4701e+06`; `SOLAR_10PC_SCIENCE`: `0.67782 kW` / `2.4715e+05`; `ALL_SCIENCE_EM`: `26.90333 kW` / `8.5275e+05` |

All six 240-DPI publication figures (`fig157`–`fig162`) in `results/figures/` were visually inspected and logged in `results/VISUAL_REVIEW.json`.
