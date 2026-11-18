# Fase `D087` Resultatrapport — Rum-FUV (`HST_STIS E140M`), Fjernrød (`VLT UVES_RED`), `G4_V38` & `200`-Stjerners (`> 4` Oktavers) Syntese

**Dato:** 18. november 2026  
**Fase:** `D087` / `Trin 10` (`SPACE_UV_STIS_AND_FARRED_V3_8`)  
**Prospektiv metodelås:** `2026-11-18T04:33:13Z` (`METHOD_LOCK.json` SHA-256 `0c5ae97eab051aced0652317a65ac6215f33e4565351a5e42d5ee424e693cd53`, første datanedhentning `+8,6 s` [afrundet `+8,0 s` i UTC-sekundtjek] ved `2026-11-18T04:33:21Z`, suppleret af `IMPLEMENTATION_LOCK.json` for dokumenterede ikke-gate bugfixes/Astropy-BERV fallback med `v3_8_detector.py` og `FROZEN_COHORT_D087.csv` 100 % uændrede)  
**Uafhængig ren-stdlib audit (`/usr/bin/python3 -S audit.py`):** **15/15 PASS** (`100 %` SHA-256 bit-identitet på tværs af `23/23` filer mellem `--from-full-inputs` og `--from-bounded-inputs`, bundt `19,32 MiB < 25,0 MiB`)  
**Verificerede ETI-detektioner (`D087` og kumulativt `D079–D087`):** **`0`**

---

## 1. Videnskabeligt Formål og Kohorte

Fase `D087` (`Trin 10`) bryder den jordbundne ozonmur (`0,305 µm`) med rum-baserede **Hubble Space Telescope `HST_STIS` `E140M`** far-UV echelle-spektre (**`0,1145–0,1710 µm`** vakuum, $R = 45{.}800$, direkte CALSTIS spektrofotometri `HST_CALSTIS_DIRECT_FLAM`) og lukker det fjernrøde gap (`0,5655–1,0425 µm` luft, $R = 42{.}310\text{–}107{.}200$) med Paranal VLT **`UVES_RED`** (dual Gaia DR3 $G_{\mathrm{RP}}$ `< 8500 Å` + 2MASS $J$ `>= 8500 Å`) samt **`ESPRESSO`** (`HR` $R = 140{.}000$ + `GJ 3138` med `1 × UHR` [$R = 190{.}000$] + `7 × HR`). Dermed spænder det prospektivt låste echelle-survey nu **over 4 spektrale oktaver (`0,1145–2,515 µm`, `4,457` oktaver)** på **9 spektrografer (10 spektralarme)** og når præcis **`200` unikke stjerner**, **`103` `< 10 pc` stjerner**, **`17` pankromatiske brostjerner**, **`60` orbitale kampagner** og **`206` distinkte multi-messenger systemer**.

- **Låst `D087`-kohorte (`FROZEN_COHORT_D087.csv`):** **`33` stjerner** og **`201` eksponeringer** (`83,0104` timers eksponeringstid; `37` kontrol / `164` science):
  - **`54` `HST_STIS` `E140M`-eksponeringer** (`10` stjerner, `1145–1710 Å` vakuum, $R = 45{.}800$, max `|v_helio_hdr - stdlib| = 0,1328 km/s <= 8,50 km/s` LEO-gate)
  - **`55` `UVES_RED`-eksponeringer** (`10` stjerner, `5655–10425 Å` luft, $R = 42{.}310\text{–}107{.}200$)
  - **`92` `ESPRESSO`-eksponeringer** (`13` stjerner inkl. `1` `UHR` $R=190{.}000$ + `7` `HR` $R=140{.}000$ på `GJ 3138`, max `|BERV - stdlib| = 0,1632 km/s <= 0,50 km/s` på tværs af alle `147` jordbundne eksponeringer inkl. `21` `esotk` `S1D_STACK_A` med Astropy BERV-korrektion)
- **Nye mål vs. pankromatisk bro (`0` `dp_id`-overlap):** `25` helt nye unikke stjerner (**`13` inden for `10 pc`**, minimal skyseparation mod alle tidligere `C001–D086`-mål = **`4.691,60"`**, `0` eksponerings-`dp_id`-overlap, eksplicit eksklusion af `o45931020` / `BD+28D4211`) samt **`8` eksisterende stjerner** udvidet med rum-FUV eller fjernrød dækning: **`PROXIMACEN`** (nu **kvadri-regime Rum-FUV + NUV + Optisk + NIR** `0,1275–1,6642 µm`, `29` broceller), **`AUMIC`**, **`ADLEO`**, **`HD209458`**, **`GJ1061`**, **`GJ729`**, **`EPSERI`** og **`GJ285`**. Hvide `GJ 1061`, `GJ 729`, `AD Leo` og `HD 209458` promoverer bro-antallet **`13 -> 17` stjerner** (`334` båndceller).
- **Kontroller & Banekampagner (`#51–#60`):** `6` verificerede `n_exo = 0` kontrolstjerner (`41ARA`, `HD100623`, `G16028`, `GJ105B`, `HD142373`, `HD73752`), `27` science-stjerner og **`10` orbitale banekampagner** (`3` kontroller + `7` planetværter: `AUMIC` [`HST_STIS`, `AU Mic b`], `CDCET` [`CD Cet b`], `GJ3138` [`GJ 3138 b`, `UHR+HR`], `HD40307` [`HD 40307 b`], `K23` [`K2-3 b`], `TOI178` [`TOI-178 b`], `TOI700` [`TOI-700 b`]; hver `4 IN + 4 OUT`; max `|Kp_stdlib - Kp_csv| = 0,00005 km/s`).

