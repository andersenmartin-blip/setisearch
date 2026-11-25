# Phase D108 (V6.6) Results Report: *IXPE* Polarimetry, SRG/*eROSITA*-DE DR1, *RXTE* HEXTE/PCA, ESO Orbits #193–#198 & 1,004-Star Synthesis

**Detector:** `TECHNOSIGNATURE_V6_6_IXPE_POLARIMETRY_EROSITA_DR1_RXTE_HEXTE_PCA_1000STAR_SYNTHESIS`  
**Phase ID:** `D108` (`V6.6`)  
**Workspace:** `analysis_workspace/work_v6_6_20261125_d108_ixpe_polarimetry_erosita_dr1_rxte_1000star`  
**Verified ETI Detections:** **`0`** (D108 and cumulative D079–D108)

---

## 1. Prospective Method Seal, Chronology & Exclusion Integrity

| Check | Verified Observed Value |
| :--- | :--- |
| Prospective `METHOD_LOCK.json` seal UTC | `2026-11-25T11:13:29.994080+00:00` (`locked_unix_epoch = 1795605209.9941`) |
| `METHOD_LOCK.json` SHA-256 | `e85f3f8cda7bbe55bd25c86399b46021cd054211168a9037afd8f1e1eb5c77a8` |
| `inputs_dir_exists_at_seal` | `false` |
| First science download UTC | `2026-11-25T11:14:01.641117+00:00` (`chronology_lag_seconds = +31.647 s`) |
| Prior excluded coordinates / `dp_id`s / format checks | `977` coords / `3,935` `dp_id`s / `46` format checks |
| Prior `dp_id` overlap count | `0` |
| Min brand-new sky separation / intra-D108 separation | `1828.38 arcsec` / `4218.55 arcsec` |
| Valid analyzed observations / physical archival files | `198 / 198` (`0` failed) / `385` physical files |
| Raw archival input volume | `1,852,606,839 B` (`1,766.7836 MiB`) |
| Bounded reproduction bundle (`d108_bounded_bundle.json.gz`) | `12,199,223 B` (`11.634 MiB <= 15.0 MiB`), SHA-256 `a3382b436bf7d12af1288a52add30fc1efd1b39ed5d30aed2f0eb8465be28a23` |
| Dual-mode zero-diff check (`--from-full-inputs` vs `--from-bounded-inputs`) | `56` top-level `results/` files compared, **`0` diffs (`ZERO_DIFF_VERIFIED`)** |

---

## 2. D108 Cohort, Exposure & X-Ray Spectro-Polarimetric Scope

