# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 14. november 2026 · **Aktivt videnskabeligt checkpoint:** `D079` afsluttet (`HARPS_ECELLE_V3` prospektivt kalibreret og gennemført på `10` friske sol-analoge stjerner + `2` kontrolstjerner; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Seneste afsluttede fase (`D079` — Trin 2 `HARPS_ECELLE_V3` kalibreret survey):** [`progress/2026-11-14-harps-d079-v3/REPORT.md`](progress/2026-11-14-harps-d079-v3/REPORT.md), [`SUMMARY.json`](progress/2026-11-14-harps-d079-v3/SUMMARY.json), [`FORENSIC_VETTING_176.csv`](progress/2026-11-14-harps-d079-v3/FORENSIC_VETTING_176.csv), [`STAR_UPPER_LIMITS_80.csv`](progress/2026-11-14-harps-d079-v3/STAR_UPPER_LIMITS_80.csv) og [`SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_2026-11-14.md`](docs/reports_d035_d077/SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_2026-11-14.md).
2. **Indeks for det kalibrerede `V3`-survey (`D079+`):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
3. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
4. **Repositoriets opbygning og kompagnonarkiver A–E:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
5. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D079"`), dedikeret `.venv`, fuld ESO-inputcache `inputs_d079_v3/`, alle fem kompagnonarkiver A–E (`45.920.303` B / `28.329.072` B / `659.654` B / `11.427.944` B / `5,770,342` B) og `restore_d079_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier, algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af en uafhængig ren-stdlib numerisk revision (`python3 -S audit.py`).
- **Bevaring af alle resultater, kontrolrater og kørselsfejl:** Tekniske opdagelser (såsom HARPS Fiber B's `71` mod Fiber A's `72` echelle-ordener ved orden `45` / `5277,2 Å`) og nominelle kontrolrater (`28` kontrol mod `148` science `G1–G5`-passager før forensisk `F1+F2`-veto i `D079`) bevares åbent i `IMPLEMENTATION_LOCK.json` og CSV-tabellerne. Retroaktiv skjult tærskeljustering er forbudt.
- **Fysiske koordinater og enheder:** Reducerede ESO HARPS/FEROS `S1D`-spektre er i **barycentriske luftbølgelængder (`Å`)**; nativ `_e2ds_A`/`_e2ds_B` bølgelængdepolynomier er i **topocentriske luftbølgelængder (`Å`)** og transformeres med $(1 + \mathrm{BERV}/c)$.
- **Lukkede køer genåbnes ikke:** `C037` (`90`-køen), `D002–D034` (`141`-køen), `work_rubin_20261102` og `HD 43629` (`D035–D078`) forbliver lukkede, og de `107.105` historiske `D077`-tabelceller forbliver frosne.

---

## 3. Aktiv videnskabelig køreplan — Trin 3 (`D080`: Opgraderet `HARPS_ECELLE_V3.1` & skaleret survey)

`D079` diagnosticerede med `100 %` fysisk klarhed de to eneste tilbageværende systematikker i `V3.0` og definerer dermed **Trin 3 (`D080`)**:

1. **Opgradering til `HARPS_ECELLE_V3.1` før næste metodelås:**
   - **Kanal P Gate G1 (`Supraphotosfærisk kontinuum-gate + 2D [Teff, [M/H]]-atlas`):** Indbyg `Test F1` (`fn_pk3 >= 1,02`) og 2-parameter metallinjeskalering direkte i `v3_detector.py`, så sub-kontinuum absorptions-mismatches (`166/166` i `D079`) frasorteres straks i 1D-screeningen.
   - **Gate G5 (`Fuld 5 × 11 separabel 2D fiber-LSF + 3-rækkers centroid-stationaritet`):** Indbyg `Test F2` (`cos_2d_5x11 >= 0,85`, `max_3row_dx_px <= 0,85`, `far_wing_34_ratio <= 0,55`) direkte i `Gate G5`, så skrå kosmiske myonspor der krydser fibercenteret i en enkelt række (`10/10` i `D079`) afvises automatisk ved selve 2D-gaten.
2. **Skalering til `50–100` nære FGKM- og exoplanet-værtsstjerner (`HARPS` + VLT `ESPRESSO`):**
   - Udvid søgningen til en større volumenbegrænset prøve (`d < 30–50 pc`, nul overlap med alle `52` hidtil undersøgte stjerner) inkl. kendte transiterende og RV-exoplaneter med eksplicit banefase-logning og VLT `ESPRESSO` ($R \approx 140\,000$, `8,2 m` spejl), som sænker lasereffekt-grænsen ned mod få kilowatt.
