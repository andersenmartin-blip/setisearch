# Centennial Phase D100 (V5.8) Scientific Results Report

**Phase ID:** `D100` (`TECHNOSIGNATURE_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN`)  
**Stage-1 Seal (UTC):** `2026-11-22T20:01:56.285999+00:00` (`inputs_dir_exists_at_seal = false`)  
**First Science Download (UTC):** `2026-11-22T20:02:14.638066+00:00` (`chronology_lag_seconds = 18.3521 s`)  
**Primary Result:** **`0` Verified ETI Detections** across **`560`** unique stellar systems, **`39`** spectrographs (**`62`** spectral arms), **`13.919` unbroken octaves (`0.0905–1,401.36089 µm`)**, explicit Band-3 atmospheric window gap **`[1,401.36089, 3,437.3982] µm`**, and long-wavelength 3 mm frontier **`3,856.0502 µm` (`15.379` total octaves)**

---

## 1. Cryptographic Sealing, Prior Exclusion & Reproducibility

- **`LOCK_RECEIPT.json` SHA-256:** `5f37bae109be7fbac291feeaba783b3233e24c59468929ff069b5b1e6121b4db`
- **`METHOD_LOCK.json` SHA-256:** `8d37e457312fe16c1876bea750ffbb87ed12149176daeac7ef571c691d4beb89`
- **`v5_8_detector.py` (Stage-1 immutable) SHA-256:** `c3c2eb1f1d5abf83f5dc148bafdf3adf62b632043c0518557e45eb912a2c904f`
- **Prior Exclusion Verification (`C001–C037 + D001–D099`):** `588` prior coordinates, `3,080` prior `dp_ids` (+ `15` format-check excluded `dp_ids`), `0` `dp_id` overlaps, minimum brand-new sky separation `358.0 arcsec`, minimum intra-D100 separation `996.76 arcsec`.
- **Raw Cohort & Bounded Bundle:** `79` FITS/gz exposures (`128,692,159 B` = `122.7304 MiB`; `82.0058 h`) compacted deterministically into `bounded_inputs/d100_bounded_bundle.json.gz` (`8,986,926 B` = `8.5706 MiB <= 18.5 MiB`, SHA-256 `4923b95a95da48ce036e1adbfa0402f0023afa23db32e874c3079083077b036d`).
- **Clean Bit-Identity Verification (`analyze.py --from-bounded-inputs`):** `41/41` result CSV/JSON files reproduced with `0` byte/SHA-256 differences.

---

## 2. Phase D100 Cohort Composition & Bridge Promotions

- **D100 Cohort (`57` unique stars, `79` exposures; `42` Science, `15` Control):**
  - **`44` Brand-New Unique Systems:** `34` Science + `10` Zero-Planet Controls (raising cumulative unique systems from `516` to **`560`**).
  - **`13` Revisited Systems:** `8` Science (`ABAUR`, `BETELGEUSE`, `CHICYG`, `HD115617`, `IRC10216`, `RCAS`, `RLEO`, `TXCAM`) + `5` Controls (`AFGL2591`, `AFGL2688`, `CRL618`, `HD114710`, `NGC7027`).
  - **`+3` Newly Promoted Science Bridges (`71 -> 74` Bridges, `855` Cells, `81` Multi-Phase Targets):** `AFGL437` (`SOFIA/FIFI-LS` dual `BLU` + `RED`), `CHICYG` (`D097` `Herschel HIFI` + `D100` `JCMT 'Alaihi 3mm`), and `HD147513` (`ESO FEROS` + `IUE LWP_HI`), plus `AFGL2591` newly multi-phase control (`6 -> 7` revisited controls).
  - **New Solar-Neighborhood (`<10 pc`) Target:** `+1` brand-new (`HD103095` / Groombridge 1830 at `9.1781 pc`, `IUE LWP_HI`), raising the `<10 pc` census from `175` to **`176` stars** (median **`1.4924 kW`**).

---

## 3. V5.8 Synthetic Calibration Scorecard (`2,331` Trials Across `12` Suites; Cumulative `46,455`)

