# Phase D109 (V6.7) Results Report: 100% <10 pc Exoplanet-Host Drift Closure, 37/37 Control Backfill, Strict Scale Separation & Bayesian $f_{\mathrm{tx}}$ / CWTFM Synthesis

**Detector:** `TECHNOSIGNATURE_V6_7_10PC_DRIFT_CLOSURE_SCALE_SEP_BAYESIAN_FTX_CWTFM`  
**Phase ID:** `D109` (`V6.7`, Roadmap Spor 1)  
**Workspace:** `analysis_workspace/work_v6_7_20261125_d109_10pc_drift_closure_bayesian_ftx_cwtfm`  
**Verified ETI Detections:** **`0`** (D109 and cumulative D079–D109)

---

## 1. Prospective Method Seal, Chronology & Reproducibility Integrity

| Check | Verified Observed Value |
| :--- | :--- |
| Prospective `METHOD_LOCK.json` seal UTC | `2026-11-25T17:27:58.842933+00:00` (`locked_unix_epoch = 1795627678.8429`) |
| `METHOD_LOCK.json` SHA-256 | `b6f3908d384dde4db26e320531b5cda34a438c8b77b4569382aff03356e16141` |
| `inputs_dir_exists_at_seal` | `false` (`0` inputs pre-downloaded at seal) |
| First science download UTC | `2026-11-25T17:28:17.961258+00:00` (`chronology_lag_seconds = +19.118 s`) |
| Prior excluded coordinates / `dp_id`s / overlap | `1,077` coords / `4,133` `dp_id`s / **`0` `dp_id` overlap** |
| Valid analyzed observations / physical FITS files | `216 / 216` (`0` failed) / `216` physical files (`54` bridge `< 10 pc` hosts $\times 4$ nights) |
| Raw archival input volume | `1,150,129,526 B` (`1,096.849 MiB`) |
| Bounded reproduction bundle (`d109_bounded_bundle.json.gz`) | `30,754,736 B` (`29.330 MiB <= 35.0 MiB`, codec `sbf16l_fl7_er4`), SHA-256 `336c1915b946bb2aaa123192b73cb36802acc1b562b9aeedf151f966f9a926a9` |
| Dual-mode zero-diff check (`--from-full-inputs` vs `--from-bounded-inputs`) | `58` top-level `results/` CSV/JSON files compared, **`0` byte diffs (`DUAL_MODE_ZERO_DIFF_PASS`)** |

---

## 2. Deliverable 1: 100.0% (`61 / 61`) `< 10 pc` Exoplanet-Host Coherent `DRIFT_V67` + `COMB_DRIFT_V67` Closure

- **Closure Architecture (`154` Total Coherent Campaigns -> `0` Verified ETI):**
  - `90` SHA-256-sealed `V6.6` campaigns carried forward from Companion Archive `AH`, with **live bit-exact regression** verified on `GJ317` (`ESO_NIRPS`, `traj=1,406`, `comb=329`, `eti=0`) and `7CMA` (`ESO_HARPS`, `traj=1,412`, `comb=292`, `eti=0`).
  - `10` retro-unlocked `N >= 4`-night campaigns reprocessed from verified Companion Archives `Q` (`D091`: `HD213885`, `GJ433`, `COROT7`, `G29751`, `GJ436`, `KEPLER156`, `OGLETR111`, `OGLETR113`, `K222`) and `AB` (`D102`: `GJ203`), adding `2` `< 10 pc` exoplanet hosts (`GJ433`, `GJ436`).
  - `54` brand-new non-overlapping `N = 4` distinct-night (`>= 1.0 d` separation) `< 10 pc` exoplanet-host campaigns (`#199–#252`, baselines `77.78 d` to `8,011.12 d`) across `38 ESO_HARPS` (`152` FITS), `15 CARMENES_VIS` (`60` FITS), and `1 HARPS_N` (`HD219134`, `4` FITS), totaling `216` FITS (`44.7116 h` integration, `0` brand-new stars; global `1,004` star roster preserved).
