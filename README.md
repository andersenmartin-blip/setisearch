# SETIsearch — Reproducerbar arkivbaseret teknosignaturforskning

*English summary: Open, prospectively locked archival technosignature research by Martin Andersen (MSc Astrophysics, University of Copenhagen), spanning high-resolution optical echelle spectroscopy (ESO HARPS & FEROS), multi-epoch narrowband radio de-Doppler searches (`seti-repeater`), and TESS fast-photometry qualification. Across all tracks, **0 qualified technosignature detections** are claimed; every negative branch, instrumental artifact diagnosis, and independent numerical audit is preserved.*

---

## Aktuel status (14. november 2026)

> **Samlet detektionsstatus: `0` kvalificerede teknosignaturer (optisk og radio).**
> - **Aktivt hovedspor:** Optisk højopløsningsspektroskopi (`HARPS` $R \approx 115\,000$ og `FEROS` $R \approx 48\,000$) gennem afsluttet checkpoint **[`D078`](progress/2026-11-14-feros-d078/REPORT.md)**, som måler `HD 43629`'s empiriske stellare hvileramme (`+33,820 ± 0,216 km/s` mod Gaia DR3 `+33,84 ± 0,45 km/s`), løser `D075`-sidebåndsafvigelsen fysisk og **afslutter hele `HD 43629`-opfølgningen (`D002`–`D078`) rent**.
> - **Næste hovedfase (Trin 2 — `V3`):** Design og syntetisk injektionskalibrering af en 2D + ordens-konsistent optisk laserdetektor (`V3`) før åbning af en ny kohorte af arkivstjerner.
> - **Start her for fortsættelse:** [**`CONTINUE_SETI.md`**](CONTINUE_SETI.md) · [**Optisk indeks (`D001`–`D078`)**](docs/OPTICAL_HD43629_INDEX.md) · [**Mappeoversigt**](docs/PROJECT_MAP.md).

---

## Oversigt over projektets fire forskningsspor

