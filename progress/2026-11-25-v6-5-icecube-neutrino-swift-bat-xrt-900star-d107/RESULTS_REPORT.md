# Phase D107 (V6.5) Results Report: IceCube 10-Yr Neutrinos, *Swift*-BAT 157m, *Swift*-XRT, ESO Orbits #187–#192 & 904-Star Quad-Messenger Synthesis

**Detector:** `TECHNOSIGNATURE_V6_5_ICECUBE_NEUTRINO_SWIFT_BAT_XRT_900STAR_QUADMESSENGER_SYNTHESIS`  
**Phase ID:** `D107` (`V6.5`)  
**Workspace:** `analysis_workspace/work_v6_5_20261125_d107_icecube_neutrino_swift_bat_xrt_900star`  
**Verified ETI Detections:** **`0`** (D107 and cumulative D079–D107)

---

## 1. Prospective Method Seal, Chronology & Exclusion Integrity

| Check | Verified Observed Value |
| :--- | :--- |
| Prospective `METHOD_LOCK.json` seal UTC | `2026-11-25T04:52:06.622933+00:00` (`locked_unix_epoch = 1795582326.6229`) |
| `METHOD_LOCK.json` SHA-256 | `bcd50d5040defa98c6f54630658537eb014ad5fe462f532e1141973522f20644` |
| `inputs_dir_exists_at_seal` | `false` |
| First science download UTC | `2026-11-25T04:52:27.897404+00:00` (`chronology_lag_seconds = +21.275 s`) |
| Prior excluded coordinates / `dp_id`s / format checks | `925` coords / `3,801` `dp_id`s / `46` format checks |
| Prior `dp_id` overlap count | `0` |
| Min brand-new sky separation / intra-D107 separation | `2676.03 arcsec` / `7993.17 arcsec` |
| Valid analyzed observations / physical archival files | `134 / 134` (`0` failed) / `59` physical files |
| Raw archival input volume | `999,332,310 B` (`953.0376 MiB`) |
| Bounded reproduction bundle (`d107_bounded_bundle.json.gz`) | `14,511,917 B` (`13.840 MiB`), SHA-256 `aad0b054982277375b6e1676e1edfdf3994f6e41a4f97964928a5e4aa6cc021a` |
| Dual-mode zero-diff check (`--from-full-inputs` vs `--from-bounded-inputs`) | `52` files compared, `0` diffs |

---

## 2. D107 Cohort, Exposure & Multi-Messenger Scope

- **Cohort (`99` locked targets):** `52` brand-new targets (`18` within `10 pc` from Gaia DR3) + `47` prior multi-phase bridge targets (`76` `SCIENCE`, `23` `CONTROL`).
- **Integration accounting (honest deduplicated):** `92,344.3857 h` total (`85,868.7846 h` unique IceCube 10-Yr livetime = `3,577.8660` live-days + `6,414.1211 h` mean *Swift*-BAT 157m exposure + `61.4801 h` pointed *Swift*-XRT & ESO optical/NIR); per-target exposure sum = `4,829,399.4792 h`.
- **IceCube 10-Yr Point-Source Neutrino Release (`IC40–IC86_VII`, DOI `10.21234/CPKQ-K003`):** `54` targets (`51` `SCIENCE` + `3` `CONTROL`; `32` within `10 pc`), `1,134,450` events across `0.1 TeV–10 PeV` (`5.0` energy decades; grid `0.5, 2.0, 10.0, 50.0, 250.0, 1000.0 TeV`), strict zero-EM-beam policy (no `10 m` diffraction beam formula; genuine $\Phi_{\nu,\mathrm{lim}}$, $E\Phi_\nu$, $F_{\nu,\mathrm{lim}}$, and $L_{\nu,\mathrm{iso}}$ only).
- **NASA *Swift*-BAT 157-Month Hard X-Ray Survey (`bs157mon`, `14–195 keV`):** `30` targets (`9` `SCIENCE`, `21` `CONTROL`), `8` spectral channels with official `.rsp` (`0.28%` Crab calibration) and `M1–78` vs `M79–157` temporal split.
- **NASA *Swift*-XRT (`0.3–10 keV`):** `20` targets (`15` Photon Counting `GRADE 0–12`, `alpha_spat = 1/21` + `5` Windowed Timing `GRADE 0–2`, `alpha_spat = 1/3`; `12` `SCIENCE`, `8` `CONTROL`) with CALDB ARF/RMF response calibration.
- **ESO Planet-Host Orbits `#187–#192`:** `6` brand-new `N=5` orbits (`30` spectra) across `ESO_ESPRESSO` (`L363_38`, `TOI771`), `ESO_HARPS` (`GJ27_1`, `HIP12961`, `GJ3634`), and `ESO_NIRPS` (`GJ328`), feeding `DRIFT_V65` and `COMB_DRIFT_V65` across all `84` multi-epoch orbital campaigns (`6` live + `78` retro from companion archives `T–Z, AA–AF`).

