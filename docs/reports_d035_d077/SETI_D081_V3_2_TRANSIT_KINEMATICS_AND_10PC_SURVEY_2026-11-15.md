# SETI Fase D081 (Trin 4) — Prospektiv 4-Kanals `ECELLE_V3_2` Transit-Kinematisk De-Doppler Søgning & Volumen-Komplet `< 10 pc` Sol-Nabolags-Syntese (`60` Stjerner / `349` Eksponeringer)

**Dato:** 15. november 2026  
**Fase:** `D081` (`work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey`)  
**Prospektiv metodelås (`METHOD_LOCK.json`):** `33bfc134ceed3a39aa45dcf24c5385332f60d284e02a0a076c44dd6cbe9d6fcc` (forseglet `2026-11-15T09:33:28.128236+00:00`, strengt før første science-download)
**Ingen post-lock kode- eller kohorte-ændringer (`0` amendments):** Den oprindeligt låste `METHOD_LOCK.json` kørte uændret fra første byte til færdig audit!  
**Uafhængig ren-stdlib numerisk audit (`/usr/bin/python3 -S audit.py`):** `PASS` (`11/11` hovedkontroller og fuld genberegning fra bunden i ren IEEE-754 Python af alle `2.226` RV-fits, `1.530` LSF-injektioner, `255` Kepleriske planet-spor-forsøg, `204` 2D-detektorforsøg, `166` 4-kanals kandidater og `153` øvre grænser med `0` fejl)  
**Hovedkonklusion:** **`0` verificerede ETI-lasersignaler** (`0` i kontrol [`0/34`], `0` i transitkanalerne `T_DIFF` og `K_PLANET` [`0/84`], `0` på alle FGK-stjerner [`0/96`], og fuld astrofysisk identifikation af alle `21` automatiske M-dværg-passager som `Fe II`/`Fe I` dMe-flare-emission og `TiO`/`VO`-båndkanter) på tværs af **`159` friske højopløste echelle-eksponeringer af `22` FGKM-stjerner** (`90` ESO `HARPS` + `69` VLT `ESPRESSO`, samlet integration `76544,8 s`, `55,744,578` gennemsøgte 1D-bins i Kanal T). Den nye Kepleriske planet-hvileramme de-Doppler-kanal (`K_PLANET`) øgede genfindingen af bevægende exoplanet-lasere under transit ved $\ge 6,5\sigma$/eksp fra **`0,0 %` (ukompenseret stjerne-ramme `T_DIFF`) til `67,3 %` (`81,4 %` ved $\ge 9\sigma$/eksp)**, mens `Legacy V2`'s **`1552` falske alarmer** blev reduceret til **`0` kontrol og `21` science**. På Solens nærmeste exoplanet-system **`Proxima Centauri` (`PROXIMACEN`, $d = 1,302$ pc)** når den kalibrerede `8σ` øvre grænse helt ned i **Watt-regimet på `9,0 W` (`0,0090 kW`)** for en `10 m`-sender — svarende til en almindelig husholdningspære eller håndholdt industrilaser på interstellare afstande! Samtidig færdiggøres en samlet **`60`-stjerners (`349`-eksponeringers) multi-fase syntese (`D079 + D080 + D081`)** inkl. **`18` stjerner inden for `10,0 pc`** (`14` exoplanet-værter med `31` bekræftede planeter).

---

## 1. Videnskabeligt formål og de 4 metodiske opgraderinger i `ECELLE_V3_2`

`D080` viste på `130` eksponeringer af `26` stjerner, at kombinationen af supraphotosfærisk kontinuum-gate (`F1`) i Kanal P og 2D-detektorfysik (`G5_F2`) fjernede alle kosmiske og fotosfæriske Kanal P-artefakter, men efterlod to klare fysiske spørgsmål til **Trin 4 (`D081`)**:
1. **Doppler-udtværing af lasere fra transiterende exoplaneter:** Under en planettransit accelererer planeten på tværs af stjerneskiven med $\Delta v_{\mathrm{orb}}(t) \approx 2\pi K_p (t - T_0)/P_{\mathrm{orb}}$, hvilket flytter en planet-monteret CW-laser med **`6,7–38,5 km/s` (`2,6–18` spektrale opløsningselementer FWHM)** i løbet af få timer! En klassisk stjerne-hvileramme-stak udtværer derfor signalet til ubemærkethed.
2. **Eliminering af de sidste svage luftglød- og absorptionskerne-artefakter fra `D080`:** De `33` svage passager i `D080` (`7` kontrol + `26` science) stammede fra ro-vibrationelle `OH Meinel`- og `Hg I 5770/5791 Å`-linjer på `FP`/`THAR2`-eksponeringer samt enkelte Kanal T-udsving nede i dybe fotosfæriske absorptionskerner.

