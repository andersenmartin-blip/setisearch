# SETI: fast driftsøgning i native udsnit 153 og 154

**10. oktober 2026.** Alle fire oprindelige familier af gemte søgeoutputs er verificeret ved særskilt kontrol. Én numerisk kørsel sluttede COMPLETE; tre sluttede med en CPU-grænsefejl efter lagring af alle felter og profiler. Deres oprindelige fejlstatus og overskridelser er bevaret.
Der er gemt **1.524 af 1.524 ON-scanningsfelter** og **36 af 36 faste top-3-profiler**. Ranglisterne er separate for hvert udsnit, hver gruppe og hver ON-scanning; profilidentiteten er (native udsnit, gruppe, track-ID).

Alle seks scanninger stammer fra ét besøg den 17. marts 2016. Udsnit og fire referencekanallister blev fastlagt før modtagelsen af de nye kildeværdier. Dette er eksplorativ analyse, ikke uafhængig eller blind validering. A/B er fortsat FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og gamle holdouts er lukkede.

De fire første kodeinvokationer stoppede før indlæsning af signalarrays på grund af en relativ filsti. Fejlfilerne og deres 1,029956 CPU-sekunder er bevaret. En særskilt offentlig fastlåsning ved `8f88b722c9508d4e209c3df540407029b80c3203` tillod korrigerede absolutte CLI-stier med uændret kode, grid og kanalvalg. Hver gruppe har derfor to kodeinvokationer, men én faktisk arrayindlæsning, søgning og profilfamilie; der er ingen numerisk genkørsel.

## Dækning og kontrol

| Native udsnit | Gruppe | Gemte felter / 381 | Profiler / 9 | Oprindelig kørselsstatus | Senere outputverifikation |
| --- | --- | ---: | ---: | --- | --- |
| 153 | 1 | 381 | 9 | INCOMPLETE_RESOURCE_LIMIT_NO_RETRY | SAVED_OUTPUT_VERIFIED_ORIGINAL_RESOURCE_FAILURE |
| 153 | 2 | 381 | 9 | COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY | SAVED_OUTPUT_VERIFIED_ORIGINAL_COMPLETE |
| 154 | 1 | 381 | 9 | INCOMPLETE_RESOURCE_LIMIT_NO_RETRY | SAVED_OUTPUT_VERIFIED_ORIGINAL_RESOURCE_FAILURE |
| 154 | 2 | 381 | 9 | INCOMPLETE_RESOURCE_LIMIT_NO_RETRY | SAVED_OUTPUT_VERIFIED_ORIGINAL_RESOURCE_FAILURE |

| Native udsnit | ON | Gemte referencekanaler | Andel af dette udsnit |
| --- | --- | ---: | ---: |
| 153 | ON1 | 1.040.384 | 99,21875 % |
| 153 | ON2 | 1.040.384 | 99,21875 % |
| 153 | ON3 | 1.040.384 | 99,21875 % |
| 154 | ON1 | 1.040.384 | 99,21875 % |
| 154 | ON2 | 1.040.384 | 99,21875 % |
| 154 | ON3 | 1.040.384 | 99,21875 % |

**6.242.304 ON-referencekanal/originkombinationer** er evalueret med **1.526 gyldige grid-/breddehypoteser hver**, i alt **9.525.755.904 hypotesekombinationer**. For hver referencekanal gemmes scoremaksimum, vindende drift og bredde samt det verificerede hypoteseantal.
De fire verificerede checkpointfamilier dækker 254 af 256 referencefelter, **99,21875 % i hvert udsnit**, alene for 763 lineære drifthastigheder fra −4 til +4 Hz/s og bredde 1 og 3. Randfelterne [0,4096) og [1044480,1048576) er usøgte i hvert udsnit. Haloer overlapper; tællingerne er beregningsdækning og ikke uafhængige statistiske forsøg.

