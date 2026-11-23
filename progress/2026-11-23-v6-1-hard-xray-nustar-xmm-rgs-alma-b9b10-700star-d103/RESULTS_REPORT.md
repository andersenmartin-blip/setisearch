# Phase `D103` (`V6.1`) Results Report: NASA *NuSTAR* (`3–79 keV`), *XMM-Newton* `RGS` (`5–38 Å`), `ALMA` Band 9 & Band 10 Complete 9-Band Closure, Orbits `#163–#168`, `60`-Campaign `DRIFT_V61`/`COMB_DRIFT_V61`, & `709`-Star Synthesis

**Phase ID:** `D103`  
**Detector:** `TECHNOSIGNATURE_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_AND_700STAR_SYNTHESIS`  
**Stage-1 Seal (`METHOD_LOCK.json`):** `2026-11-23T18:33:23.189575+00:00` (`70` locked targets = `53` brand-new + `17` prior bridges; `104` locked observations / `204` physical files; `inputs_d103_v6_1` absent at seal; `7/7` Stage-1 files byte-for-byte immutable)  
**Chronology Lag:** `+15.80 s` before first science download (`2026-11-23T18:33:38.99Z`)  
**Result:** **`0` verified technosignatures (`verified_eti_detections_total = 0`)** across **`709` unique analyzed stellar/extragalactic systems (`D079–D103`)**, **`0.0000157–8,556.41831 µm` (`29.022` total octaves)**, and **`29` Companion Archives (`A–Z, AA–AC`)**.

---

## 1. Executive Summary (`D103` & Unified `D079–D103` Survey)

1. **Stage-1 Prospective Lock, Stage-2 Archive Intake (`104/104` Valid Files, `1,490.4789 MiB`), & Transparent `ALTAIR` Quality Exclusion (`D101` Precedent):**
   - Excluding `729` prior coordinates and `3,368` prior `dp_id`s (`0` overlap, minimum prior sky separation `763.28''`, minimum intra-D103 separation `3,199.00''`), Stage 1 froze `70` unique targets (`53` brand-new incl. `5` strictly `< 10 pc` controls + `17` prior bridges; `104` observations / `204` physical FITS/FTZ/evt.gz files).
   - All **`104/104` (`100.0%`, `1,562,880,374 B = 1,490.4789 MiB`)** downloaded cleanly (`0` HTTP/FITS failures). Following `D101`'s transparent Stage-2 quality precedent with `7/7` Stage-1 files kept 100% byte-for-byte immutable, `1` observation (`ALTAIR XMM_0502360101_P0502360101R1S004SRSPEC1004.FTZ`) was excluded cleanly during extraction because ESA PPS `P0502360101R2S005SRSPEC1005.FTZ` (off-axis source #5) had `3,600/3,600` bins flagged `QUALITY = 1` (`0` usable RGS2 channels), leaving **`103/104` valid observations (`69` D103 targets = `53` brand-new + `16` prior bridges; `37` science + `32` control; `1,236.2302` integration hours)** packed into `bounded_inputs/d103_bounded_bundle.json.gz` (`15,603,592 B = 14.881 MiB <= 18.5 MiB`, SHA-256 `3246933c707dd7780049f575ffe4514c82d28aa7563e7d72904437bd879f590f`). Dual-mode `--from-full-inputs` vs `--from-bounded-inputs` yielded **`0` diffs** across all `36` result CSV/JSON files.

2. **NASA *NuSTAR* Hard X-Ray Dual-FPM Poisson Search (`NUSTAR_FPMA_FPMB`, `19` Pairs, `3–79 keV` / `0.157–4.13 Å`):**
   - Calibration `CALIBRATION_V61_NUSTAR_POISSON_240` passes **`240/240 (100.00%)`** (`60/60` clean dual-FPM beacons, `45/45` each for single-FPM glitch, NuSTAR Fe K / background atlas, Poisson continuum null, and broad Compton / 1-bin hump vetoes).
   - Across `19` archival FPMA+FPMB pairs (`8` bridges + `11` new), **`62`** raw Li & Ma `>=6 sigma` peaks (`59` deduplicated ledger rows) collapse through G4 dual-FPM coincidence, G3 atlas (`Fe Kalpha`, `Fe XXVI`, `Ca XIX`, internal `W/CsI/Sn/Ni`), G5 RMF width, and G6 spatial background gating to `0` pre-Stage-2 survivors (`0` verified ETI). Best `6-sigma` `10 m` equivalent EIRP bounds reach **`1.88431e-7 kW = 0.1884 mW` (`AUMIC`, `NUSTAR_HARD_30KEV @ 0.41328 Å`)**, **`2.88 mW` (`EKDRA`)**, and **`3.50 mW` (`HD222259A`)**.

