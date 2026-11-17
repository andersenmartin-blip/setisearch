# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 17. november 2026 · **Aktivt videnskabeligt checkpoint:** `D086` afsluttet (VLT `UVES_NUV` + `ESPRESSO` + `HARPS` `PANCHROM_NUV_OPT_V3_7_AND_COMB_V4_1` på `31` stjerner [`25` helt nye + `6` `< 10 pc` NUV/optiske broer] / `181` eksponeringer + samlet **`175`-stjerners / `1.190`-eksponeringers (`252,25 t`, `8` spektrografer, `> 3` spektrale oktaver `0,305–2,515 µm`) all-sky syntese**, **`90` `< 10 pc` stjerner** [`2,0983 kW` median; `0,80 W` rekord på `Proxima Centauri`], **`181`-systems multi-messenger syntese** med `Parkes`/`GBT` `1,4 GHz` radio [`18` direkte overlaps] og `TESS`, `COMB_V4_1` regression `19 -> 0` på `D085`, `15/15` ren-stdlib audit `PASS`, samt opdateret to-spaltet publikations-PDF; `107.105` historiske `D077`-tabelceller bevaret; **`0` verificerede teknosignaturer**).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Samlet videnskabeligt publikationsmanuskript (`D079–D086`, `> 3` oktaver `0,305–2,515 µm`, `175` unikke all-sky echelle-stjerner, `1.190` eksponeringer, `90` `< 10 pc` + `181`-systems multi-messenger syntese):** [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf), [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md) og LaTeX-kilden [`paper/main.tex`](paper/main.tex).
2. **Seneste afsluttede fase (`D086` — Trin 9 `PANCHROM_NUV_OPT_V3_7_AND_COMB_V4_1`, `175`-stjerners all-sky syntese & `181`-systems multi-messenger syntese):** [`progress/2026-11-17-uves-panchrom-d086-v3-7-comb-v4-1/RESULTS_REPORT.md`](progress/2026-11-17-uves-panchrom-d086-v3-7-comb-v4-1/RESULTS_REPORT.md), [`results/SUMMARY.json`](progress/2026-11-17-uves-panchrom-d086-v3-7-comb-v4-1/results/SUMMARY.json), [`FORENSIC_CANDIDATE_AUDIT_D086.json`](progress/2026-11-17-uves-panchrom-d086-v3-7-comb-v4-1/FORENSIC_CANDIDATE_AUDIT_D086.json), [`results/PANCHROMATIC_BRIDGE_13STARS.csv`](progress/2026-11-17-uves-panchrom-d086-v3-7-comb-v4-1/results/PANCHROMATIC_BRIDGE_13STARS.csv), [`results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_90STARS.csv`](progress/2026-11-17-uves-panchrom-d086-v3-7-comb-v4-1/results/SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_90STARS.csv), [`results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_175STARS.csv`](progress/2026-11-17-uves-panchrom-d086-v3-7-comb-v4-1/results/UNIFIED_PANCHROMATIC_V3_SYNTHESIS_175STARS.csv) og [`results/MULTIMESSENGER_ECHELLE_RADIO_TESS_181SYSTEMS.csv`](progress/2026-11-17-uves-panchrom-d086-v3-7-comb-v4-1/results/MULTIMESSENGER_ECHELLE_RADIO_TESS_181SYSTEMS.csv).
3. **Indeks for hele det pankromatiske `D079–D086`-survey (`175` stjerner, `1.190` eksponeringer):** [`docs/OPTICAL_V3_SURVEY_INDEX.md`](docs/OPTICAL_V3_SURVEY_INDEX.md).
4. **Historisk optisk indeks (`D001`–`D078`, `HD 43629` lukket):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
5. **Repositoriets opbygning og kompagnonarkiver A–L:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
6. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D086"`), `FORTSAET_FRA_D086.md`, dedikeret `.venv` (inkl. lokal `tectonic`-kompiler), fulde arkiv-inputcaches `inputs_d079_v3/` .. `inputs_d086_v3_7/`, alle tolv kompagnonarkiver A–L (senest `SETI_D086_V3_7_UVES_NUV_PANCHROM_AND_COMB_V4_1_RESULTS_2026-11-17.zip` = `22.587.203` B, SHA-256 `b37d27ac6269e6671fb341b98514b27edad5b2dbbc392bec75eaeaa63073aea1`) og `restore_d086_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås, offentlig `obs_release_date`-kontrol og dedikerede kontrolstjerner:** Enhver ny kohorte låser inputkriterier (`obs_release_date <= current_utc`), algoritme og kontrolstjerner i `METHOD_LOCK.json` *før* science-spektre hentes, efterfulgt af uafhængig ren-stdlib numerisk revision (`/usr/bin/python3 -S audit.py`).
- **Nul uerklæret mål- og eksponeringsoverlap:** Alle `217` unikke tidligere undersøgte echelle-mål (`42` i `C001–D078` + `175` i `D079–D086`) og `1.564` ekskluderede eksponeringer (`1.383` før `D086` + `181` i `D086`) er registreret med fuld SHA-256/proveniens og ekskluderes ved fremtidig kohorteudvælgelse i samme spektrale kanal.
- **Lukkede køer og arkiver genåbnes ikke:** `C037`, `D002–D034`, `work_rubin_20261102`, `HD 43629` (`D035–D078`), `M10–M36` radiomanifesterne samt de låste `D079–D086`-arbejdsmapper (kompagnonarkiver A–L) forbliver urørte, og de `107.105` historiske `D077`-tabelceller forbliver frosne.
- **Streng GitHub-afgrænsning:** Alle leverancer og PDF-manuskripter gemmes udelukkende i projektmappen og pushes kun til dette GitHub-repositorium (`external_contacts == 0`).

---

## 3. Mulige fremtidige forskningsretninger efter `D086` (`Trin 10` / `D087`)

Med `Trin 2–9` (`D079–D086`, `175` unikke echelle-stjerner over `> 3` oktaver `0,305–2,515 µm` + `181`-systems multi-messenger syntese) afsluttet og kompileret til PDF i [`paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`](paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf) peger næste skridt fremad mod:
1. **`COMB_V4_1` retroaktiv all-sky udrulning på hele `D079–D084` (`832` optisk-NIR eksponeringer) samt Keck `HIRES` / `MAROON-X` nordlig NUV-optisk komplettering:** Udvider den skov-rensede `COMB_V4_1` kam-detektor uniformt til hele 175-stjerners arkivet og lukker nordlige `< 10 pc` M-dværge ned til sub-`10 W` under `0,38 µm`.
2. **`CRIRES+` $L/M$-bånd (`2,9–5,3 µm`):** Termisk `3–5 µm` kvantekaskadelaser-søgning koblet med `COMB_V4_1` og sparsomt tellurisk/airglow-atlas.
