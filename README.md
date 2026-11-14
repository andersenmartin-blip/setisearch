# SETIsearch — Reproducerbar arkivbaseret teknosignaturforskning

*English summary: Open, prospectively locked archival technosignature research by Martin Andersen (MSc Astrophysics, University of Copenhagen), spanning high-resolution optical echelle spectroscopy (ESO HARPS & FEROS), multi-epoch narrowband radio de-Doppler searches (`seti-repeater`), and TESS fast-photometry qualification. Across all tracks, **0 qualified technosignature detections** are claimed; every negative branch, instrumental artifact diagnosis, and independent numerical audit is preserved.*

---

## Aktuel status (14. november 2026)

> **Samlet detektionsstatus: `0` kvalificerede teknosignaturer (optisk og radio).**
> - **Aktivt hovedspor:** Optisk højopløsningsspektroskopi (`HARPS` $R \approx 115\,000$ og `FEROS` $R \approx 48\,000$) gennem afsluttet checkpoint **[`D077`](progress/2026-11-14-feros-d077/REPORT.md)**.
> - **Næste sammenhængende skridt (`D078`):** Lokal fotosfærisk stjernerestframe- og ordensoverlap-kontrol i FEROS samt samlet afslutningssyntese for `HD 43629` (`TOI-880`), efterfulgt af udvikling af en kalibreret 2D+ordens-bevidst optisk detektor (`V3`).
> - **Start her for fortsættelse:** [**`CONTINUE_SETI.md`**](CONTINUE_SETI.md) · [**Optisk indeks (`D001`–`D077`)**](docs/OPTICAL_HD43629_INDEX.md) · [**Mappeoversigt**](docs/PROJECT_MAP.md).

---

## Oversigt over projektets fire forskningsspor