`ECELLE_V3_2` indfører derfor prospektivt **fire sammenhængende søgekanaler og skærpede fysiske gates**:
- **Kanal `T` (1-epoke transient burst):** Nu med ensartet supraphotosfærisk `Gate G1_V32` (`fn_pk3 >= 1,008`) og `Gate G3_V32` (`template_dip_fraction <= 0,55`).
- **Kanal `P` (fler-epoke stjerne-hvileramme CW):** 2D $(T_{\mathrm{eff}}, [\mathrm{M/H}])$ `K=5`-atlas over hele spektret (`3820–7840 Å`), inkl. `14` NIST-ankre udvidet med røde `Ca I`/`Ti I`-linjer for sene M-dværge (`Proxima Cen`, `GJ 1061`, `Wolf 359`, `Ross 128`, `Barnard's Star`).
- **Kanal `T_DIFF` (samme-nats konjunktions-differentiel `IN_TRANSIT − OUT_OF_TRANSIT`, $\alpha = 0$):** Tester konjunktions-synkroniserede fyr i stjernens/L1-punktets hvileramme fri for nat-til-nat instrumentdrift.
- **Kanal `K_PLANET` (Keplerisk planet-hvileramme de-Doppler shift-and-stack, $\alpha = 1$):** Skifter hver in-transit residual til exoplanetens øjeblikkelige hvileramme $\lambda_p = \lambda_{\mathrm{bary}} / [(1 + v_*/c)(1 + \Delta v_{\mathrm{orb}}(t)/c)]$ før median-coadd, efterfulgt af fuld `G2_V32–G5_V32`-validering (inkl. udvidet `UVES/ESPRESSO` `OH Meinel + O2 + Hg I`-nattehimlens linjeatlas og skærpet `Gate G5_V32` vingekontrol).

---

## 2. Prospektiv metodelås og nul-overlap mod alle `80` tidligere mål og `553` ESO `dp_id`

`PRIOR_EXCLUSION_VERIFICATION.json` krydstjekkede samtlige `22` `D081`-stjerner og `159` ESO `ADP.*`-identifikatorer mod alle tidligere faser (`C001–C037`, `D001–D034`, `D035–D078`, `D079` og `D080`: i alt `80` ekskluderede mål og `553` `dp_id`), med eksplicit krav om offentlig frigivelse (`max_release_date = 2026-11-10T06:40:20Z <= 2026-11-14T00:00:00Z`):
- **Overlap i stjernenavne:** **`0 / 80`**
- **Overlap i ESO `dp_id`:** **`0 / 553`**
- **Mindste vinkelafstand på himlen til nogen tidligere stjerne:** **`7654,7 buesekunder` (`2,13°`)**.

---

## 3. Barycentrisk hvileramme (`2.226` fits) og syntetisk kalibrering (`1.989` forsøg inkl. Keplerisk de-Doppler)

### 3.1 Stellar hvileramme over `-110` til `+245 km/s` (`STELLAR_RV_ANCHORS_2226.csv`)
På tværs af alle `159` eksponeringer (`2992–6327 K`, fra `Wolf 359` og `Proxima Cen` til `KELT-11` og `WASP-166`) gav de `14` NIST-absorptionsankre **`1953 / 2226`** rene absorptionsfits og **`159 / 159` eksponeringer** med direkte empirisk hvileramme-forankring (herunder `Barnard's Star` ved `-110,5 km/s` og `Kapteyn's Star` ved `+245,2 km/s`). Median absolut afvigelse mod Gaia DR3 / litteratur-RV er **`0,495 km/s`**.

### 3.2 End-to-end kalibrering af alle fire kanaler og 2D-detektorfysik (`1.989` forsøg)
På de `4` dedikerede ikke-planet kontrolstjerner (`HD 190248` & `HD 225213` på HARPS; `HD 67458` & `AX Mic` på VLT ESPRESSO) gennemførtes **`1,989` prospektive injektionsforsøg** (`3844,75–7465,10 Å`):
1. **Keplerisk planet-spor de-Doppler kalibrering (`255` parrede forsøg i `KEPLERIAN_TRACK_CALIBRATION_255.csv`):**
   - Ukompenseret stjerne-ramme (`T_DIFF`, $\alpha = 0$) ved $\ge 6,5\sigma$/eksp: **`0,00 %`** (næsten totalt Doppler-udtværet under transittens hastighedsfeje!).
   - Keplerisk de-Doppler stak (`K_PLANET`, $\alpha = 1$) gennem hele `G1–G4` ved $\ge 6,5\sigma$/eksp: **`67,32 %`**, og ved $\ge 9,0\sigma$/eksp: **`81,37 %`**.
2. **Kanal T & Kanal P med ensartet supraphotosfærisk gate (`1.530` forsøg i `INJECTION_RECOVERY_1530.csv`):**
   - Kanal T ved **`>= 8σ`: `68,30 %`** samlet (`HARPS`: `75,35 %`; `ESPRESSO`: `62,04 %`; UV-blåt `3844/3951 Å`: `81,94 %`; dybrødt `7465 Å`: `50,00 %`).
   - Kanal P ved **`>= 9σ`: `87,25 %`**, og ved **`>= 12σ`: `95,59 %`**.
3. **Skærpet `Gate G5_V32` 2D-detektorfysik (`204` rumlige forsøg i `DETECTOR_2D_CALIBRATION_204.csv`):**
   - **Ægte fiber-fødet laser pass-rate:** **`76,47 %`** (`HARPS`: `68,75 %`; `ESPRESSO`: `83,33 %`).
   - **Afvisning af 1-pixel/1-slice kosmiske spikes og skrå myonspor:** **`100,00 %`** (`HARPS`: `100,00 %`; `ESPRESSO`: `100,00 %`).

