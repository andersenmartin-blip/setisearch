# SETI D055–D056: septemberudslagets rumlige profil og modelkontrol

**12. november 2026.** Grundlag: gemt projektversion 52, SHA256 `cf1b0917cfb40ac03b6cab1bd087a7af59b2f23ab7703604c77463e21370008b`. Observationstider er UTC. Kandidat D002-0071, HD 43629, kendt position **5730.715 Å**, original 9. september 2021; kontroller 6. og 18. september.

## Hvad undersøgelsen viser

Originalens lokale spektrale overskud består, når udtrækningen varieres mellem fire faste aperturer og fire egne rumlige profilmodeller. Original minus kontrol er positiv i alle **384 deklarerede parslots**. Samtidig beskriver en skaleret, fastcentreret normalstjerneprofil ikke hele originalens rumlige pixelmønster ved udslaget.

Den første egen referenceprofil, D055, giver en central rest-RMS på **75.09–81.69 ADU**, cirka **3.82–4.23 gange** medianen blandt hver models tilbageholdte referencer. Den direkte native-pixelmodel i D056 reducerer dette til **60.93–65.25 ADU**, men dens tilbageholdte referencer bliver også bedre beskrevet. Originalens forhold til referencemedianen er derfor **4.86–5.58**. I alle otte fastlagte native-modelvarianter ligger originalens centrale RMS over den største observerede referencerække i den tilhørende fold.

Det er **ikke sigma-værdier, p-værdier eller en kalibreret sandsynlighed**. RMS her er pixelrestfejl under en bestemt rumlig model; den indeholder modelafvigelse, lysniveau, pixelplacering og støj. Den oprindelige hændelse var allerede udvalgt før disse undersøgelser. Den fysiske årsag er fortsat **uafklaret**, og der er **0 kvalificerede lasersignaler**.

Vores fortolkning er afgrænset: den målte afvigelse kan ikke i disse modeller forklares alene ved D055's interpolation af referenceprofilen. Resultatet beviser ikke kosmisk stråling, en defekt pixel eller en bestemt belysningsfejl, og den empiriske stjerneprofil er ikke en valideret lasersvarfunktion.

## Input og forhåndsfastlagt adgang

Kun de allerede gemte D054-arrays for originalen og de to kontroller er brugt. Alle har egne trace-offsets, native-indekser **2534–2790**, egen orden 53 og de tidligere verificerede identiteter. D028's egne source-/kalibreringsresultater er beholdt som allerede kendte referencer. Ingen ny FITS-fil eller native-flux-array er læst, og ingen teleskopforespørgsel, ny dato eller Monte Carlo-kørsel er udført.

D055's metode og auditkode blev låst før nye skabeloner og ekstraktionsresultater. D056 blev særskilt låst efter, at D055-afvigelsen var set, men før direkte native-profiler blev beregnet. D056 er derfor en målrettet kontrol af den første model, ikke en uafhængig opdagelsestest. Alle oprindelige og nye modelalternativer står bevaret.

## D055: egne profiler med tilbageholdte referencer

For hver observation deles native-indekserne efter lige/ulige paritet. Hver skabelon trænes kun på **abs(k−2662)>20** og positiv signeret radius-6-sum. Der kræves mindst 64 træningsrækker; de faktiske grupper har 107–108 rækker. Ingen pixelrække i den centrale 41-samplezone bruges til træning.

De rumlige profiler normaliseres med hver rækkes egen radius-6-sum, interpoleres i rumlig retning på en fast kvartpixelgrid fra −12 til +12 og kombineres med punktvis median. Signerede profilværdier beholdes. Den modsatte paritets **samtlige** 108 rækker uden for kernen bruges til validering, også når radius-6-summen er ikke-positiv. Hver sådan række er tilbageholdt præcis én gang; træningsrestfejl bruges ikke som valideringsresultat.

Hver skabelon vurderes ved de egne faktiske trace-offsets. Dens diskrete sum inden for radius 6 normaliserer profilen. På pixels inden for ±8 fit'es enten kun en signeret traceamplitude eller traceamplitude plus konstant og rumlig hældning. Centrum og bredde er faste. Alle fit er uvægtede, med fuld numerisk rang og conditiontal under 1e8. Ingen støjkovarians eller fysisk PSF tildeles.

