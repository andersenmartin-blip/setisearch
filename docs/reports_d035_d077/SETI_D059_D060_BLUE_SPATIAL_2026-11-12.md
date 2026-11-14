# SETI D059–D060: blå pixelprofil og følsomhed for udtræk

**12. november 2026.** Grundlag: projektversion **54**, SHA256 `2d3dc630633cafc3f08c14e9574ba54b33972446999f132d6aea160faa01ebba`. HD 43629, D002-0063, **4826.6475 Å** i barycentrisk luft. Original 9. marts 2021; faste kontroller 3., 4., 5. og 6. marts 2021. Observationstider og metodekvitteringer er UTC.

## Hvad analysen viser

Det blå udsving følger ikke hele den normale rumlige stjerneprofil i de undersøgte modeller. Originalens centrale pixelrække har en rest-RMS på **182.82–188.52 ADU**, svarende til **19.41–20.89 gange** den tilhørende models median blandt tilbageholdte referencer. I alle otte fastlagte profilvarianter ligger centralrækken over den største observerede referencerække i dens egen fold. Kontrollernes centrale rækker ligger nærmere deres egne referencemedianer.

Samtidig består originalens større lokale spektrale overskud, når udtrækket varieres mellem **fire faste aperturer og otte egne profilamplituder**. Original minus kontrol er positiv i alle **1,152 deklarerede sammenligninger**: 864 mod de tre kontroller med matchende headerfelter og 288 mod den særskilte sekundære kontrol fra 6. marts. Sammenligningerne genbruger de samme pixels; de er ikke 1,152 uafhængige hændelser.

Profilafvigelsen er et beskrivende modelresultat. Forholdet 19–21 er **ikke en sigma-værdi, en p-værdi eller en kalibreret falsk-alarm-sandsynlighed**. De egne stjerneprofiler er heller ikke validerede lasersvarfunktioner. Vi tildeler fortsat ingen bestemt partikel-, pixel-, instrument- eller astronomisk årsag. **Alle tre fysiske oprindelser er uafklarede; 0 kvalificerede lasersignaler.**

## Data og fastlåsning

Kun de allerede gemte D058-arrays er anvendt: fem observationers egne baggrundssubtraherede CCD1-counts, trace-offsets og native-indekser **2446–2702** i egen orden **34**. De fire egne koordinatvisninger er uændrede fra D057/D058: detektor k2574 samt barycentrisk luft NEAREST/FLOOR/CEIL. Der er ingen ny FITS-dekodning, teleskopforespørgsel, kontrolobservation, Monte Carlo-kørsel eller spektral resampling.

D059's metode og auditkode blev låst før de nye blå profiler. D060 blev særskilt låst efter, at D059's profilafvigelse var kendt, men før de nye udtrækskontraster blev beregnet. Originalhændelsen, D058's råkurver og den sekundære kontrols afvigelse var allerede kendte. Begge analyser er målrettede videreundersøgelser af udvalgte data.

Algoritmerne for splineknuder og Cox–de Boor-basis er AST-kontrolleret identiske med D056's tidligere numeriske implementering. **Kun algoritmen genbruges.** Profilerne trænes separat på hver observations egne blå pixels; ingen rød CCD2-profil eller COMB-respons overføres.

## D059: egne profiler med tilbageholdte rækker

For hver observation opdeles native-indekserne efter lige/ulige paritet. Træningen bruger kun **abs(k−2574)>20** og positiv signeret radius-6-sum, mindst 64 rækker. Her har hver fold 108 træningsrækker. Den centrale zone på 41 samples er helt ude af træningen.

Den kubiske spline tilpasses direkte til de normaliserede native-pixelcounts ved deres faktiske egne rumlige offset inden for ±8 pixels. Observationspixels interpoleres ikke. Begge faste knudegitter har klampede grænser −8/+8 og én pixels afstand: indre heltalsknuder −7…7 eller halvheltalsknuder −7.5…7.5. Fit er uvægtet least squares uden regularisering, positivklipning, fri traceforskydning eller breddejustering.

