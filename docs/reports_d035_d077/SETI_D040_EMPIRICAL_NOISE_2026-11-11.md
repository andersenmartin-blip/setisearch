# SETI D040 — reelle kontrolobservationer og støjdiagnostik

Dato: 11. november 2026. Udgangspunkt: den gemte D039-tilstand, version 45.

D040 har gennemført den afgrænsede sammenligning med alle fire allerede udvalgte kontrolstjerner. Ingen er tilstrækkeligt lysstærk til den på forhånd fastlagte direkte sammenligning med D002-0061. Den elektroniske centrale spredning er stabil omkring 4,5 elektroner, men markante baggrundspixels og lokal korrelation beskrives ikke af den antagne model med uafhængig Poisson- og Gauss-støj. Modellen er derfor fortsat ikke empirisk valideret som fuld støjfordeling. **Ingen kvalificeret laser og ingen ny fysisk klassifikation.**

## Det faktiske udvalg

Udvalget er hele det eksisterende 0061 STAR,SKY-udvalg fra D024/D025: J0621-50, J0535-08, TOI-969 og J0708-68. Tre har de relevante headerfelter som originalen; J0535-08 har THAR1-vælger frem for NONE og beholdes i sin egen gruppe. Maskebetegnelsen i tredje DPR-komponent er ikke uden videre en fysisk instrumentkonfiguration. Ingen observation blev udskiftet efter måling.

| Observation | Gruppe | Median raw-r3, ADU | Flux i forhold til original | Egen postscan-støj, elektroner |
|---|---|---:|---:|---:|
| HD 43629 | Original | 3666.93 | 100.00 % | 4.5150 |
| J0621-50 | Samme headerfelter | 418.09 | 11.40 % | 4.5136 |
| J0535-08 | Anden vælger | 348.64 | 9.51 % | 4.5475 |
| TOI-969 | Samme headerfelter | 1000.80 | 27.29 % | 4.5096 |
| J0708-68 | Samme headerfelter | 599.64 | 16.35 % | 4.5070 |

Fluxreglen var positiv median uden for de centrale 41 samples og et forhold på 0,5–2,0 til originalen. Alle fire kontroller ligger under 0,5. Geometrikontrollen bestås i alle fem optagelser: medianprofilens top ligger på 0,0 pixel i forhold til eget A-spor. **Antal andre stjerner med både samme relevante headerfelter, understøttet geometri og matchende intensitet: 0.**

Der blev genbrugt to eksisterende råfiler og to tilhørende ancillary-filer. For de øvrige tre kontroller blev der foretaget præcis tre DataLink-opslag og hentet tre råfiler samt tre ancillary-filer. Alle var tilgængelige; ingen genforsøg eller erstatningsvalg. Dette er arkivdata fra 2021, ikke nye teleskopobservationer. Tidligere native-kontrolresultater og én råkontrol var allerede kendte; undersøgelsen er ikke blind.

## Metode og verificeret geometri

Pool og adgangsgrænser blev låst før nye forespørgsler. Efter egen headerkontrol blev analyseprogram, inputhashes, geometri, bølgelængde, vinduer, fluxregel, seks kontinuumvalg, støjgrene og seeds låst før nye D040-pixelmålinger. Se POOL_AND_ACCESS_LOCK.json og SCIENCE_METHOD_LOCK.json.

Alle optagelser bruger egen native A-ordre 67 ved observer-air 6550,573287171706 Å, nærmeste sample 421 og vinduet 293–549. Der anvendes ikke en barycentrisk justering i detektorstøjtesten. Egne 72 A- og 71 B-ordrer bestemmer spor og udelukkelse af nabospor. Native indeks k svarer til rå række 4095−k; sporkolonnen beregnes ved samme argument. CCD2 beskæres korrekt, og råtal konverteres til float64 før fortegnet subtraktion. BZERO = 32768 er FITS-kodning, ikke fysisk bias.

De faste rumlige referencer har absolut sporafstand 10–14 eller 26–30 pixels og ligger mere end 8 pixels fra alle egne A/B-spor. Alle 257 rækker har 12 referencepixels og 6 pixels i radius 3-aperturen. Baggrunden estimeres med repeated-median-hældning og medianintercept. Der foretages også en kontrol med skiftevis sorterede referencer i to halvdele; forskellen mellem deres integrerede baggrundsforudsigelser annullerer den fælles stjerneapertur.