| Suite | Passed / Trials | Rate | Notes |
| --- | ---: | ---: | --- |
| `CALIBRATION_V58_JCMT_ALAIHI_180` | `180 / 180` | `1.0000` | Clean 3 mm beacon (`60/60`), standing wave, broad outflow, 1-ch LO spur (`40/40` each) |
| `CALIBRATION_V58_SOFIA_FIFILS_180` | `180 / 180` | `1.0000` | Clean far-IR beacon (`60/60`), ATRAN telluric, 1-px glitch, broad feature (`40/40` each) |
| `CALIBRATION_V58_IUE_UV_180` | `180 / 180` | `1.0000` | Clean UV beacon (`60/60`), geocoronal LyA/OI, CR glitch, order overlap (`40/40` each) |
| `CALIBRATION_V58_ECCENTRIC_KEPLERIAN_360` | `359 / 360` | `0.9972` | High-eccentricity (`e = 0.55–0.94`) exact Keplerian **`59/60`** vs. circular **`55/60`** (`0.9167`) vs. Taylor **`34/60`** (`0.5667`); circular `60/60`, cubic jerk `60/60`, short periodic `60/60`, stationary/transient/BERV vetos `40/40` each |
| `CALIBRATION_V58_G6_COINCIDENCE_120` | `120 / 120` | `1.0000` | BERV-shifted beacon recovery vs. multi-star & stationary coincidence vetos |
| `INJECTION_RECOVERY_540` | `540 / 540` | `1.0000` | Multi-band empirical injection recovery (`pass_p` across D100 spectrographs) |
| `COMB_V4_1_CALIBRATION_162` | `160 / 162` | `0.9877` | `COMB_V4_1` laser frequency comb vetting |
| `DETECTOR_V58_G4G5_CALIBRATION_108` | `108 / 108` | `1.0000` | Gates G4/G5 shape & artifact vetos |
| `KEPLERIAN_TRACK_CALIBRATION_81` | `81 / 81` | `1.0000` | Multi-epoch orbital track recovery |
| `CALIBRATION_V58_RPCA_RARITY_180` | `179 / 180` | `0.9944` | RPCA rarity Gate G7 |
| `CALIBRATION_V58_AGNOSTIC_120` | `119 / 120` | `0.9917` | Multi-scale agnostic matched filtering |
| `CALIBRATION_G8_V58_120` | `115 / 120` | `0.9583` | Gate G8 `v52` local patch novelty (`35/40` isolated, `40/40` shared leak, `40/40` topo leak) |
| **Total D100 (12 Suites)** | **`2,321 / 2,331`** | **`0.9957`** | Cumulative `D079–D100`: **`46,455` trials** |

---

## 4. Stream-by-Stream Observational & Forensic Vetting Results (`0` Verified ETI)

### Stream 1A: JCMT 'Alaihi 3 mm Band-3 Heterodyne (`23` Stars / `23` Cubes, `77.74599–87.21494 GHz`)
- **Spectral Frontier & Honest Gap Disclosure:** Extends the long-wavelength frontier to **`3,856.0502 µm`** (`OH231P8` at `77.74599 GHz`, `15.379` total octaves from `0.0905 µm`), cleanly disclosing the observed Band-3 atmospheric window gap **`[1,401.36089, 3,437.3982] µm`** (`1.40–3.44 mm`) beyond **`13.919` unbroken octaves (`0.0905–1,401.36089 µm`)**.
- **Triage (`11` Raw Peaks -> `0` Qualified -> `0` Verified ETI):** `5` `G5_ALAIHI_LO_SPUR_1CHAN`, `3` `G3_ALAIHI_3MM_ATLAS` (`2` `H13CN J=1-0` on `N7538IRS1` & `W75N`, `1` `SiO v=1 J=2-1` on `CHICYG`), `2` `G2_ALAIHI_STANDING_WAVE_RIPPLE`, and `1` `G5_ALAIHI_BROAD_MOLECULAR_ENVELOPE` (`AFGL2688 H13CN J=1-0`).
- **Tightest 10-m Equivalent Beam EIRP Limit:** `CHICYG` = `110,417,597.09 kW` (`ALAIHI_3475UM_86GHZ`).

