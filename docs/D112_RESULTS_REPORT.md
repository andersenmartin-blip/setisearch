# Phase D112 (V7.0) Results Report — INTEGRAL 511 keV, LHAASO 1.000 PeV Multi-Messenger & ALMA Band 2 SV (10/10 ALMA Bands Closure)

**Phase / Detector:** `D112` / `TECHNOSIGNATURE_V7_0_INTEGRAL_LHAASO_PEV_AND_ALMA_BAND2`  
**Stage-1 Seal (Prospective):** `2026-11-26T17:11:35.673380+00:00` (`inputs_dir_exists_at_seal == False`, chronology lag `+10.650 s`, `d112_dp_id_overlap_count == 0` across Archives `A–AK`)  
**Companion Archive:** `AL` (`SETI_D112_V7_0_INTEGRAL_LHAASO_PEV_ALMAB2_RESULTS_2026-11-26.zip`)  
**Dual-Mode Verification:** `0` byte diffs across all `64` CSV/JSON files between `--from-full-inputs` and `--from-bounded-inputs` (`d112_bounded_bundle.json.gz` = `0.1181 MiB <= 35.0 MiB`)  
**Verified Extraterrestrial Intelligence (ETI) Detections:** **`0` across all 4,383 exposures / 1,083 unique stars (D079–D112)**

---

## 1. Executive Summary (Spor 4)

Phase `D112` (`V7.0`) executes **Spor 4** across three transformative multi-messenger and millimeter observational pillars while maintaining strict prospective sealing (`METHOD_LOCK.json` frozen before any physical download), `0` prior `dp_id` overlap across all `37` prior companion archives (`A–AK`), and minimum angular separation `>= 629.85"` for all `44` brand-new sources:

1. **ESA/NASA *INTEGRAL* (`62` Real Coded-Mask & Ge Spectra):**
   - `INTEGRAL_IBIS_ISGRI` (`35` spectra, `13–970.88 keV`, explicit `511 keV` $e^+/e^-$ positron annihilation screening),
   - `INTEGRAL_JEMX` (`16` spectra, `256` channels, `3–35 keV`),
   - `INTEGRAL_SPI` (`11` spectra, coded-mask Ge `20–540 keV`),
   - Totaling **`43` spectra covering the `511 keV` annihilation regime** (`I1 = 24` raw `|z|>=6` excesses -> `I5 = 6` pre-Stage-2 residuals on `Cas A`, `Circinus Galaxy`, `Mrk 501`, `NGC 3227`, `V1223 Sgr`, `X Per` -> all **vetoed** at Stage 2 as astrophysical Compton reflection continua / coded-mask tails, **`0` ETI**). Best narrowband `L_iso` upper limit: **`SSCYG`** (`INTEGRAL_IBIS_ISGRI`, `F_lim = 7.030014e-12 erg cm^-2 s^-1`, `L_iso = 1.072946e+18 MW`).
2. ***1LHAASO* PeV Multi-Messenger Array (`58` Source-Instrument Tracks, `29` Sources):**
   - `LHAASO_WCDA` (`29` tracks, `1–25 TeV`) + `LHAASO_KM2A` (`29` tracks, `25–1,000 TeV` = **`1.000 PeV`**), incorporating real VizieR `1LHAASO` FITS (`J/ApJS/271/25`), Zenodo `J2108+5153` binned SED (`LHAASO_J2108_data_release_v1.0.0`), and `JHEAp` UHE sample tables (`13` UHE sources).
   - Pushes the survey global minimum wavelength from `4.1328066e-15 um` to **`1.239842e-15 um`** (`1.000 PeV`), extending unbroken high-energy EM coverage from **`43.945` to `45.682` octaves** and total survey EM span from **`60.845` to `62.582` octaves** (`0` qualified PeV beacons after L2 25 TeV stitch, L3 `r39 > 0.35 deg` halo, and L4 broadband curvature vetoes). Best UHE `L_iso` limit: **`J0622P3754`** (`LHAASO_KM2A`, `L_iso = 1.13595e+17 MW` up to `1,000 TeV`).
3. **ALMA Band 2 Science Verification (`ARP 220`, `2011.0.00026.SV`):**
   - Processes `3` full 3D interferometric FITS spectral cubes (`1152 x 1152 x 384` channels = `~1.9 GB` each; March 2026 SV `X36 spw51` `86.45–88.32 GHz`, `X36 spw111` `106.96–108.83 GHz`, and `X52 spw29` `112.25–114.12 GHz`) via bounded channel-by-channel `memmap=True` extraction (`< 30 MB` array footprint).
   - Completes all **`10/10` ALMA receiver bands (`B1, B2, B3, B4, B5, B6, B7, B8, B9, B10`)** in a single homogeneous panchromatic catalog (`0` qualified narrowband ETI residuals on `ARP 220`; best `X52 spw29` 7$\sigma$ limit `P_beam(10m) = 2.486514e+17 kW` at `113.19 GHz`, `L_iso = 3.498315e+22 MW`).

---

