# Optisk `V3 / ECELLE_V3_1`-survey (`D079–D080+`): Prospektivt kalibreret lasersøgning på nære FGKM- og exoplanet-stjerner

Dette dokument indekserer projektets 3. generations optiske echelle-SETI-spor (`HARPS_ECELLE_V3` og multi-instrument `ECELLE_V3_1`), iværksat efter den komplette lukning af `HD 43629`-forløbet (`D001`–`D078`, se [`OPTICAL_HD43629_INDEX.md`](OPTICAL_HD43629_INDEX.md)).

> **Samlet status over `D079 + D080` (14. november 2026):** **`0` verificerede ETI-lasersignaler** på tværs af **`190` friske højopløste echelle-eksponeringer af `38` nære FGKM-stjerner** (`130` ESO `HARPS` + `60` VLT `ESPRESSO`; `32` science-stjerner inkl. `22` exoplanet-systemer med `44` planeter + `6` dedikerede ikke-planet kontrolstjerner; `0` overlap mod alle tidligere faser). Kalibrerede `8σ`-øvre grænser for en diffraktionsbegrænset `10 m`-sender når helt ned til **`0,91 kW`** på `HIP70849` (`D080` median `10,28 kW`).

---

## Oversigt over gennemførte `V3 / V3.1`-surveyfaser

| Fase | Dato | Detektor & instrumenter | Kohorte & omfang | Nøgleresultat & stdlib-audit | Offentlige leverancer |
| --- | --- | --- | --- | --- | --- |
| **`D079`** | `2026-11-14` | `HARPS_ECELLE_V3` (`HARPS`, `3800–6900 Å`) | `12` stjerner (`2` kontrol + `10` sol-analoger), `60` HARPS-eksp (`16.439,8 s`) | `720` RV-fits (`0` randtræf), `816` syntetiske forsøg (`85,1 %` Kanal T $\ge 8\sigma$), kontrolparitet + `F1+F2` → **`0` ETI-lasere**, median $P_{10\,\mathrm{m},8\sigma} = 46,99\,\mathrm{kW}$, stdlib-audit `PASS` | [Fuld rapport](reports_d035_d077/SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_2026-11-14.md) · [Progress-mappe](../progress/2026-11-14-harps-d079-v3/REPORT.md) · [`SUMMARY.json`](../progress/2026-11-14-harps-d079-v3/SUMMARY.json) |
| **`D080`** | `2026-11-14` | `ECELLE_V3_1` (`HARPS` + VLT `ESPRESSO`, `3800–7860 Å`, indbygget `G1_F1`/`G3_F1` + `G5_F2`) | `26` stjerner (`4` kontrol + `22` exoplanet-værter med `44` planeter, `3,64–44,86 pc`), `130` eksp (`70` HARPS + `60` ESPRESSO) | `1.560` RV-fits, `1.734` syntetiske forsøg (`59,2 %` Kanal T $\ge 8\sigma$, `100,0 %` 2D kosmisk afvisning), `V2` `422` → **`0` ETI-lasere**, min. $P_{10\,\mathrm{m},8\sigma} = 0,91\,\mathrm{kW}$ (median `10,28 kW`), stdlib-audit `PASS` | [Fuld rapport](reports_d035_d077/SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_SURVEY_2026-11-14.md) · [Progress-mappe](../progress/2026-11-14-echelle-d080-v3-1/REPORT.md) · [`SUMMARY.json`](../progress/2026-11-14-echelle-d080-v3-1/SUMMARY.json) · [`STAR_UPPER_LIMITS_186.csv`](../progress/2026-11-14-echelle-d080-v3-1/STAR_UPPER_LIMITS_186.csv) |

---

## Maskinlæsbare tabeller i `progress/2026-11-14-echelle-d080-v3-1/` (`D080`)

- [`METHOD_LOCK.json`](../progress/2026-11-14-echelle-d080-v3-1/METHOD_LOCK.json) & [`IMPLEMENTATION_LOCK.json`](../progress/2026-11-14-echelle-d080-v3-1/IMPLEMENTATION_LOCK.json) — Prospektiv metodelås og dokumenteret pre-analyse `obs_release_date`- og `esotk` Phase-3 FITS-skematillæg.
- [`SOURCES.json`](../progress/2026-11-14-echelle-d080-v3-1/SOURCES.json) — Komplet ESO-, Gaia DR3- og NASA Exoplanet Archive-proveniens for alle `130` eksponeringer.
- [`STAR_RV_SUMMARY_26.csv`](../progress/2026-11-14-echelle-d080-v3-1/STAR_RV_SUMMARY_26.csv) — Empiriske barycentriske `HARPS`- og `ESPRESSO`-hastigheder mod Gaia DR3 for alle `26` stjerner.
- [`CALIBRATION_COMPLETENESS_BY_BAND.csv`](../progress/2026-11-14-echelle-d080-v3-1/CALIBRATION_COMPLETENESS_BY_BAND.csv) — Genfindingsgrad over alle `8` HARPS- og `9` ESPRESSO-bånd (`3844,75–7465,10 Å`).
- [`THREE_GEN_BENCHMARK_130.csv`](../progress/2026-11-14-echelle-d080-v3-1/THREE_GEN_BENCHMARK_130.csv) — Eksponering-for-eksponering sammenligning af `Legacy V2`, `D079 V3.0` og `Prospective D080 V3.1`.
- [`V3_1_CANDIDATE_LEDGER.csv`](../progress/2026-11-14-echelle-d080-v3-1/V3_1_CANDIDATE_LEDGER.csv) — Komplet kandidat- og gate-ledger over alle `G1_F1`-kandidater.
- [`EXOPLANET_PHASE_COVERAGE_110.csv`](../progress/2026-11-14-echelle-d080-v3-1/EXOPLANET_PHASE_COVERAGE_110.csv) — Banefasedækning og konjunktionsvinduer for alle `110` exoplanet-eksponeringer.
- [`STAR_UPPER_LIMITS_186.csv`](../progress/2026-11-14-echelle-d080-v3-1/STAR_UPPER_LIMITS_186.csv) — `8σ` spektrale og lasereffekt-øvre grænser for alle `22` exoplanet-værtsstjerner (`186` celler).
- [`AUDIT_SUMMARY.json`](../progress/2026-11-14-echelle-d080-v3-1/AUDIT_SUMMARY.json) & [`VISUAL_REVIEW.json`](../progress/2026-11-14-echelle-d080-v3-1/VISUAL_REVIEW.json) — Ren-stdlib uafhængig efterregning (`0` fejl) og visuel figurkontrol.
