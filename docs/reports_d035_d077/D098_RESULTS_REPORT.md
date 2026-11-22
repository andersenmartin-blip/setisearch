# Phase D098 (`V5.6`) Results Report — Panchromatic Echelle, Submm/THz, Mid-IR Gap-Closure & 30-Campaign Coherent Jerk-Drift SETI Survey

## 1. Executive Summary
- **Phase / Detector:** `D098` / `TECHNOSIGNATURE_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_AND_OPTICAL_COHERENT_JERK`
- **Verified ETI Detections:** **`0` verified ETI detections** across all **38 D098 target stars** (`99` real archival FITS exposures, `148.7684 h` = `535,566.224 s` integration; `26` control / `73` science exposures) and across the unified **`D079–D098` 473-star, 12.855-octave (`0.0905–670.69081 µm`)** panchromatic survey.
- **Determinism & Bit-Identity:** **`40/40` (`0` diffs)** exact SHA-256 bit-identity verified between `--from-full-inputs` (`99` real FITS files, `112,466,880 B` = `107.257 MiB` in `inputs_d098_v5_6/`) and offline `--from-bounded-inputs` decoding `bounded_inputs/d098_bounded_bundle.json.gz` (`17,809,870 B` = `16.985 MiB`, SHA-256 `468c3416778f37f335e990147dc3fecd41ae3281f64b6bbf9873dbe9b3396938`) plus Companion Archives `T/U/V/W`.
- **Independent Audit & Visual Verification:** Pure-stdlib `/usr/bin/python3 -S audit.py` (`16/16 PASS`), radiometric identity `C12` `max_rel_err = 0.0000000066 < 0.002` across `159/159` `EIRP_UPPER_LIMITS_D098.csv` rows, and `VISUAL_REVIEW.json` `PASS (6/6)` across all 240-DPI PNG figures (`fig79`–`fig84`).

---

## 2. Prospective Lock Protocol & Cohort Provenance
- **Method Lock (`METHOD_LOCK.json`):** SHA-256 `47c7c08a538b6debb980904dafe47c39a50c3063f4ce05e86764a2bc1480b84f`, locked prospectively at `2026-11-22T11:45:30Z` (`LOCK_RECEIPT.json`). All `7` Stage-1 locked files (`v5_6_detector.py`, `build_cohort.py`, `download_inputs.py`, `FROZEN_COHORT_D098.csv`, `ORBITAL_CAMPAIGNS_AND_KINEMATICS.json`, `PRIOR_EXCLUSION_VERIFICATION.json`, `PRIOR_V5_5_PHASES_SNAPSHOT.json`) remain **100% unmodified** (`0` SHA-256 diffs).
- **Chronology Receipt (`FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`):** First archival download `GREAT.75_0050_Betelgeuse_OI_averaged` at `2026-11-22T11:46:01.694035+00:00` (`chronology_lag_seconds = 31.597 s >= 3.0 s`).
- **Prior Exclusion Verification (`PRIOR_EXCLUSION_VERIFICATION.json`):** `0` DP-ID overlaps across `2,884` prior DP-IDs and `507` excluded coordinates; minimum brand-new sky separation `5,479.85 arcsec`; minimum intra-D098 separation `28,592.13 arcsec`.
- **Cohort (`38` Stars / `99` FITS):**
  - `25` brand-new unique stars (`18` science incl. `5` exoplanet hosts harboring `6` confirmed planets: `70VIR`, `ALFARI`, `GJ3988`, `GJ4274`, `LHS1478`; and `7` new controls: `ETACAR`, `GJ1286`, `NGC4151`, `NGC6543`, `NGC6720`, `NGC7009`, `RAQR`), plus `4` new `<10 pc` targets (`GJ1286` `7.1767 pc` control; `GJ4274` `7.23556 pc` 2-pl.; `GJ2066` `8.939 pc`; `GJ3988` `9.9105 pc` 1-pl.).
  - `13` revisited bridge/control stars: `8` newly promoted science bridges (`FOMALHAUT`, `HD100546`, `HD141569`, `HD192310`, `HD219134`, `IRC10216`, `REDRECT`, `TAUBOO`), `4` deepened science bridges (`ABAUR`, `AUMIC`, `BETELGEUSE`, `BETPIC`), and `1` revisited control (`NGC7027`), totaling `8` control stars in D098.
  - **Exposures (`EXPOSURE_PROVENANCE_D098.csv`):** `SOFIA_GREAT` `27` cubes (`132.6879 h`), `ISO_SWS` `17` spectra (`8.9722 h`), `SOFIA_FORCAST` `35` 4-grism spectra (`2.1082 h`), and `CARMENES_VIS` `20` exposures (`5.0000 h`), totaling `99` inputs / `148.7684 h`.

