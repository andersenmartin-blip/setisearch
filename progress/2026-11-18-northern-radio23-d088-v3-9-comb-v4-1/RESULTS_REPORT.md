# Fase `D088` Resultatrapport — 100 % Nordlig `1,4 GHz` Radio-Echelle Lukning (`23/23`), Retroaktiv All-Sky `COMB_V4_1` Sweep (`1.567` Eksponeringer) & `220`-Stjerners (`12` Spektrografer) Syntese

**Dato:** 19. november 2026  
**Fase:** `D088` / `Trin 11` (`NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_V3_9`)  
**Prospektiv metodelås:** `2026-11-18T17:00:07Z` (`METHOD_LOCK.json` SHA-256 `7348f0f516e8192cc08cc6e1a6a73283afb3733bd090dc0a1358ab00ce4d2f12`, første datanedhentning `+8,0 s` ved `2026-11-18T17:00:15Z`, suppleret af `IMPLEMENTATION_LOCK.json` for dokumenterede ikke-gate header-/kalibreringsrettelser med `v3_9_detector.py` og `FROZEN_COHORT_D088.csv` 100 % uændrede)  
**Uafhængig ren-stdlib audit (`/usr/bin/python3 -S audit.py`):** **16/16 PASS** (`100 %` SHA-256 bit-identitet på tværs af `25/25` filer mellem `--from-full-inputs` og `--from-bounded-inputs`, bundt `8,34 MiB < 25,0 MiB`)  
**Verificerede ETI-detektioner (`D088`, all-sky `COMB_V4_1` og kumulativt `D079–D088`):** **`0`**

---

## 1. Videnskabeligt Formål og Prospektiv Kohorte

Fase `D088` (`Trin 11`) gennemfører to afsluttende milestene for det prospektivt låste echelle-SETI-survey over **4,457 spektrale oktaver (`0,1145–2,515 µm`)**:

1. **Komplet nordlig `1,4 GHz` radio-echelle lukning (`23/23 = 100 %`) & 3 nye nordlige/Maunakea echelle-spektrografer (`9 -> 12` spektrografer / `10 -> 13` arme):** Tilføjer franske **OHP `SOPHIE`** ($R = 75{.}000$, `0,3872–0,6943 µm`), **OHP `ELODIE`** ($R = 42{.}000$, `0,4000–0,6800 µm`) og CFHT Maunakea **`ESPaDOnS`** ($R = 65{.}000\text{–}80{.}000$, `0,370–1,048 µm`) til de sidste **`6` hidtil ubrogede nordlige GBT `1,4 GHz`-exoplanetværter** (**`47UMA` [`M19`], `HD154345` [`M21`], `HD33564` [`M23`], `HD127506` [`M27`], `PSI1DRAB` [`M28`] og `BETUMI` [`M30` Kochab]**) sammen med **`14` nye `< 10 pc` nordlige mål** (`20` helt nye unikke stjerner med `min_prior_sep = 10.643,93"` mod alle `241` tidligere `C001–D087`-koordinater og `min_intra_sep = 14.168,73"`), `0` eksponerings-`dp_id`-overlap mod `1.769` ekskluderede `dp_id`'er (inkl. format-kontrolstjernen `HD172167` Vega) samt **`5` `< 10 pc` pankromatiske brostjerner** på `CFHT_ESPADONS` (**`61CYGA`, `61CYGB`, `GXAND`, `GJ687`, `LALANDE21185`**), hvoraf de første `4` bliver helt nye brostjerner (`17 -> 21` broer, `415` celler) og `GJ687` allerede er radio-mål `M14`.
2. **Read-only retroaktiv `COMB_V4_1`-udrulning over alle `1.009` cachede `D079–D085` råeksponeringer (`158` stjerne-fase stacks):** Forenes med de frosne `D086` (`31` stacks / `181` eksp.), `D087` (`33` stacks / `201` eksp.) og nye `D088` (`25` stacks / `176` eksp.) frekvenskams-resultater til én uniform **all-sky `COMB_V4_1`-syntese over samtlige `247` stacks / `1.567` eksponeringer (`100 %` af `D079–D088`)**.