Hver profil normaliseres med sin diskrete sum inden for radius 6. På hver række fit'es enten signeret traceamplitude alene eller traceamplitude plus konstant og rumlig hældning. Der kræves fuld rang og conditiontal under 1e8. Alle 20 profiler og 40 rumlige modeller er numerisk understøttede; **10,280 rækkefit** er gemt.

Alle rækker af modsat paritet uden for kernen bruges til validering, også eventuelle ikke-positive radius-6-rækker og store afvigelser. De 1,080 forskellige referencerækker på tværs af fem observationer er hver tilbageholdt én gang pr. knudegitter. De to gitter genbruger rækkerne og giver tilsammen 2,160 valideringsrækkepladser, ikke flere observationer. Ingen træningsrestfejl bruges som valideringsresultat.

De primære NEAREST-resultater over alle otte modeller er:

| Observation | Central rest-RMS, ADU | Central/egen referencemedian | Over egen største referencerække |
| --- | ---: | ---: | ---: |
| ORIGINAL | 182.817064–188.518609 | 19.412483–20.885809 | 8/8 |
| CONTROL3MAR | 7.814867–8.132917 | 0.963164–1.002585 | 0/8 |
| CONTROL4MAR | 9.249262–10.074479 | 1.100435–1.297178 | 0/8 |
| CONTROL5MAR | 8.372433–9.161832 | 0.891096–0.986161 | 0/8 |
| CONTROL6MAR | 9.983596–13.499955 | 0.952966–1.329616 | 0/8 |

Originalens otte udfald:

| Knudegitter / træningsparitet / model | Central RMS, ADU | Referencemedian, ADU | Største referencerække, ADU | Central/median |
| --- | ---: | ---: | ---: | ---: |
| INTEGER / 0 / TRACE_ONLY | 188.198676 | 9.283521 | 16.573932 | 20.272338 |
| INTEGER / 0 / TRACE_PLUS_AFFINE | 184.991735 | 8.857293 | 16.191324 | 20.885809 |
| INTEGER / 1 / TRACE_ONLY | 185.974868 | 9.540000 | 19.729571 | 19.494222 |
| INTEGER / 1 / TRACE_PLUS_AFFINE | 182.817064 | 9.288488 | 19.666797 | 19.682111 |
| HALF / 0 / TRACE_ONLY | 188.518609 | 9.292856 | 14.991587 | 20.286401 |
| HALF / 0 / TRACE_PLUS_AFFINE | 185.369477 | 9.039974 | 14.796010 | 20.505531 |
| HALF / 1 / TRACE_ONLY | 187.532526 | 9.660409 | 18.239011 | 19.412483 |
| HALF / 1 / TRACE_PLUS_AFFINE | 184.399770 | 9.046836 | 18.188454 | 20.382791 |

RMS er kvadratroden af gennemsnitlig kvadreret restfejl over de rumlige pixels inden for ±8. Modelafvigelse, counts, pixelplacering og støj indgår i dette mål. Det er ikke et fysisk støjparameterestimat. Alle fire koordinatvisninger og de tre centrale rækker anker−1, anker, anker+1 er bevaret i **CORE_VALIDATION160**.

Den sekundære kontrol fra 6. marts har store valideringsafvigelser uden for kernen. Alle maksimumværdier og pixels er beholdt. Dens egen centrale række er mindre afvigende, men det gør ikke hele observationen til en ren nulprøve eller ophæver dens selectorafvigelse og rå/native-Pearson på **0.5328736440484954**.

## D060: alle tolv udtræk

De fire aperturer er signerede summer inden for radius **3, 5, 6 og 7**. De otte øvrige kurver er den allerede gemte første koefficient fra hver D059-model: to gitter × to træningspariteter × to rumlige baggrundsvalg. D060 laver ingen nye rumlige fit og flytter ingen profil.

