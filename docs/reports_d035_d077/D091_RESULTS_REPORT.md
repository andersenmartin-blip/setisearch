# Phase D091 Results Report (`ESO_TRIPLE_SPECTROGRAPH_3ARM_V4_2`)

## 1. Executive Summary
Phase **D091** incorporates three complementary European Southern Observatory (ESO) Phase-3 spectrograph architectures under **`ESO_TRIPLE_SPECTROGRAPH_3ARM_V4_2`**: **VLT `X-shooter` simultaneous 3-arm (UVB + VIS + NIR)** (`0.2989–2.4790 µm`, `R = 9,860–18,340`), **MPG/ESO `FEROS` high-resolution echelle** (`0.3527–0.9216 µm`, `R = 48,000`), and **VLT `FLAMES/GIRAFFE` HR** (`0.5139–0.8994 µm`, `R = 18,000–29,000`). Integrating D091 with D079–D090 unites **19 spectrographs / 22 arms** across **`0.0905–28.00 µm` (`8.273` unbroken octaves)**, **310 unique stellar systems (`135` `< 10 pc`, `35` panchromatic bridges across `625` cells)**, **2,076 exposures (`634.3886` h)**, **`100` cumulative multi-epoch orbital campaigns (`#1–#100`)**, **`358` all-sky `COMB_V4_1` stacks**, and **310 multi-messenger systems (`23/23` radio-echelle + 1 *TESS* closure, `24` direct overlaps; `16CYGB` and `GJ849` tri-regime bridges)** — with **zero verified ETI detections**.

## 2. Prospective Lock, Implementation Lock, Cohort & Provenance
- **Prospective Method Lock (`METHOD_LOCK.json` / `LOCK_RECEIPT.json`):** Sealed at `2026-11-20T17:38:53Z` (`METHOD_LOCK` SHA-256 `c7552035aff59bffab0eadc446b1a9a7bc7eb53391b86c7a7f165a2382e8e6a3`) with `inputs_d091_v4_2/` strictly absent prior to lock.
- **ESO Phase-3 Acquisition (`FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`):** Initiated at `2026-11-20T17:39:07Z` (`+14.0 s` post-lock lag); downloaded `156/156` exposures (`222` public ESO Phase-3 1D FITS files across 49 ESO Program IDs, `225.17 MiB <= 240 MiB`).
- **Pre-Lock Exclusion (`PRIOR_EXCLUSION_VERIFICATION.json`):** `0` DP-ID overlaps against `2,303` prior exposure IDs (`C001–C037 + D001–D090`); minimum sky separation for the `30` brand-new D091 stars against all `336` prior excluded coordinates is `1,259.01"` (intra-D091 minimum `456.56"`).
- **Implementation Lock (`D091_IMPLEMENTATION_LOCK_V1`, sealed `2026-11-20T19:22:25Z`):** Kept `v4_2_detector.py` (`f941c3abdaec2447ec4c6e227febf4c87b74da346b9039178bbc972d6342d19`), `FROZEN_COHORT_D091.csv` (`95a76f9c08a5b609da60527ebf8b6c270bc8a6b2986dddd1fd6f99906383c226`), and `audit.py` (`2823d630a44786356db14c9c850a4984fec3d7c0ae6d5f61ca3e36b675dea537`) **100% bit-identical to `METHOD_LOCK.json`**. Sealed non-gate fixes in `analyze.py` (`3ed274401d1d96ee169feff3705254b8036051e1ad1d13a7acc92e9060ac1c9e`: `.reshape(-1)` vector flattening in `_decode_wave`/`_decode_f32_t21`; proper `(c_raw, c_eff)` unpacking with `fn = fl_clean / c_eff`; `D088`-parity `_rolling_comb_sigma` + exact `[lo_a-40, hi_a+40]` parallel comb slicing across 4 workers; `ESO_GIRAFFE_HR` `HR10`/`HR11` sparse-grating kNN pool augmentation via overlapping peers + FEROS references; `±25 Å` GIRAFFE UL band gating yielding exact `127` observed star-band cells; pairwise sorted `>=40 km/s` orbital-phase dispersion check in `C8`; and cool M/L-dwarf `Teff < 4200 K` ordering in `_forensic_classify`) and `plot_figures.py` (`298563d3c1306831e3ef7ebb771136839129863cdf1df97d5729c6f4b97a4fa8`).
- **D091 Cohort (`37` stars, `156` exposures / `222` FITS, `47.3328` h):**
  - `9` zero-planet control stars (`G29751`, `GJ1128`, `GJ402`, `HD104600`, `HD1064`, `HD107328`, `HD11210`, `HD220009`, `HIP103039`) + `28` science stars (`30` brand-new targets including **`10` within `10 pc`**: `DELERI`, `GJ1128`, `GJ402`, `GJ433`, `GJ908`, `HD216803`, `HIP103039`, `LP94420`, `SCR1845`, `ZETTUC`, plus `7` panchromatic bridge targets: `GJ832`, `TAUCET` existing and `LAWD37`, `GJ849`, `GJ674`, `HD20794`, `GJ436` newly bridged).
  - `33` `ESO_XSHOOTER_3ARM` (`99` FITS, `10` stars, `2.6956` h) + `36` `ESO_FEROS` (`36` FITS, `10` stars, `6.9991` h) + `87` `ESO_GIRAFFE_HR` (`87` FITS, `17` stars, `37.6382` h).
  - **Barycentric & RV Anchoring (`C4`/`C5`):** `156/156` exposures pass header/pixel provenance; `1,503` optical/NIR RV anchor evaluations (`599` `CLEAN_ABSORPTION`) across `37` stars yield `median |emp_rv - prior_rv| = 2.0249 km/s`.

