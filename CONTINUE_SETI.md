# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 14. november 2026 · **Aktivt videnskabeligt checkpoint:** `D080` afsluttet (`ECELLE_V3_1` prospektivt kalibreret og gennemført på `26` friske FGKM- og exoplanet-stjerner / `130` `HARPS` + VLT `ESPRESSO`-eksponeringer; `38` stjerner / `190` eksponeringer samlet over `D079–D080`; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Seneste afsluttede fase (`D080` — Trin 3 `ECELLE_V3_1` multi-instrument exoplanet-survey):** [`progress/2026-11-14-echelle-d080-v3-1/REPORT.md`](progress/2026-11-14-echelle-d080-v3-1/REPORT.md), [`SUMMARY.json`](progress/2026-11-14-echelle-d080-v3-1/SUMMARY.json), [`THREE_GEN_BENCHMARK_130.csv`](progress/2026-11-14-echelle-d080-v3-1/THREE_GEN_BENCHMARK_130.csv), [`STAR_UPPER_LIMITS_186.csv`](progress/2026-11-14-echelle-d080-v3-1/STAR_UPPER_LIMITS_186.csv), [`EXOPLANET_PHASE_COVERAGE_110.csv`](progress/2026-11-14-echelle-d080-v3-1/EXOPLANET_PHASE_COVERAGE_110.csv) og [`SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_SURVEY_2026-11-14.md`](docs/reports_d035_d077/SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_SURVEY_2026-11-14.md).
2. **Indeks for det kalibrerede `V3 / V3.1`-survey (`D079–D080`):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
3. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
4. **Repositoriets opbygning og kompagnonarkiver A–F:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
5. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D080"`), dedikeret `.venv`, fulde ESO-inputcaches `inputs_d079_v3/` og `inputs_d080_v3_1/`, alle seks kompagnonarkiver A–F (`45.920.303` B / `28.329.072` B / `659.654` B / `11.427.944` B / `5.770.342` B / `7.736.372` B) og `restore_d080_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (inkl. eksplicit `obs_release_date <= current_utc` mod ESO's 1-årige proprietære embargo), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af en uafhængig ren-stdlib numerisk revision (`python3 -S audit.py`).
- **Bevaring af alle resultater, kontrolrater og arkivopdagelser:** Både `D079` (`Fiber B` `71`-mod-`72` ordener) og `D080` (`HTTP 401` proprietære `2027`-rækker udskiftet før spektral indlæsning i `IMPLEMENTATION_LOCK.json`) bevares åbent med `FROZEN_PRE_INGESTION/`.
- **Fysiske koordinater og enheder:** Reducerede ESO HARPS/FEROS/ESPRESSO `S1D`-spektre og ESPRESSO `S2D_BLAZE_A` (`WAVEDATA_AIR_BARY`) er i **barycentriske luftbølgelængder (`Å`)**; nativ HARPS `_e2ds_A`/`_e2ds_B` er i **topocentriske luftbølgelængder (`Å`)** og transformeres med $(1 + \mathrm{BERV}/c)$.
- **Lukkede køer genåbnes ikke:** `C037` (`90`-køen), `D002–D034` (`141`-køen), `work_rubin_20261102` og `HD 43629` (`D035–D078`) forbliver lukkede, og de `107.105` historiske `D077`-tabelceller forbliver frosne.

---

## 3. Aktiv videnskabelig køreplan — Trin 4 (`D081`: Konjunktions-synkroniserede transit-tidsserier & `< 10 pc` volumen-syntese)

Med `ECELLE_V3_1` valideret på tværs af både `HARPS` og VLT `ESPRESSO` (`38` friske stjerner / `190` eksponeringer over `D079 + D080`, `0` kosmiske 2D-artefakter tilbage i kalibreringen, nul ETI-laser-overskud mod kontrolstjernerne og sub-kilowatt til kilowatt-følsomhed ned til `0,91 kW`) er næste oplagte hovedfase **Trin 4 (`D081`)**:
1. **In-transit tidsserier (Rossiter-McLaughlin arkivsekvenser på `HARPS` + VLT `ESPRESSO`) + fuldt Paranal/La Silla `OH Meinel / Hg I` airglow-atlas i `Gate G2`:** Udvid `Gate G2` med et komplet `UVES/ESPRESSO` nattehimlens `OH Meinel + O2 + Hg I`-linjeatlas til `FP`/`THAR2`-eksponeringer uden simultan skyfiber, og gennemsøg sammenhængende transitnætter (`20–60` eksponeringer hen over selve planettransitten $|\phi| < 0,02$) for både stationære stjerne-hvileramme-lasere og planet-accelererende emissionslinjer langs exoplanetens kendte banehastighedskurve $v_p(t) = v_* + K_p \sin(2\pi \phi(t))$.
2. **Volumen-komplet `< 10 pc` syntese:** Kombinér resultaterne i en publikationsklar grænseflade over sendereffekt mod pligtfaktor (duty cycle) for Solens nærmeste nabostjerner.
