# Phase D097 (`V5.5`) Panchromatic Technosignature Survey — Final Results Report

**Pipeline:** `TECHNOSIGNATURE_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_AND_HIGHRES_OPTICAL_COHERENT_DRIFT`  
**Date (UTC):** 2026-11-22  
**Author:** Martin Andersen (MSc Astrophysics, University of Copenhagen)  
**Verified ETI Detections (D097 & Cumulative D079–D097):** **0 / 448 systems**

---

## 1. Executive Summary & Prospective Lock Chain

Phase **D097 (`V5.5`)** completes nineteen prospectively locked phases (**D079–D097**) of the unbroken space-Lyman to Herschel submillimeter/THz panchromatic technosignature survey, expanding wavelength coverage from `37.86356 um` (**8.709 octaves**) out to `670.69081 um` (**12.855 unbroken spectral octaves**, factor of `7,411x` in wavelength) across **30 spectrographs (42 spectral arms)** and **448 unique stellar systems**.

- **Stage-1 Chronology Lock:** `METHOD_LOCK.json` (SHA-256 `d3e43cb23f2932f1788c3a133fb3509fc02a9324dbadccde2329c2bc84483245`) was sealed in `LOCK_RECEIPT.json` at `2026-11-22T07:30:25Z`, **13.756 s strictly prior** to `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json` (`2026-11-22T07:30:39.075231+00:00`). All 7 Stage-1 files (`v5_5_detector.py`, `build_cohort.py`, `download_inputs.py`, `FROZEN_COHORT_D097.csv`, `ORBITAL_CAMPAIGNS_AND_KINEMATICS.json`, `PRIOR_EXCLUSION_VERIFICATION.json`, `PRIOR_V5_4_PHASES_SNAPSHOT.json`) remain **100% byte-for-byte unmodified** and chained via `IMPLEMENTATION_LOCK.json`.
- **Prospective Cohort & Zero Overlap:** **30 D097 stars** (`23` brand-new unique stars incl. `4` within `<10 pc`: `GJ 1005`, `GJ 536`, `GJ 680`, `GJ 877` + `6` newly promoted science bridges `AB Aur`, `Alpha Cen A`, `Antares`, `Betelgeuse`, `Mira`, `Procyon A` + `1` revisited control `NGC 7027`), comprising **78 archival inputs** (`125,447,432 B` = `119.636 MiB`, `21.1526 h` integration) across **6 facilities** (`HERSCHEL_HIFI`, `HERSCHEL_SPIRE_FTS`, `HERSCHEL_PACS`, `HST_STIS_E140H`, `ESO_FEROS`, `ESO_HARPS`). Zero overlap against `2,806` prior excluded `dp_id`s (`min_brand_new_sky_separation_arcsec = 6,931.98"`, `min_intra_d097 = 18,540.37"`).
- **Bounded Reproducibility & Audits:** `bounded_inputs/d097_bounded_bundle.json.gz` (`7.5355 MiB <= 22.0 MiB`, SHA-256 `05b9d096a76082f9b2bca30ab73a01329a20c1b40c651ce2a76bf0647626f41a`) reproduces **40/40 result files at 100% SHA-256 bit-identity (`0` diffs)** via `--from-bounded-inputs` and passes **16/16** pure-stdlib `/usr/bin/python3 -S audit.py` checks.

---

## 2. Synthetic Calibration Scorecard (`2,031` D097 Trials / `39,942` Cumulative)

| Calibration Suite | Trials | Result | Pass Rate | Notes |
| --- | ---: | --- | ---: | --- |
| `CALIBRATION_V55_HERSCHEL_HIFI_180` | 180 | 179 / 180 | 99.44% | `59/60` THz recovery; `40/40` SW, `40/40` broad mol, `40/40` single-ch LO veto |
| `CALIBRATION_V55_SPIRE_PACS_180` | 180 | 180 / 180 | 100.00% | `60/60` point beacon; `40/40` off-axis ring, `40/40` sinc, `40/40` PACS glitch |
| `CALIBRATION_V55_HST_STIS_E140H_120` | 120 | 120 / 120 | 100.00% | `60/60` FUV recovery; `30/30` hot-px/overlap, `30/30` chromo/geo veto |
| `CALIBRATION_V55_COHERENT_JERK_240` | 240 | 240 / 240 | 100.00% | `60/60` cubic jerk, `60/60` periodic; `40/40` stat, `40/40` trans, `40/40` BERV |
| `CALIBRATION_G8_V55_120` | 120 | 117 / 120 | 97.50% | Clean `bg_feats` PCA-kNN manifold novelty |
| `CALIBRATION_V55_RPCA_RARITY_180` | 180 | 180 / 180 | 100.00% | `SDSS_APOGEE2` `15200-15364 A` spacing alignment |
| `CALIBRATION_V55_AGNOSTIC_120` | 120 | 118 / 120 | 98.33% | Multi-scale Gaussian + top-hat (2..14 LSF) |
| `DETECTOR_V55_G4G5_CALIBRATION_108` | 108 | 108 / 108 | 100.00% | `36/36` true LSF, `36/36` CR, `36/36` plateau |
| `INJECTION_RECOVERY_540` | 540 | 540 / 540 | 100.00% | `ESO_FEROS` + `ESO_HARPS` paired completeness |
| `COMB_V4_1_CALIBRATION_162` | 162 | 162 / 162 | 100.00% | `54/54` true combs; `0/54` forest & `0/54` sky FA |
| `KEPLERIAN_TRACK_CALIBRATION_81` | 81 | 81 / 81 | 100.00% | `K_PLANET` Keplerian de-Doppler recovery |
| **D097 Total / Cumulative** | **2,031** | **2,025 / 2,031** | **99.70%** | **Cumulative D079–D097 = 39,942 trials** |

