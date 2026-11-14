# SETI D069–D074: FEROS-hastighedskontekst og relativ mønsterregistrering

**13. november 2026. Aktuelt fagligt fortsættelsespunkt: D074.** HD43629/TIC34077285, de samme fem datoer i november 2019 og tre tidligere kendte positioner. D072–D074 er nye; de færdige D069–D071-resultater er bevaret uændret sammen med dem.

## Hvad vi har lært

Den samlede gennemgang af **2.565 gemte FITS-headers og 860 TAR-medlemsnavne** finder ingen RV-/CCF-felter eller tilsvarende filnavne i det undersøgte materiale. Der er derfor ingen herfra valideret, leveret måling af stjernens radialhastighed. Det er en afgrænset inventering af headers og navne; indholdet af øvrige ikke-FITS-tabeller er ikke gennemsøgt for skjulte målinger. Manglende stjernehastighed gemmes som manglende, aldrig som nul.

En særskilt låst kontrol kan nu tilpasse **relative lokale spektralmønstre** mellem alle ti datopar. Med begge sidebånd spænder forskydningerne over **−0,40 til +0,60 km/s**. Men ved 0061 kan blå og røde sidebånd på samme datopar give resultater, der afviger med **0,80 km/s**. Det er større end gridtrinnet og viser en konkret afhængighed af det valgte mønsterområde. Det dokumenterer ikke, hvilken fysisk årsag der skaber forskellen.

Der er derfor ikke grundlag for at kalde denne kontrol en sikker absolut stjernehastighed eller for at flytte alle kandidater ind i en valideret stjernerestframe. **Ingen kandidatsummer er blevet forskudt eller genklassificeret. 0 kvalificerede lasersignaler; alle tre tidligere fysiske oprindelser er fortsat uafklarede.**

## D072: hele den eksisterende metadatakontekst

Metode, parser og audit låses før den nye målrettede gennemgang. Der indgår de fem råfilheaders, de fem SDP-produkters HDUs og alle 2.550 pipeline-HDUs, i alt 2.565. Alle felter om radialhastighed/CCF, bølgelængderamme, observationstid og deklareret kalibreringsproveniens registreres med eksakte værdier, kommentarer og headerreferencer. Gentagne værdier samles uden at fjerne referencerne: 3.198 varianter og 500.595 matchende kortforekomster.

Inventeringen læser kun de allerede bevarede headers og medlemsnavne. Den læser ingen nye FITS-sciencearrays, rå CCD-pixels, kalibreringspixels eller anden fibers spektrum. De tidligere D071-koordinatbroer er fortsat produktkoordinater, ikke en ny fysisk kalibrering.

## D073: tid, observerkorrektion og kalibrering

Blandt de **200 primære headers** har kun de ti rå-/SDP-headers et fuldt klokkeslæt i DATE-OBS. De 190 pipelineheaders har kun dato. Deres MJD-OBS bevarer klokkeslættet; en dato alene fortolkes ikke som midnat. TIMESYS mangler i alle 200 primære headers. Under en udtrykkeligt betinget UTC-fortolkning stemmer de fulde ISO-tider med MJD inden for **0.0011114 s**; dette er intern repræsentationskonsistens og ikke bevis for en fysisk millisekundnøjagtighed eller en valideret tidsskala. Der beregnes ingen BJD eller nyt eksponeringsmidtpunkt.

De fem SDP-produkter angiver BARYCENT. Den lagrede BARYCORR er en observerkorrektion, ikke en leveret stjernehastighed. Dens nominelle km/s-enhed følger den generelle ESO-konvention; det validerer ikke FEROS' nøjagtighed. Ved hver dato har alle seks afsluttende fiber-1-grene samme observerkorrektion og samme deklarerede input til bølgelængde- og fladfeltskalibrering. Mellem datoerne er der fem forskellige WLC-sæt og fem forskellige FF-sæt.

