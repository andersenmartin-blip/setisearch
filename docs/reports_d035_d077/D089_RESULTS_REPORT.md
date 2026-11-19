# Phase D089 Results Report (`SPACE_LYMAN_FUV_NUV_V4_0`)

## 1. Executive Summary
Phase **D089** extends the panchromatic echelle laser and frequency-comb SETI survey into the **space ultraviolet and Lyman-limit regime (`0.0905–0.3150 µm`)** using archival spectra from **FUSE** (`0.0905–0.1187 µm`, `R = 20,000`), **HST/COS G130M** (`0.1125–0.1450 µm`, `R = 18,000`), and **HST/STIS NUV E230M/E230H** (`0.1605–0.3150 µm`, `R = 30,000 / 114,000`). Closing the prior `0.171–0.305 µm` gap yields **unbroken `4.796`-octave (`0.0905–2.515 µm`)** coverage across **14 spectrographs / 16 arms**, **250 unique stars (`121` `< 10 pc`, `26` multi-regime panchromatic bridges)**, **1,759 exposures (`569.3578` h)**, **80 orbital campaigns**, and **250 distinct stellar systems** with **23/23 radio-echelle + 1 *TESS* overlap closure (`24` direct overlaps)** and **zero verified ETI detections**.

## 2. Prospective Lock, Cohort Hygiene & Provenance
- **Prospective Method Lock (`METHOD_LOCK.json` / `LOCK_RECEIPT.json`):** Sealed at `2026-11-19T18:43:01Z` (`METHOD_LOCK` SHA-256 `c822fc1fabdd4af7facdb116915c78753dc7a54769086d85fa2d56ba29dc6bf6`) with `inputs_d089_v4_0/` strictly absent prior to lock.
- **MAST Data Acquisition (`FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`):** Initiated at `2026-11-19T18:43:34Z` (`+33.0 s` post-lock lag); downloaded `192/192` public science FITS files (`507.65 MiB`).
- **Pre-Lock & ASN Quality Audits:** Excluded FUSE exposure-level status stubs (`ALPCENA`) and HST/COS internal `EXP-SWAVE` Pt-Ne wavelength lamps (`TRAPPIST1` association tables, keeping only `EXP-FP` `FLUXCORR='COMPLETE'` exposures). All `192/192` downloaded FITS headers and arrays passed offline flux/error sanity checks.
- **Implementation Lock (`D089_IMPLEMENTATION_LOCK_V1`):** Expanded only the non-gate calibration Keplerian spot search grid (`analyze.py`, SHA-256 `dbe602ad8391ddfcd4008242760592309a25b3861624c3b5a129f9c429e1880c`) while keeping `v4_0_detector.py` (`5bbd0178f3b611bed90f26453c42f90a0abb99a5608eaacf296b38986caf4604`) and `FROZEN_COHORT_D089.csv` (`5e0f40744e0f0745005a8f6f74383b41f7cf3a558894c51cf5b7268e50526c0c`) strictly frozen.
- **D089 Cohort (`37` stars, `192` exposures, `203.5519` h):**
  - `30` brand-new targets (`4` within `10 pc`: `ALPCENA`, `GJ367`, `GJ667C`, `PROCYON`) + `7` panchromatic bridge stars (`55CNC`, `BETPIC`, `EPSERI`, `GJ832`, `GJ876`, `HD189733`, `HD209458`).
  - `36` `FUSE_FUV` (`8` stars) + `84` `HST_COS_FUV` (`17` stars) + `72` `HST_STIS_NUV` (`12` stars).
  - Zero overlap with prior `C001–C037` + `D001–D088` exposures (`min_brand_new_sky_separation_arcsec = 7708.86"`).
  - **BERV / LEO Ephemeris Closure (`C4`):** `192/192` PASS against stdlib Earth ephemeris (`max |V_helio - stdlib_Earth| = 0.5032 km/s <= 8.50 km/s`).
  - **UV Stellar RV Anchoring (`C5`):** `1,764` anchor measurements (`423` clean absorptions) across `37` stars, `median |emp_rv - prior_rv| = 2.5014 km/s`.