---

## 3. Synthetic Calibration (`2,024 / 2,031` Passed, `41,973` Cumulative)
Across 11 prospectively locked `V5.6` calibration suites (`2,031` D098 trials; `41,973` cumulative `D079–D098`):
- `CALIBRATION_V56_SOFIA_GREAT_180.csv`: `180/180 (1.0000)` (`CLEAN_GREAT_BEACON` 60/60, `STANDING_WAVE_VETO` 40/40, `BROAD_MOLECULAR_VETO` 40/40, `SINGLE_CHAN_LO_VETO` 40/40)
- `CALIBRATION_V56_ISO_SWS_180.csv`: `180/180 (1.0000)` (`CLEAN_SWS_BEACON` 45/45, `GREENHOUSE_GAS_CCF` 45/45, `DYSON_VS_SILICATE_BB` 30/30, `STITCH_AND_GLITCH_VETO` 30/30, `NATURAL_LINE_DUST_VETO` 30/30)
- `CALIBRATION_V56_SOFIA_FORCAST_120.csv`: `120/120 (1.0000)` (`CLEAN_FORCAST_BEACON` 60/60, `ATRAN_TELLURIC_VETO` 30/30, `GLITCH_AND_PAH_VETO` 30/30)
- `CALIBRATION_V56_COHERENT_JERK_240.csv`: `240/240 (1.0000)` (`SUBTHRESH_CUBIC_JERK` 60/60, `SUBTHRESH_PERIODIC` 60/60, `STATIONARY_VETO` 40/40, `TRANSIENT_VETO` 40/40, `BERV_SKY_VETO` 40/40)
- `CALIBRATION_G8_V56_120.csv`: `117/120 (0.9750)`; `CALIBRATION_V56_RPCA_RARITY_180.csv`: `180/180 (1.0000)`; `CALIBRATION_V56_AGNOSTIC_120.csv`: `117/120 (0.9750)`; `DETECTOR_V56_G4G5_CALIBRATION_108.csv`: `108/108 (1.0000)`; `INJECTION_RECOVERY_540.csv` (`pass_p`): `539/540 (0.9981)` (`M1_5320` `135/135`, `M2_6328` `134/135`, `M3_8082` `135/135`, `M4_8800` `135/135`); `COMB_V4_1_CALIBRATION_162.csv`: `162/162 (1.0000)`; `KEPLERIAN_TRACK_CALIBRATION_81.csv`: `81/81 (1.0000)` (`0` `T_DIFF` FA).

---

