# Phase D092 Results Report (`TECHNOSIGNATURE_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF`)

## 1. Executive Summary
Phase **D092** deploys the literature-derived **V5.0** unsupervised & synchronization-prioritized technosignature architecture across **28 ESO Phase-3 stars** (**25** brand-new targets including **11** within `10 pc` + **3** `CRIRES+` Y-band panchromatic bridges: `TRAPPIST1`, `K218`, `PROXIMACEN`; **6** verified zero-planet controls + **22** science targets) and **57 exposures** (`24` `ESO_HARPS`, `20` `ESO_FEROS`, `13` `ESO_CRIRES` Y-band `9496–11205 Å`; `12.6625 h` integration across `34` ESO Program IDs), plus two retroactive Companion Archive sweeps (`D091` `156` exposures via Archive Q and `D090` `65` `JWST_MIRI_MRS` exposures via Archive P).

Integrating Phase **D092** extends the unified panchromatic **D079–D092** survey across **19 spectrographs (22 spectral arms)** and **8.273 unbroken octaves (`0.0905–28.00 µm`)** to **335 unique stars (`146 < 10 pc`, median `1.57296 kW`; `37` panchromatic bridges across `631` cells)**, **2,133 archival exposures (`647.0511 h`)**, **`30,817` synthetic calibration trials**, **`109` orbital campaigns (`#1–#109`)**, **`386` all-sky `COMB_V4_1` stacks**, and **`301,190` legacy `V2` false alarms eliminated** — with **zero verified extraterrestrial technosignature detections (`0 ETI`)**.

---

## 2. Prospective Lock, Chronology & Exclusion Verification
- **Prospective Method Lock (`METHOD_LOCK.json` / `LOCK_RECEIPT.json`):** Sealed at `2026-11-20T20:27:32Z` (`METHOD_LOCK` SHA-256 `1e129d427b0ed8598374f737a4e2831e0a69174b408b0c7a9774233e4f2edd1a`) with `inputs_d092_v5_0/` verified absent prior to lock.
- **ESO Phase-3 Ingestion (`FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`):** Initiated at `2026-11-20T20:27:37Z` (`+5.0 s` post-lock lag); downloaded `57/57` validated FITS (`209.28 MiB <= 225 MiB`; `7.45 GiB` disk free).
- **Pre-Lock Exclusion (`PRIOR_EXCLUSION_VERIFICATION.json`):** `0` DP-ID overlaps against `2,525` prior exposure IDs (`C001–D091`); minimum prior sky separation across the `25` brand-new targets is `164.18"` (`HD16160` vs `GJ105B(D087)`), minimum intra-D092 separation `20,007.02"`.
- **Dual-Mode Deterministic Bundle:** `bounded_inputs/d092_bounded_bundle.json.gz` is `23.93 MiB (< 25.0 MiB)`. Stage B produces **100% SHA-256 bit-identical** outputs (`29/29` files, `diffs = []`) between `--from-full-inputs` and `--from-bounded-inputs`, and identically in clean-room restoration.

---

## 3. Five V5.0 Engines & 1,351-Trial Calibration Scorecard (7 Suites)
| Calibration Suite | Trials | Verified Result |
|---|---:|---|
| 1. Unsupervised RPCA + `Teff`-LOSO & Rarity (`G7_V50`) | 180 | Isolated Laser `56/60 (93.33%)`, Shared Photospheric Suppression `60/60 (100.00%)`, Topo Repeat Suppression `60/60 (100.00%)` |
| 2. Dual-Polarity Agnostic Multi-Scale (`2, 4, 8, 14 LSF`; Gaussian & Boxcar) | 120 | Recovery `118/120 (98.33%)` |
| 3. `JWST_MIRI_MRS` Greenhouse Gas CCF (`CF4, C2F6, SF6, NF3`) | 160 | Greenhouse Recovery `74/80 (92.50%)`, Confounder Veto (`CH4, O3, Silicate, PAH`) `80/80 (100.00%)` |
| 4. Narrowband Injection Recovery (`HARPS`, `FEROS`, `CRIRES`) | 540 | `Channel T (>=8 sigma) = 152/162 (93.83%)`, `Channel P (>=8 sigma) = 152/162 (93.83%)` |
| 5. Keplerian Orbital De-Doppler Track (`>= 6.5 sigma`) | 81 | `T_DIFF = 0/81 (0.00%)`, `K_PLANET = 80/81 (98.77%)` |
| 6. Detector Physics (`G4 + G5`) | 108 | True Laser `36/36 (100.0%)`, Cosmic Hot-Pixel Rej. `36/36 (100.0%)`, M-Dwarf Plateau Rej. `36/36 (100.0%)` |
| 7. Optical Frequency Comb (`COMB_V4_1`) | 162 | 6-Tooth `>= 3.8 sigma = 36/36 (100.0%)`, Dense Forest `54/54 V4 -> 0/54 V4.1`, Topo Comb `0/54` |

---

