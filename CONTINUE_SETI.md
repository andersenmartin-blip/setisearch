# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 16. november 2026 · **Aktivt videnskabeligt checkpoint:** `D084` afsluttet (Nordlig dual-observatorie 4-kanals `NORTHERN_V3_5` kampagne på `25` nye nordlige stjerner / `183` `HARPS-N` + `CARMENES_VIS` eksponeringer + samlet **`125`-stjerners / `832`-eksponeringers (`180,82 t`, `6` spektrografer) all-sky `V3.0–V3.5`-syntese**, **`136`-systems multi-messenger syntese** med `Parkes`/`GBT` `1,4 GHz` radio [`13` direkte overlaps] og `TESS`, samt færdigkompileret `12`-siders to-spaltet publikations-PDF; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D084`, `0,38–2,48 µm`, `125` unikke all-sky echelle-stjerner, `832` eksponeringer + `136`-systems multi-messenger syntese):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf), [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D084` — Trin 7 `NORTHERN_V3_5` nordlig kampagne, `125`-stjerners all-sky syntese & `136`-systems multi-messenger syntese):** [`progress/2026-11-16-northern-d084-v3-5/RESULTS_REPORT.md`](progress/2026-11-16-northern-d084-v3-5/RESULTS_REPORT.md), [`results/SUMMARY.json`](progress/2026-11-16-northern-d084-v3-5/results/SUMMARY.json), [`FORENSIC_CANDIDATE_AUDIT_D084.json`](progress/2026-11-16-northern-d084-v3-5/FORENSIC_CANDIDATE_AUDIT_D084.json), [`results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_53STARS.csv`](progress/2026-11-16-northern-d084-v3-5/results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_53STARS.csv), [`results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_125STARS.csv`](progress/2026-11-16-northern-d084-v3-5/results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_125STARS.csv) og [`results/MULTIMESSENGER_ECHELLE_RADIO_TESS_136SYSTEMS.csv`](progress/2026-11-16-northern-d084-v3-5/results/MULTIMESSENGER_ECHELLE_RADIO_TESS_136SYSTEMS.csv).
3. **Indeks for hele det pankromatiske `V3.0–V3.5`-survey (`D079–D084`, `125` stjerner, `832` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–J:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D084"`), `FORTSAET_FRA_D084.md`, dedikeret `.venv` (inkl. lokal `tectonic`-kompiler), fulde arkiv-inputcaches `inputs_d079_v3/` .. `inputs_d084_v3_5/`, alle ti kompagnonarkiver A–J (senest `SETI_D084_V3_5_NORTHERN_10PC_AND_125STAR_RESULTS_2026-11-16.zip` = `10.117.107` B) og `restore_d084_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`/usr/bin/python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `167` unikke tidligere undersøgte echelle-mål (`42` i `C001–D078` + `100` sydlige i `D079–D083` + `25` nordlige i `D084`) og `1.204` ekskluderede eksponeringer (`1.021` før `D084` + `183` i `D084`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037`, `D002–D034`, `work_rubin_20261102`, `HD 43629` (`D035–D078`), `M10–M36` radiomanifesterne samt de låste `D079–D084`-arbejdsmapper (kompagnonarkiver A–J) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.
- **Streng GitHub-afgrænsning:** Alle leverancer og PDF-manuskripter gemmes udelukkende i projektmappen og pushes kun til dette GitHub-repositorium (`external_contacts == 0`).

---

## 3. Mulige fremtidige forskningsretninger efter `D084` (Trin 8)

Med `Trin 2–7` (`D079–D084`, `125` unikke echelle-stjerner på tværs af begge halvkugler + `136`-systems multi-messenger syntese) afsluttet og kompileret til `12`-siders PDF i [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf) peger tre naturlige `Trin 8`-spor fremad:
1. **`CARMENES_NIR` (`0,96–1,71 µm`, Calar Alto) på de nordlige `< 10 pc` M-dværge:** Lukker den fysiske VIS/NIR dikroiske afskæring over `995 nm` på `Wolf 359`, `DX Cnc`, `Lalande 21185` og `GJ 486` ved `1064,1 nm` (`Nd:YAG`) og `1550,0 nm` (`Er` C-bånd).
2. **`CRIRES+` $L/M$-bånd (`2,9–5,3 µm`) eller høj-specificitet sparsomt `G6` airglow-atlas:** Direkte afprøvning af termiske `3–5 µm` kvantekaskade-lasere eller et sparsomt `~0,5–1 top/Å` airglow-atlas, der bevarer `~95 %` sand laser-komplethed ved `100 %` OH/pixel-afvisning.
3. **Kohærent multi-linje laser-frekvenskam-søgning (`V4`):** Søgning efter periodiske frekvenskam-mønstre ($\Delta\nu = \mathrm{konst.}$ eller $\Delta\lambda/\lambda = \mathrm{konst.}$) under enkeltlinje-`8σ`-grænsen tværs over hele den allerede kalibrerede `125`-stjerners `0,38–2,48 µm` database (`832` spektrer).