---

## 2. Kalibreringsvalidering (`2.697` Syntetiske Forsøg) og `D086` `G4_V38`-Regression (`577 -> 0`)

Den nye **`G4_V38`** Fiber-B kalibrerings-bleed-veto (`fb_pk / fa_med >= 1,5` i simultan `CAL/WAVE/FP/THAR`-tilstand, kombineret med `STIS_MAMA_DQ_FLAG` & `STIS_MAMA_SLIT_BACKGROUND`) eliminerer bagudrettet **100 %** af de `577` Fiber-B falske alarmer fra `D086`:

| Kalibreringssuite | Antal forsøg | Nøgleresultat i `D087` (`V3.8` + `COMB_V4_1`) | Krav / Reference |
|---|---:|---|---|
| **RV-ankre & stdlib-BERV/LEO** | `2.596` ankre | `1.439` rene absorptionstilpasninger; median `\|emp - prior\| = 0,4998 km/s` | Ground `<= 0,1632 km/s` (`<= 0,50`), STIS LEO `<= 0,1328 km/s` (`<= 8,50`) |
| **Kanal `T` enkelt-epoke** | `1.080` | `>= 8σ` genfinding = **`100,00 %`** (`648/648`) | **PASS** |
| **Kanal `P` persistent** | `540` | `>= 8σ` genfinding = **`100,00 %`** (`324/324`) | **PASS** |
| **Kepler `T_DIFF` vs `K_PLANET`** | `135` | `>= 6,5σ`: `T_DIFF = 0,00 %` vs **`K_PLANET = 100,00 %`** | **PASS** |
| **Detektor `G4_V38 + G5` fysik** | `216` | Sand LSF **`100,00 %`** (`72/72`); 1-px kosmisk **`100,00 %`** (`0/72` læk); plateau **`100,00 %`** (`0/72` læk) | **PASS** |
| **Sparsom `G6_V36` benchmark** | `240` | Sand **`100,0 %`**, OH **`100,0 %`**, warm-px **`100,0 %`**, intra-BERV **`100,0 %`** | **PASS** |
| **`COMB_V4_1` vs `COMB_V4`** | `486` | `>= 3,8σ`/tand: **`69,91 %`**; 1-linje FPR **`0,00 %`**; topo ro-vib FPR **`0,00 %`** | Skov-FPR: `COMB_V4 = 98,15 %` (`53/54`) -> **`COMB_V4_1 = 0,00 %`** (`0/54`) |
| **`D086` `G4_V38` Fiber-B regression** | `577` kandidater | Alle `577` `D086` Fiber-B falske alarmer -> **`0` overlevere** | **`577 -> 0`** (**100,0 % veto, PASS**) |

---

## 3. Falsk-Alarm Kaskade og `100 %` Forensisk Opklaring (`0` ETI)

Over **`60.460.443` søgte 1D-spektralelementer** (`46.203.418` `T`, `6.895.605` `P`, `3.680.710` `T_DIFF`, `3.680.710` `K_PLANET`) og **`107.865.988` `COMB_V4_1`-frekvenskam-konfigurationer**:

- **Enkeltlinjekaskade:** **`117.994` `Legacy V2`** $\rightarrow$ `769` `G1` $\rightarrow$ `580` efter `G2` $\rightarrow$ `338` efter `G3` $\rightarrow$ `269` efter `G4_V38` $\rightarrow$ `123` pre-`G6` $\rightarrow$ `2` `G6` sparsom-veto $\rightarrow$ **`121` post-`G6` kandidater** (`43` kontrol, `78` science; **`0` orbitale** i de `10` kampagner).
- **Kam-kaskade (`COMB_V4 -> COMB_V4_1` på `D087`):** `6` rå `COMB_V4` -> **`3`** `COMB_V4_1`-kandidater (`V41COMB-0001` på kontrol `G16028` `60 GHz` [`S_comb = 9,86`], `V41COMB-0002` på `TOI700` `15 GHz` [`10,02`] og `V41COMB-0003` på `TOI700` `100 GHz` [`9,91`]).
- **Forensisk opklaring (`FORENSIC_CANDIDATE_AUDIT_D087.json`):** Samtlige **`121` enkeltlinje-** og **`3` `COMB_V4_1`-kandidater** har **`eti_plausible = False`** og **`verified_eti_detections = 0`**:
  - **Enkeltlinje (`121`):** `93` `MOLECULAR_TIO_VO_BANDHEAD_OR_ACTIVE_CONTINUUM` (`ESPRESSO`: `50` sci + `38` ctrl; `UVES_RED`: `5` sci), `21` `STIS_FUV_CONTINUUM_OR_MAMA_BACKGROUND` (`HST_STIS` sci), `3` `STIS_FUV_SOLAR_PHOTOSPHERIC_FEATURE` (`HST_STIS` ctrl), `2` `STIS_FUV_GEOCORONAL_AIRGLOW_WING` (`1` sci + `1` ctrl), `1` `SIMULTANEOUS_CAL_FIBER_ARTIFACT` (`ESPRESSO` sci), `1` `TELLURIC_AIRGLOW_OR_OH_MEINEL_WING` (`ESPRESSO` ctrl).
  - **Frekvenskamme (`3`):** Alle `3` er `COOL_STAR_MOLECULAR_BAND_PSEUDOCOMB` (tilfældig TiO/FeH/CN-linjeskov-tilpasning i kølige M-dværge ved `Teff = 3201 K` [`G16028`] og `3459 K` [`TOI700`]).

---

## 4. Sub-Watt Rum-FUV Rekord (`97,3 mW` på `Proxima Centauri`), `200`-Stjerners (`> 4` Oktaver) & `206`-Systems Syntese

- **Nye `D087` øvre `8σ`-effektgrænser (`229` spektrale celler, `0` NaN, max stdlib-afvigelse `1,82e-04`):**
  - `HST_STIS` (`40` celler, `10` stjerner, direkte CALSTIS `FLAM`): ned til **`0,0973 W` (`97,3 mW`!!)** for en `10 m` CW-sender på **`PROXIMACEN`** ved `1275,0 Å` (`F1_FUV_1275`; median `37,6 W`), **`0,7105 W`** på **`GJ 754`** (`5,91 pc`), **`2,1548 W`** på **`AD Leo`** (`4,97 pc`), **`3,0694 W`** på **`HD 209458`** (`48,15 pc`) og **`11,5112 W`** på **`AU Mic`** (`9,71 pc`).
  - `ESPRESSO` (`117` celler, `13` stjerner, Gaia `G`): ned til **`2,4961 W`** på **`PMJ11413`** (`B1_UVBLUE_3844`), **`2,5374 W`** på **`L39968`**, **`2,7119 W`** på **`L47142`** og **`3,8718 W`** på **`CD Cet`** (median `0,9643 kW`).
  - `UVES_RED` (`72` celler, `10` stjerner, dual `G_RP`/`2MASS-J`): ned til **`419,1441 W`** på **`GJ 65 A`** (`BL Cet`, `2,67 pc`, `R4_DIODE_8082` `8082 Å`), **`765,1978 W`** på **`GJ 1224`** og **`968,9825 W`** på **`GJ 1061`** (`R2_DEEPRED_7465`; median `10,2311 kW`).
- **Kumulativt All-Sky Survey (`D079–D087`, **`4,457` oktaver `0,1145–2,515 µm`**):**
  - **`9` spektrografer (`10` arme):** `HST_STIS` (`E140M`), `UVES_NUV`, `HARPS`, `HARPS-N`, `ESPRESSO` (`HR` + `UHR`), `CARMENES_VIS`, `UVES_RED`, `NIRPS_HE`, CFHT `SPIRou`, VLT `CRIRES+`.
  - **`200` unikke stjerner** (`162` science [`111` planetværter / `226` planeter] + `38` kontroller), **`1.391` eksponeringer** (`250` kontrol / `1.141` science; `335,26` timer), **`18.678` kalibreringsforsøg**, **`133.091` `V2` falske alarmer elimineret**, **`60` orbitale banekampagner**.
  - **`103` stjerner inden for `10 pc`** (`77` science [`46` værter / `95` planeter] + `26` kontroller; median `P_10m = 1,6237 kW`; rekord **`0,0973 W`** på Proxima Cen `HST_STIS`).
  - **`17` pankromatiske brostjerner** (`334` båndceller; `PROXIMACEN` spænder `0,1275–1,6642 µm`, `AUMIC` spænder `0,1275–2,458 µm`).
  - **`206` distinkte multi-messenger systemer** med **`18` direkte echelle + `1,4 GHz` radio / `TESS` overlaps** og **`0` verificerede ETI-detektioner**.
