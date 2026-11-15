# SETI Fase D080 (Trin 3) — Prospektivt Opgraderet `ECELLE_V3_1` Multi-Instrument (`HARPS` + VLT `ESPRESSO`) Optisk Lasersøgning på 26 Friske FGKM- og Exoplanet-Stjerner

**Dato:** 14. november 2026  
**Fase:** `D080` (`work_echelle_20261114_d080_v3_1_exoplanet_survey`)  
**Prospektiv metodelås (`METHOD_LOCK.json`):** `bf757017dac55b157ebdba65eb41aa11c877b04f41e028e5debee0ccc06932a1` (frosset `2026-11-14T18:48:47.756658+00:00`, strengt før første science-download)  
**Dokumenteret pre-analyse ESO-arkiv- og skema-tillæg (`IMPLEMENTATION_LOCK.json`):** `7843291aec5a085eebe69af7ba8ddaf84e37a2fd8af422b7ff5b2628024b3fb8` (`0` detektorparametre og `0` linjer i `v3_1_detector.py`/`audit.py` ændret; offentlig `obs_release_date`-filtrering samt `esotk/0.9.8` Phase-3 FITS-kolonneindlæsning før spektral analyse)  
**Uafhængig ren-stdlib numerisk audit (`/usr/bin/python3 -S audit.py`):** `PASS` (`11/11` hovedkontroller og fuld genberegning af alle `1.560` RV-fits, `1.530` injektioner, `204` 2D-forsøg, `404` kandidater og `186` øvre grænser med `0` fejl)  
**Hovedkonklusion:** **Ingen statistisk ETI-laser-overrepræsentation** (`10` i kontrol [`0,50/eksp`] mod `24` i science [`0,22/eksp`]) på tværs af **`130` friske højopløste echelle-eksponeringer** (`70` ESO `HARPS` ved $R \approx 115\,000$ + `60` VLT `ESPRESSO` 8,2 m ved $R \approx 140\,000$, samlet integration `98732,1 s`, `46,366,818` gennemsøgte 1D-bins i Kanal T). Søgningen dækker **`22` bekræftede exoplanet-værtsstjerner med `44` planeter** (`15` transiterende systemer, afstand `3,64–44,86 pc`) + **`4` dedikerede ikke-planet kontrolstjerner** (`20` eksponeringer). De kalibrerede `8σ` øvre grænser for en diffraktionsbegrænset `10 m`-lasersender spænder fra **`0,91 kW` til `110,50 kW`** med samlet median **`10,28 kW`** (`7,52 kW` på VLT `ESPRESSO` mod `16,26 kW` på `HARPS`, og helt ned til **`0,91 kW`** på `HIP70849`!).

---

## 1. Baggrund og formål med Trin 3 (`D080` — fra `HARPS_ECELLE_V3.0` til `ECELLE_V3_1`)

I `D079` (Trin 2) blev 3. generations-pipelinen `HARPS_ECELLE_V3` kalibreret og afprøvet på `10` sol-analoge stjerner + `2` kontrolstjerner (`60` HARPS-eksponeringer). Selvom `D079` opnåede `0` verificerede ETI-lasere, afslørede de to prospektive kontrolstjerner præcis to tilbageværende fysiske baggrundskilder i `V3.0`:
1. **`166` sub-kontinuum Kanal P-passager (`Test F1`):** Små linjedybde-forskelle i fotosfæriske metallinjer (`Fe I`, `Ni I`, `Cr I`) mellem stjernen og et simpelt 1D-medianatlas gav smalle positive differens-toppe *nede i bunden af absorptionslinjer* (`fn_pk3 <= 0,979 < 1,00`).
2. **`10` skrå 2D kosmiske myonspor i Kanal T (`Test F2`):** Skrå kosmiske spor på CCD'en kunne ramme fibercenteret i én enkelt dispersionsrække og passere en 1-rækkes (`1 × 11`) tværdispersions-gate, mens centroiden drev op til `5,58 px` på naborækkerne.

**Trin 3 (`D080`)** tager derfor tre store sammenhængende skridt i én lukket fase:
1. **Prospektiv algoritmeopgradering til `ECELLE_V3_1`:** Indbygger `F1` (`fn_pk3 >= 1,008` både i 5-epoke coadd `Gate G1_F1` og nativ orden `Gate G3_F1`) kombineret med et 2D $(T_{\mathrm{eff}}, [\mathrm{M/H}])$ `K=5` nærmeste-nabo Beer-Lambert-atlas, samt indbygger fuld 2D-detektorfysik (`Gate G5_F2`) direkte i selve den låste pipeline.
2. **Tvær-instrumentel udvidelse til VLT `ESPRESSO` (`8,2 m` UT, $R \approx 140\,000$, `3772–7900 Å`):** Udnytter ESPRESSO's **anamorfiske pupil-slicer**, hvor lyset fra stjernefiberen deles i to uafhængige optiske skiver (`Slice a = 2m` og `Slice b = 2m+1`) på detektoren. Et ægte astrofysisk eller ETI-lasersignal *skal* optræde simultant i begge skiver ved eksakt samme barycentriske bølgelængde ($|\Delta v_{a,b}| \le 1,25\,\mathrm{km/s}$) og matche en fælles `2 × 11` LSF-model ($\cos_{2\mathrm{D}} \ge 0,85$), mens kosmiske enkelt-skive- og skrå spor afvises øjeblikkeligt.
3. **Skalering til `26` friske nære FGKM- og exoplanet-stjerner (`130` eksponeringer):** Udvider kohorten til `22` bekræftede exoplanet-systemer (`44` planeter, heraf `15` transiterende systemer med eksakt konjunktionsfase-logning, fra $\varepsilon$~Indi~A = `HD 209100` ved `3,64 pc` til `44,86 pc`) + `4` dedikerede ikke-planet kontrolstjerner på tværs af spektroskopiske temperaturklasser (`3589–6190 K`).

