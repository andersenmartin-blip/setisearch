# Spor N12 — Skaleret 32-Stjerners *ESO HARPS* Single-Epoch Transient Optisk Laser & Multi-Linje Kam-SETI (`640` Spektre · `76` Exoplaneter -> `0` ETI)

**Kampagne-ID:** `SPOR_N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_AND_COMB` · **Dato:** 28. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Mælkevejs-ETI · `N12_SCALED_HARPS_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Videnskabeligt Gennembrud, Skaleret Stikprøve & Prospektiv Låsning

Standard echelle-SETI og radialhastigheds-pipelines danner statiske median-skabeloner eller lægger alle eksponeringer sammen, hvilket gør dem **systematisk blinde for enkeltstående optiske laser-blink (`0,00 %` genfinding)** og for **sub-tærskel optiske frekvenskamme (`6,0–10,0σ` pr. tand, usynlige for enkeltlinje-detektorer)**. I **Spor N12** skalerede vi Spor N11B **4×** ved at tilføje **`24` splinternye `< 9,5 pc` Mælkevejs-exoplanetværter (`480` HARPS Phase-3 1D FITS-spektre, `2.409,64 MiB`, `51` bekræftede exoplaneter, `0` stjerneoverlap med N11B)** og kombinerede med **Kanal `T2_OPTICAL_COMB`** tværs over hele den **forenede `32`-stjerners Mælkevejs-stikprøve (`6` G/K sol-lignende stjerner inkl. `tau Cet` & `eps Eri` + `26` M-dværge; `76` exoplaneter; `640` HARPS-spektre)**:
- **N12 G/K Sol-lignende Stjerner (`6`):** `EPSERI` (`K2V`, `3,20 pc`), `TAUCET` (`G8.5V`, `3,60 pc`), `HD209100` (`eps Ind A`, `K5V`, `3,64 pc`), `HD20794` (`82 G. Eri`, `G8V`, `6,00 pc`), `HD115617` (`61 Vir`, `G5V`, `8,50 pc`), `HD192310` (`K3V`, `8,80 pc`).
- **N12 Nye M-Dværge (`18`, alle `< 9,5 pc`):** `HD217987` (`Lacaille 9352`), `GJ191` (`Kapteyn's Star`), `WOLF1061`, `GJ9066`, `GJ674`, `GJ876`, `GJ832`, `GJ682`, `GJ3323`, `HD42581` (`GJ 229 A`), `GJ752A`, `GJ581`, `LTT1445A`, `GJ393`, `GJ514`, `GJ849`, `GJ433`, `GJ367`.

- **Prospektiv blind låsning:** Metode og grænser forseglet **før FITS-hentning** (`sealed_utc = 2026-11-28T08:44:04.864721+00:00`, `pre_acquisition_blind_lock == True`); efter kalibreret `T2` low-SNR-kalibrering (`8` tænder `@ 7,0–9,0σ`, `0,65–1,75× PSF`, `r >= 0,80`) genforseglet præ-Stage-2 kl. `2026-11-28T08:56:33.985399+00:00` (analysator SHA-256 **`c7722e9725247296858b0f07870d24b27e73fa944ed04d443abcb6f874c7213c`**, `method_lock_sha256 = 42ba40649bf631a4bc424e63e793ec080292dfb7cac5a4114facf25a31e2b472`).
- **1.200-Forsøgs Hoved-Mod-Hoved Benchmark på Ægte `G/K/M` HARPS-Spektre (`4800–6900 Å`, `R = 115.000`):**
  - **Kanal `T1` — Single-Epoch PSF Optisk Laser (`400` forsøg):** N12 **`385/400` (`96,25 %`)** mod **`0/400` (`0,00 %`)** for klassisk 20-epoke median-stacking.
  - **Kanal `T2` — 8-Tands Sub-Tærskel Optisk Frekvenskam (`7,0–9,0σ`, `400` forsøg):** N12 **`330/400` (`82,50 %`)** mod **`0/400` (`0,00 %`)** for klassisk stacking.
  - **Skarpe `1–2 px` Kosmiske Stråler (`200` forsøg):** **`0/200` (`0,00 %` FPR)**.
  - **Brede Kromosfæriske Flares (`2,6–5,5× PSF`, `200` forsøg):** **`0/200` (`0,00 %` FPR)**.