| SDP-dato | Eksponering, s | Nominel BARYCORR, km/s | WLC-råreferencer | FF-råreferencer |
| --- | ---: | ---: | ---: | ---: |
| 2019-11-04 | 500.0438 | 19.0142 | 6 | 10 |
| 2019-11-07 | 500.0436 | 18.2126 | 6 | 10 |
| 2019-11-08 | 500.0439 | 18.0792 | 6 | 10 |
| 2019-11-10 | 500.0438 | 17.6692 | 6 | 10 |
| 2019-11-14 | 500.0432 | 16.3340 | 6 | 10 |

Alle originale kalibreringsidentiteter og QC-tal med kommentarer er bevaret. En manglende QC-enhed udfyldes ikke, og QC-resttal bruges ikke som kandidatstøj, kovarians eller signifikans. Samme deklarerede FF-input betyder heller ikke, at den ikke-fladfeltede variant fik den samme fotometriske behandling.

ESO's releasebeskrivelse oplyser, at observerkorrektionen allerede er anvendt, at den har kendte præcisionsbegrænsninger, og at den automatiske behandling ikke bruger den samtidige kalibreringsfiber til at opnå højere bølgelængdepræcision. QC-felterne er ikke et automatisk kvalitetsfilter. Vi anvender derfor ingen ekstra observerkorrektion. Som ren størrelsesillustration svarer en fejlagtig ekstra korrektion ved disse tre bølgelængder nominelt til **0,263–0,415 Å**, cirka **8,8–13,8 gemte samples**. Disse forskydninger er kun beregnet algebraisk og er ikke anvendt på data.

