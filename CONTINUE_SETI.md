# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 19. november 2026 · **Aktivt videnskabeligt checkpoint:** `D089` afsluttet (`FUSE` + `HST/COS G130M` + `HST/STIS E230M/E230H` `SPACE_LYMAN_FUV_NUV_V4_0` på `37` stjerner [`30` helt nye (`4 < 10 pc`: `ALPCENA`, `PROCYON`, `GJ667C`, `GJ367`) + `7` broer] / `192` eksponeringer + uniform `COMB_V4_1`-sweep på samtlige **`1.759` eksponeringer / `284` stacks (`100 %` af `D079–D089`)** + samlet **`250`-stjerners / `1.759`-eksponeringers (`569,36 t`, `14` spektrografer [`16` arme], `4,796` oktaver `0,0905–2,515 µm`) all-sky syntese**, **`121` `< 10 pc` stjerner** [`1,7494 kW` median; **`0,0973 W`** rekord på `Proxima Centauri` i `HST_STIS`, **`0,2194 W`** `GJ 832` i `HST_COS`, **`0,4294 W`** `ALPCENA` i `FUSE`], **`26` broer (`485` celler)**, **`80` orbitale kampagner**, **`23/23` (`100 %`) `Parkes`/`GBT` `1,4 GHz` radio-echelle lukning** [`24` direkte overlaps inkl. `TESS` `L 98-59`], `16/16` ren-stdlib audit `PASS`, samt opdateret to-spaltet publikations-PDF; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D089`, `4,796` oktaver `0,0905–2,515 µm`, `250` unikke rum- + all-sky echelle-stjerner, `1.759` eksponeringer, `14` spektrografer / `16` arme, `121` `< 10 pc` + `23/23` radio-echelle lukning + `100 %` all-sky `COMB_V4_1`):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf), [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D089` — Trin 12 `SPACE_LYMAN_FUV_NUV_V4_0`, `250`-stjerners & `4,796`-oktav syntese):** [`progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/RESULTS_REPORT.md`](progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/RESULTS_REPORT.md), [`results/SUMMARY.json`](progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/results/SUMMARY.json), [`FORENSIC_CANDIDATE_AUDIT_D089.json`](progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/FORENSIC_CANDIDATE_AUDIT_D089.json), [`results/ALLSKY_COMB_V4_1_UNIFIED_D079_D089.csv`](progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D089.csv), [`results/PANCHROMATIC_BRIDGE_26STARS.csv`](progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/results/PANCHROMATIC_BRIDGE_26STARS.csv), [`results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_121STARS.csv`](progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_121STARS.csv), [`results/UNIFIED_PANCHROMATIC_V4_SYNTHESIS_250STARS.csv`](progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/results/UNIFIED_PANCHROMATIC_V4_SYNTHESIS_250STARS.csv) og [`results/MULTIMESSENGER_ECHELLE_RADIO_TESS_250SYSTEMS.csv`](progress/2026-11-19-space-lyman-fuv-nuv-d089-v4-0/results/MULTIMESSENGER_ECHELLE_RADIO_TESS_250SYSTEMS.csv).
3. **Indeks for hele det pankromatiske `D079–D089`-survey (`250` stjerner, `1.759` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–O:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe:** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D089"`), `FORTSAET_FRA_D089.md`, dedikeret `.venv` (inkl. `tectonic`), fulde arkiv-inputcaches `inputs_d079_v3/` .. `inputs_d089_v4_0/`, alle femten kompagnonarkiver A–O (senest `SETI_D089_V4_0_SPACE_LYMAN_FUV_NUV_RESULTS_2026-11-19.zip` = `4.262.551` B, SHA-256 `4864dd3b5c0e958e428e1af815e1a378a37824d6bc87a89de9c223d89bccd723`) og `restore_d089_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`/usr/bin/python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `292` unikke tidligere undersøgte echelle-mål (`42` i `C001–D078` + `250` i `D079–D089`) og `2.142` ekskluderede eksponeringer (`1.950` før `D089` + `192` i `D089`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037`, `D002–D034`, `work_rubin_20261102`, `HD 43629` (`D035–D078`), `M10–M36` radiomanifesterne samt de låste `D079–D089`-arbejdsmapper (kompagnonarkiver A–O) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.
- **Streng GitHub-afgrænsning:** Alle leverancer og PDF-manuskripter gemmes udelukkende i projektmappen og pushes kun til dette GitHub-repositorium (`external_contacts == 0`).

---

## 3. Mulige fremtidige forskningsretninger efter `D089` (`Trin 13` / `D090+`)

Med `Trin 2–12` (`D079–D089`, `250` unikke echelle-stjerner over `4,796` oktaver `0,0905–2,515 µm`, `100 %` `23/23` radio-echelle lukning samt `100 %` all-sky `COMB_V4_1`-udrulning) afsluttet peger næste mulige skridt mod:
1. **`CRIRES+` $L/M$-bånd (`2,9–5,3 µm`):** Termisk `3–5 µm` kvantekaskadelaser-søgning udenfor det eksisterende `0,0905–2,515 µm` område.
2. **`JWST` `NIRSpec`/`MIRI` højopløsning (`0,6–28 µm`):** Udvidelse af den pankromatiske rum-IR-dækning hinsides det nuværende `2,515 µm` loftsgrænse.
