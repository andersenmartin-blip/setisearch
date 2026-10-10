# Afsluttet S2017-udvidelse af native171

Alle tre fastfrosne batches er COMPLETE, og den samlede uafhængige output/kildekontrol er PASS. Udvidelsen tilføjer 253 hidtil usøgte referencekerner, 759 ON-kort, 3.108.864 ON-kanal-maksima og 4.880.916.480 korrelerede drift-bredde-kombinationer. Der blev gemt 27 faste top-3-profiler, 162 scan-profiler og 2.592 integration-række-forekomster; alle 334.368 rå profilcelle-forekomster bestod bitpræcis kildekontrol. 12.144 ON-kernerækkemidianer blev kontrolleret. Ingen nye teleskop-GETs eller BODY-bytes blev brugt; udvidelsens angivne kost er 0 DKK.

Sammen med den tidligere afsluttede q128 er 254 af 256 referencekerner dækket: 1.040.384 referencekanaler pr. ON, 99,21875 % af det erhvervede native171-udsnit, nominelt 2.906.799,31640625 Hz pr. ON. Den nye udvidelse alene dækker 98,828125 %. Randkernerne q0 og q255 er fortsat usøgte. Det er referencekanaldækning; drift/preprocesseringshaloer og adgang til hele kildeudsnittet udvider ikke dette tal. Der er ikke bestemt en kalibreret detektionsfølsomhed, fluxgrænse eller generel nuldetektionsgrænse. Samlede q128+udvidelsesantal er 762 kort, 3.121.152 maksima, 4.900.208.640 korrelerede kombinationer og 36 faste profiler/216 scan-profiler.

## Fortolkning af de valgte spor

Batch02s 60 top-20-rækker ligger alle i q127, på referencekanaler 179.830.500–179.830.783, lige ved den tidligere fundne fælles kanal 179.830.784 (2300,390625 MHz). Alle 60 frosne bokse indeholder denne fælles kanal i mindst én integration af deres oprindelige ON-scan; det gælder også samtlige ni faste top-3-profiler. At q128 ikke er genkørt, forhindrer ikke en q127-referenceboks i at nå q128-kanalen gennem bredde/drift. Dette er samme kendte strukturs geometriske påvirkning, ikke 60 uafhængige signaler eller en ny bekræftelse.

De tre rank-1-spor starter én kanal fra den fælles linje og har små negative valgte driftsværdier. Deres bokse indeholder linjen i alle 16 oprindelige ON-rækker. Eksakte frosne OFF-profiler er markant positive: ON1-sporets OFF1-middel er 176,144631; ON2-sporets OFF1/2 er 43,946983 og 183,418388; ON3-sporets OFF3 er 11,514521, hvor boksen kun omfatter linjen i første OFF3-række. Små værdier i senere scans følger, at det frosne driftspor flytter væk fra den stationære linje. Den tidligere q128-måling viser linjen i alle seks scans. Små eksakte OFF-spormidler er derfor ikke et bevis på lokal OFF-fravær eller en kvalificeret OFF-veto.

Batch02s rank-2/3-bokse krydser linjen senere i oprindelig ON. Eksempelvis er ON1/rank2s gemte halvdelmidler 0,000520 og 201,175882; rank3s er −0,017017 og 115,066233. Disse store slut-halvdelbidrag kræver ikke en særskilt bevægende emission. Den fysiske oprindelse af den fælles stationære struktur fastslås ikke her.

Batch01s top-20-scores ligger i 5,591634–6,356479, batch03s i 5,556727–6,201318; batch02s ligger i 1.418,778509–15.458,566496. Alle er maksimale robuste rangstatistikker efter en stor, korreleret søgning, ikke kalibreret SNR eller falsk-alarm-sandsynligheder. Batch01/03s 18 valgte profiler har oprindelige ON-midler 0,058809–0,166323 og positive gemte midler i begge halvdele. Deres andre ON-midler spænder −0,038532–0,049777, og OFF-midler −0,039084–0,048383: de er små, men ikke alle nul.

Over alle 27 profiler er 25/27 oprindelige ON-profiler positive i begge gemte halvdele, mod 18/54 andre ON-profiler og 25/81 OFF-profiler. Tre valgte spor er positive i begge halvdele af alle tre ON-scans: batch01 ON2/rank3 samt batch02 ON1/rank2 og ON3/rank2. Det ene batch01-eksempel har ON-midler 0,042741/0,153596/0,029045; dets OFF2-halvdelmidler er 0,057044 og −0,037279. Tegn og halvdelmidler er beskrivelser fra de samme ON-udvalgte data, ikke nye uafhængige tests, en detektionstærskel eller kalibreret persistens. Alle 162 scan-midler, halvdelmidler og positive-række-antal findes i CSV/JSON uden at nulstille andre ON- eller OFF-værdier.

