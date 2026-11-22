# Phase D099 (V5.7) Scientific Results Report

**Phase ID:** `D099` (`TECHNOSIGNATURE_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT`)  
**Stage-1 Seal (UTC):** `2026-11-22T16:13:51.745287+00:00` (`inputs_dir_exists_at_seal = false`)  
**First Science Download (UTC):** `2026-11-22T16:13:56.217014+00:00` (`chronology_lag_seconds = 7.051 s`)  
**Primary Result:** **`0` Verified ETI Detections** across **`516`** unique stellar systems, **`36`** spectrographs (**`57`** spectral arms), and **`13.919` unbroken octaves (`0.0905–1,401.36089 µm`)**

---

## 1. Cryptographic Sealing, Prior Exclusion & Reproducibility

- **`LOCK_RECEIPT.json` SHA-256:** `228f81060b27685e38ac2f3a4baadfb6140c237a02b96f3e8ca8d320ea76984b`
- **`METHOD_LOCK.json` SHA-256:** `a7d41c95620b2f550767f9920438a7276db9232d9293d51b294e0df2bcba7bf0`
- **`v5_7_detector.py` (Stage-1 immutable) SHA-256:** `8ec1f811f8ea807395aa2e3fddd79fe3bf716a520543965281fed0fea12ff23d`
- **Prior Exclusion Verification (`C001–C037 + D001–D098`):** `539` prior coordinates, `2,983` prior `dp_ids` (+ `12` format-check excluded `dp_ids`), `0` `dp_id` overlaps, minimum brand-new sky separation `1,660.20 arcsec`, minimum intra-D099 sky separation `6,668.96 arcsec`.
- **Raw Cohort & Bounded Bundle:** `97` FITS exposures (`122,705,280 B` = `117.021 MiB`; `76,068.51 s` = `21.1301 h`) compacted losslessly/band-bounded into `bounded_inputs/d099_bounded_bundle.json.gz` (`11,554,273 B` = `11.019 MiB <= 18.5 MiB`, SHA-256 `abbc808357061ae63a084b2e11b4f61771845d85117f4e712fd4316a8b87c8b4`).
- **Clean Bit-Identity Verification (`analyze.py --from-bounded-inputs`):** `40/40` result CSV/JSON files reproduced with `0` byte/SHA-256 differences.

---

## 2. Phase D099 Cohort Composition & Bridge Promotions

- **D099 Cohort (`60` stars, `97` exposures):**
  - **`43` Brand-New Unique Systems:** `36` Science + `7` Zero-Planet Controls (breaking the **500-star** milestone: `473 + 43 = 516` unique stars).
  - **`17` Revisited Systems:**
    - `12` Science (`9` deepened prior bridges: `55CNC`, `61CYGB`, `ABAUR`, `BETELGEUSE`, `DXCNC`, `HD115617`, `HD219134`, `IRC10216`, `OCETI`; `+3` newly promoted prior stars: `HD163296`, `RCAS`, `VYCMA`).
    - `5` Controls (`NGC7027` + `4` newly multi-phase controls: `AFGL2688`, `CRL618`, `HD109358`, `HD114710`).
  - **`+2` Intra-D099 Bridges:** `RLEO` and `TXCAM` observed jointly by JCMT 230 GHz and SOFIA/EXES.
  - **Net Bridge Expansion:** `+5` newly promoted Science bridges (`HD163296`, `RCAS`, `VYCMA`, `RLEO`, `TXCAM`), raising cumulative totals from `66` to **`71` Pan-Chromatic Science Bridges** (`827` bridge cells) and **`77` multi-phase targets** (including `6` revisited controls).
  - **New Solar-Neighborhood (`<10 pc`) Targets:** `+2` brand-new (`EZAQR` at `3.4060 pc`, `61UMA` at `9.5762 pc`), raising `<10 pc` census from `173` to **`175` stars**.

---

## 3. V5.7 Synthetic Calibration Scorecard (`2,151` Trials; Cumulative `44,124`)