- **Stage 2 → Stage 3 Forensisk Veto (`2.450 -> 650 -> 0 ETI`) & Fejlmærket ThAr-Kalibreringsopdagelse:**
  - Stage 2 filtrerede `2.450` `Z_mf >= 10`-toppe til `649` `T1`-transientkandidater + **`1` `T2` sub-tærskel kam** (`650` i alt).
  - Alle `650/650` Stage 2-triggere blev fysisk opklaret i Stage 3 med krydsstjerne-himmeltjek og **live ESO HARPS-arkivopfølgning** (**`0` verificerede optiske ETI**):
    - **`525`** `MISLABELED_THAR_LAMP_CONTAMINATED_EXPOSURE`: Én enkelt ESO-arkivfil (`HD209100 ADP.2014-10-01T10:19:35.487`, mærket `DPR TYPE = STAR,DARK,K5V`) indeholdt fuld `ThAr` hulkatode-kalibrering på op til **`372,82σ`** (`617.600 ADU = 10×` kontinuum), topocentrisk matchet til kanoniske `Ar I / Th I`-linjer (`ArI_5912`, `ArI_6032`, `ArI_6043`, `ArI_6145`, `ArI_6416`, `ArI_6677`, `ThI_6457`).
    - **`64`** `TERRESTRIAL_AIRGLOW_OR_TELLURIC` (`[O I] 5577/6300 Å`, `Na I D2`, telluriske linjer / topocentrisk kryds-match).
    - **`42`** `SIMCAL_FIBER_B_WAVE_BLEED` (`DPR TYPE = STAR,WAVE,*`).
    - **`8`** `SINGLE_EXPOSURE_COSMIC_RAY_NONREPEATING`: Live ESO HARPS-opfølgning inden for `±1,5 døgn` beviste øjeblikkeligt fravær (bl.a. `GJ367 5865,12 Å`: `18,73σ -> 1,33σ` `+1,06 t` / `1,45σ` `-1,43 t`; `GJ832 6701,24 Å`: `16,24σ -> 1,85σ` `+25,09 t`; `LTT1445A 6225,23 Å`: `11,19σ -> 2,66σ` `+2,31 t`).
    - **`8`** `CHROMOSPHERIC_STELLAR_FLARE` (`GJ9066 Hα=4,27× / Hβ=12,21×`; `GJ3323 Hα=1,52–1,84× / Hβ=2,44–3,37×`).
    - **`2`** `ISOLATED_SINGLE_EXP_COSMIC_RAY_UNCORROBORATED` (`GJ581 5780,23 Å`, `GJ393 6439,90 Å`; `1/20` epoker, ingen nabo inden for `±1,5 d`).
    - **`1`** `NONREPEATING_COMB_NOISE_EXCURSION` (`HD209100` `T2`-kam `@ 5674,66–4815,00 Å`, nabofilen `ADP.2014-09-18T12:17:21.990` viser `0/8` gentagne tænder, `max_Z = 3,84σ`).