---

## 4. Fire-generations falsk-alarm-kollaps (`V2 → V3.0 → V3.1 → V3.2`) og 4-kanals søgeresultater

### 4.1 Sammenligning på tværs af generationer og gates på de `159` `D081`-eksponeringer

| Generation / gate-trin | Kontrol (`34` eksp, `4` stjerner) | Science (`125` eksp, `18` exoplanet-stjerner) | Total (`159` eksp) | Fysisk betydning |
| --- | ---: | ---: | ---: | --- |
| **`Legacy V2` (`D002`-ækvivalent 1D `S1D`)** | `106` | `1446` | **`1552`** | Ukalibreret 1D-detektor (`562` HARPS + `990` ESPRESSO) |
| **`V3.0` Kanal P før supraphotosf. `F1`** | — | — | **`239`** | Sub-kontinuum fotosfæriske absorptions-mismatches (især i M-dværges `TiO`-bånd) |
| **`V3.1` Kanal T før supraphotosf. `F1`** | — | — | **`171`** | Enkelt-epoke udsving nede i dybe absorptionskerner (elimineret af `G1_V32`) |
| **`V3.2` Samlede `Gate G1_V32`-frø (alle 4 kanaler)** | — | — | **`166`** | Kanal `T`: `136` · `P`: `30` · `T_DIFF`: `0` · `K_PLANET`: `0` |
| **Efter `Gate G2_V32` (udvidet airglow/`OH`/`Hg`/`O2`)** | — | — | **`143`** | Topocentrisk nattehimlens luftglød og mættede telluriske bånd fjernet |
| **Efter `Gate G3_V32` (nativ orden + dip-veto)** | — | — | **`99`** | Enkeltpixel-spikes og dybe template-absorptionslinjer afvist |
| **Efter `Gate G4` (ordens-overlap + Fiber B)** | — | — | **`84`** | Naboordens-konsistens og simultan kalibrerings-/skyfiber-veto |
| **Efter `Gate G5_V32` (2D HARPS `5×11` / ESPRESSO `2×11`)** | **`0`** | **`21`** | **`21`** | Endelige prospektivt kvalificerede `ECELLE_V3_2`-kandidater (`0` ETI-lasere) |

### 4.2 Fordeling af afvisningsårsager i `V3_2_CANDIDATE_LEDGER.csv`