- **100% `< 10 pc` Host & Planet Coverage (`SOLAR_10PC_EXOPLANET_HOSTS_61_DRIFT_CLOSURE.csv`):**
  - **`61 / 61` (`100.0%`)** `< 10 pc` exoplanet hosts and **`121 / 121` (`100.0%`)** confirmed `< 10 pc` exoplanets are now covered by coherent shift-and-stack orbital drift + drifting comb searches (up from `5/61` hosts / `6/121` planets in `D108`), bringing global exoplanet-host coherent drift coverage to **`132 / 298` (`44.3%`)**.
- **Search Volume & Triage (`DRIFT_V67` / `COMB_DRIFT_V67` / 4-Gen Optical-NIR):**
  - `34` synthetic calibration suites (`7,274 / 7,311 = 99.49%` passed, every suite `>= 97.5%`; `V67_BAYESIAN_OCCURRENCE_240` `240/240`, `V67_SCALE_SEPARATION_CWTFM_180` `180/180`; `88,434` cumulative trials).
  - `DRIFT_V67` (`154` campaigns): `223,684` Keplerian/jerk trajectories (`29,260,619,166` pixel-trajectory integrals) -> `66,979` raw coherent survivors (`1,342` ledger rows in `DRIFT_V67_CANDIDATE_LEDGER.csv`) -> **`0` verified ETI**.
  - `COMB_DRIFT_V67` (`154` campaigns): `38,086` comb-drift trajectories -> `10,154` raw candidates -> `457` pre-Stage-2 qualified (`1,230` ledger rows in `COMB_DRIFT_V67_CANDIDATE_LEDGER.csv`) -> **`0` verified ETI**.
  - Single-exposure 4-Gen (`216` `D109` spectra): `755` G1 seeds (`636 ESO_HARPS`, `118 CARMENES_VIS`, `1 HARPS_N`) -> `25` G8 survivors in `V6_7_CANDIDATE_LEDGER.csv` (all `ESO_HARPS`, triaged as single-exposure or photospheric artifacts) -> **`0` verified ETI**.
  - Static `COMB_V4_1`: `24,560,852` configs in `D109` -> `11,469` candidates (`45,096` cumulative across `632` stacks) -> **`0` verified ETI**; `v2` false alarms rejected in `D109`: `531,223` (`1,649,921` cumulative).
  - Deepest `D109` `10 m` optical EIRP constraints (`255` rows in `EIRP_UPPER_LIMITS_D109.csv`): `ESO_HARPS` `PROXIMACEN` (`H1_4100`) **`0.01834953 kW`**, `CARMENES_VIS` `GJ3512` (`M1_5320`) **`0.24011893 kW`**, `HARPS_N` `HD219134` (`HN3_5800`) **`26.27662154 kW`**.

---

## 3. Deliverable 2 & 3: `37 / 37` Control Backfill & Strict Physical Scale Separation

- **100% (`37 / 37`) Early `D079–D090` Control Radiometric Recovery (`CONTROL_RADIOMETRIC_BACKFILL_37STARS_D109.csv`):**
  - Recovered exact `C12` Planck-anchored limits (`min = 0.13226514 kW` on `L 49956`, `D086` `ESPRESSO`; `max = 176,268.48889392 kW` on `J1802271`, `D090` `JWST_NIRSPEC_G235H`) for `24` `D079–D085` band-noise stars, `5` `D086` calibration-patch stars, and `8` `D090` Archive `P` stars.
  - Self-consistency across all `255` `D109` EM limits + all `37` Control backfills: `c12_radiometric_max_rel_err = 0.0`.
  - Populates **`971 / 971`** EM-observed stars across the `1,004`-star table, leaving strictly **`33`** *IceCube*-only neutrino stars blank in EM columns (**`0` unexplained blank EM limits**).