Der er målt 83.525 råpixels i de gemte vinduer, 128.500 pre/postscan-pixels og 1.285 native-A-fluxsamples. Rå-HDU2 og native-A-arrayet blev afkodet i fuld størrelse; de gemte og analyserede spektroskopiske vinduer er de beskrevne. De oprindelige 0061 råpixels, masker, geometri og native-flux blev reproduceret præcist i de 257 rækker. Radius 3-udtrækket afviger højst 9,1×10⁻¹³ ADU fra det gamle udtræk.

## Central støjspredning og dens begrænsning

Egen CCD2 header angiver gain 1,36 elektroner/ADU og RON 7,07 elektroner i alle fem optagelser. Alle 50 postscan-kolonner beholdes. Efter fjernelse af række- og kolonnemiddelværdier giver de 4,507–4,547 elektroner i de fire kontroller; originalen giver 4,515 elektroner i dette vindue med 257 rækker. D039 brugte 265 rækker og fik 4,508 elektroner; vinduerne er forskellige.

To fastlagte grene pr. optagelse bruger henholdsvis headerens RON og egen målte postscan-RON, 1.000 simuleringer pr. gren. Der er i alt 10.000 træk. Hvert træk indeholder foton-Poissonstøj, analog Gauss-læsestøj, genestimeret fuld rumlig baggrund og begge referencehalvdele. Egen bias holdes betinget fast. Fotonmiddelværdier er plug-in-estimater fra de udvalgte målinger; referencebaggrunden forskydes kun til ikke-negativ forventning og alle sådanne gulve registreres. Det er ikke en ny støjkalibrering uafhængig af de udvalgte data.

Referencepixel-par i nabospektralrækker sammenholdes kun, når de er samme fysiske kolonne. Deres robuste MAD i forventede variansenheder ligger cirka 0,62–0,66 med header-RON og 0,93–0,99 med egen postscan-RON. Den lavere elektroniske støj beskriver således den centrale referencespredning bedre i disse data. Enkeltoptagelsers overscan og plug-in-fotonmodel kalibrerer dog hverken den fulde kovarians, haler eller en astronomisk nulfordeling.

For stjerneaperturen anvendes anden differens, hvor alle tre bidrag ligger uden for de centrale 41 samples. Spektrallinjer og krumning kan bidrage; dette er ikke en ren elektronisk støjmåling. Sammenligningen er udført med præcis samme filter i simuleringerne, da overlappende anden differenser selv skaber korrelation.

| Observation | Målt robust spredning / MC, header-RON | Samme, egen postscan-RON | Referencekorrelation, lag 1 |
|---|---:|---:|---:|
| HD 43629 | 0.972 | 0.991 | 0.0671 |
| J0621-50 | 0.822 | 0.988 | 0.0232 |
| J0535-08 | 0.954 | 1.135 | 0.0151 |
| TOI-969 | 0.984 | 1.095 | 0.4181 |
| J0708-68 | 1.037 | 1.179 | -0.0184 |

De typiske aperturdifferenser har omtrent den simulerede størrelse, med synlige forskelle mellem grene og stjerner. Det validerer ikke originalens formscore fra D039 eller en bestemt fysisk forklaring. D040 bruger et andet plug-in-middel og et kontekstvindue med 257 rækker; D039’s 16 grene og 22.000 formtilpasninger er ikke ændret eller genfortolket som kalibrerede sandsynligheder.

## Kraftige referenceudsving beholdt

Den ordinære samme-kolonne-korrelation er 0,418 for TOI-969 ved lag 1. Originalen har også et meget kraftigt, lokalt referenceudsving. Efter de primære resultater blev alle fem optagelser og begge støjgrene gennemgået ens med top 10 nabopar, RMS, robust MAD og deskriptive antal over henholdsvis 3, 5 og 10 modellenheder. Denne lokalisering er **efterfølgende og ikke en på forhånd fastlagt opdagelsestest**. Ingen pixel eller række er klippet, ingen maske eller udvælgelsesregel ændret, og ingen simulering kørt om.

| Observation | Reference-MAD | Reference-RMS | Maks. absolut nabodifferens | Antal over 5 | Antal over 10 |
|---|---:|---:|---:|---:|---:|
| HD 43629 | 0.655 | 7.007 | 271.02 | 8 | 4 |
| J0621-50 | 0.616 | 0.622 | 2.24 | 0 | 0 |
| J0535-08 | 0.633 | 0.632 | 2.28 | 0 | 0 |
| TOI-969 | 0.652 | 0.799 | 15.52 | 4 | 3 |
| J0708-68 | 0.651 | 0.645 | 2.43 | 0 | 0 |

