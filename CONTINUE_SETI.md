# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 14. november 2026 · **Aktivt videnskabeligt checkpoint:** `D077` afsluttet (`107.105` bevarede statustabelceller; `0` kvalificerede teknosignaturer).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Seneste afsluttede fase (`D077`):** [`progress/2026-11-14-feros-d077/REPORT.md`](progress/2026-11-14-feros-d077/REPORT.md), [`SUMMARY.json`](progress/2026-11-14-feros-d077/SUMMARY.json) og den fulde danske rapport [`SETI_D077_FEROS_WLC_METADATA_GATE_2026-11-14.md`](docs/reports_d035_d077/SETI_D077_FEROS_WLC_METADATA_GATE_2026-11-14.md).
2. **Samlet optisk historik (`D001`–`D077`):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
3. **Repositoriets opbygning og kompagnonarkiver:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
4. **Lokal permanent projektmappe (på arbejdsstationen):** `/home/martin/SETI_Fortsaettelse_2026-11-14/` med `SETI_ACTIVE_CONTINUATION.json`, dedikeret `.venv`, alle tre kompagnonarkiver (`45,920,303` B / `28,329,072` B / `659,654` B) og `restore_d077_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås før kontakt med nye spektralværdier:** Enhver ny analyse låser input-hashes, linjekataloger, masker, algoritme og fortolkningsregler i `METHOD_LOCK.json` før første læsning af nye flux-/pixelarrays, efterfulgt af en uafhængig numerisk efterregning (`NUMERICAL_AUDIT.json`).
- **Bevaring af alle resultater og fejlflag:** Negative grene, tvetydigheder, tidligere kvalitetsfejl (f.eks. `D002-0061` `rho = 0,7806562435869904 < 0,8`, `D002-0063` `k2573`-vinduesfølsomhed og manglende blå COMB-validering, `FEROS` `RA/DEC`-afvigelse mod `ESO TEL TARG ALPHA/DELTA`) samt eventuelle tekniske audit-rettelser bevares eksplicit. Intet omskrives i stilhed.
- **Fysiske koordinater og enheder:**
  - Reducerede HARPS- og FEROS-spektre er i **barycentriske luftbølgelængder (`Å`)** med observatørkorrektion allerede påført (`ESO DRS BARYCORR` i FEROS). **Påfør aldrig en ekstra barycentrisk korrektion.**
  - Manglende `TIMESYS` antages ikke bevist fra header alene; manglende lampeslots (`LAMP1, 2, 4`) behandles som `MISSING_UNKNOWN` (aldrig antaget `OFF`); `SDP ERR = NaN` og uvaliderede lokale residualmål må ikke kaldes fysisk $\sigma$ eller kalibreret falsk-alarm-rate (FAP).
- **Lukkede køer genåbnes ikke automatisk:** Den gamle `90`-rækkers HARPS-kø (`C037`), den lukkede `141`-råkø (`D002`–`D034`) og Rubin/Fink-forstudiet (`work_rubin_20261102`) forbliver lukkede.
- **Større sammenhængende faser & slanke tabeller:** Saml naturligt sammenhørende spørgsmål i komplette, velafgrænsede faser frem for små mikro-trin, og gem nye målinger i normaliserede JSON/CSV-tabeller frem for at udvide de historiske 600-kolonners CSV-snapshots yderligere.

---

## 3. Aftalt videnskabelig køreplan fremover

### Trin 1 (`D078` — Samlet lokal stjernerestframe, ordensoverlap-diagnose og `HD 43629`-syntese)
Gennemføres som **én sammenhængende, prospektivt låst undersøgelse** uden download af de 30 rå WLC-billeder:
1. Lås et autoritativt laboratorie-linjekatalog (fotosfæriske metallinjer som Fe I, Ca I, Ni I m.fl. samt eventuelle telluriske linjer i standard-luftbølgelængder) i de dækkede spektralområder før læsning af spektralværdier.
2. Mål stjernens empiriske radialhastighed $v_{\mathrm{rad}}(t)$ i alle fem FEROS-epoker (`F1`–`F5`) direkte i stjernefiberens ordener (`HDU 17`, `24`, `25`, `29`, `30`) samt det samlede spektrum (`HDU 0`), og afklar direkte om `1,45 km/s`-forskellen ved `D002-0061` skyldes en reel inter-ordens bølgelængdeforskydning mellem `HDU 29` og `HDU 30` eller kontinuum-/blaze-krumning ved ordensranden.
3. Sammenfat hele evidenskæden for `D002-0061`, `D002-0063` og `D002-0071` på tværs af HARPS (2021) og FEROS (2019) i en endelig konklusions- og afslutningsrapport for `HD 43629`.

### Trin 2 (Næste hovedetape — Kalibreret 2D+ordens-bevidst optisk detektor `V3` og ny arkivsøgning)
Med erfaringerne fra `D001`–`D078` designes og fryses en ny optisk detektor (`V3`), der *før* søgning indbygger 2D tværprofil-konsistens på rå CCD-rækker (mod kosmiske stråler og defekte pixels), konsistens mellem overlappende echelle-ordener samt fuld syntetisk injektionskalibrering (inkl. `3800–4000 Å`) til en egentlig fysisk kalibreret arkivsøgning med målt følsomhed og falsk-alarm-rate.
