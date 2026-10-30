# SETI BJ V2 — længere kørsel: bånd 25–120 er gennemsøgt

30. oktober 2026. **De 12 effektive batches er afsluttet med faktisk exitkode 0 for både søgning og resultatkontrol. Den første provenancefejl i batch 10 er bevaret.** De 96 ekstra bånd gav **5.196.054.528 korrelerede sporkombinationer**. Ingen ON-spor nåede den faste lokale ESS-tærskel 10. Ingen nye SETI-kandidater er kvalificeret.

| Størrelse | Denne kørsel: BJ | Samlet: BG–BJ |
|---|---:|---:|
| Faste bånd | 96 (q25–q120) | **120 (q1–q120)** |
| Carrierkanaler | 393.216 | 491.520 |
| Teknisk kanalbredde | 1,098633 MHz | **1,373291 MHz** |
| Scan/bånd-søgninger | 576 | 720 |
| Korrelerede sporkombinationer, inklusive OFF | 5.196.054.528 | **6.495.068.160** |
| ON-spor med lokal ESS ≥10 | 0 | 0 |
| OFF-spor med lokal ESS ≥10 | 0 | 0 |
| Faktiske, udløste ON/OFF-spormålinger | 0 | 0 |
| Beståede beskrivende ON/OFF-flag | 0 | 0 |

Forløbet tog 1.427,80 sekunder (23,80 minutter) fra den oprindelige start til V2-afslutningsmarkøren, inklusive stoppet og genoptagelsen. De 12 effektive søgekørsler brugte tilsammen 807,15 sekunders vægtid og 804,81 CPU-sekunder (bruger- og systemtid). Resultatkontrollerne brugte 23,28 sekunders vægtid og 33,04 CPU-sekunder. Dette er målinger for BJ-kørslen, ikke et samlet forbrug for hele projektet.

Den første søgning i batch 10 sluttede med exit 0, men efterkontrollen sluttede med **exit 1**: logfilen havde 19.347 gemte bytes mod 20.161 registreret ved procesafslutningen. Denne log er ikke rekonstrueret, og den fejlede kontrol er ikke omklassificeret som et godkendt nulresultat. De første ni beståede batches blev fastholdt; batch 10 blev kørt igen i nye filer med samme båndvalg, tærskler og numeriske kode, hvorefter batch 11–12 blev afsluttet.

Den oprindelige batch 10 kostede yderligere 67,03 sekunders søgetid og 1,69 sekunders fejlet kontrol. Alle 13 målte søgeforsøg brugte i alt 874,18 sekunders vægtid og 871,66 CPU-sekunder. De 13 kontrolforsøg brugte 24,96 sekunders vægtid og 35,55 CPU-sekunder. Bånd og sporkombinationer tælles stadig kun én gang i de effektive resultater.

| Batch | Bånd | ON ≥10 | OFF ≥10 | Søgning, s | Kontrol, s |
|---:|---|---:|---:|---:|---:|
| 1 | q25–q32 | 0 | 0 | 67,38 | 1,98 |
| 2 | q33–q40 | 0 | 0 | 64,89 | 1,91 |
| 3 | q41–q48 | 0 | 0 | 67,85 | 1,86 |
| 4 | q49–q56 | 0 | 0 | 65,19 | 2,00 |
| 5 | q57–q64 | 0 | 0 | 65,05 | 1,95 |
| 6 | q65–q72 | 0 | 0 | 65,65 | 1,90 |
| 7 | q73–q80 | 0 | 0 | 69,85 | 1,92 |
| 8 | q81–q88 | 0 | 0 | 70,10 | 1,98 |
| 9 | q89–q96 | 0 | 0 | 70,27 | 2,01 |
| 10 | q97–q104 | 0 | 0 | 66,93 | 1,88 |
| 11 | q105–q112 | 0 | 0 | 66,44 | 2,09 |
| 12 | q113–q120 | 0 | 0 | 67,53 | 1,80 |

BJ dækker frekvenscentrene 2.300,470736–2.301,569366 MHz i de samme seks scans af HIP98505 / HD189733 fra 28. april 2017: tre ON og tre OFF med 16 tidsrækker hver. Søgebredderne er fortsat 1, 3, 9 og 33 kanaler med 839 drifttrin over ±4 Hz/s. De afsluttede q1–q24 er bevaret.

| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |
|---:|---:|---:|
| 1 | 6,434 | 6,475 |
| 3 | 6,242 | 6,552 |
| 9 | 6,076 | 5,947 |
| 33 | 5,850 | 6,360 |

Alle båndvalg, søgekode, kontrolkode og planer blev [fastholdt på GitHub før beregningen](https://github.com/andersenmartin-blip/setisearch/commit/4c82703dd1a2de8da94b4411ace5cede2a77fa6f). Den særskilte [genoptagelsesplan blev fastholdt før nye kørsler](https://github.com/andersenmartin-blip/setisearch/commit/5623a1d31476a306cbbeceaba03101fbdb2562d1). Den numeriske metode er uændret fra BI; AC-normaliseringen beregnes over hele hver native-række før beskæring. Hver batch fulgtes af en afgrænset resultatkontrol, og kampagnen var indrettet til at stoppe ved fejl eller et bestået beskrivende signalflag.

De 12 beståede efterkontroller omfattede **20.736 udvalgte sporsummer med uafhængig `math.fsum`** og **6.912 kalibreringsgenberegninger med den delte kernel**. De største observerede afvigelser var 0,000000 for skalarsummer og 0,000000 for kalibrering. Proceskvitteringerne registrerer faktisk exitkode, stdout-EOF, afsluttet procesventning og overensstemmelse mellem observerede og gemte loghashes. Dette er en afgrænset kontrol, ikke en uafhængig genberegning af alle spor, rådatakodek eller hele normaliseringsmodellen.

Der var ingen ON-frø over tærsklen og derfor **ingen faktiske, udløste spormålinger på tværs af ON/OFF**. Konsistens i tomme kataloger er ikke et selvstændigt fysisk ON/OFF-resultat.

Resultatet er en beskrivende genanalyse af tidligere eksponerede data fra ét historisk besøg. ESS kalibreres lokalt pr. bånd, drifttrin, bredde og scan og adskiller sig fra den historiske full-native ESS. ESS er ikke en kalibreret sigma-værdi, SNR eller falsk-alarm-sandsynlighed. Sporkombinationerne er korrelerede og må ikke tælles som uafhængige statistiske prøver. Ingen astronomisk følsomhed, fysisk oprindelse eller opdagelse er kvalificeret.

Der blev foretaget 0 nye arkivanmodninger og tilføjet 0 nye observationer. BA-opgørelsen forbliver 486 unikke arkiv-ID’er og 268,50128173828125 tekniske MHz-besøg.

Binære resultater og genoptagelsesoplysninger er gemt i [SETI_BJ_SEARCH_RESULTS_V2_2026-10-30.zip](https://chatgpt.com/library?file_id=libfile_9d7e8c2adb048191955ba6f7e362cbe4&account_id=personal). Pakken har 2.133 medlemmer: 1.968 effektive binære resultatfiler, 164 særskilt mærkede binære filer fra det første fejlede batch 10-forsøg og én genoptagelsesfil. CRC og SHA-256 er kontrolleret for alle medlemmer. Sammenligningen af de 164 tilsvarende binære filer fra oprindelig og genkørt batch 10 viste 164 med samme SHA-256 og 0 med forskellige hashes. Denne bytekontrol ændrer ikke den oprindelige fejlede provenancekontrol. Rådata og programkode er bevaret via eksisterende datakilder og GitHub.

Næste scope er **q121–q127** med en ny fast plan. Derefter skal **DC-bånd q128 udelades eksplicit**, før senere sikre bånd vælges. Ingen signalsøgning kører videre i baggrunden efter denne kampagne.

- [Samlet resultat og kumulativ status](work_bj/results/REAL_SEARCH_SUMMARY_BJ_V2.json)
- [Kampagnens V2-afslutning](work_bj/results/CAMPAIGN_COMPLETE_BJ_V2.json) og [det oprindelige stop](work_bj/results/CAMPAIGN_STOP_BJ.json)
- [Faste planer](work_bj/plans) og [søgekode](work_bj/bounded_search_bj.py)
- [Sekventiel processtyring](work_bj/run_campaign_bj.py) og [afgrænset resultatkontrol](work_bj/review/audit_real_results_bj.py)
- [Datapakke og fortsættelsespunkt](work_bj/DELIVERY_BJ_V2.json)
