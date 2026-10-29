# SETI BH — næste otte bånd er gennemsøgt

29. oktober 2026. **Søgningen i q9–q16 er afsluttet med faktisk exitkode 0.** De gemte 2017-data gav yderligere 433.004.544 korrelerede sporkombinationer på 149,60 sekunder. Ingen ON-spor nåede den faste lokale ESS-tærskel 10. Den efterfølgende resultatkontrol bestod.

| Størrelse | Denne batch: BH | Samlet: BG + BH |
|---|---:|---:|
| Faste bånd i native171 | q9–q16 | q1–q16 |
| Carrierkanaler | 32.768 | 65.536 |
| Teknisk kanalbredde | 91,553 kHz | **183,105 kHz** |
| Scan/bånd-søgninger | 48 | 96 |
| Korrelerede sporkombinationer, inklusive OFF | 433.004.544 | **866.009.088** |
| ON-spor med ESS ≥10 | 0 | 0 |
| Udløste ON/OFF-målinger | 0 | 0 |
| Beståede ON/OFF-flag | 0 | 0 |
| Nye arkivanmodninger | 0 | 0 |

BH dækker frekvenscentrene 2301,660922–2301,752472 MHz i seks scans fra samme besøg ved HIP98505 / HD189733 den 28. april 2017: tre ON og tre OFF. Hvert scan indeholder 16 tidsrækker. Søgebredderne var uændret 1, 3, 9 og 33 kanaler med 839 drifttrin over ±4 Hz/s. De afsluttede q1–q8 blev bevaret uden genkørsel.

| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |
|---:|---:|---:|
| 1 | 5,888 | 5,729 |
| 3 | 5,564 | 6,193 |
| 9 | 5,270 | 5,282 |
| 33 | 5,399 | 5,849 |

Der var ingen ON-frø over tærsklen og dermed **ingen faktiske, udløste spormålinger på tværs af ON/OFF**. Kontrol af de tomme katalogers konsistens er derfor ikke et selvstændigt fysisk ON/OFF-resultat. Ingen ny SETI-kandidat er kvalificeret.

Kode og plan blev [fastholdt på GitHub før beregningen](https://github.com/andersenmartin-blip/setisearch/commit/b63ef731ae851f12746b0b680270159aed5d1b82). Kun bandvalget og stage-navne blev tilpasset fra BG. Den uændrede AC-normalisering blev beregnet over hele hver native-række før beskæring, og den uændrede sporkernel søgte de valgte bånd.

Søgning og resultatkontrol sluttede begge med faktisk exit 0, stdout-EOF, afsluttet procesventning og identiske observerede/gemte loghashes. Resultatkontrollen tog 4,33 sekunder og verificerede output og optællinger fra alle 48 scan/bånd-søgninger, **1.728 udvalgte sporsummer med uafhængig `math.fsum`** samt **576 kalibreringsgenberegninger med den delte kernel**. De største observerede numeriske afvigelser var 0. Det er en afgrænset kontrol, ikke en uafhængig genberegning af alle 433 millioner kombinationer, rådatakodek eller hele normaliseringsmodellen.

ESS kalibreres lokalt i hvert 4096-kanalers bånd for hvert drifttrin, hver bredde og hvert scan. Det er en beskrivende analyse på tidligere eksponerede data og adskiller sig fra den historiske full-native ESS. ESS er ikke en kalibreret sigma-værdi, SNR eller falsk-alarm-sandsynlighed. Sporkombinationerne er korrelerede og må ikke tælles som uafhængige statistiske prøver.

Begge batches er genanalyse af samme historiske besøg. Der tilføjes ingen nye observationer, arkiv-ID'er eller dækning til BA-opgørelsen på 486 ID'er og 268,50128173828125 tekniske MHz-besøg. Der er ingen ny kvalifikation af astronomisk følsomhed, global falsk-alarm-sandsynlighed eller fysisk oprindelse.

Binære søgeresultater og genoptagelsesoplysninger er gemt i [SETI_BH_SEARCH_RESULTS_2026-10-29.zip](https://chatgpt.com/library?file_id=libfile_329ffff857308191a803f3b48aab6bc7&account_id=personal). Pakkens 165 medlemmer er kontrolleret med CRC og SHA-256; rådata og programkode er ikke duplikeret.

Næste sammenhængende batch er **q17–q24**, med en ny fast plan før beregning. De gemte rådata gør fortsættelsen uafhængig af den pauserede HIP44295-hentning. Ingen signalsøgning kører videre i baggrunden efter denne batch.

- [Fast plan](work_bh/PLAN_BH.json) og [søgekode](work_bh/bounded_search_bh.py)
- [Samlet resultat og kumulativ status](work_bh/results/REAL_SEARCH_SUMMARY_BH.json)
- [Faktisk procesafslutning](work_bh/execution/SEARCH_ACTUAL_EXIT_BH.json)
- [Afgrænset resultatkontrol](work_bh/review/REAL_RESULT_AUDIT_BH.json)
- [Datapakke og fortsættelsespunkt](work_bh/DELIVERY_BH.json)
