# Fase `D086` Resultatrapport — Nær-UV til Optisk Pankromatisk Udvidelse (`UVES_NUV + ESPRESSO + HARPS`) & `COMB_V4_1` Opgradering

**Dato:** 17. november 2026  
**Fase:** `D086` (`PANCHROM_NUV_OPT_V3_7_AND_COMB_V4_1`)  
**Prospektiv metodelås:** `2026-11-17T19:29:01Z` (`METHOD_LOCK.json` SHA-256 `f7da997703d3a76cfde52cb6774b761e8fc20847e9014d55a70002f0d72d3f30`, første datanedhentning `+17,0 s` senere ved `2026-11-17T19:29:18Z`)  
**Uafhængig ren-stdlib audit (`/usr/bin/python3 -S audit.py`):** **15/15 PASS** (`100 %` SHA-256 bit-identitet mellem `--from-full-inputs` og `--from-bounded-inputs`)  
**Verificerede ETI-detektioner (`D086` og kumulativt `D079–D086`):** **`0`**

---

## 1. Videnskabeligt Formål og Kohorte

Fase `D086` udvider den prospektivt låste pankromatiske echelle-laser-SETI-kortlægning fra det optisk-nær-infrarøde område (`0,38–2,515 µm`, `7` spektrografer i `D079–D085`) ned i **nær-ultraviolet (NUV, `0,305–0,456 µm`)** via VLT `UVES_NUV` og opgraderer samtidigt Kanal 5 frekvenskam-detektoren til **`COMB_V4_1`** (med off-tooth skovtæthedsfilter, kvadratur inter-tooth kontrasttjek og sub-harmonisk de-aliasing). Sammen med `ESPRESSO` og `HARPS` dækker surveyet nu **over 3 spektrale oktaver (`0,305–2,515 µm`)** på **8 spektrografer**.

- **Låst `D086`-kohorte (`FROZEN_COHORT_D086.csv`):** **`31` stjerner** og **`181` eksponeringer** (`57,0151` timers eksponeringstid):
  - **`55` `UVES_NUV`-eksponeringer** (`12` stjerner, `R = 40.970–71.050`, `3043–4563 Å`)
  - **`48` `ESPRESSO`-eksponeringer** (`6` stjerner, `R = 140.000`, `3790–7860 Å`)
  - **`78` `HARPS`-eksponeringer** (`13` stjerner, `R = 115.000`, `3800–6900 Å`)
- **Nye mål vs. pankromatisk bro (`0` `dp_id`-overlap):** `25` helt nye unikke stjerner (**`17` inden for `10 pc`**, minimal skyseparation mod hele `C001–D085` = **`3.815,51"`**, `0` eksponerings-`dp_id`-overlap mod `1.383` tidligere eksluderede produkter) samt **`6` eksisterende `< 10 pc` stjerner** optaget som nye pankromatiske/NUV-broer: **`PROXIMACEN`** (nu fuldt **tri-regime NUV + Optisk + NIR**), **`EPSERI`**, **`GJ285`**, **`YZCET`**, **`GJ1002`** og **`TAUCET`**.
- **Kontrol vs. Science og banekampagner:** `6` verificerede exoplanet-fri kontrolstjerner (`HD155885`, `HD20630`, `HD191408`, `L49956`, `HD131977`, `HD32147`, alle `n_exo = 0` i NASA `pscomppars`), `25` science-stjerner og **`10` orbitale banekampagner** (`3` nul-kontroller + `7` planetværter, hver med `4` in-window og `4` out-of-window eksponeringer; max `|Kp_stdlib - Kp_csv| = 0,00004 km/s`).

---

## 2. Kalibreringsvalidering (`2.697` Syntetiske Forsøg) og `D085` Regression

