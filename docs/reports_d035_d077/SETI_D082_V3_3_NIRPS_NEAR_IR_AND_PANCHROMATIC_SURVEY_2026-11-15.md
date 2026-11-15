# SETI Fase D082 — Prospektiv 4-Kanals Nær-Infrarød (`0.98–1.80 µm` YJH) `NIRPS_V3_3` Laser-Teknosignaturundersøgelse og Samlet 80-Stjerners Pankromatisk Syntese (`2026-11-15`)

## 1. Resumé og Hovedkonklusion

Fase **D082** gennemfører og afslutter den prospektivt låste nær-infrarøde udvidelse (**`NIRPS_V3_3`**) af det optiske echelle-SETI-program (`D079–D081`) på ESO La Silla 3.6 m **NIRPS** (`NIRPS_HE`, $R = 70{,}000$, simultan `Fiber B = SKY`, bølgelængdeområde `0.98–1.80 µm` i Y-, J- og H-båndene inkl. de klassiske teknosignaturfrekvenser ved **`1064.1 nm` Nd:YAG/Yb** og **`1550.0 nm` Er-doteret telekom C-bånd**). Undersøgelsen dækker **22 nærliggende stjernesystemer** over **152 arkiviske `NIRPS_HE`-eksponeringer** (`48,738.4 s` = `13.54` timers integrationstid, `20,223,039` undersøgte spektralbins i Kanal `T`, nul `dp_id`-overlap mod alle `716` eksponeringer i `D035–D081`):

1. **4 verificerede nul-planet `CONTROL`-stjerner (`27` eksponeringer):** `12` sammenhængende enkeltnats-eksponeringer på `HD 184509` (`G0V`, `31.20 pc`) samt `5` multi-epoke eksponeringer hver på `GJ 707` (`K7V`, `13.21 pc`), `GJ 643` (`M3.5V`, `6.50 pc`) og `GJ 3618` (`M5.5V`, `4.83 pc`).
2. **5 enkeltnats exoplanet-transitkampagner (`60` eksponeringer = `5 × 12`, `6 IN_TRANSIT + 6 OUT_OF_TRANSIT`):** `AU Mic b` (`9.72 pc`), `HD 260655 b` (`10.01 pc`), `L 98-59 c` (`10.62 pc`), `TOI-270 c` (`22.48 pc`) og `HD 18599 b` (`38.57 pc`), gennemsøgt med både ukompenseret transit-differens (**Kanal `T_DIFF`**, $\alpha = 0$) og eksakt keplersk planet-hvilesystem de-Doppler-stakning (**Kanal `K_PLANET`**, $\alpha = 1$).
3. **11 nye nærliggende exoplanet-værtsstjerner (`55` eksponeringer = `11 × 5`):** `eps Eri` (`3.20 pc`), `tau Cet` (`3.60 pc`), `Teegarden's Star` (`3.83 pc`), `GJ 9066` (`4.47 pc`), `GJ 682` (`5.01 pc`), `GJ 581` (`6.30 pc`), `GJ 514` (`7.62 pc`), `GJ 849` (`8.80 pc`), `HD 222237` (`11.45 pc`), `GJ 1132` (`12.61 pc`) og `GJ 3090` (`22.48 pc`).
4. **2 nærmeste nabostjerner (`< 2 pc`) som Pankromatisk Bro (`10` eksponeringer = `2 × 5`):** `Proxima Centauri` (`1.302 pc`) og `Barnard's Star` (`1.828 pc`), observeret uafhængigt i optisk lys på VLT `ESPRESSO` ($R = 140{,}000$, `0.38–0.78 µm`) i `D081` og nu i nær-infrarødt lys på `NIRPS_HE` ($R = 70{,}000$, `0.98–1.80 µm`). Dermed forenes `D079–D082` i en samlet pankromatisk `V3`-undersøgelse af **præcis `80` unikke stjerner (`501` echelle-eksponeringer over `0.38–1.80 µm`, heraf `29` unikke stjerner inden for `< 10.0 pc`)**.