| Forskningsspor | Data & omfang | Vigtigste gennemførte arbejde og fund | Status & indgang |
| --- | --- | --- | --- |
| **1. Optisk Echelle-SETI (`HARPS` & `FEROS`)** | `300 + 50` HARPS-eksponeringer (`20 + 10` stjerner) + `5` FEROS-epoker + `30` WLC-kalibreringer | `V1`/`V2`-screening og fuld BERV/topocentrisk gennemgang af `90`-køen ([`C037`](work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md), [`D001`](work_seti_20261105_d001_delivery/README.md)); `141` `D002`-træf på 10 friske stjerner indsnævret til tre enkelt-epoke udsving i `HD 43629`, undersøgt med HARPS COMB/2D-rækker (`D035`–`D064`) og uafhængige FEROS 2019-data + 30 WLC-råreferencer (`D065`–`D077`). `0` kvalificerede lasere. | **Aktivt (`D077` → `D078`)** · [Optisk indeks](docs/OPTICAL_HD43629_INDEX.md) · [D077-rapport](docs/reports_d035_d077/SETI_D077_FEROS_WLC_METADATA_GATE_2026-11-14.md) |
| **2. Smalbåndet Radio-SETI (`seti-repeater`)** | GBT / Breakthrough Listen arkivsekvenser (`M8`–`M43AI`, `BA`–`CB`) | Multi-epoke de-Doppler-søgning under exoplanet-drifthypoteser med ON/OFF-veto. Omfatter `M43AF` (`502`-optagelsesstudie, `1.156` grænser), `M43AI` native validering, `HIP 44295` (`q1–254` over `2,91 MHz`; mangler komplet `OFF5`) og `HIP 35136` (`CB`). Ældre `M33 / HD 3651`-spor ved `1424,934238382 MHz` afventer uafhængig kadence. | **På pause** · [Arkiveret log](docs/history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) · [`src/seti_repeater/`](src/seti_repeater/__init__.py) |
| **3. Light-Sail & TESS-fotometri (`LS1`–`LS7E`)** | TESS pixeldata (bl.a. L 98-59 sektor 29/32) + radio-kandidater | Kvalifikation af kortvarig lysglimt-detektion. Påviste stærk rumlig pixelkovarians i TESS (`LS7D`–`LS7E` løftede nominel genfinding fra `3/40, 12/40, 27/40` til `18/40, 37/40, 40/40`), men svage signaler og bredere kontaminering bestod ikke forhåndskravene (`0` kandidater promoveret). | **Afsluttet metodeforløb** · Se grenen [`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification) |
| **4. Rubin / Fink optisk transient-forstudie** | `190` udvalgte objekter (`work_rubin_20261102`) | Afgrænset feasibility-tjek af alert-baseret fotometri; kun 2 objekter i primært spor (4 i forced-spor) var numerisk vurderbare mod et fastlagt minimum på `50`. Ikke et survey-nulresultat. | **Lukket forstudie** (`MINIMUM50_UNMET`) |

---

## Sammenhæng i den aktive optiske undersøgelse (`HD 43629` / `TOI-880`)

1. **Fra bred `V2`-screening til målrettet instrumentdiagnose (`D001`–`D064`):**
   - Konsolideringen i [`D001`](work_seti_20261105_d001_delivery/README.md) viste, at 1D-detektoren `V2` gav `669` træf på `200` eksponeringer (heraf `188` i `3800–4000 Å` uden blå kontrolankre). På den efterfølgende friske `50`-eksponerings kohorte (`D002`, 10 stjerner) fremkom `141` 1D-træf, hvoraf alle blev gennemgået i 2D-råkontekst.
   - Tre enkelt-epoke strukturer i K-dværgen **`HD 43629`** fra 2021 (`D002-0061` ved `6550,095 Å`, `D002-0063` ved `4826,6475 Å`, `D002-0071` ved `5730,715 Å`) gennemgik i [`D035`–`D064`](docs/OPTICAL_HD43629_INDEX.md) dybdegående HARPS-kontroller: LFC/COMB-linjerespons, empiriske støjhaler, samtlige marts/september 2021-kontrolepoker og eksakt dekomposition af de 2D native CCD-rækker (herunder påvisning af, hvordan ét enkelt ydre nabosample `k2573` flytter den ydre kontrast ved `D002-0063` med ~`5.380 ADU`).
2. **Uafhængig instrumentkontekst i FEROS (`D065`–`D077`):**
   - For at undgå cirkulære modelvarianter på de samme HARPS-pixels inddrog [`D065`–`D068`](docs/reports_d035_d077/SETI_D067_D068_FEROS_INPUTS_AND_PROFILES_2026-11-13.md) fem offentlige **FEROS-observationer fra november 2019** (`F1`–`F5`). Ved alle tre bølgelængder skifter den lokale 3-sample-kontrast fortegn på tværs af de fastlagte baggrundspolynomier (ingen bekræftet stationær emissionslinje i 2019).
   - [`D069`–`D076`](docs/reports_d035_d077/SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_2026-11-13.md) sammenlignede samtlige ekstraktionsmetoder, individuelle echelle-ordener (`HDU 17`, `24–25`, `29–30`) og frem/tilbage spektralregistreringer (`938.340` QR-gridtilpasninger) og påviste op til `1,45 km/s` metodeafhængig forskel mellem enkeltorden og samlet spektrum ved `D002-0061`.
   - [`D077`](docs/reports_d035_d077/SETI_D077_FEROS_WLC_METADATA_GATE_2026-11-14.md) verificerede samtlige **30 deklarerede `ThAr+Ne` dagslys-WLC kalibreringsråfiler** (`73/73` HTTP 200 arkivsvar, `0` FITS-kroppe hentet): identisk CCD-udlæsning (`49/49` kort), tretrins eksponeringsstige (`2×30 s + 2×150 s + 2×300 s`, `BOTHFIBS`, `ND = 0,0`) optaget `9,18–11,93 timer` før stjernen (`SKYFIB`, `ND = 1,301`), samt fravær af offentlige `ThArNe*` master-wave-tabeller i ESO `ObsCore`.

---

## Metodiske grundprincipper

1. **Prospektiv metodelåsning (`METHOD_LOCK.json`):** Input-hashes, forespørgsler, masker, modeller og beslutningskriterier fryses *før* nye spektral- eller arkivværdier inspiceres.
2. **Uafhængig numerisk efterregning (`NUMERICAL_AUDIT.json`):** Hver fase revideres med en separat implementation (f.eks. eksplicit Householder/Givens QR eller 50-cifret `Decimal`-aritmetik mod produktionens lineære solver). En intern audit verificerer regnepræcision — den udgør ikke ekstern fagfællebedømmelse.
3. **Fuld bevaring af nulresultater og fejlflag:** Signerede residualer, fejlede kvalitetskrav og skiftende fortegn over alternative baggrunde gemmes urørt; gentagne modeller på de samme fotoner tælles aldrig som uafhængige observationer.

---

## Navigation og reproduktion

- **Dokumentation og historik:**
  - [`CONTINUE_SETI.md`](CONTINUE_SETI.md) — Aktiv teknisk overdragelse og køreplan (`D078` og `V3`).
  - [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md) — Komplet indeks over alle rapporter i `D001`–`D077`.
  - [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md) — Forklaring af repositoriets mappestruktur, forseglede rod-manifests og kompagnonarkiver.
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
- **Verifikation af den optiske `FEROS`-arbejdskæde gennem `D077` (i projektmappen med kompagnonarkiverne A, B og C):**
  ```bash
  python3 restore_d077_workspace.py --check-only
  OPENBLAS_NUM_THREADS=1 .venv/bin/python analysis_workspace/work_feros_20261114_d077_wlc_metadata_gate/verify.py --recompute
  ```
