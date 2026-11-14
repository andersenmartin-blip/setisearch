# SETI D044–D046: arkividentitet og kontrol før signaloptagelsen

Dato: 11. november 2026. Alle observationstidspunkter nedenfor er UTC.
Grundlag: gemt projektversion48, SHA256 `a40fd6853aa1d0f1faa5e26b1a3d1bb24bc503197fc99665ef6525b247946d75`.

## Resultat

En yderligere arkivoptagelse af HD43629 fra **4. marts2021** er nu kontrolleret og analyseret ved den kendte6550.095Å-position. Den matcher de fastlagte relevante headerfelter, består geometri- og intensitetskontrollen og har 0.778365 gange originalens faste kontinuuumsnormalisering. Det lokale signerede3-sampleoverskud er mindre end i originaloptagelsen fra5. marts i samtlige seks baggrundsmodeller og alle24 fastlagte sammenligningsslots.

Det er en målrettet, beskrivende sammenligning af allerede udvalgte data. **Den fysiske årsag er fortsat uafklaret; kvalificerede lasersignaler:0.** Resultatet giver ingen kalibreret falsk-alarm-sandsynlighed, fysisk kildeklassifikation, duty cycle eller udelukkelse af en vedvarende/svagere kilde.

Den anden forhåndsvalgte post, fra **6. marts2021**, er bekræftet som en anden råfil af samme navngivne stjerne, men dens selectorfelter er TUN1/TUN1 mod originalens NONE/FP. Den opfylder derfor ikke D044kravet om identiske felter. Den er bevaret som et særskilt metadataudfald; dens rå-/ancillary-filer er ikke hentet, og dens flux er ikke analyseret. Selector-navnene er endnu ikke omsat til en valideret model for den faktiske optiske lysvej.

## D044: de to tidsvalgte posters identitet

Udvælgelsen var fastlagt i D043alene efter tidspunkt, før nye headers eller flux. Der er ikke valgt erstatningsoptagelser.

| Rolle | Arkivprodukt | Råfil / observation UTC | Timer fra originalens midtid | A/B-selector | D044udfald |
| --- | --- | --- | ---: | --- | --- |
| Før | ADP.2021-03-05T01:11:43.795 | HARPS.2021-03-04T01:59:35.557 | −22.377631 | NONE / FP | Identitet og alle faste felter består |
| Efter | ADP.2021-03-07T01:02:15.648 | HARPS.2021-03-06T01:16:40.899 | +24.907186 | TUN1 / TUN1 | Identitet består; to selectorfelter afviger |

Begge præcise råidentiteter er uden for de oprindelige141kandidaters råidentiteter og de fem allerede kendte HD43629epoker. Produktets ARCFILE/PROV1, entydig DataLink-progenitor, råfilens ARCFILE, måltid, objektnavn, koordinater, eksponering og CCD-geometri er krydstjekket. Det er adgang til arkivmålinger fra2021, ikke nye teleskopobservationer.

Der blev foretaget **8metadataforespørgsler**, i alt 590318bytes, og0FITS-body-/fluxlæsninger i D044. Det endelige uafhængige headeraudit kontrollerede **7910tildelte kortværdier** med en anden parser end produktionen.

### Bevarede adgangs- og parserfejl

Første URL-form kodede kolon som `%3A`; den ældre header-tjeneste behandlede dette bogstaveligt og returnerede to HTML-fejlsvar med HTTP200. Den arvede D035form med bogstaveligt kolon blev derefter fastlagt i en dokumenteret URL-amendment. De to korrekte produkt-header-svar indeholdt hver én84tegn lang ORIGFILE-visningslinje, hvor kun kommentaren fortsatte efter kolonne80. Den strenge parser standsede derfor først. En separat amendment tillod netop denne verificerede kommentarforlængelse; den komplette citerede filnavneværdi og de oprindelige HTML-bytes er bevaret.

De korrekte svar blev **genbrugt**, ikke hentet igen efter parserændringen. Der blev derefter foretaget to DataLink- og to rå-header-opslag. Hver af de otte forskellige URL'er er kaldt én gang. Alle første fejlsvar, koder, låse, amendments og resultater er bevaret. Ingen fysisk udvælgelses- eller kvalitetsgrænse blev ændret.

## D045: én fastlagt råfil med egne kalibreringsheaders

Kun4. marts-posten blev ført videre til den primære kontrol. De allerede verificerede DataLink-links blev låst før nye bodies. Præcis én råfil på13,190,385bytes og én ancillary-tar på6,963,200bytes blev hentet; to forespørgsler, ingen body-genforsøg. Der blev ikke hentet noget nyt1D-spektrumprodukt.