---

## 3. Stream-by-Stream Observational & Stage-2 Forensic Results

### 3.1 Stream 1A: `HERSCHEL_HIFI` THz Heterodyne (`11` Stars, `22` Bands, `0.56–1.16 THz`, `R = 2.2 × 10⁶`)
- **Targets:** `9` science AGB/post-AGB/SG (`RDOR`, `OCETI`, `BETELGEUSE`, `CHICYG`, `IKTAU`, `IRC10216`, `RCAS`, `REDRECT`, `VHYA`) + `2` PN controls (`NGC6302`, `NGC7027`), `178,216` valid channels (`0` Stage-A loss).
- **Detections & Stage-2 Triage:** `11` raw peaks -> **`5` Stage-1 qualified** -> **0 verified ETI**:
  - `STAGE2_VETO_HIFI_CIRCUMSTELLAR_OUTFLOW` (**4**): `RDOR 681.4480 GHz` (SO `16_15-15_14`, true wind `FWHM = 9.90 km/s`), `RDOR 569.0075 GHz` (SO `13_14-12_13`, `FWHM = 7.11 km/s`), `RCAS 681.4045 GHz` (`FWHM = 14.96 km/s`), `NGC6302 681.5095 GHz` (`FWHM = 18.48 km/s`). Unfiltered envelope wings are broader than the narrow 41-channel median filter window; global wind FWHM (`7.11–18.48 km/s >= 5.5 km/s`) cleanly distinguishes AGB winds from unresolved `~0.5 km/s` THz laser beacons.
  - `STAGE2_VETO_HIFI_MOLECULAR_ENVELOPE` (**1**): `OCETI 1151.8055 GHz` (`CO J=10-9` at `1151.9854 GHz`, `dv = +46.8 km/s` Mira systemic + wind velocity).
- **Best Limit:** `RDOR` `HIFI_571GHZ` (`525.42 um`) -> **`235,044.173974 kW`** (`10 m` TX).

### 3.2 Streams 1B & 1C: `HERSCHEL_SPIRE_FTS` (`10` Stars, `20` Arms) & `HERSCHEL_PACS` (`5` Stars, `20` Slices)
- **SPIRE FTS (`194–670.69 um`, `R = 1,000`):** `5` protoplanetary disks (`ABAUR`, `HD100546`, `HD142527`, `HD163296`, `HD169142`, each with `4` off-axis ring detectors/arm) + `4` PN/post-AGB controls (`AFGL2688`, `CRL618`, `NGC6302`, `NGC7027`) + `VYCMA`. `85` raw peaks -> **`35` Stage-1 qualified** (`13` `AFGL2688`, `12` `VYCMA`, `7` `CRL618`, `2` `NGC6302`, `1` `NGC7027`; `0` on all 5 protoplanetary disks) -> **35/35 resolved via `STAGE2_VETO_SPIRE_CDMS_ATLAS`** (`HCN`, `HCN v2=1`, `13CO`, `o/p-H2O` incl. `VYCMA 658 GHz maser 455.58 um`, `CH+ 1-0 358.97 um`; `|Δλ| < 0.22 um = <0.5 px`) -> **0 verified ETI**.
  - **Best SPIRE Limit:** `ABAUR` `SPIRE_SLWC3` (`486.86 um`) -> **`70.703128 kW`**.