En særskilt, hashbundet kildecellekontrol matcher **445.824 råcelleforekomster i 36 profiludklip bit for bit** mod de 12 kompakte kildefiler. Den omfatter 192 afkodede kilderækker, 216 scanningsprofiler og 3.456 profilrækkeforekomster. De oprindelige større HDF5-kilders fulde MD5 er fortsat ikke verificeret.

## De gemte faste profiler

Profilerne er udvalgt efter detektorens ON-rangscore inden for deres egne grupper. De er gentagne, muligvis nærliggende og afhængige beskrivelser; antallet af udvalgte spor er ikke antallet af uafhængige fysiske signaler. Frekvensintervallerne nedenfor er kun de udvalgte referencefrekvensers min/max, ikke en målt strukturafgrænsning.

| Native udsnit | Gruppe | Udvalgte spor | Native q | Referencefrekvensinterval, MHz |
| --- | --- | ---: | --- | ---: |
| 153 | 1 | 9 | 56 | 1420,898426–1420,898449 |
| 153 | 2 | 9 | 134 | 1419,999988–1420,000011 |
| 154 | 1 | 9 | 53 | 1417,968739–1417,968761 |
| 154 | 2 | 9 | 148, 164, 165, 174, 219, 241 | 1415,777428–1416,861276 |

De første tre grupper samler deres ni udvalgte spor omkring hver sin smalle referencefrekvensregion: **1420,898438 MHz** (153/1), **1420,000000 MHz** (153/2) og **1417,968750 MHz** (154/1). I hver af disse grupper har alle tre ON-scanninger samme højst rangerede stationære spor med bredde én. Det samme fysiske referencespor har positive middelresidualer i alle seks ON/OFF-scanninger: henholdsvis **5,043613–5,294804**, **1,029598–1,158125** og **6,531580–6,800076**. Små residualer på de nærliggende udvalgte bevægelige OFF-spor kan derfor sameksistere med en tydelig stationær struktur i de samme OFF-scanninger; de dokumenterer ikke fravær af OFF-struktur.

Gruppen 154/2 har et andet udvalgt mønster: dens tre rang-1-spor ligger omkring **1416,661328 MHz** med små drifthastigheder, mens de seks rang-2/3-spor er mere spredt i referencefrekvens. De gemte middelresidualer og OFF-kontekster fremgår nedenfor. Disse efter-udvælgelsesbeskrivelser fastslår hverken uafhængige fund, statistisk signifikans eller en signaloprindelse.

Tallene er gemt normaliseret centereffekt minus rækkens median af bevægelige flankkanaler med absolut offset større end tre inden for ±64. De er ikke kalibreret SNR. Detektorens robuste rangscore og profilens middelresidual er forskellige størrelser. OFF-værdierne følger den valgte, uændrede drift ved de faktiske scanningstider. ON2/ON3 har både forudgående og efterfølgende OFF; ON1 har kun efterfølgende OFF i denne sekvens. Alle seks scanningers faste forløb bevares i sammenfatningen.

