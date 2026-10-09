# SETI: kontrollernes udvalgte overskud ligner målretningens, 9. oktober 2026

To nye analysejob er færdige: en omvendt ON/OFF-søgning og tidsmåling af hele
den faste top20-liste i alle seks scanninger. **Kontrolretningerne giver også
udvalgte spektrale overskud på samme niveau som målretningerne. Blandt 60
ON-profiler har fire positive residualer i alle 16 integrationer; blandt 60
omvendt udvalgte OFF-profiler har fem det.** Dette svækker brugen af et højt
rangoverskud eller 16/16 positive rækker som selvstændigt argument for et særligt
målrettet signal. Ingen sandsynlighed eller oprindelse er bestemt.

De syv tidligere fremhævede svage ON-spor bevares som uafklarede. Det højeste
prioriterede spor ved **1424,079069888 MHz i ON2** har fortsat sit oprindelige
gennemsnitlige lokale overskud 0,139187; tilstødende OFF1/OFF2 har −0,001747 og
−0,016272 ved det samme faste kanalcentrum. Nye kontrolspor ved andre frekvenser
afviser ikke dette bestemte spor. Resultatet giver ingen uafhængig bekræftelse.

## Den nye kontrolsøgning

De oprindelige OFF-scanninger søges som pseudo-mål mod deres tilstødende ON:
OFF1 mod ON1/ON2, OFF2 mod ON2/ON3 og OFF3 mod ON3. De gemte oprindelige
ON-kontrastarrays læses uden genberegning. Bredder 1/3, ±32-kanalers kontrolvindue,
normalisering og den erklærede kanalrand er identiske med den tidligere
stationære sammenligning. Hver scanning omfatter 1.048.010 bærefrekvenser og
2.971.635,937573 Hz af det allerede åbnede bånd. Dette er ekstra kontrolanalyse,
ikke ekstra ON-eksponering eller ny uafhængig frekvensdækning.

Maksimum er forskellen mellem spektralt overskud i den valgte scanning og det
største nabooverskud i dens kontroller ved samme bredde. Det er relative
kontrastenheder, **ikke SNR, fysisk flux eller en sandsynlighed**. Tabellen
grupperer samme antal kontrolscanninger; rand- og indrescanninger blandes ikke.

| Antal nabokontroller | Oprindeligt ON-maksimum | Omvendt OFF-maksimum |
| ---: | --- | --- |
| 1 | ON1: 0,076445 | OFF3: 0,091962 |
| 2 | ON2: 0,068633; ON3: 0,077390 | OFF1: 0,079481; OFF2: 0,075469 |

Ved ON2-rang-1-sporets kontrastgrænse 0,068633 findes fire carrier-kanaler i
OFF1 og én i OFF2 med mindst samme omvendte kontrast. Det er **fem korrelerede
kanalsvar**, ikke fem uafhængige hændelser eller en falskalarmrate. Samtlige
signerede arrays for de tre nye kontrolløb og top20 pr. OFF er bevaret.

## Hele den faste tidsliste

Alle top20-centre pr. ON og top20 pr. omvendt OFF medtages: præcis 120 profiler.
Syv eksisterende ON- og ni netop gemte OFF-tidsprofiler genbruges ved eksakte
identiteter og uændrede værdier. De resterende **104 profiler** er målt én gang
ved det frosne centrum og den valgte bredde i alle seks scanninger. De nye
udsnit bevarer **1.287.936 rå effektværdier**. Kendte kontrollinjer er medtaget;
ingen profil er fjernet efter amplitude eller forklaring.

For hver integration er residualen gennemsnitlig effekt i centrum efter valgt
bredde minus medianen af flanker ±4…±64 kanaler, begge divideret med den gemte
rækkemedian for hele frekvensstykket. Alle 16 rækker bevares. Valgt bredde er 1
for 58/60 ON og 59/60 OFF; de øvrige bruger bredde 3. Ingen tidsperiode,
drifthastighed eller frekvens blev optimeret i denne måling.

| Nabokontroller | Profiler pr. side | Mindst 13/16 positive, ON / OFF | Mindst 15/16, ON / OFF | 16/16, ON / OFF |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 20 / 20 | 18 / 15 | 2 / 5 | 0 / 0 |
| 2 | 40 / 40 | 36 / 31 | 15 / 11 | 4 / 5 |
| I alt, beskrivende | 60 / 60 | 54 / 46 | 17 / 16 | 4 / 5 |

Tre af de fire 16/16-ON-profiler har store lokale gennemsnitsoverskud i alle
seks scanninger: to centre ved 1424,43918 MHz og ON2 rang 19 ved
1423,954560097 MHz. Sidstnævnte giver ON2 1,226141 mod OFF1 1,176321 og OFF2
1,160162, og er således også tydeligt til stede i kontrolretningerne. Dets
fysiske oprindelse klassificeres ikke. Det er et nyt katalogmål fra de gemte
data, ingen ny observation eller selvstændig SETI-detektion.

