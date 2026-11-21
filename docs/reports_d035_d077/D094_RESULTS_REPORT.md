# SETI Phase D094 (V5.2) Results Report: Multi-Epoch Linear Drift Chaining, SDSS APOGEE-2, ESO CRIRES+ Y/J/H, and JWST MIRI LRS + NIRSpec G395H

**Phase ID:** `D094` (`TECHNOSIGNATURE_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS`)  
**Prospective Stage-1 Lock:** `2026-11-21T12:52:10Z` (`METHOD_LOCK.json` SHA-256 `c99ed5b6c525c1a98b9e7f949f93680cc1fd3719335c7154c0edf609caae3d0c`, `inputs_d094_v5_2_exists: false`)  
**First Science Download:** `2026-11-21T12:52:28Z` (`+18.414 s >= 3.0 s` pre-download lock lag)  
**Verified Technosignature Detections:** **0 ETI**

---

## 1. Cohort, Facility Coverage & Prior Exclusion

- **Unique Targets in D094:** `30` stars (`25` science, `5` astrophysical/extragalactic controls: `2M23025951`, `2M17012756`, `10LEP`, `AZV175`, `SK70116`), comprising `23` brand-new unique stars (`3` within `10 pc`: `GJ268`, `GJ1125`, `WISE1049AB`) plus `7` revisited panchromatic bridges (`HD42581`, `AUMIC`, `GJ9827`, `55CNC`, `HD3651`, `HD209458`, `GJ1132`) and `1` intra-D094 multi-facility bridge (`HNPEG`, observed with CRIRES+ H, JWST MIRI LRS, and JWST NIRSpec G395H). Four targets were newly promoted to panchromatic optical+IR bridges in the unified ledger: `GJ9827`, `HD3651`, `GJ1132`, and `HNPEG`.
- **Zero-Overlap Verification:** `0` shared `dp_id`s against `2,612` prior exposures and `409` prior coordinates (`C001–C037` + `D001–D093`), with minimum sky separation `8,209.21 arcsec` (`>= 300 arcsec`) for all brand-new D094 stars.
- **Ingested Spectra & Size Caps:** `53` raw FITS files (`92.642 MiB` / `97,142,400 B <= 98.0 MiB`) unpacking into `75` physical exposures/visit spectra (`50.1222 h` integration) and `1` deterministic bounded bundle (`d094_bounded_bundle.json.gz`, `13.62 MiB < 22.0 MiB`):
  - **SDSS APOGEE-2 (`H` band, `R = 22,500`, `1.51–1.70 um`):** `8` FITS (`32` individual-visit spectra, `8` stars).
  - **ESO CRIRES+ (`Y/J/H` bands, `R = 43,000–86,000`, `0.95–1.80 um`):** `31` FITS (`31` exposures across `13` unique stars / `15` star-band subsets).
  - **JWST MIRI LRS (`P750L`, `R ~ 100`, `5.0–12.0 um`):** `10` FITS (`10` exposures across `10` targets).
  - **JWST NIRSpec G395H (`R = 2,700`, `2.87–5.14 um`):** `4` FITS (`2` paired `nrs1+nrs2` spectra across `2` targets: `CWISEPJ1935`, `HNPEG`).

---

## 2. Primary Search Streams (All 0 Verified ETI)

### 2.1 Four-Generation Narrowband & `G8_V52` Cascade
Across `SDSS_APOGEE2` (`T=632,744`, `P=164,865`) and `ESO_CRIRES` (`T=1,342,834`, `P=747,637`), `947` legacy V2 false alarms were eliminated and the 4-generation cascade reduced `81` `G1` seeds to **0 surviving candidates**:
- `G1 LSF Seeds`: `81` (`APOGEE2_H=27`, `CRIRES_H=29`, `CRIRES_J=1`, `CRIRES_Y=24`)
- `G2 Airglow/OH`: `67` -> `G3 Chromospheric`: `64` -> `G4+G5 Native PSF`: `19` -> `G6 Topocentric Sparse`: `16` -> `V5.0 G7 RPCA+Rarity`: `1` (`CRIRES_Y`) -> `V5.2 G8_V52 Final`: **0** (**0 ETI**)