## 3. Synthetic Calibration (`2,697` D091 Trials / `29,466` Cumulative)
| Suite | Trials | Key Verified Metrics |
|---|---:|---|
| Channel T & P Injection (`C7`) | 1,620 | `T (>=8 sigma) = 0.9333` (`378/405`), `P (>=8 sigma) = 0.9111` (`369/405`) |
| Keplerian Track (`C8`, `>= 6.5 sigma`) | 135 | `T_DIFF = 0.0000` (`0/135`), `K_PLANET = 1.0000` (`135/135`) |
| `G4_V42 + G5` Morphology (`C9`) | 216 | `True = 1.000` (`72/72`), `Cosmic-ray/hot-px rej = 1.000` (`72/72`), `Plateau rej = 1.000` (`72/72`) |
| `ESO_XSHOOTER_3ARM` Dual-Arm Coincidence (`C10`) | 8 | `UVB+VIS` (`5445–5510 Å`) & `VIS+NIR` (`10055–10160 Å`) dual-arm `8/8 PASS`; single-arm injection `8/8` vetoed (`XSHOOTER_SINGLE_ARM_DETECTOR_ARTIFACT`) |
| `G6` Sparse vs Dense Atlas (`C11`) | 240 | `240/240` (`1.000`) exact match across True, Stationary Telluric, Same-Star Stationary, & Unique classes |
| `COMB_V4_1` Frequency Comb (`C12`) | 486 | `6-tooth (>=3.8 sigma) = 1.000` (`162/162`), `Dense forest: V4 1.000 (162/162) -> V4.1 0.000 (0/162)`, `Topo/Bg = 0.000` (`0/162`) |

## 4. Real Search Cascade, Orbital Campaigns `#91–#100`, `COMB_V4_1` & Forensics
- **Searched Space (`D091`):** `9,719,414` Channel T 1D bins (`2,472,237` X-shooter + `6,825,160` FEROS + `422,017` GIRAFFE), `2,748,118` Channel P coadd bins, `490,821` `T_DIFF` bins, `490,689` `K_PLANET` bins, and `15,740,032` `COMB_V4_1` comb configurations.
- **Veto Cascade (`C13`):** `24,998` legacy V2 peaks -> `5,690` G1 -> `5,607` post-G2 -> `5,451` post-G3 -> `3,763` post-G4 -> `2,565` pre-G6 (`203` vetoed by G6 sparse) -> **`2,362` automated qualified** (`569` control + `1,793` science) -> **`0` verified ETI detections**.
- **100% Natural Forensic Attribution (`2,362` automated qualified, all `verified_eti = false`):**
  - `2,133` `M_DWARF_UNMODELED_MOLECULAR_OR_FLARE_FEATURE` (primarily `SCR1845` `2600 K`, `LP94420` `2250 K`, `GJ1128` `3050 K`, and `GJ402` TiO/VO/CrH molecular bands and low-SNR blue FEROS continua unmodeled by warmer kNN peers — directly motivating latent autoencoder/RPCA spectral modeling in `V5.0`)
  - `149` `SINGLE_EPOCH_TRANSIENT_NONPERSISTENT`
  - `71` `TELLURIC_OR_AIRGLOW_WING_RESIDUAL`
  - `6` `ARCHIVAL_REDUCTION_EDGE_OR_FRINGE_RESIDUAL`
  - `2` `XSHOOTER_DICHROIC_EDGE_ARTIFACT`
  - `1` `ZERO_PLANET_CONTROL_CALIBRATION_FEATURE`
