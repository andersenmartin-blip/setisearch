# Spor N6 — Extragalaktisk Kardashev Type III Teknosignatur-Søgning Tværs Over Den Lokale Superhob (`HECATE` `0,5–40,0 Mpc`)

**Kampagne-ID:** `SPOR_N6_KARDASHEV_III_LOCAL_SUPERCLUSTER` · **Dato:** 27. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Kardashev Type III ETI-kandidater · `N6_KARDASHEV_III_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Resumé

Spor N6 udvider projektets skala fra individuelle stjerner i Mælkevejen (`Spor N1–N5`, `1 AU – 10 kpc`) til **ekstragalaktiske Kardashev Type III-civilisationer** tværs over **Den Lokale Superhob (`D = 0,5–40,0 Mpc`)**. Ved at forene **Wright et al. (2014) $\hat{G}$ midt-IR spildvarme-kalorimetri** med **Garrett (2015) radio-infrarød $q_{22}$-selektion** over hele himlen på det prospektivt udvalgte **HECATE**-galaksekatalog (`J/MNRAS/506/1896/hecate`) opnår vi:

- **Analysepopulation:** **`1.381` galakser** (`0,5–40,0 Mpc`, $\log_{10}(M_*/M_\odot) \ge 9{,}0$) med komplet `2MASS K + WISE W1–W4 + logMtot` og garanteret **$\ge 1$ live all-sky radiodækning pr. galakse** tværs over `NVSS 1400 MHz` (`1.381`), `RACS-low 888 MHz` (`1.153`), `RACS-mid 1367,5 MHz` (`1.153`) og `LoTSS DR2 144 MHz` (`538` via Harvard VizieR `J/A+A/659/A1/catalog`-spejl).
- **Integreret stjernemasse og stjernetal:** **$M_* = 2{,}7534 \times 10^{13}\,M_\odot$** svarende til ca. **$4{,}1301 \times 10^{13}$ overvågede stjerner** (ved $1{,}5\text{ stjerner}/M_\odot$), heraf **`627`** galakser med Mælkevejs-masse eller større ($\log_{10} M_* \ge 10{,}0$) og **`373`** galakser inden for **`20 Mpc`**.
- **Prospektiv blind låsning:** `METHOD_LOCK.json` (SHA-256 `130b9bd4a3ad677f4ac14feabae677f50579c13cc392350b0c04574166c1e212`) og `n6_k3_analyzer.py` (SHA-256 `b32db7a77b00effae1ad2940e0ee5d2063ed1a7341a91faf3a47edbc9e123bf5`) låst kl. `2026-11-27T17:42:24.587724+00:00`, **+7 min 29 s før Stage 2 analyse (`2026-11-27T17:49:53.560152+00:00`)**.
- **Garrett $q_{22}$ & Wright $\hat{G}$:** **`839` radiodetekterede galakser** med median **$q_{22} = 0{,}9893$** og median midt-IR spildvarmefraktion **$\gamma_{\mathrm{III}} = 0{,}05113$**.
- **Stage 2 → Stage 3 Veto (`1.381 -> 11 -> 0 ETI`):** Nøjagtig **`11`** galakser udløser de blindt låste K-III-kriterier (`6` `K3_RADIO_QUIET_WASTE_HEAT` + `5` `K3_EXTREME_GHAT_50PCT`). Live `VLASS 1.2` (`3,0 GHz`) FITS-udsnit (`12/12` inkl. benchmark `IC 0691`) og `Legacy Survey DR10` optiske RGB-billeder (`12/12`) samt eksisterende radiomodstykker i `NVSS`/`LoTSS` (`11/11`) identificerer utvetydigt **alle `11` som kendt astrofysik** (`5` AGN/Seyfert/støvslørede kerner, `3` FIR kolde starburst-spiraler og `3` Markarian/blå kompakte dværg-starburstgalakser) $\rightarrow$ **`0` verificerede Kardashev Type III ETI-kandidater**.
- **1.200 Syntetiske Injektioner:** **`92,67 %`** detektionsfuldstændighed for radio-stille Type III-galakser med $\gamma_{\mathrm{III}} \ge 0{,}30$ (`0,0 %` ved `0,05–0,20`; `87,0 %` ved `0,30`; `93,0 %` ved `0,50`; `98,0 %` ved `0,75`), hvilket giver en fuldstændighedskorrigeret effektiv stikprøve på **$N_{\mathrm{eff}} = 1.279{,}73$ galakser**.
- **Bayesianske 95 % øvre prævalensgrænser (`0` ETI):**
  - **Alle superhobgalakser ($N_{\mathrm{eff}} = 1.279{,}73$):** **Jeffreys $f_{95} = 0{,}1499\,\%$** · Uniform $f_{95} = 0{,}2336\,\%$ · Clopper-Pearson $f_{95} = 0{,}2338\,\%$.
  - **Mælkevejs-masse ($\log M_* \ge 10$, $n = 627$):** **Jeffreys $f_{95} = 0{,}3057\,\%$** · Uniform $0{,}4759\,\%$.
  - **Nære galakser ($D \le 20\text{ Mpc}$, $n = 373$):** **Jeffreys $f_{95} = 0{,}5133\,\%$** · Uniform $0{,}7978\,\%$.
  - **Radiodetekteret $q_{22}$-kohorte ($n = 839$):** **Jeffreys $f_{95} = 0{,}2286\,\%$** · Uniform $0{,}3560\,\%$.
  - **Pr. stjerne K-III-grænse ($4{,}1301 \times 10^{13}$ stjerner):** **Jeffreys $f_{95}^{\star} = 4{,}6488 \times 10^{-14}$**.

---

## 2. Prospektiv Blind Låsning & Dataindsamling (Stage 1)

| Komponent | Kilde / Tjeneste | Dækning / Resultat | Note |
| --- | --- | --- | --- |
| **Metodelås** | `METHOD_LOCK.json` | `130b9bd4a3ad677f4ac14feabae677f50579c13cc392350b0c04574166c1e212` | Låst `2026-11-27T17:42:24.587724+00:00` |
| **Analyselås** | `scripts/n6_k3_analyzer.py` | `b32db7a77b00effae1ad2940e0ee5d2063ed1a7341a91faf3a47edbc9e123bf5` | Ren stdlib-analysator; **urørt efter lås** |
| **Galaksekatalog** | `HECATE` (`J/MNRAS/506/1896/hecate`) | **`1.381` galakser** | `0,5 <= D <= 40,0 Mpc`, `logMtot >= 9,0`, fuld `K+W1–W4` |
| **1.400 MHz Radio** | `NVSS` (`VIII/65/nvss`, $\delta \ge -40^\circ$) | **`1.381` dækket / `826` matches** | $5\sigma$-grænse `2,5 mJy` hvor ikke detekteret |
| **888 MHz Radio** | `RACS-low` (`J/other/PASA/38.58/racslow`, $\delta \le +41^\circ$) | **`1.153` dækket / `1.319` matches** | Skaleret til $1{,}4\text{ GHz}$ med $\alpha = -0{,}7$ |
| **1.367,5 MHz Radio** | `RACS-mid` (`VIII/109/racsmid`, $\delta \le +49^\circ$) | **`1.153` dækket / `433` matches** | Komplementær Syd- og ækvatorialdækning |
| **144 MHz Radio** | `LoTSS DR2` (`J/A+A/659/A1/catalog` via Harvard VizieR) | **`538` dækket / `1.472` matches** | Fallback fra `vo.astron.nl` (HTTP 502) uden kodeændring i låst analysator |
| **Opfølgende cutouts** | `VLASS 1.2` (`3 GHz` FITS) + `Legacy DR10` (RGB JPEG) | **`12/12` VLASS FITS + `12/12` Optiske DR10** | `11` K-III triggere + `1` kontrolbenchmark (`IC 0691`) |

Faste prospektive selektionsporte for Type III-kandidater i `n6_k3_analyzer.py`:
- **Radio-Quiet Waste-Heat (`K3_RADIO_QUIET_WASTE_HEAT`):** $\gamma_{\mathrm{III}} \ge 0{,}25$, `W1 - W4 >= 5,0 mag`, $q_{22} = \log_{10}(S_{22\,\mu\mathrm{m}}/S_{1{,}4\,\mathrm{GHz,eq}}) \ge 2{,}0$ ($\ge 10\times$ radio-underskud ift. starburst-linjen), og `W1 - W2 < 0,8 mag`.
- **Extreme Waste-Heat (`K3_EXTREME_GHAT_50PCT`):** $\gamma_{\mathrm{III}} \ge 0{,}50$ (over 50 % af stjernelyset re-emitteret i varm midt-IR, svarende til stærk $\hat{G}$-spildvarme) uanset `W1 - W2`.

---

## 3. Fuld Afklaring af Alle `11` Type III-Triggere (Stage 3 Veto)

Alle `11` Stage 2-triggere viste sig allerede at have live radiodetektion i all-sky arkivkatalogerne (`9/11` i `NVSS 1400 MHz` og `2/11` dybe lavfrekvens-detektioner i `LoTSS DR2 144 MHz`), og **`9/11` detekteres desuden direkte ved $\ge 5\sigma$ i `VLASS 1.2` (`3,0 GHz`)**. Den resterende svage dværggalakse (`UGC 05776`, `VLASS SNR = 1,66`) og kompakt starburst (`MRK 0462`, `VLASS SNR = 4,31`) har klare `144 MHz` `LoTSS`-detektioner og klassisk blåt optisk/IR starburst-kontinuum.

| PGC | Galakse | Dist (`Mpc`) | $\log M_*$ | $\gamma_{\mathrm{III}}$ | `W1-W2` | Kat. Radio (`1.4 GHz eq`) | $q_{22}$ (kat.) | `VLASS 3 GHz` Peak (`SNR`) | Port / Klassifikation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `10266` | **MESSIER 077** | `10,41` | `10,951` | `0,657` | `1,358` | `4.848,1 mJy` (`NVSS`) | `1,211` | `775,73 mJy` (`694,6`) | `K3_EXTREME_GHAT_50PCT` · **Seyfert 2 AGN** (`AGNs17=Y, AGNh=Y`) | `VETOED_ASTROPHYSICAL_NON_K3` |
| `40762` | **NGC 4355** | `32,51` | `10,241` | `0,876` | `1,112` | `40,8 mJy` (`NVSS`) | `2,495` | `29,08 mJy` (`203,3`) | `K3_EXTREME_GHAT_50PCT` · **Obscured CON/AGN** (`NGC 4418`, `AGNh=Y`) | `VETOED_ASTROPHYSICAL_NON_K3` |
| `50620` | **CGCG 074-129** | `22,80` | `9,404` | `0,667` | `0,899` | `7,6 mJy` (`NVSS`) | `2,270` | `5,20 mJy` (`33,7`) | `K3_EXTREME_GHAT_50PCT` · **AGN / Seyfert** (`AGNh=Y`) | `VETOED_ASTROPHYSICAL_NON_K3` |
| `39068` | **NGC 4194** | `39,08` | `10,564` | `0,621` | `0,686` | `100,7 mJy` (`NVSS`) | `1,633` | `20,58 mJy` (`174,8`) | `K3_EXTREME_GHAT_50PCT` · **Medusa Merger AGN/SB** (`AGNh=Y`) | `VETOED_ASTROPHYSICAL_NON_K3` |
| `31141` | **UGC 05720** | `15,42` | `9,435` | `0,501` | `0,313` | `16,6 mJy` (`NVSS`) | `1,848` | `3,34 mJy` (`25,9`) | `K3_EXTREME_GHAT_50PCT` · **Mrk 33 AGN/WR SB** (`AGNh=Y`) | `VETOED_ASTROPHYSICAL_NON_K3` |
| `26979` | **NGC 2893** | `25,23` | `9,912` | `0,362` | `0,133` | `7,4 mJy` (`NVSS`) | `2,004` | `2,72 mJy` (`20,5`) | `K3_RADIO_QUIET_WASTE_HEAT` · **FIR Starburst Spiral** (`F60=2,57 Jy`) | `VETOED_ASTROPHYSICAL_NON_K3` |
| `34107` | **IC 0676** | `20,04` | `9,955` | `0,335` | `0,174` | `9,7 mJy` (`NVSS`) | `2,047` | `2,21 mJy` (`16,8`) | `K3_RADIO_QUIET_WASTE_HEAT` · **FIR Starburst Barred Spiral** | `VETOED_ASTROPHYSICAL_NON_K3` |
| `40564` | **NGC 4385** | `33,42` | `10,368` | `0,485` | `0,235` | `13,1 mJy` (`NVSS`) | `2,162` | `3,23 mJy` (`23,3`) | `K3_RADIO_QUIET_WASTE_HEAT` · **FIR Starburst Barred Spiral** | `VETOED_ASTROPHYSICAL_NON_K3` |
| `40349` | **UGCA 280** | `23,12` | `9,262` | `0,474` | `0,328` | `2,9 mJy` (`NVSS`) | `2,053` | `0,93 mJy` (`8,7`) | `K3_RADIO_QUIET_WASTE_HEAT` · **Compact Dwarf HII** (`F60=1,19 Jy`) | `VETOED_ASTROPHYSICAL_NON_K3` |
| `31601` | **UGC 05776** | `27,31` | `9,554` | `0,331` | `0,179` | `0,451 mJy` (`LoTSS`) | `2,750` | `0,20 mJy` (`1,7`) | `K3_RADIO_QUIET_WASTE_HEAT` · **Markarian BCD Starburst** | `VETOED_ASTROPHYSICAL_NON_K3` |
| `49191` | **MRK 0462** | `38,05` | `9,469` | `0,303` | `0,447` | `0,220 mJy` (`LoTSS`) | `2,570` | `0,55 mJy` (`4,3`) | `K3_RADIO_QUIET_WASTE_HEAT` · **Markarian BCD HII** | `VETOED_ASTROPHYSICAL_NON_K3` |

*(Kontrolbenchmark `PGC 35206 / IC 0691` på `21,24 Mpc`, $\gamma_{\mathrm{III}} = 0{,}426$, detekteret med `VLASS Peak = 2,94 mJy`, `SNR = 22,2` som forventet for aktiv starburst.)*

---

## 4. Kalibrering (1.200 Injektioner) & Bayesianske Nullgrænser

Syntetiske radio-stille Kardashev Type III-galakser (bevaret ved ægte radiostøjgrænse og skaleret over HECATE-populationens `K+W1–W4`-fordeling, `200` forsøg pr. trin = **`1.200` forsøg**) bekræfter høj følsomhed over $\gamma_{\mathrm{III}} \ge 0{,}30$:

| Injektion $\gamma_{\mathrm{III}}$ | Forsøg | Genfundet | Fuldstændighed |
| --- | --- | --- | --- |
| `0,05` | `200` | `0` | `0,0 %` |
| `0,10` | `200` | `0` | `0,0 %` |
| `0,20` | `200` | `0` | `0,0 %` |
| `0,30` | `200` | `174` | **`87,0 %`** |
| `0,50` | `200` | `186` | **`93,0 %`** |
| `0,75` | `200` | `196` | **`98,0 %`** |
| **Samlet $\gamma_{\mathrm{III}} \ge 0{,}30$** | **`600`** | **`556`** | **`92,67 %`** |

Der er **`0` radio-stille Type III ETI-kandidater** i hele Den Lokale Superhob ($N_{\mathrm{eff}} = 1.381 \times 0{,}9267 = 1.279{,}73$):
- **Alle superhobgalakser:** **Jeffreys $f_{95} = 0{,}1499\,\%$** (`Uniform = 0,2336 %`, `Clopper-Pearson = 0,2338 %`).
- **Mælkevejs-masse ($\log_{10} M_* \ge 10{,}0$, $n=627$):** **Jeffreys $f_{95} = 0{,}3057\,\%$**.
- **Nærvolumen ($\le 20\text{ Mpc}$, $n=373$):** **Jeffreys $f_{95} = 0{,}5133\,\%$**.
- **Radiodetekterede galakser ($n=839$):** **Jeffreys $f_{95} = 0{,}2286\,\%$**.
- **Per-stjerne K-III-grænse ($4{,}1301 \times 10^{13}$ stjerner):** **Jeffreys $f_{95}^{\star} = 4{,}6488 \times 10^{-14}$**.

---

## 5. Visuelle Figurer (`6/6` Visuelt Verificeret i `VISUAL_REVIEW_N6.json`)

1. `figN6_01_local_supercluster_allsky_map.png` — All-sky Mollweide-kort over alle `1.381` HECATE-galakser farvet efter afstand (`0,5–40,0 Mpc`) og de `11` afviste triggere.
2. `figN6_02_garrett_q22_radio_ir_correlation.png` — Garrett (2015) `S_22um` vs. `1,4 GHz`-ækvivalent radioflux (`q_22 = 0,9893`) og `q_22` vs. $\gamma_{\mathrm{III}}$.
3. `figN6_03_ghat_waste_heat_and_wise_colors.png` — Wright $\hat{G}$ spildvarme-fraktion mod stjernemasse og Stern WISE-farveklassifikation (`W1-W2` vs. `W1-W4`).
4. `figN6_04_vlass_optical_cutouts_and_veto_funnel.png` — Parrede `Legacy DR10` optiske RGB-billeder & `VLASS 1.2` (`3 GHz`) FITS-radioudsnit med $7{,}5''$-aperturer samt fuld veto-tragt (`1.381 -> 11 -> 0 ETI`).
5. `figN6_05_k3_injection_recovery_and_bayesian_f95.png` — `1.200`-forsøgs Type III injektionskalibrering og Bayesianske 95 % øvre grænser på tværs af kohorter.
6. `figN6_06_kardashev_scale_synthesis_k1_to_k3.png` — Sammenhængende syntese fra Solsystemet (`Spor N2`, `1–40 AU`) og Mælkevejsstjerner (`Spor N1/N3/N4/N5`) til Den Lokale Superhob (`Spor N6`, `0,5–40 Mpc`).

---

## 6. Audit & Reproducerbarhed

- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n6_kardashev_iii.py`):** **`N6_KARDASHEV_III_AUDIT: 12/12 PASSED`** (`external_contacts == 0`).
- **Lokal arkivpakke:** `archives_n6/SETI_N6_KARDASHEV_III_LOCAL_SUPERCLUSTER_2026-11-27.zip`.
- **Synkroniserede rapportkopier:** `RESULTS_REPORT.md` (workspace & `progress/2026-11-27-n6-kardashev-iii-supercluster/`), `setisearch/docs/N6_KARDASHEV_III_SUPERCLUSTER_REPORT.md` og `reports/N6_KARDASHEV_III_SUPERCLUSTER_REPORT.md`.