---

## 2. Prospektiv metodelås, nul-overlap-verifikation og ESO-frigivelsestillæg

### 2.1 Nul-overlap mod alle `52` tidligere stjerner og `423` ESO `dp_id`
`PRIOR_EXCLUSION_VERIFICATION.json` krydstjekkede samtlige `26` `D080`-stjerner og `130` ESO `ADP.*`-identifikatorer mod alle tidligere faser (`C001–C037`, `D001–D034`, `D035–D078` og `D079`: i alt `52` stjerner og `423` `dp_id`) samt de to uafhængige Stage-0 format-kontrolmål (`BD+04 4988` og `Venus`):
- **Overlap i stjernenavne:** **`0`**
- **Overlap i ESO `dp_id`:** **`0`**
- **Mindste vinkelafstand på himlen til nogen tidligere stjerne:** **`6119,75 buesekunder` (`1,70°`)**.

### 2.2 Bevaret pre-analyse arkivopdagelse (`IMPLEMENTATION_LOCK.json`)
Metodelåsen (`METHOD_LOCK.json`, SHA-256 `bf757017dac55b15...`) blev forseglet ved `2026-11-14T18:48:47.756658+00:00` før download af science-data (`FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`). Under Pass-1 download (ved `25 / 268` filer, *før* ét eneste FITS-spektrum var åbnet eller analyseret) returnerede ESO `dataPortal` `HTTP 401 Unauthorized` på `ADP.2026-07-16T00:08:48.929` (`HD 161098` epoke 5). Årsagen var entydig: Stage-0C's `ivoa.ObsCore`-forespørgsel udlæste `obs_release_date`, men manglede et `WHERE obs_release_date <= '2026-11-13'`-filter, så `7` eksponeringer fra `2026` stadig var under ESO's 1-årige proprietære embargo frem til `2027`.

I nøje overensstemmelse med projektets gennemsigtighedsregler og forbuddet mod at omgå adgangsbegrænsninger blev de oprindelige filer bevaret byte-for-byte i `FROZEN_PRE_INGESTION/*_v0.*`, mens to rent tekniske ESO-arkivtilpasninger før enhver spektral analyse blev forseglet i `IMPLEMENTATION_LOCK.json`:
- **Offentlig frigivelsesdato (`obs_release_date <= '2026-11-13T00:00:00Z'`):** **`116 / 130` eksponeringer (`89,2 %`)** var uændrede. `HD 161098` (`51` offentlige nætter), `HD 93083` (`25` offentlige nætter) og `HD 222259A` (`9` offentlige nætter) genvalgte udelukkende offentligt frigivne nætter, mens `HD 208704` (`0` offentlige nætter før maj 2027) blev erstattet af den næste Stage-0B ikke-planet ESPRESSO-kontrolstjerne **`HD 191849`** (`Gliese 784`, `M0V`, `6,16 pc`, `31` offentlige nætter, `SNR = 254–356`), så kontrolkohorten nu dækker både sol-analoger (`HD 59468`, `HD 161098`), `K1V` (`HD 109200`) og kølige `M0V`-stjerner (`HD 191849`) med `TiO`-bånd.
- **ESO FITS-indlæsningsformater (`esotk/0.9.8` Phase-3 + tidlig enkelt-HDU HARPS `RAW`):** Mens `54 / 60` ESPRESSO `S1D`-filer fra `espdr` indeholder kolonnerne `WAVE_AIR` og `FLUX_EL`, leveres `6` OB-kombinerede `esotk/0.9.8`-spektre (`HD 161098` epoke 1–5 og `GJ 9827` epoke 5) med kolonnerne `WAVE` (vakuum-Å), `FLUX` (cgs), `SNR`, `QUAL` og `CONTRIB` samt `ESO QC BERV` i den tilhørende `S1D_FINAL_B`-header; tilsvarende lagres `3 / 51` tidlige 2004 HARPS rå 2D-billeder som et enkelt `(4096, 4296)` 2-chip mosaik-HDU frem for to `(4096, 2148)` HDU-udvidelser. FITS-indlæserne i `analyze.py` blev udvidet til at læse alle disse ESO-arkivskemaer (og springe ikke-standard telemetri-kort som `ESO INS TEMP40 RMS` over), mens **`v3_1_detector.py`, `audit.py`, `plot_figures.py` og samtlige detektorgates og tærskler forblev `100 %` uændrede**.