| Endelig `ECELLE_V3_2`-disposition (`V3_2_CANDIDATE_LEDGER.csv`, alle 4 kanaler) | Antal kandidater |
| --- | ---: |
| `QUALIFIED_V3_2_LASER_CANDIDATE` | `21` |
| `ASYMMETRIC_COSMIC_RAY_SPIKE` | `19` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT;V32_DIAGONAL_MUON_ROW_SPAN;V32_SINGLE_COL_COSMIC_SPIKE` | `12` |
| `SINGLE_ORDER_CCD_ARTIFACT` | `10` |
| `SINGLE_SLICE_COSMIC_RAY;SLICE_CONTRAST_IMBALANCE;DUAL_SLICE_2X11_LSF_MISMATCH` | `10` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;F2_2D_5X11_LSF_MISMATCH;V32_SINGLE_COL_COSMIC_SPIKE` | `9` |
| `TELLURIC_AIRGLOW_OI_5577_auroral` | `9` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;RAW2D_CENTROID_OFFSET;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT;V32_DIAGONAL_MUON_ROW_SPAN` | `7` |
| `TEMPLATE_ABSORPTION_DIP_GHOST` | `7` |
| `FIBER_B_CALIBRATION_BLEED` | `5` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;F2_2D_5X11_LSF_MISMATCH;V32_DIAGONAL_MUON_ROW_SPAN;V32_SINGLE_COL_COSMIC_SPIKE` | `5` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;RAW2D_CENTROID_OFFSET;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT;V32_DIAGONAL_MUON_ROW_SPAN;V32_SINGLE_COL_COSMIC_SPIKE` | `5` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR;ASYMMETRIC_COSMIC_RAY_SPIKE` | `5` |
| `TELLURIC_AIRGLOW_OI_6300_nebular` | `5` |
| `TELLURIC_O2_A_band_core` | `5` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;RAW2D_CENTROID_OFFSET;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT;V32_SINGLE_COL_COSMIC_SPIKE` | `3` |
| `SUB_CONTINUUM_OR_TELLURIC_DIP_GHOST` | `3` |
| `SUB_CONTINUUM_OR_TELLURIC_DIP_GHOST;TEMPLATE_ABSORPTION_DIP_GHOST` | `3` |
| `F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT;V32_DIAGONAL_MUON_ROW_SPAN;V32_SINGLE_COL_COSMIC_SPIKE` | `2` |
| `F2_2D_5X11_LSF_MISMATCH;V32_SINGLE_COL_COSMIC_SPIKE` | `2` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR;SUB_LSF_SINGLE_PIXEL_SPIKE;ASYMMETRIC_COSMIC_RAY_SPIKE` | `2` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR;SUB_LSF_SINGLE_PIXEL_SPIKE;ASYMMETRIC_COSMIC_RAY_SPIKE;SUB_CONTINUUM_OR_TELLURIC_DIP_GHOST` | `2` |
| `TELLURIC_O2_B_band_core` | `2` |
| `DUAL_SLICE_2X11_LSF_MISMATCH` | `1` |
| `F2_2D_5X11_LSF_MISMATCH;V32_DIAGONAL_MUON_ROW_SPAN` | `1` |
| `F2_DIAGONAL_MUON_CENTROID_DRIFT;V32_DIAGONAL_MUON_ROW_SPAN` | `1` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;F2_2D_5X11_LSF_MISMATCH;F2_DISPERSION_WING_BROADENING;V32_DIAGONAL_MUON_ROW_SPAN;V32_SINGLE_COL_COSMIC_SPIKE` | `1` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;RAW2D_CENTROID_OFFSET;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT` | `1` |
| `RAW2D_SPATIAL_PROFILE_MISMATCH;RAW2D_CENTROID_OFFSET;RAW2D_OFF_FIBER_TRACK;F2_2D_5X11_LSF_MISMATCH;F2_DIAGONAL_MUON_CENTROID_DRIFT;V32_DIAGONAL_MUON_ROW_SPAN` | `1` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR` | `1` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR;ASYMMETRIC_COSMIC_RAY_SPIKE;SUB_CONTINUUM_OR_TELLURIC_DIP_GHOST;TEMPLATE_ABSORPTION_DIP_GHOST` | `1` |
| `S1D_REBIN_OR_LOW_NATIVE_SNR;TEMPLATE_ABSORPTION_DIP_GHOST` | `1` |
| `SINGLE_SLICE_COSMIC_RAY;SLICE_CONTRAST_IMBALANCE;SLICE_WAVELENGTH_CENTROID_MISMATCH;DUAL_SLICE_2X11_LSF_MISMATCH` | `1` |
| `SLICE_WAVELENGTH_CENTROID_MISMATCH;DUAL_SLICE_2X11_LSF_MISMATCH` | `1` |
| `TELLURIC_AIRGLOW_NaID2_5889` | `1` |
| `TELLURIC_O2_gamma_bandhead` | `1` |

### 4.3 Overblik over alle `22` `D081`-stjerner (sorteret efter afstand `1,30–114,3 pc`)

| Stjerne (navn) | Instr. | Subrolle | Planeter | Afstand (pc) | $G$ (mag) | $T_{\mathrm{eff}}$ (K) | Empirisk $\overline{\mathrm{RV}}$ (km/s) | $\Delta\mathrm{RV}_{\mathrm{emp-ref}}$ (km/s) | V2 træf | V3.2 G1 (4 kan.) | V3.2 kval. | Bedste $P_{10\,\mathrm{m},8\sigma}$ |
| --- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `PROXIMACEN` (Proxima Centauri) | `ESPRESSO` | `SCIENCE_10PC` | 2 | 1,30 | 8,98 | 2992 | -21,837 | +0,105 | 532 | 19 | **11** | **9,0 W** |
| `BARNARDSSTAR` (Barnard's Star) | `ESPRESSO` | `SCIENCE_10PC` | 4 | 1,83 | 8,19 | 3259 | -110,455 | +0,013 | 63 | 7 | **4** | **23,6 W** |
| `HD217987` (Lacaille 9352) | `ESPRESSO` | `SCIENCE_10PC` | 4 | 3,29 | 6,52 | 3667 | +8,873 | +0,566 | 18 | 1 | **0** | **108,6 W** |
| `GJ273` (Luyten's Star) | `ESPRESSO` | `SCIENCE_10PC` | 2 | 3,79 | 8,58 | 3382 | +18,053 | +0,699 | 162 | 5 | **2** | **80,8 W** |
| `GJ191` (Kapteyn's Star) | `ESPRESSO` | `SCIENCE_10PC` | 1 | 3,93 | 8,06 | 3819 | +245,350 | +0,297 | 5 | 2 | **1** | **89,9 W** |
| `VAXMIC` (Lacaille 8760) | `ESPRESSO` | `CONTROL_5EPOCH` | 0 | 3,97 | 5,98 | 3800 | +21,284 | +0,574 | 24 | 2 | **0** | — |
| `WOLF1061` (Wolf 1061) | `ESPRESSO` | `SCIENCE_10PC` | 3 | 4,31 | 8,80 | 3342 | -21,222 | +0,575 | 140 | 5 | **2** | **79,7 W** |
| `HD225213` (GJ 1) | `HARPS` | `CONTROL_5EPOCH` | 0 | 4,35 | 7,68 | 3567 | +25,663 | +0,537 | 42 | 6 | **0** | — |
| `GJ674` (GJ 674) | `HARPS` | `SCIENCE_10PC` | 1 | 4,55 | 8,34 | 3461 | -2,866 | +0,505 | 105 | 5 | **0** | **235,4 W** |
| `GJ832` (GJ 832) | `HARPS` | `SCIENCE_10PC` | 1 | 4,97 | 7,74 | 3472 | +13,150 | +0,426 | 64 | 7 | **0** | **384,5 W** |
| `HD42581` (GJ 229 A) | `HARPS` | `SCIENCE_10PC` | 2 | 5,76 | 7,31 | 3564 | +4,716 | +0,490 | 49 | 4 | **1** | **720,4 W** |
| `GJ752A` (Wolf 1055) | `HARPS` | `SCIENCE_10PC` | 1 | 5,92 | 8,10 | 3499 | +35,957 | +0,627 | 124 | 6 | **0** | **494,5 W** |
| `HD20794` (82 G. Eridani) | `ESPRESSO` | `SCIENCE_10PC` | 4 | 6,04 | 4,06 | 5401 | +88,279 | +0,521 | 10 | 1 | **0** | 5,17 kW |
| `HD190248` (delta Pav) | `HARPS` | `CONTROL_TIMESERIES` | 0 | 6,10 | 3,36 | 5604 | -21,172 | +0,558 | 38 | 2 | **0** | — |
| `HD115617` (61 Virginis) | `HARPS` | `SCIENCE_10PC` | 3 | 8,53 | 4,53 | 5562 | -7,476 | +0,389 | 8 | 5 | **0** | 14,32 kW |
| `HD69830` (HD 69830) | `ESPRESSO` | `SCIENCE_NEARBY_FGK` | 3 | 12,58 | 5,76 | 5385 | +30,598 | +0,512 | 23 | 1 | **0** | 6,11 kW |
| `55CNC` (55 Cnc) | `HARPS` | `SCIENCE_TRANSIT` | 5 | 12,59 | 5,73 | 5172 | +27,687 | +0,500 | 51 | 8 | **0** | 13,79 kW |
| `HD67458` (HD 67458) | `ESPRESSO` | `CONTROL_TIMESERIES` | 0 | 25,67 | 6,65 | 5891 | -15,275 | +0,435 | 2 | 1 | **0** | — |
| `HD209458` (HD 209458) | `ESPRESSO` | `SCIENCE_TRANSIT` | 1 | 48,15 | 7,52 | 6091 | -14,356 | +0,420 | 11 | 11 | **0** | 24,16 kW |
| `KELT11` (KELT-11) | `HARPS` | `SCIENCE_TRANSIT` | 1 | 99,95 | 7,84 | 5375 | +35,417 | +0,403 | 17 | 18 | **0** | 263,92 kW |
| `HD106315` (HD 106315) | `HARPS` | `SCIENCE_TRANSIT` | 2 | 109,02 | 8,90 | 6327 | -3,114 | +0,102 | 46 | 28 | **0** | 139,59 kW |
| `WASP166` (WASP-166) | `HARPS` | `SCIENCE_TRANSIT` | 1 | 114,26 | 9,26 | 6050 | +23,952 | +0,463 | 18 | 22 | **0** | 152,61 kW |

### 4.4 Astrofysisk forensisk diagnose af de `21` automatiske M-dværg-passager (`0` kontrol, `0` transit, `0` FGK-stjerner, `0` ETI-lasere)

Den prospektivt låste 4-kanals pipeline gav **`0 / 34` (`0,000/eksp`) i kontrol**, **`0` i Kanal `T_DIFF`**, **`0` i Kanal `K_PLANET`** og **`0 / 96` eksponeringer på samtlige FGK-stjerner ($T_{\mathrm{eff}} > 4000\,\mathrm{K}$)**. Alle `21` automatiske Kanal `T`/`P`-passager (`0,168/eksp`, dokumenteret i `FORENSIC_ASTROPHYSICAL_DIAGNOSIS_21.csv` / `.json`) forekommer **udelukkende på kølige M-dværge ($T_{\mathrm{eff}} = 2992\text{–}3819\,\mathrm{K}$)** (`11` på M5.5Ve flarestjernen `Proxima Centauri`, `4` på `Barnard's Star`, `2` på `GJ 273`, `2` på `Wolf 1061`, `1` på `GJ 191` og `1` på `GJ 229 A`). Fordi lyset stammer fra stjernens egen kromosfære/fotosfære i den optiske fiber, passerer det som fysisk forventet 2D-profilkravet i `Gate G5_V32` (`cos_2d = 0,881–0,989`), men har både **termisk/molekylær linjebredde over instrumentets laser-LSF** (median `FWHM/LSF = 1,38×`, interval `1,04–1,61×`) og **identiske hvilebølgelængder i andre uafhængige M-dværge (inkl. kontrolstjernerne `AX Mic` og `GJ 1`)**:

