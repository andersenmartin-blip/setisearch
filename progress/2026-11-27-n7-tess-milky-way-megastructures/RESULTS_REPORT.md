# Spor N7 — Ren Mælkevejs-Søgning Efter Megastrukturer & Optiske Fyrtårne med *NASA TESS* (`2-min SPOC`, `558` Stjerner)

**Kampagne-ID:** `SPOR_N7_TESS_MEGASTRUCTURE_AND_OPTICAL_BEACON_MILKY_WAY` · **Dato:** 27. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Mælkevejs-ETI · `N7_TESS_MILKY_WAY_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Resumé

Efter Spor N6 vender **Spor N7** tilbage udelukkende til **kilder i vores egen galakse (Mælkevejen)**. På vores prospektivt prioriterede Mælkevejskohorte (`< 10 pc` $\cup$ `ETZ` $\cup$ `SN 1987A Ellipsoid` $\cup$ `Exoplanet-værter` fra `table1_master_catalog_1083stars.csv`) plus galaktiske kalibreringsbenchmarks (`Boyajians Stjerne / TIC 185336364`, `TOI-700`, `WD 1145+017`) analyserer vi høj-præcisions **`2-minutters NASA TESS SPOC`** rumfotometri for tre fysiske teknosignatur-kanaler:

- **Analyseomfang (Ren Mælkevej):** Ud af `680` prioriterede mål matchede `678` i `TIC v8.2`, hvoraf **`565` unikke mål** havde verificerede 2-minutters `TESS SPOC` `_lc.fits`-lyskurver (`3.064` tilgængelige sektor-FITS på MAST; **`8.638.983`** gyldige 2-minutters målinger over **`15.183,78` sektor-dage**, median støjgulv **`812,54 ppm`**). Efter eksplicit udskillelse af **`6` ekstragalaktiske blazar/AGN-kontroller** (`3C 273`, `PKS 2155-304`, `3C 120`, `OJ 287`, `TXS 0506+056`, `BL Lac`) og `1` TIC-alias-sammenfald (`HD 139139` delte `TIC 100100827` med `WASP-18`) omfatter den **rene Mælkevejs-analyse `558` stjerner** (**`555`** prioriterede Mælkevejs-stjerner + **`3`** særskilte galaktiske benchmarks: `Boyajians Stjerne`, `TOI-700`, `WD 1145+017`).
- **Prospektiv blind låsning:** `METHOD_LOCK.json` (SHA-256 `49370003...`) og analysatoren `n7_tess_megastructure_analyzer.py` (SHA-256 `613128aca582392ce711c043138f4d677a507333bd9597f0408b3915e9863b4d`) blev forseglet kl. **`2026-11-27T18:33:29.550149+00:00`**, før Stage 1-downloads og **`+8 min 09 s`** før Stage 2-analysen (`2026-11-27T18:41:38.855801+00:00`).
- **Tre uafhængige detektionskanaler (`123` Stage 2-triggere $\rightarrow$ `0` ETI):**
  1. **Kanal A (`N7_MEGADIP` — `76` triggere):** Asymmetriske Arnold (2005)- / Dyson-sværm-formørkelser ($\ge 0{,}5\,\%$, `SNR >= 12` over `1,2 / 6 / 24 t`). Alle galaktiske triggere opklares som **kendte transitterende exoplaneter (`25`)**, **unge YSO/protoplanetariske skiver (`21`, inkl. `HD 145718` `18,5 %`, `PDS 70` `6,63 %`, `SZ 90`, `RY Tau`, `LkCa 15`)**, **stjerneplet-rotatorer/binære (`10`)**, **hvide dværg-artefakter/blends (`5`, `sap_drop <= 0` / Jordskin `bkg` op til `2,66×`)**, `TOI-700` benchmark (`1`) og **`4` ekskluderede AGN-kontroller**.
  2. **Kanal B (`N7_COHERENT_BEACON` — `21` triggere):** Smalbåndede periodiske optiske lasere/fyrtårne (`2–300 cyc/dag`, `FFT SNR >= 15`, `SAP SNR >= 8`, `Q >= 4`). Genfinder blindt **magnetiske kataklysmiske variable / Intermediate Polars (`5`: `V1223 Sgr` `f=108,77 c/d`, `PQ Gem` `207,32 c/d`, `FO Aqr` `68,88 c/d`, `AO Psc`, `AE Aqr`)**, **`delta Scuti` / `beta Cep` / AGB-pulsatorer (`7`, inkl. `Sigma Sco`, `HIP 99770`, `HD 172555`, `HD 131835`)**, den **magnetiske hvide dværg `LAWD 96` (`f=8,9071 c/d`, $P=2{,}694\text{ t}$)**, samt **blendede rotatorer (`3`, bl.a. `Wolf 1069` med `CROWDSAP = 0,7559` & `RUWE = 1,42`)**.
  3. **Kanal C (`N7_SYMMETRIC_FLASH` — `43` triggere):** Symmetriske lysssejl-glimt ($\ge 1\,\%$, `SNR >= 15`, anti-FRED $t_{\mathrm{decay}}/t_{\mathrm{rise}} \le 1{,}8$). Samtlige **`41`** tilbageværende skyldes koronale superflares eller hurtig pletrotation på aktive M/K-dværge (bekræftet ved `SIMBAD HARVARD` + `19` uafhængige 2.-sektor `TESS`-tjek).
- **1.200 Syntetiske Injektioner & Bayesianske Nullgrænser (Ren Mælkevej, `0` ETI):**
  - Over tærsklen opnås **`48,0 %`** (Kanal A $\ge 5.000\text{ ppm}$, `84,0 %` ved `2,5 %`), **`97,0 %`** (Kanal B $\ge 500\text{ ppm}$, `100,0 %` ved `2.500 ppm`) og **`57,33 %`** (Kanal C $\ge 1\,\%$, `78,0 %` ved `5,0 %`), svarende til en samlet effektivitet på **`67,44 %`** og **$N_{\mathrm{eff}} = 374{,}29$ Mælkevejsstjerner**.
  - **Ren Mælkevej (`n=555` raw / `N_eff=374,29`):** **Jeffreys $f_{95} = 0{,}3453\,\%$** (`raw`) / **$0{,}5115\,\%$** (`eff`; Uniform `0,7951 %`, Clopper-Pearson `0,7972 %`).
  - **Delkohorter:** **Exoplanet-værter (`n=296`):** Jeffreys **`0,6462 %`** · **`< 10 pc` (`n=224`):** **`0,8529 %`** · **`ETZ` Mælkevej (`n=136`):** **`1,3998 %`** · **`SN 1987A Ellipsoid` (`n=31`):** **`5,9608 %`**.

---

## 2. Prospektiv Blind Låsning & `TESS SPOC`-Indsamling

| Trin | Parameter / Kilde | Resultat | Note |
| --- | --- | --- | --- |
| **Metodelås** | `METHOD_LOCK.json` | Låst `2026-11-27T18:33:29.550149+00:00` | Prospektivt forseglet før Stage 1 download |
| **Analysator** | `scripts/n7_tess_megastructure_analyzer.py` | SHA-256 `613128aca582392ce711c043138f4d677a507333bd9597f0408b3915e9863b4d` | **Urørt efter låsning** |
| **Udvalgt Mælkevej + Bench.** | `table1_master_catalog_1083stars.csv` (`<10pc | ETZ | Ell | Hosts`) + `4` gal. bench. | `680` mål (`678` `TIC v8.2`) | Egenbevægelse ført tilbage `J2016 -> J2000` via `Gaia DR3` |
| **Live Exoplaneter** | `NASA Exoplanet Archive` (`pscomppars` TAP) | `6.162` rækker | Eksakt periodicitet & transitdybder |
| **Live `TESS SPOC` 2-min** | `MAST CAOM + API v0.1` (`_lc.fits`) | **`565`** downloadede lyskurver (`3.064` totalt fundet) | **`8.638.983`** rene kadenser / **`15.183,78`** dage |
| **Ren Mælkevejs-korrektion** | Ekskl. `6` AGN-kontroller & `1` alias (`HD139139`) | **`558`** galaktiske stjerner (**`555`** master + **`3`** bench.) | `0` ekstragalaktiske kilder i finale grænser |

---

## 3. Forensisk Stage 3-Afklaring (`123 -> 0 ETI`)

Tværs over alle `123` Stage 2-triggere kombinerer Stage 3 (`stage3_n7_forensic_vetting.py`) **NASA Exoplanet Archive**, **SIMBAD Harvard TAP**, **Gaia DR3 `RUWE`**, **`SAP_FLUX` vs. `PDCSAP_FLUX`**, **spredt lys (`SAP_BKG`)**, **`CROWDSAP`/centroideforskydning** og **`19` uafhængige 2.-sektor `TESS`-lyskurver**:

| Forensisk Kategori | Antal | Eksempler & Fysisk Årsag | Slutstatus |
| --- | --- | --- | --- |
| `STELLAR_FLARE_OR_ACTIVE_MDWARF_ROTATION` | `41` | `GJ 569 A`, `RY Sex`, `DX Cnc`, `Wolf 359`, `TRAPPIST-1`, `YZ Cet`, `AD Leo` — M-dværg flares & hurtig pletrotation | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `KNOWN_TRANSITING_EXOPLANET` | `25` | `HD 209458` (`1,60 %`), `HD 189733` (`2,48 %`), `WASP-107`, `WASP-76`, `TRAPPIST-1`, `LHS 1140`, `WASP-18` | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `YSO_OR_PROTOPLANETARY_DISK_DIPPER` | `21` | `HD 145718` (`18,5 %`), `SZ 90` (`25,3 %`), `GQ Lup` (`21,1 %`), `PDS 70` (`6,63 %`), `RY Tau`, `AB Aur`, `HD 100546` | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `BLENDED_APERTURE_OR_STARSPOT_ROTATION` | `10` | `GJ 4274` (`CROWDSAP=0,454`), `EQ Peg` (`0,513`), `psi1 Dra B` (`0,141`), `YY Gem`, `KX Lib` | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `STELLAR_PULSATION_OR_AGB_RSG` | `7` | `Sigma Sco` (`bC*`, `4,064 c/d`), `HIP 99770` (`dS*`, `37,44 c/d`), `HD 131835` (`63,59 c/d`), `HD 172555` (`36,52 c/d`), `Mira`, `R Leo`, `Betelgeuse` | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `ACCRETING_WD_INTERMEDIATE_POLAR_SPIN` | `5` | `V1223 Sgr` (`108,77 c/d`), `PQ Gem` (`207,32 c/d`, sec2 `24,1σ`), `FO Aqr` (`68,88 c/d`), `AO Psc` (sec2 `24,5σ`), `AE Aqr` | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `PDC_SAP_DETRENDING_OR_BLENDED_WD_ARTIFACT` | `5` | `VMA2` (`sap_drop=-0,0184`), `GJ 1221` (`bkg=2,66×`, sec2 `1,67σ`), `LAWD 37` (`0,679`), `WD 0552-041` (`0,738`), `GAIA_536000` (`0,0086`) | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `EXTRAGALACTIC_AGN_CONTROL` | `4` | `PKS 2155-304`, `BL Lac`, `OJ 287`, `3C 120` (ekstragalaktiske kontroller udeladt fra Mælkevej) | `VETOED_EXTRAGALACTIC_CONTROL` |
| `BLENDED_APERTURE_ROTATOR_OR_BINARY` | `3` | `Wolf 1069` (`CROWDSAP=0,756`, `RUWE=1,42`), `GJ 65 A` (`CROWDSAP=0,435`), `Fomalhaut C` | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `MAGNETIC_WHITE_DWARF_ROTATION` | `1` | `LAWD 96 / WD 2359-434` (`DAP5.8`, `f=8,9071 c/d`, $P=2{,}694\text{ t}$) | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| `CALIBRATION_BENCHMARK_ASTROPHYSICS` | `1` | `TOI-700` (multi-planet M-dværg benchmark) | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` |
| **Verificerede Mælkevejs-ETI** | **`0`** | — | **`0` ETI** |