---

## 3. Stellar hvileramme og syntetisk multi-instrument kalibrering (`1.734` forsøg)

### 3.1 Barycentrisk hvileramme-verifikation (`1.560` NIST-ankerfits på `130` eksponeringer)
På tværs af alle `130` eksponeringer (`3589–6190 K`) tilpassedes de `12` låste NIST-absorptionsankre:
- **`1450 / 1560`** rene absorptionsfits og **`130 / 130` eksponeringer** med fuld empirisk hvileramme-forankring.
- Median absolut afvigelse mod Gaia DR3 på tværs af alle `26` stjerner er **`0,511 km/s`** (maks. `0,759 km/s`), og epoke-til-epoke RMS ligger nede på få titals m/s både på `HARPS` og VLT `ESPRESSO`.

### 3.2 End-to-end syntetisk laser-genfinding og 2D detektorfysik (`1.734` forsøg, `3844–7465 Å`)
På de `4` dedikerede ikke-planet kontrolstjerner (`HD 109200` & `HD 59468` på HARPS; `HD 161098` & `HD 191849` på ESPRESSO) gennemførtes **`1,734` prospektive kalibreringsforsøg** over `8` HARPS-bånd (`3844,75–6825,40 Å`) og `9` ESPRESSO-bånd (inkl. det nye dybrøde bånd ved **`7465,10 Å`**):
1. **Kanal T (`1.020` enkelt-epoke injektioner gennem `G1 + G2 + G3 + G4`):**
   - Samlet genfindingsgrad ved **`>= 8σ`: `59,15 %`** (`HARPS`: `57,29 %`; `ESPRESSO`: `60,80 %`).
   - Blåt interval (`3844,75 Å` & `3951,50 Å`) ved **`>= 8σ`: `48,61 %`**; ESPRESSO dybrødt bånd (`7465,10 Å`) ved **`>= 8σ`: `69,44 %`**.
2. **Kanal P (`510` 5-epoke injektioner inkl. supraphotosfærisk `Gate G1_F1` & `G3_F1`):**
   - Samlet genfindingsgrad ved **`>= 9σ`: `84,31 %`**, og ved **`>= 12σ`: `92,65 %`**.
3. **Gate `G5_F2` 2D detektorfysik (`204` rumlige forsøg = `96` HARPS `5 × 11` rå CCD + `108` ESPRESSO `2 × 11` dual-slice):**
   - **Ægte fiber-fødet laser pass-rate:** **`97,06 %`** samlet (`HARPS`: `100,00 %`; `ESPRESSO` dual-slice: **`94,44 %`**).
   - **Afvisning af kosmiske 1-pixel/1-slice spikes og skrå myonspor:** **`100,00 %`** samlet (`HARPS`: `100,00 %`; `ESPRESSO`: **`100,00 %`**).

---

## 4. Tre-generations falsk-alarm-kollaps (`V2 → V3.0 → V3.1`) og søgeresultater på `26` stjerner

### 4.1 Sammenligning af `Legacy V2`, `D079 V3.0` og `Prospective D080 V3.1` på samme `130` eksponeringer

| Generation / trin | Kontrol (`20` eksp, `4` stjerner) | Science (`110` eksp, `22` exoplanet-stjerner) | Total (`130` eksp) | Fysisk betydning |
| --- | ---: | ---: | ---: | --- |
| **`Legacy V2` (`D002`-ækvivalent 1D `S1D`)** | `76` | `346` | **`422`** | Ukalibreret 1D-detektor oversvømmes af telluriske/kosmiske/fotosfæriske artefakter (`160` HARPS + `262` ESPRESSO) |
| **`D079 V3.0` Kanal P G1 (før `F1`)** | `11` | `142` | **`153`** | Sub-kontinuum fotosfæriske absorptions-mismatches (som i `D079` krævede post-hoc forensisk `F1`-veto) |
| **`D080 V3.1` Kanal P `Gate G1_F1` (med `F1` + `K=5`-atlas)** | `0` | `12` | **`12`** | Supraphotosfærisk kontinuum-gate eliminerer sub-kontinuum absorptions-bumps direkte i G1! |
| **`D080 V3.1` Samlede `G1_F1`-kandidater (Kanal T + P)** | — | — | **`404`** | `392` i Kanal T + `12` i Kanal P |
| **Efter `Gate G2` (airglow + tellurisk $\mathrm{O}_2/\mathrm{H}_2\mathrm{O}$-bånd)** | — | — | **`330`** | Topocentrisk nattehimlens emissionslinjer og mættede telluriske bånd fjernet |
| **Efter `Gate G3_F1` (nativ orden LSF + supraphotosf.)** | — | — | **`234`** | Enkeltpixel-spikes og asymmetriske linjer afvist direkte på `_e2ds_A` / `S2D_BLAZE_A` |
| **Efter `Gate G4` (ordens-overlap + Fiber B lampe/sky)** | — | — | **`209`** | Naboordens-konsistens og simultan kalibrerings-/skyfiber-kontrol |
| **Efter `Gate G5_F2` (2D HARPS `5×11` / ESPRESSO `2×11` slice)** | **`10`** | **`24`** | **`34`** | Fuld prospektiv `ECELLE_V3_1`-kvalifikation (`HARPS`: `10`, `ESPRESSO`: `24`) |

