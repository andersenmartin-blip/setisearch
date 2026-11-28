# Spor N13 — Skaleret `33`-Stjerners Fin-Opløsning Vandhuls-SETI (`2,794–2,836 Hz` Gajjar Plasma, Parabolisk De-Chirp v2 & Kam v2 -> `0` ETI)

**Kampagne-ID:** `SPOR_N13_SCALED_33STAR_WATERHOLE_PLASMA_DECHIRP_COMB` · **Dato:** 28. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Mælkevejs-ETI · `N13_SCALED_WATERHOLE_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Blind-Spot Gennembrud v2, `3,7×` Skalering & Prospektiv Låsning

Klassiske smalbånds-radio-SETI-pipelines (`turboSETI` 1-bin lineær de-Doppler) forbliver **100 % blinde (`0,00 %` genfinding på `1.200` forsøg)** over for signaler, der udviser interstellær/stellær-vind **Gajjar plasma-udtværing (`10–350 Hz`)**, stærk **parabolisk orbital acceleration** eller **sub-tærskel harmoniske frekvenskamme**. I **Spor N13** opskalerede vi Spor N11A (`9` `<= 6 pc` M-dværge, `54` skanninger) **3,7×** med **`24` splinternye stråle-uafhængige `< 9,1 pc` Mælkevejsstjerner (`144` ~`15 GB` *Breakthrough Listen* GBT `.0000.h5`-skanninger = `1,98 TiB` rå arkivdata)** og opgraderede samtidig detektorkernen til **Fine Water-Hole Blind-Spot v2**:
- **Kirurgisk HTTP-Range (nul fuld `.h5`-hentning):** Skar præcis den justerede `1422,3633–1427,5055 MHz` (`1.048.576`-kanalers Vandhuls-blok, `2,794–2,836 Hz/bin`) fra alle `144` eksterne skanninger med `7,39 GiB` overført mod `1,98 TiB` arkivvolumen (**`274,6×` båndbreddebesparelse**), hvilket forener med N11A til **`33` nabostjerner (`198` `.0000.h5`-skanninger = `2,74+ TiB` råt / `97,1868 MHz` rent Vandhuls-spektrum / `2.112` blokke)**.
- **Stikprøve tværs over `A/G/K/M`-spektraltyper (`0` overlap med N11A):** `2` `A`-stjerner (`GJ244` Sirius A/B, `GJ768` Altair), `2` `G`-solanaloger (`HIP72659` Xi Boo A/B, `HIP64924` 61 Vir), `6` `K`-stjerner (`GJ820B` 61 Cyg B, `GJ380`, `HIP19849` 40 Eri A, `GJ702A`, `HIP32984`, `HIP17378` δ Eri) og `14` nye `M`-dværge (`GJ699` Barnard's Star, `GJ406` Wolf 359, `GJ905`, `GJ447` Ross 128, `GJ725`, `GJ1111`, `GJ860A`, `GJ628` Wolf 1061, `GJ473AB`, `GJ83.1` TZ Ari, `GJ412A`, `GJ873` EV Lac, `HIP103039`, `HIP109388` GJ 849), heraf **`6` optisk+radio-broværter** mod Spor N11B/N12 (`GJ699`, `GJ447`, `GJ628`, `GJ83.1`, `HIP64924`, `HIP109388`).
- **Prospektiv blind låsning:** Analysator (`SHA-256 = 03638ed34550b8afb6ce6cd52da6e82482af21a4a8ae4c32bca4ac96c463e3e1`) og `METHOD_LOCK.json` (`SHA-256 = 79caf0279be28a98b7046b711fae57fbf09086b943d8a498709a128d4665e409`) blev kryptografisk forseglet kl. `2026-11-28T10:31:14.652411+00:00` **før første Stage 1 Range-kald** (`pre_acquisition_blind_lock == True`).
- **`1.400`-Forsøgs Hoved-Mod-Hoved Benchmark på Ægte Vandhuls-Støj (`G1–G3 v2` mod `N11A v1` & Klassisk `turboSETI`-analog):**
  - **Kanal `G1` — Gajjar Plasma-Udtværing (`10–350 Hz`, `400` forsøg):** **`375/400` (`93,75 %`)** mod **`0/400` (`0,00 %`)** klassisk 1-bin.
  - **Kanal `G2 v2` — Opgraderet Parabolisk De-Chirp (`w=3`, fint net `Δd1=3` + matched-trajectory `OFF < 5,5`, `400` forsøg):** **`399/400` (`99,75 %`)** (løftet fra `9,75 %` i N11A!) mod **`0/400` (`0,00 %`)** klassisk 1-bin.
  - **Kanal `G3 v2` — Opgraderet `3`-Bin Udjævnet `4096`-Vindues Kam-Korrelation (`400` forsøg):** **`383/400` (`95,75 %`)** (løftet fra `63,25 %` i N11A!) mod **`0/400` (`0,00 %`)** klassisk 1-bin.
  - **Ren-Støj Nul-Test (`NULL_NOISE_FPR`, `200` ikke-injicerede forsøg):** **`0/200` (`0,00 %` FPR)**.
  - **Samlet `3`-klasses gennemsnitlig komplethed:** **`96,42 %` (`1.157/1.200`)** mod **`55,17 %`** i N11A v1 og **`0,00 %`** klassisk 1-bin.
- **Stage 2 & Stage 3 Veto (`1.536` blokke -> `0` ETI) + Fysiske Grænser:**
  - **`0` Stage 2 `ABACAD`-triggere** tværs over alle `24` stjerner / `70,6932 MHz` nyt rent Vandhuls-spektrum (`97,1868 MHz` samlet); `OFF`-veto eliminerede effektivt alle delte terrestriske kamme op til `comb_on2 = 110,009` (`OFF = 217,278`), med median `>5σ` RFI-belægning på under `0,01 %`.
  - **`10σ` `W=1` Isotropisk EIRP (`GBT SEFD = 10 Jy`):** **`2,8069–68,6458 GW`** (N13-median **`18,086 GW`**, fx **`2,81 GW`** på Barnard's Star `GJ 699`, `4,87 GW` på Wolf 359, `5,75 GW` på Sirius A/B); for `W=16` (`~45 Hz` plasma) median `72,345 GW`.
  - **Forenede `33`-stjerners / `2.112`-blokkes Bayesianske $f_{95}$ (`0` ETI):**
    - **N13 alene (`24` raw / `23,14` eff.):** Jeffreys $f_{95} = \mathbf{7{,}6141\,\%}$ raw / **`7,8826 %`** eff. · Uniform `11,6707 %` eff. (`0,1296 %` pr. blok eff.).
    - **Forenet N11A + N13 (`33` raw / `28,105` eff.):** **Jeffreys $f_{95} = \mathbf{5{,}6126\,\%}$** raw / **`6,5490 %`** eff. (Uniform `8,4340 %` raw / `9,7808 %` eff.) — **4,7× skærpelse** fra N11A (`30,7435 %` eff.).
    - **Forenet `2.112` blokke (`1.798,72` eff.):** **Jeffreys $f_{95} = \mathbf{0{,}1067\,\%}$** (`0,0909 %` raw · Uniform `0,1663 %` eff.).

---

## 2. Stjerneoversigt (`24` Nye `< 9,1 pc` Stjerner · `144` HTTP-Range Utsnit · `1.536` Blokke)

| Stjerne | Navn | Sp.Type | Afst. (`pc`) | Kadence | `df` (`Hz`) | Ren `BW` (`MHz`) | `RFI` (`%`) | `EIRP W=1` (`GW`) | `EIRP W=16` (`GW`) | `G1/G2/G3` -> `ETI` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GJ699` | Barnard's Star (`N11B,D112`) | `M4V` | `1,8282` | `--91648` | `2,8355` | `2,9728` | `0,00925` | **`2,8069`** | `11,2276` | `0` -> **`0`** |
| `GJ406` | Wolf 359 (`D110`) | `M6V` | `2,4086` | `--71675` | `2,8355` | `2,9728` | `0,00909` | **`4,8720`** | `19,4881` | `0` -> **`0`** |
| `GJ244` | Sirius A/B (`D110`) | `A1V` | `2,6371` | `--75886` | `2,7940` | `2,9292` | `0,00828` | **`5,7547`** | `23,0189` | `0` -> **`0`** |
| `GJ905` | Ross 248 (`D109`) | `M5.5V` | `3,1570` | `--76560` | `2,7940` | `2,9292` | `0,00848` | **`8,2475`** | `32,9899` | `0` -> **`0`** |
| `GJ447` | Ross 128 (`N11B`) | `M4V` | `3,3749` | `--71687` | `2,8355` | `2,9728` | `0,00906` | **`9,5654`** | `38,2616` | `0` -> **`0`** |
| `GJ820B` | 61 Cygni B (`D109`) | `K7V` | `3,4973` | `--74913` | `2,7940` | `2,9292` | `0,00852` | **`10,1213`** | `40,4854` | `0` -> **`0`** |
| `GJ725` | Struve 2398 A/B (`D109`) | `M3V` | `3,5223` | `--75057` | `2,7940` | `2,9292` | `0,00829` | **`10,2666`** | `41,0662` | `0` -> **`0`** |
| `GJ1111` | DX Cancri (`D099`) | `M6.5V` | `3,5810` | `--66099` | `2,7940` | `2,9292` | `0,00817` | **`10,6116`** | `42,4464` | `0` -> **`0`** |
| `GJ860A` | Kruger 60 A/B (`D109`) | `M3V` | `4,0110` | `--71913` | `2,8355` | `2,9728` | `0,01051` | **`13,5110`** | `54,0439` | `0` -> **`0`** |
| `GJ628` | Wolf 1061 (`N12`) | `M3.5V` | `4,3059` | `--82957` | `2,7940` | `2,9292` | `0,00817` | **`15,3426`** | `61,3706` | `0` -> **`0`** |
| `GJ473AB` | FL Virginis (`D109`) | `M5.5V` | `4,3900` | `--71063` | `2,8355` | `2,9728` | `0,25545` | **`16,1849`** | `64,7396` | `0` -> **`0`** |
| `GJ83.1` | TZ Ari / GJ 9066 (`N12`) | `M5.0V` | `4,4710` | `--73219` | `2,7940` | `2,9292` | `0,00850` | **`16,5418`** | `66,1670` | `0` -> **`0`** |
| `GJ380` | Groombridge 1618 (`D109`) | `K7V` | `4,8706` | `--63792` | `2,7940` | `2,9292` | `0,00828` | **`19,6308`** | `78,5231` | `0` -> **`0`** |
| `GJ412A` | Lalande 21258 (`D109`) | `M1V` | `4,9047` | `--73183` | `2,7940` | `2,9292` | `0,00845` | **`19,9066`** | `79,6264` | `0` -> **`0`** |
| `HIP19849` | 40 Eridani A (`D109`) | `K0.5V` | `5,0098` | `--85469` | `2,8355` | `2,9728` | `0,06389` | **`21,0776`** | `84,3105` | `0` -> **`0`** |
| `GJ873` | EV Lacertae (`D104`) | `M3.5V` | `5,0516` | `--76548` | `2,7940` | `2,9292` | `0,00854` | **`21,1169`** | `84,4676` | `0` -> **`0`** |
| `GJ702A` | 70 Ophiuchi A/B (`D109`) | `K0V` | `5,1140` | `--72585` | `2,8355` | `2,9728` | `0,00914` | **`21,9635`** | `87,8542` | `0` -> **`0`** |
| `GJ768` | Altair (`D103`) | `A7V` | `5,1300` | `--73764` | `2,7940` | `2,9292` | `0,00823` | **`21,7774`** | `87,1098` | `0` -> **`0`** |
| `HIP103039` | LP 816-60 (`D109`) | `M4V` | `5,6202` | `--73800` | `2,7940` | `2,9292` | `0,00829` | **`26,1382`** | `104,5528` | `0` -> **`0`** |
| `HIP72659` | Xi Bootis A/B (`D109`) | `G8V` | `6,7490` | `--73113` | `2,7940` | `2,9292` | `0,01134` | **`43,5232`** | `174,0927` | `0` -> **`0`** |
| `HIP64924` | 61 Virginis (`N12`) | `G5V` | `8,5033` | `--84887` | `2,8355` | `2,9728` | `0,00874` | **`60,7234`** | `242,8936` | `0` -> **`0`** |
| `HIP32984` | HD 50281 (`D109`) | `K3.5V` | `8,7450` | `--95069` | `2,7940` | `2,9292` | `0,00806` | **`63,2837`** | `253,1348` | `0` -> **`0`** |
| `HIP109388` | GJ 849 (`N12`) | `M3.5V` | `8,8006` | `--73890` | `2,7940` | `2,9292` | `0,00973` | **`64,0910`** | `256,3639` | `0` -> **`0`** |
| `HIP17378` | Delta Eridani (`D109`) | `K0IV` | `9,0410` | `--71301` | `2,8355` | `2,9728` | `0,00976` | **`68,6458`** | `274,5832` | `0` -> **`0`** |

