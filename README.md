# SETIsearch — Reproducerbar arkivbaseret teknosignaturforskning

*English summary: Open, prospectively locked archival technosignature research by Martin Andersen (MSc Astrophysics, University of Copenhagen), spanning panchromatic high-resolution optical and near-infrared echelle spectroscopy (`0.38–1.80 µm`; ESO HARPS, VLT ESPRESSO, ESO NIRPS & FEROS), multi-epoch narrowband radio de-Doppler searches (`seti-repeater`), and TESS fast-photometry qualification. Across all tracks — culminating in the completed **80-star (`501`-exposure) Panchromatic `V3.0–V3.3` Survey** (`D079–D082`, [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) / [`paper/main.tex`](paper/main.tex)) down to **9.0 W** optically and **607.7 W** at `1064.1 nm` (`1,026.1 W` at `1550.0 nm`) on Proxima Centauri — **0 qualified technosignature detections** are claimed; every negative branch, instrumental artifact diagnosis, and pure-stdlib numerical audit is preserved.*

---

## Aktuel status (15. november 2026)

> **Samlet detektionsstatus: `0` kvalificerede teknosignaturer (pankromatisk optisk/nær-IR og radio).**
> - **Aktivt hovedspor afsluttet gennem `Trin 5` (`D082`):** Pankromatisk højopløsnings-echellespektroskopi (`0,38–1,80 µm`: `HARPS` $R \approx 115\,000$, VLT `ESPRESSO` $R \approx 140\,000$, ESO `NIRPS_HE` $R \approx 70\,000$ og `FEROS` $R \approx 48\,000$) gennem afsluttet checkpoint **[`D082` (Trin 5 — 4-kanals `NIRPS_V3_3` nær-IR `0,98–1,80 µm` YJH-survey & samlet `80`-stjerners pankromatisk syntese)](progress/2026-11-15-nirps-d082-v3-3/REPORT.md)** over **`152` `NIRPS_HE`-eksponeringer af `22` nære stjerner** (`18` exoplanet-værter med `42` planeter ved `1,30–38,57 pc`, inkl. `< 2 pc`-broen på `Proxima Centauri` og `Barnard's Star`, `5` komplette transit-nætter + `4` kontrolstjerner): **`0` kontrol- og `0` science-kandidater** efter `G5_V33` (mod `3.828` i `Legacy V2`), med `8σ`-øvre grænser ned til **`607,7 W` ved `1064,1 nm` (`Nd:YAG`/`Yb`)** og **`1.026,1 W` ved `1550,0 nm` (`Er` C-bånd)** på `Proxima Centauri` (`10 m`-sender).
> - **Samlet Pankromatisk `V3`-Syntese (`D079–D082`) & Artikelmanuskript:** **`80` unikke stjerner og `501` eksponeringer** (`220` HARPS + `129` VLT ESPRESSO + `152` ESO NIRPS_HE; **`29` stjerner inden for `10,0 pc`** inkl. `23` exoplanet-værter med `51` planeter; `6.570` syntetiske kalibreringsforsøg; **`0` verificerede ETI-lasere**). Komplet engelsk publikationsmanuskript og LaTeX-kilde: **[`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md)** · **[`paper/main.tex`](paper/main.tex)**.
> - **Start her for fortsættelse:** [**`CONTINUE_SETI.md`**](CONTINUE_SETI.md) · [**Pankromatisk `V3.0–V3.3`-survey-indeks (`D079–D082`)**](docs/OPTICAL_V3_SURVEY_INDEX.md) · [**Historisk indeks (`D001`–`D078`)**](docs/OPTICAL_HD43629_INDEX.md) · [**Mappeoversigt**](docs/PROJECT_MAP.md).

---

## Oversigt over projektets fire forskningsspor

| Forskningsspor | Data & omfang | Vigtigste gennemførte arbejde og fund | Status & indgang |
| --- | --- | --- | --- |
| **1A. Pankromatisk Echelle-SETI — Kalibreret `V3.0–V3.3`-survey (`D079–D082`, `0,38–1,80 µm`)** | `501` eksponeringer (`220` HARPS + `129` VLT ESPRESSO + `152` ESO NIRPS_HE på **`80` unikke FGKM-stjerner** ved `1,30–114,3 pc`, inkl. `29` inden for `< 10 pc`) | `D079` (`V3.0`, `60` eksp) + `D080` (`V3.1`, `130` eksp) + `D081` (`ECELLE_V3_2`, `159` eksp, ned til **`9,0 W`** optisk) + `D082` (`NIRPS_V3_3`, `152` eksp, `100 %` H2RG IPC/persistens-afvisning, ned til **`607,7 W`** ved `1064,1 nm` / **`1.026,1 W`** ved `1550,0 nm`) → **`0` ETI-lasere** (`5.850` `V2`-falskalarmer elimineret). | **`D082` afsluttet (`80`-stjerners syntese + manuskript)** · [Artikel (`MD`)](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) · [`LaTeX`](paper/main.tex) · [`V3`-indeks](docs/OPTICAL_V3_SURVEY_INDEX.md) · [`D082`-rapport](docs/reports_d035_d077/SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_SURVEY_2026-11-15.md) |
| **1B. Optisk Echelle-SETI — `C001–D078` & `HD 43629` (`HARPS` & `FEROS`)** | `300 + 50` HARPS-eksponeringer (`20 + 10` stjerner) + `5` FEROS-epoker + `30` WLC-kalibreringer | Lukning af `90`-køen ([`C037`](work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md), [`D001`](work_seti_20261105_d001_delivery/README.md)), `141` `D002`-træf og fuld HARPS COMB/2D + FEROS stellar hvileramme-syntese for `HD 43629` (`+33,820 ± 0,216 km/s`; `0` kvalificerede lasere). | **Lukket rent (`D078`)** · [Historisk optisk indeks](docs/OPTICAL_HD43629_INDEX.md) |
| **2. Smalbåndet Radio-SETI (`seti-repeater`)** | GBT / Breakthrough Listen arkivsekvenser (`M8`–`M43AI`, `BA`–`CB`) | Multi-epoke de-Doppler-søgning under exoplanet-drifthypoteser med ON/OFF-veto (`M43AF` `502`-optagelsesstudie, `M43AI`, `HIP 44295`, `HIP 35136`, `M33 / HD 3651`). | **På pause** · [Arkiveret log](docs/history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) · [`src/seti_repeater/`](src/seti_repeater/__init__.py) |
| **3. Light-Sail & TESS-fotometri (`LS1`–`LS7E`)** | TESS pixeldata (bl.a. L 98-59 sektor 29/32) + radio-kandidater | Kvalifikation af kortvarig lysglimt-detektion og rumlig TESS-pixelkovarians (`0` kandidater promoveret). | **Afsluttet metodeforløb** · Se grenen [`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification) |
| **4. Rubin / Fink optisk transient-forstudie** | `190` udvalgte objekter (`work_rubin_20261102`) | Afgrænset feasibility-tjek af alert-baseret fotometri (`MINIMUM50_UNMET`). | **Lukket forstudie** |

