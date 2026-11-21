# Phase D096 (`V5.4`) Results Report — SOFIA/EXES Mid-IR Echelon-Echelle, Coherent Shift-Stack Drift (`DRIFT_V54`), and JWST NIRISS/SOSS + NIRSpec/G140H Search

## 1. Executive Summary & Prospective Stage-1 Lock Chronology
- **Phase ID:** `D096`
- **Detector:** `TECHNOSIGNATURE_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_AND_JWST_NIRISS`
- **Stage-1 Prospective Lock UTC:** `2026-11-21T20:21:09Z` (`METHOD_LOCK.json` SHA-256: `9929446eb263df99ceaf114528fc3d8b8c7a2684d004c758f07510b118593373`; 7/7 Stage-1 locked artifacts unmodified)
- **First Science Download UTC:** `2026-11-21T20:21:27Z` (`+18.01 s` post-lock lag; `SOFIA_EXES/SIRIUS/...`)
- **Cohort & Zero Overlap:** `30` stars (`24` brand-new unique stars, `6` panchromatic bridges: `ALFTAU`, `ARCTURUS`, `HD62509`, `SIRIUS`, `VHS1256B`, plus `BD601753` revisited control; `4` brand-new within `10 pc`; `6` controls / `24` science targets; `39` raw FITS files totaling `115.587 MiB`; `131` physical exposures; `30.1721` integration hours; `0` prior `dp_id` overlap across `460` prior excluded coordinates; min brand-new separation `1,655.13"`).
- **Bounded Reproducibility Bundle:** `bounded_inputs/d096_bounded_bundle.json.gz` = `11.85 MiB` (`12,430,078` bytes `<= 22.0 MiB`), achieving `36/36` 100% SHA-256 bit-identical regeneration under `--from-bounded-inputs`.
- **Headline Finding:** **0 verified ETI detections** across all five D096 streams (`SOFIA_EXES`, `CARMENES_VIS`, `SDSS_APOGEE2`, `JWST_NIRISS_SOSS`, `JWST_NIRSPEC_G140H`), retroactive `DRIFT_V54` campaigns, Orbital Campaigns `#134–#138`, and unified `448`-stack laser comb search.
- **Unified D079–D096 Survey Totals:** `425` unique stars (`327` science / `98` control; `165` within `10 pc` with median limit `1.5222 kW`), `27` spectrographs / `36` arms spanning `0.0905–37.86356 um` (`8.709` octaves), `52` calibrated bridges (`719` bridge cells; `53` total multi-phase targets including `BD601753`), `2,523` exposures (`751.6534` hr), `138` orbital campaigns, `448` comb stacks, `37,911` synthetic calibration trials, `313,257` V2 false alarms eliminated (`810` in D096), and **`0` verified ETI detections**.

## 2. Stream-by-Stream Scientific Results

### Stream 1: SOFIA/EXES High-Resolution Mid-IR Echelon-Echelle (`17` stars, `348` orders, `5.62–26.13 um`)
- Ingested `19` SOFIA/EXES Level-3 `_CMB_` files across `17` stars (`15` science + `2` controls: `NGC1068`, `NGC7027`), parsing `(N_orders, 4 or 5, N_pix)` cubes from descending wavenumber (`cm^-1`) to ascending vacuum wavelength (`um`) and computing analytical BERV from Gaia/SIMBAD coordinates.
- Scanned `326,686` Channel-T spectral bins: `149` Stage-1 G1 seeds -> `0` G2 ATRAN failures -> **`148` G4/G5 PSF/cosmic-ray vetoes** (dominated by `BETELGEUSE` 86 and `HR7957` 24 narrow detector spikes) -> **`1` G6 topocentric repeatability veto** -> **`0` qualified candidates**.
- Tightest mid-IR beam limit: **`SIRIUS` (`2.67 pc`, `EXES_7UM` `7.21 um`) = `202.381291 kW`** (`10 m` aperture, `8-sigma`), promoting `SIRIUS`, `HD62509`, `ALFTAU`, and `ARCTURUS` into multi-octave mid-IR calibrated bridges.