## 3. Synthetic Calibration (`2,697` D089 Trials / `24,072` Cumulative)
| Suite | Trials | Key Verified Metrics |
|---|---:|---|
| Channel T & P Injection (`C6`) | 1,620 | `T (>=8 sigma) = 1.000`, `P (>=8 sigma) = 1.000` |
| Keplerian Track (`C6`, `>= 6.5 sigma`) | 135 | `T_DIFF = 0.000`, `K_PLANET = 1.000` |
| `G4_V40 + G5` Morphology (`C6`) | 216 | `True = 1.000`, `Cosmic-ray rej = 1.000`, `Plateau rej = 1.000` |
| `FUSE_FUV` Dual-Channel Coincidence (`C10`) | 8 | Dual-channel `8/8 PASS`; single-channel injection `8/8` vetoed (`FUSE_SINGLE_CHANNEL_DETECTOR_ARTIFACT`) |
| `G6` Sparse vs Dense Atlas (`C7`) | 240 | `True = 1.000`, `Geocoronal = 1.000`, `Hot pixel = 1.000`, `Intra-BERV = 1.000` |
| `COMB_V4_1` Frequency Comb (`C8`) | 486 | `6-tooth (>=3.8 sigma) = 1.000`, `1-line = 0.000`, `Topo = 0.000`, `Dense forest: V4 1.000 -> V4.1 0.000` |

## 4. Real Search Cascade, Orbital Campaigns & Forensic Classification
- **Searched Space (`D089`):** `4,011,501` Channel T bins, `724,464` Channel P coadd bins, `262,719` `T_DIFF` bins, `263,703` `K_PLANET` bins, and `11,574,920` `COMB_V4_1` comb configurations.
- **Veto Cascade (`C11`–`C12`):** `24,123` legacy V2 peaks -> `303` G1 -> `270` post-G2 -> `202` post-G3 -> `202` post-G4 -> `194` pre-G6 (`67` vetoed by G6 sparse) -> `127` automated post-G6 (`1` control + `126` science).
- **100% Natural Forensic Attribution:**
  - `123` `NUV_PHOTOSPHERIC_CONTINUUM_FLUCTUATION` (HST/STIS Fe I/Fe II line-curtain structure)
  - `3` `STELLAR_UV_CHROMOSPHERIC_LINE_WING`
  - `1` `UV_FIXED_PATTERN_OR_ISM_CONTINUUM_FLUCTUATION`
  - All `127` have `eti_plausible = false`.
- **10 Orbital Campaigns (`#71–#80` Cumulative, `C13`):** `3` null controls (`HD122563`, `HD211998`, `LTT2050`) + `7` science campaigns (`55CNC`, `HD189733`, `HD209458`, `HD97658`, `LTT9779`, `TOI776`, `TRAPPIST1`), each with `4 IN_WINDOW` + `4 OUT_OF_WINDOW` exposures; `0` `T_DIFF` and `0` `K_PLANET` automated detections (`max |Kp_std - Kp_csv| = 0.00004 km/s`).
- **Unified All-Sky `COMB_V4_1` Sweep (`D079–D089`, `284` stacks / `1,759` exp, `C9`):** `5,434` `COMB_V4` -> `15` `COMB_V4_1` (including `0` in `D089`) -> `0` verified ETI.

## 5. Space-UV Radiometric Limits & Unified 250-Star Survey Synthesis
- **D089 Direct-FLAM Upper Limits (`150` cells, `C14`, max stdlib recompute rel diff `4.83e-05`):**
  - **Best overall D089:** `GJ832` (`C3_COS_1280`): `0.21938 W` (`0.00021938 kW`)
  - **Best `FUSE_FUV`:** `ALPCENA` (`L2_FUSE_1005`): `0.42944 W` (median FUSE `0.2282 kW`)
  - **Best `HST_STIS_NUV`:** `HD62509` (`N2_STIS_1950`): `0.73877 kW` (median STIS NUV `68.31 kW`)
  - **`TRAPPIST1` (`12.47 pc`, `HST_COS_FUV`):** `1.351–4.430 W` (`0.001351–0.004430 kW`) across `C1–C5`
- **Unified Panchromatic v4 Census (`D079–D089`, `C15`–`C16`):**
  - `250` unique stars (`121` `< 10 pc`, median `10 m` CW laser limit `1.7494 kW`), `26` multi-regime panchromatic bridges (`485` cells) including `BETPIC` (`4.77`-octave Lyman-alpha to K-band) and `EPSERI` (4-arm Lyman-to-NIR).
  - `14` spectrographs / `16` arms across `0.0905–2.515 µm` (`4.796` octaves), `1,759` exposures, `569.3578` integration hours, `24,072` calibration trials, `257,124` legacy V2 peaks eliminated, `80` orbital campaigns.
  - **Multi-Messenger Closure:** `250` distinct stellar systems; `23/23` (`100%`) radio-echelle targets + `1` *TESS* photometrically overlapped system (`24` direct overlaps); `0` verified ETI detections.

## 6. Offline Reproducibility & Verification (`16/16 PASS`)
- `bounded_inputs/d089_bounded_bundle.json.gz`: `2.48 MiB` (`< 25.0 MiB`).
- Stage B deterministic recompute: `24/24` output files `100%` SHA-256 bit-identical.
- Standalone `/usr/bin/python3 -S audit.py`: **`OVERALL: PASS (16/16)`** (`C1`–`C16` all PASS).
