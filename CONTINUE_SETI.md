# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 15. november 2026 · **Aktivt videnskabeligt checkpoint:** `D081` afsluttet (4-kanals `ECELLE_V3_2` transit-kinematisk de-Doppler og `< 10 pc` sol-nabolags-survey gennemført på `22` friske FGKM-stjerner / `159` `HARPS` + VLT `ESPRESSO`-eksponeringer; **`60` unikke stjerner / `349` eksponeringer** samlet over `D079–D081`; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Seneste afsluttede fase (`D081` — Trin 4 `ECELLE_V3_2` transit-kinematik & `< 10 pc` syntese):** [`progress/2026-11-15-echelle-d081-v3-2/REPORT.md`](progress/2026-11-15-echelle-d081-v3-2/REPORT.md), [`SUMMARY.json`](progress/2026-11-15-echelle-d081-v3-2/SUMMARY.json), [`TRANSIT_CAMPAIGN_RESULTS_7.csv`](progress/2026-11-15-echelle-d081-v3-2/TRANSIT_CAMPAIGN_RESULTS_7.csv), [`SOLAR_NEIGHBORHOOD_10PC_SYNTHESIS.csv`](progress/2026-11-15-echelle-d081-v3-2/SOLAR_NEIGHBORHOOD_10PC_SYNTHESIS.csv), [`MULTI_PHASE_V3_SYNTHESIS_60STARS.csv`](progress/2026-11-15-echelle-d081-v3-2/MULTI_PHASE_V3_SYNTHESIS_60STARS.csv) og [`SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_SURVEY_2026-11-15.md`](docs/reports_d035_d077/SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_SURVEY_2026-11-15.md).
2. **Indeks for det kalibrerede `V3.0–V3.2`-survey (`D079–D081`, `60` stjerner):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
3. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
4. **Repositoriets opbygning og kompagnonarkiver A–G:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
5. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D081"`), dedikeret `.venv`, fulde ESO-inputcaches `inputs_d079_v3/`, `inputs_d080_v3_1/` og `inputs_d081_v3_2/`, alle syv kompagnonarkiver A–G (`45.920.303` B / `28.329.072` B / `659.654` B / `11.427.944` B / `5.770.342` B / `7.736.372` B / `8.045.722` B) og `restore_d081_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`python3 -S audit.py`).
- **Nul mål- og eksponeringsoverlap:** Alle `102` tidligere undersøgte mål (`80` før `D081` + `22` i `D081`) og `712` ESO `dp_id` (`553` før `D081` + `159` i `D081`) ekskluderes ved ny kohorteudvælgelse (medmindre en helt ny bølgelængdekanal som nær-infrarød `NIRPS` `0,98–1,80 µm` åbnes eksplicit).
- **Lukkede køer genåbnes ikke:** `C037` (`90`-køen), `D002–D034` (`141`-køen), `work_rubin_20261102` og `HD 43629` (`D035–D078`) forbliver lukkede, og de `107.105` historiske `D077`-tabelceller forbliver frosne.

---

## 3. Næste mulige hovedfase — Trin 5 (`D082`)

Med `60` unikke stjerner og `349` højopløste optiske eksponeringer (`3800–7860 Å`) afsluttet gennem `ECELLE_V3_2` peger projektet naturligt på to muligheder for **Trin 5 (`D082`)**:
1. **Nær-infrarød echelle-udvidelse (`ESO NIRPS`, `0,98–1,80 µm`, $R \approx 80\,000$–$100\,000$):** Udvid `ECELLE_V3_2` til YJH-båndet omkring de industrielle og interstellare telekommunikationsbølgelængder **`1064 nm` (`Nd:YAG`/`Yb`) og `1550 nm` (`Er`-fiberlaser)** på sene M-dværge med beboelige planeter (`Proxima Cen`, `LHS 1140`, `TRAPPIST-1` / `GJ 1002`), hvor M-dværges kontinuum og atmosfærisk transmission er optimal.
2. **Samlet videnskabeligt publikationsmanuskript (`D079–D081`):** Sammenskrivning af hele det `60`-stjerners optiske `HARPS + VLT ESPRESSO`-survey (`4.539` syntetiske kalibreringsforsøg, Keplerisk planet-spor de-Doppler og Watt-skala grænser inden for `10 pc`) til en artikel i *AJ* / *A&A* / *RAS Techniques and Instruments*.