Det giver **6 skabeloner, 12 rumlige modeller og 3,084 rækkefit**. For originalens primære NEAREST-række k2662 fås:

| D055-model | Central rest-RMS, ADU | Valideringsmedian, ADU | Største valideringsrække, ADU | Central/median |
| --- | ---: | ---: | ---: | ---: |
| TRAIN_0_TRACE_ONLY | 81.691853 | 21.382531 | 29.690808 | 3.820495 |
| TRAIN_0_TRACE_PLUS_AFFINE | 76.833466 | 19.423301 | 28.140153 | 3.955737 |
| TRAIN_1_TRACE_ONLY | 79.833324 | 19.006704 | 33.667024 | 4.200272 |
| TRAIN_1_TRACE_PLUS_AFFINE | 75.094344 | 17.752454 | 32.630999 | 4.230082 |

RMS er kvadratroden af den gennemsnitlige kvadrerede pixelrestfejl inden for ±8 rumlige pixels. De to øvrige faste kernerækker, anker−1 og anker+1, samt alle fire koordinatvisninger er bevaret i CORE_VALIDATION48.

## Udtrækningsfølsomhed: alle seks baggrunde og fire visninger

Radius 3, 5, 6 og 7 er beholdt som fire særskilte signerede aperturekurver. De to paritetsprofiler og to rumlige fitmodeller giver fire yderligere ekstraktorer. Hver kurve normaliseres med sin egen faste median uden for den centrale 41-samplezone.

De seks spektrale baggrunde og de fire egne D054-ankre er uændrede: affine/kvadratiske sidebånd ±5..7, ±8..12 og ±12..20; detektor k2662 og barycentrisk luft NEAREST/FLOOR/CEIL. Alle signerede 3-, 5- og 15-samplesummer bevares. Ingen spektral resampling, flytning eller foretrukken model vælges efter resultatet.

Det giver **576 cases, 336 forskellige native-fit, 384 parslots og 288 forskellige native-par**. Alle 384 original-minus-kontrol-3sumforskelle er positive. De er modelalternativer på genbrugte pixels, ikke 384 uafhængige hændelser.

Primære NEAREST-forhold, signeret normaliseret kontrol/original-3sum, over alle seks baggrunde:

| Ekstraktor | Kontrol 6. september | Kontrol 18. september |
| --- | ---: | ---: |
| AP_R3 | -0.467707 til -0.018332 | +0.006487 til +0.219210 |
| AP_R5 | -0.457841 til -0.037509 | +0.014079 til +0.213998 |
| AP_R6 | -0.449791 til -0.023287 | +0.024691 til +0.227948 |
| AP_R7 | -0.435786 til -0.022240 | +0.047323 til +0.250079 |
| TRAIN_0_TRACE_ONLY | -0.473982 til +0.005121 | -0.055106 til +0.191005 |
| TRAIN_0_TRACE_PLUS_AFFINE | -0.490061 til +0.045946 | -0.094937 til +0.205073 |
| TRAIN_1_TRACE_ONLY | -0.473536 til +0.005157 | -0.054092 til +0.190405 |
| TRAIN_1_TRACE_PLUS_AFFINE | -0.490177 til +0.046051 | -0.093539 til +0.204230 |

De 64 fulde visningsgrupper indeholder også detektor-, FLOOR- og CEIL-udfaldene. Negative værdier er negative lokale residualer for et baggrundsvalg. Ingen af tallene er en øvre laserstyrke- eller konfidensgrænse.

## D056: direkte fit til de målte native-pixels

For at teste referenceprofilens interpolation tilpasses en kubisk B-spline **direkte til de normaliserede native-pixelværdier ved deres faktiske egne rumlige offset**. Pixeldata bliver ikke interpoleret. Den observerede pixelrespons G(x) er en beskrivende funktion af de registrerede counts, ikke en dekonvolveret optisk PSF.

Begge på forhånd fastlagte knudegrids bruger én pixels afstand og klampede grænser −8/+8: indre heltalsknuder −7..7 eller halvheltalsknuder −7.5..7.5. Der bruges de samme to paritetsfolds og trænings-/valideringsmasker som i D055. Ingen regularisering, positivklipning, fri traceforskydning eller breddejustering indføres.

