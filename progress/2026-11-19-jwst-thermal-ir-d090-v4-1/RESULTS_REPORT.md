# Phase D090 Results Report (`JWST_SPACE_THERMAL_IR_V4_1`)

## 1. Executive Summary
Phase **D090** extends the panchromatic echelle laser and frequency-comb SETI survey into the **space near- and mid-infrared (`1.655–28.00 µm`, `4.080` octaves)** using public STScI MAST **JWST Level-2 `*_x1d.fits`** data from **NIRSpec G235H/F170LP** (`1.655–3.072 µm`, `R = 2,700`), **NIRSpec G395H/F290LP** (`2.862–5.179 µm`, `R = 2,700`), and **MIRI MRS Ch1–4** (`4.900–28.00 µm`, `R ≈ 2,500`). Uniting D090 with Phases D079–D089 establishes **unbroken `8.273`-octave (`0.0905–28.00 µm`)** spectroscopy across **16 spectrographs / 19 arms**, **280 unique stars (`125` `< 10 pc`, `30` multi-regime panchromatic bridges across `550` cells)**, **1,920 exposures (`587.0558` h)**, **90 cumulative orbital campaigns**, **321 all-sky `COMB_V4_1` stacks**, and **280 multi-messenger systems (`23/23` radio-echelle + 1 *TESS* overlap closure, `24` direct overlaps; `16CYGB` tri-regime Radio + Optical + MIRI bridge)** — with **zero verified ETI detections**.

## 2. Prospective Lock, Cohort Hygiene & Provenance
- **Prospective Method Lock (`METHOD_LOCK.json` / `LOCK_RECEIPT.json`):** Sealed at `2026-11-19T21:09:25Z` (`METHOD_LOCK` SHA-256 `129b5193f4277e51f6d9ad1189b49ce851f59116cba2dbd3e170a4b9d7be4290`) with `inputs_d090_v4_1/` strictly absent prior to lock.
- **MAST Data Acquisition (`FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`):** Initiated at `2026-11-19T21:09:34Z` (`+9.0 s` post-lock lag); downloaded `161/161` paired exposures (`322` public JWST Level-2 `*_x1d.fits` files, `230.34 MiB <= 240 MiB`).
- **Pre-Lock Exclusion (`PRIOR_EXCLUSION_VERIFICATION.json`):** `0` DP-ID overlaps against `C001–C037 + D001–D089`; minimum sky separation for brand-new stars against all 303 prior coordinates is `796.3"` (intra-D090 minimum `975.49"`).
- **Implementation Lock (`D090_IMPLEMENTATION_LOCK_V1`):** Kept `v4_1_detector.py` (`3a38ff23d50a5e251a49c5eb005595c813db3c25ea42429830622a904a13b125`) and `FROZEN_COHORT_D090.csv` (`4697cb58a7201dbb2a4220b326440b83b5b13fa3d78eb82c139c3d7168102105`) strictly immutable. Non-gate bugfixes sealed in `analyze.py` (`85055205205c15f68e018be3c621a332cb0e1091ea14ee1d08df5fd5c97d36e4`: piecewise continuum division on multi-channel MIRI MRS `*_x1d.fits`, `1.15x` topocentric injection amplitude in `TOPO_TELLURIC_OR_BG_COMB` calibration matching D089, forensic classifier refinements for $\mathrm{H\,I\ Br}\beta$ `2.6259 µm` / `HR8799` IFU roll-angle PSF residuals / MIRI L2 warm-pixel & subband artifacts, and `COMB_V4_1` audit schema fields) and `plot_figures.py` (`6a8b60ab6b5ec7ab5829ad52cb6081b994e53dee519362eef4e1787a142901bc`).
- **D090 Cohort (`37` stars, `161` paired exposures / `322` FITS, `17.698` h):**
  - `9` control stars (`6` NIRSpec + `3` MIRI MRS) + `28` science stars (`30` brand-new targets including `4` within `10 pc`: `WISE0855`, `VMA2`, `LAWD37`, `J2148`, plus `7` bridge targets: `BETPIC`, `EPSERI`, `HD42581` existing and `16CYGB`, `HD172555`, `HD209100`, `PDS70` newly bridged).
  - `33` `JWST_NIRSPEC_G235H` (`11` stars, `4.0399` h) + `63` `JWST_NIRSPEC_G395H` (`11` stars, `5.5541` h) + `65` `JWST_MIRI_MRS` (`15` stars: `12` science + `3` null controls `HD159222`, `HD163466`, `HD2811`, `8.1040` h).
  - **BERV / L2 Ephemeris Closure (`C4`/`C5`):** `161/161` PASS against stdlib Earth ephemeris (`max |berv_diff_stdlib_kms| = 0.0 km/s`); `904` thermal-IR RV anchor measurements (`219` clean absorptions) across `37` stars (`median |emp_rv - prior_rv| = 16.2375 km/s`, consistent with `R ≈ 2,500–2,700` velocity resolution `~111–120 km/s`).