OFF-profiler med 16/16 positive rækker ligger ved 1422,596234869,
1424,439181658, 1422,573051793, 1422,185540554 og 1422,238314943 MHz.
De to første er tidligere kendte kontrollinjer, som bevares i panelet. De fem
kan derfor ikke fortolkes som fem støjrealisationer. De viser, at tidslig
vedvarenhed også forekommer blandt dataudvalgte kontrolspor.

## Konklusion og næste bevistrin

Det tidligere fremhævede 16/16-mønster er ikke enestående for de udvalgte
målprofiler. Ved sammenligning med samme antal nabokontroller er deres største
kontraster heller ikke særlige for målretningen. Disse kontrolmålinger giver
mod-evidens til en fortolkning baseret alene på udvalgt rang eller positive
rækker; de beviser hverken støj, interferens eller udenjordisk oprindelse for
de syv svage spor.

Et næste bevistrin for 1424,079069888-MHz-sporet skal være en faktisk uafhængig
observation med passende kontroller eller en særskilt valideret model for hele
udvælgelsesfamilien og dens afhængigheder. Denne native sammenligning er
**beskrivende**, ikke en sådan kalibrering: OFF er ikke certificeret støjfri,
scanningerne antages ikke udvekslelige, og både kanaler, bredder, rækker og
rangcentre er korrelerede. Et binomialt argument ud fra 16/16 anvendes ikke.

Alle seks scanninger er stadig ét historisk besøg fra 17. marts 2016. Gamle
kandidater, stopstatusser og beskyttede holdouts bevares. **A/B forbliver
FAIL_CLOSED, og den oprindelige kvalificerede pilot er fortsat blokeret.**
Ingen ny kandidat promoveres, og der drages ingen generel sky-nulkonklusion.

## Ressourcer, kontrol og evidens

De to nye analyseprocesser brugte henholdsvis 10,556546 og 3,074007 CPU-s:
**13,630552 målte process-CPU-s**, inklusive imports. Vægtid var 10,517814 og
3,034395 s; maksimal målt RSS var 416.714.752 og 160.665.600 bytes. Forberedelse,
gennemgang, overførsel og publicering er ikke samlet CPU-målt, så dette er ikke
hele aktivitetens forbrug. Begge job bestod deres frosne CPU-/tid-/RAM-grænser.

Aktiviteterne har i alt **300 CPU-s nye konservative reservationer**, inklusive
forberedelsesfejl og afslutning. De blev omfordelt prospektivt fra den internt
fastlagte afslutningsreserve under brugerens prioritet til signalanalyse;
den godkendte total på 12 CPU-timer øges ikke. Gamle reservationer refunderes
ikke. Saldo er **1.702,705145 CPU-s**, heraf **1.700 beskyttet til afslutningen**.
Der blev hentet 0 nye teleskopbytes og foretaget 0 nye teleskopforespørgsler.
Eksisterende arkiver på 592.148.151 bytes blev materialiseret. Pris: 0 kr.

Begge regler og kodeversioner er publiceret og læst tilbage før deres nye
udfald: [første frysning](https://github.com/andersenmartin-blip/setisearch/commit/2cacae559ac1e068a2356410f958c4f6314b5a5b)
og [hele tidslistens frysning](https://github.com/andersenmartin-blip/setisearch/commit/b2a7534dbba8accbc7987997c9c4452a43973b41).
19 og 11 inputpins blev kontrolleret før beregning. Alle 120 identiteter, seks
scanninger og komplette finite 16-række-output er kontrolleret; de 16 genbrugte
profiler er bevaret eksakt. Dette er integritetskontrol, ingen ekstra
kvalifikationsbank eller genkørsel af gamle detektorscores.

Resultater: [omvendt kontrol](results/radio_native_controls_20261009/outputs/NATIVE_CONTROL_RESULT.json),
[alle 120 tidsprofiler](results/radio_native_controls_20261009/ranked_time_panel/ALL_120_TIME_PROFILES.json),
[samlede tidstal](results/radio_native_controls_20261009/ranked_time_panel/RANKED_TIME_PANEL_RESULT.json),
[første kvittering](results/radio_native_controls_20261009/outputs/ANALYSIS_RECEIPT.json),
[anden kvittering](results/radio_native_controls_20261009/ranked_time_panel/ANALYSIS_RECEIPT.json),
[aktuel ledger](results/radio_native_controls_20261009/RESOURCE_LEDGER.json)
og [arkividentitet for arrays og figurer](results/radio_native_controls_20261009/EXTERNAL_DATA_ARCHIVE.json).

Kode og tekstlige kvitteringer ligger på analysegrenen. Arrays og figurer ligger
i det separate resultatarkiv; dets ejertilgængelige identitet gør dem ikke til
anonymt downloadbare Git-filer eller en fuld offline-reproduktion af de tidligere
rå teleskopreads. Originale kildearkiver og tidligere resultater er uændrede.
