# SETIsearch — Reproducerbar arkivbaseret teknosignaturforskning

*English summary: Open, prospectively locked archival technosignature research by Martin Andersen (MSc Astrophysics, University of Copenhagen), spanning high-resolution optical echelle spectroscopy (ESO HARPS & FEROS), multi-epoch narrowband radio de-Doppler searches (`seti-repeater`), and TESS fast-photometry qualification. Across all tracks, **0 qualified technosignature detections** are claimed; every negative branch, instrumental artifact diagnosis, and independent numerical audit is preserved.*

---

## Aktuel status (14. november 2026)

> **Samlet detektionsstatus: `0` kvalificerede teknosignaturer (optisk og radio).**
> - **Aktivt hovedspor:** Optisk højopløsningsspektroskopi (`HARPS` $R \approx 115\,000$ og `FEROS` $R \approx 48\,000$) gennem afsluttet checkpoint **[`D079` (Trin 2 — `HARPS_ECELLE_V3`)](progress/2026-11-14-harps-d079-v3/REPORT.md)**, som prospektivt kalibrerer en 2D + ordens- og hvileramme-forankret optisk laserdetektor (`816` syntetiske forsøg over `3800–6900 Å`, inkl. det nyåbnede blå interval `3800–4000 Å`) og gennemfører en ublindet søgning på **`10` friske nære sol-analoge stjerner (`50` eksponeringer, `15,2–46,3 pc`) + `2` prospektive kontrolstjerner (`10` eksponeringer)**: **`0` verificerede ETI-lasere**, med kalibrerede `8σ`-øvre grænser på **`17,30–201,41 kW` (median `46,99 kW`)** for en diffraktionsbegrænset `10 m`-sender.
> - **Næste hovedfase (Trin 3 — `D080` / `V3.1`):** Opgradering af `V3` til `V3.1` (indbygning af supraphotosfærisk flux-gate `F1` i Kanal P og fuld `5 × 11` separabel 2D fiber-PSF `F2` direkte i Gate G5) og skalering til `50–100` nære FGKM- og exoplanet-værtsstjerner i `HARPS` + `ESPRESSO`.
> - **Start her for fortsættelse:** [**`CONTINUE_SETI.md`**](CONTINUE_SETI.md) · [**`V3`-survey-indeks (`D079+`)**](docs/OPTICAL_V3_SURVEY_INDEX.md) · [**Historisk indeks (`D001`–`D078`)**](docs/OPTICAL_HD43629_INDEX.md) · [**Mappeoversigt**](docs/PROJECT_MAP.md).

---

## Oversigt over projektets fire forskningsspor