Råfilens824tildelte headerfelter blev sammenlignet med header-visningen:823var eksakt ens; primær DATASUMvar den samme værdi0med ekstra indledende mellemrum i den faktiske FITS-streng. Den første helt strenge sammenligning standsede på dette felt og er bevaret. En særskilt, låst repræsentationsafstemning tillod udelukkende whitespace omkring DATASUM; alle øvrige værdier forblev eksakte. Ingen tællinger blev læst som arrays i dette trin.

Egne e2dsA/B-headers blev udtaget fra det præcist navngivne råprogenitor-produkt. A har72ordener, B71, begge4096samples. Egne observationsdatoer, BERV, bølgelængde-/tracepolynomier og readout er kontrolleret. Geometrien bruger disse egne headers, ikke en kopieret trace fra originalen.

## D046: metode fastlagt før de nye pixels

Den kendte barycentriske luftbølgelængde er6550.095Å. Sammenhængen er den samme som i D042:

`lambda_bary = lambda_observer * (1 + BERV / 299792.458 km/s)`.

Kontrollens BERV er−22.2662475224974km/s. Egen native-A-orden67giver den fraktionelle position **421.404189360178**. NEARESTog FLOORer421; CEILer422. Den faste detektorsammenligning bruger421. Der er ingen tilpasning af topposition, hastighed eller lokal skalering og ingen spektral resampling. Dette er en barycentrisk sammenligning, ikke en ny fysisk valideret stjerneramme med intrinsisk RV-korrektion.

Den rumlige udtrækning følger de tidligere D040/D041regler: egne A72/B71traces, rå række4095−k, radius3sum, og robust rumlig affin baggrund på alle fastlagte referencepixels, mere end8pixels fra alle traces. Hele det faste native-interval293..549bevares. Normaliseringen er medianen uden forabs(k−421)≤20, identisk med D042reglen. Kontrollen har median **2854.210526315789ADU**, originalen **3666.929769392033ADU**. Forholdet **0.778365200812** ligger inden for den uændrede[0.5,2]grænse.

Alle216mulige rækker uden for central41har positiv radius6sum. Medianprofilens maksimum ligger ved0.0pixel, inden for den uændrede±1.5pixel-grænse. Den nye kontrols egen lokale rå/native-korrelation er0.989281162189; dette er en beskrivende kontrolværdi og ændrer ikke originalens historiske mislykkede rho0.780656<0.8krav.

Baggrundsmodellerne er affine og kvadratiske polynomier på sidebåndene±5..7,±8..12og±12..20native samples. Det primære mål er den signerede sum ved anchor−1,anchor,anchor+1efter egen spektral baggrund, divideret med den faste egen median.5- og15-samplesummer bevares også. Et diagnostisk maksimum i±2må ikke flytte ankeret eller udvælge modeller.

## Alle deklarerede resultater

Originalens3-samplesum er positiv i alle relevante D042kilderesultater. De originale24caseværdier genbruges uændret. Der er24nye kontrolcase-slots og24par; hver omfatter12forskellige native-tilpasninger/par. Detektor, NEARESTog FLOORhar her samme anker, så de tre slots pr. baggrund er dubletter og udgør ikke uafhængig evidens.

| Sammenligning | Kontrolanker | Kontrol3sum, ADU | Signeret normaliseret kontrol/original3sum | Original minus kontrol positiv i alle6? |
| --- | ---: | ---: | ---: | --- |
| DETECTOR_NATIVE / FIXED_K421 | 421 | -107.246612 til +234.676031 | -0.176138 til +0.318823 | ja |
| BARYCENTRIC_AIR / NEAREST | 421 | -107.246612 til +234.676031 | -0.176138 til +0.318823 | ja |
| BARYCENTRIC_AIR / FLOOR | 421 | -107.246612 til +234.676031 | -0.176138 til +0.318823 | ja |
| BARYCENTRIC_AIR / CEIL | 422 | +17.803609 til +243.176929 | +0.020720 til +0.386689 | ja |

For den primære NEARESTsammenligning spænder de signerede forhold altså fra **-17.61%til31.88%**. Det største positive tal blandt de seks baggrundsvalg er31.88%. **Dette er ikke en statistisk øvre grænse, en laserstyrkegrænse eller sandsynligheden for en bestemt fysisk forklaring.** Negative tal betyder et negativt lokalt residual i den valgte baggrundsmodel, ikke negativ fysisk luminositet. Samplesummer er ikke en præcist fælles bølgelængdeintegral eller ækvivalentbredde.