Hver kurve divideres med sin egen faste median uden for den centrale 41-samplezone. Alle 60 kurver er finite med positiv median. De oprindelige D058-regler for lokal råintensitet og geometri videreføres. Forhold mellem nye udtræksmedianer registreres beskrivende og bruges ikke som en ny efterfølgende udvælgelsesregel.

De seks spektrale baggrunde er uændrede: affine/kvadratiske fit på ±5–7, ±8–12 og ±12–20 native-samples. Signerede 3-, 5- og 15-samplesummer, negative udfald, alle dubletankre og alle baggrunde er bevaret. Den primære størrelse er fortsat den normaliserede signerede 3-samplesum.

Der er **1,440 cases**, **720 forskellige native-fit**, **1,152 parslots** og **864 forskellige native-par**. Alle 1,152 source-minus-kontrol-3sumforskelle er positive. De større aperturer og profilmodeller giver forskellige kontraststørrelser; ingen af varianterne vælges som den foretrukne efter resultatet.

Primære NEAREST-forhold: normaliseret signeret kontrol/original-3sum over alle seks baggrunde. Sidste kolonne er sekundær.

| Udtræk | 3. marts | 4. marts | 5. marts | 6. marts, sekundær |
| --- | ---: | ---: | ---: | ---: |
| AP_R3 | -0.035175 til +0.103655 | +0.055180 til +0.197990 | +0.058602 til +0.147732 | +0.101470 til +0.163735 |
| AP_R5 | -0.037057 til +0.099753 | +0.057423 til +0.189150 | +0.055625 til +0.139520 | +0.098770 til +0.160850 |
| AP_R6 | -0.032720 til +0.067552 | +0.037205 til +0.140710 | +0.039797 til +0.100247 | +0.064843 til +0.107115 |
| AP_R7 | -0.027683 til +0.044914 | +0.028735 til +0.100110 | +0.026015 til +0.066008 | +0.042202 til +0.075760 |
| INTEGER__TRAIN_0__TRACE_ONLY | -0.037987 til +0.093935 | +0.050608 til +0.192439 | +0.042295 til +0.124949 | +0.086623 til +0.146609 |
| INTEGER__TRAIN_0__TRACE_PLUS_AFFINE | -0.087309 til +0.204029 | +0.104666 til +0.366212 | +0.079424 til +0.288577 | +0.164167 til +0.338782 |
| INTEGER__TRAIN_1__TRACE_ONLY | -0.038064 til +0.093291 | +0.050269 til +0.191495 | +0.042091 til +0.124435 | +0.085885 til +0.145639 |
| INTEGER__TRAIN_1__TRACE_PLUS_AFFINE | -0.087344 til +0.201412 | +0.103249 til +0.362918 | +0.078610 til +0.285673 | +0.162167 til +0.335080 |
| HALF__TRAIN_0__TRACE_ONLY | -0.038092 til +0.093895 | +0.050873 til +0.193017 | +0.042324 til +0.125179 | +0.086084 til +0.146106 |
| HALF__TRAIN_0__TRACE_PLUS_AFFINE | -0.087729 til +0.204355 | +0.105696 til +0.368125 | +0.079648 til +0.289501 | +0.162849 til +0.337530 |
| HALF__TRAIN_1__TRACE_ONLY | -0.038212 til +0.093253 | +0.050594 til +0.192283 | +0.042181 til +0.124356 | +0.084820 til +0.145033 |
| HALF__TRAIN_1__TRACE_PLUS_AFFINE | -0.087874 til +0.201553 | +0.104407 til +0.365500 | +0.079005 til +0.285420 | +0.159334 til +0.333136 |

Forholdene er hverken konfidensgrænser eller øvre grænser for en lasers lysstyrke. Hver aperture har sin egen median; normaliserede aperturer kan ikke lægges sammen som bidrag på én fælles skala. Alle 192 visningsgrupper og 1,152 par findes i de fulde tabeller.

## Uafhængig beregning og bevaring

