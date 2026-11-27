# Spor N5 Resultatrapport: 10-Års Midt-IR (`AllWISE` + `CatWISE2020` + `NEOWISE-R` `2010–2024`) & Optisk (`ZTF DR24` + `Gaia DR3`) Sekulær Megastruktur-Bro over alle 1.083 Master-Stjerner

**Kampagne-ID:** `SPOR_N5_10YR_SECULAR_IR_OPTICAL_1083`  
**Prospektivt låst:** `2026-11-27T16:45:24.180619+00:00` (`METHOD_LOCK.json` + `IMPLEMENTATION_LOCK.json`)  
**Stage 1 & Stage 2:** `1.083` Master-Stjerner + `13` Eksterne Benchmarks = `1.096` mål (`0` verificerede teknosignaturer, `external_contacts == 0`)  
**Låst ren-stdlib analysator SHA-256 (`n5_secular_analyzer.py`):** `c36ee2a522d764aef2a6eae9b5522053dd3651c8703a0c86e7e4c220e9033cfb`

---

## 1. Videnskabelig Hovedkonklusion

Spor N5 lukker det **tiårige tidsvindue (`2010–2024`, ~`14` års baseline)** for aktiv konstruktion af Dyson-sværme og optisk formørkende / midt-IR opvarmende megastrukturer på tværs af **samtlige `1.083` master-stjerner** (`787` Science + `296` Control; `267` `< 10 pc`) samt **`13` kalibreringsbenchmarks** (`ASASSN-21qj`, `Boyajians Stjerne / KIC 8462852`, `KH 15D`, `UX Ori`, `RZ Psc`, `V889 Her` og samtlige `7` *Hephaistos II*-kandidater `A–G`):

1. **Multiepokes dækning tværs over hele himlen:**
   - **`Gaia DR3` (`ARI` + høj-PM parallax-match):** **`1.041 / 1.083`** master-stjerner (`1.054 / 1.096` totalt).
   - **`WISE / AllWISE / CatWISE2020` (`2010–2018`):** **`1.033 / 1.083`** (`AllWISE = 1.018`, `CatWISE2020 = 745`, umættet `W2 >= 7,0` på **`450`** stjerner / **`280`** Science).
   - **`ZTF DR24` (`2018–2025`, `ngoodobs >= 40`):** **`218`** nordlige stjerner (`Dec >= -31°`).
   - **`NEOWISE-R` 10-års enkelteksponeeringer (`2014–2024`, egenbevægelsessporet):** **`81` mål** / **`22.394` rene enkelteksponeeringer** (~`21–22` halvårlige besøg) + **`9.800` `ZTF`-lyskurverækker**.
2. **Positiv kalibreringsgenfinding (*ASASSN-21qj* iskæmpe-kollision):**
   - `ASASSN_21QJ` udløser prospektivt både Tier-1 (`T1_IR_SECULAR_W1 | T1_IR_VAR_CHI2`) og vores Stage 3 `NEOWISE-R` sekulære Dyson-gate: **`21` halvårlige besøg (`9,94 år`, `304` rene eksponeringer)** giver **`dW2/dt = -0,02309 mag/år` (`Z = -15,97`)**, **`ptp = 0,872 mag`**, **`chi2_red = 493,31`** samt rødning **`d(W1-W2)/dt = +0,01243 mag/år`**, præcist som forventet når støvskyen varmer op i midt-IR.
   - Samtidig er **Boyajians Stjerne (`KIC 8462852`, `521` rene eksponeringer)** fuldkommen stabil i midt-IR over `10,0 år` (`dW2/dt = +0,00302 mag/år`, `ptp = 0,046 mag`, `chi2_red = 0,32`).
3. **10-års `NEOWISE-R` stabilitet på alle 7 *Hephaistos II*-kandidater (`A–G`):**
   - Alle **`7/7`** *Hephaistos*-kandidater viser **`0` sekulær opbygning over `10,4–10,5 år` (`21–22` besøg)** med $|dW2/dt| \le 0{,}00587\,\text{mag/år}$ (`HEPH_A = +0,00203`, `HEPH_D = -0,00117`, `HEPH_G = +0,00539`).
4. **Stage 1 → Stage 3 Veto tværs over `160` Science-triggere (`0` ETI):**
   - **`82`** klare `WISE`-mætning / høj-PM-skift inkl. `Luhman 16AB` (`WISE1049AB`, `1,996 pc`, Gaia-fraværende brun dværg med egenbevægelse `2,78"/år` der passerede gennem den faste `4,5"`-blænde `W2=14,2 -> 7,1`).
   - **`11`** høj-PM / `unWISE` katalogartefakter.
   - **`31`** flade i `NEOWISE-R` 10-års enkelteksponeeringer eller overfyldte baggrundsblends (bl.a. `OGLE-TR-111`: flad over `22` `NEOWISE-R`-besøg med `ptp = 0,1005 mag`).
   - **`18`** kendte aktive koronale / flare / formørkelsesbinære (`RZ Cas`, `XY UMa`, `AR Lac`, `YY Gem`, `HR 5907` m.fl.).
   - **`16`** kendte YSO'er & protoplanetariske diske (`Oph 163131`, `IRAS 16293-2422`, `GW Ori`, `LkCa 15`, `AS 209`, `GQ Lup`, `T Tau`, `2MASS J16090141` `dW2/dt = -0,02494`).
   - **`2`** kendte udviklede / kataklysmiske variable (`Mu Cephei` rød superkæmpe & `SS Cygni` dværgnova).
   - **Endeligt antal uforklarede sekulære Science-kandidater = `0` ETI.**

---