---

## 3. Calibration, Triage & Headline Upper Limits

- **Synthetic Calibration (`28` suites, `6,022 / 6,051` passed; cumulative `74,232` trials):** Every suite passed `>= 97.5%`, including `V65_ICECUBE_NEUTRINO_240` (`237/240`, `98.75%`), `V65_SWIFT_BAT_240` (`239/240`, `99.58%`), `V65_SWIFT_XRT_180` (`178/180`, `98.89%`), and `G8_V58_120` (`117/120`, `97.50%`).
- **High-Energy & Multi-Messenger Triage (`115` rows in `V6_5_MULTIMESSENGER_CANDIDATE_LEDGER.csv`, `0` verified ETI):**
  - `ICECUBE_10YR`: `21` raw triggers -> `0` pre-S2 -> `0` ETI.
  - `SWIFT_BAT`: `38` raw -> `7` pre-S2 (`CHCYG@28.98KEV`, `FOAQR@28.98KEV`, `GAMMACAS@28.98KEV`, `MRK421@16.73KEV`, `SCOX1@16.73KEV`, `SCOX1@28.98KEV`, `TVCOL@28.98KEV`) -> `0` ETI.
  - `SWIFT_XRT`: **`63` pre-NMS raw extrema** (counted in `n_raw` prior to non-maximum suppression) -> **`56` NMS-deduplicated ledger entries** in `V6_5_MULTIMESSENGER_CANDIDATE_LEDGER.csv` -> `0` pre-S2 -> `0` ETI. Total ledger rows = `21 + 38 + 56 = 115`.
- **Optical / NIR & Coherent Drift Triage (`0` verified ETI):**
  - `optical_4gen` (`Orbits #187–#192`): `138` G1 seeds -> `0` G8 -> `0` ETI (`V6_5_CANDIDATE_LEDGER.csv` has `0` rows).
  - `DRIFT_V65` (`84` campaigns): `116,865` trajectories / `14,267,321,081` pixel-trajectory integrals -> `30,605` raw -> `3,471` eccentric Keplerian survivors (`858` ledger rows) -> `0` ETI.
  - `COMB_DRIFT_V65` (`84` campaigns): `17,599` comb trajectories -> `5,554` raw -> `216` pre-S2 (`GJ27_1=2`, `TOI771=3`, `HIP12961=2` in live orbits) -> `0` ETI.
  - `comb_v4_1`: `2,863,724` configs -> `4,283` candidates -> `0` ETI (`570` cumulative stacks).
  - `v2` false-alarm rejections in `D107`: `1,392` (`1,092,237` cumulative).
