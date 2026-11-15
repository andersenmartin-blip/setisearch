# SETIsearch — Reproducerbar arkivbaseret teknosignaturforskning

*English summary: Open, prospectively locked archival technosignature research by Martin Andersen (MSc Astrophysics, University of Copenhagen), spanning high-resolution optical echelle spectroscopy (ESO HARPS, VLT ESPRESSO & FEROS), multi-epoch narrowband radio de-Doppler searches (`seti-repeater`), and TESS fast-photometry qualification. Across all tracks — including the completed 60-star (`349`-exposure) optical `V3.0–V3.2` survey down to **9,0 W** on Proxima Centauri — **0 qualified technosignature detections** are claimed; every negative branch, instrumental artifact diagnosis, and pure-stdlib numerical audit is preserved.*

---

## Aktuel status (15. november 2026)

> **Samlet detektionsstatus: `0` kvalificerede teknosignaturer (optisk og radio).**
> - **Aktivt hovedspor:** Optisk højopløsningsspektroskopi (`HARPS` $R \approx 115\,000$, VLT `ESPRESSO` $R \approx 140\,000$ og `FEROS` $R \approx 48\,000$) gennem afsluttet checkpoint **[`D081` (Trin 4 — 4-kanals `ECELLE_V3_2` transit-kinematik & `< 10 pc` sol-nabolags-survey)](progress/2026-11-15-echelle-d081-v3-2/REPORT.md)** over **`159` friske eksponeringer af `22` FGKM-stjerner** (`90` HARPS + `69` VLT ESPRESSO; `18` exoplanet-værter med `41` planeter ved `1,30–114,3 pc`, inkl. `5` komplette transit-nætter og `12` exoplanet-systemer inden for `10 pc` + `4` kontrolstjerner): **`0` verificerede ETI-lasere**, med Keplerisk planet-hvileramme de-Doppler-genfinding øget fra `0,0 %` til **`67,3 %`** ved $\ge 6,5\sigma$/eksp og `8σ`-øvre grænser helt ned til **`9,0 W` (`0,0090 kW`)** på `Proxima Centauri` (`10 m`-sender).
> - **Samlet multi-fase `V3`-syntese (`D079 + D080 + D081`):** **`60` unikke stjerner og `349` eksponeringer** (`18` stjerner inden for `10,0 pc`, `4.539` syntetiske kalibreringsforsøg, **`0` ETI-lasere**).
> - **Start her for fortsættelse:** [**`CONTINUE_SETI.md`**](CONTINUE_SETI.md) · [**`V3.0–V3.2`-survey-indeks (`D079–D081`)**](docs/OPTICAL_V3_SURVEY_INDEX.md) · [**Historisk indeks (`D001`–`D078`)**](docs/OPTICAL_HD43629_INDEX.md) · [**Mappeoversigt**](docs/PROJECT_MAP.md).

---

## Oversigt over projektets fire forskningsspor

