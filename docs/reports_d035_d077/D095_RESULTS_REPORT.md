# SETI Phase D095 (V5.3) Results Report: Curved & Periodic Drift Chaining, Gemini GHOST Simultaneous Sky-IFU Veto, Spitzer IRS Greenhouse CCF & Dyson vs. Silicate Discrimination, and SDSS APOGEE-2

**Phase ID:** `D095` (`TECHNOSIGNATURE_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2`)  
**Prospective Stage-1 Lock:** `2026-11-21T17:35:21Z` (`METHOD_LOCK.json` SHA-256 `a52ee7420e0bd43183009d161ba36d20856aa5ea8ab2bc0898bc98e35f971475`, `inputs_d095_v5_3_exists: false`)  
**First Science Download:** `2026-11-21T17:35:44Z` (`+23.839 s >= 3.0 s` pre-download lock lag)  
**Verified Technosignature Detections:** **0 ETI**

---

## 1. Cohort, Facility Coverage & Zero-Overlap Verification

- **Unique Targets in D095:** `35` stars (`29` science, `6` astrophysical/extragalactic controls: `2M23032370`, `2M01452047`, `GD71`, `NGC3268CE1`, `HD149757`, `HD019356`), comprising `28` brand-new unique stars (`5` within `10 pc`: `GJ3801`, `SIRIUS`, `FOMALHAUT`, `HD38393`, `HD151288`) plus `7` revisited panchromatic bridges (`LTT9779`, `TAUCET`, `HD115617`, `HD69830`, `HD10647`, `HD40307`, `HR8799`). Six revisited targets (`LTT9779`, `HD115617`, `HD69830`, `HD10647`, `HD40307`, `HR8799`) are newly promoted to panchromatic optical/UV+IR bridges alongside previously bridged `TAUCET`, raising the survey bridge total from `41` to **`47` stars (`706` cells)**.
- **Zero-Overlap Verification:** `0` shared `dp_id`s against `2,670` prior exposures and `432` prior coordinates (`C001–C037` + `D001–D094`), with minimum brand-new sky separation **`2,178.11 arcsec`** (`>= 300 arcsec`) and minimum intra-D095 separation `3,187.05 arcsec`.
- **Ingested Spectra & Bounded Bundle:** `54` raw archival files (`124.246 MiB` / `130,281,789 B <= 125.0 MiB`) unpacking into `154` physical spectra/visits (`18.6444 h` integration) and `1` deterministic compressed bundle (`d095_bounded_bundle.json.gz`, **`13.35 MiB < 22.0 MiB`**):
  - **SDSS APOGEE-2 (`H` band, `R = 22,500`, `1.51–1.70 um`):** `10` `apStar` FITS (`123` individual-visit spectra across `10` stars: `9` multi-epoch `N=6..26` campaigns plus `< 10 pc` target `GJ3801` `N=2`).
  - **Gemini-South GHOST (`BLUE+RED`, `R = 56,000`, `0.348–1.061 um`):** `26` DRAGONS 1D FITS (`13` paired BLUE+RED exposures across `7` targets, including simultaneous sky-IFU HDU `[4..5]`).
  - **Spitzer IRS (`SL+LL` merged IPAC `.tbl`, `R ~ 100`, `5.2–37.86356 um`):** `18` enhanced spectral tables across `18` targets.

---

## 2. Primary Search Streams (All 0 Verified ETI)

### 2.1 Four-Generation Cascade, GHOST Simultaneous Sky-IFU Veto & Stage-2 Physical Triage
Across `SDSS_APOGEE2` (`T=2,374,764`, `P=199,346`) and `GEMINI_GHOST` (`T=3,083,770`, `P=1,659,258`), **`9,302` Legacy V2 false alarms** were eliminated. On `GEMINI_GHOST`, the simultaneous HDU `[4..5]` sky-IFU fiber veto (`apply_ghost_sky_fiber_veto_v53`) independently rejected **`109/232` G1 seeds**, collapsing `232 G1 -> 122 G2+Sky -> 120 G3 -> 21 G4/5 -> 21 G6 -> 4 G7 -> 4 Stage-1 G8_V53`. All `4` raw Stage-1 `GEMINI_GHOST` ledger hits are deterministically resolved to **`0` verified ETI** in Stage-2 physical triage (`_evaluate_stage2_physical_triage` in `analyze.py`, keeping Stage-1 `v5_3_detector.py` 100% unmodified):
1. **`LTT9779` at `w_rest = 4305.28 A` (`2` `ch=T` hits in `S20240827S0062` & `S20240827S0065`):** Forensically confirmed stationary sub-photospheric Fraunhofer CH G-band (`4304 A`) micro-continuum crest inside a `15 A`-wide deep absorption trough (`F_peak / P90(+-25 A) = 1.0040` and `1.0006 < 1.05`; `0.941` relative to the outer `4312–4320 A` photospheric continuum at `3,652 ADU`; present across all `3` epochs with `BERV` span `1.88 km/s < 4.0 km/s`) -> **`STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH` (`verified_eti = False`)**.
2. **`MASCARA1` at `w_rest = 8606.60 A` / `w_bary = 8606.48 A` (`2` hits `ch=T` & `ch=P` in single exposure `S20240702S0246_red001`):** Forensically confirmed unflagged single-exposure DRAGONS cosmic-ray hit (`HDU[7] HISTORY` runs zero CR rejection; `M`-shaped split core `16,611 / 17,181 / 16,939 / 17,074 / 16,498` ADU vs `~16,050` ADU continuum) -> **`STAGE2_VETO_1EP_DRAGONS_NOCR_SPLIT_CR` (`verified_eti = False`)**, independently confirmed non-persistent by `4` same-night CADC adjacent `MASCARA-1` DRAGONS exposures taken `28–34 min` later (`S20240702S0267 = 1.0079x`, `S20240702S0268 = 1.0097x`, `S20240702S0270 = 1.0050x`, `S20240702S0271 = 1.0167x` flat continuum at `8606.5 A`).
`SDSS_APOGEE2` reduced `134 G1 -> 108 G2 -> 98 G3 -> 41 G4/5 -> 28 G6 -> 1 G7 -> 0 G8 -> 0 verified ETI`.

