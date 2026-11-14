# Fortsæt SETI-projektet — Autoritative retningslinjer og aktiv køreplan

**Senest opdateret:** 14. november 2026 · **Aktivt videnskabeligt checkpoint:** `D078` afsluttet (`HD 43629`-opfølgningen `D002`–`D078` lukket rent; `107.105` bevarede historiske statustabelceller + normaliserede `D078`-tabeller; `0` kvalificerede teknosignaturer).

> Tidligere omvendt-kronologiske fortsættelsesnoter er bevaret ubeskåret i [`docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md`](docs/history/CONTINUE_SETI_ARCHIVE_THROUGH_2026-11-14.md). Brug nærværende dokument som eneste aktive overdragelsesvejledning.

---

## 1. Autoritative kilder at læse ved sessionsstart

1. **Seneste afsluttede fase (`D078` — afslutning af `HD 43629`):** [`progress/2026-11-14-feros-d078/REPORT.md`](progress/2026-11-14-feros-d078/REPORT.md), [`SUMMARY.json`](progress/2026-11-14-feros-d078/SUMMARY.json), [`HD43629_SYNTHESIS3.csv`](progress/2026-11-14-feros-d078/HD43629_SYNTHESIS3.csv) og [`SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_2026-11-14.md`](docs/reports_d035_d077/SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_2026-11-14.md).
2. **Samlet optisk historik (`D001`–`D078`):** [`docs/OPTICAL_HD43629_INDEX.md`](docs/OPTICAL_HD43629_INDEX.md).
3. **Repositoriets opbygning og kompagnonarkiver A–D:** [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md).
4. **Permanent lokal projektmappe (`SETI_Fortsaettelse_2026-11-14/`):** Indeholder `SETI_ACTIVE_CONTINUATION.json` (`active_phase = "D078"`), dedikeret `.venv`, alle fire kompagnonarkiver A–D (`45.920.303` B / `28.329.072` B / `659.654` B / `11.427.944` B) og `restore_d078_workspace.py`.

---

## 2. Ufravigelige faglige og metodiske regler

- **Prospektiv metodelås før kontakt med nye spektralværdier:** Enhver ny analyse låser input-hashes, linjekataloger, masker, algoritme og fortolkningsregler i `METHOD_LOCK.json` før første læsning af nye flux-/pixelarrays, efterfulgt af en uafhængig numerisk efterregning (`NUMERICAL_AUDIT.json`).
- **Bevaring af alle resultater og fejlflag:** Negative grene, tvetydigheder, tidligere kvalitetsfejl (`D002-0061` `rho = 0,7806562435869904 < 0,8`, `D002-0063` `k2573`-vinduesfølsomhed og manglende blå COMB-validering, `D002-0071` rumlig 2D-rækkeafvigelse, `FEROS` `RA/DEC`-afvigelse mod `ESO TEL TARG ALPHA/DELTA`, manglende `TIMESYS`) bevares eksplicit. Intet omskrives i stilhed.
- **Fysiske koordinater og enheder:**
  - Reducerede HARPS- og FEROS-spektre er i **barycentriske luftbølgelængder (`Å`)** med observatørkorrektion allerede påført (`ESO DRS BARYCORR` i FEROS). **Påfør aldrig en ekstra barycentrisk korrektion.**
  - `SDP ERR = NaN` og uvaliderede lokale residualmål må ikke kaldes fysisk $\sigma$ eller kalibreret falsk-alarm-rate (FAP) uden en prospektivt valideret injektions-/støjmodel.
- **Lukkede køer genåbnes ikke automatisk:** Den gamle `90`-rækkers HARPS-kø (`C037`), den lukkede `141`-råkø (`D002`–`D034`), Rubin/Fink-forstudiet (`work_rubin_20261102`) og `HD 43629`-dybdeundersøgelsen (`D035`–`D078`) er afsluttede og genåbnes ikke uden ny uafhængig observationsdata.
- **Større sammenhængende faser & normaliserede tabeller:** Saml naturligt sammenhørende spørgsmål i komplette, velafgrænsede faser, og udgiv nye målinger i normaliserede JSON/CSV-tabeller (det historiske `107.105`-cellers CSV-snapshot i `D077` holdes frosset uden yderligere kolonne-bloat).

---

## 3. Aktiv videnskabelig køreplan — Trin 2 (`V3` kalibreret optisk laserdetektor og ny arkivkohorte)

Med Trin 1 (`D078` og lukningen af `HD 43629`) fuldført starter **Trin 2**: udvikling, frysning og syntetisk kalibrering af en ny optisk echelle-detektor (**`V3`**) *før* ublindet anvendelse på en ny kohorte af arkivstjerner (ekskl. de allerede gennemsøgte 20 `C001`-stjerner og 10 `D001`/`D002`-stjerner):

1. **Gate 1 — 2D tværdispersions fiber-PSF konsistens på rå CCD-rammer:** Enhver 1D-kandidat skal på det rå 2D-spektrogram matche stjernespektrets empiriske tværprofil inden for kalibrerede residualgrænser (eliminerer skrå kosmiske stråler og enkeltpixel-asymmetrier som `D002-0063` / `k2573` og `D002-0071` ved selve detektionen).
2. **Gate 2 — Ordens-overlap & rå fotonvarians-konsistens:** I bølgelængdeintervaller dækket af to nabordener testes begge individuelle ordener direkte vægtet efter rå fotonflux og blaze-profil i stedet for udelukkende at stole på sammenlagte 1D-produkter (`S1D`/`ADP`).
3. **Gate 3 — Eksplicit stellar RV-forankring samt tellurisk og K-dværg kontinuummaskering:** Hver eksponering forankres på isolerede fotosfæriske linjer, mens topocentriske telluriske $\mathrm{H_2O}$/$\mathrm{O_2}$-bånd og smalle kontinuumtoppe flankeret af dybe metallinjer modelleres eksplicit.
4. **Gate 4 — End-to-end syntetisk laser-injektion/recovery og kalibreret `FAP`:** Følsomhed $P_{\mathrm{det}}(F, \lambda)$ og falsk-alarm-rate kalibreres ved syntetisk injektion af LFC/LSF-profilerede smalle emissionslinjer i reelle kontroleksponeringer *før* metodelås på en ny arkivkohorte.