## 4. Stream-by-Stream Science Findings
### 4.1 Stream 1A — `SOFIA_GREAT` Super-THz Heterodyne (`12` Stars, `27` Cubes)
- `23` raw peaks (`20` `G5_GREAT_LO_SPUR_1CHAN` incl. `ETACAR` `1381.665 GHz` / `SNR=460.903`, `2` `G5_GREAT_BROAD_MOLECULAR` incl. `BETELGEUSE` `[OI]` `4744.782663 GHz` at `63.1836 µm` with `SNR=42.212` and thermal wind `FWHM=11.937 km/s`, `1` `G2_GREAT_STANDING_WAVE_RIPPLE`) $\rightarrow$ `0` `qualified_v56` $\rightarrow$ **`0` verified ETI**.
- Tightest 10 m beamed EIRP limit: **`19,268,981.04 kW` (`19.27 GW`)** on `HD141569` (`GREAT_OI_63UM`, `63.1928 µm`), followed by `DGTAU` (`31,708,029.65 kW`) and `IRC10216` (`33,660,690.62 kW`).

### 4.2 Stream 1B — `ISO_SWS` Continuous Mid-IR Gap-Closure (`17` Stars, `2.36–45.39 µm`)
- Continuous 12-segment coverage (up to `49,279` bins on `AUMIC`) yielded `52` raw peaks (`42` `G5_SWS_BROAD_DUST_PAH` led by `NGC6543` `10.508 µm` `[S IV]` `SNR=999.16`, `10` `G2_SWS_SEGMENT_STITCH_EDGE`) $\rightarrow$ `0` `qualified_v56`, **`0/102` 6-gas (`SF6, CFC11, CFC12, NO2, NH3, C2H6`) CCF detections**, **`0` silicate-free Dyson sphere candidates** (silicate features separated at `691.384σ` on `ETACAR`, `487.01σ` on `MUCEP`, `182.392σ` on `BETPIC`, `83.407σ` on `AUMIC`), and **`0` verified ETI**.
- Tightest 10 m EIRP limit: **`2,781.39 kW`** on `HD219134` (`SWS_3P5UM`, `3.5000 µm`), followed by `AUMIC` (`3,412.88 kW`) and `HD192310` (`5,046.42 kW`).

### 4.3 Stream 1C — `SOFIA_FORCAST` 4-Grism Dust & Dyson Search (`11` Stars, `35` Spectra)
- `33` raw peaks (`8` `G5_FORCAST_1PX_GLITCH`, `7` `G2_FORCAST_BASELINE_ARTIFACT`, `7` natural nebular lines [`SIII_18_71`, `SIII_33_48`, `SIV_10_51`, `ArIII_8_99`, `OIV_25_89`, `HI_Pf_alpha`], `6` `G2_FORCAST_ATRAN_TELLURIC`, `4` `G5_FORCAST_BROAD_PAH_SILICATE`, `1` `G6_FORCAST_TELLURIC_COINCIDENCE`) $\rightarrow$ `0` `qualified_v56`, `0` Dyson excess $\rightarrow$ **`0` verified ETI**.
- Tightest 10 m EIRP limit: **`21,388,408.73 kW` (`21.39 GW`)** on `HD166191` (`FOR_G063`, `6.5290 µm`), followed by `HD113766` (`43,673,421.59 kW`, `FOR_G111`).

### 4.4 Stream 2 — `CARMENES_VIS` 4-Gen, Orbits `#141–#143`, & `COMB_V4_1` (`5` Stars, `20` Exposures)
- **4-Generation Veto Cascade (`FOUR_GEN_BENCHMARK_D098.csv`):** `514 G1 -> 486 G2 -> 484 G3 -> 2 G45 -> 0 G6 -> 0 G7 -> 0 G8 -> 0 ETI`.
- **Orbital `K_PLANET` Campaigns (`#141–#143`; `143` cumulative):** `GJ 4274 b` (`P=1.6339 d`, `Kp=102.066 km/s`, `dv=154.282 km/s`), `GJ 3988 b` (`P=6.9442 d`, `Kp=63.497 km/s`, `dv=78.971 km/s`), and `LHS 1478 b` (`P=1.94953941 d`, `Kp=104.513 km/s`, `dv=126.482 km/s`) all yield `0` `K_PLANET` hits and **`0` ETI**.
- **`COMB_V4_1` Sweep (`CARM_GREEN/RED/FARRED`):** `1,214,360` configurations (`242,872` × 5) $\rightarrow$ `8,921` V4 raw $\rightarrow$ `100` `c41` (`GJ1286: 16`, `GJ2066: 63`, `GJ3988: 13`, `GJ4274: 8`, `LHS1478: 0`) $\rightarrow$ `100/100 STAGE2_VETO_MDWARF_TIO_FOREST` $\rightarrow$ **`0` ETI** (`458` cumulative stacks across `D079–D098`, `212` candidate rows $\rightarrow$ `0` ETI).
- **Tightest D098 Optical Limit:** **`0.45553819 kW` (`455.54 W`)** on `GJ1286` (`M1_5320`), followed by `GJ4274` (`0.8221 kW`) and `GJ3988` (`0.9543 kW`).