### 2.2 Curved & Periodic Multi-Epoch Drift (`DRIFT_V53_CURVED_AND_PERIODIC`, 26 `N >= 4` Campaigns)
Evaluating `scan_curved_and_periodic_drift_v53` (`61,570` curved + `119,743` periodic = `181,313` search evaluations) across **`26` `N >= 4` campaigns** yielded **`0` surviving ETI**:
- **`D095` (`9` APOGEE-2 campaigns, `N=6..26`):** Up to `408` (`KEPLER93`), `355` (`KEPLER37`), `348` (`KEPLER409`), and `172` (`KEPLER1869`, `N=26`) raw non-linear tracks -> **`0` survivors**.
- **Retroactive `D091` `Archive Q` (`12` `N>=4` FEROS/GIRAFFE/X-shooter campaigns):** `127 -> 0` (`HD213885`), `59 -> 0` (`GJ433`), `30 -> 0` (`OGLETR113`), `19 -> 0` (`K222`), `1 -> 0` (`KEPLER156`) -> **`0` survivors**.
- **Retroactive `D094` `Archive T` (`5` `N>=4` APOGEE-2 campaigns):** `74 -> 0` (`2M23025951`), `5 -> 0` (`2M17012756`) -> **`0` survivors**.
Linear `DRIFT_V52` (`11` D095 campaigns) and pairwise `DRIFT_V51` (`3` D095 `N=2` pairs) also yielded **`0` survivors**.

### 2.3 Spitzer IRS (`5.2–37.86 um`) 6-Gas Greenhouse CCF & Dyson Waste-Heat vs. Silicate Discrimination (`18` Targets)
- **Union-Excluded 6-Gas CCF (`CF4`, `C2F6`, `SF6`, `NF3`, `CFC-11`, `CFC-12` vs. 7 Natural Confounders):** **`0` technosignature detections** across all `18` targets (`108` star-gas pairs; max gas significance `sf6_sigma = 4.034` on `HD40307` vs `max_confounder_sigma = 7.426`).
- **Dyson Waste-Heat (`100–400 K`) vs. Silicate Debris Belts (`10 / 18–24 um`):** **`0` Dyson candidates**. Prominent natural crystalline/amorphous silicate debris emission was cleanly measured and isolated from smooth blackbody waste heat on **`HD69830` (`75.797 sigma`)**, **`HR8799` (`21.074 sigma`)**, and **`FOMALHAUT` (`17.139 sigma`)**.

### 2.4 Orbital Campaigns `#126–#133`, `COMB_V4_1`, Agnostic Filter & `401`-Star Multi-Event Ellipsoid
- **Orbital Campaigns `#126–#133`:** `4` `GEMINI_GHOST` (`WASP-74 b`, `WASP-178 b`, `HD 2685 b`, `LTT 9779 b`) and `4` `SDSS_APOGEE2` (`Kepler-37 b`, `Kepler-409 b`, `Kepler-93 b`, `Kepler-1869 c`) yielded **`0` `K_PLANET` candidates** (cumulative `133` campaigns -> `0` ETI).
- **Laser Frequency Comb (`COMB_V4_1`):** `5,789,588` configurations searched across `17` D095 stacks; `3` photospheric `Fe I` / `CN` violet bandhead (`3823–3866 A`) inter-line crests on `LTT9779_GHOST_BR` (`0 verified_eti_combs`) across **`441` cumulative all-sky stacks -> `0` ETI**.
- **Agnostic Multi-Scale Wavelet/Boxcar Filter:** `64` natural residuals (`32` positive) across `8` targets -> **`0` ETI**.
- **Multi-Event SETI Ellipsoid (`401` stars):** Against `SN 1987A`, `GW170817`, and `SN 2023ixf`, **`13` ETZ (`|beta| <= 0.265 deg`)** targets (newly adding `2M00100614`, `2M00050730`, `2M00013563`) and **`35` stars within `|dt_sync| <= 180 d`** (newly adding `HD69830` at `43.148 d`).

