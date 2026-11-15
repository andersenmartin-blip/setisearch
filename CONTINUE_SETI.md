# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 15. november 2026 · **Aktivt videnskabeligt checkpoint:** `D083` afsluttet (4-kanals `CRIRES_V3_4` termisk nær-infrarød `1,95–2,48 µm` $K$-båndssurvey på `22` stjerner / `148` VLT `CRIRES+`-eksponeringer + samlet **`100`-stjerners / `649`-eksponeringers (`154,11 t`) pankromatisk `V3.0–V3.4`-syntese**, **`120`-systems multi-messenger syntese** med `Parkes`/`GBT` `1,4 GHz` radio og `TESS`, samt færdigkompileret to-spaltet publikations-PDF; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D083`, `0,38–2,48 µm`, `100` unikke echelle-stjerner, `649` eksponeringer + `120`-systems multi-messenger syntese):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf), [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D083` — Trin 6 `CRIRES_V3_4` $K$-båndssurvey, `100`-stjerners pankromatisk syntese & `120`-systems multi-messenger syntese):** [`progress/2026-11-15-crires-d083-v3-4/REPORT.md`](progress/2026-11-15-crires-d083-v3-4/REPORT.md), [`SUMMARY.json`](progress/2026-11-15-crires-d083-v3-4/SUMMARY.json), [`PANCHROMATIC_OPTICAL_NIR_KBAND_BRIDGE.csv`](progress/2026-11-15-crires-d083-v3-4/PANCHROMATIC_OPTICAL_NIR_KBAND_BRIDGE.csv), [`SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_35STARS.csv`](progress/2026-11-15-crires-d083-v3-4/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_35STARS.csv), [`UNIFIED_PANCHROMATIC_V3_SYNTHESIS_100STARS.csv`](progress/2026-11-15-crires-d083-v3-4/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_100STARS.csv), [`MULTIMESSENGER_ECHELLE_RADIO_TESS_SYNTHESIS.csv`](progress/2026-11-15-crires-d083-v3-4/MULTIMESSENGER_ECHELLE_RADIO_TESS_SYNTHESIS.csv) og [`SETI_D083_V3_4_CRIRES_KBAND_AND_100STAR_SURVEY_2026-11-15.md`](docs/reports_d035_d077/SETI_D083_V3_4_CRIRES_KBAND_AND_100STAR_SURVEY_2026-11-15.md).
3. **Indeks for det pankromatiske `V3.0–V3.4`-survey (`D079–D083`, `100` stjerner, `649` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–I:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D083"`), dedikeret `.venv` (inkl. lokal `tectonic`-kompiler), fulde ESO-inputcaches `inputs_d079_v3/`, `inputs_d080_v3_1/`, `inputs_d081_v3_2/`, `inputs_d082_v3_3/` og `inputs_d083_v3_4/`, alle ni kompagnonarkiver A–I (`45.920.303` B / `28.329.072` B / `659.654` B / `11.427.944` B / `5.770.342` B / `7.736.372` B / `8.045.722` B / `29.473.205` B / `5.549.428` B) og `restore_d083_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `142` unikke tidligere undersøgte echelle-mål (`42` i `C001–D078` + `100` unikke i `D079–D083`) og `1.021` ESO `dp_id` (`873` før `D083` + `148` i `D083`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037` (`90`-køen), `D002–D034` (`141`-køen), `work_rubin_20261102`, `HD 43629` (`D035–D078`), de forseglede `M10–M36` radiomanifester samt de låste `D079–D083`-arbejdsmapper (kompagnonarkiver A–I) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.
- **Streng GitHub-afgrænsning:** Alle leverancer og PDF-manuskripter gemmes udelukkende i projektmappen og pushes kun til dette GitHub-repositorium (`external_contacts == 0`).

---

## 3. Mulige fremtidige forskningsretninger efter `D083`

Med `Trin 2–6` (`D079–D083`, `100` unikke echelle-stjerner + `120`-systems multi-messenger syntese) komplet gennemført og kompileret til færdig PDF i [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf) peger tre naturlige næste forskningsspor fremad:
1. **Nordlige `< 10 pc` højopløsnings-echellearkiver (`HARPS-N` på TNG, `CARMENES` på Calar Alto eller `SPIRou` på CFHT):** Udvidelse af `V3`-frameworket til nordlige solnabolagsstjerner uden for ESO's sydlige dækningsfelt (`Lalande 21185`, `Ross 248`, `GX And`, `61 Cygni A/B`, `Struve 2398`).
2. **Automatiseret `V3.5` topocentrisk kryds-stjerne OH/detektor-koincidensgate & $L/M$-bånd (`CRIRES+` `2,9–5,3 µm`):** Direkte implementering af den empiriske `(wlen_id, ORDER, DETEC, XPOS)` topocentriske koincidensregel dokumenteret i `D083` samt udvidelse til termiske `3–5 µm` kvantekaskade-laservinduer.
3. **Kohærent multi-linje laser-frekvenskam-søgning (`V4`):** Søgning efter periodiske frekvenskam-mønstre ($\Delta\nu = \mathrm{konst.}$ eller $\Delta\lambda/\lambda = \mathrm{konst.}$) under tærsklen for enkeltlinje-`8σ`-detektion på tværs af de `100` allerede kalibrerede `0,38–2,48 µm`-stjerner.
