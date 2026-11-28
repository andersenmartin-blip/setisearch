# Spor N11B — Single-Epoch Transient Optisk Laser-SETI i *ESO HARPS* (`160` Spektre over `8` `< 11 pc` M-Dværge -> `0` ETI)

**Kampagne-ID:** `SPOR_N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER` · **Dato:** 28. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Mælkevejs-ETI · `N11B_HARPS_TRANSIENT_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Blind-Spot Gennembrud & Prospektiv Låsning

Standard echelle-SETI og RV-pipelines bygger statiske median-skabeloner eller lægger alle eksponeringer sammen — og bliver dermed **fundamentalt blinde over for sjældne eller enkeltstående optiske laser-blink**, fordi en enkelt epoke forsvinder fuldstændig i medianen (`0,00 %` genfinding på `400` real-støj injektioner). I **Spor N11B** angreb vi dette tidsdomæne-blinde punkt ved **Leave-One-Epoch-Out (`LOEO`)** differentielfiltrering og **`R = 115.000` HARPS PSF-matched filtering** (`4800,0–6900,0 Å` fotonrigt M-dværg-bånd, `0,01 Å/px`, CCD-hul `5299,5–5343,5 Å` maskeret) tværs over **`160` HARPS Phase-3 1D FITS-spektre** (`803,35 MiB`, `20` tid-stratificerede epoker pr. stjerne med spænd på `8,5–57,3 km/s` `BERV`) for **`8` `< 11 pc` Mælkevejs-exoplanetværter (`25` bekræftede exoplaneter):**
- `PROXIMACEN` (`1,30 pc`, `2` pl.), `BARNARDSSTAR` (`1,83 pc`, `4` pl.), `ROSS128` (`3,37 pc`, `1` pl.), `GJ1061` (`3,67 pc`, `3` pl.), `YZCET` (`3,72 pc`, `3` pl.), `GJ273` (`3,79 pc`, `2` pl.), `GJ667C` (`7,24 pc`, `5` pl.) og `L9859` (`10,62 pc`, `5` pl.).

- **Prospektiv blind låsning:** Scripts skrevet og forseglet **præ-FITS-hentning** (`sealed_utc = 2026-11-28T07:31:29.415476+00:00`, `pre_acquisition_blind_lock == True`); efter diagnosticeret NaN-randbeskyttelse og restriktion til `4800–6900 Å` med fysisk PSF-gulv (`0,80–1,50×` FWHM) genforseglet præ-kørsel kl. `2026-11-28T07:40:08.084813+00:00` (analysator SHA-256 **`7d132703f61ec2220dee1a0704c34d0b9f0cbdec3798498302251940072352e5`**).
- **1.200-Forsøgs Hoved-Mod-Hoved Benchmark på Rigtige HARPS-Spektre:**
  - **Single-Epoch PSF Optical Laser (`TRANSIENT_PSF_LASER`, `400` forsøg):** N11B `LOEO+PSF` = **`368/400` (`92,00 %`)** mod **`0/400` (`0,00 %`)** for klassisk 20-epoke median-stacking.
  - **Skarpe `1–2 px` Kosmiske Stråler (`COSMIC_RAY_1_2PX`, `400` forsøg):** **`0/400` (`0,00 %` FPR)**.
  - **Brede Kromosfæriske Flares (`BROAD_STELLAR_FLARE`, `2,6–5,5× PSF`, `400` forsøg):** **`0/400` (`0,00 %` FPR)**.
- **Stage 2 → Stage 3 Forensisk Veto (`463 -> 60 -> 0 ETI`) med Live ESO Arkiv-Opfølgning:**
  - Af `463` rå `Z_mf >= 10` toppe afviste Stage 2 automatisk `246` skarpe sub-PSF kosmiske stråler, `92` brede/forvrængede spidser og `65` vedvarende (`>3` epoker) linjer, hvilket sendte **`60` `T1`-transient-laserkandidater** til Stage 3.
  - Alle `60/60` blev afklaret fysikbaseret (**`0` verificerede optiske ETI**): **`30`** terrestrisk nattehimmel / tellurisk `O2-H2O` (`[O I] 5577/6300/6364`, `Na I D`, kryds-stjerne topocentrisk match), **`15`** ikke-gentagne kosmiske stråler direkte bekræftet forsvundet i næste ESO HARPS-eksponering (`0,18–23,9 t` senere, fx `ROSS128 5034,79 Å` `13,84σ -> 1,95σ` på `+20,5 min` & `1,66σ` på `+41 min`; `GJ1061 5248,13 Å` `13,42σ -> 0,88σ` på `+31,6 min`), **`6`** kromosfæriske M-dværg-flares (`Proxima Cen` `Hα=19,7× / Hβ=73,3×`), **`5`** solitære `1/20`-epoke kosmiske stråler uden arkiv-nabo inden for `±1,5 d`, samt **`4`** simultane Fiber-B `STAR,WAVE` kalibreringsgennemslag.
- **Fysiske Beamed Lasereffektgrænser (`D_tx = 10 m`, `10σ`) & Bayesianske $f_{95}$:**
  - **`0,1077–6,8696 kW`** (median **`0,45783 kW`**, heraf **`108 W`** på `Proxima Cen`, **`157 W`** på `GJ 1061` og **`363 W`** på `YZ Cet`).
  - **Stjerne-niveau (`N = 8` raw / `7,36` eff.):** Jeffreys $f_{95} = \mathbf{20{,}7508\,\%}$ (`22,2822 %` eff.) · Uniform `28,3129 %` (`30,1165 %` eff.).
  - **Enkelt-Epoke-niveau (`160` raw / `147,2` eff.):** Jeffreys $f_{95} = \mathbf{1{,}1914\,\%}$ (`1,2942 %` eff.) · Uniform `1,8435 %` (`2,0011 %` eff.).

---

## 2. Stjerneoversigt (`8` `< 11 pc` M-Dværge · `160` HARPS Epoker · `25` Exoplaneter)

| Stjerne | Navn | Afstand (`pc`) | Planeter | Epoker | Tidsspænd (`d`) | `BERV`-Spænd (`km/s`) | Median `SNR50` | `10σ` Beamed Eff. (`kW`) | `Z>=10` -> `T1` -> `ETI` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `PROXIMACEN` | Proxima Centauri | `1,302` | `2` | `20` | `3.974,3` | `41,82` | `25,6` | **`0,10770`** (`108 W`) | `113` -> `3` -> **`0`** |
| `BARNARDSSTAR` | Barnard's Star | `1,8282` | `4` | `20` | `6.696,6` | `52,76` | `75,8` | **`0,44858`** (`449 W`) | `28` -> `0` -> **`0`** |
| `ROSS128` | Ross 128 | `3,3749` | `1` | `20` | `5.471,9` | `46,65` | `42,1` | **`0,46708`** (`467 W`) | `44` -> `9` -> **`0`** |
| `GJ1061` | GJ 1061 | `3,6743` | `3` | `20` | `515,7` | `26,98` | `19,1` | **`0,15670`** (`157 W`) | `121` -> `22` -> **`0`** |
| `YZCET` | YZ Cet (GJ 54.1) | `3,7167` | `3` | `20` | `4.543,7` | `54,70` | `24,8` | **`0,36274`** (`363 W`) | `56` -> `16` -> **`0`** |
| `GJ273` | Luyten's Star | `3,7861` | `2` | `20` | `4.082,8` | `57,30` | `71,8` | **`1,14945`** | `26` -> `3` -> **`0`** |
| `GJ667C` | GJ 667 C | `7,2429` | `5` | `20` | `4.860,9` | `57,22` | `73,5` | **`6,86958`** | `29` -> `0` -> **`0`** |
| `L9859` | L 98-59 | `10,6194` | `5` | `20` | `1.910,9` | `8,52` | `30,6` | **`4,16722`** | `46` -> `7` -> **`0`** |

---

## 3. Figurer, Verifikation & Arkiv

- **6 visuelt kontrollerede 300-DPI PNG-figurer (`figN11B_01`–`figN11B_06`, forseglet i `VISUAL_REVIEW_N11B.json`):** HARPS BERV-baser & `0,11–6,87 kW` effektgrænser; `1.200`-forsøgs benchmark (`92,0 %` mod `0,0 %` statisk median); ægte `Proxima Cen TiO`-skov-subtraktion (`MAD σ = 0,0557`); `463` `Z>=10` formdiagnostik & Stage 3 veto-stave; veto-tragt + Bayesiansk $f_{95}$; samt samlet N10 + N11A + N11B Mælkevejs blind-spot syntese.
- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n11b_harps_transient.py`):** **`N11B_HARPS_TRANSIENT_AUDIT: 12/12 PASSED`** (`external_contacts == 0`).
- **Lokal arkivpakke:** `archives_n11b/SETI_N11B_HARPS_TRANSIENT_LASER_2026-11-28.zip`.
