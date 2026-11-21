# SETI Phase D093 Results Report (`V5.1`: Blind Drift-Rate De-Doppler, Standardized Patch Novelty `G8_V51b`, Multi-Event SETI Ellipsoid, and `JWST_NIRSPEC_G395H` Molecular CCF)

**Phase ID:** `D093`  
**Detector:** `TECHNOSIGNATURE_V5_1_DEDOPPLER_DRIFT_MULTIEVENT_ELLIPSOID_GRACES_CORALIE_CARMENES`  
**Date:** `2026-11-21`  
**Audit Status:** `16/16 PASS` (`/usr/bin/python3 -S audit.py`) | `33/33` Bit-Identical (`--from-full-inputs` vs `--from-bounded-inputs`, `22.49 MiB < 25.0 MiB`)

---

## 1. Executive Summary

Phase **D093** extends the prospectively locked panchromatic SETI survey to **15 phases (`D079–D093`)**, **21 spectrographs (24 spectral arms)** spanning **8.273 unbroken octaves (`0.0905–28.00 µm`)**, **350 unique stellar systems** (`268` science---including `169` planet hosts with `347` confirmed exoplanets---and `82` verified zero-planet controls), and **2,163 archival exposures** (`652.7147 hours` cumulative integration).

In **D093**, three new spectrographs---**Gemini-North GRACES** (`R = 67,500`, `4` stars / `8` exposures), **ESO 1.2 m Euler CORALIE** (`R = 60,000`, `5` stars / `10` exposures), and **CAHA 3.5 m CARMENES_VIS** (`R = 94,600`, `6` stars / `12` exposures)---ingest `30` public archival 1D FITS spectra (`215.38 MiB` / `225,843,840` bytes; `5.6636 h`) across **15 brand-new unique stars** (`10` science, `5` controls; `7` within `10 pc`; `>= 8,935.51 arcsec` from all `394` prior targets; `0` `dp_id` overlap across `2,582` prior exposures) and **8 new orbital campaigns (`#110–#117`)**.

Across **1,591 synthetic calibration trials** (`9` suites, bringing the cumulative survey calibration ledger to **32,408 trials**), **five parallel `V5.1` search engines**, **4,727 retroactive Northern `D088` records**, **11 retroactive `JWST_NIRSPEC_G395H` thermal-IR molecular CCF targets (`44` cells)**, **401 all-sky `COMB_V4_1` stacks**, and **350 multi-event SETI Ellipsoid / Earth Transit Zone (`ETZ`) synchronization geometries**:

- **Zero verified ETI detections (`0/350`)** across all five `V5.1` search streams, eliminating **302,198 cumulative Legacy `V2` false alarms** (`1,008` in `D093` -> `668` `G1` -> `83` `V4.2` -> `8` `V5.0 G7` -> `4` `V5.1 G8_V51b` -> `0 ETI`).
- **Blind Linear Drift-Rate Search (`DRIFT_V51`):** `100.0% (60/60)` synthetic drifting laser recovery (`|dv| = 18..210 km s^-1`) at `0/30` stationary and `0/30` single-epoch false alarms; `111,520,615` empirical evaluations yield `135` two-epoch drift pairs (`109` rejected by `G8_V51b`, `16` telluric/airglow, `5` M-dwarf molecular, `3` chromospheric, `2` chance photospheric noise coincidences on `HD217107` and `KELT16` -> `0 ETI`).
- **Gate `G8_V51b` & Retroactive Northern `D088` Suppression:** Achieves `97.5% (39/40)` isolated LSF laser acceptance at `100.0% (80/80)` shared photospheric/topo rejection, cuts `D093` `V5.0` survivors by `50%` (`8 -> 4`), and suppresses retroactive Northern `D088` `V3.9` survivors by **95.0% (`20 V3.9 -> 13 V5.0 -> 1 V5.1` on `LALANDE21185` at `7690.48 Å` telluric O2 A-band; `GJ625 15->0`, `HD114710 1->0`, `HD157881 1->0` -> `0 ETI`)**.
- **`JWST_NIRSPEC_G395H` Molecular CCF (`2.86–5.18 µm`):** Achieves `100.0% (80/80)` synthetic molecular recovery (`NO2`, `N2O`, `CH4_C2H6`, `CO_13CO`) at `100.0% (80/80)` confounder rejection; `0/12` control flags (`BD601753`, `J1743045`, `P330E`), and `1/44` physical detection (`GJ504 CH4_C2H6 depth=0.05486, +8.291 sigma`, `max_conf=0.456`, cold L/T substellar companion methane absorption -> `0 ETI`).
- **Multi-Event Ellipsoid (`350` Stars) & `10 m` EIRP Upper Limits:** Identifies `10` `ETZ` stars (`|beta| <= 0.264 deg`, adding `ROSS64` `+0.11281 deg` and `HD206301` `-0.20199 deg`) and `33` stars within `<= 180 d` of `SN 1987A`, `GW170817`, or `SN 2023ixf` (`HD111031` `5.311 d` to `GW170817`; `ROSS64` `170.556 d` to `SN 1987A`). Reaches **`0.267574 kW` (`267.57 W`)** on `GJ3512` (`CARMENES_VIS M1_5320`) and anchors **`153 < 10 pc` stars (`1.45576 kW` median)**.

