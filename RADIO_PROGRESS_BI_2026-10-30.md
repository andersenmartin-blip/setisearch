# SETI BI — bånd 17–24 er gennemsøgt

30. oktober 2026. **Alle otte bånd er afsluttet med faktisk exitkode 0:** yderligere 433.004.544 korrelerede sporkombinationer på 66,25 sekunder. Ingen ON-spor nåede den faste lokale ESS-tærskel 10. Den efterfølgende resultatkontrol bestod.

| Størrelse | BI: q17–q24 | Samlet: q1–q24 |
|---|---:|---:|
| Bånd | 8 | **24** |
| Carrierkanaler | 32.768 | 98.304 |
| Teknisk kanalbredde | 91,553 kHz | **274,658 kHz** |
| Scan/bånd-søgninger | 48 | 144 |
| Korrelerede sporkombinationer, inklusive OFF | 433.004.544 | **1.299.013.632** |
| ON-spor med lokal ESS ≥10 | 0 | 0 |
| Faktiske, udløste ON/OFF-spormålinger | 0 | 0 |
| Beståede ON/OFF-flag | 0 | 0 |

BI dækker frekvenscentrene 2301,569369–2301,660919 MHz i seks scans fra HIP98505 / HD189733 den 28. april 2017: tre ON og tre OFF, hver med 16 tidsrækker. Den uændrede søgning bruger bredderne 1, 3, 9 og 33 kanaler og 839 drifttrin over ±4 Hz/s. De tidligere q1–q16 er bevaret.

| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |
|---:|---:|---:|
| 1 | 5,896 | 6,181 |
| 3 | 5,794 | 5,654 |
| 9 | 5,329 | 5,210 |
| 33 | 5,383 | 4,787 |

Kode og plan blev [fastholdt før beregningen](https://github.com/andersenmartin-blip/setisearch/commit/6f2258d01fdd5e6c4bb6490b3ced76f8dd63c6e6). Kun båndvalg og navne blev tilpasset fra BH. Rådata og beregningsmiljø blev genindlæst og kontrolleret; normaliseringen blev fortsat beregnet over hele native-rækken før beskæring. Ingen nye arkivanmodninger var nødvendige.

Søgning og resultatkontrol sluttede begge med faktisk exit 0, stdout-EOF, afsluttet procesventning og identiske observerede/gemte loghashes. Kontrollen tog 1,87 sekunder og efterprøvede output og optællinger fra alle 48 scan/bånd-søgninger, **1.728 udvalgte sporsummer med uafhængig `math.fsum`** og **576 kalibreringsgenberegninger med den delte kernel**. De største observerede numeriske afvigelser var 0. Det er en afgrænset kontrol; alle 433 millioner sporkombinationer, rådatakodek og hele normaliseringsmodellen er ikke genberegnet uafhængigt.

Der var ingen ON-frø over tærsklen og derfor ingen faktiske, udløste spormålinger på tværs af ON/OFF. De tomme katalogers konsistens er ikke et selvstændigt fysisk ON/OFF-resultat. Ingen ny SETI-kandidat er kvalificeret.

Dette er beskrivende genanalyse af tidligere eksponerede data fra samme historiske besøg. ESS kalibreres lokalt pr. bånd, drifttrin, bredde og scan og adskiller sig fra den historiske full-native ESS. ESS er ikke en kalibreret sigma-værdi eller falsk-alarm-sandsynlighed; sporkombinationerne er korrelerede. Der tilføjes ingen nye observationer eller kredit til BA-opgørelsen på 486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg. Ingen ny astronomisk følsomhed eller fysisk oprindelse er kvalificeret.

Binære søgeresultater og genoptagelsesoplysninger er gemt i [SETI_BI_SEARCH_RESULTS_2026-10-30.zip](https://chatgpt.com/library?file_id=libfile_b499aef35e7081919980a74915abe1f8&account_id=personal). Alle 165 pakkemedlemmer er kontrolleret med CRC og SHA-256. Rådata og kode er bevaret via de eksisterende datakilder og GitHub.

Næste sammenhængende batch er **q25–q32**, med en ny fast plan før beregning. Ingen signalsøgning kører videre i baggrunden efter denne batch.

- [Fast plan](work_bi/PLAN_BI.json) og [søgekode](work_bi/bounded_search_bi.py)
- [Samlet resultat og kumulativ status](work_bi/results/REAL_SEARCH_SUMMARY_BI.json)
- [Faktisk procesafslutning](work_bi/execution/SEARCH_ACTUAL_EXIT_BI.json)
- [Afgrænset resultatkontrol](work_bi/review/REAL_RESULT_AUDIT_BI.json)
- [Datapakke og fortsættelsespunkt](work_bi/DELIVERY_BI.json)