Den direkte respons vurderes ved hver egen pixelplacering, normaliseres inden for radius 6 og bruges med begge tidligere rumlige fitmodeller. Der er **12 direkte profiler, 24 modeller og 6,168 rækkefit**, alle numerisk understøttede. D056 laver ingen nye spektrale baggrundsfit og ændrer ingen af D055's 576 cases eller 384 par.

| Observation | Central rest-RMS over alle 8 native-varianter, ADU | Central/egen valideringsmedian | Over egen største valideringsrække |
| --- | ---: | ---: | ---: |
| ORIGINAL | 60.931122–65.253983 | 4.858131–5.579932 | 8/8 |
| BEFORE | 5.794785–7.658135 | 0.561134–0.773508 | 0/8 |
| AFTER | 12.905469–13.468974 | 1.225918–1.516432 | 0/8 |

Originalens otte primære udfald er:

| Grid / træningsparitet / model | Central RMS, ADU | Valideringsmedian, ADU | Største valideringsrække, ADU | Central/median |
| --- | ---: | ---: | ---: | ---: |
| INTEGER / 0 / TRACE_ONLY | 65.253983 | 11.694405 | 25.738350 | 5.579932 |
| INTEGER / 0 / TRACE_PLUS_AFFINE | 62.570817 | 11.563515 | 25.648959 | 5.411055 |
| INTEGER / 1 / TRACE_ONLY | 63.521362 | 12.503455 | 27.351374 | 5.080305 |
| INTEGER / 1 / TRACE_PLUS_AFFINE | 60.931122 | 12.263705 | 26.952333 | 4.968410 |
| HALF / 0 / TRACE_ONLY | 65.151878 | 12.207928 | 25.748413 | 5.336850 |
| HALF / 0 / TRACE_PLUS_AFFINE | 62.598314 | 11.947418 | 25.667523 | 5.239485 |
| HALF / 1 / TRACE_ONLY | 63.491719 | 12.663190 | 29.784897 | 5.013880 |
| HALF / 1 / TRACE_PLUS_AFFINE | 61.002661 | 12.556816 | 29.683022 | 4.858131 |

Den direkte models centrale restfejl er **0.7953–0.8147 gange** den tilhørende D055-fejl, en reduktion på cirka 19–20 %. Originalens almindelige referencer bliver også bedre beskrevet; derfor bliver det relative core/median-forhold større. De otte resultater genbruger de samme sourcepixels og udgør ikke otte uafhængige prøver.

For originalens FLOOR-række k2661 er den direkte RMS 64.02–64.72 ADU; for detektor/NEAREST/CEIL-k2662 er den 60.93–65.25 ADU. Alle fire visninger og alle fold-/grid-/modelkombinationer findes i CORE_VALIDATION96. Der er ingen efterfølgende flytning af ankeret for at forbedre profilen.

## Hvad støjoplysningerne kan understøtte

Pre-/postscanens tidligere målte tovejs-restspredninger reproduceres: **3.2791–3.3405 ADU**, svarende til 4.4595–4.5430 elektroner med egen gain 1.36. Headerens RON er 7.07 elektroner, eller 5.1985 ADU efter gain. Disse størrelser er registreret separat og er ikke uden videre identiske fysiske støjmål. Header-RON er ikke erstattet af overscanværdien.

De to kontroldatoer har lavere counts og kortere eksponering end originalen. De rumlige residualer omfatter også profilmodellens begrænsninger og eventuelle andre lokale afvigelser. Især efterkontrollens valideringsrækker indeholder store restfejl langt over dens median; alle disse rækker og deres maksimum er beholdt i figuren og tabellerne. De kan ikke behandles som en renset, certificeret laserfri nulfordeling.

Ingen fysisk foton-/kovariansmodel er valideret, og ingen FAP, p-værdi eller sigma-betydning udledes af core/median-forholdene. Resultaterne understøtter en fortsat undersøgelse af udslagets rumlige struktur; de tildeler ikke en fysisk årsag. Tidligere spektrale bredder og den nye tværprofil er forskellige egenskaber ved den samme allerede udvalgte hændelse, ikke uafhængige opdagelser.

## Uafhængig kontrol og figurer

