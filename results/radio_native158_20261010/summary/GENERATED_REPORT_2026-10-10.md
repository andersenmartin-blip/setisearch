# SETI: fast driftsøgning i native udsnit 158

**10. oktober 2026.** Alle de fastlåste numeriske grupper sluttede COMPLETE én gang og har bestået de krævede kontroller af gemte outputs og kildeceller.
Der er gemt 762 ON-felter og 18 faste top-3-profiler.

Alle seks scanninger er fra ét historisk besøg den 17. marts 2016. Ranglisterne forbliver separate pr. native udsnit, gruppe og ON-scanning; profilidentiteten er (source_chunk_id, batch_id, track_id). Antallet af udvalgte spor er ikke antallet af uafhængige fysiske signaler.

3.121.152 ON-referencekanal/originkombinationer er evalueret med 1.526 gyldige drift/breddehypoteser hver: 4.762.877.952 hypotesekombinationer.
For hver referencekanal gemmes maksimumscore og vindende drift/bredde med verificeret hypoteseantal. Dækningen er 254/256 referencefelter (99,21875 %) i hvert af disse udsnit, alene for de 763 drifthastigheder fra −4 til +4 Hz/s og bredde 1/3. De to randfelter er usøgte; haloer er ikke yderligere carrier-dækning eller uafhængige forsøg.

En særskilt kildecellekontrol matcher 222.912 råcelleforekomster i 18 udklip bit for bit mod de kompakte kilder.
Overlap mellem udklip kan gentage fysiske celler. Kompakt- og rækkehashes erstatter ikke de store originale HDF5-kilders fulde MD5, som fortsat ikke er verificeret.

| Udsnit | Gruppe | Felter | Profiler | CPU-sekunder | Vægtid, sekunder | Maksimal RSS, bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 158 | 1 | 381 | 9 | 1607,359 | 1608,802 | 632442880 |
| 158 | 2 | 381 | 9 | 1378,854 | 1379,562 | 634335232 |

Den oprindelige grænse er 2.000 CPU-sekunder, 2.400 sekunders vægtid og 4 GiB RAM pr. numerisk gruppe. Arbejdsallokeringer er planlægning, ikke en abonnementsbalance eller global stopgrænse. Der bruges ingen betalte ressourcer eller nye teleskopbytes i opsummeringen.

| Udsnit | Gruppe | ON/rang | Frekvens, MHz | Drift, Hz/s | Bredde | ON-middel | OFF før | OFF efter |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 158 | 1 | ON1/1 | 1406,250000 | 0,000000 | 1 | 40312,503646 | — | 40153,356265 |
| 158 | 1 | ON1/2 | 1406,249989 | 0,052493 | 3 | 6688,540366 | — | 0,326878 |
| 158 | 1 | ON1/3 | 1406,250011 | -0,052493 | 3 | 6688,525017 | — | 0,317197 |
| 158 | 1 | ON2/1 | 1406,250000 | 0,000000 | 1 | 40674,489033 | 40153,356265 | 40662,893647 |
| 158 | 1 | ON2/2 | 1406,250011 | -0,052493 | 3 | 6727,463409 | 0,081207 | 0,305157 |
| 158 | 1 | ON2/3 | 1406,249989 | 0,052493 | 3 | 6727,435864 | 0,121791 | 0,327178 |
| 158 | 1 | ON3/1 | 1406,250000 | 0,000000 | 1 | 40231,514621 | 40662,893647 | 40648,170492 |
| 158 | 1 | ON3/2 | 1406,249989 | 0,052493 | 3 | 6661,019037 | 0,121309 | 0,317273 |
| 158 | 1 | ON3/3 | 1406,250011 | -0,052493 | 3 | 6661,006920 | 0,118186 | 0,334128 |
| 158 | 2 | ON1/1 | 1404,138063 | 0,000000 | 1 | 0,988111 | — | 1,161299 |
| 158 | 2 | ON1/2 | 1404,166767 | -0,010499 | 3 | 0,381846 | — | 0,141148 |
| 158 | 2 | ON1/3 | 1404,166778 | -0,083990 | 3 | 0,238624 | — | -0,020326 |
| 158 | 2 | ON2/1 | 1404,138063 | 0,000000 | 1 | 0,995061 | 1,161299 | 0,613452 |
| 158 | 2 | ON2/2 | 1404,166767 | 0,000000 | 3 | 0,363968 | 0,356674 | 0,333125 |
| 158 | 2 | ON2/3 | 1404,131924 | 0,000000 | 1 | 0,481408 | 0,269105 | 0,340909 |
| 158 | 2 | ON3/1 | 1404,138063 | -0,010499 | 1 | 0,787424 | 0,093876 | 0,114009 |
| 158 | 2 | ON3/2 | 1404,166767 | -0,010499 | 3 | 0,328846 | 0,271758 | 0,268061 |
| 158 | 2 | ON3/3 | 1404,131924 | 0,000000 | 1 | 0,419427 | 0,340909 | 0,315515 |

Tabellen viser gemte middelresidualer af normaliseret centereffekt minus de bevægelige flankkanalers median inden for ±64 kanaler med absolut offset større end tre. Detektorens robuste rangscore er en anden størrelse end denne profilmiddelresidual. Alle seks uændrede spor bevares i JSON/CSV. ON1 har kun efterfølgende OFF i sekvensen; ON2/ON3 har både forudgående og efterfølgende OFF.
En lille residual på det præcise OFF-spor fastslår ikke fravær af nærliggende OFF-struktur. Profilerne er udvalgt efter ON-rangscore og forbliver uafklarede. Ingen OFF-forskydning, ny score, rangliste eller profil genberegnes af opsummeringen.

A/B forbliver FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og gamle holdouts samt beskyttede udsnit 156/159 er lukkede. Der er ikke beregnet kalibreret SNR, falskalarmrate, flux, EIRP eller følsomhed. Der fastslås ingen signaloprindelse, kvalificeret SETI-kandidat, generelt nulresultat eller uafhængighed mellem hypoteser, spor, udsnit eller scanninger.
Original kode/scope blev fastlåst ved `a8803167e7963a507454083bf116965253bfe83a` med scope-SHA256 `2e3b2401d1295f0864d2a2e3f8030b5860c7352a6881e25dce81ff11a3f11c23` før de nye kildeværdier. Dette skaber ikke en uafhængig besøgsobservation. Den senere gemte-JSON-opsummering er bundet til postprocesseringsscope `f065a101fd3ea59f041e5f9c923b8a28b0c1c9638d68c80d3a37dcb4ad242d69` ved `c8f222e3da85cfdc3519e67cf1b64d65775ab54f` og kvitterer for alle input- og outputhashes.

[Dækningsfigur](results/radio_native158_20261010/figures/STAGE_COVERAGE.png) · [Faste profilmidler](results/radio_native158_20261010/figures/STAGE_FIXED_PROFILE_MEANS.png)