| Suite | Passed / Trials | Rate | Notes |
| --- | ---: | ---: | --- |
| `CALIBRATION_V57_JCMT_MM_180` | `180 / 180` | `1.0000` | Clean mm beacon (`60/60`), standing wave, broad molecular, 1-ch LO (`40/40` each) |
| `CALIBRATION_V57_SOFIA_EXES_180` | `179 / 180` | `0.9944` | Clean laser (`59/60`), ATRAN artifact, 1-px CR, natural atlas line (`40/40` each) |
| `CALIBRATION_V57_IRTF_SPEX_180` | `180 / 180` | `1.0000` | Clean SpeX beacon (`60/60`), telluric blackout, 1-px glitch, broad bandhead (`40/40` each) |
| `CALIBRATION_V57_KEPLERIAN_JERK_300` | `300 / 300` | `1.0000` | Multi-rev 2–10 yr Keplerian `60/60` (vs. Taylor baseline **`36/60 = 0.6000`**), cubic jerk `60/60`, short periodic `60/60`, stationary/transient/BERV vetos `40/40` each |
| `CALIBRATION_G8_V57_120` | `117 / 120` | `0.9750` | Gate G8 optical vetting |
| `CALIBRATION_V57_RPCA_RARITY_180` | `179 / 180` | `0.9944` | RPCA rarity Gate G7 |
| `CALIBRATION_V57_AGNOSTIC_120` | `120 / 120` | `1.0000` | Multi-scale agnostic matched filtering |
| `DETECTOR_V57_G4G5_CALIBRATION_108` | `108 / 108` | `1.0000` | Gates G4/G5 shape & artifact vetos |
| `INJECTION_RECOVERY_540` | `538 / 540` | `0.9963` | 6-band ESO UVES/HARPS empirical recovery (`90/90` in 5 bands, `89/90` in `H2_5320`) |
| `COMB_V4_1_CALIBRATION_162` | `161 / 162` | `0.9938` | `COMB_V4_1` laser frequency comb vetting |
| `KEPLERIAN_TRACK_CALIBRATION_81` | `81 / 81` | `1.0000` | Multi-epoch orbital track recovery |

---

## 4. Stream-by-Stream Observational & Vetting Results (`0` Verified ETI)

### Stream 1A: JCMT Submillimeter & Millimeter Heterodyne (`18` Stars, `23` Cubes: `5` HARP + `18` 230 GHz)
- **Spectral Frontier:** Extends panchromatic coverage to **`213.93 GHz = 1,401.36089 µm`** (`OCETI` `JCMT_MM_230GHZ`), spanning **`13.919` unbroken octaves** from FUSE Lyman UV (`0.0905 µm`).
- **Triage (`23` Raw Peaks -> `0` Qualified -> `0` Verified ETI):** `21` `G2_JCMT_STANDING_WAVE_RIPPLE`, `1` `G3_JCMT_MOLECULAR_ATLAS:12CO_J2-1` (`O Ceti` `12CO J=2-1` emission at `79.8 sigma`), `1` `G5_JCMT_BROAD_MOLECULAR_ENVELOPE`.
- **Tightest 10-m Equivalent Beam EIRP Limits:** `JCMT_HARP` `LKCA15` = `2,040,500.05755668 kW` (`JCMT_HARP_850UM`); `JCMT_MM_230GHZ` `HD163296` = `4,222,791.0855968 kW` (`JCMT_UU_1300UM`).

### Stream 1B: SOFIA/EXES High-Resolution Mid-IR Echelle (`13` Stars, `5.70–25.31 µm`)
- **Triage (`88` Raw Peaks -> `0` Qualified -> `0` Verified ETI):** `82` `G5_EXES_BROAD_FEATURE` (ro-vibrational emission/absorption features incl. `RLEO`), `5` `G5_EXES_1PX_CR`, `1` `G4_EXES_LSF_FAIL`.
- **Tightest 10-m Equivalent Beam EIRP Limits:** `MUUMA` = `33,883.11020633 kW` (`EXES_7UM`); `ABAUR` = `582,497.57 kW` (`EXES_18UM`).

### Stream 1C: IRTF/SpeX Near-IR & QCL Window Survey (`26` Stars, `0.80–5.43 µm`)
- **Triage (`1` Raw Peak -> `0` Qualified -> `0` Verified ETI):** `1` `G6_SPEX_TELLURIC_COINCIDENCE`.
- **Tightest 10-m Equivalent Beam EIRP Limits:** `DXCNC` = `57.04399686 kW` (`SPEX_J_125UM`); `EZAQR` = `180.818377 kW` (`SPEX_J_125UM`); `HD219134` = `2,086.67 kW` (`SPEX_QCL_350UM`).