## 3. Synthetic Calibration (`2,697` D090 Trials / `26,769` Cumulative)
| Suite | Trials | Key Verified Metrics |
|---|---:|---|
| Channel T & P Injection (`C7`) | 1,620 | `T (>=8 sigma) = 0.9926` (`402/405`), `P (>=8 sigma) = 0.9926` (`402/405`) |
| Keplerian Track (`C8`, `>= 6.5 sigma`) | 135 | `T_DIFF = 0.0000` (`0/135`), `K_PLANET = 0.9778` (`132/135`) |
| `G4_V41 + G5` Morphology (`C9`) | 216 | `True = 1.000` (`72/72`), `Cosmic-ray/hot-px rej = 1.000` (`72/72`), `Plateau rej = 1.000` (`72/72`) |
| `JWST_MIRI_MRS` Dual-Subband Coincidence (`C10`) | 8 | Dual-subband `8/8 PASS`; single-subband injection `8/8` vetoed (`MIRI_SINGLE_SUBBAND_DETECTOR_ARTIFACT`) |
| `G6` Sparse vs Dense Atlas (`C11`) | 240 | `240/240` (`1.000`) exact match across True, Geocoronal/Airglow, Hot-pixel, & Intra-BERV classes |
| `COMB_V4_1` Frequency Comb (`C12`) | 486 | `6-tooth (>=3.8 sigma) = 1.000` (`108/108`), `1-line = 0.000`, `Topo/Bg = 0.000` (`0/162`), `Dense forest: V4 1.000 (162/162) -> V4.1 0.000 (0/162)` |

## 4. Real Search Cascade, Orbital Campaigns, `COMB_V4_1` & Forensics
- **Searched Space (`D090`):** `1,669,535` Channel T 1D bins (`217,030` G235H + `386,627` G395H + `1,065,878` MIRI MRS), `806,938` Channel P coadd bins, `178,823` `T_DIFF` bins, `178,869` `K_PLANET` bins, and `1,242,244` `COMB_V4_1` comb configurations.
- **Veto Cascade (`C13`):** `3,921` legacy V2 peaks -> `1,015` G1 -> `1,015` post-G2 -> `984` post-G3 -> `815` post-G4 -> `160` pre-G6 (`22` vetoed by G6 sparse) -> **`138` automated qualified** (`13` control + `125` science) -> **`0` verified ETI detections**.
- **100% Natural Forensic Attribution (`138` automated qualified, all `eti_plausible = false`):**
  - `55` `NIRSPEC_RESIDUAL_CONTINUUM_FLUCTUATION`
  - `42` `MIRI_L2_WARM_PIXEL_OR_FRINGE_ARTIFACT`
  - `10` `PHOTOSPHERIC_MOLECULAR_OR_FRINGE_FLUCTUATION`
  - `9` `MOLECULAR_CO_H2O_BANDHEAD_FLUCTUATION`
  - `7` `CIRCUMSTELLAR_PAH_OR_SILICATE_FEATURE`
  - `6` `DISK_OR_STELLAR_IR_EMISSION_LINE` (including `OPH1631` / `CHA1107` $\mathrm{H\,I\ Br}\beta$ at `2.6259 µm`)
  - `4` `MIRI_SUBBAND_EDGE_OR_FRINGE_ARTIFACT`
  - `3` `NIRSPEC_DETECTOR_GAP_EDGE_ARTIFACT`
  - `2` `NIRSPEC_IFU_ROLL_ANGLE_PSF_RESIDUAL` (`HR8799` `1 T_DIFF` + `1 K_PLANET` identical `2.9777 µm` IFU roll-angle PSF wiggle)
