# SETIsearch — Reproducerbar arkivbaseret teknosignaturforskning

*English summary: Open, prospectively locked archival technosignature research by Martin Andersen (MSc Astrophysics, University of Copenhagen), spanning high-resolution optical echelle spectroscopy (ESO HARPS, VLT ESPRESSO & FEROS), multi-epoch narrowband radio de-Doppler searches (`seti-repeater`), and TESS fast-photometry qualification. Across all tracks, **0 qualified technosignature detections** are claimed; every negative branch, instrumental artifact diagnosis, and independent numerical audit is preserved.*

---

## Aktuel status (14. november 2026)

> **Samlet detektionsstatus: `0` kvalificerede teknosignaturer (optisk og radio).**
> - **Aktivt hovedspor:** Optisk højopløsningsspektroskopi (`HARPS` $R \approx 115\,000$, VLT `ESPRESSO` $R \approx 140\,000$ og `FEROS` $R \approx 48\,000$) gennem afsluttet checkpoint **[`D080` (Trin 3 — `ECELLE_V3_1` multi-instrument exoplanet-survey)](progress/2026-11-14-echelle-d080-v3-1/REPORT.md)**, som prospektivt opgraderer detektoren med supraphotosfærisk kontinuum-gate (`G1_F1`/`G3_F1`), 2D $(T_{\mathrm{eff}}, [\mathrm{M/H}])$ `K=5`-stjerneatlas og 2D-detektorfysik (`G5_F2`: HARPS `5×11` rå CCD + VLT ESPRESSO `2×11` anamorfisk pupil-slice) over **`130` friske eksponeringer af `26` nære FGKM-stjerner** (`22` exoplanet-værter med `44` planeter ved `3,64–44,86 pc` + `4` kontrolstjerner): **`0` verificerede ETI-lasere**, med kalibrerede `8σ`-øvre grænser ned til **`0,91 kW` (median `10,28 kW`)** for en diffraktionsbegrænset `10 m`-sender.
> - **Næste hovedfase (Trin 4 — `D081`):** Tætte konjunktions-synkroniserede transit-tidsserier (`HARPS` + VLT `ESPRESSO` Rossiter-McLaughlin-sekvenser under selve planettransitten) kombineret med en volumen-komplet `< 10 pc` syntese.
> - **Start her for fortsættelse:** [**`CONTINUE_SETI.md`**](CONTINUE_SETI.md) · [**`V3 / V3.1`-survey-indeks (`D079–D080`)**](docs/OPTICAL_V3_SURVEY_INDEX.md) · [**Historisk indeks (`D001`–`D078`)**](docs/OPTICAL_HD43629_INDEX.md) · [**Mappeoversigt**](docs/PROJECT_MAP.md).

---

## Oversigt over projektets fire forskningsspor

