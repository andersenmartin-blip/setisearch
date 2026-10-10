# SETI: fast driftsøgning i native udsnit 155, 157

**10. oktober 2026.** Alle de fastlåste numeriske grupper sluttede COMPLETE én gang og har bestået de krævede kontroller af gemte outputs og kildeceller.
Der er gemt 1.524 ON-felter og 36 faste top-3-profiler.

De stærkeste udvalgte spor i gruppe1 af begge udsnit er stationære linjer, som også er tydelige i alle tre OFF-kontrolscanninger. De giver derfor foreløbig ikke grundlag for at udpege et signal fra målet. De øvrige profiler forbliver uafklarede; denne beskrivende sammenligning fastslår ingen signaloprindelse.

Alle seks scanninger er fra ét historisk besøg den 17. marts 2016. Ranglisterne forbliver separate pr. native udsnit, gruppe og ON-scanning; profilidentiteten er (source_chunk_id, batch_id, track_id). Antallet af udvalgte spor er ikke antallet af uafhængige fysiske signaler.

6.242.304 ON-referencekanal/originkombinationer er evalueret med 1.526 gyldige drift/breddehypoteser hver: 9.525.755.904 hypotesekombinationer.
For hver referencekanal gemmes maksimumscore og vindende drift/bredde med verificeret hypoteseantal. Dækningen er 254/256 referencefelter (99,21875 %) i hvert af disse udsnit, alene for de 763 drifthastigheder fra −4 til +4 Hz/s og bredde 1/3. De to randfelter er usøgte; haloer er ikke yderligere carrier-dækning eller uafhængige forsøg.

En særskilt kildecellekontrol matcher 445.824 råcelleforekomster i 36 udklip bit for bit mod de kompakte kilder.
Overlap mellem udklip kan gentage fysiske celler. Kompakt- og rækkehashes erstatter ikke de store originale HDF5-kilders fulde MD5, som fortsat ikke er verificeret.

| Udsnit | Gruppe | Felter | Profiler | CPU-sekunder | Vægtid, sekunder | Maksimal RSS, bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 155 | 1 | 381 | 9 | 1777,975 | 1797,574 | 635129856 |
| 155 | 2 | 381 | 9 | 1433,467 | 1453,122 | 632098816 |
| 157 | 1 | 381 | 9 | 1589,188 | 1606,389 | 631746560 |
| 157 | 2 | 381 | 9 | 1874,898 | 1896,328 | 632803328 |

Den oprindelige grænse er 2.000 CPU-sekunder, 2.400 sekunders vægtid og 4 GiB RAM pr. numerisk gruppe. Arbejdsallokeringer er planlægning, ikke en abonnementsbalance eller global stopgrænse. Der bruges ingen betalte ressourcer eller nye teleskopbytes i opsummeringen.

I gruppe1 vælger alle tre ON-ranglister samme stationære kanal som rang1. De gemte middelresidualer på det uændrede spor er:

| Udsnit / frekvens, MHz | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 155 / 1415,0390625 | 4,814162 | 4,714112 | 4,822211 | 4,916491 | 4,535683 | 4,840158 |
| 157 / 1409,1796875 | 6,558549 | 6,424657 | 6,528459 | 6,463567 | 6,406578 | 6,519083 |

Rang2/3 i disse to grupper ligger tæt på samme linjer og er bevægelige varianter af de udvalgte spor, ikke dokumenterede uafhængige signaler. En lav residual på deres præcise OFF-spor kan sameksistere med den stærke stationære linje tæt ved. Gruppe2 har lavere profilmiddelresidualer og flere valgte frekvenser og drifthastigheder; en kort tabel er ikke en validering af disse profiler.

