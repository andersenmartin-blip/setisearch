# Spor N10 — Blind-Spot Multi-Morfologi Radio-SETI i Rå Breakthrough Listen GBT `ABACAD`-Kadenser (`6` `< 5 pc` Mælkevejs-M-Dværge)

**Kampagne-ID:** `SPOR_N10_BL_RADIO_BLINDSPOT_ABACAD` · **Dato:** 27. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Mælkevejs-ETI · `N10_RADIO_BLINDSPOT_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Resumé

**Spor N10** bygger direkte oven på vores eget rene Mælkevejs-katalog (`< 10 pc` M-dværge med bekræftede exoplaneter) og vores tidligere `seti-repeater`-arbejde, men skifter fra traditionel smalbånds- og katalogsøgning til **rå Green Bank Telescope (`GBT`) L-bånds (`1.080–1.920 MHz`, `1.475,1 MHz` Vandhullet) Breakthrough Listen `ABACAD` ON–OFF-spektrogrammer (`.0002.h5`)** gennem en ny **4-spors Blind-Spot Detektor (`M1–M4`)**, målrettet signaler som standard lineær `turboSETI` ikke kan fange:

- **Analysepopulation (Streng Mælkevej `< 5 pc`, hentet & MD5-verificeret `36/36` HDF5 = `8,05 GiB`):**
  - `6` komplette 6-scans `ABACAD`-kadenser (`4.118,3 MHz` samlet ren båndbredde tværs over `2.829` rene `512`-kanalers felter): **`GJ 411`** (`2,55 pc`, `2` pl.), **`GJ 65A`** (`2,67 pc`, `0` pl.), **`GJ 54.1`** (`3,72 pc`, `3` pl.), **`GJ 273`** (`3,79 pc`, `2` pl.), **`GJ 687`** (`4,55 pc`, `2` pl.) og **`GJ 1002`** (`4,85 pc`, `2` pl.).
- **Prospektiv blind låsning:** `METHOD_LOCK.json` forseglet præ-datahentning kl. `2026-11-27T20:21:50+00:00`, og den paralleliserede/noise-kalibrerede `n10_radio_blindspot_analyzer.py` (SHA-256 `ca65404e9a315c2ca6d50452741c73499a29fc2d05508598a0f359321ae60a10`) låst præ-Stage-2 før første analyseoutput.
- **1.200-Forsøgs Hoved-Mod-Hoved Benchmark i Rigtig GBT L-Båndsstøj:**
  - Samme detektor-kerne testet mod en klassisk 1-bin lineær fuld-scan baseline (`turboSETI`-analog):
    - **Plasma-udtværede (`PLASMA_BROADENED`, Gajjar-regimet):** N10 = **`281/300` (`93,67 %`)** mod Klassisk = **`0/300` (`0,00 %`)**.
    - **Krumme/accelererede Doppler-baner (`CURVED_DRIFT`):** N10 = **`244/300` (`81,33 %`)** mod Klassisk = **`0/300` (`0,00 %`)**.
    - **Korte intermitterende pakker (`SHORT_BURST`, `1,5–5 %` duty cycle):** N10 = **`265/300` (`88,33 %`)** mod Klassisk = **`0/300` (`0,00 %`)**.
    - **Frekvens-hop (`FHSS_HOPPING`, 8-hop gitter):** N10 = **`294/300` (`98,00 %`)** mod Klassisk = **`0/300` (`0,00 %`)**.
    - **Samlet genfinding:** **`90,33 %` (`1.084/1.200`)** for Spor N10 mod **`0,00 %` (`0/1.200`)** for klassisk 1-bin lineær søgning.
- **Stage 2 → Stage 3 Forensisk Veto (`136 -> 0 ETI` tværs over `36` rå HDF5-filer):**
  - Stage 2 fandt `136` `ABACAD`-triggere (`23` `M1_BROAD_CURVED` + `111` `M2_SHORT_BURST` + `2` `M3_FHSS_AC2D` + `0` `M4`).
  - Live kryds-kadence & svag-`OFF` kontrol på alle `36` `.0002.h5` filer afklarede samtlige `136`: `31` naturlig galaktisk `HI 21-cm`-emission (`1420,4 MHz`), `28` *Inmarsat* GEO MSS (`1525–1560 MHz`), `22` *GPS L1* (`1575,4 MHz`), `15` *GPS L5/Galileo E5* (`1176,5 MHz`), `11` *Iridium/Globalstar* (`1610–1626 MHz`), `9` *ADS-B/DME*, `9` *FAA Radar/GPS L3*, `5` delt `1647,5 MHz` satellit-RFI (observeret i 5 stjerner), `4` *METSAT* `1700 MHz`, `1` *PCS* `1909 MHz` (alle 6 stjerner), samt `1` `1500,00 MHz` `BLC` beregningsnode-kant (bekræftet ved at trimme `20` kantkanaler) $\rightarrow$ **`0` verificerede radio-ETI**.
- **Fysiske EIRP-grænser & Bayesianske $f_{95}$ (`0` ETI):**
  - GBT radiometer-grænser (`SEFD = 10 Jy`): **`171,4–620,8 GW`** (median **`372,0 GW`**) for smalbånd `W=1`, **`1.488,1 GW`** for `W=16` plasma-udtværede signaler, og **`5.235,2 GW`** for korte `τ=8` bursts (langt under Arecibo-radar `~20.000 GW`).
  - **Stjerne-niveau (`N = 6` raw / `5,42` eff.):** Jeffreys $f_{95} = \mathbf{26{,}42\,\%}$ (`28,68 %` eff.) · Uniform `34,82 %` (`37,29 %` eff.).
  - **Stjerne × Frekvens-felt (`2.829` raw / `2.555,51` eff.):** Jeffreys $f_{95} = \mathbf{0{,}0751\,\%}$ · Uniform `0,1171 %`.

---

## 2. Kadenceoversigt & Stage 3 Veto-Tabel

| Stjerne | Afstand (`pc`) | Exoplaneter | Ren BW (`MHz`) | EIRP `W=1` (`GW`) | Stage 2 (`M1/M2/M3/M4`) | Vetoed / ETI |
| --- | --- | --- | --- | --- | --- | --- |
| `GJ 411` (`--72283`) | `2,55` | `2` | `686,62` | `171,4` | `0 / 31 / 0 / 0` (`31`) | `GPS L1` (`22`) + `Galactic HI` (`9`) $\rightarrow$ `0 ETI` |
| `GJ 65A` (`--73638`) | `2,67` | `0` | `686,12` | `189,1` | `0 / 13 / 0 / 0` (`13`) | `Radar` (`9`) + `Inmarsat` (`4`) $\rightarrow$ `0 ETI` |
| `GJ 54.1` (`--73620`) | `3,72` | `3` | `686,15` | `365,1` | `5 / 25 / 0 / 0` (`30`) | `Inmarsat` (`23`) + `Galactic HI` (`5`) + `METSAT` (`2`) $\rightarrow$ `0 ETI` |
| `GJ 273` (`--517180`) | `3,79` | `2` | `686,73` | `378,9` | `12 / 12 / 2 / 0` (`26`) | `Iridium` (`11`) + `Galactic HI` (`9`) + `1647.5 Sat` (`5`) + `1500 Node` (`1`) $\rightarrow$ `0 ETI` |
| `GJ 687` (`--75045`) | `4,55` | `2` | `688,11` | `547,2` | `6 / 27 / 0 / 0` (`33`) | `GPS L5` (`15`) + `ADS-B` (`9`) + `Galactic HI` (`6`) + `METSAT` (`2`) + `PCS` (`1`) $\rightarrow$ `0 ETI` |
| `GJ 1002` (`--72885`) | `4,85` | `2` | `684,57` | `620,8` | `0 / 3 / 0 / 0` (`3`) | `Galactic HI` (`2`) + `Inmarsat` (`1`) $\rightarrow$ `0 ETI` |

---

## 3. Figurer, Audit & Reproducerbarhed

- **Visuelt verificerede 300-DPI PNGs (`figN10_01`–`figN10_06`, godkendt i `VISUAL_REVIEW_N10.json`):** GBT L-bånds RFI & EIRP, `1.200`-forsøgs hoved-mod-hoved benchmark (N10 vs. klassisk 1-bin lineær), reelle `ABACAD` vandfalds-cutouts (`CTRL_GJ54.1`, `GJ 273 1647,5 MHz`, `GJ 687 HI 21-cm`), `M3`/`M4`-diagnostik, `136 -> 0` veto-tragt + Bayesianske $f_{95}$ og samlet Mælkevejs-syntese.
- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n10_radio_blindspot.py`):** **`N10_RADIO_BLINDSPOT_AUDIT: 12/12 PASSED`** (`external_contacts == 0`).
- **Lokal arkivpakke:** `archives_n10/SETI_N10_BL_RADIO_BLINDSPOT_ABACAD_2026-11-27.zip`.