| Native udsnit | Gruppe | ON/rang | Frekvens, MHz | Drift, Hz/s | Bredde | ON-middel | OFF før | OFF efter |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 153 | 1 | ON1/1 | 1420,898438 | 0,000000 | 1 | 5,054320 | — | 5,191658 |
| 153 | 1 | ON1/2 | 1420,898449 | -0,052493 | 3 | 0,876525 | — | -0,023682 |
| 153 | 1 | ON1/3 | 1420,898426 | 0,052493 | 3 | 0,836987 | — | -0,010558 |
| 153 | 1 | ON2/1 | 1420,898438 | 0,000000 | 1 | 5,106650 | 5,191658 | 5,102541 |
| 153 | 1 | ON2/2 | 1420,898449 | -0,052493 | 3 | 0,860034 | -0,000637 | 0,001670 |
| 153 | 1 | ON2/3 | 1420,898426 | 0,052493 | 3 | 0,845383 | -0,016538 | 0,021732 |
| 153 | 1 | ON3/1 | 1420,898438 | 0,000000 | 1 | 5,043613 | 5,102541 | 5,294804 |
| 153 | 1 | ON3/2 | 1420,898426 | 0,052493 | 3 | 0,849207 | 0,010210 | 0,007739 |
| 153 | 1 | ON3/3 | 1420,898449 | -0,052493 | 3 | 0,819525 | 0,020128 | 0,019469 |
| 153 | 2 | ON1/1 | 1420,000000 | 0,000000 | 1 | 1,158125 | — | 1,041411 |
| 153 | 2 | ON1/2 | 1420,000011 | -0,052493 | 3 | 0,201133 | — | -0,023477 |
| 153 | 2 | ON1/3 | 1419,999988 | 0,052493 | 3 | 0,156175 | — | 0,008338 |
| 153 | 2 | ON2/1 | 1420,000000 | 0,000000 | 1 | 1,029598 | 1,041411 | 1,139157 |
| 153 | 2 | ON2/2 | 1420,000011 | -0,052493 | 3 | 0,183450 | 0,001511 | -0,009545 |
| 153 | 2 | ON2/3 | 1419,999988 | 0,052493 | 3 | 0,176213 | -0,023461 | 0,008189 |
| 153 | 2 | ON3/1 | 1420,000000 | 0,000000 | 1 | 1,033093 | 1,139157 | 1,058596 |
| 153 | 2 | ON3/2 | 1419,999988 | 0,052493 | 3 | 0,178358 | 0,017717 | 0,016361 |
| 153 | 2 | ON3/3 | 1420,000011 | -0,052493 | 3 | 0,170186 | 0,030734 | 0,011201 |
| 154 | 1 | ON1/1 | 1417,968750 | 0,000000 | 1 | 6,587733 | — | 6,649291 |
| 154 | 1 | ON1/2 | 1417,968761 | -0,052493 | 3 | 1,073347 | — | -0,001121 |
| 154 | 1 | ON1/3 | 1417,968739 | 0,052493 | 3 | 1,074188 | — | 0,026139 |
| 154 | 1 | ON2/1 | 1417,968750 | 0,000000 | 1 | 6,697052 | 6,649291 | 6,800076 |
| 154 | 1 | ON2/2 | 1417,968761 | -0,052493 | 3 | 1,143911 | -0,022545 | -0,020810 |
| 154 | 1 | ON2/3 | 1417,968739 | 0,052493 | 3 | 1,128154 | -0,000382 | -0,006556 |
| 154 | 1 | ON3/1 | 1417,968750 | 0,000000 | 1 | 6,531580 | 6,800076 | 6,567691 |
| 154 | 1 | ON3/2 | 1417,968739 | 0,052493 | 3 | 1,092981 | -0,005278 | 0,002171 |
| 154 | 1 | ON3/3 | 1417,968761 | -0,052493 | 3 | 1,087612 | -0,003762 | 0,007190 |
| 154 | 2 | ON1/1 | 1416,661328 | 0,020997 | 3 | 0,081658 | — | 0,034920 |
| 154 | 2 | ON1/2 | 1416,564297 | 1,228346 | 3 | 0,058895 | — | 0,011425 |
| 154 | 2 | ON1/3 | 1416,038614 | 3,863517 | 1 | 0,163395 | — | 0,022372 |
| 154 | 2 | ON2/1 | 1416,661331 | -0,041995 | 3 | 0,090574 | 0,033992 | 0,007660 |
| 154 | 2 | ON2/2 | 1416,861276 | -3,853018 | 1 | 0,171851 | -0,008201 | 0,007978 |
| 154 | 2 | ON2/3 | 1415,777428 | 3,212598 | 3 | 0,106279 | -0,007611 | 0,010827 |
| 154 | 2 | ON3/1 | 1416,661328 | -0,020997 | 3 | 0,089582 | 0,036915 | 0,023756 |
| 154 | 2 | ON3/2 | 1415,785044 | 1,217848 | 1 | 0,172204 | -0,006826 | 0,012322 |
| 154 | 2 | ON3/3 | 1416,678190 | 0,524934 | 3 | 0,077704 | -0,003252 | -0,002113 |