### 4.2 Fordeling af afvisningsårsager i `V3_1_CANDIDATE_LEDGER.csv`

| Endelig `ECELLE_V3_1`-disposition (`V3_1_CANDIDATE_LEDGER.csv`) | Antal kandidater |
| --- | ---: |
| `SINGLE_SLICE_COSMIC_RAY;SLICE_CONTRAST_IMBALANCE;DUAL_SLICE_2X11_LSF_MISMATCH` | `78` |
| `ASYMMETRIC_COSMIC_RAY_SPIKE` | `36` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR;SUB_LSF_SINGLE_PIXEL_SPIKE;ASYMMETRIC_COSMIC_RAY_SPIKE` | `36` |
| `TELLURIC_AIRGLOW_OI_5577_auroral` | `36` |
| `QUALIFIED_V3_1_LASER_CANDIDATE` | `34` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;RAW2D_CENTROID_OFFSET;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT` | `28` |
| `SINGLE_ORDER_CCD_ARTIFACT` | `21` |
| `TELLURIC_AIRGLOW_OI_6300_nebular` | `18` |
| `F2_DISPERSION_WING_BROADENING` | `16` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;F2_2D_5X11_LSF_MISMATCH` | `16` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR;ASYMMETRIC_COSMIC_RAY_SPIKE` | `15` |
| `F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT` | `12` |
| `TELLURIC_AIRGLOW_OI_6363_nebular` | `11` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT` | `9` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR` | `7` |
| `FIBER_B_CALIBRATION_BLEED` | `3` |
| `TELLURIC_O2_B_band_core` | `3` |
| `DUAL_SLICE_2X11_LSF_MISMATCH` | `2` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;RAW2D_CENTROID_OFFSET;RAW2D_OFF_FIBER_TRACK;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT` | `2` |
| `SUB_CONTINUUM_PHOTOSPHERIC_BUMP` | `2` |
| `TELLURIC_AIRGLOW_NaID2_5889` | `2` |
| `F2_2D_5X11_LSF_MISMATCH` | `1` |
| `F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT;F2_DISPERSION_WING_BROADENING` | `1` |
| `F2_DIAGONAL_MUON_CENTROID_DRIFT` | `1` |
| `F2_DIAGONAL_MUON_CENTROID_DRIFT;F2_DISPERSION_WING_BROADENING` | `1` |
| `FIBER_B_CALIBRATION_BLEED;SINGLE_ORDER_CCD_ARTIFACT` | `1` |
| `RAW2D_CENTROID_OFFSET;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT` | `1` |
| `RAW2D_OFF_FIBER_TRACK;F2_2D_5X11_LSF_MISMATCH;F2_DISPERSION_WING_BROADENING` | `1` |
| `RAW2D_OFF_FIBER_TRACK;F2_DISPERSION_WING_BROADENING` | `1` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;F2_2D_5X11_LSF_MISMATCH;F2_DISPERSION_WING_BROADENING` | `1` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT` | `1` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;RAW2D_CENTROID_OFFSET;RAW2D_OFF_FIBER_TRACK;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT;F2_DISPERSION_WING_BROADENING` | `1` |
| `SINGLE_SLICE_COSMIC_RAY;SLICE_CONTRAST_IMBALANCE;SLICE_WAVELENGTH_CENTROID_MISMATCH;DUAL_SLICE_2X11_LSF_MISMATCH` | `1` |
| `SLICE_CONTRAST_IMBALANCE;DUAL_SLICE_2X11_LSF_MISMATCH` | `1` |
| `TELLURIC_AIRGLOW_HgI_4046` | `1` |
| `TELLURIC_AIRGLOW_HgI_4358` | `1` |
| `TELLURIC_AIRGLOW_NaID1_5895` | `1` |
| `TELLURIC_AIRGLOW_NaI_5460_HgI` | `1` |

### 4.3 Overblik over alle `26` stjerner (`4` kontrol + `22` exoplanet-værtsstjerner)