| Forskningsspor | Data & omfang | Vigtigste gennemførte arbejde og fund | Status & indgang |
| --- | --- | --- | --- |
| **1A. Optisk Echelle-SETI — Kalibreret `V3.0–V3.2`-survey (`D079–D081`)** | `349` friske eksponeringer (`220` HARPS + `129` VLT ESPRESSO på `60` unikke FGKM-stjerner ved `1,30–114,3 pc`, `0` overlap mod `C001–D078`) | `D079` (`V3.0`, `60` eksp) + `D080` (`V3.1`, `130` eksp) + `D081` (`ECELLE_V3_2`, `159` eksp, 4 kanaler `T`/`P`/`T_DIFF`/`K_PLANET`, `67,3 %` Keplerisk planet-spor genfinding, `100,0 %` 2D kosmisk afvisning → **`0` ETI-lasere**, `8σ`-grænse ned til **`9,0 W`** på `Proxima Centauri`). | **`D081` afsluttet (`60`-stjerners syntese)** · [`V3`-indeks](docs/OPTICAL_V3_SURVEY_INDEX.md) · [`D081`-rapport](docs/reports_d035_d077/SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_SURVEY_2026-11-15.md) |
| **1B. Optisk Echelle-SETI — `C001–D078` & `HD 43629` (`HARPS` & `FEROS`)** | `300 + 50` HARPS-eksponeringer (`20 + 10` stjerner) + `5` FEROS-epoker + `30` WLC-kalibreringer | Lukning af `90`-køen ([`C037`](work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md), [`D001`](work_seti_20261105_d001_delivery/README.md)), `141` `D002`-træf og fuld HARPS COMB/2D + FEROS stellar hvileramme-syntese for `HD 43629` (`+33,820 ± 0,216 km/s`; `0` kvalificerede lasere). | **Lukket rent (`D078`)** · [Historisk optisk indeks](docs/OPTICAL_HD43629_INDEX.md) |
| **2. Smalbåndet Radio-SETI (`seti-repeater`)** | GBT / Breakthrough Listen arkivsekvenser (`M8`–`M43AI`, `BA`–`CB`) | Multi-epoke de-Doppler-søgning under exoplanet-drifthypoteser med ON/OFF-veto (`M43AF` `502`-optagelsesstudie, `M43AI`, `HIP 44295`, `HIP 35136`, `M33 / HD 3651`). | **På pause** · [Arkiveret log](docs/history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) · [`src/seti_repeater/`](src/seti_repeater/__init__.py) |
| **3. Light-Sail & TESS-fotometri (`LS1`–`LS7E`)** | TESS pixeldata (bl.a. L 98-59 sektor 29/32) + radio-kandidater | Kvalifikation af kortvarig lysglimt-detektion og rumlig TESS-pixelkovarians (`0` kandidater promoveret). | **Afsluttet metodeforløb** · Se grenen [`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification) |
| **4. Rubin / Fink optisk transient-forstudie** | `190` udvalgte objekter (`work_rubin_20261102`) | Afgrænset feasibility-tjek af alert-baseret fotometri (`MINIMUM50_UNMET`). | **Lukket forstudie** |

---

## Hovedresultater fra `D081` (`ECELLE_V3_2` Transit-Kinematik & `< 10 pc` Syntese)

1. **Keplerisk planet-hvileramme de-Doppler søgning (`Channel K_PLANET`):** På `7` sammenhængende 12-eksponerings transit-tidsserier (`HD 209458 b`, `55 Cnc e`, `KELT-11 b`, `HD 106315 c`, `WASP-166 b` + `2` kontrolserier) løfter eksakt kompensation af planetens banehastighed $\Delta v_{\mathrm{orb}}(t)$ (`6,7–38,5 km/s`) genfindingen af bevægende exoplanet-lasere ved $\ge 6,5\sigma$/eksp fra `0,0 %` til **`67,3 %`** (`81,4 %` ved $\ge 9\sigma$/eksp).
2. **Fire-generations falsk-alarm-kollaps (`V2 → V3.0 → V3.1 → V3.2`):** På de `159` uinjicerede eksponeringer kollapsede falske alarmer fra `1552` (`Legacy V2`) til **`0` kontrol og `21` science** på tværs af alle fire søgekanaler (`T`, `P`, `T_DIFF`, `K_PLANET`).
3. **Watt-skala grænser i Solens nabolag (`< 10 pc`) & `60`-stjerners syntese:** På tværs af `18` stjerner inden for `10,0 pc` ([`SOLAR_NEIGHBORHOOD_10PC_SYNTHESIS.csv`](progress/2026-11-15-echelle-d081-v3-2/SOLAR_NEIGHBORHOOD_10PC_SYNTHESIS.csv)) når `8σ`-følsomheden ned til **`9,0 W`** på `Proxima Centauri` (median `310 W` over `14` exoplanet-værter inden for `10 pc`), mens den samlede `60`-stjerners syntese er dokumenteret i [`MULTI_PHASE_V3_SYNTHESIS_60STARS.csv`](progress/2026-11-15-echelle-d081-v3-2/MULTI_PHASE_V3_SYNTHESIS_60STARS.csv).

---

## Navigation og reproduktion

- **Dokumentation:** [`CONTINUE_SETI.md`](CONTINUE_SETI.md) · [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md) · [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md) · [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
- **Kørsel af automatiseret test-suite (`seti-repeater`):**
  ```bash
  python3 -m pip install -e .
  OMP_NUM_THREADS=8 OMP_DYNAMIC=FALSE python3 -m unittest discover -s tests -v
  ```
- **Offline verifikation og clean-room genberegning gennem `D081` (i projektmappen med kompagnonarkiverne A–G):**
  ```bash
  /usr/bin/python3 -S restore_d081_workspace.py --check-only
  .venv/bin/python analysis_workspace/work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey/analyze.py --from-bounded-inputs
  /usr/bin/python3 -S analysis_workspace/work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey/audit.py
  ```