### Stream 1B: SOFIA/FIFI-LS Far-IR Integral-Field Spectroscopy (`14` Stars / `15` Cubes, `51.5924–186.4382 µm`)
- **Triage (`7` Raw Peaks -> `0` Qualified -> `0` Verified ETI):** `6` `G5_FIFILS_BROAD_LINE` (`CO J=14-13` at `186 µm`, `[O III]` `51.81 µm`, `[O I]` `145.53 µm`) and `1` `G2_FIFILS_ATRAN_TELLURIC` (`AFGL437` `51.6787 µm`).
- **Tightest 10-m Equivalent Beam EIRP Limit:** `ABAUR` = `2,404,426,427.33 kW` (`FIFILS_RED_160UM`).

### Stream 1C: IUE High-Dispersion UV Echelle Archive (`17` Stars, `115–335 nm`)
- **Triage (`102` Raw Peaks -> `10` Stage-1 Qualified -> `0` Verified ETI):** `92` raw features rejected in Stage-1 (`54` `G4_IUE_ORDER_OVERLAP_MISMATCH`, `17` `G5_IUE_CAMERA_CR_GLITCH`, `8` `G5_IUE_BROAD_EMISSION`, `7` `G2_IUE_GEOCORONAL_LYALPHA`, `2` `G2_IUE_GEOCORONAL_OI`, `4` `G3_IUE_CHROMO_ATLAS`). All `10` Stage-1 qualified peaks vetoed forensically in Stage-2 (`5` chromospheric lines incl. `Betelgeuse` `Fe II` `1785.5 Å`, `Si I` `1226.5 Å`, `S I`; `2` broad features on `HD166620`; `1` photospheric opacity window on `HD35296`; `2` unoverlapped single-epoch SEC-Vidicon particle hits: `HD104304` `LWP24850` Ord `71` at `3243.8554 Å` [sole archival IUE exposure, `13` NEWSIPS bright spots] and `HD144668` `SWP26370` Ord `105` [`77` NEWSIPS bright spots]).
- **Tightest 10-m Equivalent Beam EIRP Limits:** `IUE_SWP_HI` `HD114710` = `6.6380 kW` (`IUE_SWP_1350`); `IUE_LWP_HI` `HD103095` (`<10 pc` halo star) = `22.5100 kW` (`IUE_LWP_2600`).

### Stream 2 & Stream 3: ESO HARPS/FEROS 4-Gen, High-$e$ Orbits `#146–#150`, & 42-Campaign `DRIFT_V58_ECCENTRIC_KEPLERIAN`
- **ESO 4-Gen Optical (`6` stars, `24` exposures):** `178` `G1` seeds -> `178` `G2` -> `177` `G3` -> `24` `G4/G5` -> `24` `G6` -> `4` `G7` -> `0` `G8` -> **`0` ETI** (`ESO_HARPS` `HD20782` = `29.7126 kW`; `ESO_FEROS` `HD154577` = `71.6307 kW`).
- **Orbital Campaigns (`#146–#150`, `150` Cumulative):** `HD20782 b` ($e=0.950$, $14.0\,\text{yr}$ HARPS), `HD28254 b` ($e=0.950$, $17.4\,\text{yr}$ HARPS), `HD76920 b` ($e=0.878$, FEROS), `HD7449 b` ($e=0.752$, $12.2\,\text{yr}$ HARPS), `HD147513 b` ($e=0.26$, $20.3\,\text{yr}$ FEROS). Topocentric sky-frame stacking and cross-star same-instrument coincidence checks cleanly eliminated two fixed ESO FEROS topocentric detector/ThAr-bleed features on `HD76920` (`4796.85 Å` and `6638.88 Å`, independently present in zero-planet control `HD154577`) -> **`0` ETI**.
- **Empirical Stellar RVs (`STAR_RV_SUMMARY_D100.csv`):** `HD147513` `13.6233 (2.7199)` km/s, `HD154577` `7.3692 (6.1726)` km/s, `HD20782` `40.6251 (0.0332)` km/s, `HD28254` `-8.4407 (0.0776)` km/s, `HD7449` `-19.0327 (0.0818)` km/s, `HD76920` `21.1794 (0.1556)` km/s (`146/216` `CLEAN_ABSORPTION` anchors).
- **42-Campaign Coherent Eccentric Keplerian + 3D Jerk Search (`6` D100 + `36` Retroactive Y–T):** `347` epochs, `69,805` trajectories evaluated, **`5,346,359,179` pixel trajectory integrals**, `4,863` eccentric Keplerian polishes, **`15,995` raw coherent survivors** (`8,415` cubic jerk, `4,438` Keplerian coherent, `1,677` curved, `863` eccentric Keplerian, `374` linear, `228` periodic) resolved uniformly to **`0` Verified ETI** (`11,283` sub-photospheric troughs, `2,862` OH sky/telluric, `1,826` stationary/absorption bands, `13` non-LSF shape, `5` spurious epoch subsets, `5` low-continuum CR ringing, `1` single-epoch H2O telluric-absence amplitude outlier on `HNLIB` `7228.84382 Å` with `amp_out = 10.01`).
- **Comb, Ellipsoid & Agnostic Closure:** `3,721,152` D100 `COMB_V4_1` configs -> `3` raw `FEROS_BLUE` photospheric line-forest hits (`HD154577`) -> **`0` ETI** (`470` cumulative all-sky stacks / `215` candidates -> `0`); `201,527` D100 V2 false alarms eliminated (`715,414` cumulative); `1,209` multiscale agnostic survivors -> `0` ETI; `560`-star Multi-Event Ellipsoid (`49` ETZ, `37 <= 180 d`) -> **`0` ETI**.