| Forskningsspor | Data & omfang | Vigtigste gennemførte arbejde og fund | Status & indgang |
| --- | --- | --- | --- |
| **1A. Optisk Echelle-SETI — Kalibreret `V3` & `V3.1`-survey (`D079–D080`)** | `190` friske eksponeringer (`130` HARPS + `60` VLT ESPRESSO på `38` nære FGKM- og exoplanet-stjerner, `0` overlap mod `C001–D078`) | `D079` (`HARPS_ECELLE_V3`, `60` eksp) + `D080` (`ECELLE_V3_1`, `130` eksp, `44` exoplaneter, `1.734` syntetiske forsøg over `3844–7465 Å`, `59,2 %` Kanal T $\ge 8\sigma$, `100,0 %` 2D kosmisk afvisning → **`0` ETI-lasere**, `8σ`-grænse ned til **`0,91 kW`** på `HIP70849`). | **`D080` afsluttet → Trin 4 (`D081`)** · [`V3/V3.1`-indeks](docs/OPTICAL_V3_SURVEY_INDEX.md) · [`D080`-rapport](docs/reports_d035_d077/SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_SURVEY_2026-11-14.md) |
| **1B. Optisk Echelle-SETI — `C001–D078` & `HD 43629` (`HARPS` & `FEROS`)** | `300 + 50` HARPS-eksponeringer (`20 + 10` stjerner) + `5` FEROS-epoker + `30` WLC-kalibreringer | Lukning af `90`-køen ([`C037`](work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md), [`D001`](work_seti_20261105_d001_delivery/README.md)), `141` `D002`-træf og fuld HARPS COMB/2D + FEROS stellar hvileramme-syntese for `HD 43629` (`+33,820 ± 0,216 km/s`; `0` kvalificerede lasere). | **Lukket rent (`D078`)** · [Historisk optisk indeks](docs/OPTICAL_HD43629_INDEX.md) |
| **2. Smalbåndet Radio-SETI (`seti-repeater`)** | GBT / Breakthrough Listen arkivsekvenser (`M8`–`M43AI`, `BA`–`CB`) | Multi-epoke de-Doppler-søgning under exoplanet-drifthypoteser med ON/OFF-veto (`M43AF` `502`-optagelsesstudie, `M43AI`, `HIP 44295`, `HIP 35136`, `M33 / HD 3651`). | **På pause** · [Arkiveret log](docs/history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) · [`src/seti_repeater/`](src/seti_repeater/__init__.py) |
| **3. Light-Sail & TESS-fotometri (`LS1`–`LS7E`)** | TESS pixeldata (bl.a. L 98-59 sektor 29/32) + radio-kandidater | Kvalifikation af kortvarig lysglimt-detektion og rumlig TESS-pixelkovarians (`0` kandidater promoveret). | **Afsluttet metodeforløb** · Se grenen [`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification) |
| **4. Rubin / Fink optisk transient-forstudie** | `190` udvalgte objekter (`work_rubin_20261102`) | Afgrænset feasibility-tjek af alert-baseret fotometri (`MINIMUM50_UNMET`). | **Lukket forstudie** |

---

## Hovedresultater fra `D080` (`ECELLE_V3_1` på `HARPS` + VLT `ESPRESSO`, `26` stjerner / `44` exoplaneter)

1. **Tvær-instrumentel kalibrering fra UV-blåt til dybrødt (`3844,75–7465,10 Å`):** `1.560` NIST-hvilerammefits giver median afvigelse `0,511 km/s` mod Gaia DR3. På `1.734` syntetiske forsøg opnås `59,15 %` genfinding i Kanal T ved $\ge 8\sigma$, `84,31 %` i Kanal P ved $\ge 9\sigma$ (`92,65 %` ved $\ge 12\sigma$) samt `97,06 %` 2D laser-accept mod `100,00 %` afvisning af kosmiske stråler i `Gate G5_F2`.
2. **Tre-generations falsk-alarm-kollaps (`V2 → V3.0 → V3.1`):** På de samme `130` uinjicerede eksponeringer kollapsede falske alarmer fra `422` (`Legacy V2`) og `153` sub-kontinuum Kanal P-bumps (`D079 V3.0` før `F1`) til **`10` kontrol- og `24` science-kandidater** i den prospektivt låste `ECELLE_V3_1`-pipeline (`0` ETI-lasersignaler).
3. **Kilowatt-klasse astrofysiske øvre grænser:** På tværs af de `22` exoplanet-værtsstjerner (`186` stjerne-bånd-celler, inkl. `15` transiterende systemer) sættes `8σ`-grænser ned til **`0,91 kW`** på `HIP70849` (samlet median **`10,28 kW`**, VLT `ESPRESSO` median **`7,52 kW`**) ([`STAR_UPPER_LIMITS_186.csv`](progress/2026-11-14-echelle-d080-v3-1/STAR_UPPER_LIMITS_186.csv)).

---

## Navigation og reproduktion

- **Dokumentation:** [`CONTINUE_SETI.md`](CONTINUE_SETI.md) · [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md) · [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md) · [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
- **Kørsel af automatiseret test-suite (`seti-repeater`):**
  ```bash
  python3 -m pip install -e .
  OMP_NUM_THREADS=8 OMP_DYNAMIC=FALSE python3 -m unittest discover -s tests -v
  ```
- **Offline verifikation og clean-room genberegning gennem `D080` (i projektmappen med kompagnonarkiverne A–F):**
  ```bash
  /usr/bin/python3 -S restore_d080_workspace.py --check-only
  .venv/bin/python analysis_workspace/work_echelle_20261114_d080_v3_1_exoplanet_survey/analyze.py --from-bounded-inputs
  /usr/bin/python3 -S analysis_workspace/work_echelle_20261114_d080_v3_1_exoplanet_survey/audit.py
  ```