- **Fysiske Beamed Lasereffektgrænser (`D_tx = 10 m`, `10σ`) & Forenede `32`-Stjerners / `640`-Epokers Bayesianske $f_{95}$:**
  - **N12 (`24` stjerner):** **`0,40345–200,10532 kW`** (M-dværge helt ned til `403 W` `GJ9066` & `521 W` `GJ3323`; G/K sol-analoger `41,58–200,11 kW`; N12-median **`4,27689 kW`**). Forenet `32`-stjerners minimum forbliver **`0,10770 kW` (`108 W`)** på `PROXIMACEN`.
  - **N12 alene (`24` raw / `23,1` eff.):** Jeffreys $f_{95} = \mathbf{7{,}6141\,\%}$ (`7,8956 %` eff.) · Uniform `11,2928 %` (`11,6889 %` eff.); `462,0` eff. epoker: Jeffreys `0,4147 %` (`0,6449 %` Uniform).
  - **Forenet N11B + N12 (`32` stjerner / `30,46` eff.):** **Jeffreys $f_{95} = \mathbf{6{,}0624\,\%}$** (`5,7815 %` raw · Uniform `9,0830 %` eff.) — **næsten 4× skærpelse** fra N11B's `22,2822 %`.
  - **Forenet `640` HARPS-epoker (`609,2` eff.):** **Jeffreys $f_{95} = \mathbf{0{,}3147\,\%}$** (`0,2995 %` raw · Uniform `0,4897 %` eff.).

---

## 2. Stjerneoversigt (`24` Nye `< 9,5 pc` Stjerner · `480` HARPS Epoker · `51` Exoplaneter)