[ESO FEROS-releasebeskrivelse](https://www.eso.org/rm/api/v1/public/releaseDescriptions/94). [ESO's generelle dokumentation af BARYCORR-enheden](https://ftp.eso.org/pub/dfs/pipelines/instruments/esotk/esotk-pipeline-manual-0.9.7.pdf); denne anden kilde bruges kun som enhedskontekst, ikke som evidens for den ældre FEROS-reduktions præcision.

## D074: relativ mønstertilpasning med kandidatkerner udeladt

En separat metode låses efter metadatagennemgangen. Den tidligere profilsammenligning er kendt, så dette er en begrundet opfølgning og ikke en blind uafhængig signaltest. Der bruges alle **90 eksisterende samlede profiler**: fem datoer, tre kendte positioner, tre ekstraktionsmåder samt med/uden fladfeltning. Alle ti uordnede datopar undersøges med den tidligere dato som reference.

Tilpasningen benytter faste sidebånd **1–4 Å på hver side af den oprindelige kandidatposition**. Området inden for ±1 Å udelades. Vi tilpasser både begge sider samlet, kun blå side og kun rød side. Referenceprofilens midlertidige model evalueres ved en Dopplerforskudt koordinat med stykkevis lineær interpolation; målprofilen tilpasses med en fri skala samt konstant og lineær baggrund; skalaen er positiv ved alle fundne minima. Profilernes egen baseline bruges kun som positiv numerisk skalering. Ingen samples klippes efter udseende eller residual.

**D074 anvender således interpolation i en midlertidig referencemodel. D071's oprindelige flux- og bølgelængdearrays forbliver eksakt uændrede.** Der er ingen ekstra barycentrisk korrektion, ingen ekstern stjerneskabelon og ingen flytning af de oprindelige kandidatstatistikker.

Der er 180 par-/vindues-/reduktionskontekster og **540 tilpasningskurver**. Hver kurve evalueres på det på forhånd fastlagte grid fra −10 til +10 km/s med trin 0,05 km/s: **216.540 gridtilpasninger**. Alle slots kan beregnes, alle skalaer ved minimum er positive, og intet minimum ligger ved gridgrænsen. Der er ikke udvidet søgeområde eller valgt et finere grid efter resultatet. **Gridtrinnet er ikke en målt hastighedspræcision.**

Målet er den uvægtede sum af kvadrerede residualer, SSE. ERR er fortsat en pladsholder, og SSE er ikke chi-square, støj-likelihood eller FAP. Den samme observation og de samme fotoner genbruges i mange varianter; antal gridpunkter eller par er ikke antal uafhængige detektioner.

### Alle faste resultater

Intervaller er faktiske metode-/parintervaller, ikke konfidensgrænser. Forskydningens fortegn beskriver, hvordan den tidligere references mønster flyttes mod det senere måls koordinater. »Sløjferest« sammenligner stien i→j→k med i→k i additive log-bølgelængdeforskydninger, angivet i km/s-enheder.

| Position | Begge sider, km/s | Alle tre masker, km/s | Største rød–blå-forskel, km/s | Største sløjferest, begge sider | Største sløjferest, alle masker |
| --- | ---: | ---: | ---: | ---: | ---: |
| D002-0061 | -0.35 til +0.55 | -0.70 til +0.80 | 0.80 | 0.10 | 0.65 |
| D002-0063 | -0.40 til +0.60 | -0.40 til +0.65 | 0.20 | 0.10 | 0.15 |
| D002-0071 | -0.25 til +0.35 | -0.30 til +0.40 | 0.15 | 0.10 | 0.10 |

Alle 540 tre-dato-sløjfer samt 180 side-, 540 mode- og 270 fladfeltsforskelle er bevaret. Ved 0061 er sideafhængigheden og de største sløjferester tydeligere end ved de øvrige steder. Det er en metodefølsomhed i lokal mønsterregistrering. Den kan bl.a. påvirkes af linjeblandinger, profilvariation, ordenssamling eller kalibrering, men denne analyse fastslår ingen af årsagerne. Den er heller ikke en fysisk måling af en planets eller stjernes hastighed.

## Kontroller og databevaring

Alle tre nye audits består. D072 efterregner 61.560 skalarfelters tilstedeværelse/værdi/kommentar, alle 500.595 matchende kort og 860 medlemsnavne. D073 bruger selvstændig datetime- og Decimalaritmetik til tid, kalibreringslister og størrelsesillustrationer. D074 bruger en anden interpolationsberegning, QR i stedet for least squares og skalar summering til alle 216.540 gridpunkter. Alle minima genfindes; største uafhængige SSE-forskel er **1.16e-10**. Alle 990 pardifferencer og 540 sløjferester genkontrolleres. Dette er interne alternative beregninger udført af samme assistent, ikke ekstern fagfællebedømmelse eller fysisk kalibrering.

Fire nye figurer er visuelt kontrolleret: alle 15 standardprofiler med de faste masker, alle 540 minima, alle 540 sløjferester og alle 90 fladfeltede begge-sider-kurvers komplette søgegrid. Hele datasættet, også ikke-fladfeltede og enkeltsidede kurver, findes i JSON/CSV/NPZ.

Alle **98.561 tidligere færdige tabelceller** og alle **94.289 celler fra den gemte baseline** er bevaret eksakt i de samme 37+141 rækker. Tre nye faser tilføjer otte kolonner hver: nu **102.833 celler**. Den gamle 0061-rho-fejl, den blå COMB-mangel, 6. marts' sekundære status og alle tidligere oprindelsesvurderinger ændres ikke.

De fulde D069–D071-resultater er medtaget som den oprindelige, byteeksakte resultat-ZIP i den nye samlede pakke. Det aktive fortsættelsespunkt er nu **SETI_ACTIVE_CONTINUATION.json**, som peger på denne pakke og den præcist fastholdte historiske baseline version 59. Den store historikfil omskrives ikke, og den gamle ubekræftede gemmeoperation genforsøges ikke. Denne fortsættelse påstår derfor ikke, at den tidligere version 60 blev gemt. Se REPRODUCTION.md for den samlede evidens og genkørsel.

## Næste trin

D075 foreslås som en separat låst gentagelse af samme relative mønstertilpasning i de individuelle ordener. Den skal kontrollere, om ordenssamlingen påvirker resultaterne, med alle datoer, positioner, modes, fladfeltsvarianter og faste masker bevaret. D075 er endnu ikke låst eller udført. Der er endnu ingen valideret stjernerestframe, fysisk persistensudelukkelse, laserrespons, støjkovarians eller FAP.

0 kvalificerede lasersignaler; alle tre tidligere oprindelser uafklarede. Ingen nye arkivhentninger, nye FITS-sciencearrays, rå CCD-analyser, udgifter, personkontakter eller baggrundsberegninger. Den gamle 141-råkø er lukket, 90-/Rubinspor stoppet og offentlig upload udskudt.