- **PACS Far-IR (`51–210 um`, `R = 2,000`):** `5` Herbig/T-Tauri disks (`HD100546`, `HD142527`, `HD163296`, `HD169142`, `HD36112`). `5` raw peaks -> **`1` Stage-1 qualified**: `HD100546 130.3859 um` = CDMS `CO J=20-19` (`130.3688 um`, `Δλ = +0.0171 um`) (`STAGE2_VETO_PACS_CDMS_ATLAS`) -> **0 verified ETI**.
  - **Best PACS Limit:** `HD163296` `PACS_124UM` (`124.08 um`) -> **`102,995.140533 kW`**.

### 3.3 Stream 1D: `HST_STIS_E140H` Ultra-High-Resolution FUV (`6` Stars, `R = 114,000`)
- **Targets:** `4` science (`ALPCENA`, `ANTARES`, `PROCYON`, `REGULUS`) + `2` controls (`BD332642`, `NGC7027`), `243,483` good native pixels.
- **Detections & Stage-2 Triage:** `30` raw peaks -> **`4` Stage-1 qualified**, **ALL 4 inside `CONTROL` planetary nebula `NGC7027`** (`1510.9058 / 1510.9851 A` and `1516.3662 / 1516.4459 A`, adjacent order overlap pairs) -> **4/4 resolved via `STAGE2_VETO_STIS_EXTENDED_PN_BK_OVERSHOOT`** showing severe CALSTIS background-strip negative-flux overshoot flanks (`min_z = -79.3` & `-35.5`, `min_fl = -2.85e-14` & `-4.90e-14`) bracketing bright extended nebular knots (`0` qualified peaks on all 4 science stars) -> **0 verified ETI**.
- **Best STIS Limit:** **`ALPCENA` (`Alpha Centauri A`, `1.339 pc`) `E140H_1400` (`1400.0 A`) = `65.45981 W` (`0.065460 kW`)**; `PROCYON` (`3.514 pc`) `E140H_1250` = **`1.441765 kW`**.

### 3.4 Stream 2: Live `ESO_FEROS` + `ESO_HARPS` Cascade, Orbits `#139–#140`, & Optical Stage-2 Triage
- **Stage-A All-NaN `ERR` Handling:** All `20` ESO Phase-3 `ADP` spectra (`8` `ESO_FEROS`, `12` `ESO_HARPS`) ship with finite flux arrays (`94,820–313,142 px`) and an all-NaN `ERR` column (`0` positive finite `ERR` entries). `_extract_eso_1d` masks only invalid/zero fluxes when `ERR` is absent while Stage-B `_unpack_echelle_exposure` assigns a 512-bin rolling MAD noise scale.
- **Measured Stellar RVs:** `GJ536` (`-26.0189 ± 0.1003 km/s`), `GJ680` (`-22.8733 ± 0.2200 km/s`, `156/180` clean anchors across Cohort), `GJ877` (`+65.6048 ± 0.4368 km/s`), `GJ1005` (`-18.9980 ± 5.4765 km/s`), and rapid rotator `ALTAIR` (`v sin i ~ 240 km/s`, anchor scatter `39.4276 km/s > 8.0 km/s` -> aligned at locked prior RV `-26.1000 km/s`).
- **Four-Generation Optical Cascade + `K_PLANET` (`#139–#140`):**
  - `ESO_FEROS` (`ALTAIR`, `GJ1005`, `8` exp.): `573 G1 -> 571 G2 -> 569 G3 -> 288 G45 -> 274 G6 -> 242 G7 -> 187 G8` -> resolved physically via Stage-2 (`87 LOWCONT_SNR`, `73 COSMIC_RAY_SINGLE_EPOCH`, `23 LOWCONT_CR_RINGING` incl. `GJ1005 3984.5645 A` where raw FITS `ADP.2016-09-23T12:25:48.855` has `cont_snr=5.07`, `pk_fn=57.53`, `min_wing=0.3933`, absent in all `3` other epochs, `3 SUBPHOTOSPHERIC_TROUGH`, `1 OH_OR_AIRGLOW_WING`) -> **0 verified ETI**. (Incl. `ALTAIR 3707.4245 A`, verified in raw FITS `.284` as a `2.5 px` U-band spike `[0.085, 0.164, 0.326, 0.243, 0.062]` completely absent 24 h later in `.456` [`fn=0.92`] and `.243` [`fn=0.96`], with `.020` `cont_snr=5.83 < 8.0`.)
  - `ESO_HARPS` (`GJ536`, `GJ680`, `GJ877`, `12` exp.): `198 G1 -> 187 G2 -> 186 G3 -> 67 G45 -> 56 G6 -> 50 G7 -> 54 G8` (`40 Ch-T + 14 K_PLANET`) -> resolved physically (`22 LOWCONT_SNR`, `18 SUBPHOTOSPHERIC_TROUGH` [incl. `12 K_PLANET`], `10 COSMIC_RAY_SINGLE_EPOCH`, `2 OH_OR_AIRGLOW_WING`, `2 KPLANET_LOW_COHERENCE` on `#139 GJ680`) -> **0 verified ETI**.
  - **Orbital Campaigns `#139–#140`:** `#139 GJ680 b` (`P = 17,281.665 d`, `K_p = 6.338 km/s`: `12 G7 -> 0 verified ETI`) and `#140 GJ536 b` (`P = 8.70874 d`, `K_p = 83.641 km/s`, `Δv = 148.576 km/s`: `11 G7 -> 0 verified ETI`), lifting cumulative orbital campaigns to **140 (`0` ETI)**.
  - **Best Optical EIRP Limits:** `GJ1005` (`ESO_FEROS F1_4100`, `6.0 pc`) = **`0.249612 kW` (`249.61 W`)**; `GJ536` (`ESO_HARPS H1_4100`) = **`0.937855 kW` (`937.86 W`)**; `ALTAIR` `F1_4100` = `761.656993 kW`.
  - **`COMB_V4_1` & `Agnostic`:** `3,017,372` D097 comb configs evaluated (`3` raw `V4` peaks on `GJ1005` -> `0 V4.1` survivors), expanding uniform sweep to **453 all-sky comb stacks (`D079–D097` -> `0` ETI)**; `474` broad/top-hat agnostic multiscale features on D097 optical spectra (`0` ETI).