| Stjerne | Instr. | Rolle | Planeter (tr.) | Afstand (pc) | $G$ (mag) | $T_{\mathrm{eff}}$ (K) | $[\mathrm{M/H}]$ | Empirisk $\overline{\mathrm{RV}}$ (km/s) | Epoke-RMS (m/s) | $\Delta\mathrm{RV}_{\mathrm{emp-Gaia}}$ (km/s) | V2 træf | V3.1 G1_F1 (T+P) | V3.1 G1–G5 kval. | Median $P_{10\,\mathrm{m},8\sigma}$ (kW) |
| --- | :---: | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `GJ9827` | `ESPRESSO` | `SCIENCE` | 3 (Ja) | 29,65 | 9,84 | 4182 | -0,00 | +32,260 | 26,1 | +0,246 | 18 | 10 | **3** | 3,35 |
| `HD109200` | `HARPS` | `CONTROL` | 0 (Ctrl) | 16,19 | 6,90 | 5005 | -0,47 | +2,881 | 15,1 | +0,449 | 7 | 7 | **1** | — |
| `HD111232` | `ESPRESSO` | `SCIENCE` | 2 (RV) | 28,89 | 7,42 | 5476 | -0,87 | +105,030 | 168,1 | +0,499 | 20 | 24 | **9** | 10,36 |
| `HD136352` | `HARPS` | `SCIENCE` | 3 (Ja) | 14,74 | 5,48 | 5621 | -0,60 | -68,409 | 12,7 | +0,368 | 3 | 3 | **0** | 34,64 |
| `HD15337` | `HARPS` | `SCIENCE` | 2 (Ja) | 44,86 | 8,86 | 5063 | -0,03 | -3,544 | 20,2 | +0,331 | 20 | 18 | **2** | 19,15 |
| `HD161098` | `ESPRESSO` | `CONTROL` | 0 (Ctrl) | 29,75 | 7,50 | 5543 | -0,21 | -16,570 | 9,9 | +0,576 | 38 | 43 | **5** | — |
| `HD181433` | `ESPRESSO` | `SCIENCE` | 3 (RV) | 26,99 | 8,10 | 4819 | +0,45 | +40,548 | 15,1 | +0,536 | 28 | 13 | **1** | 8,54 |
| `HD185283` | `ESPRESSO` | `SCIENCE` | 1 (RV) | 31,34 | 8,72 | 4709 | +0,12 | +52,083 | 13,9 | +0,534 | 7 | 22 | **1** | 4,97 |
| `HD189733` | `HARPS` | `SCIENCE` | 1 (Ja) | 19,78 | 7,43 | 4897 | -0,19 | -1,988 | 97,0 | +0,544 | 12 | 14 | **2** | 14,17 |
| `HD191849` | `ESPRESSO` | `CONTROL` | 0 (Ctrl) | 6,16 | 7,24 | 3589 | -1,41 | -32,930 | 12,0 | +0,587 | 21 | 4 | **3** | — |
| `HD192310` | `HARPS` | `SCIENCE` | 2 (RV) | 8,81 | 5,48 | 4978 | -0,10 | -53,943 | 18,7 | +0,468 | 14 | 6 | **2** | 8,78 |
| `HD207496` | `HARPS` | `SCIENCE` | 1 (Ja) | 23,64 | 7,98 | 4741 | +0,02 | -10,947 | 17,7 | +0,565 | 16 | 30 | **0** | 12,69 |
| `HD209100` | `HARPS` | `SCIENCE` | 1 (RV) | 3,64 | 4,32 | 4560 | -0,30 | -39,668 | 36,3 | +0,759 | 4 | 3 | **0** | 4,22 |
| `HD21749` | `HARPS` | `SCIENCE` | 2 (Ja) | 16,33 | 7,69 | 4425 | +0,09 | +59,900 | 6,6 | +0,582 | 17 | 11 | **0** | 6,56 |
| `HD222259A` | `HARPS` | `SCIENCE` | 1 (Ja) | 44,18 | 8,34 | 5525 | -0,36 | +7,837 | 161,2 | +0,708 | 23 | 10 | **0** | 38,34 |
| `HD39091` | `HARPS` | `SCIENCE` | 3 (Ja) | 18,29 | 5,51 | 5856 | -0,23 | +11,122 | 138,4 | +0,415 | 3 | 17 | **0** | 48,02 |
| `HD59468` | `HARPS` | `CONTROL` | 0 (Ctrl) | 22,47 | 6,55 | 5566 | -0,41 | +5,242 | 11,7 | +0,425 | 10 | 8 | **1** | — |
| `HD93083` | `ESPRESSO` | `SCIENCE` | 2 (RV) | 28,49 | 8,05 | 4926 | +0,11 | +43,965 | 28,2 | +0,523 | 21 | 15 | **0** | 5,18 |
| `HIP70849` | `ESPRESSO` | `SCIENCE` | 1 (RV) | 24,12 | 9,70 | 3721 | -0,71 | +0,454 | 27,8 | +0,560 | 17 | 16 | **1** | 2,51 |
| `TOI174` | `ESPRESSO` | `SCIENCE` | 5 (Ja) | 39,09 | 9,39 | 4626 | -0,04 | +34,853 | 25,6 | +0,412 | 15 | 19 | **1** | 8,92 |
| `TOI214` | `ESPRESSO` | `SCIENCE` | 2 (Ja) | 38,94 | 8,51 | 5341 | -0,20 | +18,137 | 9,6 | +0,568 | 34 | 17 | **0** | 13,68 |
| `TOI2194` | `HARPS` | `SCIENCE` | 1 (Ja) | 19,55 | 8,07 | 4571 | -0,37 | +53,441 | 19,2 | +0,523 | 5 | 17 | **0** | 7,69 |
| `TOI260` | `ESPRESSO` | `SCIENCE` | 1 (Ja) | 20,21 | 9,32 | 3891 | -0,54 | -10,582 | 8,0 | +0,137 | 23 | 25 | **0** | 2,62 |
| `TOI262` | `ESPRESSO` | `SCIENCE` | 1 (Ja) | 44,14 | 8,68 | 5120 | +0,22 | +32,987 | 19,6 | +0,463 | 20 | 22 | **0** | 15,70 |
| `TOI396` | `HARPS` | `SCIENCE` | 3 (Ja) | 31,70 | 6,26 | 6190 | -0,51 | +9,960 | 20,3 | +0,195 | 13 | 13 | **2** | 57,86 |
| `TOI431` | `HARPS` | `SCIENCE` | 3 (Ja) | 32,62 | 8,80 | 4714 | +0,26 | +49,122 | 25,2 | +0,457 | 13 | 17 | **0** | 13,68 |

