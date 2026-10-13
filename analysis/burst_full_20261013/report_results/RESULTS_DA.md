# Fuld ON-burstsøgning, 13. oktober 2026

Søgningen er afsluttet med bestået kilde-QA, uafhængig global sorterings-QA og kildekontrol af alle 54 faste profiler. Ingen kvalificeret SETI-detektion eller kalibreret falsk-alarm-sandsynlighed er etableret.

2.010 nye kort og 288 uændrede pilotkort dækker de fastlagte 766 referencekerner pr. ON-scan i native 170/171/172. Det er 9.412.608 referencekanalforekomster og 20.952.465.408 korrelerede hypoteseforekomster. Dækningen gælder dette afgrænsede frekvensudsnit og søgegitter. Alle scans kommer fra samme allerede eksponerede besøg 28. april 2017.

| Faste profiler | Antal | Fire-række-score, min til maks. | Fuld 16-række-score, min til maks. |
|---|---:|---:|---:|
| Oprindeligt ON-scan | 9 | 6,638491 til 7,450295 | 2,170159 til 4,579651 |
| Andre ON-scans | 18 | -1,243823 til 2,042495 | -1,223910 til 3,336837 |
| OFF-scans | 27 | -2,191447 til 2,306076 | -1,544274 til 2,604961 |

Syv af de ni globale udvalg kommer fra udvidelsen; to svarer til eksakte tidligere pilot-tupler. Alle 54 profiler blev beregnet i denne udførelse. Tolv tidligere query-identiteter blev efterfølgende verificeret som bitidentiske; 42 er nye faste queries. Ingen af de 54 profiler har direkte kontakt med de tre kendte DC-kanaler i de valgte fire rækker eller de fulde 16 rækker. Det udelukker ikke anden interferens eller lækage fra nabokanaler.

Den højeste udvalgte søgescore er 7,450295 ved referencefrekvens 2297,995686159 MHz i epoch3_on. Det er en empirisk score efter maksimering. Den er ikke SNR, sigma eller evidens for kunstig oprindelse. Svage faste ON/OFF-responser beviser ikke stjerneeksklusivitet eller fravær af et signal; de grove drifttrin og pauser mellem scans begrænser sammenligningen. 73,014 sekunder er testvinduets længde, ikke en målt emissionsvarighed.

Begge maksimumfamilier er bevaret: frit maksimum og bedste hypotese, hvis fire bokse undgår DC. 1.431 frie vindere ændres eller bliver tomme; 1.422 har et tilladt alternativ, og ni har ingen. Kilde-QA kontrollerer 10.050 rå scoreforespørgsler og genberegner hele den oprindelige dual-familie i 18 DC-nære kerner. De øvrige 1.992 nye kerner har geometrisk identiske tilladte familier, med rå median- og scorekontrol; deres komplette gitter er ikke uafhængigt genberegnet.

Resultatpakken indeholder alle 2.298 kort, råkapsler, profiler, kode og kontrolgrundlag. De oprindelige 18 H5-kompakter er eksterne forudsætninger for en genkørsel af hele produktionsanalysen. Den selvstændige NumPy-replay efterregner de 10.050 gemte scoreforespørgsler og 18 gemte DC-rammer; den efterregner ikke alle pilot-, globale rang- og kontekstberegninger. Den genbruger de samme uafhængige QA-hjælpere og er derfor ikke en tredje uafhængig implementering.

Original A/B er fortsat FAIL_CLOSED; beskyttede 2016-kontroller og lukkede 2019-data er uændrede. Ingen ny observation eller teleskoprequest. Udgift: 0 DKK. Det formelle checkpoint er fortsat 20. oktober 2026.