### Hovedresultater i Fase D082

* **Prospektiv protokol og uafhængig stdlib-audit (`PASS 10/10`):** Metodologi, tærskler og kohorte (`FROZEN_COHORT_D082.csv`) blev kryptografisk forseglet i `METHOD_LOCK.json` (`sha256 = 8a7d0ab5965cbc6a...`, `locked_utc = 2026-11-15T13:28:15.888294+00:00`) strengt før første ESO-dataforespørgsel (`first_science_request_utc = 2026-11-15T13:30:25.530925+00:00`). En ren arkivformat-adapter for de `44 / 152` ESO `P3ORIG='IDP'` `*_S1D_FINAL_TRUNCATED_WAVE_A.fits`-produkter (med indlejret `FLUX_EL - FLUX_EL_SKYSUB` Fiber-B himmelvektor, uden ændring af nogen detektionstærskel eller gate-formel) er dokumenteret i `IMPLEMENTATION_LOCK.json` med bevarede præ-ingestionsfiler. `/usr/bin/python3 -S audit.py` bestod **10 ud af 10** uafhængige kontrolpunkter med `0` afvigelser.
* **Syntetisk kalibrering (`1,971` forsøg på de 4 nul-planet kontrolstjerner):**
  * **Kanal `T` (enkelt-epoke CW ved `8σ`):** `90.90%` genfindelsesgrad på tværs af alle 9 YJH-bånd (`91.67%` ved `1064.1 nm` Nd:YAG/Yb og `72.22%` ved `1550.0 nm` Er C-bånd).
  * **Kanal `P` (5-epoke persistent CW):** `83.95%` ved `9σ` og `96.76%` ved `12σ`.
  * **Kanal `K_PLANET` vs. `T_DIFF` (`135` keplerske transitspor med $\Delta v_{\text{orb}} = 19.3\text{ km s}^{-1}$):** Ved `9.0 σ_exp` stiger genfindelsesgraden fra **`0.0%` (`0/27`)** uden de-Doppler til **`74.1%` (`20/27`)** med keplersk `K_PLANET`-stakning, og ved `14.0 σ_exp` fra **`11.1%` (`3/27`)** til **`100.0%` (`27/27`)** (samlet `3.70%` $\rightarrow$ `58.02%` for `>= 6.5 σ_exp`, en **`15.7×` følsomhedsforøgelse**).
  * **Gate `G5_V33` Hawaii-2RG 2D-detektorfysik (`216` forsøg på `71 × 4084` `2DECHELLE`-ordrer):** **`100.0%` (`72/72`)** pasrate for ægte $R=70{,}000$ fiberlasere og **`100.0%` (`144/144`)** afvisning af både Hawaii-2RG inter-pixel kapacitans (`IPC`) hot-pixels (`72/72`) og persistens-/båndhoved-plateauer (`72/72`).
* **Fire-generations falsk-alarm-kollaps (`3,828` $\rightarrow$ `0` kontrol og `0` videnskabskandidater):**
  * Den historiske `Legacy V2` 1D-detektor udløste **`3,828` falske alarmer** i de nær-infrarøde spektre (`736` på de `27` kontroleksponeringer + `3,092` på de `125` videnskabseksponeringer) som følge af telluriske divisionsspidser, OH Meinel-nattehimmelemission og M-dværges FeH/CO/$\text{H}_2\text{O}$-båndhoveder.
  * `NIRPS_V3_3` reducerede alle **`4,053` `G1`-frø** (`3,675` i Kanal `T`, `378` i Kanal `P`, `0` i `T_DIFF`, `0` i `K_PLANET`) trin for trin: **`G2_V33` (`54` overlevende, `98.67%` tellurisk/OH-veto) $\rightarrow$ `G3_V33` (`6` overlevende efter kromosfærisk og kryds-stjerne molekylær-ryg-veto) $\rightarrow$ `G4_V33` (`3` overlevende efter simultan `Fiber B = SKY`- og echelle-overlap-veto) $\rightarrow$ `G5_V33` (`0` kontrol og `0` videnskabskandidater)**!