| Kalibreringssuite | Antal forsøg | Nøgleresultat i `D086` (`V3.7` + `COMB_V4_1`) | Sammenligning / Tærskel |
|---|---:|---|---|
| **RV-ankre & stdlib-BERV** | `2.424` ankre | `1.979` rene absorptionstilpasninger; median `\|emp - prior\| = 0,5138 km/s` | Max `\|BERV - stdlib\| = 0,1714 km/s <= 0,50` |
| **Suite A: Kanal `T` enkelt-epoke** | `1.080` | `>= 8σ` genfinding = **`90,74 %`** (`0,90741`) | Krav `>= 70 %` — **PASS** |
| **Suite B: Kanal `P` persistent** | `540` | `>= 9σ` genfinding = **`89,51 %`** (`0,89506`) | Krav `>= 75 %` — **PASS** |
| **Suite C: Kepler `T_DIFF` vs `K_PLANET`** | `135` | `>= 6,5σ`: `T_DIFF = 0,00 %` vs **`K_PLANET = 50,62 %`** | `0,50617 > 0,0` — **PASS** |
| **Suite D: Detektor `G4/G5` fysik** | `216` | Sand LSF **`94,44 %`** (`68/72`); 1-px kosmisk **`100,0 %`**; plateau **`100,0 %`** | Krav `>= 90 %, 100 %, >= 95 %` — **PASS** |
| **Suite E: Sparsom `G6` vs Tæt `V3.5`** | `240` | Sparsom `G6`: True **`100 %`**, OH **`100 %`**, warm-px **`100 %`**, intra-BERV **`100 %`** | Tæt `V3.5`: intra-BERV `0 %` — **PASS** |
| **Suite F: `COMB_V4_1` vs `COMB_V4`** | `486` | `>= 3,8σ`/tand: **`82,87 %`**; 1-linje FPR **`0,00 %`**; topo ro-vib FPR **`0,00 %`** | Skov-pseudokam FPR: `COMB_V4 = 100,0 %` -> **`COMB_V4_1 = 0,00 %`** — **PASS** |
| **`D085` Read-Only `COMB_V4_1`-test** | `19` kandidater | Alle `19` `D085` SPIRou `COMB_V4` falske alarmer (`Lalande 21185` [17], `Rho CrB` [2]) -> **`0` overlevere** | **`19 -> 0`** (**PASS**) |

---

## 3. Falsk-Alarm Kaskade og `100 %` Forensisk Opklaring (`0` ETI)

Over i alt **`59.993.954` søgte 1D-spektralelementer** (`45.731.281` `T`, `6.929.242` `P`, `3.665.745` `T_DIFF`, `3.667.686` `K_PLANET`) samt **`131.321.712` `COMB_V4_1`-konfigurationer**:

- **Enkeltlinjekaskade:** `2.990` `Legacy V2` -> `2.428` `V3.7 G1` -> `1.447` efter `G2` -> `1.085` efter `G3/G4` -> `886` pre-`G6` -> **`865` post-`G6` kandidater** (`49` kontrol, `816` science; **`0` orbitale** i de `10` banekampagner).
- **Kam-kaskade (`COMB_V4 -> COMB_V4_1` på `D086`):** **`5.417`** rå `COMB_V4`-kandidater reduceres automatisk til blot **`6`** `COMB_V4_1`-kandidater (**`99,89 %` reduktion**).
- **Forensisk opklaring (`FORENSIC_CANDIDATE_AUDIT_D086.json`):** Samtlige **`865` enkeltlinje-** og **`6` `COMB_V4_1`-kandidater** er fuldt forensisk klassificeret med **`eti_plausible = False`** og **`verified_eti_detections = 0`**:
  - **Enkeltlinje (`865`):** `577` `FIBER_B_SIMULTANEOUS_CALIBRATION_BLEED` (ESPRESSO `TRG_CALB` / HARPS `WAVE` kalibreringslyslæk ind i svag M-dværg Fiber A, op til `~1.800×` Fiber-B/Fiber-A kontrast), `171` `SINGLE_EPOCH_STELLAR_ACTIVITY_OR_NOISE_EXCURSION`, `100` `DETECTOR_ORDER_JOIN_OR_CR_ARTIFACT`, `8` `NUV_OZONE_CUTOFF_LOW_SNR_FLUCTUATION`, `8` `PHOTOSPHERIC_FEI_TIO_TEMPLATE_RESIDUAL`, `1` `CHROMOSPHERIC_FLARE_OR_WING`.
  - **Frekvenskamme (`6`):** `2` `ESPRESSO` `GJ1002` `40 GHz` (`OPT_GREEN` `4976–4978 Å`) = `FIBER_B_FABRY_PEROT_HARMONIC_BLEED` (`2 × 20 GHz` FSR etalon-læk i `TRG_CALB`); `4` `HARPS` (`HD19994` [2], `TAUCET` [2]) = `PHOTOSPHERIC_TEMPLATE_MISMATCH_OR_WAVE_CAL_RIPPLE` (`[Fe/H]`/rotations-mismatch i delte Fe I-bånd).