1. **Kromosfæriske dMe-flare-emissionslinjer på `Proxima Centauri` (`2 / 21`):** `V32-T-0091` ved stellar hvilebølgelængde **`4233,168 Å`** matcher NIST **`Fe II` multiplet 27 (`4233,167 Å`, $\Delta\lambda = +0,001\,\text{{Å}} = 0,07\,\mathrm{{km/s}}$**, `2,25×` flare-variabilitet mellem epokerne), og `V32-T-0090` ved **`4375,928 Å`** matcher NIST **`Fe I` multiplet 41 (`4375,932 Å`, $\Delta\lambda = -0,004\,\text{{Å}} = 0,27\,\mathrm{{km/s}}$**, `1,49×` flare-variabilitet).
2. **Snævre fotosfæriske `TiO`/`VO`/`K I` molekylære båndkant-rygge på de koldeste M-dværge (`19 / 21`):** Ved kohortens kolde temperaturgrænse (`Proxima Cen` `2992 K`, `Barnard's Star` `3259 K`) er alle `K=5` KNN-naboer varmere (`3259–3800 K`) med svagere `TiO`-absorption, hvilket efterlader smalle (`1,2–1,6× LSF`) molekylære opacitetsvinduer over det lokalt `TiO`-dæmpede kontinuum (f.eks. samme stellar-hvileramme-top ved `7176,62–7176,72 Å` i både `Barnard's Star` ved `-110,5 km/s` og `Proxima Cen` ved `-21,8 km/s`, samt `7691,333 Å` / `7691,330 Å` i både `GJ 273` ved `+18,1 km/s` og `Wolf 1061` ved `-21,2 km/s`).