---

## 5. Centennial Unified D079–D100 Synthesis (`560` Unique Stars, `26` Companion Archives `A–Z`)

| Metric | Value |
| --- | --- |
| Phase Range & Companion Archives | `D079–D100` (`22` survey phases; `26` Archives `A–Z`) |
| Spectrographs / Spectral Arms | `39` spectrographs / `62` spectral arms |
| Unbroken Spectral Span | `0.0905–1,401.36089 µm` (**`13.919` unbroken octaves**) |
| Observed Band-3 Gap & Frontier | `[1,401.36089, 3,437.3982] µm` gap; frontier **`3,856.0502 µm`** (**`15.379` total octaves**) |
| Unique Stellar Systems | **`560`** (`433` Science [`219` planet hosts, `417` confirmed exoplanets] + `127` Controls) |
| Solar Neighborhood (`<10 pc`) | **`176` stars** (median **`1.4924 kW`** across `154` finite bounds) |
| Panchromatic Science Bridges | **`74` Science bridges** (`855` cells) + `7` revisited controls = **`81` multi-phase targets** |
| Cumulative Exposures & Integration | `2,876` exposures / `1,024.7103 h` |
| Cumulative Calibration & False-Alarm Closure | `46,455` trials; `715,414` V2 false alarms; `C12` `max_rel_err = 0.0005986391` -> **`0` Verified ETI** |

---

## 6. Visual Figures (`results/figures/`, `240 DPI`, `VISUAL_REVIEW.json = PASS (6/6)`)

| Figure File | Size (B) | Subject |
| --- | ---: | --- |
| `results/figures/fig91_d100_jcmt_alaihi_3mm_23stars.png` | `445,687` | JCMT 'Alaihi 3 mm (`77.75–87.22 GHz`), `180/180` cal, `11->0` funnel, `23`-star limits (`CHICYG` `110.42 GW`, `OH231P8` `3,856.05 µm`) |
| `results/figures/fig92_d100_sofia_fifils_farir_14stars.png` | `436,868` | SOFIA/FIFI-LS dual BLU/RED spectra vs. ATRAN, `180/180` cal, `7->0` funnel, `14`-star limits (`ABAUR` `2.404 TW`) |
| `results/figures/fig93_d100_iue_uv_echelle_17stars.png` | `522,842` | IUE `HD 104304` Order-71 particle-hit triage, `180/180` cal, `102->10->0` funnel, `17`-star UV limits (`HD 114710` `6.64 kW`) |
| `results/figures/fig94_d100_eccentric_keplerian_42campaigns.png` | `408,097` | `V5.8D` (`59/60` vs `55/60` vs `34/60`), 42 campaigns & Orbits `#146–#150`, `15,995` branch hits -> `0` ETI |
| `results/figures/fig95_d100_panchromatic_560stars_15p38octaves.png` | `785,600` | `0.0905–3,856.05 µm` frontier + shaded Band-3 gap, `560`-star sky map, `176 <10 pc` (`1.4924 kW`), 12-suite scorecard |
| `results/figures/fig96_d100_centennial_synthesis_d079_d100.png` | `334,742` | UV-to-3 mm bridge heatmap (`*` promoted -> `74` bridges / `855` cells) and `D079–D100` growth (`12 -> 560`) |