- **10 Orbital Campaigns (`#91–#100` Cumulative, `C6`):** `3` null controls (`HD220009`, `HD107328`, `G29751`) + `7` science campaigns (`K222`, `GJ433`, `HD213885`, `GJ436`, `OGLETR113`, `OGLETR111`, `KEPLER156`; `min_dv_span = 7.83 km/s`, up to `432.29 km/s`); **`0` `K_PLANET` candidates across all 10 campaigns**, and `5` `T_DIFF` survivors (`2` `K222` M-dwarf features, `1` `HD213885` order residual, `2` `KEPLER156` `OI_6300`/`OI_6364` airglow wings) -> **`0` verified ETI**.
- **`COMB_V4_1` & All-Sky Sweep (`D079–D091`, `358` stacks / `2,076` exp, `C12`):**
  - `D091`: `8,735 COMB_V4` -> **`4 COMB_V4_1`** (all `4` on zero-planet control `GJ1128` in `FEROS_BLUE` at `4694–4696 Å` -> **`0` verified ETI**).
  - Cumulative `D079–D091` (`358` stacks / `2,076` exposures): **`16,037 COMB_V4` $\rightarrow$ `45 COMB_V4_1` $\rightarrow$ `0` verified ETI**.

## 5. Radiometric Limits (`127` Cells), `35` Panchromatic Bridges & `310`-Star Synthesis
- **D091 `10 m`-Transmitter Upper Limits (`127` cells across `15` bands [`60` X-shooter + `50` FEROS + `17` GIRAFFE], `C14`, max stdlib recompute rel err `0.000896675`):**
  - **Best formal Gaia-`G` Planck extrapolation cell:** `LP94420` (`6.42681 pc`, `2250 K` brown dwarf, `ESO_FEROS F1_4100`): `2.26997 W` (`0.00227 kW`, followed by `SCR1845` `F1_4100` `0.00332 kW`). *Physical caveat:* because `LP94420` and `SCR1845` are cool brown/ultracool dwarfs with low blue SNR (`mad_rel = 0.562` and `0.277`, continuum SNR ~1.8–3.6 at `4100 Å`), these `F1_4100` numbers reflect formal Wien-tail Gaia-`G` (`6218 Å`) Planck continuum extrapolations rather than directly detected photospheric continua.
  - **Best high-SNR continuum bounds by instrument:** `ESO_XSHOOTER_3ARM` **`LAWD37`** (`4.6366 pc`, `X3_6800`): **`0.33023 kW`** (and `GJ674` `0.23537 kW` overall cross-instrument bridge); `ESO_GIRAFFE_HR` **`OGLETR113`** (`G3_5715`): **`1.00596 kW`**; `ESO_FEROS` high-SNR optical stars down to **`0.05015 kW`** (`HIP103039` `F1_4100`, `mad = 0.03095`, `CONTROL`) and **`4.40419 kW`** (`GJ433` `F1_4100`, `SCIENCE` at `9.07679 pc`).
- **Unified Panchromatic V4.2 Census (`D079–D091`, `C15`–`C16`):**
  - **`310` unique stars** (`239` science [`154` exoplanet hosts harboring `304` planets] + `71` controls; `269` finite optical-to-IR limit cells across `1.30–1,928.26 pc`; **`135` `< 10 pc` stars** [`100` science (`53` hosts / `110` planets) + `35` controls] with median limit **`1.62371 kW`**; all-time space-UV record **`0.0973 W`** on `Proxima Cen` `HST_STIS`).
  - **`35` panchromatic bridges (`625` cells)** across **`0.0905–28.00 µm` (`8.273` octaves)**: D091 adds 5 new bridges — **`LAWD37`** (`0.3601–23.5024 µm`, `6.03` octaves, `JWST_MIRI_MRS + ESO_XSHOOTER_3ARM`), **`GJ849`** (`0.3600–2.0969 µm`, `2.54` octaves), **`GJ674`** (`0.3600–2.0970 µm`), **`HD20794`** (`0.3601–2.0976 µm`), and **`GJ436`** (`0.5480–2.3450 µm`) — alongside expanded **`GJ832`** (`0.1165–2.0972 µm`, `4.17` octaves) and **`TAUCET`** (`0.3845–1.6642 µm`).
  - **Survey Totals (`D079–D091`):** `19` spectrographs / `22` arms, `2,076` exposures (`634.3886` h), `29,466` calibration trials, `286,043` legacy V2 false alarms eliminated, `100` cumulative orbital campaigns.
  - **Multi-Messenger Closure (`310` Systems):** `23/23` (`100%`) radio-echelle closure (`24` direct overlaps incl. `TESS` `L 98-59`), now featuring **two tri-regime systems**: **`16CYGB`** (GBT `1.4 GHz` + Optical + *JWST* MIRI) and **`GJ849`** (Parkes/GBT `1.4 GHz` [`M17`] + `NIRPS_HE` + `ESO_XSHOOTER_3ARM`), with **`0` verified ETI detections across all modalities**.

## 6. Offline Reproducibility & Verification (`16/16 PASS`)
- `bounded_inputs/d091_bounded_bundle.json.gz`: `19.84 MiB` (`< 25.0 MiB`).
- Stage B deterministic recompute: `24/24` Stage-B output files **100% SHA-256 bit-identical** between `--from-bounded-inputs` and `--from-full-inputs` (`inputs_d091_v4_2/`).
- Standalone `/usr/bin/python3 -S audit.py`: **`OVERALL: PASS (16/16)`** (`C1`–`C16` all PASS).