D042s allerede afsluttede9. marts-kontrol gav ligeledes mindre overskud ved den deklarerede bølgelængde. Den nye4. marts-kontrol føjer nu en tidligere dato til den kontrollerede, beskrivende evidens. Der er ikke her udført en ny samlet tre-epoke-fit, en tidsvariabilitetstest eller en blind søgning.

## Uafhængig kontrol og faktisk arrayadgang

Audit: **PASS**.16,705lokale råpixels,25,700overscanpixels og257bevarede native-A-samples er reproduceret eksakt. Den robuste rumlige baggrund er beregnet med en anden, skalær implementation; største forskel i r3er 9.09e-13ADU. En60cifret Decimal-inversion af bølgelængden afviger 1.19e-11pixel.

72kontrolsummer og72genbrugte kildesummer er kontrolleret med QR mod produktionens least squares.72lineære kontrastoperatorer reproducerer summerne og annihilerer deres baggrundspolynomier. Største sumafvigelser er 1.36e-11ADU(QR)og1.41e-11ADU(lineær operator); største forholdsafvigelse er7.02e-15.

FITS-containerne blev ved D046arrayadgang dekodet som hele CCD2(8,798,208pixels)og hele native-A-arrayet(72×4096=294,912samples); selve analysen/bevaringen afspektrale samples er begrænset til det på forhånd fastlagte vindue. Native-B-flux, den blå CCD-array og CCF-arrays blev ikke læst. Der er0nye Monte Carlo-træk,0nye forespørgsler i D046og0fulde genafspilninger af141-køen. De tre endelige figurer er visuelt gennemgået.

## Bevaring og næste afgrænsede skridt

Alle **58,689tidligere tabelceller** er bevaret eksakt. Hver fase tilføjer8nye kolonner til de samme37+141rækker; slutstatus er **62,961celler**. Ingen oprindelige kandidatposter, årsagsvurderinger, D039/D040/D041støjresultater, D042kontraster eller D043metadatarækker er ændret. Alle tidligere videnskabelige arkivmedlemmer bevares; kun de tre rod-pegefiler opdateres, og deres gamle bytes gemmes separat.

De syv TOI-880navne fra D043er stadig uafklarede aliases. De øvrige tre klare ekstra metadataposter er ikke kontrolleret som egne råidentiteter i dette pas. D043s10arcsec/±30dages afgrænsning gælder stadig og udgør ikke en fuldstændig inventering af alle målinger af stjernen.

Næste foreslåede trin(D047, ikke udført eller låst)er en afgrænset gennemgang af primær HARPSdokumentation og de allerede gemte headers for at forstå6. marts-selectorernes faktiske lysvej. Den eksisterende exact-field-afvigelse skal blive stående. En eventuel sekundær fluxanalyse kræver sin egen fastlagte metode; posten må ikke automatisk omklassificeres til en identisk kontrol.

Kvalificerede lasere0; alle tre fysiske årsager uafklarede; ingen kalibreret FAPeller valideret stjerneramme/persistensudelukkelse. D002-0061s gamle kvalitetsfejl og D002-0063s blå status er bevaret. Offentlig upload er fortsat udskudt; de gamle90-/Rubinspørgsmål er stoppet. Ingen udgifter, eksterne kontakter eller baggrundsberegning.

## Reproduktion og primære kilder

Udpak resultatpakken sammen med hovedprojektet i samme rod, så de oprindelige medlemsstier bevares. Resultatpakken indeholder den nye råfil/ancillary, alle headers, første fejl, metodeamendments, koder, arrays, kontrastoperatorer, audits, CSV/JSON-tabeller og tre fulde figurer. Hovedprojektet indeholder de nye metoder og afledte resultater, mens de nye body-filer og fulde figurer ligger i resultatpakken af hensyn til størrelsen. Dette er ikke en selvstændig pakke uden det tidligere projektgrundlag.

Primær dokumentation: [ESO Programmatic Access](https://www.eso.org/cms/eso-data/programmatic-access.html), [ESO Raw Data Help](https://archive.eso.org/eso/eso_archive_help.html) og [ESO Programmatic Demo](https://archive.eso.org/programmatic/). De dokumenterer adgang og proveniens; kontrastresultaterne ovenfor stammer fra vores præcise inputbytes og beregninger. Se også D042s dokumentation af bølgelængdekonventionen.
