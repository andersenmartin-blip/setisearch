# BW — sidste udsnit med fuld datastøtte analyseret

31. oktober 2026. **q254 er gennemført i alle fem komplette scanninger: nul katalogrækker over ESS-tærsklen 10.** Højeste lokale ESS er 5,756009608887369. Den planlagte kørsel og uafhængige kontrol bestod og afsluttede naturligt med exitkode 0. Samlet køretid var 17,850877174001653 sekunder.

Dette er første detektorsøgning i q254 fra de allerede indlæste og normaliserede observationer af HIP44295 fra 29. september 2016. Der er ingen ny observation eller arkivhentning. Kontrolscanning 5 er fortsat ufuldstændig; en fuld ON/OFF-vurdering er derfor stadig `NOT_EVALUABLE_MISSING_OFF5`.

## Resultat og afgrænsning

| Scanning | Rolle | Kilde | Arkiv-ID | Katalogrækker | Højeste lokale ESS |
|---|---|---|---:|---:|---:|
| 0 | ON | HIP44295 | 65133 | 0 | 5,166922291 |
| 1 | OFF | HIP43151 | 65135 | 0 | 5,356640919 |
| 2 | ON | HIP44295 | 65137 | 0 | 5,413406895 |
| 3 | OFF | HIP43162 | 65139 | 0 | 5,646461341 |
| 4 | ON | HIP44295 | 65141 | 0 | 5,756009609 |

BW tilføjer 45.104.640 korrelerede sporkombinationer, heraf 27.062.784 i ON-scanninger, og 0,011444091796875 MHz i frekvenskanaler. ESS er en lokal median/MAD-baseret score; den angiver ikke antal sigma eller en kalibreret falsk-alarm-sandsynlighed. Kombinationerne er ikke uafhængige forsøg.

BU+BV+BW dækker nu q1–254: **2,90679931640625 MHz**, 1.270 scanning/udsnit-kombinationer og 11.456.578.560 korrelerede sporkombinationer. De yderste undersøgte bærekanalers centre ligger ved 2298,9372281357646 og 2301,844024658203 MHz. q0 og q255 er udeladt, fordi de ikke har fulde støtteområder på begge sider.

BW tilføjer ingen kandidatrækker og ændrer ikke BV-resultatet: 67 overlappende rækker, som passerede tre ON-scanninger, blev alle afvist af de tilgængelige OFF-scanninger. Den fælles struktur omkring 2300,390625 MHz er dokumenteret i BV. Ingen række passerer den definerede partielle tre-ON/tilgængelig-OFF-screening. Dette er ikke et fuldstændigt nulresultat for seks scanninger eller en astronomisk følsomhedsgrænse.

## Rettelse af den tidligere dækningsbeskrivelse

BV fastlagde og gennemførte præcis q33–253. Formuleringen om, at alle sikre udsnit dermed var dækket, var for bred: den oprindelige BN-validator tillod q254. BN's antal på 253 udsnit skyldtes, at q128 var udeladt; det var ikke en øvre grænse ved q253.

En gennemgang af metadata viste, at q254 har bæreinterval [1040384, 1044480) og fuldt støtteinterval [1036288, 1048576), med 4096 kanaler på hver side. Den konservative forskydningsgrænse inklusive associationsradius er 2218 kanaler. BW blev derfor fastlagt særskilt før scoring. De tidligere planer, resultater og fejlede forsøg er bevaret.

## Uafhængig kontrol

Plan, kildekode og gennemgang blev offentliggjort før scoring i commit [`63715dbedf50442e33423608422ca8764b27c147`](https://github.com/andersenmartin-blip/setisearch/commit/63715dbedf50442e33423608422ca8764b27c147); alle 17 offentliggjorte filer blev læst tilbage og sammenlignet nøjagtigt. Fire tests af afgrænsning, støttegeometri, uændrede numeriske funktioner og kaldemønster bestod.

Resultatkontrollen bestod med:

- 180 uafhængigt beregnede skalarsporsummer og 60 kalibreringsvektorer; observeret forskel 0 i de kontrollerede værdier.
- 20.480 normaliseringsankerpar kontrolleret og 983.040 værdier i støtteområdet rekonstrueret nøjagtigt.
- Alle 53.760 gemte maksimumscorer kontrolleret, alle kataloger tomme, og alle arkivmedlemmers indhold kontrolleret med størrelse, CRC og SHA256.
- Uændrede kilde- og inputidentiteter før og efter kørsel; begge underprocesser afsluttet med faktisk exitkode 0 og naturlig stdout-EOF.

Der var ingen kandidater at foretage tværgående tvungen genmåling på. Kontrollen er afgrænset og er ikke en anden komplet detektorsøgning.

## Næste observationsdata

Den eksisterende BE-genoptagelse er kortlagt i [`work_bw/recovery/README.md`](work_bw/recovery/README.md) og [`RESUME_SPEC_BW.json`](work_bw/recovery/RESUME_SPEC_BW.json). Den mangler præcis OFF5/HIP43223/65143 tidsrækker 8–15 og én fuld kontrolgenlæsning af række 7. Det første manglende metadataområde er byte 9241886720–9241903103; det er en TREE-node, ikke en kendt række-8-payload. Payload-positioner skal udledes af ægte metadata.

En genoptagelse kræver alle ni BB-pakker, BC-pakken, de fastlåste BE-kilder og runtime-afhængigheder samt de oprindelige beviskontroller. De fem lokale komplette arrays er ikke et tilstrækkeligt grundlag for fuld arkivgenoptagelse. Arkivværten er ikke tilgængelig under dette miljøs aktuelle netværksbegrænsninger. Der er foretaget nul arkivforespørgsler og ingen omgåelse.

En afgrænset gennemgang af alternative, oprindelige GitHub-datakilder fandt mindre ATA-kalibratordata og historiske Wow!-transskriptioner, men ingen verificeret komplet ny ON/OFF-serie til denne protokol. De er ikke hentet eller talt som nye søgedata; begrænsninger og identiteter er dokumenteret i [`DATA_SOURCE_SCOUT_BW.json`](work_bw/review/DATA_SOURCE_SCOUT_BW.json).

Næste nye mål i den eksisterende kø er fortsat HIP58684/65193 og HIP59280/65205. Den oprindelige BA-status er uændret: 486 unikke arkiv-ID'er, 268,50128173828125 tekniske MHz-besøg og nul kvalificeret astronomisk følsomhed. Køen er ikke rykket, og ingen beregningsjob kører videre i baggrunden.

Maskinlæsbare resultater: [`SUMMARY_BW.json`](work_bw/SUMMARY_BW.json), [`FINAL_CLOSURE_REVIEW_BW.json`](work_bw/review/FINAL_CLOSURE_REVIEW_BW.json), [`SUMMARY_BINDING_REVIEW_BW.json`](work_bw/review/SUMMARY_BINDING_REVIEW_BW.json).