De tre batches er administrative opdelinger af ét historisk besøg den 28. april 2017. Der er ingen ny observation eller blind uafhængig validering. S-båndsbesøget reproducerer ikke de gamle L-båndsspor ved samme frekvens. Der foreligger ingen kvalificeret SETI-detektion, fysisk oprindelsesafgørelse, kalibreret falsk-alarm-sandsynlighed eller generel nuldetektionsgrænse.

## Rank1: alle seks eksakte gemte midler

Midlerne er bredde-middel af rå power divideret med rækkens median over hele native-udsnittet, minus den faste flankemedian. De er dimensionløse beskrivende mål; scores har en særskilt uændret kerne-median/MAD-normalisering. Tabellen er afrundet; JSON/CSV bevarer de gemte værdier.

| Batch | Valgt ON | MHz ved reference | Drift Hz/s | Score | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| batch01 | epoch1_on | 2301.269515045 | 0.336734694 | 6.160813 | 0.091451 | -0.019401 | -0.005640 | -0.008366 | 0.006022 | 0.017494 |
| batch01 | epoch2_on | 2301.795672253 | -0.948979592 | 6.188912 | -0.005027 | 0.004491 | 0.089477 | -0.026871 | -0.000102 | 0.011583 |
| batch01 | epoch3_on | 2301.035984047 | -2.938775510 | 6.356479 | -0.020238 | 0.004203 | 0.022096 | 0.001742 | 0.097547 | 0.004584 |
| batch02 | epoch1_on | 2300.390627794 | -0.010204082 | 15458.566496 | 230.396937 | 176.144631 | -0.009474 | -0.011129 | 0.022507 | -0.028582 |
| batch02 | epoch2_on | 2300.390627794 | -0.010204082 | 12813.739287 | 0.008896 | 43.946983 | 189.506116 | 183.418388 | 0.007931 | -0.015741 |
| batch02 | epoch3_on | 2300.390627794 | -0.020408163 | 12942.460482 | 0.002847 | 0.018148 | -0.001419 | -0.016114 | 191.241516 | 11.514521 |
| batch03 | epoch1_on | 2299.051501416 | 3.887755102 | 6.121757 | 0.058809 | 0.003673 | 0.011460 | -0.006593 | 0.002212 | 0.001508 |
| batch03 | epoch2_on | 2299.603231810 | -1.867346939 | 6.005318 | 0.012404 | -0.002264 | 0.091747 | 0.002960 | 0.010846 | 0.005075 |
| batch03 | epoch3_on | 2299.071958847 | 1.091836735 | 6.201318 | 0.025065 | 0.002694 | -0.011871 | -0.010735 | 0.104572 | 0.009871 |

## Faktiske procesmålinger

| Proces | CPU s | Wall s | Peak RSS bytes |
|---|---:|---:|---:|
| batch01 | 468.237484 | 468.257866 | 543232000 |
| batch02 | 465.514561 | 465.509392 | 543346688 |
| batch03 | 469.011889 | 469.044300 | 543305728 |
| Samlet output/kilde-QA | 4.464805 | 4.414701 | 156336128 |

CPU-tallene summerer til 1.402,763934 s for de tre batch-processer; dette er ikke samlet ende-til-ende setup-, rapporterings- eller paknings-CPU. Hver proces havde 1.000 CPU-s / 1.800 wall-s / 2 GiB AS-grænse; to kernel-låsepladser begrænser samtidige udvidelsesprocesser til et samlet AS-loft på 4 GiB. AS-grænsen og målt RSS er forskellige størrelser.

## Evidens

Den faktiske samlede QA-receipt er `e1d77ef88fa7a47965bd783b09258b36578c476cd5788ffc94924f3e03d1bc6f`; udvidelsens offentlige kode/scope-fastfrysning er `76fb1da5a0af22d6182daed90e4bdca92f2470f8`. `FULL_BAND_SUMMARY.json` og `FULL_BAND_PROFILE_MEANS.csv` blev genereret præcis én gang fra de tre faktiske COMPLETE-receipts og QA-hashbundne gemte profil/top-20-JSON. Den uafhængige kontrol genberegner ikke detektorscores. Denne opsummering og videnskabelige gennemgang læser ingen HDF5- eller NPZ-data, tilpasser ingen spor og foretager ingen ny søgning. A/B-status og oprindelige fejlkvitteringer forbliver uændrede.