**Begge audits: PASS.** D059 kontrollerer produktionens Cox–de Boor-basis med en separat SciPy B-spline-basis, inklusive endepunkter og nul uden for intervallet. 20 profilfit er kontrolleret med QR, og alle 10,280 rækkefit med separat QR/skalarprojektion. Største basisafvigelse er **2.22e-16**, største forudsagte pixelafvigelse **1.82e-12 ADU**, største RMS-afvigelse **4.55e-13 ADU**. Ingen kernerække indgår i profiltræningen.

D060 efterregner aperturer med skalarsummer, kontrollerer native-amplituder eksakt mod D059 og bruger separat QR til de spektrale baggrunde. **4,320 QR- og 4,320 lineære operatorkontroller** består. Største sumafvigelse er **2.09e-11 ADU** med QR og **1.91e-11 ADU** med operatorer; største forholdsafvigelse **2.05e-15**.

Radius 3 reproducerer **840 tidligere D058-caseskalartal** og **576 tidligere parskalartal eksakt**, inklusive alle oprindelige baggrunde og koordinatvalg. Alle frosne D058- og D059-outputhashes består. Den separate implementering er lavet af samme assistent; det er ikke en ekstern fagfællebedømmelse.

Alle **80,049 tidligere tabelceller** er bevaret eksakt. D059 og D060 tilføjer otte kolonner hver til de samme 37+141 rækker; nu **82,897 celler**. Den gamle røde D002-0061-fejl `rho=0.7806562435869904<0.8`, det blå COMB-responsgab og den sekundære status fra 6. marts består. D055/D056's septemberresultater og alle tidligere fysiske fortolkninger er uændrede.

## Figurer og reproduktion

Fire endelige figurer er visuelt kontrolleret: alle fem centrale pixelprofiler og deres residualer; alle otte modelvarianter mod samtlige egne referencemaksima; præcise native-residualpixelkort med fælles ADU-farveskala; samt alle 1,152 udtrækskontraster inklusive negative værdier og dubletvisninger.

Visningen af profiler og pixelkort bruger det på forhånd fastlagte **INTEGER / paritet 0 / TRACE_ONLY / NEAREST**. De øvrige varianter bevares fuldt i tabellerne og valideringsfiguren. Alle observationer vises. Pixelkort resamples ikke; grå celler ligger uden for modellens ±8-pixelstøtte. Residualkortene er modelafvigelser, ikke kort over bestemte fysiske energideponeringer.

Resultatpakken indeholder alle nye metoder, kode, arrays, profiler, operatorer, fulde tabeller, state-tabeller, audits og fire figurer. Den medtager også de uændrede D057/D058-inputfiler, der kræves for D059/D060-audits. Sammen med hovedprojektet kan de nye audits køres uden FITS-læsning eller teleskopadgang. Se REPRODUCTION og EVIDENCE_MANIFEST for de præcise input.

Hovedprojektet beholder alle tidligere videnskabelige filbytes og peger på de nye fulde data i resultatpakken. De tre tidligere aktive rodpegere er bevaret eksakt i **D059/FROZEN_PARENT i resultatpakken**. Ingen tidligere hovedarkivmedlemmer fjernes for at give plads. Den nye opdeling af filer ændrer ingen målinger.

## Næste afgrænsede opgave

D061 foreslås som et **fast rumligt bidragsregnskab**: hvor meget de på forhånd definerede pixelbånd bidrager til apertureafhængigheden, med positive og negative værdier bevaret. Det kan afklare, hvilke dele af den gemte pixelstruktur der driver kontrasterne, uden at indføre ny peakudvælgelse eller årsagsklassifikation. Metoden skal låses særskilt. **D061 er foreslået, ikke låst eller udført.**

Ingen kalibreret FAP, fysisk kovarians, laserrespons, stjerneramme eller persistensudelukkelse etableres her. Alle tre oprindelser er uafklarede; **0 kvalificerede lasersignaler**. Den gamle 141-kø er lukket, gamle 90-/Rubinspor stoppet og offentlig upload fortsat udskudt. Ingen udgifter, eksterne kontakter eller baggrundsberegninger.