### 3.5 Stream 3: `DRIFT_V55_COHERENT_JERK` Across `25` $N \ge 4$ Campaigns (`1.411B` Pixel Integrals)
Scanning `32,426` cubic-jerk (`v_dddot`), quadratic-sag (`v_ddot`), linear-drift (`v_dot`), and periodic Keplerian trajectories (**`1,410,603,112` pixel-trajectory integrals**) across all **25 $N \ge 4$ campaigns** (`5` live `D097` FEROS/HARPS + `20` retroactive Archive `T/U/V` APOGEE-2 & CARMENES) yielded **3,619 raw Stage-1 survivors** -> **0 verified ETI**:
- `STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH`: **1,688**
- `STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND`: **1,316** (incl. `HNLIB 8281.3390 A` where `-58 km/s` BERV flip `[+29.8, +30.2, +29.3, -28.25]` exposed an Earth `8280–8284 A` H2O telluric trough baked into `tpl_s = 0.6512`, `ep0` peak in absorption `0.9359 < 1.0`, only `1/4` true emission epochs)
- `STAGE2_VETO_OH_SKY_OR_TELLURIC`: **613** (incl. `2M23032370 16347.6841 A` fixed APOGEE-2 topocentric sky/OH line at `w_topo = 16352.42–16353.42 A`, `std = 0.398 A`, `snr_sky/stack = 0.683`, verified across independent D095 stars `KEPLER37` & `KEPLER93`)
- `STAGE2_VETO_NON_LSF_SHAPE`: **2**

---

## 4. Unified `448`-Star Synthesis & `12.855`-Octave Panchromatic Limits (`D079–D097`)

- **Spectral Span:** `0.0905–670.69081 um` (**12.855 unbroken octaves**) across **30 spectrographs (42 arms)**.
- **Total Cohort:** **448 unique stars** (`345` science / `103` control; `205` planet-host stars harboring `399` confirmed exoplanets), `2,601` exposures, `772.806 h` integration, `39,942` calibration trials, **`317,805` Legacy V2 false alarms eliminated**, and **0 verified ETI detections**.
- **Solar Neighborhood (`< 10 pc`):** **169 unique stars** (`126` science [`59` planet hosts / `118` planets] + `43` controls), median `10 m` TX EIRP limit = **`1.4627 kW`**.
- **Panchromatic Multi-Instrument Bridges:** **58 calibrated science bridges (`728` cells)** + `2` revisited controls (`BD601753`, `NGC7027`) = **`60` multi-phase targets** (`ABAUR`, `ALPCENA`, `ANTARES`, `BETELGEUSE`, `OCETI`, `PROCYON` newly linked into UV/THz/far-IR in D097).
- **Multi-Event Ellipsoid (`448` Stars):** `18` Ecliptic Transit Zone (`|beta| <= 2 deg`) stars and `36` within `|Delta t| <= 180 d` of SN 1987A / GW170817 / SN 2023ixf -> **0 ETI**.
- **Radiometry Audit (`95` D097 Cells):** Verified in `/usr/bin/python3 -S audit.py` (`C12`) with zero external dependencies across all 3 anchors (`DIRECT_CGS`, `GAIA_G_PLANCK`, `2MASS_H_PLANCK`).