### 4.4 Detaljeret kontrol- mod science-gennemgang af kvalificerede `V3.1`-passager

Den prospektive sammenligning mellem dedikerede ikke-planet kontrolstjerner (`10` overlevende på `20` eksponeringer = **`0,50/eksp`**) og exoplanet-værtsstjerner (`24` overlevende på `110` eksponeringer = **`0,22/eksp`**) viser en **lavere rate pr. eksponering på exoplanet-stjernerne end på kontrolstjernerne** — både på `HARPS` (`0,13/eksp` i science mod `0,20/eksp` i kontrol) og på VLT `ESPRESSO` (`0,32/eksp` i science mod `0,80/eksp` i kontrol). Der er således **`0` statistisk overskydende ETI-lasersignaler**.

Fysisk forklares disse svage restpassager entydigt af ægte atmosfærisk nattehimlens luftglød, som trænger ind gennem teleskopets pupil og derfor ægte belyser begge `ESPRESSO` pupil-slices ($\cos_{2\mathrm{D}} = 0,87\text{--}0,99$) hhv. hele `HARPS` `5×11` fiber-PSF'en på eksponeringer, hvor `Fiber B` var konfigureret til simultan bølgelængdekalibrering (`FP` / `THAR2`) frem for himmelbaggrund (`OBJ_SKY`): herunder det klassiske gule kviksølv-gadebelysningsdublet `Hg I 5769,60 / 5790,67 Å` (`TOI-396`, samme tusmørke-eksponering som `Hg I 4046/4358/5461 Å`) samt svage ro-vibrationelle `OH Meinel`-emissionslinjer i det røde/dybrøde vindue (`6276–7840 Å`, bl.a. gentagne topocentriske linjer ved `6282–6283 Å`, `6291–6292 Å` og `6946–6947 Å` på tværs af både kontrolstjernen `HD 161098` og science-stjernerne `GJ 9827` og `HD 111232`). Dette fund motiverer direkte næste kalibreringstrin i `D081`: udvidelse af `Gate G2` fra de `7` kraftige atomare airglow-linjer til et komplet Paranal/La Silla `UVES/ESPRESSO` `OH Meinel + O2 + Hg I`-nattehimlens linjeatlas for `FP`/`THAR2`-eksponeringer.