### 2.2 Multi-Epoch Linear Drift-Rate Chaining (`DRIFT_V52_MULTIEPOCH`, 44 `N >= 3` Campaigns)
Applying `DRIFT_V52_MULTIEPOCH` across all `N >= 3`-epoch campaigns evaluated `3,916` triplet/chain trajectories:
- **D094 (`13` campaigns: `8` APOGEE-2, `5` CRIRES+):** `0` raw drift tracks, **0 surviving ETI candidates**.
- **Retroactive D091 Archive Q (`SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip`, `31` multi-night stars across FEROS, GIRAFFE `HR09B/HR10/HR11/HR13`, and X-Shooter 3-arm):** `3` raw tracks (`G06410702` `HR09B` `raw=1->0`; `G115` `HR13` `raw=2->0`; `G2421` `0->0`), all vetoed by Tier-2 LSF/F1 confirmation (`DRIFT_G1_LSF_SHAPE`) with **0 surviving ETI candidates**.

### 2.3 JWST MIRI LRS (`10` Stars) & NIRSpec G395H (`2` Stars) Union-Excluded Molecular CCF
- **JWST MIRI LRS (`CF4`, `C2F6`, `SF6`, `NF3`, `CFC-11` vs `NH3`, `CH4`, `H2O`):** `0` technosignature detections across `10` targets (`WISE1049AB`, `WD0806B`, `HNPEG`, `ROSS19B`, `GUPSCB`, `HD106906B`, `HD42581`, `GJ1132`, and SMC/LMC hot B-star controls `AZV175` and `SK70116`). Natural brown-dwarf/companion `NH3` triggers appeared on `HD42581` (`nh3_lrs_conf_sigma=+6.487`) and `HNPEG` (`+7.306`), while `GUPSCB` (`sf6_sigma=+6.916` vs `max_confounder_sigma=3.066`) failed joint validation (`detected_molecules=""`), and `ROSS19B` (`med_cont_snr=-0.72`) was bounded via its `3 * sigma_err` subcontinuum floor (`subcontinuum_nd=True`).
- **JWST NIRSpec G395H (`NO2`, `N2O`, `CH4/C2H6`, `CO/13CO` vs `CO2 4.26 um`, `H2O`):** `0` detections across `CWISEPJ1935` (`ch4_c2h6_sigma=-4.542` auroral `CH4`) and `HNPEG` (`co2_4p26_conf_sigma=+6.977`).

### 2.4 Keplerian Orbital Campaigns `#118–#125`, `COMB_V4_1`, Agnostic Filter & Multi-Event Ellipsoid
- **Orbital Campaigns `#118–#125` (`ESO_CRIRES`):** `TOI-674 b`, `TOI-942 b`, `WASP-76 b`, `AU Mic b`, `GJ 9827 c`, `55 Cnc e`, `HD 3651 b`, and `HD 209458 b` (`406,846` `T_DIFF`/`K_PLANET` elements) yielded **0** `K_PLANET` candidates.
- **Laser Frequency Comb (`COMB_V4_1`):** `1,071,376` comb configurations searched across `23` star-band subsets -> **0** candidates; unified all-sky comb ledger reaches `424` stacks (`0` ETI).
- **Agnostic Multi-Scale Wavelet/Boxcar Filter:** `100` natural absorption/emission survivors across `5` targets (`51PEG`, `55CNC`, `AUMIC`, `HD190360`, `HNPEG`; `1` positive chromospheric peak on `AUMIC`), **0 ETI**.
- **Multi-Event SETI Ellipsoid (`373` stars):** Evaluated against `SN 1987A`, `GW170817`, and `SN 2023ixf`: `10` Earth Transit Zone (`|beta| <= 0.265 deg`) stars and `34` stars within `|dt_sync| <= 180 d` (led by `HD111031` at `5.3 d`, `2M12392658` at `52.3 d`, and `WOLF359` at `67.6 d`).

---

## 3. Radiometric Upper Limits (`108` Cells) & Unified `373`-Star Census

- **Phase D094 `108` Star-Band `10 m` Directed Laser EIRP Limits (by facility):**
  - Overall Best D094 (`JWST_NIRSPEC_G395H`): **`CWISEPJ1935` `N1_33200` = `0.142383 kW` (`142.38275 W`)**
  - `JWST_MIRI_LRS`: **`WISE1049AB` (1.996 pc) `ML1_58000` = `0.205331 kW`**
  - `SDSS_APOGEE2`: **`2M12392658` `A4_16750` = `4.353531 kW`**
  - `ESO_CRIRES`: **`TOI674` `C3_15500` = `18.800222 kW`**