- **Låst `D088`-kohorte (`FROZEN_COHORT_D088.csv`):** **`25` stjerner** og **`176` offentlige eksponeringer** (`30,5423` timers eksponeringstid; `6` nul-planet kontrolstjerner `HD109358`, `HD114710`, `HD6582`, `HD30652`, `HD4614`, `HD39587` + `19` science-stjerner):
  - **`68` `OHP_SOPHIE`-eksponeringer** (`9` stjerner; `s1d` + `e2ds` Fiber-A/B): empirisk Astropy ICRS-krydstjek afslørede og rettede OHP DRS header-BERV-drift på `2` april–maj 2023 `47UMA`-eksponeringer (`SOPHIE_3375820`: `-0,778 km/s`; `SOPHIE_3381430`: `-0,392 km/s`).
  - **`48` `OHP_ELODIE`-eksponeringer** (`7` stjerner): empirisk `HD6582`-test (`BERV = -6,00..+21,46 km/s`) dokumenterede, at `ELODIE` `z=s1d` (`SPECSYS=None`, `CTYPE1=AWAV`) er topocentrisk luft og konverteredes deterministisk til barycentrisk via `(1 + BERV/c)`.
  - **`60` `CFHT_ESPADONS`-eksponeringer** (`9` stjerner): `load_espadons_i` håndterer både 12-rækkers polarimetri (`54` filer) og 28-rækkers `Spectroscopy, star+sky` (`6` filer).
- **`10` orbitale banekampagner (`#61–#70` kumulativt):** `3` nul-kontroller (`HD109358`, `HD6582`, `HD39587`) + `7` planetværter (`47UMA` [`47 UMa b`], `BETUMI` [`bet UMi b`], `GJ49` [`Gl 49 b`], `GJ625` [`GJ 625 b`], `GJ686` [`Gl 686 b`], `HD127506` [`HD 127506 b`], `HD33564` [`HD 33564 b`]; hver `4 IN + 4 OUT`; max `|Kp_stdlib - Kp_csv| = 0,00005 km/s`).

---

## 2. Kalibreringsvalidering (`2.697` Forsøg) og Kinematisk Verifikation

| Kalibrerings- / Verifikationssuite | Antal | Resultat i `D088` (`V3.9` + `COMB_V4_1`) | Krav / Reference |
|---|---:|---|---|
| **Pure-stdlib BERV & NIST RV-ankre** | `176` eksp / `2.704` ankre | Max `\|BERV - stdlib\| = 0,1308 km/s`; `2.327` rene fits, median `\|emp - prior\| = 0,3411 km/s` | Gate `<= 0,50 km/s` (**PASS**) |
| **Kanal `T` enkelt-epoke** | `1.080` | `>= 8σ` genfinding = **`100,00 %`** (`648/648`) | **PASS** |
| **Kanal `P` persistent** | `540` | `>= 8σ` genfinding = **`100,00 %`** (`324/324`) | **PASS** |
| **Kepler `T_DIFF` vs `K_PLANET`** | `135` | `>= 6,5σ`: `T_DIFF = 0,00 %` vs **`K_PLANET = 100,00 %`** | **PASS** |
| **Detektor `G4_V38 + G5` fysik** | `216` | Sand LSF **`100,00 %`** (`72/72`); kosmisk **`100,00 %`** (`0/72`); plateau **`100,00 %`** (`0/72`) | **PASS** |
| **Sparsom `G6_V36` benchmark** | `240` | Sand **`100,0 %`**, OH **`100,0 %`**, hot-px **`100,0 %`**, intra-BERV **`100,0 %`** | **PASS** |
| **`COMB_V4_1` vs `COMB_V4`** | `486` | `>= 3,8σ`/tand (`40/60/100 GHz`): **`97,22 %`**; 1-linje `0,00 %`; topo `0,00 %` | Skov-FPR: `COMB_V4 = 100,00 %` -> **`COMB_V4_1 = 0,00 %`** |
| **`D086` `G4_V38` Fiber-B regression** | `577` kandidater | Alle `577` `D086` Fiber-B falske alarmer -> **`0` overlevere** (`D088` cal/Fiber-B veto = `3`) | **`577 -> 0`** (**PASS**) |

---

## 3. Falsk-Alarm Kaskade (`D088`) & All-Sky `COMB_V4_1` (`1.567` Eksponeringer / `247` Stacks)

Over **`23.986.101` Kanal-`T`**, `3.444.377` `P`, `1.303.553` `T_DIFF`, `1.306.338` `K_PLANET` 1D-bins og `26.168.368` `D088` `COMB_V4_1`-konfigurationer:

- **Enkeltlinjekaskade (`D088`):** **`99.910` `Legacy V2`** $\rightarrow$ `4.727` `G1` $\rightarrow$ `164` `G2` $\rightarrow$ `27` `G3` $\rightarrow$ `24` `G4` (inkl. `3` Fiber-B/kal-vetoer) $\rightarrow$ **`20` pre-`G6` / post-`G6`** (`1` kontrol, `19` science; **`0` orbitale** i `#61–#70`). Samtlige `20` overlevere er forensisk afklaret (`FORENSIC_CANDIDATE_AUDIT_D088.json`, `eti_plausible = False`): **`19` `MOLECULAR_TIO_VO_BANDHEAD_OR_ACTIVE_CONTINUUM`** (`15` på `GJ625`, `1` `HD157881`, `3` `LALANDE21185`) og **`1` `SIMULTANEOUS_CAL_FIBER_ARTIFACT`** (`HD114710` kontrol).
- **All-Sky `COMB_V4_1` (`D079–D088`, `247` stacks / `1.567` eksponeringer = `100 %`):**
  - `D079` (`12/60`), `D080` (`26/130`), `D081` (`22/159`), `D082` (`22/152`, `V4: 2 -> V4.1: 0`), `D083` (`22/148`, `V4: 1 -> V4.1: 1` `BETPIC` `50 GHz`), `D084` (`25/183`, `V4: 8 -> V4.1: 5` på M-dværge `DXCNC, GJ486, LALANDE21185, STRUVE2398B, WOLF359`), `D085` (`29/177`, `0`), `D086` (`31/181`, `V4: 5417 -> V4.1: 6`), `D087` (`33/201`, `V4: 6 -> V4.1: 3`), `D088` (`25/176`, `0`).
  - **Samlet All-Sky total (`ALLSKY_COMB_V4_1_UNIFIED_D079_D088.csv`):** **`5.434` `COMB_V4` $\rightarrow$ `15` `COMB_V4_1`-kandidater**, samtlige `15/15` forensisk naturlige (`10` `COOL_STAR_MOLECULAR_BAND_PSEUDOCOMB`, `5` `PHOTOSPHERIC_OR_TELLURIC_PSEUDOCOMB`, **`0` verificerede ETI-kamme**).

---

## 4. Øvre Effektgrænser (`D088`) & Samlet `220`-Stjerners / `23/23` Radio-Echelle Lukning

- **`225` nye `D088` `8σ`-effektgrænser (`0` NaN; max ren-stdlib Planck/`JOHNSON_V` afvigelse = `4,16e-05`):**
  - **`OHP_SOPHIE`** (`81` celler, `9` stjerner, `Gaia G`, median `78,521 kW`): ned til **`0,5181 kW` (`518,1 W`)** på **`GJ 625`** (`S2_BLUE_4244`, `S1_VIOLET_4050`: `0,6695 kW`, `S3_BLUEGRN_4675`: `0,7572 kW`).
  - **`CFHT_ESPADONS`** (`81` celler, `9` stjerner, dual `Gaia G`/`G_RP`/`2MASS-J` + `JOHNSON_V` til `BETUMI`, median `52,632 kW`): ned til **`1,0796 kW`** på **`GJ 687`** (`C1_UVBLUE_3844`), **`1,2865 kW`** på **`Lalande 21185`** og **`1,8559 kW`** på **`GX And`**.
  - **`OHP_ELODIE`** (`63` celler, `7` stjerner, `Gaia G`, median `125,74 kW`): ned til **`49,434 kW`** på **`HD 10476`** (`E3_BLUEGRN_4675`), **`53,48 kW`** på **`HD 127506`** og **`55,068 kW`** på **`HD 165341`**.
- **Afsluttet All-Sky & Space Survey (`D079–D088`, `0,1145–2,515 µm`, `4,457` oktaver):**
  - **`12` spektrografer (`13` arme)**, **`220` unikke echelle-stjerner** (`176` science [`121` planetværter / `238` planeter] + `44` kontroller), **`1.567` eksponeringer** (`365,80` timer), **`21.375` kalibreringsforsøg**, **`233.001` `V2`-falskalarmer elimineret**, **`70` orbitale kampagner**.
  - **`117` stjerner inden for `10 pc`** (`85` science [`50` værter / `99` planeter] + `32` kontroller; median `P_10m = 1,7757 kW`; all-time rekord **`0,0973 W` [`97,3 mW`]** på `Proxima Centauri` i rum-FUV `HST_STIS`).
  - **`21` pankromatiske brostjerner (`415` celler)** og **`220`-systems multi-messenger syntese** med **`23/23` (`100 %`) `Parkes`/`GBT` `1,4 GHz` radio-echelle lukning** + `1` `TESS` (`L 98-59`) = **`24` direkte overlaps** og **`0` verificerede ETI-detektioner**.