Tabellen bruger header-RON. Tallene er variansnormaliserede deskriptive størrelser; de er ikke kalibrerede gaussiske signifikansniveauer eller laser-sandsynligheder. Originalens største referencepixel ligger ved native indeks 385 og sammenføjet fysisk kolonne 3625, cirka 2.175 ADU over egen rækkebias. TOI-969 har et udsving ved indeks 497/kolonne 3666, cirka 212 ADU over bias, med forhøjede naboer. De ligger uden for de centrale 41 samples. Deres årsager er ikke fastslået; de må ikke automatisk kaldes hverken kosmisk stråling, laser eller fejl i kandidatens centrale aperture. Den tidligere 0061 kvalitetsfejl består.

Dette er grunden til at holde robust central spredning og ekstreme udsving adskilt i konklusionen: en model kan beskrive den første rimeligt og stadig mangle den anden. Der er ingen kalibreret fysisk kovarians eller falsk-alarm-rate.

## Kontinuum og numerisk kontrol

Alle seks arvede kontinuumvalg er bevaret: affine og kvadratiske polynomier på sidebånd 5–7, 8–12 og 12–20 pixels. De giver en spredning i central kontinuumforudsigelse på 132,81 ADU for originalen og 22,59–86,24 ADU for kontrollerne. Betingede noise-only-sammenligninger og alle 15 fortegnede residualsamples er gemt. Stjernernes linjer, de meget forskellige fluxniveauer og estimerede middelværdier forhindrer, at disse tal kan bruges som en direkte nulprøve for formscoren fra D039. Intet kontinuumvalg er udpeget bagefter som det foretrukne.

Den separate implementering læser FITS-blokke og signed 16 bit-kodning uden Astropy og verificerer 15 DATASUM-felter. Egen geometri beregnes med Horner-evaluering. SciPys uafhængige, kompilerede Siegel-estimator kontrollerer samtlige 2.570.000 fulde og 5.140.000 halve simulerede baggrundstilpasninger samt 3.855 reelle fulde/halve tilpasninger. Alle 60.000 simulerede kontinuumcentralværdier genberegnes med QR i stedet for produktionens pseudoinvers. De 50 reference-lagstatistikker og 50.000 MC-korrelationsværdier kontrolleres særskilt. Begge numeriske kontroller består. Det er en separat implementering i samme arbejdssession, ikke ekstern fagfællebedømmelse.

Fem figurer er gemt med data og kode: INTENSITY_AND_OVERSCAN5.png, EMPIRICAL_NOISE_DIAGNOSTICS10.png, SPECTRAL_CONTEXTS_AND_CONTINUA5.png, COVARIANCE_DIAGNOSTICS5.png og REFERENCE_PIXEL_CONTEXT5.png. Alle genererede tilfældige input, alle 10 grene og alle ekstreme værdier bevares i resultatarkivet. De gamle 37 og 141 tabellers 52.993 felter er uændrede; D040 tilføjer kun sine egne kolonner.

## Næste afgrænsede skridt

Der findes allerede en gemt råoptagelse af **samme stjerne, HD 43629, fra 9. marts 2021**, HARPS.2021-03-09T01:17:26.087. Dens identitet, 1.799,9965 sekunders eksponering, STAR,SKY,K3, vælgere, læseindstilling, gain og RON er kontrolleret alene i metadata. Egne native A/B-sporheaders findes også. Det giver mulighed for at undersøge, om et kendt 655 nm-vindue her kan levere en kontrol ved mere sammenlignelig flux uden flere rådownloads.

Dette er forslaget til D041. Metode og nyt rødt vindue er **ikke fastlåst eller målt endnu**; intensitetsmatch er ukendt. En blå 0063 kandidat i denne anden optagelse giver ikke dens røde vindue status som bevist laserfri kontrol. Der foretages ingen overførsel af blå/rød COMB-respons. En eventuel senere fysisk gentagelses- eller fraværstest kræver særskilt bølgelængde-/hastighedsbehandling og fastlagt metode.

Samlet status: 0 kvalificerede lasere, alle tre oprindelige fysiske årsager uafklarede, 0061 rho 0,780656<0,8 fortsat ikke bestået. Den gamle 141 råkø er lukket, old90/Rubin fortsat stoppet, offentlig upload udskudt. Ingen baggrundsanalyse kører efter denne afslutning; ingen udgifter eller eksterne henvendelser.