---

## 3. Radiometric Upper Limits (`170` Cells) & Unified `401`-Star `8.709`-Octave Landmark Census

- **Phase D095 `170` Star-Band `10 m` Directed Laser EIRP Limits (by facility):**
  - Overall Best D095 (`GEMINI_GHOST`): **`GD71` `G5_7800` (`7800 A`) = `5.790936 kW` (`5,790.93563 W`)**
  - `SDSS_APOGEE2`: **`GJ3801` (`9.19 pc`) `A2_15700` = `37.574518 kW`**
  - `SPITZER_IRS` (`3 sigma` direct CGS): **`HD151288` (`GJ 638`, `9.85 pc`) `S4_260000` (`26.0 um`) = `947.720106 kW`**
- **Unified `D079–D095` Synthesis (`V3.0–V5.3`):** **`401` unique stars** (`308` science [`195` planet hosts / `386` confirmed exoplanets] + `93` controls) across **`25` spectrographs (`33` spectral arms)** and **`8.709` continuous octaves (`0.0905–37.86356 um`)**; **`161` stars within `10 pc`** (`1.74941 kW` median `10 m` EIRP limit); **`47` panchromatic bridges (`706` cells)**; **`2,392` exposures (`721.4813 h`)**; **`36,060` calibration trials** (`34,149 + 1,911`); **`312,447` V2 false alarms eliminated**; **`133` orbital campaigns**; **`441` all-sky comb stacks**; **`0` verified ETI**.

---

## 4. Stage-2 Pipeline Notes & `1,911`-Trial Calibration Validation

Stage-1 locked files (`7/7` hashes in `METHOD_LOCK.json`, including `v5_3_detector.py` SHA-256 `fad12754aa5849897f4141f246e1041691e2fafea47de43205fa9ef0a92120f8` and `download_inputs.py` SHA-256 `907318e4249253dd248b73c120d93376b0c75f90deacf38253352a8418b65446`) remain 100% unmodified:
1. **`download_inputs.py` IPAC Offset-`518` Note:** Locked `download_inputs.py` inspected `[:512]` for `'SPITZER'`, whereas `HD38393` (`SPITZER_S5_16014848_01_merge.tbl`) places `\TELESCOP = 'Spitzer'` at offset `518`. Stage-2 `complete_spitzer_download.py` validated `4096`-byte IPAC headers + `|order|wavelength|` for files `39–54`.
2. **GHOST DRAGONS Barycentric `AWAV-LOG` & Bright Spitzer IRS Pedestal Guard:** Verified HDU `[7]` `barycentricCorrect` on GHOST (`w_topo = w_bary / (1 + BERV/c)`) and filtered saturated `DATA_ERROR_MIN` pixels (`err_jy <= 0.00015` when `flux_jy > 0.5 Jy`) on `SIRIUS` (`30` bins), `FOMALHAUT` (`9` bins), and `HD168009` (`1` bin).
3. **Stage-2 GHOST Physical Triage (`4 -> 0`):** Rejected `LTT9779 4305.28 A` (sub-photospheric CH G-band trough) and `MASCARA1 8606.48 A` (1-exposure split DRAGONS CR, refuted by CADC `S20240702S0267–S0271`) as detailed in Section 2.1.
4. **`1,911` Synthetic Calibration Trials (`10` Suites, `0.00%` FP Across All Veto Classes):**
   - `CALIBRATION_V53_CURVED_PERIODIC_DRIFT_240`: `58/60 (0.9667)` curved, `55/60 (0.9167)` periodic recovery; `40/40` stationary, `40/40` transient, `40/40` BERV-sky veto (`120/120` = `0.00%` FA).
   - `CALIBRATION_V53_SPITZER_IRS_CCF_AND_DYSON_240`: `46/60 (0.7667)` 6-gas CCF, `60/60 (1.0000)` Dyson blackbody recovery; `60/60` spectral confounder & `60/60` silicate debris veto (`120/120` = `0.00%` FA).
   - `CALIBRATION_V53_GHOST_SKY_FIBER_120`: `55/60 (0.9167)` clean star-fiber pass; `60/60 (1.0000)` simultaneous sky airglow veto.
   - `CALIBRATION_G8_V53_120`: `40/40` isolated pass; `40/40` shared & `40/40` topo veto (`80/80`).
   - `CALIBRATION_V53_RPCA_RARITY_180`: `59/60 (0.9833)` isolated; `60/60` shared & `60/60` topo veto (`120/120`).
   - `CALIBRATION_V53_AGNOSTIC_120`: `120/120 (1.0000)`; `DETECTOR_V53_G4G5_CALIBRATION_108`: `108/108 (1.0000)`; `INJECTION_RECOVERY_540`: `540/540 (1.0000)`; `COMB_V4_1_CALIBRATION_162`: `54/54` recovery (`0/54` forest FA, `0/54` topo FA); `KEPLERIAN_TRACK_CALIBRATION_81`: `81/81 (1.0000)` (`0` `T_DIFF` FA).