- **Strict Physical Scale Separation (`PHYSICAL_SCALE_SEPARATION_1004STARS_D109.csv`):**
  - Diffraction-beamed UV–optical–IR–mm laser EIRP (`min_beamed_uv_opt_ir_mm_10m_kw`, `736` stars) is cleanly decoupled from model-independent isotropic HE X-ray/$\gamma$-ray luminosity (`min_he_l_iso_mw`, `306` stars, plus $1^\circ$ and $1'$ cone conversions) and *IceCube* neutrino limits (`min_icecube_l_nu_iso_mw`).
  - Zero HE/neutrino instruments appear in `best_beamed_instrument`, `ICECUBE_10YR` is absent from `EIRP_UPPER_LIMITS_D109.csv`, and all `126 / 126` `ICECUBE_10YR` cells in `PANCHROMATIC_BRIDGE_178STARS_V67.csv` retain empty EM fields.
  - Clean `< 10 pc` medians: beamed UV–mm **`0.82489339 kW`** (`opt/IR = 0.9412 kW`), `< 10 pc` coherent hosts median **`0.49453 kW`**, HE isotropic $L_{\mathrm{iso}}$ median **`6.648475e+13 MW`**.

---

## 4. Deliverable 4: Exact Numerical Bayesian $f_{\mathrm{tx}}$ & CWTFM / Haystack Benchmark

- **Exact Numerical Bayesian 95% Credible Upper Limits (`BAYESIAN_FTX_OCCURRENCE_LIMITS_D109.csv`):**
  - Integrated directly over exact per-star effective detection probability $p_i = c_{\mathrm{cal}}[1 - (1 - \eta_{\mathrm{duty}})^{K_i}]$ using `n_distinct_nights_total` across `7` beamed and `4` HE/$\nu_\mu$ cohorts under both `Uniform(0,1)` and `Jeffreys Beta(1/2, 1/2)` priors:
    - `ALL_SCIENCE_EM` (`n=562`, any calibrated threshold): $f_{95} = \mathbf{0.5384\%}$ Uniform / $\mathbf{0.3480\%}$ Jeffreys at $\eta=1.0$; $\mathbf{0.6770\%}$ at $\eta=0.5$; $\mathbf{1.6402\%}$ ($\mathbf{1.0602\%}$ Jeffreys) at $\eta=0.1$; $\mathbf{12.1589\%}$ ($\mathbf{7.9998\%}$ Jeffreys) at $\eta=0.01$ ($\mathbf{1.2585\%}$ at $P_{10\mathrm{m}} \le 10\,\mathrm{kW}, \eta=1.0$).
    - `EXOPLANET_HOSTS_298` (`n=268` beamed): $\mathbf{1.1236\%}$ at $\eta=1.0$ (any calibrated).
    - `SOLAR_10PC_SCIENCE` (`n=178` beamed): $\mathbf{2.9650\%}$ at $P_{10\mathrm{m}} \le 1\,\mathrm{kW}$ and $\mathbf{2.0061\%}$ at $P_{10\mathrm{m}} \le 10\,\mathrm{kW}$ ($\eta=1.0$).
    - `DRIFT_V67_COHERENT_154` (`n=154`): $\mathbf{1.9361\%}$ at $\eta=1.0$ (any calibrated).
    - `SOLAR_10PC_HOSTS_61` (`n=61`): $\mathbf{4.7710\%}$ Uniform / $\mathbf{3.1288\%}$ Jeffreys at $\eta=1.0$ (`ANY_CALIBRATED`, $\mathbf{5.4582\%}$ at $P_{10\mathrm{m}} \le 5\,\mathrm{kW}$), degrading slowly to $\mathbf{7.0751\%}$ at $\eta=0.1$ via multi-night revisiting.
- **CWTFM & Cosmic Haystack Context (`CWTFM_COSMIC_HAYSTACK_BENCHMARK_D109.csv`):**
  - Unites `35` companion archives (`A–AI`), `66` spectrographs / `96` spectral arms, `60.845` EM octaves (`4.1328066e-15` to `8556.41831 um`), `43.945` unbroken high-energy octaves, `13.935` strict zero-gap Lyman-to-mm octaves (`14.693` octaves to `ALMA` Band 4 low edge `2397.28632 um`), across `1,004` unique stars (`753` `SCIENCE`, `251` `CONTROL`; `298` hosts / `543` planets; `267` stars `< 10 pc`; `194` ETZ / `41 <= 180 d` Ellipsoid; `178` `SCIENCE` bridge targets / `222` multi-phase targets / `2,589` bridge cells in `PANCHROMATIC_BRIDGE_178STARS_V67.csv`), `4,063` exposures, `121,516.4078 h` integration, `88,434` calibration trials, **`0` verified ETI detections**.