**Begge audits: PASS.** D055 bruger separat intervalinterpolation og sorterede medianer mod produktionens NumPy-funktioner, derefter skalarprojektion/QR mod least squares. Alle 3,084 rækkefit er kontrolleret. Største skabelonafvigelse er 1.11e-16; største forudsagte pixelafvigelse er 1.14e-12 ADU.

Alle fire historiske D028-sourceaperturer reproduceres på 257 fælles samples med største afvigelse 9.09e-13 ADU. **504 tidligere D054-radius-3-skalartal er bevaret eksakt.** 1,728 QR- og lineære operatorkontroller efterprøver de signerede spektrale summer. Største QR-/operatorafvigelse er 5.55e-11/6.64e-11 ADU; største forholdsafvigelse er 1.18e-14.

D056 kontrollerer Cox–de Boor-basis mod en uafhængig SciPy B-spline-basis, inklusive endepunkter og nul uden for intervallet. 12 profilfit og 6,168 rækkefit er genberegnet med QR/skalarprojektion. Største basisafvigelse er 2.22e-16, pixelafvigelse 1.96e-12 ADU og RMS-afvigelse 4.01e-13 ADU. Alle frosne D055-outputhashes består efter D056.

Der er 648 tilbageholdte native-rækker på tværs af de tre observationer, hver brugt én gang pr. foldgennemgang. D056's to knudegrids genbruger disse rækker; de skaber ikke flere observationer. Alle modeldubletter er mærket.

Tre endelige videnskabelige figurer er visuelt gennemgået: central pixelprofil med D055/D056-modeller; hver centralrække mod alle otte holdout-modellers medianer, 95-percentiler og maksimum; samt de præcise native-restpixels i de tre epoker. Visningen bruger det på forhånd fastlagte INTEGER/paritet-0/TRACE_ONLY/NEAREST-valg. Alle alternativer står i tabellerne, også når de ikke tegnes som pixelkort.

## Bevaring og næste opgave

Alle **74,353 tidligere tabelceller** er bevaret eksakt. D055 og D056 tilføjer hver otte kolonner til de samme 37+141 rækker; samlet **77,201 celler**. Ingen tidligere status, kildevalg eller kvalitetsfejl er omskrevet. Gamle arkivmedlemmers bytes bevares; de tre tidligere aktive rodpegere står eksakt i D055/FROZEN_PARENT.

Resultatpakken bevarer alle nye profiler, pixel-/fitarrays, kontrastoperatorer, tabeller, metoder, kode, audits, rapporter, fulde state-tabeller og tre figurer. Den inkluderer også den uændrede D054-arrayfil, der bruges som numerisk input. Udtræk pakken under samme rod som hovedprojektet. Hovedprojektet indeholder den kompakte fortsættelse og en hashbundet pakkehenvisning. **De aktuelle fulde D055/D056-state- og analysetabeller ligger i resultatpakken og skal udtrækkes før videre tabel-/arrayarbejde.** Tidligere payloads fjernes ikke for at få plads.

Efter denne afgrænsede septemberundersøgelse prioriteres det eksisterende blå informationshul, **D002-0063 ved 4826.6475 Å**. Den foreslåede D057-gennemgang fastlægger egne header- og blå geometri-/inputkrav for de allerede identificerede 3., 4., 5. og 6. marts sammenlignet med kilden 9. marts. Den starter med gemte metadata og filproveniens; ingen nye teleskopopslag eller kontrolpixels er udført her. D057 er endnu ikke låst eller udført. Dette er en arbejdsprioritet, ikke en rangordning af kunstige signalers sandsynlighed.

Septemberens betingede profilafvigelse bevares som uafklaret. D002-0061's gamle `rho=0.7806562435869904<0.8`-fejl, D002-0063's uvaliderede blå COMB-respons og 6. marts' sekundære status består. **Alle tre fysiske årsager er uafklarede; 0 kvalificerede lasersignaler.** Ingen fysisk laserrespons, kovarians, persistensudelukkelse, blå/rød COMB-overførsel eller bestemt partikel-/pixelårsag tildeles. Den gamle 141-kø er lukket, de gamle 90-/Rubinspor stoppet og offentlig upload fortsat udskudt. Ingen udgifter, eksterne kontakter eller baggrundsberegninger.