### Stream 2 & Stream 3: ESO UVES/HARPS Optical 4-Gen & 36-Campaign `DRIFT_V57_KEPLERIAN_JERK`
- **ESO 4-Gen Optical (`6` stars, `35` exposures):** `11` raw `G1` seeds -> `11` `G2` -> `11` `G3` -> `2` `G4/G5` -> `1` `G6` -> `0` `G7` -> `0` `G8` -> **`0` ETI**.
- **Orbital Campaigns (`#144–#145`, `145` Cumulative):** `GJ422` (`P = 20.129 d`, `K_p = 55.158 km/s`, `6` UVES epochs, `10.8 yr`) best UVES limit `40.18792826 kW` (`U2_5320`); `HD113538` (`P = 663.2 d`, `K_p = 20.419 km/s`, `5` HARPS epochs, `21.1 yr`) best HARPS limit `104.46713649 kW` (`H1_4100`).
- **Empirical Stellar RVs (`STAR_RV_SUMMARY_D099.csv`):** `GJ1009` `16.5843 (0.3599)` km/s, `GJ1046` `63.1879 (1.5585)` km/s, `GJ3082` `6.2396 (0.4294)` km/s, `GJ422` `-50.7715 (8.8846)` km/s, `HD113538` `39.6141 (0.1668)` km/s, `HD98800` `9.4897 (3.5535)` km/s.
- **36-Campaign Coherent Keplerian + 3D Jerk Search (`6` D099 + `30` Retroactive D094–D098):** `323` epochs, `56,270` trajectories evaluated, `3,566,447,968` pixel integrals, `47,580` Keplerian polishes, **`10,852` raw coherent survivors** (`6,133` cubic jerk, `2,984` Keplerian coherent, `1,234` curved, `269` linear, `232` periodic) cleanly eliminated (`8,586` subphotospheric trough, `1,293` OH sky/telluric, `967` stationary/absorption band, `2` low-continuum CR ringing, `2` spurious epoch subset, `2` non-LSF shape) -> **`0` Verified ETI**.
- **Comb, Ellipsoid & Agnostic Closure:** `1,548,664` D099 `COMB_V4_1` configs -> `0` candidates (`464` cumulative stacks, `0` ETI); `89,899` D099 V2 false alarms eliminated (`513,887` cumulative); `281` multiscale agnostic survivors -> `0` ETI; `516`-star multi-event ellipsoid (`48` ETZ, `36` `<= 180 d`) -> `0` ETI.

---

## 5. Unified D079–D099 Synthesis (`516` Unique Stars, `13.919` Octaves)

| Metric | Value |
| --- | --- |
| Phase Range | `D079–D099` (`21` phases) |
| Spectrographs / Spectral Arms | `36` spectrographs / `57` spectral arms |
| Unbroken Spectral Span | `0.0905–1,401.36089 µm` (**`13.919` octaves**) |
| Unique Stellar Systems | **`516`** (`399` Science [`214` planet hosts, `411` confirmed exoplanets] + `117` Controls) |
| Solar Neighborhood (`<10 pc`) | **`175` stars** (`131` Science [`61` hosts, `121` planets] + `44` Controls); median **`1.4627 kW`** |
| Panchromatic Science Bridges | **`71` Science bridges** (`827` cells) + `6` revisited controls = `77` multi-phase targets |
| Cumulative Exposures & Integration | `2,797` exposures / `942.7045 h` |
| Cumulative Calibration & False-Alarm Closure | `44,124` trials; `513,887` V2 false alarms -> **`0` Verified ETI** |

---

## 6. Visual Figures (`results/figures/`, `240 DPI`, `VISUAL_REVIEW.json = PASS (6/6)`)

| Figure File | Size (B) | Subject |
| --- | ---: | --- |
| `results/figures/fig85_d099_jcmt_mm_heterodyne_18stars.png` | `497,354` | JCMT mm heterodyne spectra (`O Ceti 12CO J=2-1` veto), `180/180` cal, veto funnel, 18-star limits |
| `results/figures/fig86_d099_sofia_exes_midir_13stars.png` | `615,860` | SOFIA/EXES `R Leo` vs. ATRAN model, `179/180` cal, `88->0` funnel, 13-star limits |
| `results/figures/fig87_d099_irtf_spex_nir_qcl_26stars.png` | `537,971` | IRTF/SpeX `0.80–5.43 µm` SEDs & QCL windows, `180/180` cal, J/H/K/QCL/M limits (`DX Cnc 57.0 kW`) |
| `results/figures/fig88_d099_keplerian_jerk_36campaigns.png` | `454,020` | `300/300` vs. `60%` multi-rev Taylor baseline, Orbits `#144–#145`, `10,852` coherent hits -> `0` ETI |
| `results/figures/fig89_d099_panchromatic_516stars_13p92octaves.png` | `746,046` | `13.919`-octave 36-spectrograph frontier, `516`-star sky map, `175 <10 pc` (`1.4627 kW` med), 11-suite scorecard |
| `results/figures/fig90_d099_bridge_71stars_and_milestone_500plus.png` | `271,934` | `14` D099 bridge stars (`+5` promoted -> `71`) and milestone growth across `500` to `516` stars |
