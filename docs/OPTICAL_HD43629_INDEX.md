# Optisk SETI-spor (`D001`–`D078`): Fra 50-eksponerings HARPS-udvalg til `HD 43629` og FEROS

Dette dokument samler den fulde sammenhæng mellem konsolideringsrapporten [`D001`](../work_seti_20261105_d001_delivery/README.md) (5. november 2026) og den aktive optiske undersøgelseskæde gennem [`D078`](../progress/2026-11-14-feros-d078/REPORT.md) (14. november 2026).

> **Videnskabelig status (`HD 43629` afsluttet ved `D078`):** `0` kvalificerede lasersignaler. Empirisk FEROS-stjernehastighed målt til `+33,820 ± 0,216 km/s` (`-0,020 km/s` fra Gaia DR3); ingen vedvarende smal emissionskomponent findes ved hvilebølgelængderne `6549,356 Å`, `4826,103 Å` eller `5730,069 Å`, og de tre 2021 HARPS enkelt-epoke strukturer forklares uden teknosignaturer (se [`HD43629_SYNTHESIS3.csv`](../progress/2026-11-14-feros-d078/HD43629_SYNTHESIS3.csv)).

---

## 1. Bindeleddet `D001` → `D002`–`D034`: De 141 triggers på 10 friske HARPS-stjerner

I [`D001`](../work_seti_20261105_d001_delivery/README.md) blev den oprindelige HARPS-undersøgelse (`300` eksponeringer af `20` stjerner; `90`-rækkers opfølgningskø lukket i [`C037`](../work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md)) gjort op, og et deterministisk metadata-udvalg på **50 hovedeksponeringer af 10 friske stjerner + 4 kontrolspektre** blev fastlagt ([`FRESH_METADATA_COHORT54.csv`](../work_seti_20261105_d001_delivery/results/FRESH_METADATA_COHORT54.csv)).

I faserne **`D002`–`D034`** (bevaret i det lokale hovedarkiv `SETI_D002_D003_CONTINUATION_2026-11-05.zip`, v59, samt i statustabellerne `FULL_SAMPLE_STATE141.csv` og `ALL37_INTERPRETATION.csv` i D069–D077-kompagnonarkiverne) blev den uændrede `V2`-detektor anvendt på disse 50 eksponeringer:

- **Samlet udfald i `D002`:** `141` 1D-træf (`D002-0001` til `D002-0141`) fordelt over `44` eksponeringer på alle 10 stjerner: `HD 43629` (`37`), `HD 52758` (`17`), `HD 30177` (`16`), `HD 28185` (`13`), `HD 55` (`13`), `HD 73267` (`13`), `HD 6718` (`12`), `HD 4208` (`9`), `HD 48265` (`9`) og `HD 72687` (`2`).
- **Råbilled- og kontekstgennemgang (`141`-køen lukket):** Samtlige `141` poster gennemgik 2D-råbilled- og ordenskontekst (`139` med fuld dækning og `2` med randafskæring i orden 2; køen er lukket).
- **Fokus på `HD 43629` (`37` poster → `3` enkelt-epoke strukturer):** Alle `37` poster på `HD 43629` (`TIC34077285` / `TOI-880`) gennemgik himmel-/atmosfærekontrol (`D004`–`D006`), epokegentagelsestest (`D007`), atomar linjekontrol (`D008`) og 2D rå/native detektorprofil-triage (`D016`–`D034`). Heraf stod **tre enkelt-epoke strukturer fra 2021** tilbage til dyb instrumentel og tvær-instrumentel opfølgning:

| Kandidat-ID | HARPS-observation (UTC) | Råfil | Barycentrisk luftbølgelængde | Centrale kendetegn og bevarede forbehold |
| --- | --- | --- | ---: | --- |
| `D002-0061` | `2021-03-05` | `HARPS.2021-03-05T00:22:15.030` | `6550,0950 Å` | Positiv tidskontrast mod 2021-kontroller, men oprindelig kvalitetsfejl `rho = 0,7807 < 0,8` består fortsat (`D018`). |
| `D002-0063` | `2021-03-09` | `HARPS.2021-03-09T01:17:26.087` | `4826,6475 Å` | Kraftig lokal kontrast og tydelig rumlig tværprofil-afvigelse; ydre rækkeandel styres kraftigt af nabosamplet `k2573` (`D063`); blå COMB uvalideret (`D036`). |
| `D002-0071` | `2021-09-09` | `HARPS.2021-09-09T09:12:50.220` | `5730,7150 Å` | Positiv kontrast mod 6. og 18. sep. 2021 og lokal 2D-rækkeafvigelse (`D055`–`D056`); skelner endnu ikke laser fra kosmisk stråle eller lokal defekt. |