### 4.5 Stream 3 — `DRIFT_V56` 30-Campaign Coherent 3D Jerk Search (`2.299B` Pixel Integrals)
- Spanning **`30` `N >= 4` campaigns** (`5` live D098 `CARMENES_VIS` + `25` retroactive campaigns from Companion Archives `W/V/U/T` verified against `METHOD_LOCK.json`), `DRIFT_V56` evaluates `38,226` trajectories and **`2,298,916,322` pixel-trajectory integrals**, recovering `8,344` raw survivors (`5,198` jerk + `3,141` curved + `5` periodic).
- Deterministic Stage-2 physical triage resolves **all `8,344 -> 0 ETI`**:
  - `6,948` `STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH`
  - `714` `STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND` (including **`CSS56_D096_WOLF1069_931`** at `6524.57364 Å` `CARMENES_VIS`, where `ep0` carried a `+8.55 km/s` `SERVAL` RV outlier displacing a `1.2855×` TiO pseudo-continuum crest; exact center residuals `z_center = [3.33, 3.93, 0.35, 1.87]` give `zc_unw = 4.74 < 5.0`)
  - `675` `STAGE2_VETO_OH_SKY_OR_TELLURIC`
  - `6` `STAGE2_VETO_NON_LSF_SHAPE`
  - `1` `STAGE2_VETO_LOWCONT_CR_RINGING` (**`CSS56_D097_GJ1005_003`** at `4239.30468 Å` `ESO_FEROS`, where native blue flux `4200–4280 Å` drops to continuum `SNR = 1.97–2.95` with rolling `σ = 0.1185` and `50.3×` epoch excess dynamic range)

### 4.6 Stream 4 — Unified Panchromatic Synthesis (`D079–D098`: `473` Stars, `12.855` Octaves)
- **Total Survey Census:** **`473` unique stars** (`363` science [`210` hosts / `405` planets] + `110` verified zero-planet controls) across **`33` spectrographs / `51` spectral arms** spanning **`12.855` unbroken octaves (`0.0905–670.69081 µm`)**, `2,700` archival exposures (`921.5744 h`), `41,973` synthetic calibration trials, `423,988` Legacy V2 false alarms eliminated, `143` orbital campaigns, `458` all-sky comb stacks, `30` `DRIFT_V56` campaigns, and **`0` verified ETI detections**.
- **Solar Neighborhood (`<10 pc`):** **`173` unique stars** (`129` science [`61` hosts / `121` planets] + `44` controls), median 10 m EIRP limit **`1.4558 kW`**.
- **Panchromatic Bridges & Multi-Event Ellipsoid:** **`66` calibrated science bridge stars** (`780` cells; `68` multi-phase targets including `2` revisited controls `BD601753` and `NGC7027`), **`473`-star Ellipsoid** (`19` ETZ targets including `HD166191` `β=-0.14932°` and `IRC10216` `β=-0.0102°`; `36` targets within `|Δt| <= 180 d`), **`23/23 (100%)` Parkes/GBT radio-echelle closure**, and **`150` agnostic multiscale rows (`0` ETI)**.