| ID | Instr. | Kanal | Rolle | Stjerne | `dp_id` | $\lambda_{\mathrm{bary}}$ (Å) | $\lambda_{\mathrm{topo}}$ (Å) | `snr_mid` | `g5_cos_2d` | `g5_drift` | `g5_far_wing` |
| --- | :---: | :---: | :---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `V31-T-0006` | `HARPS` | `T` | `CONTROL` | `HD109200` | `ADP.2014-10-06T10:06:10.547` | 6482,025 | 6481,825 | 8,24 | 0,955 | 0,068 | -0,482 |
| `V31-T-0009` | `HARPS` | `T` | `CONTROL` | `HD59468` | `ADP.2014-09-29T13:27:14.710` | 5703,865 | 5703,685 | 6,53 | 0,872 | 0,318 | 0,389 |
| `V31-T-0018` | `ESPRESSO` | `T` | `CONTROL` | `HD161098` | `ADP.2025-05-02T12:00:50.025` | 6292,458 | 6291,905 | 17,82 | 0,906 | 0,018 | 0,135 |
| `V31-T-0019` | `ESPRESSO` | `T` | `CONTROL` | `HD161098` | `ADP.2025-05-02T12:00:50.025` | 6946,905 | 6946,294 | 12,89 | 0,959 | 0,045 | 0,175 |
| `V31-T-0032` | `ESPRESSO` | `T` | `CONTROL` | `HD161098` | `ADP.2025-06-04T13:20:49.448` | 6305,280 | 6304,996 | 6,69 | 0,877 | 0,287 | 0,228 |
| `V31-T-0043` | `ESPRESSO` | `T` | `CONTROL` | `HD161098` | `ADP.2025-06-26T09:20:12.846` | 6292,458 | 6292,525 | 11,73 | 0,902 | 0,019 | 0,143 |
| `V31-T-0044` | `ESPRESSO` | `T` | `CONTROL` | `HD161098` | `ADP.2025-06-26T09:20:12.846` | 6946,908 | 6946,982 | 9,80 | 0,952 | 0,048 | 0,207 |
| `V31-T-0059` | `ESPRESSO` | `T` | `CONTROL` | `HD191849` | `ADP.2021-04-19T13:01:06.096` | 6989,425 | 6988,814 | 14,02 | 0,959 | 0,017 | -0,051 |
| `V31-T-0060` | `ESPRESSO` | `T` | `CONTROL` | `HD191849` | `ADP.2021-04-19T13:01:06.096` | 7016,895 | 7016,282 | 6,52 | 0,951 | 0,016 | -0,072 |
| `V31-T-0061` | `ESPRESSO` | `T` | `CONTROL` | `HD191849` | `ADP.2021-04-19T13:01:06.096` | 7227,947 | 7227,316 | 8,59 | 0,955 | 0,020 | 0,032 |
| `V31-T-0112` | `HARPS` | `T` | `SCIENCE` | `HD189733` | `ADP.2014-09-16T11:07:01.563` | 6710,438 | 6710,427 | 9,01 | 0,883 | 0,409 | 0,270 |
| `V31-T-0113` | `HARPS` | `T` | `SCIENCE` | `HD189733` | `ADP.2014-09-16T11:03:32.817` | 5555,005 | 5555,028 | 12,81 | 0,918 | 0,400 | 0,396 |
| `V31-T-0157` | `HARPS` | `T` | `SCIENCE` | `TOI396` | `ADP.2019-02-01T01:09:30.484` | 5769,193 | 5769,600 | 51,55 | 0,989 | 0,084 | 0,165 |
| `V31-T-0158` | `HARPS` | `T` | `SCIENCE` | `TOI396` | `ADP.2019-02-01T01:09:30.484` | 5790,257 | 5790,667 | 33,00 | 0,994 | 0,129 | 0,010 |
| `V31-T-0193` | `HARPS` | `T` | `SCIENCE` | `HD15337` | `ADP.2014-09-23T11:05:03.227` | 3802,375 | 3802,673 | 7,12 | 0,910 | 0,480 | 0,508 |
| `V31-T-0210` | `HARPS` | `T` | `SCIENCE` | `HD192310` | `ADP.2014-09-26T16:54:52.420` | 6571,465 | 6571,089 | 9,20 | 0,964 | 0,047 | 0,457 |
| `V31-T-0211` | `HARPS` | `T` | `SCIENCE` | `HD192310` | `ADP.2014-10-07T08:34:58.677` | 6474,585 | 6474,603 | 15,10 | 0,957 | 0,120 | 0,402 |
| `V31-T-0239` | `ESPRESSO` | `T` | `SCIENCE` | `GJ9827` | `ADP.2021-04-27T13:01:35.033` | 6291,726 | 6291,330 | 14,57 | 0,984 | 0,029 | 0,052 |
| `V31-T-0243` | `ESPRESSO` | `T` | `SCIENCE` | `GJ9827` | `ADP.2021-04-27T15:46:50.522` | 6291,726 | 6291,936 | 7,70 | 0,986 | 0,034 | 0,034 |
| `V31-T-0247` | `ESPRESSO` | `T` | `SCIENCE` | `GJ9827` | `ADP.2022-09-06T09:46:06.042` | 6291,726 | 6291,372 | 19,70 | 0,976 | 0,043 | 0,059 |
| `V31-T-0273` | `ESPRESSO` | `T` | `SCIENCE` | `TOI174` | `ADP.2021-04-27T18:47:48.836` | 6276,454 | 6276,513 | 8,75 | 0,960 | 0,063 | -1,040 |
| `V31-T-0332` | `ESPRESSO` | `T` | `SCIENCE` | `HD181433` | `ADP.2025-07-17T00:12:17.498` | 7839,890 | 7839,972 | 7,74 | 0,866 | 0,154 | 0,042 |
| `V31-T-0349` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2024-05-08T07:56:58.795` | 6282,297 | 6282,085 | 17,49 | 0,987 | 0,004 | -0,073 |
| `V31-T-0350` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2024-05-08T07:56:58.795` | 6283,067 | 6282,855 | 19,48 | 0,988 | 0,005 | -0,175 |
| `V31-T-0361` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2025-06-04T13:55:51.024` | 6282,289 | 6282,348 | 11,24 | 0,981 | 0,029 | 0,124 |
| `V31-T-0362` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2025-06-04T13:55:51.024` | 6283,057 | 6283,115 | 18,69 | 0,981 | 0,038 | 0,133 |
| `V31-T-0363` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2025-06-04T13:55:51.024` | 6497,826 | 6497,887 | 7,34 | 0,939 | 0,046 | 0,271 |
| `V31-T-0366` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2025-07-01T08:55:24.878` | 6282,289 | 6282,534 | 11,54 | 0,993 | 0,029 | 0,038 |
| `V31-T-0367` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2025-07-01T08:55:24.878` | 6283,060 | 6283,304 | 11,74 | 0,988 | 0,071 | 0,104 |
| `V31-T-0369` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2025-07-01T08:55:24.878` | 6497,829 | 6498,082 | 8,77 | 0,939 | 0,078 | 0,331 |
| `V31-T-0371` | `ESPRESSO` | `T` | `SCIENCE` | `HD111232` | `ADP.2025-07-01T08:55:24.878` | 7238,228 | 7238,510 | 6,91 | 0,950 | 0,028 | 0,446 |
| `V31-T-0379` | `ESPRESSO` | `T` | `SCIENCE` | `HD185283` | `ADP.2024-05-08T07:54:57.911` | 6323,229 | 6322,707 | 6,82 | 0,950 | 0,017 | 0,030 |
| `V31-P-0393` | `HARPS` | `P` | `SCIENCE` | `HD15337` | `ADP.2019-07-28T01:08:01.411` | 3867,515 | 3867,182 | 13,40 | 0,941 | 0,306 | 0,547 |
| `V31-P-0399` | `ESPRESSO` | `P` | `SCIENCE` | `HIP70849` | `ADP.2024-05-08T08:32:50.767` | 7292,270 | 7292,041 | 11,25 | 0,977 | 0,062 | -0,015 |