| Udsnit | Gruppe | ON/rang | Frekvens, MHz | Drift, Hz/s | Bredde | ON-middel | OFF før | OFF efter |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 155 | 1 | ON1/1 | 1415,039062 | 0,000000 | 1 | 4,814162 | — | 4,714112 |
| 155 | 1 | ON1/2 | 1415,039074 | -0,052493 | 3 | 0,843579 | — | 0,011550 |
| 155 | 1 | ON1/3 | 1415,039051 | 0,052493 | 3 | 0,827666 | — | -0,017651 |
| 155 | 1 | ON2/1 | 1415,039062 | 0,000000 | 1 | 4,822211 | 4,714112 | 4,916491 |
| 155 | 1 | ON2/2 | 1415,039074 | -0,052493 | 3 | 0,812919 | -0,007732 | 0,004828 |
| 155 | 1 | ON2/3 | 1415,039051 | 0,052493 | 3 | 0,813414 | -0,002851 | -0,014661 |
| 155 | 1 | ON3/1 | 1415,039062 | 0,000000 | 1 | 4,535683 | 4,916491 | 4,840158 |
| 155 | 1 | ON3/2 | 1415,039051 | 0,052493 | 3 | 0,754957 | -0,015430 | 0,030743 |
| 155 | 1 | ON3/3 | 1415,039074 | -0,052493 | 3 | 0,734913 | 0,000361 | 0,012410 |
| 155 | 2 | ON1/1 | 1413,381498 | 0,010499 | 3 | 0,138326 | — | 0,105539 |
| 155 | 2 | ON1/2 | 1413,350010 | 0,000000 | 1 | 0,201045 | — | 0,170953 |
| 155 | 2 | ON1/3 | 1413,381509 | -0,062992 | 3 | 0,111249 | — | -0,011686 |
| 155 | 2 | ON2/1 | 1413,381501 | 0,000000 | 3 | 0,121177 | 0,126484 | 0,103572 |
| 155 | 2 | ON2/2 | 1413,350010 | 0,000000 | 1 | 0,200619 | 0,170953 | 0,206384 |
| 155 | 2 | ON2/3 | 1413,610303 | -3,863517 | 3 | 0,056225 | -0,004036 | 0,016804 |
| 155 | 2 | ON3/1 | 1413,381498 | -0,010499 | 3 | 0,103810 | 0,102330 | 0,021446 |
| 155 | 2 | ON3/2 | 1413,350010 | 0,000000 | 1 | 0,186027 | 0,206384 | 0,230868 |
| 155 | 2 | ON3/3 | 1413,787741 | 2,456693 | 1 | 0,150114 | -0,020984 | -0,013583 |
| 157 | 1 | ON1/1 | 1409,179688 | 0,000000 | 1 | 6,558549 | — | 6,424657 |
| 157 | 1 | ON1/2 | 1409,179676 | 0,052493 | 3 | 1,102968 | — | 0,016514 |
| 157 | 1 | ON1/3 | 1409,179699 | -0,052493 | 3 | 1,094775 | — | -0,010112 |
| 157 | 1 | ON2/1 | 1409,179688 | 0,000000 | 1 | 6,528459 | 6,424657 | 6,463567 |
| 157 | 1 | ON2/2 | 1409,179699 | -0,052493 | 3 | 1,106991 | -0,035810 | 0,017090 |
| 157 | 1 | ON2/3 | 1409,179676 | 0,052493 | 3 | 1,102486 | -0,028129 | -0,005941 |
| 157 | 1 | ON3/1 | 1409,179688 | 0,000000 | 1 | 6,406578 | 6,463567 | 6,519083 |
| 157 | 1 | ON3/2 | 1409,179699 | -0,052493 | 3 | 1,089125 | -0,011302 | 0,016074 |
| 157 | 1 | ON3/3 | 1409,179676 | 0,052493 | 3 | 1,063485 | 0,028892 | 0,000830 |
| 157 | 2 | ON1/1 | 1407,714841 | 0,241470 | 3 | 0,070854 | — | 0,020233 |
| 157 | 2 | ON1/2 | 1407,714986 | -0,335958 | 3 | 0,074830 | — | -0,009233 |
| 157 | 2 | ON1/3 | 1407,852661 | 0,000000 | 3 | 0,124149 | — | 0,102566 |
| 157 | 2 | ON2/1 | 1407,714841 | 0,545932 | 3 | 0,070632 | 0,005827 | 0,010493 |
| 157 | 2 | ON2/2 | 1407,852661 | 0,000000 | 3 | 0,123760 | 0,102566 | 0,096905 |
| 157 | 2 | ON2/3 | 1407,714858 | 0,000000 | 3 | 0,103096 | 0,066072 | 0,075858 |
| 157 | 2 | ON3/1 | 1407,714838 | 0,923885 | 3 | 0,058640 | 0,001121 | -0,024494 |
| 157 | 2 | ON3/2 | 1407,714895 | -0,094488 | 3 | 0,101605 | 0,039378 | 0,042719 |
| 157 | 2 | ON3/3 | 1407,852661 | -0,010499 | 3 | 0,130828 | 0,085832 | 0,104248 |

Tabellen viser gemte middelresidualer af normaliseret centereffekt minus de bevægelige flankkanalers median inden for ±64 kanaler med absolut offset større end tre. Detektorens robuste rangscore er en anden størrelse end denne profilmiddelresidual. Alle seks uændrede spor bevares i JSON/CSV. ON1 har kun efterfølgende OFF i sekvensen; ON2/ON3 har både forudgående og efterfølgende OFF.
En lille residual på det præcise OFF-spor fastslår ikke fravær af nærliggende OFF-struktur. Profilerne er udvalgt efter ON-rangscore og forbliver uafklarede. Ingen OFF-forskydning, ny score, rangliste eller profil genberegnes af opsummeringen.

A/B forbliver FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og gamle holdouts samt beskyttede udsnit 156/159 er lukkede. Der er ikke beregnet kalibreret SNR, falskalarmrate, flux, EIRP eller følsomhed. Der fastslås ingen signaloprindelse, kvalificeret SETI-kandidat, generelt nulresultat eller uafhængighed mellem hypoteser, spor, udsnit eller scanninger.
Original kode/scope blev fastlåst ved `5acdb2f9c42b5e7ce58437d30ea9527763f8f821` med scope-SHA256 `9670e4c961d349dc3cc320a16b8c2f705928edeb58c543aa5d52166a6c021e7a` før de nye kildeværdier. Dette skaber ikke en uafhængig besøgsobservation. Den senere gemte-JSON-opsummering er bundet til postprocesseringsscope `f065a101fd3ea59f041e5f9c923b8a28b0c1c9638d68c80d3a37dcb4ad242d69` ved `c8f222e3da85cfdc3519e67cf1b64d65775ab54f` og kvitterer for alle input- og outputhashes.

[Dækningsfigur](results/radio_rolling_bands_20261010/figures/STAGE_COVERAGE.png) · [Faste profilmidler](results/radio_rolling_bands_20261010/figures/STAGE_FIXED_PROFILE_MEANS.png)