### Stream 2: CARMENES VIS (`R = 94,600`) & SDSS APOGEE-2 (`N = 14–28` visits)
- Applied per-exposure CARACAL SERVAL RV barycentric alignment for `CARMENES_VIS` (`HNLIB`, `LP73158`, `WOLF1069`), eliminating M-dwarf TiO RV offsets that caused `85` spurious `COMB_V4_1` candidates on `HNLIB` (`85 -> 0`), and enforced full `oh2/airglow/G3–G5/G6` gating in `Channel P`.
- Four-generation cascade: `CARMENES_VIS` `212 G1 -> 198 G2 -> 196 G3 -> 2 G45 -> 0 G6/G7/G8`; `SDSS_APOGEE2` `184 G1 -> 116 G2 -> 116 G3 -> 0 G45–G8`; `0` verified ETI.
- Tightest CARMENES limit: **`LP73158` (`4.49 pc`, `M1_5320`) = `0.114498 kW` (`114.5 W`)**.
- **Orbital Campaigns `#134–#138`** (`WOLF1069 b`, `HNLIB b`, `KEPLER381 b`, `KEPLER1313 b`, `KEPLER1002 b`): `0` `K_PLANET` candidates (`138` cumulative campaigns).
- **All-Sky Laser Comb (`COMB_V4_1`):** `846,168` configs scanned across D096 -> `0` candidates (`448` cumulative D079–D096 stacks -> `0` verified ETI).
- **Tightest APOGEE-2 limit:** `KEPLER1313` (`702.6146 kW` at `1.535 um`).

### Stream 3: Coherent Multi-Epoch Shift-Stack Drift (`DRIFT_V54`, `20` `N >= 4` Campaigns)
- Executed sub-threshold curved + periodic coherent shift-stacking across **`20` campaigns** (`6` D096 + `9` retroactive D095 Archive U + `5` retroactive D094 Archive T): `13,538` trajectories / `203,752,384` pixel-trajectory integrals.
- NaN-preserving template subtraction `fn_drift = 1.0 + (fn_raw - tpl_s)` eliminated unit-fill NaN step artifacts.

### Stream 4: JWST NIRISS/SOSS (`2` stars) & NIRSpec/G140H (`4` stars)
- Flattened 1D/2D `EXTRACT1D` spectra (`SIMP0136`, `HD59533`, `VHS1256B`, `BD601753`, `HD54306`, `GSPCP177D`).
- Deepest optical/NIR laser EIRP limit across the entire 425-star survey: **`SIMP0136` (`6.13 pc`, `SOSS_8500` `0.85 um`) = `0.039712 kW` (`39.71 W`)**.
- Tightest NIRSpec/G140H limit: **`VHS1256B` (`12.7 pc`, `G140H_10640_NDYAG` `1.064 um`) = `34.509826 kW`**, promoting `VHS1256B` into an extended NIRSpec+MIRI JWST bridge (and `BD601753` as a control multi-phase target).

## 3. Transparent Stage-2 Physical Triage & Forensic Resolutions
Stage-1 `v5_4_detector.py` remained **100% immutable**. All Stage-1 raw candidates were resolved via deterministic Stage-2 physical triage in `analyze.py`:
1. **`V5_4_CANDIDATE_LEDGER.csv` (`19` raw JWST hits -> `0` ETI):**
   - **J1 (`1` hit, `HD59533` `1.2325 um` CONTROL):** `STAGE2_VETO_JWST_NEGATIVE_CONTINUUM` (`med40 = -0.2389`, `p90 = -0.0286`).
   - **J2 (`3` hits, `SIMP0136` `0.7367 / 0.7368 / 2.1356 um`):** `STAGE2_VETO_JWST_SOSS_CROSS_ORDER_CONTAMINANT` (Orders 1/2/3 trace overlap cross-correlation `r = 0.9972–0.999985 >= 0.90`).
   - **J3 (`2` hits, `VHS1256B` `1.4436 / 1.4549 um`):** `STAGE2_VETO_JWST_DETECTOR_GAP_EDGE` (adjacent `NRS1–NRS2` detector chip-gap dropout `gap12 >= 7 px`).
   - **J4 (`1` hit, `VHS1256B` `1.1631 um`):** `STAGE2_VETO_JWST_UNFLAGGED_CR_ERROR_SPIKE` (`err_rat = 17.52 >= 4.0`).
   - **J5 (`12` hits: `BD601753` `9` CONTROL + `HD54306` `3` CONTROL):** `STAGE2_VETO_JWST_FIXED_SLIT_UNDERSAMPLING_WIGGLE` (`f/p90 = 1.003–1.104 < 1.12` and `med_err/med40 = 0.0018–0.0046 < 0.008`).