---

## 4. Kalibrering (`1.200` Injektioner) & Bayesianske Grænser

| Kanal & Niveau | Forsøg | Genfundet | Fuldstændighed |
| --- | --- | --- | --- |
| **Kanal A (`Arnold` asymmetrisk transit `0,2% / 0,5% / 1,0% / 2,5%`)** | `400` | `0 / 1 / 59 / 84` (pr. `100`) | **`48,0 %`** ($\ge 0{,}5\,\%$) |
| **Kanal B (`Koherent optisk laser 200 / 500 / 1000 / 2500 ppm`)** | `400` | `0 / 92 / 99 / 100` (pr. `100`) | **`97,0 %`** ($\ge 500\text{ ppm}$) |
| **Kanal C (`Symmetrisk lysssejl 0,5% / 1,0% / 2,5% / 5,0%`)** | `400` | `0 / 19 / 75 / 78` (pr. `100`) | **`57,33 %`** ($\ge 1{,}0\,\%$) |
| **Samlet over tærsklen ($\ge 1\times\text{Gate}$)** | **`900`** (af `1.200`) | **`607`** | **`67,44 %`** |

Bayesianske 95 % øvre prævalensgrænser over rene Mælkevejsstjerner (`0` ETI):
- **Alle prioriterede Mælkevejsstjerner (`n = 555` raw):** Jeffreys **$0{,}3453\,\%$** · Uniform $0{,}5374\,\%$ · Clopper-Pearson $0{,}5383\,\%$.
- **Alle prioriterede Mælkevejsstjerner ($N_{\mathrm{eff}} = 374{,}29$ eff.):** Jeffreys **$0{,}5115\,\%$** · Uniform $0{,}7951\,\%$ · Clopper-Pearson $0{,}7972\,\%$.
- **Exoplanet-værter (`n = 296`):** Jeffreys **$0{,}6462\,\%$** · **`< 10 pc` (`n = 224`):** **$0{,}8529\,\%$** · **`ETZ` (`n = 136`):** **$1{,}3998\,\%$** · **`Ellipsoid` (`n = 31`):** **$5{,}9608\,\%$**.