- **Unified `D079–D094` Synthesis:** `373` unique stars (`286` science / `181` planet hosts / `364` confirmed exoplanets + `87` controls) across `23` spectrographs, `29` spectral arms, and `8.273` octaves (`0.33–12.0 um`); `156` stars within `10 pc` (`1.48898 kW` median `10 m` EIRP limit); `41` panchromatic optical+IR bridges (`664` cells); `2,238` exposures (`702.8369 h`); `34,149` synthetic calibration trials; `303,145` V2 false alarms eliminated; `125` orbital campaigns; `424` all-sky comb stacks; **0 verified ETI**.

---

## 4. Stage-2 Pipeline Notes & `1,741`-Trial Calibration Validation

Stage-1 `v5_2_detector.py` remained cryptographically untouched (`SHA-256 ca5d46a7bde938a7d8d037183005a65f153fa551ec1233e112b656eb7f62a425`). All Stage-2 orchestration fixes reside strictly in `analyze.py` and are logged in `SUMMARY.json["stage2_pipeline_notes"]`:
1. **`DRIFT_V52_MULTIEPOCH` Rolling-MAD & Tier-2 LSF/F1 Veto:** Replaced global-MAD scaling with `_compute_rolling_mad_1d(win_bins=512)` plus supraphotospheric floor (`fn >= 1.01`) prior to `scan_multiepoch_drift_chaining_v52`, grouped Archive Q D091 peers by `grating_family` with `>= 3850 A` blue-edge trim and cross-star RPCA, and applied Tier-2 multi-epoch LSF/F1 confirmation (`snr >= 4.5`, `cos >= 0.80`, `0.55 <= fwhm_ratio <= 1.85`, `fn_pk3 >= 1.05`). This suppressed photospheric Br15 wing residuals on control SB1/SB2 `2M23025951` (`0 -> 0`) and cosmic-ray / single-pixel artifacts in Archive Q D091 (`G06410702` `1 -> 0` and `G115` `2 -> 0`, with `G2421` already reduced to `0 -> 0`).
2. **JWST MIRI LRS Hampel 1-px Despike & Subcontinuum Floor:** Applied a `7`-px running-median / `11`-px MAD outlier despike (`4.5 * mad` on `1.2x` narrow neighbors) to eliminate unflagged `DQ=0` single-pixel artifacts such as SMC control `AZV175` (`3` pixels removed at `11.7883 um`), and bounded low-SNR `ROSS19B` (`med_cont_snr = -0.72`) via its `3 * sigma_err` flux floor (`subcontinuum_nd=True`).
3. **`1,741` Synthetic Calibration Trials (`10` Suites, `0.00%` FP Across All Veto Suites):**
   - `CALIBRATION_V52_MULTIEPOCH_DRIFT_150`: `59/60 (0.9833)` laser recovery; `30/30` stationary, `30/30` transient, `30/30` BERV-sky vetoed (`90/90`).
   - `CALIBRATION_V52_MIRI_LRS_CCF_160`: `77/80 (0.9625)` 5-gas recovery; `80/80` confounder veto.
   - `CALIBRATION_V52_NIRSPEC_CCF_120`: `60/60 (1.0000)` recovery; `60/60` confounder veto.
   - `CALIBRATION_V52_PATCH_NOVELTY_120`: `40/40 (1.0000)` isolated pass; `40/40` shared + `40/40` topo veto.
   - `CALIBRATION_V52_RPCA_RARITY_180`: `58/60 (0.9667)` isolated recovery; `60/60` shared + `60/60` topo veto.
   - `CALIBRATION_V52_AGNOSTIC_120`: `120/120 (1.0000)` multiscale recovery.
   - `DETECTOR_V52_G4G5_CALIBRATION_108`: `36/36` true LSF pass; `36/36` cosmic + `36/36` plateau rejection (`108/108`).
   - `INJECTION_RECOVERY_540`: `540/540 (1.0000)` Channel P `>= 8 sigma` recovery.
   - `COMB_V4_1_CALIBRATION_162`: `54/54 (1.0000)` comb recovery; `0/54` dense molecular forest FA; `0/54` topocentric sky-comb FA (`108/108` confounders vetoed).
   - `KEPLERIAN_TRACK_CALIBRATION_81`: `81/81 (1.0000)` `K_PLANET` orbital recovery (`0` `T_DIFF` false alarms).