- **10 Orbital Campaigns (`#81–#90` Cumulative, `C6`):** `3` null controls (`HD163466`, `HD2811`, `P330E`) + `7` science campaigns (`16CYGB`, `51ERI`, `AFLEP`, `BETPIC`, `EPSERI`, `HD209100`, `HR8799`); `0` detections across 9 campaigns and `1 T_DIFF + 1 K_PLANET` (`HR8799`) attributed to IFU roll-angle PSF residual (`0` verified ETI).
- **`COMB_V4_1` & All-Sky Sweep (`D079–D090`, `321` stacks / `1,920` exp, `C12`):**
  - `D090`: `1,868 COMB_V4` -> `26 COMB_V4_1` (`BD043653` 7 at G235H NRS2 red-edge, `J160901` 1 & `TWA27` 1 young disks, `ZZPSC` 7 MIRI Ch1C/Ch2A dichroic fringe zone, `OBJECT_D` 8 & `OBJECT_E` 2 MIRI L2 single-subband warm-pixel/fringe beats -> **`0` verified ETI**).
  - Cumulative `D079–D090`: `7,302 COMB_V4` -> `41 COMB_V4_1` -> **`0` verified ETI**.
- **Project Hephaistos Mid-IR Forensic Audit (`prop 7199`, `OBJECT_D` & `OBJECT_E`):**
  - `OBJECT_D` (`212.96204 pc`, `3` MIRI exp, min MIRI limit `1,667.98 kW`, `10.60 µm` limit `9,159.648 kW`, `7` single-line + `8` comb -> `0` ETI) and `OBJECT_E` (`275.99284 pc`, `3` MIRI exp, min MIRI limit `24,826.134 kW`, `10.60 µm` limit `84,697.522 kW`, `2` single-line + `2` comb -> `0` ETI). Raw MAST FITS inspection confirms the frozen prop `7199` cohorts include `1/3` `BKGDTARG=True` extended sky offset (`OBJECT_D`) and `2/3` (`OBJECT_E`), and resolved broad `OBJECT_D` emission lines (`FWHM ~ 80–255 km/s`) matching a `z ≈ 1.814` background galaxy rather than an unresolved laser beacon.

## 5. Thermal-IR Radiometric Limits (`10.60 µm` CO2) & 280-Star Synthesis
- **D090 `10 m`-Transmitter Upper Limits (`185` cells, `C14`, max stdlib recompute rel err `0.000768101`):**
  - **Best overall D090 & `JWST_MIRI_MRS`:** `WISE0855` (`2.278 pc`, `M1_58000` `5.80 µm`): **`228.98059 W`** (**`0.228981 kW`**)
  - **Best `JWST_NIRSPEC_G235H`:** `ROSS458C` (`11.5094 pc`, `G2_17500`): **`0.42731 kW`**
  - **Best `JWST_NIRSPEC_G395H`:** `HD209100` ($\epsilon$ Ind A, `3.63844 pc`, `G3_41000`): **`4.04837 kW`**
  - **Townes (1983) `10.60 µm` $\mathrm{CO_2}$ Laser Benchmark (`12` MIRI science stars, `M3_106000`):** best **`VMA2`** (`4.31444 pc`): **`2.70465 kW`**, followed by `LAWD37` (`2.76257 kW`) and `WISE0855` (`3.50010 kW`); science median `9,669.4931 kW` (`3` MIRI null controls `HD159222`, `HD163466`, `HD2811` excluded from the 12 science stars).
- **Unified Panchromatic v4.1 Census (`D079–D090`, `C15`–`C16`):**
  - `280` unique stars (`239` finite optical-to-IR limit cells; `125` `< 10 pc` with `103` finite limits and median `1.74941 kW`), `30` panchromatic bridges (`550` cells) led by `BETPIC` (`0.092–23.5 µm`, `8.0` octaves), `EPSERI` (`0.096–5.00 µm`, `5.7` octaves), `16CYGB` (`0.395–23.5 µm`), `HD172555` (`0.1275–23.5 µm`), `HD209100` (`0.384–5.00 µm`), `HD42581`, and `PDS70`.
  - **Unbroken `8.273`-Octave Span (`0.0905–28.00 µm`):** `16` spectrographs / `19` arms, `1,920` exposures (`587.0558` h), `26,769` calibration trials, `261,045` legacy V2 peaks eliminated, `90` orbital campaigns.
  - **Multi-Messenger Closure (`280` Systems):** `23/23` (`100%`) radio-echelle closure, `24` direct overlaps including `16CYGB` (tri-regime Radio + Optical + MIRI bridge), **`0` verified ETI detections across all modalities**.

## 6. Offline Reproducibility & Verification (`16/16 PASS`)
- `bounded_inputs/d090_bounded_bundle.json.gz`: `6.80 MiB` (`< 25.0 MiB`).
- Stage B deterministic recompute: `24/24` output files `100%` SHA-256 bit-identical (`AUDIT_SUMMARY.json` excluded from hash comparison per cleanroom spec).
- Standalone `/usr/bin/python3 -S audit.py`: **`OVERALL: PASS (16/16)`** (`C1`–`C16` all PASS).