| Forskningsspor | Data & omfang | Vigtigste gennemførte arbejde og fund | Status & indgang |
| --- | --- | --- | --- |
| **1A. Optisk Echelle-SETI — Kalibreret `V3`-survey (`D079+`)** | `60` friske HARPS-eksponeringer (`10` science- + `2` kontrolstjerner, `0` overlap mod alle `40` tidligere mål og `363` `dp_id`) | Prospektivt låst `HARPS_ECELLE_V3` med `720` NIST-ankerfits (`0` randtræf, `12–44 m/s` epoke-RMS), `816` syntetiske injektions-/2D-forsøg (`85,1 %` Kanal T $\ge 8\sigma$, `83,3 %` i `3800–4000 Å` blåt), paritetsdiagnose via kontrolstjerner (`2,80` mod `2,96` nominelle G1–G5-passager/eksp) og forensisk lukning (`F1+F2` → **`0` ETI-lasere**, median `8σ`-grænse **`46,99 kW`**). | **`D079` afsluttet → Trin 3 (`V3.1`)** · [`V3`-indeks](docs/OPTICAL_V3_SURVEY_INDEX.md) · [`D079`-rapport](docs/reports_d035_d077/SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_2026-11-14.md) |
| **1B. Optisk Echelle-SETI — `C001–D078` & `HD 43629` (`HARPS` & `FEROS`)** | `300 + 50` HARPS-eksponeringer (`20 + 10` stjerner) + `5` FEROS-epoker + `30` WLC-kalibreringer | Lukning af `90`-køen ([`C037`](work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md), [`D001`](work_seti_20261105_d001_delivery/README.md)), `141` `D002`-træf og fuld HARPS COMB/2D + FEROS stellar hvileramme-syntese for `HD 43629` (`+33,820 ± 0,216 km/s`; `0` kvalificerede lasere). | **Lukket rent (`D078`)** · [Historisk optisk indeks](docs/OPTICAL_HD43629_INDEX.md) |
| **2. Smalbåndet Radio-SETI (`seti-repeater`)** | GBT / Breakthrough Listen arkivsekvenser (`M8`–`M43AI`, `BA`–`CB`) | Multi-epoke de-Doppler-søgning under exoplanet-drifthypoteser med ON/OFF-veto (`M43AF` `502`-optagelsesstudie, `M43AI`, `HIP 44295`, `HIP 35136`, `M33 / HD 3651`). | **På pause** · [Arkiveret log](docs/history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) · [`src/seti_repeater/`](src/seti_repeater/__init__.py) |
| **3. Light-Sail & TESS-fotometri (`LS1`–`LS7E`)** | TESS pixeldata (bl.a. L 98-59 sektor 29/32) + radio-kandidater | Kvalifikation af kortvarig lysglimt-detektion og rumlig TESS-pixelkovarians (`0` kandidater promoveret). | **Afsluttet metodeforløb** · Se grenen [`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification) |
| **4. Rubin / Fink optisk transient-forstudie** | `190` udvalgte objekter (`work_rubin_20261102`) | Afgrænset feasibility-tjek af alert-baseret fotometri (`MINIMUM50_UNMET`). | **Lukket forstudie** |

---

## Hovedresultater fra `D079` (`HARPS_ECELLE_V3` kalibreret optisk søgning)

1. **Stellar hvileramme og syntetisk følsomhed over hele `3800–6900 Å`:** `720` uafhængigt reviderede NIST-linjefits giver `0` randtræf, `12,0–44,2 m/s` epoke-til-epoke HARPS-RMS og median `+0,431 km/s` nulpunktsskift mod Gaia DR3. På `816` syntetiske forsøg opnås `85,07 %` genfinding i Kanal T ved $\ge 8\sigma$ (`83,33 %` i `3800–4000 Å` blåt bånd) og `83,33 %` i Kanal P ved $\ge 9\sigma$ (`100 %` i begge blå bånd).
2. **Kontrolstjerne-paritet og forensisk identifikation af samtlige falske positiver:** De to prospektive kontrolstjerner (`HD 1461`, `HD 4308`) viste `2,80` nominelle `G1–G5`-passager pr. eksponering mod `2,96` på de `10` science-stjerner (`0,50/eksp` mod `0,10/eksp` i Kanal T) — nul science-overskud. Pixel- og kontinuum-forensik ([`FORENSIC_VETTING_176.csv`](progress/2026-11-14-harps-d079-v3/FORENSIC_VETTING_176.csv)) beviste, at **`166 / 166` Kanal P-passager** ligger *under* det lokale stellare kontinuum (`maks. fn_pk3 = 0,9787 < 1,00`, fotosfærisk metallinje-mismatch), og at **`10 / 10` Kanal T-passager** er skrå 2D kosmiske myonspor (`tilt` op til `5,58 px`) eller kontinuum-pedestal → **`0` verificerede ETI-lasere**.
3. **Astrofysiske øvre grænser:** På tværs af de `10` nære sol-analoge stjerner (`15,2–46,3 pc`) sættes `8σ`-øvre grænser på **`1,68–23,39 mÅ`** (median **`3,81 mÅ`**) og **`17,30–201,41 kW`** (median **`46,99 kW`**) for en diffraktionsbegrænset `10 m`-lasersender ([`STAR_UPPER_LIMITS_80.csv`](progress/2026-11-14-harps-d079-v3/STAR_UPPER_LIMITS_80.csv)).

---

## Metodiske grundprincipper

1. **Prospektiv metodelåsning (`METHOD_LOCK.json`):** Kohorte, parametre og tærskler fryses med kryptografisk SHA-256-kvittering *før* science-spektre hentes.
2. **Uafhængig ren-stdlib numerisk efterregning (`NUMERICAL_AUDIT.json`):** Hver fase revideres uden tredjepartsbiblioteker (`/usr/bin/python3 -S audit.py`: `6.072` kontroller og `0` fejl i `D079`).
3. **Fuld bevaring af nulresultater og tekniske fejl:** Både initiale kørselsfejl (Fiber B `71`-mod-`72` ordener i `IMPLEMENTATION_LOCK.json`) og ufiltrerede `G1–G5`-kontrolrater bevares ubeskåret.

---

## Navigation og reproduktion

- **Dokumentation:** [`CONTINUE_SETI.md`](CONTINUE_SETI.md) · [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md) · [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md) · [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
- **Kørsel af automatiseret test-suite (`seti-repeater`):**
  ```bash
  python3 -m pip install -e .
  OMP_NUM_THREADS=8 OMP_DYNAMIC=FALSE python3 -m unittest discover -s tests -v
  ```
- **Offline verifikation og clean-room genberegning gennem `D079` (i projektmappen med kompagnonarkiverne A–E):**
  ```bash
  /usr/bin/python3 -S restore_d079_workspace.py --check-only
  .venv/bin/python analysis_workspace/work_harps_20261114_d079_v3_calibrated_search/analyze.py --from-bounded-inputs
  /usr/bin/python3 -S analysis_workspace/work_harps_20261114_d079_v3_calibrated_search/audit.py
  ```