---

## 3. Figurer, Verifikation & Arkiv

- **6 visuelt kontrollerede 300-DPI PNG-figurer (`figN13_01`–`figN13_06`, forseglet i `VISUAL_REVIEW_N13.json`):** `33`-stjerners `2,8–68,6 GW` EIRP & `A/G/K/M`-dækning (`70,7 / 97,2 MHz`); `1.400`-forsøgs `v2`-benchmark (`93,75 %` Gajjar, `99,75 %` parabolisk de-chirp, `95,75 %` kam v2, `0,00 %` Null FPR mod `0,00 %` klassisk); bandpass RFI på Barnard's Star, Sirius, 61 Vir & 40 Eri A; `1.536`-blokkes `G3 v2` & RFI-fordeling; skærpede `33`-stjerners Bayesianske $f_{95}$ (`6,55 %` / `0,11 %`); samt Mælkevejens **Blind-Spot Pentalogy (`N10 + N11A + N11B + N12 + N13`)**.
- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n13_scaled_waterhole.py`):** **`N13_SCALED_WATERHOLE_AUDIT: 12/12 PASSED`** (`external_contacts == 0`).
- **Lokal arkivpakke:** `archives_n13/SETI_N13_SCALED_WATERHOLE_BLINDSPOT_2026-11-28.zip`.
