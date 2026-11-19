# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 19. november 2026 · **Aktivt videnskabeligt checkpoint:** `D088` afsluttet (`OHP_SOPHIE` + `OHP_ELODIE` + `CFHT_ESPADONS` `NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_V3_9` på `25` stjerner [`20` helt nye + `5` broer] / `176` eksponeringer + retroaktiv uniform `COMB_V4_1`-sweep på samtlige **`1.567` eksponeringer / `247` stacks (`100 %` af `D079–D088`)** + samlet **`220`-stjerners / `1.567`-eksponeringers (`365,80 t`, `12` spektrografer [`13` arme], `4,457` oktaver `0,1145–2,515 µm`) all-sky syntese**, **`117` `< 10 pc` stjerner** [`1,7757 kW` median; **`0,0973 W` (`97,3 mW`)** rekord på `Proxima Centauri` i rum-FUV; `0,5181 kW` `GJ 625` på `OHP_SOPHIE`], **`21` broer (`415` celler)**, **`70` orbitale kampagner**, **`23/23` (`100 %`) `Parkes`/`GBT` `1,4 GHz` radio-echelle lukning** [`24` direkte overlaps inkl. `TESS` `L 98-59`], `16/16` ren-stdlib audit `PASS`, samt opdateret to-spaltet publikations-PDF; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D088`, `4,457` oktaver `0,1145–2,515 µm`, `220` unikke all-sky + rum echelle-stjerner, `1.567` eksponeringer, `12` spektrografer / `13` arme, `117` `< 10 pc` + `23/23` radio-echelle lukning + `100 %` all-sky `COMB_V4_1`):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf), [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D088` — Trin 11 `NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_V3_9`, `220`-stjerners & `23/23` syntese):** [`progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/RESULTS_REPORT.md`](progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/RESULTS_REPORT.md), [`results/SUMMARY.json`](progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/results/SUMMARY.json), [`FORENSIC_CANDIDATE_AUDIT_D088.json`](progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/FORENSIC_CANDIDATE_AUDIT_D088.json), [`results/ALLSKY_COMB_V4_1_UNIFIED_D079_D088.csv`](progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D088.csv), [`results/PANCHROMATIC_BRIDGE_21STARS.csv`](progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/results/PANCHROMATIC_BRIDGE_21STARS.csv), [`results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_117STARS.csv`](progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_117STARS.csv), [`results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_220STARS.csv`](progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_220STARS.csv) og [`results/MULTIMESSENGER_ECHELLE_RADIO_TESS_220SYSTEMS.csv`](progress/2026-11-18-northern-radio23-d088-v3-9-comb-v4-1/results/MULTIMESSENGER_ECHELLE_RADIO_TESS_220SYSTEMS.csv).
3. **Indeks for hele det pankromatiske `D079–D088`-survey (`220` stjerner, `1.567` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–N:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe:** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D088"`), `FORTSAET_FRA_D088.md`, dedikeret `.venv` (inkl. `tectonic`), fulde arkiv-inputcaches `inputs_d079_v3/` .. `inputs_d088_v3_9/`, alle fjorten kompagnonarkiver A–N (senest `SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip` = `9.492.762` B, SHA-256 `c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d`) og `restore_d088_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`/usr/bin/python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `262` unikke tidligere undersøgte echelle-mål (`42` i `C001–D078` + `220` i `D079–D088`) og `1.945` ekskluderede eksponeringer (`1.769` før `D088` + `176` i `D088`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037`, `D002–D034`, `work_rubin_20261102`, `HD 43629` (`D035–D078`), `M10–M36` radiomanifesterne samt de låste `D079–D088`-arbejdsmapper (kompagnonarkiver A–N) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.
- **Streng GitHub-afgrænsning:** Alle leverancer og PDF-manuskripter gemmes udelukkende i projektmappen og pushes kun til dette GitHub-repositorium (`external_contacts == 0`).

---

## 3. Mulige fremtidige forskningsretninger efter `D088` (`Trin 12` / `D089+`)

Med `Trin 2–11` (`D079–D088`, `220` unikke echelle-stjerner over `4,457` oktaver `0,1145–2,515 µm`, `100 %` `23/23` radio-echelle lukning samt `100 %` all-sky `COMB_V4_1`-udrulning) afsluttet peger næste mulige skridt mod:
1. **`CRIRES+` $L/M$-bånd (`2,9–5,3 µm`):** Termisk `3–5 µm` kvantekaskadelaser-søgning udenfor det eksisterende `0,1145–2,515 µm` område.
2. **`HST/COS` FUV (`G130M/G160M`, `0,115–0,180 µm`) / `JWST` `NIRSpec`/`MIRI`:** Udvidelse af det sub-watt rum-UV-regime (`0,0973 W` på Proxima Cen) til yderligere `< 5 pc` M-dværge.
