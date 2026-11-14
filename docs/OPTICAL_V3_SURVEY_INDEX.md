# Optisk `HARPS_ECELLE_V3`-survey (`D079+`): Prospektivt kalibreret lasersøgning på nære sol-analoge stjerner

Dette dokument indekserer projektets 3. generations optiske echelle-SETI-spor (`HARPS_ECELLE_V3`), iværksat efter den komplette lukning af `HD 43629`-forløbet (`D001`–`D078`, se [`OPTICAL_HD43629_INDEX.md`](OPTICAL_HD43629_INDEX.md)).

> **Aktuel status (`D079` afsluttet 14. november 2026):** `0` verificerede ETI-lasersignaler på tværs af `50` friske eksponeringer af `10` nære sol-analoge stjerner (`15,2–46,3 pc`) + `10` kontroleksponeringer på `2` prospektive kontrolstjerner (`HD 1461`, `HD 4308`). Kalibrerede `8σ`-øvre grænser for en diffraktionsbegrænset `10 m`-sender ligger på **`17,30–201,41 kW` (median `46,99 kW`)** over hele `3800–6900 Å` (inkl. `3800–4000 Å` blåt bånd).

---

## Oversigt over gennemførte `V3`-surveyfaser

| Fase | Dato | Kohorte & omfang | Nøgleresultat & audit | Offentlige leverancer |
| --- | --- | --- | --- | --- |
| **`D079`** | `2026-11-14` | `12` stjerner (`2` kontrol + `10` science), `60` HARPS-eksponeringer (`16.439,8 s`), `0` overlap mod alle `40` tidligere stjerner og `363` `dp_id` | `720` NIST RV-fits (`0` randtræf), `816` syntetiske forsøg (`85,1 %` Kanal T $\ge 8\sigma$, `83,3 %` i `3800–4000 Å`), kontrolparitet (`2,80` mod `2,96`/eksp), forensisk `F1+F2` → **`0` ETI-lasere**, median $P_{10\,\mathrm{m},8\sigma} = 46,99\,\mathrm{kW}$, stdlib-audit `PASS` (`6.072` tjek) | [Fuld rapport](reports_d035_d077/SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_2026-11-14.md) · [Progress-mappe](../progress/2026-11-14-harps-d079-v3/REPORT.md) · [`SUMMARY.json`](../progress/2026-11-14-harps-d079-v3/SUMMARY.json) · [`STAR_UPPER_LIMITS_80.csv`](../progress/2026-11-14-harps-d079-v3/STAR_UPPER_LIMITS_80.csv) |

---

## Maskinlæsbare tabeller i `progress/2026-11-14-harps-d079-v3/`

- [`METHOD_LOCK.json`](../progress/2026-11-14-harps-d079-v3/METHOD_LOCK.json) & [`IMPLEMENTATION_LOCK.json`](../progress/2026-11-14-harps-d079-v3/IMPLEMENTATION_LOCK.json) — Prospektiv metodelås og dokumenteret Fiber B (`71`-mod-`72` ordener) + forensisk `F1+F2`-tillæg.
- [`SOURCES.json`](../progress/2026-11-14-harps-d079-v3/SOURCES.json) — Komplet ESO- og Gaia DR3-proveniens for alle `60` eksponeringer.
- [`STAR_RV_SUMMARY_12.csv`](../progress/2026-11-14-harps-d079-v3/STAR_RV_SUMMARY_12.csv) — Empiriske barycentriske HARPS-hastigheder og Gaia DR3-sammenligning for alle `12` stjerner.
- [`CALIBRATION_COMPLETENESS_BY_BAND.csv`](../progress/2026-11-14-harps-d079-v3/CALIBRATION_COMPLETENESS_BY_BAND.csv) — Genfindingsgrad over alle `8` bølgelængdebånd (`3825,4–6815,5 Å`) i Kanal T og Kanal P.
- [`V2_VS_V3_BENCHMARK_60.csv`](../progress/2026-11-14-harps-d079-v3/V2_VS_V3_BENCHMARK_60.csv) — Eksponering-for-eksponering sammenligning mellem `V2` og `V3`.
- [`V3_CANDIDATE_LEDGER.csv`](../progress/2026-11-14-harps-d079-v3/V3_CANDIDATE_LEDGER.csv) & [`FORENSIC_VETTING_176.csv`](../progress/2026-11-14-harps-d079-v3/FORENSIC_VETTING_176.csv) — Alle `321` Gate G1-kandidater og komplet `F1+F2`-forensisk afvisning af de `176` nominelle `G1–G5`-passager.
- [`STAR_UPPER_LIMITS_80.csv`](../progress/2026-11-14-harps-d079-v3/STAR_UPPER_LIMITS_80.csv) — `8σ` spektrale og lasereffekt-øvre grænser for alle `10` science-stjerner × `8` bånd.
- [`NUMERICAL_AUDIT.json`](../progress/2026-11-14-harps-d079-v3/NUMERICAL_AUDIT.json) & [`VISUAL_REVIEW.json`](../progress/2026-11-14-harps-d079-v3/VISUAL_REVIEW.json) — Ren-stdlib uafhængig efterregning (`6.072` tjek, `0` fejl) og visuel figurkontrol.