- **Cohort (`145` locked targets):** `100` brand-new targets (`5` within `10 pc`: `ERO_8855002381`, `L 403-34`, `LP 655-48`, `SCR J0630-7643A`, `WD 0435-088`) + `45` prior multi-phase bridge targets (`116` `SCIENCE`, `29` `CONTROL`).
- **Integration accounting:** `2,165.3943 h` in `D108` across `198` observations (`385` physical archival files; `0` failed observations, `0` Stage-2 exclusions), advancing cumulative `D079–D108` exposure to `121,471.6962 h` across `3,847` exposures.
- **NASA/ASI *IXPE* GPD Spectro-Polarimetry (`2.0–8.0 keV`, `17` targets):** First X-ray spectro-polarimetric SETI search across dual Stokes $I$ + linear polarization Stokes $(Q, U)$ across all `3` Detector Units (`2,186,715` on-source events; `12` prior bridges + `5` new `CONTROL` targets).
- **SRG/*eROSITA*-DE DR1 (`0.2–8.0 keV`, `TM1–7`, `111` targets):** `106` `SCIENCE` + `5` `CONTROL` targets (`83` new `10–20 pc` + `9` `< 10 pc` [`4` new + `5` bridges] + `19` prior bridges `> 10 pc`) using `eROSITA-DE DR1` SourceProducts (odd/even `TM` split + `SRCGTI0` temporal split, `0.015 keV` grid).
- **NASA *RXTE* `HEXTE` (`15.0–250.0 keV`, `16` targets) & `PCA` Std2 (`2.0–60.0 keV`, `16` targets):** `6` `SCIENCE` (`ABDOR`, `ARLAC`, `AUMIC`, `HD22468`, `HD34029`, `IIPEG`) + `10` `CONTROL` targets (`15` prior bridges + `1` brand-new `AR Lac`) across Cluster A/B (`HEXTE`) and Std2 (`PCA`).
- **ESO `UVES` `<10 pc` (`8` spectra) & Planet-Host Orbits `#193–#198` (`30` spectra):** `WD 0435-088` (`6` UVES) and `LP 655-48` (`2` UVES, forming an intra-D108 `<10 pc` bridge with `EROSITA_DR1`), plus `6` brand-new `N=5` distinct-night orbits (`#193 GJ 317` `ESO_NIRPS` `441.89 d`, `#194 GJ 1252` `ESO_NIRPS` `593.65 d`, `#195 TOI-198` `ESO_ESPRESSO` `930.75 d`, `#196 TOI-244` `ESO_ESPRESSO` `369.81 d`, `#197 GJ 3293` `ESO_HARPS` `2,311.82 d`, `#198 7 CMa` `ESO_HARPS` `4,300.18 d`), feeding `DRIFT_V66` and `COMB_DRIFT_V66` across all `90` coherent orbital campaigns (`6` live + `84` retro from companion archives `T–Z, AA–AG`).

---

## 3. Calibration, Triage & Headline Upper Limits

- **Synthetic Calibration (`32` suites, `6,854 / 6,891` = `99.46%` passed; cumulative `81,123` trials):** Every suite passed `>= 97.5%`, including `V66_IXPE_POLARIMETRY_240` (`237/240`, `98.75%`), `V66_EROSITA_DR1_240` (`236/240`, `98.33%`), `V66_RXTE_HEXTE_180` (`180/180`, `100.00%`), `V66_RXTE_PCA_180` (`179/180`, `99.44%`), and all `28` inherited D107 suites (`6,022 / 6,051`).
- **High-Energy Triage (`145` pre-dedup raw peaks -> `143` NMS-deduplicated rows in `V6_6_HIGH_ENERGY_CANDIDATE_LEDGER.csv`, `0` verified ETI):**
  - `IXPE_GPD`: `46` Stokes-$I$ raw / `0` Stokes-$(Q,U)$ raw (`46` ledger rows) -> `2` pre-Stage-2 (`CENA@4.38KEV`, `MRK501@4.62KEV`, AGN continuum fluctuations) -> **`0` ETI**.
  - `EROSITA_DR1`: `62` pre-dedup raw (`61` NMS-deduplicated ledger rows) -> `0` pre-Stage-2 -> **`0` ETI**.
  - `RXTE_HEXTE`: `6` raw (`6` ledger rows) -> `3` pre-Stage-2 (`CYGX1@144.7KEV`, `EXHYA@17.4KEV`, `MRK421@17.4KEV`) -> **`0` ETI**.
  - `RXTE_PCA`: `31` pre-dedup raw (`30` NMS-deduplicated ledger rows) -> `2` pre-Stage-2 (`EXHYA@20.7KEV`, `HERX1@23.9KEV`) -> **`0` ETI**.
- **Optical / NIR & Coherent Drift Triage (`0` verified ETI):**
  - `optical_4gen` (`Orbits #193–#198` + `UVES <10 pc`): `207` G1 seeds (`3` `ESPRESSO`, `48` `HARPS`, `148` `NIRPS`, `8` `UVES`) -> `6` G8 pass (`4` `GJ3293` `ESO_HARPS`, `2` `GJ1252` `ESO_NIRPS` in `V6_6_CANDIDATE_LEDGER.csv`) -> **`0` ETI**.
  - `DRIFT_V66` (`90` campaigns): `125,549` trajectories / `15,627,501,311` pixel-trajectory integrals -> `33,424` raw coherent survivors (`3,590` eccentric Keplerian survivors; `929` ledger rows) -> **`0` ETI**.
  - `COMB_DRIFT_V66` (`90` campaigns): `19,201` comb-drift trajectories -> `5,803` raw -> `222` pre-Stage-2 (`65` V4.1 static hits; `631` ledger rows) -> **`0` ETI**.
  - `comb_v4_1`: `3,547,168` configs -> `3,954` candidates (`33,627` cumulative candidates across `578` cumulative stacks) -> **`0` ETI**.
  - `v2` false-alarm rejections in `D108`: `26,461` (`1,118,698` cumulative).
- **Headline Physical Constraints & Radiometric Closure (`C12`):**
  - *IXPE* GPD (`2–8 keV`): deepest broadband `MDP99 = 2.086%` on `VELAX1` (`IXPE_2P5KEV`); deepest polarized flux limit `1.679832e-13 erg cm^-2 s^-1` (`NGC4945`, `IXPE_4P0KEV`); deepest formal `10 m` EIRP `0.00138766908 kW` (`EXHYA`, `IXPE_6P0KEV`, $F_{\mathrm{lim}} = 8.276896 \times 10^{-13}\,\mathrm{erg\,cm^{-2}\,s^{-1}}$).
  - SRG/*eROSITA*-DE DR1: deepest `10 m` EM EIRP `5.978702e-6 kW` (`5.98 mW`, $F_{\mathrm{lim}} = 7.037853 \times 10^{-14}\,\mathrm{erg\,cm^{-2}\,s^{-1}}$ on `EPSERI`, `ERO_1P5KEV`; deepest flux `1.140321e-14 erg cm^-2 s^-1` on `ABDOR`, `<10 pc` `SCRJ06307643A` at `9.841634e-6 kW`).
  - *RXTE* HEXTE: deepest `10 m` EM EIRP `1.7748268e-5 kW` (`HD34029`, `HEXTE_100KEV`, $5.689303 \times 10^{-11}\,\mathrm{erg\,cm^{-2}\,s^{-1}}$).
  - *RXTE* PCA: deepest `10 m` EM EIRP `1.4848924e-5 kW` (`AUMIC`, `PCA_45KEV`, $1.707094 \times 10^{-11}\,\mathrm{erg\,cm^{-2}\,s^{-1}}$; `HD34029` `1.506959e-5 kW` at `PCA_10KEV`).
  - Deepest ESO `D108` `10 m` EM EIRP: `ESO_UVES` (`WD0435_088`, `U3_6800`) `0.000137431281 kW` (`0.137 W`), `ESO_ESPRESSO` (`TOI244`, `ESPRESSO_BLU_4200`) `0.36648718 kW`, `ESO_HARPS` (`GJ3293`, `H1_4100`) `1.03039635 kW`, `ESO_NIRPS` (`GJ1252`, `N2_10640`) `5.88412573 kW`.
  - `C12` EM closure (`657` rows in `EIRP_UPPER_LIMITS_D108.csv`): `c12_radiometric_max_rel_err = 0.0` (exact $L_{\mathrm{iso}} = 4\pi d^2 F$ & $(\pi D/\lambda)^2$ beam gain within `< 1e-5`), and `126 / 126` `ICECUBE_10YR` rows in `PANCHROMATIC_BRIDGE_155STARS_V66.csv` preserve strict zero-EM-beam compliance (`p_beam_10m_kw == ""`, `p_beam_10m_w == ""`, `wave_A == ""`, `wave_um == ""`; `0` IceCube rows in `EIRP_UPPER_LIMITS_D108.csv`).

---

## 4. Cumulative D079–D108 1,004-Star Quad-Messenger Synthesis

- **Archive & Instrument Continuity:** `34` Companion Archives (`A–Z, AA–AH`), `66` spectrographs / `96` spectral arms, `60.845` EM octaves (`4.1328066e-15 um` to `8556.41831 um`), `43.945` unbroken high-energy octaves (`[4.1328066e-15, 0.06998] um`), `13.935` strict zero-gap Lyman-to-mm octaves (`0.0905 -> 1417.76119 um`; `14.693` octaves to `2397.28632 um` ALMA B4 low edge), plus `0.1 TeV–10 PeV` IceCube muon neutrinos and `2.0–8.0 keV` *IXPE* X-ray polarimetry.
- **Sample Totals (`UNIFIED_PANCHROMATIC_V6_6_SYNTHESIS_1004STARS.csv`):** `1,004` unique stars (`753` `SCIENCE`, `251` `CONTROL`; `298` planet hosts with `543` confirmed exoplanets), `267` stars within `10 pc` (`212` `SCIENCE` [`61` hosts / `121` planets] + `55` `CONTROL`; global median `0.380594 kW`, optical/IR median `0.6058 kW`), `194` `ETZ` & `41 <= 180 d` SETI Ellipsoid targets (`MULTIEVENT_ELLIPSOID_1004STARS.csv`).
- **Multi-Phase Bridge Totals (`PANCHROMATIC_BRIDGE_155STARS_V66.csv`):** `155` multi-phase `SCIENCE` bridges (`10` promoted in `D108`: `AFLEP`, `BETACMA`, `BETACRU`, `EIERI`, `EPSCMA`, `GJ504`, `HD35296`, `REGULUS`, `ZETAORI`, `ZETAPUP` + intra-D108 `<10 pc` `LP655_48`) + `44` multi-phase `CONTROL` targets = `199` multi-phase targets (`2,334` bridge cells = `126` IceCube neutrino + `2,208` EM rows).
- **Cumulative Search Totals:** `3,847` exposures, `121,471.6962 h` integration, `81,123` calibration trials, `198` cumulative orbital campaigns (`90` coherent eccentric Keplerian & drifting comb campaigns), `578` comb stacks, `1,118,698` v2 false-alarm rejections, **`0` verified ETI detections**.