| Forskningsspor | Data & omfang | Vigtigste gennemførte arbejde og fund | Status & indgang |
| --- | --- | --- | --- |
| **1. Optisk Echelle-SETI (`HARPS` & `FEROS`)** | `300 + 50` HARPS-eksponeringer (`20 + 10` stjerner) + `5` FEROS-epoker + `30` WLC-kalibreringer | `V1`/`V2`-screening og fuld BERV/topocentrisk gennemgang af `90`-køen ([`C037`](work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md), [`D001`](work_seti_20261105_d001_delivery/README.md)); `141` `D002`-træf på 10 friske stjerner indsnævret til tre enkelt-epoke udsving i `HD 43629`, undersøgt med HARPS COMB/2D-rækker (`D035`–`D064`) og FEROS 2019-data, 30 WLC-råreferencer samt empirisk stellar hvileramme og 5-epoke coadd-syntese (`D065`–`D078`). `0` kvalificerede lasere. | **`HD 43629` afsluttet (`D078`) → Trin 2 (`V3`)** · [Optisk indeks](docs/OPTICAL_HD43629_INDEX.md) · [D078-rapport](docs/reports_d035_d077/SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_2026-11-14.md) |
| **2. Smalbåndet Radio-SETI (`seti-repeater`)** | GBT / Breakthrough Listen arkivsekvenser (`M8`–`M43AI`, `BA`–`CB`) | Multi-epoke de-Doppler-søgning under exoplanet-drifthypoteser med ON/OFF-veto. Omfatter `M43AF` (`502`-optagelsesstudie, `1.156` grænser), `M43AI` native validering, `HIP 44295` (`q1–254` over `2,91 MHz`; mangler komplet `OFF5`) og `HIP 35136` (`CB`). Ældre `M33 / HD 3651`-spor ved `1424,934238382 MHz` afventer uafhængig kadence. | **På pause** · [Arkiveret log](docs/history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) · [`src/seti_repeater/`](src/seti_repeater/__init__.py) |
| **3. Light-Sail & TESS-fotometri (`LS1`–`LS7E`)** | TESS pixeldata (bl.a. L 98-59 sektor 29/32) + radio-kandidater | Kvalifikation af kortvarig lysglimt-detektion. Påviste stærk rumlig pixelkovarians i TESS (`LS7D`–`LS7E` løftede nominel genfinding fra `3/40, 12/40, 27/40` til `18/40, 37/40, 40/40`), men svage signaler og bredere kontaminering bestod ikke forhåndskravene (`0` kandidater promoveret). | **Afsluttet metodeforløb** · Se grenen [`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification) |
| **4. Rubin / Fink optisk transient-forstudie** | `190` udvalgte objekter (`work_rubin_20261102`) | Afgrænset feasibility-tjek af alert-baseret fotometri; kun 2 objekter i primært spor (4 i forced-spor) var numerisk vurderbare mod et fastlagt minimum på `50`. Ikke et survey-nulresultat. | **Lukket forstudie** (`MINIMUM50_UNMET`) |

---

## Sammenhæng og konklusion for `HD 43629` (`TOI-880`, `D001`–`D078`)

1. **HARPS 2021 (`D001`–`D064`):**
   - Blandt `141` `V2`-træf på 50 friske eksponeringer (`D002`, 10 stjerner) optrådte tre enkelt-epoke hændelser i K-dværgen **`HD 43629`** (`D002-0061` ved `6550,095 Å`, `D002-0063` ved `4826,6475 Å`, `D002-0071` ved `5730,715 Å`). Ingen af dem gentog sig i kontroloptagelser fra marts og september 2021; `D002-0061` dumpede den oprindelige rå/native kvalitetsgrænse (`rho = 0,7807 < 0,8`), mens `D002-0063` (`k2573`-ydre rækkeasymmetri) og `D002-0071` (`4,9–5,6×` forhøjet 2D række-RMS) udviste markante 2D tværprofil-afvigelser mod den stellare fiber-PSF.
2. **FEROS 2019 & stellar hvileramme-syntese (`D065`–`D078`):**
   - Fem uafhængige FEROS-epoker fra november 2019 (`D065`–`D076`) og en komplet metadata-revision af samtlige 30 dagslys-`ThAr+Ne` WLC-kalibreringer (`D077`) blev i **[`D078`](docs/reports_d035_d077/SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_2026-11-14.md)** fulgt til dørs med `810` prospektivt låste fotosfæriske og telluriske linjefits (`324.810` QR-reviderede mindste-kvadraters evalueringer).
   - `D078` fastlægger `HD 43629`'s empiriske barycentriske hastighed i FEROS til **`+33,820 ± 0,216 km/s`** (`-0,020 km/s` fra Gaia DR3 `+33,84 ± 0,45 km/s`), beviser sub-`0,18 km/s` bølgelængdekonsistens mellem overlappende echelle-ordener (`HDU 30 - 29` og `HDU 25 - 24`), forklarer `D075`'s `1,45 km/s` enkelt-sidebåndsafvigelse ved `D002-0061` som atmosfærisk $\mathrm{H_2O}$ (`6552,629 Å`)-drift + variabel luftfugtighed + ordensrands-blaze i `HDU 30`, og viser, at 5-epoke RV-justerede coadds ved hvilebølgelængderne (`6549,356 Å`, `4826,103 Å`, `5730,069 Å`) skifter fortegn hen over baggrundsmodeller uden spor af vedvarende smal emission ([`HD43629_SYNTHESIS3.csv`](progress/2026-11-14-feros-d078/HD43629_SYNTHESIS3.csv)).

---

## Metodiske grundprincipper

1. **Prospektiv metodelåsning (`METHOD_LOCK.json`):** Input-hashes, forespørgsler, linjelister, masker og beslutningskriterier fryses *før* nye spektral- eller arkivværdier inspiceres.
2. **Uafhængig numerisk efterregning (`NUMERICAL_AUDIT.json`):** Hver fase revideres med en separat implementation (f.eks. ren Python stdlib QR med `python -S` uden NumPy/SciPy i `D078` eller 50-cifret `Decimal`-aritmetik i `D077`). En intern audit verificerer regnepræcision — den udgør ikke ekstern fagfællebedømmelse.
3. **Fuld bevaring af nulresultater og fejlflag:** Signerede residualer, fejlede kvalitetskrav og skiftende fortegn over alternative baggrunde gemmes urørt; gentagne modeller på de samme fotoner tælles aldrig som uafhængige observationer.

---

## Navigation og reproduktion

- **Dokumentation og historik:**
  - [`CONTINUE_SETI.md`](CONTINUE_SETI.md) — Aktiv teknisk overdragelse og køreplan for **Trin 2 (`V3`)**.
  - [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md) — Komplet indeks over alle rapporter i `D001`–`D078`.
  - [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md) — Forklaring af repositoriets mappestruktur, forseglede rod-manifests og kompagnonarkiver A–D.
  - [`docs/history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) — Ubeskåret historisk logbog fra `README.md` frem til 14. november 2026.
- **Kørsel af automatiseret test-suite (`seti-repeater` pakken):**
  ```bash
  python3 -m pip install -e .
  OMP_NUM_THREADS=8 OMP_DYNAMIC=FALSE python3 -m unittest discover -s tests -v
  ```
- **Reproduktion af `D001`-leverancekontrollen (uden netværk):**
  ```bash
  python3 work_seti_20261105_d001_delivery/audit_delivery.py --out /tmp/seti-d001-check
  ```
- **Verifikation af hele `FEROS`-arbejdskæden gennem `D078` (i projektmappen med kompagnonarkiverne A, B, C og D):**
  ```bash
  python3 restore_d078_workspace.py --check-only
  OPENBLAS_NUM_THREADS=1 .venv/bin/python analysis_workspace/work_feros_20261114_d078_stellar_restframe_and_hd43629_synthesis/verify.py --recompute
  ```
