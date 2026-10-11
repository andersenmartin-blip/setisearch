# S2017 råeffekt-injektioner — resultat 11. oktober 2026

Den prospektivt fastlåste benchmark er afsluttet én gang på seks autentiske,
allerede bevarede S2017-scanninger fra besøget 28. april 2017. Den omfatter
**450 gemte søgekort**: 18 uændrede baselinekort og 432 kort med digitale
råeffekt-injektioner. Alle **540 fastlagte diagnostiske cases** og alle 30
amplitude-/bredde-/kernegrupper er bevaret. En separat saved-output-QA består
alle deklarerede kontroller uden detektor- eller søgegenkørsel.

Dette er en betinget engineering- og recoverymåling i ét historisk besøg. Det
er ikke ny himmeldækning, en uafhængig observation, en ON-only-kildeprøve, en
OFF-vetotest eller en kalibreret falskalarm-/følsomhedsmåling. Oprindelig A/B
forbliver `FAIL_CLOSED`; der er ingen kvalificeret SETI-detektion.

## Hovedresultat

Hver celle nedenfor har 18 faste cases: seks scanroller og tre indsprøjtede
driftindeks. `Lokal` kræver positivt boks-overlap i alle 16 tidsrækker og gemt
score mindst 10 i et ±5-kanalers vindue ved kendt injektionsplacering. `Global
rang 1` kræver samme støtte for hele kernens vindende kandidat. Tællingerne er
afhængige, deterministiske cases — ikke binomialforsøg.

| Kontekst | Indsat bredde | A=1 lokal | A=3 lokal | A=6 lokal | A=12 lokal | A=1 global rang 1 | A=3 global rang 1 | A=6 global rang 1 | A=12 global rang 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| q64, fast sidekerne | 1 | 0/18 | 18/18 | 18/18 | 18/18 | 0/18 | 18/18 | 18/18 | 18/18 |
| q192, fast sidekerne | 1 | 0/18 | 18/18 | 18/18 | 18/18 | 0/18 | 18/18 | 18/18 | 18/18 |
| q128, kendt konkurrent | 1 | 0/18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 0/18 |
| q64, fast sidekerne | 9 mismatchstress | 0/18 | 18/18 | 18/18 | 18/18 | 0/18 | 18/18 | 18/18 | 18/18 |
| q192, fast sidekerne | 9 mismatchstress | 0/18 | 18/18 | 18/18 | 18/18 | 0/18 | 18/18 | 18/18 | 18/18 |
| q128, kendt konkurrent | 9 mismatchstress | 0/18 | 18/18 | 18/18 | 18/18 | 0/18 | 0/18 | 0/18 | 0/18 |

Ved bredde 1 er A=1 altså under den operationelle scoregrænse i alle 54
cases; A≥3 passerer lokalt i alle 54. I de to sidekerner bliver A≥3 også den
globale rang-1-vinder i alle 36 cases pr. amplitude. I q128 bevarer den kendte
stærke konkurrent global rang 1 i alle 18 cases ved hver amplitude op til A=12,
selv om den indsprøjtede linje findes lokalt. Et globalt top-1-output er derfor
ikke det samme som lokal recovery.

Bredde 9 er med vilje uden for søgefamiliens bredder 1/3. Det tilføjer ni gange
råeffekten ved samme A og har boks-overlap/scorestøtte fra A=3, men kan ikke
opfylde eksakt-bredde-kriteriet og må ikke rapporteres som kvalificeret
recovery. A=0 er de 18 delte baselinekort; alle rapporterede støtte+10-tællinger
er 0/18.

## Uafhængig kontrol

Den uafhængige QA verificerede:

- 450 kort, 432 modificerede cases og 540 diagnostiske poster;
- 1.843.200 carrier-maksima og 1.843.200 rangpositioner;
- 2.893.824.000 deklarerede gyldige hypotese-records;
- 540 rå sandhedsaudits med 4.363.200 rå vinduesceller;
- 1.080 uafhængigt beregnede sandhedsscores og 5.400 tuple-scorekontroller;
- 96 afkodede kilderækker og 7.200 kernemedianer.

Største absolutte afvigelse i den uafhængige rå-rækkesumsaritmetik var
`2.6929569685307797e-12`, under de fastlagte tolerancer. QA importerede ikke
detektoren og genkørte ikke søgningen.

## Ressourcer og afgrænsning

| Proces | CPU-s | Wall-s | Peak RSS |
|---|---:|---:|---:|
| Offcenter q64/q192, 300 kort | 537.024484065 | 537.117399584 | 172,695,552 bytes |
| Kendt konkurrent q128, 150 kort | 271.881173805 | 271.915273317 | 165,044,224 bytes |
| Uafhængig saved-output-QA | 5.379952227 | 5.329344679 | 482,721,792 bytes |
| All-group-sammenfatning | 0.231509657 | 0.231971622 | 70,668,288 bytes |
| Statisk figur | 0.695181851 | 0.698155473 | 91,267,072 bytes |

De fem målte komponenter summerer til **815.212301605 CPU-s**. Der blev ikke
foretaget nye HTTP-requests eller hentet nye teleskopbytes; pris er 0 DKK.
Kilde-HDF5 blev kun læst af de to prospektive benchmarkjob. Efterfølgende QA,
sammenfatning og figur læste gemte resultater; figuren læste kun QA-godkendt
JSON.

## Fortolkning

Benchmarket viser to forskellige begrænsninger. For bredde 1 ligger den faste
operationelle overgang i dette grid mellem A=1 og A=3. Separat viser q128, at
en stærk eksisterende linje kan blokere global top-1-promovering, selv når det
indsprøjtede spor lokalt passerer score- og støttekravet. Resultatet kalibrerer
ikke en astronomisk detektionssandsynlighed: baggrundene er 18 faste
scan/kerne-kombinationer, alle seks roller modtager syntetiske spor, og
amplituderne er i lokale baseline-MAD-enheder pr. celle, ikke flux eller SNR.

Den næste videnskabelige beslutning må derfor ikke tælle top-1-fravær som
manglende lokal signalrespons eller bredde-9-støtte som eksakt recovery. En ny
himmelkonklusion kræver fortsat uafhængige observationer og kontroller.