Profilerne forbliver uafklarede. Positive rækker og halvdele er målt efter udvælgelse. En lille middelresidual på et præcist OFF-spor fastslår ikke fravær af nærliggende OFF-struktur. Ingen OFF-forskydning er optimeret; ingen kvalificeret OFF-veto, oprindelsesbestemmelse eller SETI-kandidat er fastslået.

## Målt kørsel

| Native udsnit | Gruppe | CPU, sekunder | Vægtid, sekunder | Maksimal RSS, bytes |
| --- | --- | ---: | ---: | ---: |
| 153 | 1 | 1555,066 | 1558,420 | 635416576 |
| 153 | 2 | 1471,779 | 1474,965 | 635830272 |
| 154 | 1 | 1553,235 | 1556,166 | 633012224 |
| 154 | 2 | 1649,797 | 1652,658 | 634155008 |

Den oprindelige numeriske grænse var 1500 CPU-sekunder, 1.800 sekunders vægtid og 4 GiB RAM. Tre oprindelige kørsler overskred CPU-grænsen ved afslutningskontrollen; grænsen eller fejlkvitteringerne er ikke ændret. En senere fastlåst kontrol af gemte outputs genkører ingen søgning, score, rangliste eller profil og omklassificerer ikke de numeriske kørsler til COMPLETE. Fasens 7200 CPU-sekunder er arbejdsplanlægning, ikke en abonnementsbalance eller global stopgrænse. Analyserne bruger 0 nye teleskoprequests/bytes; datamodtagelsens særskilte byte- og ressourcekvitteringer skal læses separat. Projektet fortsætter uden betalte ressourcer.

## Begrænsninger og reproduktion

Den særskilte gemte-outputkontrol blev fastlåst ved `50c120ba94e0a24c9473afc883ef24f7dd1846f5` med scope-SHA256 `8f744e099b0b31b9c976255c5c321b2ce49243ec56f60460048b966885f2cf37`. Verificeret betyder her, at de gemte outputs består de fastlagte integritets- og kildekontroller; det er ikke en kvalificeret SETI-kandidat eller en godkendelse af de oprindelige ressourcegrænser.
Der er ikke beregnet kalibreret SNR, falskalarmrate, flux, EIRP eller følsomhed. Der påstås intet generelt nulresultat eller uafhængighed mellem hypoteser, profiler, udsnit eller scanninger. Ingen barycentrisk korrektion, ikke-lineære spor, andre bredder eller injektionskalibrering er tilføjet. De beskyttede gamle native udsnit 156 og 159 er lukkede.
Fælles scope og kode blev fastlåst offentligt ved `d1bfe755e205e99b3c93544f4af84cc8d4585938` før de nye kildeværdier. Scope-SHA256: `60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4`. Den prospektive fastlåsning gør ikke denne ene historiske sekvens til en uafhængig besøgsobservation. Kildekompakters lokale hashes og afkodede rækkehashes erstatter ikke originalfilernes fulde MD5.
Sammenfatningen åbner kun eksplicit hashpinnede JSON-filer efter særskilt GO. Den genkører ikke detektoren og åbner hverken HDF5 eller NPZ. Inputhashes, outputhashes og ressourceforbrug findes i sammenfatningskvitteringen.

[Dækningsfigur](results/radio_next_bands_20261010/figures/NEXT_BANDS_COVERAGE.png) · [Faste profilmidler](results/radio_next_bands_20261010/figures/NEXT_BANDS_FIXED_PROFILE_MEANS.png)