2. **`BLIND_DRIFT_V51` (`17` raw -> `0` ETI):**
   - `LP73158` (`7` raw) and `WOLF1069` (`10` raw) resolved via `V51_TOPO_AIRGLOW` (fixed terrestrial airglow `[O I] 5577.34`, `[O I] 6300.30`, `[Na I D1/D2] 5889.95/5895.92`, `OH 8344.59` with `|d_topo| <= 1.21 km/s` appearing shifted in rest-frame due to per-exposure CARACAL SERVAL RV offsets) and `V51_TELLURIC_TROUGH_ANTIPAIR` (`6911/7187 A` deep O2/H2O telluric troughs `fn < 0.75` depressing `tpl_s`).
3. **`DRIFT_V52` (`17` raw -> `0` ETI):** Vetoed via `DRIFT_G1_LSF_SHAPE` / `DRIFT_F1_SUBCONTINUUM`.
4. **`DRIFT_V54` Coherent Shift-Stack (`765` raw candidates across 20 campaigns -> `0` ETI):**
   - `640` `STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH`
   - `56` `STAGE2_VETO_SPURIOUS_EPOCH_SUBSET` (including `HNLIB 7193.71 A` TiO/H2O bump, `WOLF1069 5440.12 A`, `2M23025951` Control `16353.5/16355.7 A`, `2M23032370` Control `16894–16896 A` / `16349 A` where `>= 67%` of stacked power came from `<= 2` epochs)
   - `55` `STAGE2_VETO_OH_SKY_OR_TELLURIC` (exact-RV topocentric OH airglow and cross-epoch topocentric CO2 telluric hopping `trep = 4/4` on `2M17012756` at `15775–15788 A` and `2M23032370` at `16352–16905 A`)
   - `11` `STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND`
   - `3` `STAGE2_VETO_NON_LSF_SHAPE`

## 4. Synthetic Calibration Summary (`1,851` Trials; `37,911` Cumulative)
| Suite | Trials | Passed / Rejected |
|---|---:|---|
| `CALIBRATION_V54_SOFIA_EXES_180` | 180 | Laser `59/60`, ATRAN `40/40`, CR `40/40`, Natural `40/40` |
| `CALIBRATION_V54_COHERENT_SHIFT_STACK_240` | 240 | Curved `57/60`, Periodic `54/60`, Vetoes `120/120` |
| `CALIBRATION_V54_JWST_SOSS_G140H_120` | 120 | Laser `57/60`, HotPx `30/30`, Broad `30/30` |
| `CALIBRATION_G8_V54_120` | 120 | Isolated `38/40`, Shared/Topo Suppress `80/80` |
| `CALIBRATION_V54_RPCA_RARITY_180` | 180 | Isolated `59/60`, Shared/Topo Suppress `120/120` |
| `CALIBRATION_V54_AGNOSTIC_120` | 120 | Multi-scale recovery `120/120` |
| `DETECTOR_V54_G4G5_CALIBRATION_108` | 108 | True LSF `36/36`, Cosmic/Plateau Vetoes `72/72` |
| `INJECTION_RECOVERY_540` | 540 | Channel P `537/540` (`0.9944`) |
| `COMB_V4_1_CALIBRATION_162` | 162 | Comb recovery `54/54`, Confounders `108/108` |
| `KEPLERIAN_TRACK_CALIBRATION_81` | 81 | `K_PLANET` `81/81`, `TDIFF` FA `0/81` |
| **D096 Total** | **1,851** | **Cumulative D079–D096 = 37,911 trials** |

## 5. Multi-Event SETI Ellipsoid (`425` Stars)
- `15` stars satisfy `|ecliptic_lat| <= 2.0 deg` (Earth Transit Zone, including `MUGEM`, `SIMP0136`), and `36` stars lie within `|Delta t| <= 180 d` of SN 1987A, GW170817, or SN 2023ixf optical/IR ellipsoids (`0` ETI signals).