## 4. Empirical Results Across All 4 Detection Streams & Geometric Tracks
1. **D092 Single-Line & V5.0 RPCA + `G7_V50` Cascade:** Searching `7,949,385` Channel `T`, `3,966,420` Channel `P`, `1,254,938` `T_DIFF`, and `1,254,700` `K_PLANET` bins collapses `15,147` Legacy `V2` triggers $\rightarrow$ `3,461` `G1` $\rightarrow$ `3,435` `G2` $\rightarrow$ `3,419` `G3` $\rightarrow$ `1,601` `G4` $\rightarrow$ `925` `G5` $\rightarrow$ `815` `V4.2 G6` $\rightarrow$ **`146` `V5.0 G7` survivors** (`669` additional vetoed; `6` control + `140` science: `41` single-epoch residual, `37` FEROS blue UV `<4000 Å` roll-off/order edge, `34` M-dwarf TiO/flare, `16` telluric/`O2`/`H2O`, `12` persistent pseudo-continuum, `4` chromospheric wing, `2` `HD56986` fast rotator) $\rightarrow$ **`0 verified ETI`**.
2. **Retroactive D091 Regression (`98.815%` Suppression):** Scoring all `2,362` `D091` `V4.2` auto-qualified survivors through the `V5.0` Masked Inexact-ALM RPCA + `Teff`-LOSO & Rarity manifold suppresses **`2,362 -> 28` (`98.815%` elimination)**: `SCR1845` `1,050 -> 11`, `LP94420` `474 -> 8`, `GJ1128` `382 -> 0`, and `HD213885` `85 -> 0`.
3. **Dual-Polarity Agnostic Multi-Scale Matched Filter (`14,274` evaluations):** Recovers **`107` natural/instrumental survivors** across `26` stars (`26` M-dwarf molecular/pseudo-continuum, `23` FEROS `<4000 Å` roll-off, `23` `CRIRES+` chip-gap edge/telluric, `16` photospheric residual, `10` Przybylski's Star `HD101065` lanthanide/peculiar atomic features, `6` telluric, `3` chromospheric wings) $\rightarrow$ **`0 verified ETI`**.
4. **Geometric Synchronization Tracks & Orbital Campaigns (`#101–#109`):**
   - **Earth Transit Zone (ETZ, `|beta| <= 0.264 deg`):** `5` targets (`ESPRI1542`, `HATS521`, `HD28343`, `HD56986`, `HIP95417`) -> `0` ETI.
   - **SN 1987A SETI Ellipsoid (`|dt| <= 180 d`, `< 10 pc`):** `6` targets (`GL250B` `64.6d`, `GL465` `28.6d`, `GL618A` `92.8d`, `HD16160` `28.3d`, `J16570570` `89.6d`, `V2215OPH` `116.7d`) -> `0` ETI.
   - **9 PPO Multi-Planet Campaigns (`#101–#109`, `dv_span = 7.09–310.78 km/s`):** `HIP41378`, `K2138`, `HD3167`, `LHS1678`, `HD108236`, `TOI5789`, `TOI1203`, `TRAPPIST1`, `K218` yielded **`0` `K_PLANET` and `0` `T_DIFF` hits -> `0 verified ETI`**.
5. **Frequency Comb (`COMB_V4_1`) & All-Sky `386`-Stack Sweep:** Across `13,906,744` comb configs in D092, `64` automated FEROS candidates (`45` on fast rotator `HD56986`, `19` blue UV line congestion; `0` HARPS / `0` CRIRES) yield `0` ETI. Cumulatively across **386 stacks / 2,133 exposures (`D079–D092`)**, `22,691 COMB_V4 -> 109 COMB_V4_1 -> 0 verified ETI`.
6. **Retroactive D090 `JWST_MIRI_MRS` Greenhouse Gas CCF (`60` Cells, `0.07 µm` Dichroic Edge-Trimmed):** Trimming `0.07 µm` dichroic roll-off edges eliminates all disk-quiet/control artifacts (`16CYGB`, `ETACRV`, `HD163466`, `HD159222`, `HD2811`, `VMA2` all consistent with noise; median 5-sigma sensitivity: `CF4 = 5.91%`, `C2F6 = 3.12%`, `SF6 = 2.61%`, `NF3 = 1.96%`). The `4` flagged cells (`BETPIC C2F6 +9.0 sigma`, `PDS70 C2F6 +48.8 sigma`, `OBJECT_D SF6 +5.1 sigma`, `OBJECT_E NF3 +7.9 sigma`) map forensically to young circumstellar silicate disks and faint extragalactic DOG continua -> **`0 verified ETI`**.

---

## 5. Upper Limits (`122` Cells) & Unified `335`-Star Panchromatic V5.0 Census
- **Best D092 10 m CW Transmitter Limits (`122` cells, Gaia-`G` Planck CGS):**
  - **Overall / `ESO_FEROS`:** `ESPRI1542` (`F1_4100`, `4100 Å`): **`0.49515 kW` (`495.153 W`)**
  - **`ESO_HARPS`:** `LHS1678` (`H1_4100`): **`0.52481 kW`**
  - **`ESO_CRIRES` Y-band:** `TRAPPIST1` (`C2_10450`/`Y`): **`1.18663 kW`**
- **Unified `D079–D092` Synthesis (`8.273` Octaves, `0.0905–28.00 µm`):**
  - `335` unique stars (`146` within `10 pc` with median **`1.57296 kW`**), `37` panchromatic bridge stars (`631` cells in `PANCHROMATIC_BRIDGE_35STARS_V50.csv`), `2,133` exposures (`647.0511 h`), `30,817` calibration trials, `109` orbital campaigns, `301,190` V2 false alarms eliminated, **`0` verified ETI detections**.