---

## Hovedresultater fra `D082` (`NIRPS_V3_3` YJH-Survey & `80`-Stjerners Pankromatisk Syntese)

1. **Nær-infrarød Hawaii-2RG & Keplerisk de-Doppler kalibrering (`1.971` syntetiske forsøg):** På `152` $R=70\,000$ `NIRPS_HE`-eksponeringer (`0,98–1,80 µm` YJH) opnår `NIRPS_V3_3` **`90,9 %`** komplethed i `Channel T` ($\ge 8\sigma$; **`91,7 %`** ved `1064,1 nm` og **`72,2 %`** ved `1550,0 nm`), øger Keplerisk planet-hvileramme genfinding (`Channel K_PLANET`) ved $\ge 6,5\sigma$/eksp fra `3,7 %` til **`58,0 %`** (`87,0 %` ved $\ge 9\sigma$/eksp over alle niveauer) og opnår **`100,0 %` (`72/72`) ægte laser-transmission mod `100,0 %` (`144/144`) afvisning** af Hawaii-2RG inter-pixel kapacitans (`IPC`) hot-pixels og persistens-plateauer (`Gate G5_V33`).
2. **Komplet eliminering af `3.828` nær-IR falske alarmer (`Legacy V2 → NIRPS_V3_3`):** Tellurisk/OH-maske (`G2_V33`: `4.053 → 54`), stellar kromosfærisk/molekylær ryg-veto (`G3_V33`: `54 → 6`), Fiber-B `SKY` + ordensoverlap (`G4_V33`: `6 → 3`) og 2D H2RG detektor-morfologi (`G5_V33`: `3 → 0`) reducerer samtlige falske alarmer til **`0` kontrol (`0/27`) og `0` science (`0/125`) kandidater**.
3. **Sub-kilowatt `1064 nm` / `1550 nm` grænser & `80`-stjerners pankromatisk syntese (`0,38–1,80 µm`):** Den pankromatiske `< 2 pc`-bro på `Proxima Centauri` (`9,0 W` optisk; **`607,7 W` ved `1064,1 nm`**, **`1.026,1 W` ved `1550,0 nm`**) og `Barnard's Star` (`75,3 W` optisk; **`1.433,0–2.016,0 W`** i YJH) forankrer hele det samlede `80`-stjerners (`501`-eksponeringers) katalog i [`UNIFIED_PANCHROMATIC_V3_SYNTHESIS_80STARS.csv`](progress/2026-11-15-nirps-d082-v3-3/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_80STARS.csv) og [`SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_29STARS.csv`](progress/2026-11-15-nirps-d082-v3-3/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_29STARS.csv) (median bedste `10 m`-grænse **`1,75 kW`** over `23` exoplanet-værter inden for `10 pc`).

---

## Navigation og reproduktion

- **Videnskabeligt manuskript (`D079–D082`):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) · [`paper/main.tex`](paper/main.tex).
- **Dokumentation:** [`CONTINUE_SETI.md`](CONTINUE_SETI.md) · [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md) · [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md) · [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
- **Kørsel af automatiseret test-suite (`seti-repeater`):**
  ```bash
  python3 -m pip install -e .
  OMP_NUM_THREADS=8 OMP_DYNAMIC=FALSE python3 -m unittest discover -s tests -v
  ```
- **Offline verifikation og clean-room genberegning gennem `D082` (i projektmappen med kompagnonarkiverne A–H):**
  ```bash
  /usr/bin/python3 -S restore_d082_workspace.py --check-only
  .venv/bin/python analysis_workspace/work_nirps_20261115_d082_v3_3_near_ir_and_panchromatic_survey/analyze.py --from-bounded-inputs
  /usr/bin/python3 -S analysis_workspace/work_nirps_20261115_d082_v3_3_near_ir_and_panchromatic_survey/audit.py
  ```