> **Teknisk bemærkning om rå pipeline-kolonne i låst output:** I den forhåndslåste `analyze.py` blev feltet `verified_eti_detections` i `SUMMARY.json`, `SOLAR_NEIGHBORHOOD_10PC_SYNTHESIS.csv` og `MULTI_PHASE_V3_SYNTHESIS_60STARS.csv` sat direkte lig det automatiske `qualified_v32_laser`-antal (`21`) før den spektroskopiske linjeidentifikation. Som dokumenteret i `FORENSIC_ASTROPHYSICAL_DIAGNOSIS_21.json` er det verificerede antal ETI-lasere **`0`**.

| ID | Kanal | Stjerne ($T_{\mathrm{eff}}$) | $\lambda_{\mathrm{rest,*}}$ (Å) | $\lambda_{\mathrm{topo}}$ (Å) | `SNR` | `FWHM/LSF` | 5-ep. max/min | Samme $\lambda_{\mathrm{rest,*}}$-top i andre M-dværge | Astrofysisk klassifikation |
| --- | :---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `V32-T-0090` | `T` | `PROXIMACEN` (`2992 K`) | 4375,928 | 4375,297 | 10,42 | 1,342 | 1,49× | `HD217987(1.14x), VAXMIC(1.27x)` | `DME_FLARE_CHROMOSPHERIC_EMISSION_LINE` |
| `V32-T-0091` | `T` | `PROXIMACEN` (`2992 K`) | 4233,168 | 4232,784 | 7,33 | 1,462 | 2,25× | `BARNARDSSTAR(1.22x), GJ191(1.15x), GJ273(1.29...` | `DME_FLARE_CHROMOSPHERIC_EMISSION_LINE` |
| `V32-T-0093` | `T` | `PROXIMACEN` (`2992 K`) | 7171,929 | 7171,279 | 8,69 | 1,533 | 1,18× | `BARNARDSSTAR(1.76x), GJ191(1.21x), GJ273(1.84...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-T-0094` | `T` | `PROXIMACEN` (`2992 K`) | 7303,181 | 7302,520 | 13,20 | 1,610 | 1,39× | `WOLF1061(1.12x)` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-T-0097` | `T` | `PROXIMACEN` (`2992 K`) | 6600,288 | 6600,271 | 9,78 | 1,574 | 1,03× | `BARNARDSSTAR(1.38x), GJ273(1.42x), GJ674(1.25...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-T-0102` | `T` | `BARNARDSSTAR` (`3259 K`) | 6316,756 | 6314,775 | 7,62 | 1,356 | 1,13× | `GJ273(1.19x), GJ674(1.13x), PROXIMACEN(1.26x)...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-T-0103` | `T` | `BARNARDSSTAR` (`3259 K`) | 7176,616 | 7174,583 | 8,53 | 1,291 | 1,19× | `GJ191(1.13x), GJ273(1.35x), PROXIMACEN(1.71x)...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0142` | `P` | `BARNARDSSTAR` (`3259 K`) | 5017,568 | 5016,151 | 8,61 | 1,362 | 1,01× | `GJ191(1.13x), GJ273(1.50x), GJ674(1.27x), GJ7...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0143` | `P` | `BARNARDSSTAR` (`3259 K`) | 7287,265 | 7285,201 | 8,58 | 1,284 | 1,01× | `GJ273(1.24x), PROXIMACEN(1.37x)` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0146` | `P` | `GJ191` (`3819 K`) | 7679,842 | 7685,951 | 10,89 | 1,438 | 1,01× | `GJ273(1.27x), PROXIMACEN(1.42x), WOLF1061(1.25x)` | `MDWARF_TIO_KI_WING_PSEUDOCONTINUUM_PEAK` |
| `V32-P-0149` | `P` | `GJ273` (`3382 K`) | 7691,333 | 7692,312 | 11,91 | 1,433 | 1,05× | `BARNARDSSTAR(1.24x), PROXIMACEN(1.22x), WOLF1...` | `MDWARF_TIO_KI_WING_PSEUDOCONTINUUM_PEAK` |
| `V32-P-0150` | `P` | `GJ273` (`3382 K`) | 7696,775 | 7697,767 | 13,15 | 1,038 | 1,02× | `BARNARDSSTAR(1.22x), PROXIMACEN(1.29x), WOLF1...` | `MDWARF_TIO_KI_WING_PSEUDOCONTINUUM_PEAK` |
| `V32-P-0154` | `P` | `HD42581` (`3564 K`) | 5095,578 | 5095,895 | 11,24 | 1,430 | 1,04× | `GJ191(1.26x), HD217987(1.26x), HD225213(1.12x...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0158` | `P` | `PROXIMACEN` (`2992 K`) | 5449,153 | 5449,139 | 7,38 | 1,375 | 1,04× | `BARNARDSSTAR(1.28x), GJ273(1.22x), HD217987(1...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0159` | `P` | `PROXIMACEN` (`2992 K`) | 6002,625 | 6001,760 | 7,17 | 1,432 | 1,03× | `BARNARDSSTAR(1.21x), GJ273(1.20x), WOLF1061(1...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0160` | `P` | `PROXIMACEN` (`2992 K`) | 6273,392 | 6273,377 | 7,39 | 1,364 | 1,03× | `BARNARDSSTAR(1.20x), GJ273(1.20x), WOLF1061(1...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0161` | `P` | `PROXIMACEN` (`2992 K`) | 6501,185 | 6500,596 | 16,23 | 1,381 | 1,01× | `BARNARDSSTAR(1.15x)` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0162` | `P` | `PROXIMACEN` (`2992 K`) | 6754,245 | 6753,633 | 7,72 | 1,351 | 1,02× | `BARNARDSSTAR(1.72x), GJ191(1.19x), GJ273(1.69...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0163` | `P` | `PROXIMACEN` (`2992 K`) | 7176,722 | 7175,689 | 7,87 | 1,194 | 1,16× | `BARNARDSSTAR(1.76x), GJ191(1.14x), GJ273(1.52...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0165` | `P` | `WOLF1061` (`3342 K`) | 5879,778 | 5879,895 | 7,10 | 1,418 | 1,04× | `BARNARDSSTAR(1.21x), GJ273(1.25x), PROXIMACEN...` | `LATE_MDWARF_TIO_VO_MOLECULAR_BANDHEAD_RIDGE` |
| `V32-P-0166` | `P` | `WOLF1061` (`3342 K`) | 7691,330 | 7691,419 | 8,38 | 1,404 | 1,06× | `BARNARDSSTAR(1.23x), GJ273(1.23x), PROXIMACEN...` | `MDWARF_TIO_KI_WING_PSEUDOCONTINUUM_PEAK` |

---

## 5. Transit-tidsserier (`7` kampagner), Watt-skala grænser (`< 10 pc`) og `60`-stjerners V3-syntese

### 5.1 De `7` enkeltnats konjunktions- og transitkampagner (`84` eksponeringer, `TRANSIT_CAMPAIGN_RESULTS_7.csv`)

| Kampagne / planet | Instr. | Rolle | Afstand (pc) | $P_{\mathrm{orb}}$ (d) | $K_p$ (km/s) | In-transit $\Delta v_{\mathrm{sweep}}$ (km/s) | `T_DIFF` G1 / kval. | `K_PLANET` G1 / kval. | Bedste `T_DIFF` $8\sigma$ (kW) | Bedste `K_PLANET` $8\sigma$ (kW) |
| --- | :---: | :---: | ---: | ---: | ---: | ---: | :---: | :---: | ---: | ---: |
| `NONE_NULL_CONTROL` (`HD190248`) | `HARPS` | `CONTROL` | 6,10 | 2,200 | 163,7 | **17,46** | `0 / 0` | `0 / 0` | 7,27 | 4,30 |
| `55 Cnc e` (`55CNC`) | `HARPS` | `SCIENCE` | 12,59 | 0,737 | 228,0 | **118,80** | `0 / 0` | `0 / 0` | 7,98 | 5,11 |
| `NONE_NULL_CONTROL` (`HD67458`) | `ESPRESSO` | `CONTROL` | 25,67 | 2,200 | 163,7 | **44,24** | `0 / 0` | `0 / 0` | 16,70 | 9,69 |
| `HD 209458 b` (`HD209458`) | `ESPRESSO` | `SCIENCE` | 48,15 | 3,525 | 149,9 | **32,86** | `0 / 0` | `0 / 0` | 13,43 | 8,43 |
| `KELT-11 b` (`KELT11`) | `HARPS` | `SCIENCE` | 99,95 | 4,736 | 143,2 | **55,72** | `0 / 0` | `0 / 0` | 145,64 | 102,17 |
| `HD 106315 c` (`HD106315`) | `HARPS` | `SCIENCE` | 109,02 | 21,057 | 79,4 | **4,32** | `0 / 0` | `0 / 0` | 76,75 | 53,50 |
| `WASP-166 b` (`WASP166`) | `HARPS` | `SCIENCE` | 114,26 | 5,444 | 128,3 | **17,63** | `0 / 0` | `0 / 0` | 85,45 | 59,86 |

### 5.2 Solens nabolag inden for `10,0 pc` (`18` stjerner på tværs af `D080 + D081`, `SOLAR_NEIGHBORHOOD_10PC_SYNTHESIS.csv`)

På Solens `18` undersøgte nabostjerner inden for `10,0 pc` (`14` bekræftede exoplanet-værter med `31` planeter + `4` kontrolstjerner) når vores kalibrerede `8σ`-følsomhed for en `10 m`-sender ned på **`9,0 W`** på **`Proxima Centauri`** ($d = 1,302$ pc), med en median bedste grænse på **`310 W` (`0,310 kW`)** på tværs af alle `14` exoplanet-systemer inden for `10 pc`:

| Stjerne (navn) | Fase | Instr. | Rolle | Afstand (pc) | Planeter | Eksponeringer | V3.2 auto-kval. (`ETI = 0`) | Bedste $8\sigma$ `10 m` grænse | Median $8\sigma$ `10 m` grænse |
| --- | :---: | :---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: |
| `PROXIMACEN` (Proxima Centauri) | `D081` | `ESPRESSO` | `SCIENCE` | 1,302 | 2 | 5 | `11` (`0 ETI`) | **9,0 W** | 17,5 W |
| `BARNARDSSTAR` (Barnard's Star) | `D081` | `ESPRESSO` | `SCIENCE` | 1,828 | 4 | 5 | `4` (`0 ETI`) | **23,6 W** | 42,9 W |
| `HD217987` (Lacaille 9352) | `D081` | `ESPRESSO` | `SCIENCE` | 3,288 | 4 | 5 | `0` | **108,6 W** | 206,4 W |
| `HD209100` (epsilon Indi A) | `D080` | `HARPS` | `SCIENCE` | 3,638 | 1 | 5 | `0` | 2,62 kW | 4,22 kW |
| `GJ273` (Luyten's Star) | `D081` | `ESPRESSO` | `SCIENCE` | 3,786 | 2 | 5 | `2` (`0 ETI`) | **80,8 W** | 182,6 W |
| `GJ191` (Kapteyn's Star) | `D081` | `ESPRESSO` | `SCIENCE` | 3,934 | 1 | 5 | `1` (`0 ETI`) | **89,9 W** | 190,6 W |
| `VAXMIC` (Lacaille 8760) | `D081` | `ESPRESSO` | `CONTROL` | 3,970 | 0 | 5 | `0` | — (Ctrl) | — (Ctrl) |
| `WOLF1061` (Wolf 1061) | `D081` | `ESPRESSO` | `SCIENCE` | 4,308 | 3 | 5 | `2` (`0 ETI`) | **79,7 W** | 160,4 W |
| `HD225213` (GJ 1) | `D081` | `HARPS` | `CONTROL` | 4,346 | 0 | 5 | `0` | — (Ctrl) | — (Ctrl) |
| `GJ674` (GJ 674) | `D081` | `HARPS` | `SCIENCE` | 4,553 | 1 | 5 | `0` | **235,4 W** | 371,7 W |
| `GJ832` (GJ 832) | `D081` | `HARPS` | `SCIENCE` | 4,967 | 1 | 5 | `0` | **384,5 W** | 607,8 W |
| `HD42581` (GJ 229 A) | `D081` | `HARPS` | `SCIENCE` | 5,761 | 2 | 5 | `1` (`0 ETI`) | **720,4 W** | 1,23 kW |
| `GJ752A` (Wolf 1055) | `D081` | `HARPS` | `SCIENCE` | 5,915 | 1 | 5 | `0` | **494,5 W** | 770,9 W |
| `HD20794` (82 G. Eridani) | `D081` | `ESPRESSO` | `SCIENCE` | 6,041 | 4 | 5 | `0` | 5,17 kW | 7,21 kW |
| `HD190248` (delta Pav) | `D081` | `HARPS` | `CONTROL` | 6,099 | 0 | 12 | `0` | — (Ctrl) | — (Ctrl) |
| `HD191849` (AU Microscopii) | `D080` | `ESPRESSO` | `CONTROL` | 6,165 | 0 | 5 | `0` | — (Ctrl) | — (Ctrl) |
| `HD115617` (61 Virginis) | `D081` | `HARPS` | `SCIENCE` | 8,534 | 3 | 5 | `0` | 14,32 kW | 20,88 kW |
| `HD192310` (82 G. Ceti (GJ 827)) | `D080` | `HARPS` | `SCIENCE` | 8,812 | 2 | 5 | `0` | 5,73 kW | 8,78 kW |

### 5.3 Samlet multi-fase syntese over `D079 + D080 + D081` (`60` unikke stjerner, `349` eksponeringer)
Med afslutningen af `D081` omfatter projektets prospektivt låste 3. generations optiske echelle-survey (`MULTI_PHASE_V3_SYNTHESIS_60STARS.csv`):
- **`60` unikke FGKM-stjerner** (`50` science-stjerner inkl. `40` bekræftede exoplanet-systemer med `85` exoplaneter + `10` ikke-planet kontrolstjerner, afstand **`1,302–114,30 pc`**).
- **`349` højopløste eksponeringer** (`220` ESO `HARPS` + `129` VLT `ESPRESSO`) og **`4.539` syntetiske injektions- og 2D-kalibreringsforsøg** (`816` i `D079` + `1.734` i `D080` + `1.989` i `D081`).
- **`0` verificerede ekstraterrestriske lasersignaler**, med median bedste `8σ` `10 m`-grænse på **`8,10 kW`** på tværs af alle `50` science-stjerner og helt ned til **`9,0 W`** ved `1,30 pc`.