3. **ESA/NASA *XMM-Newton* `RGS` High-Res X-Ray (`XMM_RGS`, `26` Dual-RGS Obs., `5–38 Å`) & `12.122` Unbroken High-Energy Octaves:**
   - Calibration `CALIBRATION_V61_XMM_RGS_180` achieves **`177/180 (98.33%)`** (`59/60` beacons, `40/40` single-camera/chipgap, `40/40` coronal atlas, `38/40` broad-wind/1-bin).
   - Across `26` analyzed dual-RGS observations, **`350`** raw peaks (`348` deduplicated ledger rows) collapse through G3 coronal/G4 single-RGS/G5 gating to `15` pre-Stage-2 survivors (`14` deduplicated `STAGE2_VETO_HELIKE_RRC_OR_STELLAR_WIND_BLEND` rows) -> **`0` verified ETI**. Best `10 m` bound reaches **`3.6165e-7 kW = 0.3617 mW` (`PROXIMACEN`, `RGS_SHORT_8A @ 8.0 Å`)**.
   - Bridging *NuSTAR* (`3–79 keV`), *XMM-Newton* `RGS` (`5–38 Å`), *Chandra* `HETG/LETG` (`1.2–175 Å`), and *EUVE* (`70–700 Å`) establishes **`[0.0000157, 0.06998] µm` = `12.122` strictly unbroken high-energy octaves** right up to the neutral hydrogen ISM photoionization wall (`699.8–905.0 Å`).

4. **ALMA Sub-mm Band 9 & Band 10 Complete 9-Band Receiver Closure (`ALMA_B9_0P4MM` + `ALMA_B10_0P3MM`, `20` Cubes):**
   - Scoring `10` Band 9 (`613.2062–713.1487 GHz = 420.379–488.893 µm`) and `10` Band 10 (`800.2106–893.3625 GHz = 335.578–374.642 µm`) single-pointing cubes (`19` unique targets; `239/240 = 99.58%` ALMA calibration) completes all `9/9` ALMA bands (**`B1, B3–B10`**) across **`29.022` total octaves (`0.0000157–8,556.41831 µm`)**.
   - All `20/20` cubes show clean noise floors (`0` raw `>=6 sigma` candidates -> **`0` verified ETI**), reaching **`138,160.08 kW` (`DMTAU B9`)** and **`149,882.94 kW` (`AS209 B10`)**.

5. **ESO `ESPRESSO`/`HARPS` Orbits `#163–#168` (`38` Spectra) & `60`-Campaign `DRIFT_V61`/`COMB_DRIFT_V61` (`D094–D103`):**
   - Orbits `#163–#168` (`HD134987`, `HD82943`, `HD196067` on `ESPRESSO`; `HD10180`, `HD134060`, `BD210397` on `HARPS`) plus `8` `<= 10.12 pc` 0-planet controls (`5` strictly `<= 10.0 pc`: `GJ257A`, `HD32450A`, `PMJ19070P2053`, `GJ867A`, `LHS1731`) yield best 10-m optical limits **`0.06270593 kW = 62.71 W` (`L480_69 ESPRESSO`)** and **`0.16380171 kW = 163.80 W` (`GJ867A HARPS`)**, `4-Gen` `26 -> 0` `G8` (`0` ETI), and `COMB_V4_1` `7,964,216` configs -> `4,744` cands -> `0` ETI (`501` cumulative all-sky stacks -> `0` ETI).
   - Across all **`60` campaigns (`D094–D103`)**, `DRIFT_V61` evaluates **`80,348` trajectories (`8,662,517,142` pixel-trajectory integrals -> `17,689` raw -> `565` Stage-1 survivors -> `0` verified ETI)** and `COMB_DRIFT_V61` evaluates **`9,858` trajectories (`3,659` raw -> `197` pre-S2 -> `0` verified ETI)**.

---

## 2. Calibration, Radiometric Closure (`C12`), & Unified `709`-Star Synthesis

- **Calibration (`15` Suites):** **`3,094 / 3,111` (`99.45%`)** passed (`>= 95%` on every suite; **`54,528`** cumulative trials `D079–D103`).
- **Radiometric Closure (`C12`):** Independent pure-stdlib recomputation across all **`265` `D103`** EIRP rows and **`1,002`** finite `PANCHROMATIC_BRIDGE_87STARS_V61.csv` rows (`1,267` rows total) yields `max_rel_err = 0.0005986394 < 0.002` (internal `D103` `analyze.py` closure `0.0000000000`).
- **Unified `D079–D103` Totals:** **`709` unique stars** (`519` Science [`238` planet hosts / `458` confirmed exoplanets] + `190` Control), **`188` unique `< 10 pc` stars** (median **`1.0483 kW`**; best `0.1884 mW` `AUMIC NuSTAR`), **`87` multi-phase science bridge stars** (`+16` revisited controls -> `103` multi-phase targets; **`1,016` bridge cells**), **`109` ETZ & `39 <= 180 d` Ellipsoid targets**, **`49` spectrographs / `79` spectral arms**, **`3,187` exposures (`4,723.4709 h`)**, **`894,016` Legacy V2 false alarms eliminated (`46,004` in `D103`)**, **`168` orbital campaigns**, **`60` `DRIFT_V61` + `COMB_DRIFT_V61` campaigns**, **`501` comb stacks**, and **0 verified ETI** across all **`29` Companion Archives (`A–Z, AA–AC`)**.