---

## 2. Prospective Lock & Stage-2 Calibration Refinements

- **Stage-1 Pre-Download Lock (`METHOD_LOCK.json` + `LOCK_RECEIPT.json`):** Locked at `2026-11-21T06:47:49Z` (`METHOD_LOCK.json` SHA-256 `655b7c543a202d808360d21cded9a2f34a3615a86bd87626bad66a10206aadef`), `+11.0 s` before first FITS download (`2026-11-21T06:48:00Z`). All `7` Stage-1 locked files (`v5_1_detector.py`, `build_cohort.py`, `download_inputs.py`, `FROZEN_COHORT_D093.csv`, `ORBITAL_CAMPAIGNS_AND_KINEMATICS.json`, `PRIOR_EXCLUSION_VERIFICATION.json`, `PRIOR_V5_0_PHASES_SNAPSHOT.json`) remain **100% byte-for-byte untouched** (`v5_1_detector.py` SHA-256 `3cf86d603e18aeeef6ddb5065e1ec3abf3d356ae5bf16f63e3d6679c045a7e6d`).
- **Two Stage-2 Calibration Refinements (`WS93/analyze.py` + `IMPLEMENTATION_LOCK.json`):** Retaining Stage-1 `v5_1_detector.py` untouched, Stage-2 calibration runs exposed two estimator pathologies that were corrected cleanly inside `analyze.py`:
  1. **`Gate G8_V51b` (`g8_v51b_standardized_patch_novelty`):** Stage-1 `fit_patch_novelty_model_v51` / `evaluate_gate_g8_v51` normalized each 17-px patch by its L2 norm before retaining top-8 background PCA components, suppressing isolated `10–30 sigma` LSF Gaussians (`0/40`). `_extract_g8_feat_v51b` / `_fit_g8_v51b` / `_eval_g8_v51b` compute feature-wise standardized `arcsinh(sub/2.5)` + 8 morphological/rarity features (`pca_dim=8`, `knn_k=7`, `min_novelty_z=3.5`) with explicit LSF concentration (`e_conc >= 0.85`), wing quietness (`wing_rms <= 1.35`, `wing_min >= -2.5`), and cohort sparsity guards, recovering `39/40 (97.5%)` isolated lasers while vetoing `80/80` confounders and reducing retroactive `D088` survivors by `95.0%`.
  2. **`JWST_NIRSPEC_G395H` Multi-Component CCF (`nirspec_v51b_joint_multicomp_ccf`):** Stage-1 `_fit_miri_sideband_template` built sidebands per individual Gaussian component, causing `CO` (`4.67 µm`) and `13CO` (`4.78 µm`) to contaminate each other's sidebands (`0/20` recovery for `CO_13CO`). `_fit_nirspec_template_v51b` / `_joint_nirspec_confounder_v51b` / `_scan_nirspec_v51b` exclude the union of all template components (`|w - mu_i| < 2 sigma_i`) when fitting the log-log continuum within each segment and solve the exact joint continuum-covariance term, lifting `NIRSPEC_MOL_CCF_160` to `80/80 (100.0%)` recovery with `0/80` confounder false positives.

---

## 3. D093 Cohort, Exposure Provenance & Orbital Campaigns (`#110–#117`)

