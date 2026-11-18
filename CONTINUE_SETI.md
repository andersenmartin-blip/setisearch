# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 18. november 2026 · **Aktivt videnskabeligt checkpoint:** `D087` afsluttet (Rum-baseret `HST_STIS` `E140M` + VLT `UVES_RED` + `ESPRESSO` HR/UHR `SPACE_UV_STIS_AND_FARRED_V3_8` på `33` stjerner [`25` helt nye + `8` broer] / `201` eksponeringer + samlet **`200`-stjerners / `1.391`-eksponeringers (`335,26 t`, `9` spektrografer [`10` arme], `4,457` oktaver `0,1145–2,515 µm`) all-sky syntese**, **`103` `< 10 pc` stjerner** [`1,6237 kW` median; **`0,0973 W` (`97,3 mW`)** rekord på `Proxima Centauri` i rum-FUV], **`17` broer (`334` celler)**, **`60` orbitale kampagner**, **`206`-systems multi-messenger syntese** med `Parkes`/`GBT` `1,4 GHz` radio [`18` direkte overlaps] og `TESS`, `G4_V38` regression `577 -> 0` på `D086`, `15/15` ren-stdlib audit `PASS`, samt opdateret to-spaltet publikations-PDF; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D087`, `4,457` oktaver `0,1145–2,515 µm`, `200` unikke all-sky + rum echelle-stjerner, `1.391` eksponeringer, `103` `< 10 pc` + `206`-systems multi-messenger syntese):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf), [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D087` — Trin 10 `SPACE_UV_STIS_AND_FARRED_V3_8`, `200`-stjerners & `206`-systems syntese):** [`progress/2026-11-18-stis-farred-d087-v3-8-200star/RESULTS_REPORT.md`](progress/2026-11-18-stis-farred-d087-v3-8-200star/RESULTS_REPORT.md), [`results/SUMMARY.json`](progress/2026-11-18-stis-farred-d087-v3-8-200star/results/SUMMARY.json), [`FORENSIC_CANDIDATE_AUDIT_D087.json`](progress/2026-11-18-stis-farred-d087-v3-8-200star/FORENSIC_CANDIDATE_AUDIT_D087.json), [`results/PANCHROMATIC_BRIDGE_17STARS.csv`](progress/2026-11-18-stis-farred-d087-v3-8-200star/results/PANCHROMATIC_BRIDGE_17STARS.csv), [`results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_103STARS.csv`](progress/2026-11-18-stis-farred-d087-v3-8-200star/results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_103STARS.csv), [`results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_200STARS.csv`](progress/2026-11-18-stis-farred-d087-v3-8-200star/results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_200STARS.csv) og [`results/MULTIMESSENGER_ECHELLE_RADIO_TESS_206SYSTEMS.csv`](progress/2026-11-18-stis-farred-d087-v3-8-200star/results/MULTIMESSENGER_ECHELLE_RADIO_TESS_206SYSTEMS.csv).
3. **Indeks for hele det pankromatiske `D079–D087`-survey (`200` stjerner, `1.391` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–M:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D087"`), `FORTSAET_FRA_D087.md`, dedikeret `.venv` (inkl. lokal `tectonic`-kompiler), fulde arkiv-inputcaches `inputs_d079_v3/` .. `inputs_d087_v3_8/`, alle tretten kompagnonarkiver A–M (senest `SETI_D087_V3_8_SPACE_UV_STIS_FARRED_AND_200STAR_RESULTS_2026-11-18.zip` = `19.262.628` B, SHA-256 `95b35e2a8b93b536c07b3c47c6c70f2ab1712455613059d66c7a00fe9591671c`) og `restore_d087_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`/usr/bin/python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `242` unikke tidligere undersøgte echelle-mål (`42` i `C001–D078` + `200` i `D079–D087`) og `1.765` ekskluderede eksponeringer (`1.564` før `D087` + `201` i `D087`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037`, `D002–D034`, `work_rubin_20261102`, `HD 43629` (`D035–D078`), `M10–M36` radiomanifesterne samt de låste `D079–D087`-arbejdsmapper (kompagnonarkiver A–M) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.
- **Streng GitHub-afgrænsning:** Alle leverancer og PDF-manuskripter gemmes udelukkende i projektmappen og pushes kun til dette GitHub-repositorium (`external_contacts == 0`).

---

## 3. Mulige fremtidige forskningsretninger efter `D087` (`Trin 11` / `D088`)

Med `Trin 2–10` (`D079–D087`, `200` unikke echelle-stjerner over `4,457` oktaver `0,1145–2,515 µm` + `206`-systems multi-messenger syntese) afsluttet og kompileret til PDF i [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf) peger næste skridt fremad mod:
1. **`COMB_V4_1` & `G4_V38` retroaktiv all-sky udrulning på hele `D079–D085` (`1.009` optisk-NIR eksponeringer) samt Keck `HIRES` / `MAROON-X` nordlig NUV-optisk komplettering:** Udvider de skov-rensede og Fiber-B-immunte detektorer uniformt til hele 200-stjerners arkivet.
2. **`CRIRES+` $L/M$-bånd (`2,9–5,3 µm`) eller `HST/COS` FUV (`G130M/G160M`, `0,115–0,180 µm`):** Termisk `3–5 µm` kvantekaskadelaser-søgning eller dybere rum-FUV-komplettering koblet med `COMB_V4_1`.