* **Sub-kilowatt nær-infrarøde lasergrænser (`8σ`, $D_{\text{tx}} = 10\text{ m}$):** Direkte to-bånds 2MASS ($J, H$) fotometrisk kalibrering over alle `162` stjerne-bånd-celler sætter `8σ` øvre grænser ned til **`607.7 W` ved `1064.1 nm` (Nd:YAG/Yb)** og **`1,026.1 W` (`1.03 kW`) ved `1550.0 nm` (Er C-bånd)** på `Proxima Centauri` (`1.302 pc`), **`1,433.0 W`** på `Barnard's Star` (`1.828 pc`), **`1,623.7 W`** på `GJ 9066` (`4.47 pc`) og **`1,749.4 W`** på `Teegarden's Star` (`3.83 pc`), med en median på **`8.29 kW`** på tværs af solnabolagets `< 10 pc` NIRPS-værtsstjerner.

---

## 2. Fire-Generations Veto-Kaskade og Forensisk Analyse (`152` `NIRPS_HE`-Eksponeringer)

| Detektortrin / Gate | Kontrol (`4` stjerner, `27` eksp.) | Videnskab (`18` værter, `125` eksp.) | Total (`22` stjerner, `152` eksp.) | Primær fysisk frasorteringsmekanisme |
| :--- | :---: | :---: | :---: | :--- |
| **`Legacy V2` (1D ukorrigeret)** | `736` | `3,092` | `3,828` | Tellurisk divisionsstøj, OH-airglow og molekylære M-dværgtoppe |
| **`V3.1` Præ-`F1` Kanal `T` `G1`** | `662` | `3,182` | `3,844` | Sub-kontinuum residualer i dybe absorptionslinjer |
| **`NIRPS_V3_3` `G1` (alle 4 kanaler)** | `685` | `3,368` | `4,053` | Supraphotosfærisk `F1` (`fn_pk3 >= 1.02`) + 1D $R=70\text{k}$ LSF-profil (`T: 3675`, `P: 378`, `T_DIFF: 0`, `K_PLANET: 0`) |
| **Efter `G2_V33` (Nær-IR atmosfære)** | `17` | `37` | `54` | HITRAN `ATM_TRANSM >= 0.78`, præ/post-tellurisk ratio `[0.72, 1.35]` og topocentrisk OH/$\text{O}_2$-veto (`3,999` afvist) |
| **Efter `G3_V33` (2D + kromosfære + ryg)** | `3` | `3` | `6` | Nativ ordens-SNR, He I `10830` / Paschen / Brackett-maske og kryds-stjerne FeH/CO/$\text{H}_2\text{O}$-ryg `<= 1` stjerne (`48` afvist) |
| **Efter `G4_V33` (Fiber B SKY + overlap)** | `2` | `1` | `3` | Simultan `Fiber B = SKY` himmelemissions-veto (`2` afvist: `GJ 3618`, `GJ 9066`) + nabooordens blaze-overlap (`1` afvist: `GJ 1132`) |
| **Efter `G5_V33` (Hawaii-2RG 2D morfologi)** | **`0`** | **`0`** | **`0`** | 11-px LSF cosinus `>= 0.92`, IPC hot-pixel ratio `<= 2.55` og fjern-vinge plateau `<= 0.35` (`3` brede vinge-plateauer afvist) |