## 2. Unified Survey Metrics (`D079–D112`)

| Survey Metric | D111 (`V6.9`) | D112 (`V7.0`) | Delta |
|---|---:|---:|---:|
| Companion Archives | 37 (`A–AK`) | **38 (`A–AL`)** | +1 (`AL`) |
| Unique Spectrographs | 67 | **72** | +5 |
| Distinct Spectral Arms | 98 | **104** | +6 |
| ALMA Receiver Bands Covered | 9/10 (`B1, B3–B10`) | **10/10 (`B1, B2, B3–B10`)** | Band 2 SV closed |
| Shortest Wavelength ($\lambda_{\min}$) | `4.1328066e-15 um` (300 TeV) | **`1.239842e-15 um` (1.000 PeV)** | $3.33\times$ shorter |
| Unbroken High-Energy EM Span | `43.945` octaves | **`45.682` octaves** | +`1.737` octaves |
| Total EM Span (35 GHz ALMA B1 – 1 PeV LHAASO) | `60.845` octaves | **`62.582` octaves** | +`1.737` octaves |
| Unique Targets / Stars | `1,039` | **`1,083`** (`787` Sci + `296` Ctl) | +`44` new (`+27` bridges) |
| Panchromatic Bridge Science Stars | `197` | **`197`** (`2,695` bridge cells) | +`2` D112 HE bridge rows |
| Solar Neighborhood `< 10 pc` Stars | `267` | **`267`** (median `0.7881 kW` @ 10m) | Preserved |
| IceCube-Only Zero-EM Targets | `33` (`126` empty EM cells) | **`33` (`126` empty EM cells)** | Strictly preserved |
| Total Exposures Analyzed (`D079–D112`) | `4,261` | **`4,383`** | +`122` (`736,410.27` hrs cum.) |
| Cumulative Synthetic Calibration Trials | `104,856` (`40` suites) | **`113,967` (`43` suites)** | +`9,111` (`9,072/9,111 = 99.57%`) |
| Verified ETI Detections | `0` | **`0`** | Null confirmed |

---

## 3. Calibration, Anchor Verification & Bayesian `f_tx`

- **All `43/43` Calibration Suites >= 97.5%:** New `V7.0` suites achieve `CALIBRATION_V70_INTEGRAL_511KEV_ISGRI_JEMX_240 = 240/240 (1.0000)`, `CALIBRATION_V70_LHAASO_PEV_KM2A_WCDA_240 = 240/240 (1.0000)`, and `CALIBRATION_V70_ALMA_BAND2_INTERFEROMETRIC_120 = 119/120 (0.9917)` (`599/600 = 99.83%`); combined D112 suite total `9,072/9,111 (99.57%)`, bringing the cumulative synthetic benchmark to **`113,967` trials**.
- **Bit-Exact Archive `AH` Live Anchor Regression:** `GJ317 (traj=1406, comb=329, eti=0)` and `7CMA (traj=1412, comb=292, eti=0)` verified bit-exactly, alongside SHA-256 verification of Archive `AJ` and Archive `AK`.
- **Bayesian 95% Credible Occurrence Limits (`f_tx`, steady $\eta = 1.0$, uniform prior):**
  - `ALL_SCIENCE_EM (ANY_CALIBRATED, N=600 beamed)`: **`0.5048%`**
  - `SOLAR_NEIGHBORHOOD_10PC_SCI (ANY_CALIBRATED, N=179)`: **`1.6753%`**
  - `EXOPLANET_HOSTS (ANY_CALIBRATED, N=298)`: **`1.0120%`**
  - `ALL_HE_ISOTROPIC_EM (ANY_CALIBRATED, N=352)`: **`0.8484%`**
  - `ICECUBE_NEUTRINO (ANY_CALIBRATED, N=54)`: **`5.3626%`**
- **Scale Separation Guarantee:** `INTEGRAL_IBIS_ISGRI`, `INTEGRAL_JEMX`, `INTEGRAL_SPI`, `LHAASO_WCDA`, and `LHAASO_KM2A` contribute strictly to isotropic HE luminosity bounds (`min_he_flux_lim_cgs`, `min_he_l_iso_mw`, `min_he_ptx_1deg_mw`, `min_he_ptx_1arcmin_mw`) and never contaminate `min_beamed_uv_opt_ir_mm_10m_kw`; `ALMA_B2_3MM` enters exclusively the beamed UV–mm regime.

---

## 4. Visually Verified Deliverables (`fig163–fig168`)

All six figures in `results/` have been visually verified via direct image inspection (`results/VISUAL_REVIEW.json`):
1. `fig163_d112_integral_511kev_and_hard_xray_limits.png`
2. `fig164_d112_lhaaso_1pev_frontier_and_sed.png`
3. `fig165_d112_alma_band2_sv_arp220_closure.png`
4. `fig166_d112_62p6_octave_panchromatic_continuity.png`
5. `fig167_d112_physical_scale_separation_and_ftx_1083stars.png`
6. `fig168_d112_43suites_calibration_and_haystack.png`