*(Bemærk: Den oprindelige binære leverancepakke med 663 filer fra `D002`–`D003` blev afvist af en automatisk godkendelsesgate i et tidligere kørselsmiljø den 5. november 2026 og genforsøges ikke som rå git-upload; de komplette statusmatricer bevares i stedet i projektets hash-verificerede kompagnonarkiver).*

---

## 2. Kronologisk rapportindeks (`D035`–`D078`)

| Fase | Dato | Rapport (dansk) | Hovedindhold |
| --- | --- | --- | --- |
| `D035` | `2026-11-10` | [`SETI_D035_EVIDENCE_COMB_INVENTORY_2026-11-10.md`](reports_d035_d077/SETI_D035_EVIDENCE_COMB_INVENTORY_2026-11-10.md) | HARPS COMB/LFC evidens- og råfilsinventering |
| `D036` | `2026-11-11` | [`SETI_D036_COMB_COVERAGE_2026-11-11.md`](reports_d035_d077/SETI_D036_COMB_COVERAGE_2026-11-11.md) | HARPS COMB-dækning omkring 0061 (brugbar) og 0063 (ingen accepterede blå linjer) |
| `D037–D038` | `2026-11-11` | [`SETI_D037_D038_COMB_RESPONSE_2026-11-11.md`](reports_d035_d077/SETI_D037_D038_COMB_RESPONSE_2026-11-11.md) | Effektiv spline- vs. Gauss-linjerespons på HARPS COMB |
| `D039` | `2026-11-11` | [`SETI_D039_INTENSITY_NOISE_2026-11-11.md`](reports_d035_d077/SETI_D039_INTENSITY_NOISE_2026-11-11.md) | Intensitets- og støjsimuleringer ved kandidatpositionerne |
| `D040` | `2026-11-11` | [`SETI_D040_EMPIRICAL_NOISE_2026-11-11.md`](reports_d035_d077/SETI_D040_EMPIRICAL_NOISE_2026-11-11.md) | Empiriske støjfordelinger, haler og kovariansgrænser |
| `D041` | `2026-11-11` | [`SETI_D041_SAME_TARGET_NOISE_2026-11-11.md`](reports_d035_d077/SETI_D041_SAME_TARGET_NOISE_2026-11-11.md) | Samme-stjerne støjkontrol (~97,43 % kontinuumniveau) |
| `D042–D043` | `2026-11-11` | [`SETI_D042_D043_SIGNAL_AND_EPOCHS_2026-11-11.md`](reports_d035_d077/SETI_D042_D043_SIGNAL_AND_EPOCHS_2026-11-11.md) | Signalparametre og HARPS 2021-epokesammenligning |
| `D044–D046` | `2026-11-11` | [`SETI_D044_D046_EPOCH_CONTROL_2026-11-11.md`](reports_d035_d077/SETI_D044_D046_EPOCH_CONTROL_2026-11-11.md) | Primære marts-epokekontroller og konfigurationsproveniens |
| `D047–D049` | `2026-11-11` | [`SETI_D047_D049_SECONDARY_EPOCH_2026-11-11.md`](reports_d035_d077/SETI_D047_D049_SECONDARY_EPOCH_2026-11-11.md) | Sekundær 6. marts 2021-kontrol (afvigende selector-indstillinger) |
| `D050–D051` | `2026-11-11` | [`SETI_D050_D051_EPOCH_SYNTHESIS_2026-11-11.md`](reports_d035_d077/SETI_D050_D051_EPOCH_SYNTHESIS_2026-11-11.md) | Syntese af marts-epoker og restframe-forbehold |
| `D052–D054` | `2026-11-11` | [`SETI_D052_D054_SEPTEMBER_CONTROLS_2026-11-11.md`](reports_d035_d077/SETI_D052_D054_SEPTEMBER_CONTROLS_2026-11-11.md) | September 2021-kontroller (6. og 18. sep.) omkring D002-0071 |
| `D055–D056` | `2026-11-12` | [`SETI_D055_D056_SPATIAL_SUPPORT_2026-11-12.md`](reports_d035_d077/SETI_D055_D056_SPATIAL_SUPPORT_2026-11-12.md) | 2D rumlig støtte og detektorrækkeprofiler ved D002-0071 |
| `D057–D058` | `2026-11-12` | [`SETI_D057_D058_BLUE_CONTROLS_2026-11-12.md`](reports_d035_d077/SETI_D057_D058_BLUE_CONTROLS_2026-11-12.md) | Blå epokekontroller omkring D002-0063 (4826,6475 Å) |
| `D059–D060` | `2026-11-12` | [`SETI_D059_D060_BLUE_SPATIAL_2026-11-12.md`](reports_d035_d077/SETI_D059_D060_BLUE_SPATIAL_2026-11-12.md) | Blå 2D-rækkegeometri og ekstraktionsbredde ved D002-0063 |
| `D061–D062` | `2026-11-12` | [`SETI_D061_D062_BLUE_BAND_2026-11-12.md`](reports_d035_d077/SETI_D061_D062_BLUE_BAND_2026-11-12.md) | Blå tværbåndsdekomposition og ThAr-lampereference |
| `D063–D064` | `2026-11-12` | [`SETI_D063_D064_ROW_AND_EVIDENCE_2026-11-12.md`](reports_d035_d077/SETI_D063_D064_ROW_AND_EVIDENCE_2026-11-12.md) | Eksakt k2573-nabosampleregnskab og 34-punkts evidenssyntese |
| `D065–D066` | `2026-11-13` | [`SETI_D065_D066_INDEPENDENT_INSTRUMENTS_2026-11-13.md`](reports_d035_d077/SETI_D065_D066_INDEPENDENT_INSTRUMENTS_2026-11-13.md) | Uafhængig ESO-arkivsøgning og verifikation af 5 FEROS-par (nov. 2019) |
| `D067–D068` | `2026-11-13` | [`SETI_D067_D068_FEROS_INPUTS_AND_PROFILES_2026-11-13.md`](reports_d035_d077/SETI_D067_D068_FEROS_INPUTS_AND_PROFILES_2026-11-13.md) | Validering af 15 FEROS-input og 1D-kontraster (fortegnskift over baggrunde) |
| `D069–D074` | `2026-11-13` | [`SETI_D069_D074_FEROS_VELOCITY_CONTEXT_2026-11-13.md`](reports_d035_d077/SETI_D069_D074_FEROS_VELOCITY_CONTEXT_2026-11-13.md) | FEROS ekstraktionsmåder, ordensprofiler, header-RV-fravær og 540 fremad-kurver |
| `D075–D076` | `2026-11-13` | [`SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_2026-11-13.md`](reports_d035_d077/SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_2026-11-13.md) | 900 ordenskurver + 1.440 baglæns kurver (op til 1,45 km/s ordensforskel ved 0061) |
| `Status` | `2026-11-13` | [`SETI_GITHUB_OG_FEROS_STATUS_2026-11-13.md`](reports_d035_d077/SETI_GITHUB_OG_FEROS_STATUS_2026-11-13.md) | Afstemning af D075-reproduktion, D076-checkpoint og GitHub-status |
| `D077` | `2026-11-14` | [`SETI_D077_FEROS_WLC_METADATA_GATE_2026-11-14.md`](reports_d035_d077/SETI_D077_FEROS_WLC_METADATA_GATE_2026-11-14.md) | Prospektiv metadata- og proveniensgate for alle 30 FEROS dagslys-WLC råfiler |
| `D078` | `2026-11-14` | [`SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_2026-11-14.md`](reports_d035_d077/SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_2026-11-14.md) | Empirisk stellar hvileramme (+33,820 km/s), løsning af 1,45 km/s sidebåndseffekt, 5-epoke coadd og afslutning af HD 43629 |

Maskinlæsbare metodelåse, kilde-ID'er og numeriske audit-kvitteringer for de nyeste FEROS-faser findes tillige under [`progress/2026-11-13-feros-d075/`](../progress/2026-11-13-feros-d075/REPORT.md), [`progress/2026-11-13-feros-d076/`](../progress/2026-11-13-feros-d076/REPORT.md) [`progress/2026-11-14-feros-d077/`](../progress/2026-11-14-feros-d077/REPORT.md) og [`progress/2026-11-14-feros-d078/`](../progress/2026-11-14-feros-d078/REPORT.md).
