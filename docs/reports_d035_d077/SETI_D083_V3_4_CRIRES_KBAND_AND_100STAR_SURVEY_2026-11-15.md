# Videnskabelig Rapport — Fase D083 (`CRIRES_V3_4`): Termisk Nær-IR $K$-Bånd Laser-Teknosignatur-Survey (`1,95–2,48 µm`, $R = 86\,000$), `100`-Stjerners Pankromatisk `V3`-Syntese & `120`-Systems Multi-Messenger Census

**Dato:** 2026-11-15  
**Forfatter:** Martin Andersen (Cand.scient. i astrofysik, Københavns Universitet)  
**Fase / Detektor:** `D083` / `CRIRES_V3_4` (`0` DKK omkostning, `0` eksterne kontakter, kun offentlige ESO Phase-3 arkivdata med `obs_release_date <= 2026-11-15T00:00:00Z`)  
**Prospektiv lås:** `METHOD_LOCK.json` (`SHA-256 = 3a5e9332342e2fa7017afb13a9ace7d54d4ba7c5b9bc962e3c6326f99c781af8`), låst `2026-11-15T17:26:42.041583+00:00` **før** første FITS-download (`2026-11-15T17:26:44.542737+00:00`)  
**Uafhængig ren-stdlib audit:** `/usr/bin/python3 -S audit.py` — **`PASS` (`11/11` kontroller, `0` fejl)**

---

## 1. Videnskabelig motivation og arkitektonisk nyhed i `D083`

Med faserne `D079–D082` etablerede projektet et prospektivt låst pankromatisk echelle-lasersøgesystem (`V3.0–V3.3`) fra `0,38 µm` til `1,80 µm` på tværs af `80` unikke stjerner (`501` eksponeringer fra `HARPS`, `ESPRESSO` og `NIRPS_HE`). Den væsentligste uafdækkede spektralregion for interstellare kontinuert-bølge (CW) laserfyrtårne var det **termiske nær-infrarøde $K$-bånd (`1,95–2,48 µm`)**, hvor:

1. **Industrielle højeffekts $2\,\mu\text{m}$ faststof- og fiberlasere** — specifikt **Thulium-doterede silica-fiberlasere ved `2040,0 nm` (`20400,0 Å` vakuum)** og **Holmium:YAG-lasere ved `2097,0 nm` (`20970,0 Å` vakuum)** — kombinerer høj elektro-optisk virkningsgrad, diffrakteret strålekvalitet og lav interstellart støveksstinktion ($A_K \approx 0{,}11\,A_V$) med de højtransmissive atmosfæriske vinduer på Cerro Paranal.
2. **ESO VLT UT3 `CRIRES+`** med den smalle `w_0.2`-spalte leverer en spektral opløsningsevne på **$R = \lambda / \Delta\lambda = 86\,000$** ($\text{FWHM} = 3{,}49\text{ km s}^{-1}$) hen over en mosaik af **tre `2048 × 2048` Teledyne Hawaii-2RG (H2RG) HgCdTe-detektorer** (`DET1`, `DET2`, `DET3`) pr. echelle-orden i ABBA-spaltenodding.

`CRIRES_V3_4` indfører fem dedikerede metodiske nyskabelser for $K$-båndet:
- **Empirisk Cerro Paranal $R = 86\,000$ tellurisk dekomposition (`Gate G2_V34`):** Isolerer dybe $\text{CO}_2$-bånd ved `1,96–2,08 µm` og $\text{CH}_4/\text{H}_2\text{O}$-absorption over `2,36 µm` via luftmasse-skaleret zenittransmission samt præ-/post-tellurisk fluxforhold.
- **5-nærmeste-nabo (`kNN`) spektralskabelon på tværs af 4 `CRIRES+` gitterindstillinger (`K2148`, `K2166`, `K2192`, `K2217`) + optisk-dybde-skalering $\gamma$** samt empirisk stellar radialhastighedsforankring på `12` vakuum-atomlinjer (`Na I`, `Ca I`, `Al I`, `Mg I`, `Ti I`, `Si I`; `1.776` fits i alt).
- **4-kanals søgearkitektur (`T`, `P`, `T_DIFF`, `K_PLANET`):** Ud over enkelt-epoke transiente (`T`) og flerspektrede stellare hvilesystem-stakke (`P`) udføres eksplicit **Kepleriansk planet-hvilesystem de-Doppler-stakning (`K_PLANET`)** på `7` multi-epoke kampagner (`66` eksponeringer), bl.a. ultra-kortperiode klippeplaneten `LHS 3844 b` ($\Delta v_{\text{orb}} = 229{,}65\text{ km s}^{-1}$), `Ross 128 b` (`3,375 pc`), `GJ 3323 b` (`5,375 pc`), `LTT 1445 A c` (`6,864 pc`), `AU Mic b` (`9,714 pc`) og `K2-33 b`.
- **3-detektor Hawaii-2RG spalte-LSF fysik-gate (`Gate G5_V34`):** Evaluerer kandidatprofilen direkte på de rå 1D-ekstraherede orden-detektor-tabeller (`01_INTENS..08_INTENS` for nod-positioner `A` og `B`), tester AB-spaltenodding-asymmetri (mod negative spøgelseslinjer fra himmel-/OH-subtraktion), inter-pixel kapacitans (`IPC`) enkeltpixel-spidser og H2RG-persistensplateauer.
- **Direkte 2MASS $K_s$-forankret Cohen et al. (2003) radiometri (`2,159 µm`, $F_{\lambda,0} = 4{,}283\times 10^{-11}\text{ erg cm}^{-2}\text{ s}^{-1}\text{ Å}^{-1}$):** Eliminerer systematisk bolometrisk ekstrapolation fra optisk $G$-fotometri for sene M-dværge over `5–8` størrelsesklasser.

