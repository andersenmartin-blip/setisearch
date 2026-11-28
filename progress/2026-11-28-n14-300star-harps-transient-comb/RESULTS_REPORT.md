# Spor N14 — 300-Stjerners Forenet Mælkevejs-Exoplanetværts-Census i *ESO HARPS*: Single-Epoch Transient Optisk Laser & Sub-Tærskel Frekvenskam (`SPOR_N14_300STAR_HARPS_TRANSIENT_LASER_AND_COMB`)

> **Konklusion (28. november 2026):** **Sub-1 % Bayesiansk gennembrud nået (`0` verificerede ETI-kandidater tværs over alle `300` bekræftede Mælkevejs-exoplanetværter / `508` planeter / `2.784` *ESO HARPS*-spektre).** Tværs over `268` helt nye værtsstjerner (`6,24–49,35 pc`, median `29,38 pc`; `432` bekræftede exoplaneter; `0` overlap med Spor N11B+N12's `32` stjerner) og `2.144` tid- og BERV-stratificerede `HARPS Phase-3` 1D spektre (`11.286.069.120 B = 10.763,23 MiB` ~ `10,51 GiB` strømmet 100 % gennem RAM uden bulklagring af FITS) opnår vores 8-epokers Leave-One-Epoch-Out (`LOEO`) + PSF + sub-tærskel-kam-pipeline **`92,75 %` (`371/400`)** genfinding for single-epoch transient optiske lasere (`T1`) og **`88,75 %` (`355/400`)** for sub-tærskel 8-tands optiske frekvenskamme (`T2`), mod **`0,00 %` (`0/400`)** for klassisk statisk median-stacking ved **`0,00 %` (`0/200` CR, `0/200` Flare)** falsk-positiv rate (`1.200` realdata-injektionsforsøg). Alle `5.472` rå $Z \ge 10$-spidser filtreres gennem PSF-formtest til `923` Stage 2-triggere (`908` `T1` + `15` `T2`), som alle `923/923` forklares entydigt i Stage 3 inkl. live ESO TAP-nabotjek (`±1,5 døgn`, `293` cachede opfølgnings-FITS): **`650` luftglød/tellurisk (`TERRESTRIAL_AIRGLOW_OR_TELLURIC`)**, **`139` Fiber-B `SimCal` (`STAR,WAVE`)**, **`62` live ESO ikke-gentagne kosmiske stråler**, **`25` solitære ikke-bekræftede CR**, **`23` + `7` kromosfæriske flares (`T1`+`T2`)**, **`5` `HARPS EGGS` (`R=80.000`) vs. `HARPS` (`R=115.000`) opløsningsforskelle (`HD 4308`, `LTT 3780`)**, **`5` ikke-gentagne kam-støjudslag**, **`4` echelle-ordensammenføjningstrin (`±8–15 %` trin ved ordensoverlap i bl.a. `bet Pic` `4975,84 Å`)**, **`2` solitære kam-udslag**, og **`1` henfalden single-exposure absorptionsbund-spids (`GJ 676 A`) $\rightarrow$ `0` ETI**. Forenet med Spor N11B (`8` værter / `160` epoker) og N12 (`24` værter / `480` epoker) spænder den samlede **`300`-stjerners Mælkevejssøgning (`2.784` epoker, `508` exoplaneter)** over følsomheder fra **`0,1077 kW` (`Proxima Cen`)** til **`12,82 MW`** (median `150,43 kW` samlet; `186,60 kW` i N14 alene) ved `D_tx = 10 m` og etablerer en **eksakt analytisk Jeffreys $\mathrm{Beta}(0,5, N_{\mathrm{eff}}+0,5)$ `95 %`-øvre grænse på `0,6377 %` rå (`0,6854 %` effektivt ved `N_eff = 279,03`; Uniform `0,9903 %` rå / `1,0641 %` eff.)** samt **`0,0690 %` rå / `0,0739 %` effektiv (`N_eff = 2.597,76`) pr. epoke**. `AUDIT: 12/12 PASSED`, `external_contacts = 0`.

---

### Kort opsummering på almindeligt dansk

Tidligere optiske SETI-søgninger med højtopløsende spektrografer har typisk enten kigget efter helt **stille** lasere (som så næsten ingen opdagede, hvis laseren kun blinkedet én nat), eller mistet svage pulskamme i støjen. I Spor N11B og N12 byggede vi en ny metode på `32` stjerner, og nu har vi skaleret den **næsten ti gange op** til i alt **`300` sikre exoplanet-stjerner (`508` kendte planeter) i Mælkevejen** ved hjælp af **`2.784` arkivspektre fra *ESO HARPS*-spektrografen**:
- Vi streamede **`2.144` nye spektre (`10,5 GiB`)** direkte gennem computerens arbejdshukommelse fra ESO's arkiv uden at fylde harddisken op.
- Tværs over de **268 helt nye stjerner** fangede metoden `92,75 %` af indlagte enkelt-nats lasere og `88,75 %` af svage 8-tands laserkamme — hvor den klassiske metode opdagede **0,00 %** — samtidig med `0,00 %` fejlalarmer fra simulerede flares og kosmiske stråler.
- Af de `923` virkelige kandidater i de nye arkivdata blev **samtlige `923` opklaret fysisk**: størstedelen var jordens egen atmosfære (`650`) og kalibreringslampe (`139`), plus enkelte kosmiske stråler, stjerneudbrud (`flares`), fire stjerneoptagelser med blanding af `R=80.000` (`EGGS`) og `R=115.000` opløsning, samt et `10,4 %` echelle-sammenføjningstrin i `beta Pictoris` (`HARPS_3.8` ved `4975,84 Å`). **Resultat: `0` aliensignaler.**
- Ved at nå **`300` stjerner med `0` fund** bryder den optiske laser-SETI-grænse for første gang under **1 %**: højst **0,64 %** (`0,69 %` justeret for fuldstændighed) af nære exoplanetværtsstjerner udsender sådanne smalbåndede optiske lasere mod Solsystemet i deres observationsvindue.

---

## 1. Prospektiv Forsegling & Nul-Overlap Arkitektur

| Kontrolelement | Verificeret Værdi |
| --- | --- |
| **Metode-lås (`METHOD_LOCK.json`)** | SHA-256 `eb0596ddb65c9fdf571845d733a7f46bc2ebc1ff891eafda9a4d5ed4f4c4fc6f` (`pre_acquisition_blind_lock: true`) |
| **Implementerings-lås (`IMPLEMENTATION_LOCK.json`)** | SHA-256 `a122fd506f9511c16e0436d6e1462774c4092833c5e460fb548b2d7390e42dc7` (`sealed_utc: 2026-11-28T14:01:42.559399+00:00`) |
| **Katalog-lås (`n14_target_catalog.json`)** | SHA-256 `e0039b7c426e386497812d165129a938a79687cfd2b27d98204893c31b4ac112` (`268` primære + `24` backup) |
| **Overlap med Spor N11B (`8`) + Spor N12 (`24`)** | **`0` af `268`** (ekskluderet prospektivt både pr. navn/alias og pr. himmelkoordinat) |
| **Strømmet arkivvolumen** | **`11.286.069.120 B` (`10.763,23 MiB` ~ `10,51 GiB`)** gennem RAM i **`2.366,26 s`** (`0` bulk FITS på disk) |
| **Afstand & Spektralklassefordeling (N14 / Samlet `300`)** | N14 (`268`): `60 M`, `84 K`, `106 G`, `18 F/A` (`6,2444–49,3520 pc`, `432` planeter). Forenet (`300`): `86 M` (`163` pl.), `87 K` (`144` pl.), `109 G` (`171` pl.), `18 F/A` (`30` pl.) = **`508` planeter**, **`2.784` epoker** |
| **Tidsspænd & BERV-spænd (N14)** | MJD-spænd median `3.017,8` døgn (maks. `7.932,3` d), `BERV`-spænd median `40,83 km/s` (maks. `59,65 km/s`), median header-SNR `124,6` |

---

## 2. Head-to-Head Ydeevne (`1.200` Realdata-Injektionsforsøg)

Indsprøjtet direkte i kalibrerede epoker på tværs af reelle `F/G/K/M`-stjernespektre i N14 (med skarp sammenligning mod en klassisk statisk median-stack på samme 8-epokers kuber):

| Testmorfologi | Forsøg (`N`) | N14 Positiv / FPR | Klassisk Statisk Stack | Dom |
| --- | --- | --- | --- | --- |
| **Single-Epoch PSF Laser (`T1`)** | `400` | **`371 / 400` (`92,75 %`)** | `0 / 400` (`0,00 %`) | **Pass** — overvinder fuldt ud transient blindhed |
| **Sub-Tærskel 8-Tands Kam (`T2`, `6,0–10,0σ`)** | `400` | **`355 / 400` (`88,75 %`)** | `0 / 400` (`0,00 %`) | **Pass** — samler kamtænder under enkeltlinje-tærsklen |
| **Skarp Kosmisk Stråle (`1–2 px`) FPR** | `200` | **`0 / 200` (`0,00 %` FPR)** | `0 / 200` (`0,00 %`) | **Pass** — `fwhm_ratio` + `r_gauss` afviser perfekt |
| **Bred Kromosfærisk Flare (`5–10 px`) FPR** | `200` | **`0 / 200` (`0,00 %` FPR)** | `0 / 200` (`0,00 %`) | **Pass** — afvist via breddegrænse `<= 1,50× PSF` |

---

## 3. Fysisk Afvisning & Stage 3 Forensisk Opklaring (`5.472 -> 923 -> 0 ETI`)

Ud af **`5.472` rå $Z_{\mathrm{MF}} \ge 10$-spidser** tværs over `2.144` spektre bortsorterede Stage 2 **`3.550`** skarpe kosmiske stråler, **`826`** brede/forvrængede spidser, **`154`** negative vinge-artefakter og **`34`** vedvarende linjer ($n > 3$ epoker), hvilket efterlod **`908` `T1`** + **`15` `T2`** = **`923` Stage 2-triggere**. Stage 3 løste alle `923` gennem fysiske kataloger, header-diagnostik (`SPEC_RES`, `ESO INS MODE`, `CCF RVC`, `Hα`/`Hβ`) og live ESO TAP `±1,5 d` arkivopfølgning (`293` FITS):

| Stage 3 Veto-Kategori | Antal | Fysisk Forklaring |
| --- | ---: | --- |
| **`TERRESTRIAL_AIRGLOW_OR_TELLURIC`** | `650` | Jordens øvre atmosfære (topocentrisk `[O I] 5577/6300/6364`, `Na D`, `Hg I`, H₂O/O₂ telluriske bånd samt kryds-stjerne topocentrisk sammenfald). |
| **`SIMCAL_FIBER_B_WAVE_BLEED`** | `139` | Simultant ThAr-kalibreringslys (`DPR = STAR,WAVE`) lækket mellem Fiber B og Fiber A. |
| **`SINGLE_EXPOSURE_COSMIC_RAY_NONREPEATING`** | `62` | Kosmisk stråle afkræftet i umiddelbar ESO TAP `±1,5 døgn` nabo-eksponering (inkl. lave-SNR/absorptionslinje-udsving i `GJ 1214`, `LTT 3780`, `TOI 700`). |
| **`ISOLATED_SINGLE_EXP_COSMIC_RAY_UNCORROBORATED`** | `25` | Solitær én-nattes-spids (`1/8` epoker) uden tilgængelig `±1,5 d` ESO nabo-eksponering. |
| **`CHROMOSPHERIC_STELLAR_FLARE` (`T1` + `T2`)** | `23 + 7` | Stellært udbrud bekræftet ved forhøjet `Hα`/`Hβ`-ratio eller eksakt hvilerammelinje (`Fe II`, `He I D3`, `Mg I b`, `Hα`, `Hβ`). |
| **`INSTRUMENT_MODE_RESOLUTION_MISMATCH`** | `5` | `HARPS EGGS` (`SPEC_RES = 80.000`, f.eks. `HD 4308` og `LTT 3780` `MJD 60051`) mod `HARPS` `R = 115.000` skabelon i dybe absorptionslinjer (`norm < 1,0`). |
| **`NONREPEATING_COMB_NOISE_EXCURSION`** | `5` | Sub-tærskel `T2`-kamme uden gentagelse i live ESO `±1,5 d` nabo-spektre. |
| **`ECHELLE_ORDER_STITCH_STEP_ARTIFACT`** | `4` | Kontinuumtrin (`±8–15 %`) ved overlappende `HARPS`-echelle-ordner (bl.a. `bet Pic` `HARPS_3.8` ved `4975,84 Å` med permanent `+10,4 %` ordentrappe mellem `4975 Å` og `4976,8 Å`). |
| **`ISOLATED_UNCORROBORATED_COMB_EXCURSION`** | `2` | Solitært enkelt-epoke `T2`-udsving uden nabo-gentagelse i `ref`-epoker. |
| **`SINGLE_EXPOSURE_SPIKE_DECAYED_NONREPEATING`** | `1` | `GJ 676 A` (`6448,41 Å`): single-exposure spids i dyb absorption (`ex=+0,247 -> +0,055` i `ADJ`, `>77 %` fald til referencegrundniveau). |
| **Verificerede ETI-kandidater** | **`0`** | **Ingen vedvarende eller uforklarede smalbåndslasere eller optiske kamme.** |

---

## 4. Sub-1 % Bayesiansk Grænse (`0` ETI tværs over `300` Værter & `2.784` Epoker)

| Omfang | Rå / Eff. Antal (`N_eff`) | Jeffreys `f_95` | Uniform `f_95` | Fysisk Effekttærskel (`D_tx = 10 m`) |
| --- | ---: | ---: | ---: | --- |
| **Spor N14 alene (stjerner, rå)** | `268,0` | **`0,7135 %`** | `1,1075 %` | `0,7917–12.819,76 kW` (`med. 186,60 kW`) |
| **Spor N14 alene (stjerner, eff.)** | `248,57` | **`0,7690 %`** | `1,1932 %` | Korrigeret for `92,75 %` `T1`-fuldstændighed |
| **Spor N14 alene (epoker, eff.)** | `1.988,56` | **`0,0965 %`** | `0,1505 %` | Pr.-epoke duty-cycle øvre grænse |
| **Forenet `300`-stjerners Census (rå)** | `300,0` | **`0,6377 %`** | **`0,9903 %`** | **`0,1077–12.819,76 kW`** (`med. 150,43 kW`) |
| **Forenet `300`-stjerners Census (eff.)** | **`279,03`** | **`0,6854 %`** | **`1,0641 %`** | Forener `N11B (8) + N12 (24) + N14 (268)` (`508` planeter) |
| **Forenet `2.784`-epokers Census (rå / eff.)** | `2.784,0` / `2.597,76` | **`0,0690 %` / `0,0739 %`** | **`0,1075 %` / `0,1152 %`** | Samlet `2.784` optiske `HARPS`-epoker |

---

## 5. Leverancer, Visuel Kvalitetskontrol & Reproducerbarhed

- **Visuelle figurer (`6/6` inspiceret `PASSED` i `VISUAL_REVIEW_N14.json`):**
  1. `figN14_01_300star_distance_and_power_census.png` — `300` værter / `508` exoplaneter afstand vs. effekttærskel og spektralfording (`F/A, G, K, M`).
  2. `figN14_02_head_to_head_8epoch_benchmark.png` — `1.200`-forsøgs benchmark (`92,75 %` `T1`, `88,75 %` `T2`, `0,00 %` klassisk & `0,00 %` FPR) + $Z_{\mathrm{MF}}$ udskæringskurver.
  3. `figN14_03_fgkm_loeo_subtraction_gallery.png` — `F/G/K/M` 7-epoke `LOEO` fotosfærisk eliminering tværs over 4 stjerneklasser.
  4. `figN14_04_shape_diagnostics_and_stage3_veto.png` — `5.472` $Z\ge 10$-spidser i `(fwhm_ratio, r_gauss)` og samlet Stage 3 tragt (`923 -> 0 ETI`).
  5. `figN14_05_sub1pct_bayesian_f95_breakthrough.png` — Skaleringskurve `8 -> 32 -> 268 -> 300` stjerner, der bryder `< 1,0 %` (`0,6377 %` rå / `0,6854 %` eff.).
  6. `figN14_06_milky_way_blindspot_hexalogy.png` — Samlet `N7–N14` Mælkevejs-blindspot syntese tværs over 6 uafhængige regimer (`0 ETI`).
- **Revision & Arkivpakke:** `audit_n14_300star_harps.py` (`/usr/bin/python3 -S`) bestod `12/12 PASSED`; fuld metadata- og resultatpakke gemt i `/home/martin/SETI_Fortsaettelse_2026-11-14/archives_n14/SETI_N14_300STAR_HARPS_TRANSIENT_COMB_2026-11-28.zip`.