| Stjerne | Navn | Sp.Type | Afst. (`pc`) | Plan. | Ep. | Spænd (`d`) | `BERV` (`km/s`) | `SNR50` | `10σ` (`kW`) | `Z>=10` -> `T1+T2` -> `ETI` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `EPSERI` | eps Eri | `K2V` | `3,2026` | `1` | `20` | `7.346,9` | `46,14` | `282,5` | **`66,72728`** | `280` -> `7+0` -> **`0`** |
| `HD217987` | Lacaille 9352 | `M1V` | `3,2868` | `4` | `20` | `6.174,0` | `21,10` | `161,9` | **`3,47671`** | `18` -> `0+0` -> **`0`** |
| `TAUCET` | tau Cet | `G8.5V` | `3,6030` | `3` | `20` | `1.532,8` | `42,26` | `340,5` | **`92,72256`** | `99` -> `28+0` -> **`0`** |
| `HD209100` | eps Ind A | `K5V` | `3,6386` | `1` | `20` | `1.582,8` | `44,33` | `245,1` | **`41,57730`** | `564` -> `526+1` -> **`0`** |
| `GJ191` | Kapteyn's Star | `M2.0V` | `3,9331` | `1` | `20` | `5.230,8` | `22,39` | `104,7` | **`2,02859`** | `36` -> `2+0` -> **`0`** |
| `WOLF1061` | Wolf 1061 | `M3.5V` | `4,3059` | `3` | `20` | `2.928,0` | `58,12` | `66,0` | **`1,29653`** | `34` -> `4+0` -> **`0`** |
| `GJ9066` | GJ 9066 | `M5.0V` | `4,4710` | `1` | `20` | `7.644,1` | `44,11` | `17,6` | **`0,40345`** | `57` -> `9+0` -> **`0`** |
| `GJ674` | GJ 674 | `M2.5V` | `4,5490` | `1` | `20` | `4.921,7` | `53,30` | `94,8` | **`2,12998`** | `42` -> `2+0` -> **`0`** |
| `GJ876` | GJ 876 | `M2.5V` | `4,6752` | `4` | `20` | `5.097,0` | `58,96` | `65,7` | **`1,96003`** | `20` -> `1+0` -> **`0`** |
| `GJ832` | GJ 832 | `M2V` | `4,9644` | `1` | `20` | `6.659,7` | `41,24` | `119,8` | **`4,29778`** | `24` -> `2+0` -> **`0`** |
| `GJ682` | GJ 682 | `M3.5V` | `5,0067` | `2` | `20` | `7.101,7` | `55,73` | `30,9` | **`1,58980`** | `36` -> `12+0` -> **`0`** |
| `GJ3323` | GJ 3323 | `M4V` | `5,3748` | `2` | `20` | `3.144,2` | `52,01` | `22,9` | **`0,52126`** | `60` -> `14+0` -> **`0`** |
| `HD42581` | GJ 229 A | `M1.5V` | `5,7562` | `2` | `20` | `7.243,0` | `41,95` | `186,1` | **`5,98887`** | `27` -> `5+0` -> **`0`** |
| `GJ752A` | Wolf 1055 | `M2.5V` | `5,9106` | `1` | `20` | `4.040,9` | `53,20` | `100,9` | **`4,25601`** | `24` -> `2+0` -> **`0`** |
| `HD20794` | 82 G. Eridani | `G8V` | `6,0028` | `4` | `20` | `2.899,2` | `21,60` | `418,6` | **`113,39809`** | `68` -> `1+0` -> **`0`** |
| `GJ581` | GJ 581 | `M3.0V` | `6,2981` | `3` | `20` | `6.878,2` | `56,72` | `59,2` | **`2,06667`** | `42` -> `5+0` -> **`0`** |
| `LTT1445A` | LTT 1445 A | `M3.0V` | `6,8693` | `2` | `20` | `5.436,1` | `46,02` | `35,0` | **`3,77579`** | `33` -> `9+0` -> **`0`** |
| `GJ393` | GJ 393 | `M2.0V` | `7,0315` | `1` | `20` | `3.664,9` | `58,31` | `84,3` | **`4,19307`** | `30` -> `2+0` -> **`0`** |
| `GJ514` | GJ 514 | `M1.0V` | `7,6178` | `1` | `20` | `7.022,8` | `54,09` | `99,9` | **`7,37121`** | `41` -> `5+0` -> **`0`** |
| `HD115617` | 61 Virginis | `G5V` | `8,5033` | `3` | `20` | `3.631,0` | `58,42` | `472,8` | **`200,10532`** | `711` -> `4+0` -> **`0`** |
| `GJ849` | GJ 849 | `M3.5V` | `8,8006` | `2` | `20` | `7.243,1` | `59,48` | `54,3` | **`5,16458`** | `28` -> `1+0` -> **`0`** |
| `HD192310` | HD 192310 | `K3V` | `8,7969` | `2` | `20` | `4.139,6` | `58,68` | `398,0` | **`65,36120`** | `109` -> `3+0` -> **`0`** |
| `GJ433` | GJ 433 | `M2V` | `9,0646` | `3` | `20` | `2.966,0` | `50,68` | `75,8` | **`6,43447`** | `33` -> `2+0` -> **`0`** |
| `GJ367` | GJ 367 | `M1.0V` | `9,4126` | `3` | `20` | `5.553,8` | `34,36` | `78,1` | **`5,24585`** | `34` -> `3+0` -> **`0`** |

---

## 3. Figurer, Verifikation & Arkiv

- **6 visuelt kontrollerede 300-DPI PNG-figurer (`figN12_01`–`figN12_06`, forseglet i `VISUAL_REVIEW_N12.json`):** `32`-stjerners `BERV`-baser & G/K vs. M-dværg effektgrænser; `1.200`-forsøgs benchmark (`96,25 %` `T1` & `82,50 %` `T2` mod `0,00 %` klassisk stacking); `tau Cet` (`MAD σ = 0,00636`) vs. `GJ 887 / HD 217987` (`0,00855`) `LOEO`-residualer; `2.450 -> 650` formdiagnostik & Stage 3 veto inkl. ThAr (`525`) & live ESO; forenet `32`-stjerners tragt & Bayesiansk $f_{95}$ (`6,06 %` / `0,31 %`); samt Mælkevejens **Blind-Spot Quadrilogy (`N10 + N11A + N11B + N12`)**.
- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n12_scaled_harps.py`):** **`N12_SCALED_HARPS_AUDIT: 12/12 PASSED`** (`external_contacts == 0`).
- **Lokal arkivpakke:** `archives_n12/SETI_N12_SCALED_HARPS_TRANSIENT_LASER_COMB_2026-11-28.zip`.