---

## 2. Prospektivt låst kohorte (`22` stjerner, `148` VLT `CRIRES+` eksponeringer, `87,32 t`)

Alle `148` ESO Phase-3 `CRIRES+` spektralprodukter (`261,61 MiB`, `0` overlap med de `873` tidligere ekskluderede `dp_id`'er fra `D077–D082`) blev låst i `FROZEN_COHORT_D083.csv` før download:
- **`4` nul-planet kontrolstjerner (`26` eksponeringer):** `GJ 588` (`5,92 pc`, M2.5V tidsseriekontrol med `12` epoker), `HD 131156 A` ($\xi$ Boo A, `6,75 pc`, `6` epoker), `HD 22879` (`26,09 pc`, `4` epoker) og `HD 49933` (`29,82 pc`, `4` epoker).
- **`18` videnskabelige mål (`122` eksponeringer):**
  - **`20` helt nye unikke stjerner** (mindste vinkelafstand til alle `115` tidligere koordinater i `D077–D082` og `M5–M36`/`TESS`: **`7.890,9"` (`2,19°`)**, langt over grænsen på `120"`), hvilket løfter det samlede `V3`-survey præcis fra `80` til **`100` unikke echelle-stjernesystemer**.
  - **`2` planlagte `< 10 pc` pankromatiske brostjerner:** `HD 42581` (`GJ 229 A`, `5,761 pc`, M1V med `HARPS` i `D081` + `CRIRES+` i `D083`) og `AU Mic` (`9,714 pc`, ung M1V med `4` planeter, `NIRPS_HE` i `D082` + `CRIRES+` i `D083`), som sammen med `Proxima Centauri` og `Barnard's Star` danner en `4`-stjerners `0,38–2,48 µm` pankromatisk bro (`71` bølgelængdeceller).
  - **`8` stjerner inden for `10 pc` i `D083`**, hvilket udvider solnabolags-censussen ($d < 10\text{ pc}$) til **`35` unikke stjerner**.
- **Samlet eksponeringstid og søgerum i `D083`:** `314.360,0 s` (**`87,3222 timer`**) og **`7.779.376` gennemsøgte 1D-spektralbins** (`5.939.825` i Kanal `T`, `1.156.188` i Kanal `P`, `333.717` i Kanal `T_DIFF` og `349.646` i Kanal `K_PLANET`).
- **Barycentrisk & stellar RV-præcision:** Uafhængig ren-stdlib Cerro Paranal BERV-verifikation bekræfter `max |ΔBERV| = 0,0602 km/s` (`<= 0,08 km/s` krav) over alle `148` eksponeringer, og `905` rene atomare absorptionsfits giver median $|\text{RV}_{\text{emp}} - \text{RV}_{\text{prior}}| = 0{,}2785\text{ km s}^{-1}$.

---

## 3. Syntetisk kalibrering på kontrolstjerner (`1.971` prospektive injektionsforsøg)

Ingen tærskler blev justeret efter eksponering mod science-spektre. Alle detektions- og afvisningsrater blev målt på de `4` kontrolstjerner over `9` $K$-båndsvinduer (`1976,4–2458,0 nm`):

| Kalibreringssuite | Antal forsøg | Nøglemetrik | Målt værdi |
|---|---:|---|---:|
| **Kanal `T` (enkelt-epoke CW-puls)** | `1.080` | Samlet genfindingsgrad ved `>= 8σ` (`9` bånd) | **`78,86 %`** |
| — heraf **`2040,0 nm` Tm-fiberlaser** | `120` | Genfindingsgrad ved `>= 8σ` (`8σ / 12σ / 20σ`) | **`83,33 %`** (`62,5 % / 87,5 % / 100 %`) |
| — heraf **`2097,0 nm` Ho:YAG-laser** | `120` | Genfindingsgrad ved `>= 8σ` (`8σ / 12σ / 20σ`) | **`94,44 %`** (`83,3 % / 100 % / 100 %`) |
| **Kanal `P` (5-epokers hvilesystem-stak)** | `540` | Samlet genfindingsgrad ved `>= 9σ` / `>= 12σ` | **`82,10 %` / `88,89 %`** (`100 %` ved `12σ` for både `2040 nm` & `2097 nm`) |
| **Kepleriansk banespor på `GJ 588`** ($\Delta v_{\text{orb}} = 224{,}4\text{ km/s}$) | `135` par | Ukompenseret `T_DIFF` ($\alpha = 0$) vs. de-Doppler `K_PLANET` ($\alpha = 1$) ved `>= 6,5σ_exp` | **`0,00 %` → `53,09 %`** (`70,37 %` ved `14σ_exp`) |
| **3-H2RG detektor-fysik (`Gate G5_V34`)** | `216` | Ægte `w_0.2` spaltelaser pass-rate / IPC hot-pixel afvisning / persistens-afvisning | **`98,61 %` (`71/72`) / `100,00 %` (`72/72`) / `100,00 %` (`72/72`)** |

---

## 4. 4-generations kaskade og forensisk diagnose (`0` verificerede ETI-signaler)

På tværs af alle `148` `CRIRES+` eksponeringer reducerer den prospektivt låste kaskade falske alarmer dramatisk:

| Trin i kaskaden | Kontrol (`4` stjerner, `26` eksp.) | Science (`18` stjerner, `122` eksp.) | Total (`148` eksp.) |
|---|---:|---:|---:|
| **Legacy `V2` (rå flux-spidsdetektor)** | `188` | `855` | **`1.043`** |
| **`V3.1` præ-`F1` kNN-skabelon `G1`** | `44` | `213` | **`257`** |
| **`CRIRES_V3_4` 4-kanals `G1` (`F1`-ankret)** | `48` | `207` | **`255`** |
| **Efter `Gate G2_V34` (Paranal tellurisk & OH-katalog)** | `16` | `55` | **`71`** |
| **Efter `Gate G3_V34` (nativ orden/detektor & kryds-stjerne ryg)** | `2` | `19` | **`21`** |
| **Efter `Gate G4_V34` (H2RG ordenrand & AB-nod spøgelse)** | `2` | `19` | **`21`** |
| **Efter `Gate G5_V34` — Orbitale kanaler (`T_DIFF` + `K_PLANET`, `66` eksp.)** | **`0`** | **`0`** | **`0`** |
| **Efter `Gate G5_V34` — Automatisk Kanal `T`/`P` overlevere** | `1` (`GJ 588`) | `16` | **`17`** |
| **Verificerede ETI-laserdetektioner (efter forensisk FITS-kontrol)** | **`0`** | **`0`** | **`0`** |

Alle `21` post-`G3_V34` kandidater (`4` afvist automatisk af `G5_V34` + `17` automatiske Kanal `T`/`P` overlevere; `0` i `T_DIFF` og `0` i `K_PLANET`) er fuldt dokumenteret på pixel- og topocentrisk bølgelængdeniveau i `results/FORENSIC_KBAND_CASCADE_DIAGNOSIS_21.json`:
1. **`15 af 17` overlevere (inkl. den enlige kontrolkandidat `V34-T-0009` på `GJ 588` ved `22904,76 Å` topocentrisk)** falder på nøjagtigt stationære **topocentriske vakuumbølgelængder og faste `(wlen_id, ORDER, DETEC, XPOS)` H2RG-koordinater**, som genfindes inden for `±1 pixel` hos `2–13` urelaterede stjerner med vidt forskellige radialhastigheder — nemlig svage høj-$J$ natlige **OH Meinel `(8-6)`, `(9-7)` og `(10-8)` $\Lambda$-dubletter** (Rousselot et al. 2000; Oliva et al. 2015; fx den klassiske `1,00 Å`-separerede `OH (9-7) P2(3.5)` dublet ved `21759,25 Å` og `21760,25 Å` på `WASP-189`) eller svage H2RG flatfield-pixelrester.
2. **`1 af 17` (`V34-T-0128` på $\beta$ Pictoris, `21654,93 Å` hvilebølgelængde)** ligger ved `Δv = -86,8 km s⁻¹` i blåfløjen af **$\text{H I}$ Brackett-$\gamma$ (`21661,20 Å` vakuum)** — velkendt cirkumstellar gas- og eksokomet-absorptionsvariabilitet i $\beta$ Pictoris' kantstillede skive relativt til `WASP-189`/`HD 141569`-skabelonen.
3. **`1 af 17` (`V34-T-0196` på `PDS 70`, `22687,89 Å` topocentrisk)** er en monotont faldende kontinuumskulder (`1,105 → 0,971`) umiddelbart ved kanten af en dyb `22688,0 Å` tellurisk linje uden lokal emissionsspids.

Dermed er antallet af verificerede ekstraterrestriske laserdetektioner eksakt **`0`**, og diagnosen definerer direkte næste generations opgradering (`V3.5`): automatisk kryds-stjerne topocentrisk `(wlen_id, ORDER, DETEC, XPOS)` koincidens-gating kombineret med Oliva et al. (2015) høj-$J$ OH-vakuumkataloget.

---

## 5. Direkte 2MASS $K_s$-kalibrerede $8\sigma$ CW-lasergrænser (`162` celler) & `4`-stjerners pankromatisk bro

For en antat `10 m` diffrakteret senderblænde ($G_t = (\pi D_t / \lambda)^2$) opnås skarpere termiske nær-IR øvre grænser uden én eneste `NaN`-celle (`162/162` celler verificeret med relativ afvigelse `< 10⁻⁶` i `audit.py`):

- **Skarpeste $K$-båndsgrænse i hele `D083`:** **`LHS 3844`** (`14,88 pc`, M5V, $K_s = 9{,}145$): **`1.513,2 W` (`1,51 kW`)** i enkelt-epoke ved `2183,5 nm`, **`1.557,7 W`** ved **`2097,0 nm` Ho:YAG**, **`2.380,1 W`** ved **`2040,0 nm` Tm-fiber**, og helt ned til **`653,6 W` (`0,65 kW`)** i den Kepleriansk de-Doppler-stakkede planetkanal `K_PLANET` for `LHS 3844 b`!
- **Nærmeste solnabolags-exoplanetværter ($d < 10\text{ pc}$) i $K$-båndet:**
  - **`Ross 128`** (`3,375 pc`): **`2,92 kW`** bedst (`3,78 kW` ved `2097 nm` Ho:YAG; `5,79 kW` ved `2040 nm` Tm-fiber).
  - **`GJ 3323`** (`5,375 pc`): **`3,76 kW`** enkelt-epoke (`2,55 kW` i `T_DIFF` og `2,80 kW` i `K_PLANET`).
  - **`LTT 1445 A`** (`6,864 pc`): **`4,69 kW`** enkelt-epoke (`3,83 kW` i `K_PLANET`).
  - **`YZ CMi` (`GJ 285`, `5,989 pc`)**: **`8,61 kW`** (`9,80 kW` Ho:YAG; `12,48 kW` Tm-fiber).
- **Fuldt udbygget `4`-stjerners `0,38–2,48 µm` pankromatisk bro (`71` bølgelængdeceller):**
  - **`Proxima Centauri` (`1,30 pc`, `ESPRESSO + NIRPS`):** **`9,0 W`** optisk (`467,6 nm`) → **`607,7 W`** (`1064,1 nm` Nd:YAG) → **`1.026,1 W`** (`1550,0 nm` Er C-bånd).
  - **`Barnard's Star` (`1,83 pc`, `ESPRESSO + NIRPS`):** **`23,6 W`** optisk (`467,6 nm`) → **`1.433,0 W`** (`1096,5 nm`) → **`2.016,0 W`** (`1550,0 nm`).
  - **`GJ 229 A` (`HD 42581`, `5,76 pc`, `HARPS + CRIRES+ K`):** **`720,4 W`** optisk (`467,6 nm`) → **`16,64 kW`** i $K$-båndet (`2114,5 nm`; `20,08 kW` Ho:YAG; `40,12 kW` Tm-fiber).
  - **`AU Mic` (`9,71 pc`, `NIRPS + CRIRES+ K`):** **`38,13 kW`** nær-IR (`1096,5 nm`) → **`52,30 kW`** i $K$-båndet (`2183,5 nm`; `67,60 kW` Ho:YAG; `104,86 kW` Tm-fiber).

---

## 6. Samlet `100`-Stjerners Pankromatisk `V3`-Syntese (`D079–D083`) & `120`-Systems Multi-Messenger Census

Med afslutningen af `D083` udgør projektets optiske/nær-IR spor og radiosporet ét samlet, fuldt reproducerbart multi-messenger teknosignatur-atlas:

1. **`100` unikke echelle-stjernesystemer (`0,378–2,480 µm`, `D079–D083`):**
   - **`649` højopløste echelle-eksponeringer** (`220` `HARPS` + `129` `ESPRESSO` + `152` `NIRPS_HE` + `148` `CRIRES+`), **`154,11 timers` åben-lukker integrationstid** og **`148,50 millioner` gennemsøgte 1D-spektralbins**.
   - **`35` unikke solnabolagsstjerner inden for `10 pc`** (`29` fra `D079–D082` + `6` nye `< 10 pc` stjerner i `D083`, heraf `2` brostjerner).
   - **`8.541` prospektive syntetiske kalibreringsforsøg** og kollaps af **`6.893` Legacy `V2` falske alarmer** til **`0` verificerede ETI-laserdetektioner**.
2. **`120` distinkte stjernesystemer på tværs af tre uafhængige SETI-modaliteter:**
   - `100` pankromatiske echelle-stjerner (`0,38–2,48 µm`) + `23` exoplanet-systemer gennemsøgt for planet-hvilesystem smalbånds-radiosignaler ved `1,4 GHz` med **Parkes `64 m` UWL og Green Bank Telescope (`100 m`)** (`M5–M36`, hvor `M35` sætter en eksakt `95 %` øvre populationsgrænse på `33,16 %` ved `SNR = 40` over `20` uafhængige systemer) + `1` fotometrisk `TESS` spekulær lyssejl-kandidatvært (`L 98-59`, `LS7`).
   - **`4` direkte multi-messenger overlap-systemer** undersøgt i både højopløst echelle-spektroskopi og radio/lyssejl: **`Proxima Centauri`**, **`GJ 581`**, **`GJ 849`** og **`L 98-59`** (`96` kun-echelle + `20` kun-radio + `4` multi-messenger = **`120` systemer**, **`0` verificerede ETI-detektioner**).

---

## 7. Fuld leveranceliste i `D083`

- **Lås & reproducerbarhed:** `METHOD_LOCK.json`, `LOCK_RECEIPT.json`, `IMPLEMENTATION_LOCK.json`, `FROZEN_COHORT_D083.csv`, `ORBITAL_CAMPAIGNS_AND_KINEMATICS.json`, `bounded_inputs/d083_bounded_bundle.json.gz` (`23,2 MiB`), `audit.py` (`PASS 11/11`).
- **15 kvantitative CSV-tabeller + JSON-synteser i `results/`:** `EXPOSURE_PROVENANCE_148.csv`, `STELLAR_RV_ANCHORS_1776.csv`, `STAR_RV_SUMMARY_22.csv`, `INJECTION_RECOVERY_1620.csv`, `KEPLERIAN_TRACK_CALIBRATION_135.csv`, `DETECTOR_H2RG_CALIBRATION_216.csv`, `CALIBRATION_COMPLETENESS_BY_BAND.csv`, `V3_4_CANDIDATE_LEDGER.csv`, `FOUR_GEN_BENCHMARK_148.csv`, `ORBITAL_CAMPAIGN_RESULTS_7.csv`, `STAR_UPPER_LIMITS_162.csv`, `PANCHROMATIC_OPTICAL_NIR_KBAND_BRIDGE.csv`, `SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_35STARS.csv`, `UNIFIED_PANCHROMATIC_V3_SYNTHESIS_100STARS.csv`, `MULTIMESSENGER_ECHELLE_RADIO_TESS_SYNTHESIS.csv`, `FORENSIC_KBAND_CASCADE_DIAGNOSIS_21.json`, `SOURCES.json`, `SUMMARY.json`, `AUDIT_SUMMARY.json`, `VISUAL_REVIEW.json`.
- **4 publikationsfigurer (`180 DPI` PNG, visuelt godkendt):** `fig1_kband_telluric_and_tm_hoyag_completeness.png`, `fig2_keplerian_orbital_tracks_and_cascade.png`, `fig3_kband_laser_limits_and_bridge_spectra.png`, `fig4_100star_panchromatic_and_multimessenger_census.png`.