Samtlige `6` kandidater, der nåede frem til `G4_V33`/`G5_V33`, er individuelt dokumenteret i `results/FORENSIC_NEAR_IR_CASCADE_DIAGNOSIS_6.json`:
* `V33-T-0441` (`GJ 3618`, kontrol, `12254.37 Å` topo) og `V33-T-2376` (`GJ 9066`, videnskab, `15505.35 Å` topo tæt ved `1550 nm` telekombåndet) blev fanget direkte af **`G4_V33`** som svage atmosfæriske OH/$\text{O}_2$-himmelemissionslinjer synlige i den simultane `Fiber B = SKY`-kanal.
* `V33-T-3185` (`GJ 1132`, videnskab, `12544.88 Å`) var til stede i én `71 × 4084` Hawaii-2RG echelle-orden, men manglede i den overlappende naboorden (`overlap_tested = True`) og blev afvist af **`G4_V33`** som et enkelt-ordens H2RG-detektorartefakt.
* De sidste `3` kandidater (`V33-T-3259` på `GJ 1132` samt `V33-P-3754` og `V33-P-3755` på kontrolstjernen `GJ 3618`) udviste alle bredde/vinge-plateauer (`fwhm_over_lsf = 1.30–1.39`, `g5_far_wing_ratio = 0.436–0.536 > 0.35`) og blev rent afvist af **`G5_V33`**.

---

## 3. Enkeltnats Exoplanet-Transitkampagner (`Kanal T_DIFF` & `Kanal K_PLANET`)