- **Headline Physical Constraints & Radiometric Closure (`C12`):**
  - `16CYGB` (first Quad-Messenger exoplanet bridge): `IC_10TEV` $\Phi_{\nu,\mathrm{lim}} = 5.56250966 \times 10^{-13}\,\mathrm{cm^{-2}\,s^{-1}}$ ($L_{\nu,\mathrm{iso}} = 4.76010248 \times 10^{16}\,\mathrm{MW}$); best `IC_50TEV` $\Phi_{\nu,\mathrm{lim}} = 5.65381676 \times 10^{-14}\,\mathrm{cm^{-2}\,s^{-1}}$ ($F_\nu = 4.52920656 \times 10^{-12}\,\mathrm{erg\,cm^{-2}\,s^{-1}}$, $L_{\nu,\mathrm{iso}} = 2.41911914 \times 10^{16}\,\mathrm{MW}$).
  - Deepest IceCube `SCIENCE` flux (`HD165341`, `IC_250TEV`): $\Phi_{\nu,\mathrm{lim}} = 7.78495213 \times 10^{-15}\,\mathrm{cm^{-2}\,s^{-1}}$ ($F_\nu = 3.11821710 \times 10^{-12}\,\mathrm{erg\,cm^{-2}\,s^{-1}}$, $L_{\nu,\mathrm{iso}} = 9.75494773 \times 10^{14}\,\mathrm{MW}$); minimum `<10 pc` IceCube isotropic neutrino luminosity bound `4.67587807e14 MW`.
  - Deepest *Swift*-BAT `10 m` EM EIRP (`SSCYG`): `1.3456826e-4 kW` (`4.284732e-12 erg cm^-2 s^-1`); `MRK421` control `BAT_87KEV` `3.803601e-12 erg cm^-2 s^-1`.
  - Deepest *Swift*-XRT `10 m` EM EIRP (`PROXIMACEN`): `9.07157141e-08 kW` (`8.686446e-14 erg cm^-2 s^-1`); `TRAPPIST1` `XRT_5P5KEV` `3.608328e-14 erg cm^-2 s^-1`.
  - Deepest ESO `D107` `10 m` EM EIRP: `ESO_ESPRESSO` (`L363_38`) `0.04861853 kW`, `ESO_HARPS` (`GJ3634`) `0.80341692 kW`, `ESO_NIRPS` (`GJ328`) `18.46090515 kW`.
  - `C12` EM closure (`368` rows in `EIRP_UPPER_LIMITS_D107.csv`): `c12_radiometric_max_rel_err = 0.0` (exact $L_{\mathrm{iso}} = 4\pi d^2 F$ & $(\pi D/\lambda)^2$ beam gain within `< 1e-6`), and `126 / 126` IceCube rows in `PANCHROMATIC_BRIDGE_145STARS_V65.csv` carry empty `p_beam_10m_kw`.

---

## 4. Cumulative D079–D107 Quad-Messenger Synthesis

- **Archive & Instrument Continuity:** `33` Companion Archives (`A–Z, AA–AG`), `62` spectrographs / `92` spectral arms, `60.845` EM octaves (`4.1328066e-15 um` to `8556.41831 um`), `43.945` unbroken high-energy octaves (`[4.1328066e-15, 0.06998] um`), `13.935` strict zero-gap Lyman-to-mm octaves (`0.0905 -> 1417.76119 um`; `14.693` octaves to `2397.28632 um` ALMA B4 low edge), plus `0.1 TeV–10 PeV` (`5.0` decades) IceCube muon neutrinos.
- **Sample Totals (`UNIFIED_PANCHROMATIC_V6_5_SYNTHESIS_904STARS.csv`):** `904` unique stars (`659` `SCIENCE`, `245` `CONTROL`; `292` planet hosts with `532` planets), `262` stars within `10 pc` (`208` `SCIENCE` [`61` hosts / `121` planets] + `54` `CONTROL`; global median `0.491505 kW`, optical/IR median `0.6317 kW`).
- **Multi-Phase Bridge Totals (`PANCHROMATIC_BRIDGE_145STARS_V65.csv`):** `145` multi-phase `SCIENCE` bridges + `32` multi-phase `CONTROL` targets = `177` multi-phase targets (`192` distinct bridge stars across `2,067` cells = `126` IceCube neutrino + `1,941` EM rows).
- **Cumulative Search Totals:** `3,649` exposures, `119,306.3019 h` integration, `74,232` calibration trials, `192` orbital campaigns (`84` coherent eccentric Keplerian & drifting comb campaigns), `570` comb stacks, `1,092,237` v2 false-alarm rejections, **`0` verified ETI detections**.