---

## 4. Øvre Effektgrænser, `13`-Stjerners Bro og Samlet `> 3`-Oktav All-Sky Syntese

- **Nye `D086` øvre `8σ`-grænser (`185` rene spektrale celler, Gaia DR3 `G_BP`/`G`, `0` NaN, max stdlib-afvigelse `5,71e-10`):**
  - `UVES_NUV` (`61` celler, `10` stjerner): ned til **`0,800 W`** (10 m CW transmitter) på **`PROXIMACEN`** ved `3180 Å` (`U1_NUV_O3_3180`; **`1,61 W`** ved `3335 Å`, **`2,47 W`** ved `3520 Å`, **`4,60 W`** ved `3685 Å`, **`6,00 W`** ved `3844,8 Å`), median `41.139 W`.
  - `ESPRESSO` (`36` celler, `4` stjerner): ned til **`13,687 W`** på **`GJ1061`** (`B1_UVBLUE_3844`), median `74,12 W`.
  - `HARPS` (`88` celler, `11` stjerner): ned til **`85,026 W`** på **`GJ729`** (`B1_UVBLUE_3844`), median `14.554 W`.
- **Pankromatisk bro vokser `8 -> 13` stjerner (`253` båndceller):** Omfatter nu `PROXIMACEN` (`25` celler fra `0,3180` til `1,6642 µm`, **tri-regime NUV + Optisk + NIR**), `GJ285` (`0,3180–2,4580 µm`), `EPSERI`, `TAUCET`, `GJ1002`, `YZCET` samt `AUMIC`, `BARNARDSSTAR`, `DXCNC`, `GJ486`, `HD42581`, `LALANDE21185` og `WOLF359`.
- **Kumulativt All-Sky Survey (`D079–D086`, `> 3` spektrale oktaver `0,305–2,515 µm`):**
  - **`8` uafhængige echelle-spektrografer** (`HARPS`, `ESPRESSO`, `NIRPS`, `CRIRES+`, `HARPS-N`, `CARMENES_VIS`, `SPIROU`, **`UVES_NUV`**)
  - **`175` unikke stjerner** (`143` science [`102` planetværter / `201` planeter] + `32` kontroller), **`1.190` eksponeringer** (`252,25 h`), **`15.981` kalibreringsforsøg**, **`15.097` `V2` falske alarmer elimineret**, **`50` orbitale banekampagner**
  - **`90` stjerner inden for `10 pc`** (`68` science [`45` værter / `94` planeter] + `22` kontroller; median `P_10m = 2,0983 kW`; rekord **`0,80 W`** på Proxima Cen)
  - **`181` distinkte multi-messenger systemer** med **`18` direkte optisk/NIR/NUV + radio/TESS overlaps** (tilføjer `LHS 1140`, `HD 192263`, `HD 19994` og `HD 11964`) og **`0` verificerede ETI-detektioner**.