- **Instruments & Spectral Coverage:**
  - `GEMINI_GRACES`: `4` stars (`WASP52`, `KELT16`, `QATAR7`, control `HD205905`), `8` OPERA 1D FITS (`0.399–1.048 µm`, `R = 67,500`, CADC Programs `GN-2017B-Q-3`, `GN-2020B-LP-106`, `GN-2022B-LP-106`), `0.1361 h`.
  - `ESO_CORALIE`: `5` stars (`HD217107`, `HD10647`, `HD206301`, controls `HD2151` & `HD111031`), `10` Phase-3 1D FITS (`0.386–0.690 µm`, `R = 60,000`), `0.9742 h`.
  - `CARMENES_VIS`: `6` stars (`GJ1289`, `ROSS64`, `GJ3512`, `G19215`, controls `GJ213` & `HD199305`), `12` CAHA/GAVO DR1 61-order FITS (`0.514–0.979 µm`, `R = 94,600`), `4.5533 h`.
- **Orbital Campaigns (`#110–#117`):** `8` transiting/RV systems spanning `P = 0.969–989.2 d`, `K_p = 19.93–229.335 km s^-1`, and observed intra-window `dv` spans `39.09–224.62 km s^-1` (`#110 WASP52`, `#111 KELT16`, `#112 QATAR7`, `#113 HD217107`, `#114 HD10647`, `#115 GJ1289`, `#116 GJ3512`, `#117 G19215`). Zero `T_DIFF` or `K_PLANET` candidates pass across `1,491,331` `T_DIFF` + `1,490,770` `K_PLANET` bins (`0 ETI`).

---

## 4. Synthetic Calibration Ledger (`1,591` Trials Across `9` Suites)

| Suite | Trials | Pass Metric | Result | False-Alarm / Control Suppression |
| :--- | :---: | :--- | :---: | :---: |
| `CALIBRATION_V51_BLIND_DRIFT_120` | 120 | Drifting laser recovery | **60/60 (100.0%)** | Stationary `0/30`; Transient `0/30` |
| `CALIBRATION_V51_PATCH_NOVELTY_120` (`G8_V51b`) | 120 | Isolated LSF pass (`novelty_z >= 3.5`) | **39/40 (97.5%)** | Shared `0/40`; Topo/Blaze `0/40` |
| `CALIBRATION_V51_RPCA_RARITY_180` | 180 | Isolated RPCA + G7 recovery | **56/60 (93.33%)** | Shared leak `0/60`; Topo repeat `0/60` |
| `CALIBRATION_V51_AGNOSTIC_MULTISCALE_120` | 120 | `2–14 LSF`, Gaussian/boxcar, `+/-` | **120/120 (100.0%)** | Matched polarity & scale `120/120` |
| `CALIBRATION_V51_NIRSPEC_MOL_CCF_160` | 160 | `NO2, N2O, CH4_C2H6, CO_13CO` CCF | **80/80 (100.0%)** | Confounder veto `80/80 (100.0%)` |
| `INJECTION_RECOVERY_540` | 540 | Channel `T` / `P` `>= 8 sigma` | **150/162 (92.59%)** / **157/162 (96.91%)** | Completeness across `9` bands |
| `KEPLERIAN_TRACK_CALIBRATION_81` | 81 | `K_PLANET` de-Doppler vs `T_DIFF` | **80/81 (98.77%)** | `T_DIFF` uncompensated `0/81 (0.0%)` |
| `DETECTOR_V51_G4G5_CALIBRATION_108` | 108 | True LSF pass vs cosmic / plateau | **36/36 (100.0%)** | Cosmic hot-px `0/36`; Plateau `0/36` |
| `COMB_V4_1_CALIBRATION_162` | 162 | `>= 3.8 sigma` 6-tooth recovery | **36/36 (100.0%)** (`47/54` all) | `V4` forest `54/54` -> `V4.1` `0/54`; Topo `0/54` |

---

## 5. Five-Stream Empirical Search & Forensic Triage (`0` Verified ETI)

