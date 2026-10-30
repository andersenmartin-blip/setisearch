# SETI BK — alle 253 valgte sikre bånd i native171 er gennemgået

30. oktober 2026. **Alle 17 batches er afsluttet med faktisk exitkode 0 for både søgning og resultatkontrol.** De 133 ekstra bånd gav **7.198.700.544 korrelerede sporkombinationer**. ON-katalogerne indeholder 52.510 lokale spor med ESS ≥10. Der blev målt 315.060 understøttede ON/OFF-sporværdier; 0 rækker opfyldte de beskrivende ON/OFF-regler.

| Størrelse | Denne kørsel: BK | Samlet: BG–BK |
|---|---:|---:|
| Faste carrierbånd | 133 (q121–q127 og q129–q254) | **253 (q1–q254, q128 udeladt)** |
| Carrierkanaler | 544.768 | 1.036.288 |
| Teknisk kanalbredde | 1,522064 MHz | **2,895355 MHz** |
| Scan/bånd-søgninger | 798 | 1.518 |
| Korrelerede sporkombinationer, inklusive OFF | 7.198.700.544 | **13.693.768.704** |
| ON-spor med lokal ESS ≥10 | 52.510 | 52.510 |
| OFF-spor med lokal ESS ≥10 | 52.678 | 52.678 |
| Faktiske, udløste ON/OFF-spormålinger | 315.060 | 315.060 |
| Beståede beskrivende ON/OFF-flag | 0 | 0 |

Kampagnen tog 1.181,50 sekunder (19,69 minutter) fra start til afslutningsmarkør. De målte søgekørsler brugte tilsammen 1.138,52 sekunders vægtid og 1.135,01 CPU-sekunder (bruger- og systemtid). Resultatkontrollerne brugte 32,02 sekunders vægtid og 45,82 CPU-sekunder. Dette er målinger for BK-kørslen, ikke et samlet forbrug for hele projektet.

| Batch | Bånd | ON ≥10 | OFF ≥10 | Søgning, s | Kontrol, s |
|---:|---|---:|---:|---:|---:|
| 1 | q121–q127 | 52.510 | 52.678 | 66,89 | 1,91 |
| 2 | q129–q136 | 0 | 0 | 68,72 | 1,90 |
| 3 | q137–q144 | 0 | 0 | 67,55 | 1,94 |
| 4 | q145–q152 | 0 | 0 | 72,03 | 2,00 |
| 5 | q153–q160 | 0 | 0 | 66,08 | 1,87 |
| 6 | q161–q168 | 0 | 0 | 68,35 | 1,95 |
| 7 | q169–q176 | 0 | 0 | 66,55 | 1,82 |
| 8 | q177–q184 | 0 | 0 | 70,97 | 2,09 |
| 9 | q185–q192 | 0 | 0 | 72,92 | 1,96 |
| 10 | q193–q200 | 0 | 0 | 65,77 | 1,81 |
| 11 | q201–q208 | 0 | 0 | 66,53 | 1,83 |
| 12 | q209–q216 | 0 | 0 | 68,86 | 1,86 |
| 13 | q217–q224 | 0 | 0 | 67,14 | 1,87 |
| 14 | q225–q232 | 0 | 0 | 67,10 | 1,89 |
| 15 | q233–q240 | 0 | 0 | 65,44 | 1,92 |
| 16 | q241–q248 | 0 | 0 | 67,79 | 1,87 |
| 17 | q249–q254 | 0 | 0 | 49,84 | 1,52 |

BK dækker frekvenscentrene 2.298,937228–2.300,470734 MHz i de samme seks scans af HIP98505 / HD189733 fra 28. april 2017: tre ON og tre OFF med 16 tidsrækker hver. Søgebredderne er fortsat 1, 3, 9 og 33 kanaler med 839 drifttrin over ±4 Hz/s. De afsluttede q1–q120 er bevaret. DC-bånd q128 og kantbånd q0/q255 er udeladt fra søgecentrene.

| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |
|---:|---:|---:|
| 1 | 8.386,589 | 6.920,443 |
| 3 | 15.468,433 | 12.457,416 |
| 9 | 9.116,125 | 7.606,159 |
| 33 | 5.044,370 | 4.431,902 |

