# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 17. november 2026 · **Aktivt videnskabeligt checkpoint:** `D085` afsluttet (CFHT `3,6 m` SPIRou 5-kanals `SPIROU_V3_6_AND_COMB_V4` YJHK + frekvenskam-kampagne på `29` stjerner [`25` helt nye + `4` nordlige bro-lukninger] / `177` eksponeringer + samlet **`150`-stjerners / `1.009`-eksponeringers (`195,23 t`, `7` spektrografer) all-sky `V3.0–V4.0`-syntese**, **`160`-systems multi-messenger syntese** med `Parkes`/`GBT` `1,4 GHz` radio [`14` direkte overlaps inkl. $\rho$\,CrB / `M20`] og `TESS`, samt opdateret to-spaltet publikations-PDF; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D085`, `0,38–2,515 µm`, `150` unikke all-sky echelle-stjerner, `1.009` eksponeringer + `160`-systems multi-messenger syntese):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf), [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D085` — Trin 8 `SPIROU_V3_6_AND_COMB_V4` kampagne, `150`-stjerners all-sky syntese & `160`-systems multi-messenger syntese):** [`progress/2026-11-17-spirou-d085-v3-6-comb-v4/RESULTS_REPORT.md`](progress/2026-11-17-spirou-d085-v3-6-comb-v4/RESULTS_REPORT.md), [`results/SUMMARY.json`](progress/2026-11-17-spirou-d085-v3-6-comb-v4/results/SUMMARY.json), [`FORENSIC_CANDIDATE_AUDIT_D085.json`](progress/2026-11-17-spirou-d085-v3-6-comb-v4/FORENSIC_CANDIDATE_AUDIT_D085.json), [`results/PANCHROMATIC_OPTICAL_NIR_K_BRIDGE_8STARS.csv`](progress/2026-11-17-spirou-d085-v3-6-comb-v4/results/PANCHROMATIC_OPTICAL_NIR_K_BRIDGE_8STARS.csv), [`results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_73STARS.csv`](progress/2026-11-17-spirou-d085-v3-6-comb-v4/results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_73STARS.csv), [`results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_150STARS.csv`](progress/2026-11-17-spirou-d085-v3-6-comb-v4/results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_150STARS.csv) og [`results/MULTIMESSENGER_ECHELLE_RADIO_TESS_160SYSTEMS.csv`](progress/2026-11-17-spirou-d085-v3-6-comb-v4/results/MULTIMESSENGER_ECHELLE_RADIO_TESS_160SYSTEMS.csv).
3. **Indeks for hele det pankromatiske `V3.0–V4.0`-survey (`D079–D085`, `150` stjerner, `1.009` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–K:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D085"`), `FORTSAET_FRA_D085.md`, dedikeret `.venv` (inkl. lokal `tectonic`-kompiler), fulde arkiv-inputcaches `inputs_d079_v3/` .. `inputs_d085_v3_6/`, alle elleve kompagnonarkiver A–K (senest `SETI_D085_V3_6_SPIROU_YJHK_AND_COMB_V4_RESULTS_2026-11-17.zip` = `17.448.033` B) og `restore_d085_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`/usr/bin/python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `192` unikke tidligere undersøgte echelle-mål (`42` i `C001–D078` + `150` i `D079–D085`) og `1.382` ekskluderede eksponeringer (`1.205` før `D085` + `177` i `D085`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037`, `D002–D034`, `work_rubin_20261102`, `HD 43629` (`D035–D078`), `M10–M36` radiomanifesterne samt de låste `D079–D085`-arbejdsmapper (kompagnonarkiver A–K) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.
- **Streng GitHub-afgrænsning:** Alle leverancer og PDF-manuskripter gemmes udelukkende i projektmappen og pushes kun til dette GitHub-repositorium (`external_contacts == 0`).

---

## 3. Mulige fremtidige forskningsretninger efter `D085` (`Trin 9` / `D086`)

Med `Trin 2–8` (`D079–D085`, `150` unikke echelle-stjerner på tværs af begge halvkugler + `160`-systems multi-messenger syntese) afsluttet og kompileret til PDF i [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf) peger tre naturlige `Trin 9`-spor fremad:
1. **Nordlig dyb-optisk (`360–920 nm` / `HARPS-N`, Keck `HIRES` eller `MAROON-X`) + `CARMENES_NIR` (`0,96–1,71 µm`):** Dækker de resterende nordlige `< 10 pc` stjerner, som hidtil kun har nær-IR SPIRou (`YZ Cet` / `GJ 1002` under `10 W` optisk) eller fuld optisk-NIR-K dækning.
2. **Global udrulning af Kanal 5 `COMB_V4` på hele `D079–D084` (`832`-eksponerings databasen):** Anvender Kanal 5 `COMB_V4` med skarp supraphotosfærisk tandtærskel (`comb_tooth_fn_min >= 1,008`) over alle `150` kalibrerede echelle-stjerner across `0,38–2,515 µm`.
3. **`CRIRES+` $L/M$-bånd (`2,9–5,3 µm`):** Direkte afprøvning af termiske `3–5 µm` kvantekaskade-lasere kombineret med sparsomt `G6_V36` airglow-atlas.
