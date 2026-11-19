# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 19. november 2026 · **Aktivt videnskabeligt checkpoint:** `D090` afsluttet (`JWST NIRSpec G235H/F170LP` + `NIRSpec G395H/F290LP` + `MIRI MRS Ch1–4` `JWST_SPACE_THERMAL_IR_V4_1` på `37` stjerner [`30` helt nye (`4 < 10 pc`: `WISE0855`, `VMA2`, `LAWD37`, `J2148`) + `7` broer] / `161` parrede eksponeringer [`322` L2 `*_x1d.fits`] + uniform `COMB_V4_1`-sweep på samtlige **`1.920` eksponeringer / `321` stacks (`100 %` af `D079–D090`)** + samlet **`280`-stjerners / `1.920`-eksponeringers (`587,0558 t`, `16` spektrografer [`19` arme], `8,273` oktaver `0,0905–28,00 µm`) all-sky & rum-IR syntese**, **`125` `< 10 pc` stjerner** [`1,74941 kW` median; **`0,0973 W`** rekord på `Proxima Centauri` i `HST_STIS`, **`0,2194 W`** `GJ 832` i `HST_COS`, **`0,4294 W`** `ALPCENA` i `FUSE`, **`228,98 W`** `WISE0855` i `JWST_MIRI_MRS` `5,80 µm`, **`2,70465 kW`** `VMA2` ved `10,60 µm` CO2], **`30` broer (`550` celler)**, **`90` orbitale kampagner**, **`23/23` (`100 %`) `Parkes`/`GBT` `1,4 GHz` radio-echelle lukning** [`24` direkte overlaps inkl. `TESS` `L 98-59` og **`16CYGB` som tri-regime Radio + Optisk + MIRI bro**], `16/16` ren-stdlib audit `PASS`, Project Hephaistos `OBJECT_D`/`OBJECT_E` (`prop 7199`) forensisk lukket [`0` ETI], samt opdateret to-spaltet publikations-PDF; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D090`, `8,273` oktaver `0,0905–28,00 µm`, `280` unikke rum- + all-sky stjerner, `1.920` eksponeringer, `16` spektrografer / `19` arme, `125` `< 10 pc` + `23/23` radio-echelle lukning + `100 %` all-sky `COMB_V4_1`):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf), [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D090` — Trin 13 `JWST_SPACE_THERMAL_IR_V4_1`, `280`-stjerners & `8,273`-oktav syntese):** [`progress/2026-11-19-jwst-thermal-ir-d090-v4-1/RESULTS_REPORT.md`](progress/2026-11-19-jwst-thermal-ir-d090-v4-1/RESULTS_REPORT.md), [`results/SUMMARY.json`](progress/2026-11-19-jwst-thermal-ir-d090-v4-1/results/SUMMARY.json), [`FORENSIC_CANDIDATE_AUDIT_D090.json`](progress/2026-11-19-jwst-thermal-ir-d090-v4-1/FORENSIC_CANDIDATE_AUDIT_D090.json), [`results/ALLSKY_COMB_V4_1_UNIFIED_D079_D090.csv`](progress/2026-11-19-jwst-thermal-ir-d090-v4-1/results/ALLSKY_COMB_V4_1_UNIFIED_D079_D090.csv), [`results/PANCHROMATIC_BRIDGE_30STARS.csv`](progress/2026-11-19-jwst-thermal-ir-d090-v4-1/results/PANCHROMATIC_BRIDGE_30STARS.csv), [`results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_125STARS.csv`](progress/2026-11-19-jwst-thermal-ir-d090-v4-1/results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_125STARS.csv), [`results/UNIFIED_PANCHROMATIC_V4_1_SYNTHESIS_280STARS.csv`](progress/2026-11-19-jwst-thermal-ir-d090-v4-1/results/UNIFIED_PANCHROMATIC_V4_1_SYNTHESIS_280STARS.csv) og [`results/MULTIMESSENGER_ECHELLE_RADIO_TESS_280SYSTEMS.csv`](progress/2026-11-19-jwst-thermal-ir-d090-v4-1/results/MULTIMESSENGER_ECHELLE_RADIO_TESS_280SYSTEMS.csv).
3. **Indeks for hele det pankromatiske `D079–D090`-survey (`280` stjerner, `1.920` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–P:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe:** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D090"`), `FORTSAET_FRA_D090.md`, dedikeret `.venv` (inkl. `tectonic`), fulde arkiv-inputcaches `inputs_d079_v3/` .. `inputs_d090_v4_1/`, alle seksten kompagnonarkiver A–P (senest `SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip` = `8.610.790` B, SHA-256 `2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a`) og `restore_d090_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`/usr/bin/python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `322` unikke tidligere undersøgte echelle/rum-IR mål (`42` i `C001–D078` + `280` i `D079–D090`) og `2.303` ekskluderede eksponeringer (`2.142` før `D090` + `161` parrede i `D090`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037`, `D002–D034`, `work_rubin_20261102`, `HD 43629` (`D035–D078`), `M10–M36` radiomanifesterne samt de låste `D079–D090`-arbejdsmapper (kompagnonarkiver A–P) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.
- **Streng GitHub-afgrænsning:** Alle leverancer og PDF-manuskripter gemmes udelukkende i projektmappen og pushes kun til dette GitHub-repositorium (`external_contacts == 0`).

---

## 3. Mulige fremtidige forskningsretninger efter `D090` (`Trin 14` / `D091+`)

Med `Trin 2–13` (`D079–D090`, `280` unikke stjerner over ubrudte `8,273` oktaver `0,0905–28,00 µm`, `100 %` `23/23` radio-echelle lukning samt `100 %` all-sky `COMB_V4_1`-udrulning) afsluttet peger næste naturlige skridt mod:
1. **Højopløsnings $L/M$-bånd (`CRIRES+` `2,9–5,3 µm`, $R \approx 86{.}000$):** `30×` finere spektral opløsning end JWST `NIRSpec G395H` (`R=2.700`) over det termiske `3–5 µm` vindue for `< 10 pc` stjerner og transiterende planeter.
2. **Ekstremt højopløste radio/mm/sub-mm broer (`ALMA` / `MeerKAT` / `ASKAP`) & `JWST` `NIRSpec`/`MIRI` udvidelse (`> 280` stjerner):** Målrettede opfølgninger på yderligere `< 10 pc` G/K/M-stjerner og transiterende exoplanetværter.