Alle båndvalg, søgekode, kontrolkode og planer blev [fastholdt på GitHub før beregningen](https://github.com/andersenmartin-blip/setisearch/commit/35875088a7b5fcb8c7424386b29acb7318bfc877). Den numeriske metode er uændret fra BJ; AC-normaliseringen beregnes over hele hver native-række før beskæring. Hver batch fulgtes af en afgrænset resultatkontrol, og kampagnen var indrettet til at stoppe ved fejl eller et bestået beskrivende signalflag.

Kontrollerne omfattede **28.728 udvalgte sporsummer med uafhængig `math.fsum`** og **9.576 kalibreringsgenberegninger med den delte kernel**. De største observerede afvigelser var 0,000000 for skalarsummer og 0,000000 for kalibrering. Proceskvitteringerne registrerer faktisk exitkode, stdout-EOF, afsluttet procesventning og overensstemmelse mellem observerede og gemte loghashes. Dette er en afgrænset kontrol, ikke en uafhængig genberegning af alle spor, rådatakodek eller hele normaliseringsmodellen.

ON-frøene udløste 315.060 målepladser, hvoraf 315.060 var understøttede og 0 lå uden for det gemte supportområde. Beskrivende flag er ikke kvalificerede SETI-detektioner.

Alle 52.510 ON-katalogrækker ligger i q127, lige ved det udeladte DC-bånd. Det er korrelerede sporforslag, ikke 52.510 forskellige signaler. Af dem opfyldte 33 kravet om lokal ESS ≥10 i alle tre ON-scans; alle 33 havde også OFF-udslag ≥5 og blev derfor fravalgt. De øvrige 52.477 opfyldte ikke kravet i alle tre ON-scans. [Fordeling ud fra de allerede gemte kontrolmålinger](work_bk/results/Q127_TRIAGE_DISPOSITION_BK.json).

Resultatet er en beskrivende genanalyse af tidligere eksponerede data fra ét historisk besøg. ESS kalibreres lokalt pr. bånd, drifttrin, bredde og scan og adskiller sig fra den historiske full-native ESS. ESS er ikke en kalibreret sigma-værdi, SNR eller falsk-alarm-sandsynlighed. Sporkombinationerne er korrelerede og må ikke tælles som uafhængige statistiske prøver. Ingen astronomisk følsomhed, fysisk oprindelse eller opdagelse er kvalificeret.

Der blev foretaget 0 nye arkivanmodninger og tilføjet 0 nye observationer. BA-opgørelsen forbliver 486 unikke arkiv-ID’er og 268,50128173828125 tekniske MHz-besøg.

Binære resultater og genoptagelsesoplysninger er gemt i [SETI_BK_SEARCH_RESULTS_2026-10-30.zip](https://chatgpt.com/library?file_id=libfile_7525d4b15af88191828cbefa51630eeb&account_id=personal). Pakken har 2.732 medlemmer: 2.731 binære resultatfiler og én genoptagelsesfil. CRC og SHA-256 er kontrolleret for alle medlemmer. Rådata og programkode er bevaret via eksisterende datakilder og GitHub.

Den fastlagte familie af **253 sikre carrierbånd i netop denne gemte native171-rådatablok er nu færdig**. Dette afslutter ikke hele teleskoparkivet eller projektet.

Som konkret næste datagrundlag er de tidligere gemte **native170 og native172** fra samme historiske besøg genindlæst i en særskilt mappe. De tre arkivdele, det samlede arkiv på 604.399.781 bytes, alle 12 kompakte HDF5-filer og deres 192 dekodede rækker matcher de oprindelige SHA-256-kontrolsummer. Det krævede ingen ny anmodning til teleskoparkivet. Der er endnu ikke beregnet nye søgescorer på disse naboblokke. Næste trin er en særskilt fast plan for en udvidet beskrivende søgning på native170; native172 følger under sin egen afgrænsning, med de historiske A/B- og B06-fejlstatusser bevaret. [Kontrolleret datagrundlag og præcist fortsættelsespunkt](work_bk/next_data/PREPARED_ADJACENT_DATA_BK.json).

Beskyttede 2016-/2019-data, DC-bånd q128 og kantbånd q0/q255 åbnes ikke automatisk. Ingen signalsøgning kører videre i baggrunden efter denne kampagne.

- [Samlet resultat og kumulativ status](work_bk/results/REAL_SEARCH_SUMMARY_BK.json)
- [Kampagnens afslutningsmarkør](work_bk/results/CAMPAIGN_COMPLETE_BK.json)
- [Faste planer](work_bk/plans) og [søgekode](work_bk/bounded_search_bk.py)
- [Sekventiel processtyring](work_bk/run_campaign_bk.py) og [afgrænset resultatkontrol](work_bk/review/audit_real_results_bk.py)
- [Datapakke og fortsættelsespunkt](work_bk/DELIVERY_BK.json)