---

## 5. Visuelle Figurer (`6/6` Verificeret i `VISUAL_REVIEW_N7.json`)

1. `figN7_01_milky_way_tess_sky_and_distance.png` — All-sky kort og afstandshistogram over de `558` Mælkevejsstjerner (`1,3–755 pc`).
2. `figN7_02_megastructure_dip_and_asymmetry_plane.png` — Kanal A transitdybde mod SNR samt ind-/udtrædelsesasymmetri mod `CROWDSAP`.
3. `figN7_03_coherent_optical_beacon_fft_and_flashes.png` — Kanal B smalbånds Fourier-spektrum (`2–300 c/d`) og Kanal C anti-FRED glimt-veto.
4. `figN7_04_tess_lightcurve_gallery_and_veto_funnel.png` — Ægte `TESS` lyskurver (`HD 145718`, `HD 209458 b`, fasefoldet `LAWD 96`) samt samlet veto-tragt (`565 -> 558 -> 123 -> 0 ETI`).
5. `figN7_05_injection_recovery_and_bayesian_f95.png` — `1.200`-forsøgs injektionskurver og Bayesianske 95 % øvre grænser.
6. `figN7_06_milky_way_unified_seti_landscape.png` — Ren Mælkevejs-syntese tværs over `2` minutter (`Spor N7`) til `73` år (`Spor N1C` `VASCO`).

---

## 6. Audit & Reproducerbarhed

- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n7_tess_milky_way.py`):** **`N7_TESS_MILKY_WAY_AUDIT: 12/12 PASSED`** (`external_contacts == 0`).
- **Lokal arkivpakke:** `archives_n7/SETI_N7_TESS_MILKY_WAY_MEGASTRUCTURES_2026-11-27.zip`.
- **Synkroniserede rapportkopier:** `RESULTS_REPORT.md` (workspace & `progress/2026-11-27-n7-tess-milky-way-megastructures/`), `setisearch/docs/N7_TESS_MILKY_WAY_MEGASTRUCTURES_REPORT.md` og `reports/N7_TESS_MILKY_WAY_MEGASTRUCTURES_REPORT.md`.
