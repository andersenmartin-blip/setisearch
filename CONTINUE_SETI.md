# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 15. november 2026 · **Aktivt videnskabeligt checkpoint:** `D082` afsluttet (4-kanals `NIRPS_V3_3` nær-infrarød `0,98–1,80 µm` YJH-survey gennemført på `22` nære stjerner / `152` `NIRPS_HE`-eksponeringer + samlet **`80`-stjerners / `501`-eksponeringers pankromatisk `V3.0–V3.3`-syntese og publikationsmanuskript** over `D079–D082`; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D082`, `0,38–1,80 µm`, `80` unikke stjerner, `501` eksponeringer):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D082` — Trin 5 `NIRPS_V3_3` nær-IR YJH-survey & `80`-stjerners pankromatisk syntese):** [`progress/2026-11-15-nirps-d082-v3-3/REPORT.md`](progress/2026-11-15-nirps-d082-v3-3/REPORT.md), [`SUMMARY.json`](progress/2026-11-15-nirps-d082-v3-3/SUMMARY.json), [`PANCHROMATIC_2PC_BRIDGE_PROXIMA_BARNARDS.csv`](progress/2026-11-15-nirps-d082-v3-3/PANCHROMATIC_2PC_BRIDGE_PROXIMA_BARNARDS.csv), [`SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_29STARS.csv`](progress/2026-11-15-nirps-d082-v3-3/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_29STARS.csv), [`UNIFIED_PANCHROMATIC_V3_SYNTHESIS_80STARS.csv`](progress/2026-11-15-nirps-d082-v3-3/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_80STARS.csv) og [`SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_SURVEY_2026-11-15.md`](docs/reports_d035_d077/SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_SURVEY_2026-11-15.md).
3. **Indeks for det pankromatiske `V3.0–V3.3`-survey (`D079–D082`, `80` stjerner, `501` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–H:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D082"`), dedikeret `.venv`, fulde ESO-inputcaches `inputs_d079_v3/`, `inputs_d080_v3_1/`, `inputs_d081_v3_2/` og `inputs_d082_v3_3/`, alle otte kompagnonarkiver A–H (`45.920.303` B / `28.329.072` B / `659.654` B / `11.427.944` B / `5.770.342` B / `7.736.372` B / `8.045.722` B / `29.473.205` B) og `restore_d082_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `122` unikke tidligere undersøgte mål (`42` i `C001–D078` + `80` unikke i `D079–D082`) og `864` ESO `dp_id` (`712` før `D082` + `152` i `D082`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037` (`90`-køen), `D002–D034` (`141`-køen), `work_rubin_20261102`, `HD 43629` (`D035–D078`) samt de låste `D079–D082`-arbejdsmapper (kompagnonarkiver A–H) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.

---

## 3. Mulige fremtidige forskningsretninger efter `D082`

Med `Trin 2–5` (`D079–D082`) komplet gennemført og sammenskrevet i [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) står projektet ved en naturlig milepæl med tre mulige næste spor:
1. **Indsendelse / preprint-forberedelse af `D079–D082`-artiklen:** Kompiler [`paper/main.tex`](paper/main.tex) lokalt med TeX Live (`pdflatex`) til færdig PDF til *AJ* / *A&A* / *RAS Techniques and Instruments*.
2. **Termisk nær-IR `K`-bånd (`CRIRES+`, `1,9–2,5 µm`, $R \approx 100\,000$) eller nordlig halvkugle (`HARPS-N` / `CARMENES` / `SPIRou`):** Udvidelse af det 4-kanals pankromatiske framework til nordlige `< 10 pc`-exoplanetsystemer eller `2 µm` `Tm`/`Ho`-laserbånd.
3. **Multi-messenger optisk + radio krydssyntese:** Kobling af det `80`-stjerners echelle-katalog med `seti-repeater` GBT/Breakthrough Listen radio-de-Doppler grænser på fælles nære exoplanet-værter.