## 2. *Hephaistos II* `A–G` & Benchmarks (`10`-Års `NEOWISE-R`, `2014–2024`)

| Mål | Besøg (`år`) | Median `W2` | `dW2/dt` (`mag/år`) | `Z(dW2/dt)` | `p2p W2` (`mag`) | Konklusion |
| --- | --- | --- | --- | --- | --- | --- |
| **`ASASSN_21QJ`** | `21` (`9,94`) | `11,6965` | **`-0,02309`** | **`-15,97`** | **`0,8720`** | **Positiv benchmark genfundet (`chi2_red = 493,31`)** |
| **`KIC_8462852`** | `21` (`10,00`) | `10,4530` | `+0,00302` | `+2,09` | `0,0460` | Boyajians Stjerne: stabil i midt-IR (`chi2_red = 0,32`) |
| **`HEPH_A`** | `22` (`10,44`) | `11,8370` | `+0,00203` | `+1,45` | `0,0690` | Flad over 10,4 år (`0` Dyson-opbygning) |
| **`HEPH_B`** | `21` (`10,4`) | `13,6595` | `+0,00219` | `+0,88` | `0,2405` | Flad (DR10 galakseblend i PSF) |
| **`HEPH_C`** | `21` (`10,4`) | `14,1910` | `+0,00203` | `+0,79` | `0,1860` | Flad (svag nabo i PSF) |
| **`HEPH_D`** | `22` (`10,50`) | `13,6235` | `-0,00117` | `-0,38` | `0,1610` | Flad (LoTSS radio-AGN + DR10 galakseblend) |
| **`HEPH_E`** | `21` (`10,4`) | `13,2450` | `+0,00253` | `+1,22` | `0,2095` | Flad (DR10 galakseblend i PSF) |
| **`HEPH_F`** | `21` (`10,4`) | `12,7050` | `+0,00587` | `+3,70` | `0,1050` | Flad (svag lineær drift < artefakttærskel) |
| **`HEPH_G`** | `22` (`10,4`) | `12,8485` | `+0,00539` | `+3,20` | `0,1190` | Flad (`127σ` VLASS radio-AGN) |

---

## 3. `1.200` Injektioner & Bayesianske $f_{95}$ Øvre Grænser ($k=0$ ETI)

| Rate `|dW2/dt|` (`mag/år`) | Forsøg | Genfundet | Komplethed | | Kohort ($k=0$ ETI) | $N_{\text{eff}}$ | Jeffreys $f_{95}$ | Uniform $f_{95}$ | Clopper-Pearson $f_{95}$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0,005` | `200` | `0` | `0,0 %` | | **All Master Stars (`Gaia + IR`)** | `1.083,0` | **`0,1772 %`** | `0,2760 %` | `0,2762 %` |
| `0,01` | `200` | `21` | `10,5 %` | | **`Gaia DR3` Monitored** | `1.041,0` | **`0,1843 %`** | `0,2871 %` | `0,2874 %` |
| `0,02` | `200` | `147` | `73,5 %` | | **Science Stars (`All`)** | `787,0` | **`0,2437 %`** | `0,3794 %` | `0,3799 %` |
| `0,04` | `200` | `176` | `88,0 %` | | **Solar Neighborhood (`< 10 pc`)** | `267,0` | **`0,7161 %`** | `1,1116 %` | `1,1157 %` |
| `0,08` | `200` | `185` | `92,5 %` | | **Unsaturated IR (`S >= 0,04 mag/yr`)** | `258,53` | **`0,7395 %`** | `1,1476 %` | `1,1521 %` |
| `0,15` | `200` | `193` | **`96,5 %`** | | **`ZTF DR24` Northern (`n>=40`)** | `218,0` | **`0,8762 %`** | `1,3586 %` | `1,3648 %` |

Samlet genfinding ved `>= 0,04 mag/år` = **`92,33 %`** (`>= 0,02 mag/år` = **`87,62 %`**).

---

## 4. Figurer & Reproducerbarhed

Alle 6 figurer (300 DPI PNG) er inspiceret og godkendt (`VISUAL_REVIEW_N5.json`):
1. `figures/figN5_01_allsky_10yr_coverage_and_ruwe.png` — All-sky multi-epoke fodaftryk + `Gaia DR3 RUWE` vs. `CatWISE2020`.
2. `figures/figN5_02_10yr_ir_drift_vs_optical_trend.png` — `NEOWISE-R` sekulær drift vs. termisk rødning (`ASASSN-21qj` vs. `0` Science ETI).
3. `figures/figN5_03_neowise_10yr_benchmark_and_hephaistos.png` — `10`-års lyskurver for `ASASSN-21qj`, Boyajians Stjerne, `KH 15D` og `Hephaistos A, D, G`.
4. `figures/figN5_04_science_triggers_neowise_ztf_vetting.png` — `10`-års lyskurver af centrale Science-triggere (`J160901`, `SS Cyg`, `OGLE-TR-111`, `Luhman 16AB`) + veto-tragt (`1.083 -> 160 -> 0`).
5. `figures/figN5_05_injection_recovery_and_bayesian_f95.png` — `1.200` sekulære injektioner & Bayesianske $f_{95}$-grænser.
6. `figures/figN5_06_unified_5track_seti_landscape_n1_to_n5.png` — Samlet overblik over **Spor R1+R2 & N1–N5**.

Lokalt arkiv (inkl. alle `NEOWISE-R` & `ZTF` rå-lyskurver): `archives_n5/SETI_N5_10YR_SECULAR_IR_OPTICAL_1083_2026-11-27.zip`.  
Ingen eksterne tidsskriftsuploads (`external_contacts == 0`).