1. **Stream 1 — Narrowband Cascade (`1,008 -> 4 -> 0 ETI`):** `5,416,831` Channel `T` + `2,708,486` Channel `P` bins yield `1,008` Legacy `V2` false alarms -> `668` `G1` -> `644` `G2` -> `644` `G3` -> `194` `G4` -> `117` pre-`G6` -> `83` `V4.2 G6` -> `8` `V5.0 G7` (`HARPS/FEROS+CORALIE/GRACES/CARMENES` augmented via `20` Archive `R` `ESO_FEROS` spectra) -> **`4` `V5.1 G8_V51b` survivors**:
   - `D093_C00222` (`ESO_CORALIE`, `T`, `SCIENCE`, `HD217107`, `4693.2588 Å`, `z_rpca=10.092`, `novelty_z=13.7198`, `SINGLE_EPOCH_ARCHIVAL_RESIDUAL` -> `0 ETI`)
   - `D093_C00265` (`ESO_CORALIE`, `T`, `CONTROL`, `HD111031`, `4804.9713 Å`, `z_rpca=14.238`, `novelty_z=20.7956`, `SINGLE_EPOCH_ARCHIVAL_RESIDUAL` -> `0 ETI`)
   - `D093_C00287` (`ESO_CORALIE`, `P`, `CONTROL`, `HD111031`, `4804.9663 Å`, `z_rpca=14.238`, `novelty_z=20.7956`, `PHOTOSPHERIC_ORDER_MERGE_RESIDUAL` -> `0 ETI`)
   - `D093_C00315` (`ESO_CORALIE`, `T`, `SCIENCE`, `HD10647`, `5673.3338 Å`, `z_rpca=11.036`, `novelty_z=12.6437`, `SINGLE_EPOCH_ARCHIVAL_RESIDUAL` -> `0 ETI`)
2. **Stream 2 — `DRIFT_V51` (`111,520,615` evals -> `135 -> 0 ETI`):** `109` rejected by `G8_V51b`, `16` telluric/airglow pairs, `5` M-dwarf molecular pairs, `3` chromospheric wings, and `2` `G8`-passed chance photospheric noise coincidences (`D093_DRF_0024` `HD217107`, `D093_DRF_0046` `KELT16`; `0 ETI`).
3. **Stream 3 — Agnostic Multi-Scale (`6,093` evals -> `3 -> 0 ETI`):** `HD111031` (`4238.05 Å`, `z=24.145`; `4907.475 Å`, `z=14.138`) and `QATAR7` (`4039.42 Å`, `z=13.686`), all `PHOTOSPHERIC_OR_ORDER_MERGE_RESIDUAL` (`0 ETI`).
4. **Stream 4 — `COMB_V4_1` (`4,248,132` D093 configs -> `0`; `401` all-sky stacks -> `0 ETI`):** D093 `3` `V4` triggers (`GJ3512`, `HD217107`) collapse to **`0`** under `COMB_V4_1`; across all `401` stacks (`2,163` exposures, `D079–D093`), `22,694` `V4` triggers collapse to `109` `V4.1` -> **`0 ETI`**.
5. **Stream 5 — `JWST_NIRSPEC_G395H` CCF (`44` cells -> `1 -> 0 ETI`):** `0/12` control flags; sole detection is `GJ504 CH4_C2H6` (`depth = 0.05486`, `+8.291 sigma`, `max_conf = 0.456`), matching the direct-imaged cold L/T substellar companion methane band (`0 ETI`). Median `5 sigma` sensitivities: `3.314 ppm equiv` (`CH4_C2H6`), `3.719 ppm` (`CO_13CO`), `4.556 ppm` (`NO2`), `5.758 ppm` (`N2O`).

---

## 6. Radiometric Upper Limits (`60` Cells) & `350`-Star `8.273`-Octave Synthesis

- **D093 Best `10 m` Laser EIRP Limits (Gaia-`G` Planck CGS):**
  - Overall & `CARMENES_VIS`: **`0.267574 kW` (`267.574 W`)** on `GJ3512` (`9.497 pc`, `3141 K`, `M1_5320`); median `CARMENES_VIS` `1.7056 kW`.
  - `ESO_CORALIE`: **`198.044 kW`** on `HD217107` (median `337.23 kW`).
  - `GEMINI_GRACES`: **`205.361 kW`** on `WASP52` (median `951.05 kW`).
- **Cumulative `D079–D093` Totals:** `350` unique stars (`268` sci [`169` hosts / `347` exoplanets], `82` ctrl), `153 < 10 pc` stars (`1.45576 kW` median; `0.0973 W` record on `PROXIMACEN`), `37` bridges (`631` cells), `21` spectrographs (`24` arms, `8.273` octaves), `2,163` exposures (`652.7147 h`), `32,408` calibration trials, `302,198` `V2` false alarms eliminated, `117` orbital campaigns, `23/23` radio-echelle closure, `0 verified ETI`.