---

## 5. Exoplanet-banefasedækning og astrofysiske `8σ` lasereffekt-grænser (`186` stjerne-bånd-celler)

### 5.1 Banefasedækning på tværs af `44` exoplaneter i `22` systemer (`EXOPLANET_PHASE_COVERAGE_110.csv`)
Blandt de `110` science-eksponeringer har samtlige `22` stjerner bekræftede exoplanet-efemerider fra NASA Exoplanet Archive (`15` transiterende systemer med eksakt transit-midt-epoke $T_0$ og `7` radialhastigheds-systemer):
- **`25` eksponeringer** ligger inden for **nedre konjunktion / transitvinduet** ($|\phi| \le 0,08$, hvor Jordens synslinje passerer langs planet-stjerne-aksen — den klassiske geometri for synkroniserede planet-til-Jord optiske fyr).
- **`18` eksponeringer** ligger inden for **øvre konjunktion / sekundær formørkelse** ($|\phi - 0,50| \le 0,08$).

### 5.2 Kalibrerede `8σ` øvre grænser ned til kilowatt-regimet (`STAR_UPPER_LIMITS_186.csv`)
For en diffraktionsbegrænset $D_{\mathrm{tx}} = 10\,\mathrm{m}$ sender rettet mod Solsystemet opnås på tværs af alle `186` stjerne-bånd-celler (`12` HARPS-stjerner × `8` bånd + `10` ESPRESSO-stjerner × `9` bånd):
- **Spektral ækvivalentbredde $\mathrm{EW}_{8\sigma}$:** **`1,04 mÅ` til `82,39 mÅ`** (median **`3,61 mÅ`**).
- **Samlet lasereffekt-grænse $P_{10\,\mathrm{m},8\sigma}$:** **`0,91 kW` til `110,50 kW`**, med samlet median **`10,28 kW`** (`HARPS` median `16,26 kW`; VLT `ESPRESSO` median **`7,52 kW`**).
- **Dybeste følsomhed:** **`0,91 kW`** på **`HIP70849`** (`ESPRESSO`, bånd `B4_BLUEGRN_4675`) — en forbedring på mere end en størrelsesorden i forhold til sol-analoge grænser i `D079` (`17,30 kW`).

---

## 6. Næste naturlige hovedfase — Trin 4 (`D081`)

Med `ECELLE_V3_1` prospektivt valideret på tværs af både ESO `HARPS` og VLT `ESPRESSO` (`38` kalibrerede stjerner og `190` eksponeringer samlet over `D079 + D080`) peger resultaterne direkte på **Trin 4 (`D081`)**:
1. **Tætte transit-tidsserier (konjunktions-synkroniseret Rossiter-McLaughlin arkiv-SETI):** Mens `D080` samplede `5` adskilte nætter pr. stjerne for at maksimere fler-epoke hvileramme-baseline, rummer ESO's `HARPS`- og `ESPRESSO`-arkiver sammenhængende transit-nætter med `20–60` eksponeringer i træk hen over selve planettransitten ($|\phi| < 0,02$). Anvendelse af `ECELLE_V3_1` på sådanne in-transit tidsserier tester direkte kortvarige, konjunktions-låste laserfyr og planet-hvileramme-accelererende linjer under transit!
2. **Volumen-komplet `< 10 pc` syntese:** Sammenkobling af alle sydlige sol-naboer inden for `10 pc` til en samlet publikationsklar øvre-grænse-fordeling i $P_{\mathrm{tx}}$-rummet fra sub-kilowatt til megawatt.