| Stjerne (Planet) | Rolle | Afstand (`pc`) | $P_{\text{orb}}$ (`d`) | $K_p$ (`km/s`) | $\Delta v_{\text{orb}}$ under transit (`km/s`) | Søgte bins (`T_DIFF` / `K_PLANET`) | Kvalificerede kandidater (`T_DIFF` / `K_PLANET`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`HD 184509`** *(kontrol-pseudoephemeris)* | `CONTROL` | `31.20` | `3.200` | `124.5` | `19.32` | `118,225` / `117,976` | **`0` / `0`** |
| **`AU Mic b`** | `SCIENCE` | `9.72` | `8.463` | `85.2` | `16.47` | `118,017` / `117,843` | **`0` / `0`** |
| **`HD 260655 b`** | `SCIENCE` | `10.01` | `2.770` | `109.1` | `17.65` | `118,522` / `118,327` | **`0` / `0`** |
| **`L 98-59 c`** | `SCIENCE` | `10.62` | `3.691` | `93.8` | `15.29` | `118,303` / `118,125` | **`0` / `0`** |
| **`TOI-270 c`** | `SCIENCE` | `22.48` | `5.660` | `85.6` | `11.77` | `117,676` / `117,540` | **`0` / `0`** |
| **`HD 18599 b`** | `SCIENCE` | `38.57` | `4.137` | `118.4` | `23.56` | `117,521` / `117,223` | **`0` / `0`** |

---

## 4. `< 2 pc` Pankromatisk Bro (`ESPRESSO` + `NIRPS_HE`) og De 18 `D082` Exoplanet-Værter

Kombinationen af `D081` (`ESPRESSO`, `0.38–0.78 µm`, $R=140{,}000$) og `D082` (`NIRPS_HE`, `0.98–1.80 µm`, $R=70{,}000$) leverer kontinuerlige pankromatiske `8σ` CW-lasergrænser ($D_{\text{tx}} = 10\text{ m}$) for Solens to nærmeste nabosystemer:
* **`Proxima Centauri` (`1.302 pc`, `M5.5V`, `10` eksponeringer = `5 ESPRESSO + 5 NIRPS_HE`):** **`9.03 W`** bedste optiske grænse (`467.6 nm`), **`607.7 W`** ved **`1064.1 nm` (Nd:YAG/Yb)** og **`1,026.1 W` (`1.03 kW`)** ved **`1550.0 nm` (Er C-bånd)**.
* **`Barnard's Star` (`1.828 pc`, `M4V`, `10` eksponeringer = `5 ESPRESSO + 5 NIRPS_HE`):** **`23.61 W`** bedste optiske grænse (`467.6 nm`), **`1,433.0 W`** bedste nær-IR grænse (`1096.5 nm`), **`1,569.7 W`** ved **`1064.1 nm`** og **`2,016.0 W` (`2.02 kW`)** ved **`1550.0 nm`**.

På tværs af alle `18` `D082` exoplanet-værter (`162` stjerne-bånd-celler i `results/STAR_UPPER_LIMITS_162.csv`) spænder de bedste `8σ` `10 m` nær-infrarøde sendereffektgrænser fra **`607.7 W`** (`Proxima Centauri`) til **`168.7 kW`** (`HD 18599` ved `38.57 pc`), med bemærkelsesværdigt dybe kilowatt-grænser på nærliggende M-dværge som `GJ 9066` (`1.62 kW` ved `4.47 pc`), `Teegarden's Star` (`1.75 kW` ved `3.83 pc`), `GJ 581` (`4.68 kW` ved `6.30 pc`), `GJ 682` (`4.74 kW` ved `5.01 pc`) og `GJ 1132` (`6.03 kW` ved `12.61 pc`).

---

## 5. Samlet Pankromatisk `V3`-Syntese (`D079–D082`: `80` Unikke Stjerner, `501` Eksponeringer)

| Fase | Detektor | Instrumenter | Bølgelængde (`µm`) | Stjerner (Nye) | Eksponeringer | Syntetiske Forsøg | `Legacy V2` Falske Alarmer | Kvalificerede Kontrol-Alarmer | Verificerede ETI-Detektioner |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **D079** | `OPTICAL_V3` | `HARPS` | `0.38–0.69` | `12` (`12`) | `60` | `990` | `48` | `28` *(præ-F1)* | **`0`** |
| **D080** | `OPTICAL_V3_1` | `HARPS + ESPRESSO` | `0.38–0.78` | `26` (`26`) | `130` | `1,620` | `422` | `10` *(præ-F1)* | **`0`** |
| **D081** | `OPTICAL_V3_2` | `HARPS + ESPRESSO` | `0.38–0.78` | `22` (`22`) | `159` | `1,989` | `1,552` | **`0`** | **`0`** |
| **D082** | `NIRPS_V3_3` | `NIRPS_HE` | `0.98–1.80` | `22` (`20` + `2` bro) | `152` | `1,971` | `3,828` | **`0`** | **`0`** |
| **Total (`V3`)** | **`V3.0–V3.3`** | **`HARPS + ESPRESSO + NIRPS`** | **`0.38–1.80`** | **`80` unikke** | **`501`** | **`6,570`** | **`5,850`** | **`0` i `V3.2/V3.3`** | **`0`** |

*Bemærkning om historisk navnekonvention i `D080`:* Nul-planet M0V kontrolstjernen `HD 191849` (`d = 6.165 pc`, `RV = -33.52 km/s`, `Gaia DR3 6631762811402194944`) i `D080` er `GJ 784` (ikke det unge exoplanet-system `AU Mic = HD 197481`, `d = 9.722 pc`, som er separat observeret under transit i `D082` med en himmelafstand på `> 10,649"`).

---

## 6. Reproducerbarhed og Leverancer

* **Reproducerbar bundet bundle:** `bounded_inputs/d082_bounded_bundle.json.gz` (`~25 MiB`) tillader deterministisk fuld genberegning uden netværksadgang via `python3 analyze.py --from-bounded-inputs` og uafhængig kontrol via `/usr/bin/python3 -S audit.py` (`PASS 10/10`).
* **Samlet pankromatisk videnskabelig artikel:** Publiceringsklart engelsksproget manuskript i `paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md` og LaTeX-kildekode i `paper/main.tex`.
* **Companion Archive H:** `SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_RESULTS_2026-11-15.zip` (`< 48 MiB`), fuldt integreret med `restore_d082_workspace.py` (`Archives A–H`).
