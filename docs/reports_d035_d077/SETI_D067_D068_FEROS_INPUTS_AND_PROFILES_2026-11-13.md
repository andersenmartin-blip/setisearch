# SETI D067–D068: FEROS-filer valideret og første faste profiler analyseret

**13. november 2026.** Grundlag: projektversion58, SHA256 `ba9d80a47ba464baddae27587352c5e1a04f31574dd77bda9e99a1d3491a2f68`. HD43629/TIC34077285, fem allerede fastlagte observationsdatoer4.,7.,8.,10. og14.november2019. Tider i kvitteringer erUTC.

## Resultat

Alle **15 inputfiler** er hentet og valideret: fem råfiler, fem reducerede1D-spektre og fem tilhørende pipelinearkiver, i alt **387,225,961bytes**. Der er nu udført en målrettet første analyse ved de tre tidligere kendte bølgelængder i samtlige fem FEROS-spektre.

Den på forhånd valgte primære baggrund giver positive lokale kontraster i alle15profiler. **Ved alle tre positioner skifter kontrasten imidlertid fortegn, når de øvrige fastlagte baggrundsmodeller og sampleankre anvendes.** De positive tal kan derfor ikke i sig selv fortolkes som laserlinjer eller som bekræftelse af de tidligere HARPS-udsving. De lokale billeder viser, at baggrundsvinduerne indeholder tydelig absorptionsstruktur, som påvirker polynomierne.

**0 kvalificerede lasersignaler. Alle tre tidligere fysiske oprindelser forbliver uafklarede.** Resultatet er et reproducerbart første regnskab på nye arkivinput fra et andet instrument. Der er endnu ingen valideret fysisk signalmodel, støjkovarians, FAP eller stjernerestframe-sammenligning.

## D067: faste input og integritet

Udgangspunktet er D066's fem entydige raw-/produktidentiteter og allerede gemte DataLink-relationer. Før den første filhentning låses alle15URLs, filgrænser, to samtidige downloads, én anmodning per fil, parser-/auditkode og identitetskontroller. Alle fem pipelinearkiver tages med som den samme deterministiske tilføjelse til hvert par. Der vælges ikke efter SNR, kontrast, ekstraktion eller udseende.

Samtlige15anmodninger lykkedes medHTTP200; de modtagne længder matcher alle de gemte DataLink-længder. Præcise transportbytes ogSHA256 er bevaret. Råfilerne er komprimeret med Unixcompress og dekodes midlertidigt til kontrol. Ingen råfil eller spektralfil omskrives. De ti FITS-filer indeholder i alt15HDUs; **alle30 CHECKSUM-/DATASUM-kontroller består**. Den uafhængige efterregning bruger en anden implementering af byte-summerne. Omkringliggende whitespace i en numeriskDATASUM tolkes numerisk, mens de oprindelige filbytes bevares.

Instrument, målalias, targetkoordinater, observationstider ogPROV1 i de modtagne filer stemmer med D066. Det tidligere RA/DEC-afvigelsesflag og de særskilte targetfelter bevares. Kroppenes checksums og headeridentitet understøtter de valgte input; faktisk fiber-/komponentbelysning er stadig ikke fysisk bevist.

Pipelinearkiverne er kontrolleret for gzip-/TAR-integritet og sikre medlemsstier. Der er **860medlemsposter** i alt; alle filnavne og størrelser er gemt. Ingen medlemspixels eller råCCD-billedarrays er analyseret i inputfasen. De komplette arkiver bevares til en senere kontrollen af ekstraktioner og ordener.

## Bølgelængde og fejlkolonne

De modtagne spektralheaders angiver **SPECSYS=BARYCENT**, **TUCD1=em.wl;obs.atmos** og **TUNIT1=angstrom**. WAVE anvendes derfor som barycentrisk luftbølgelængde. Den allerede anvendte observatørkorrektion lægges ikke til igen, og der foretages ingen gættet stjernerestframe-flytning.

ESO's FEROS-releasebeskrivelse oplyser, atERR er en NaN-pladsholder, at de sammensatte spektre er omprøvede, og at barycentrisk korrektion har kendte præcisionsbegrænsninger. De faktisk læste femERR-arrays har ingen endelige værdier. ERR bruges derfor ikke som usikkerhed, og SNR-headerværdien bruges ikke til valg eller signifikans. De tilhørende pipelinefiler bevarer ekstraktions-/ordenskontekst til videre kontrol. [ESO: FEROS-releasebeskrivelse](https://www.eso.org/rm/api/v1/public/releaseDescriptions/94).

Fluksen er produktets egne skalerede, ukalibrerede enheder. Koden bruger feltnavnetADU efterTUNIT2, men tal er ikke en fælles fotometrisk skala på tværs af instrumenter. Kun brøker af det enkelte FEROS-profilvindues egen tilpassede baggrund sammenlignes her.

## D068: samme15profiler og alle faste alternativer

Metode, kode og audit er låst før den første læsning af FEROS'WAVE-/FLUX-arrays. De gamle kandidaters `original_center_air_bary_A` læses direkte fra D066's fulde state; de oprindelige tekstværdier og hash er gemt. Der er fem spektre gange tre positioner, hver med alle gemte samples inden for±5Å. Arkivproduktets eget omprøvede1D-grid beholdes numerisk eksakt; der oprettes intet nyt bølgelængdenet. »Native samples« i tabellerne betyder dette gemte produktgrid, ikke råCCD-pixels.

Tre faste ankre er med: NEAREST, FLOOR ogCEIL i bølgelængde. Der findes ikke nye peaks eller tilpassede forskydninger. Duplicerede ankre beholdes. Baggrunden tilpasses med lineære og kvadratiske polynomier i tre fastlagte symmetriske bånd:0.5–1Å,1–2Å og2–3Å fra det enkelte sampleanker. Der klippes ikke i flux, referencer eller residualer.

Den primære kombination er på forhånd NEAREST og lineær baggrund på±1–2Å. For hvert tilfælde gemmes signerede3-,5- og15-samplesummer samt brøken af baggrundssummen i samme samples. Alle **270tilfælde og810summer** er beregnet; ingen støtte mangler. Der er180forskellige native casekombinationer, fordi nogle ankre genbruger de samme samples. Modellerne genbruger data og udgør ikke270uafhængige forsøg.

Den lokale sidebånds-MAD gemmes som en beskrivende skala for blandingen af linjestruktur, reduktionsafvigelser og støj. Den er ikke certificeret stokastisk støj eller et sigma-estimat.

### Resultater ved de tre steder

Den signerede3-samplebrøk er summen af flux minus polynomium, divideret med det samme polynomiums samlede flux i de tre samples. Positivt betyder over den valgte lokale model. Intervallerne nedenfor er metode-/datointervaller, ikke konfidensgrænser eller detektionsgrænser.

| Kendt position | Barycentrisk luft, Å | Primærkombination, fem datoer | Alle faste ankre/baggrunde, fem datoer |
| --- | ---: | ---: | ---: |
| D002-0061 | 6550.0950 | +1.655 til +2.409 % | -5.854 til +6.242 % |
| D002-0063 | 4826.6475 | +14.984 til +18.444 % | -13.450 til +40.046 % |
| D002-0071 | 5730.7150 | +9.362 til +13.180 % | -6.401 til +22.174 % |

Primærkombinationen for hver dato:

| Dato2019 | 0061,6550.095Å | 0063,4826.6475Å | 0071,5730.715Å |
| --- | ---: | ---: | ---: |
| 2019-11-04 | +2.284 % | +17.613 % | +9.362 % |
| 2019-11-07 | +2.346 % | +17.446 % | +11.142 % |
| 2019-11-08 | +1.655 % | +16.314 % | +10.097 % |
| 2019-11-10 | +2.288 % | +14.984 % | +13.180 % |
| 2019-11-14 | +2.409 % | +18.444 % | +11.162 % |

Ved0061 er66af90tilfælde positive, ved0063 er75af90positive og ved0071 er66af90positive. Disse andele er beskrivende og er ikke signal-sandsynligheder eller gentagne detektioner. Alle tre intervaller over de fastlagte alternativer rummer både positive og negative tal. Den negative fortegnsgren skjules ikke, og der vælges ikke en efterfølgende »bedste« baggrund.

Figurerne viser hele de lokale1D-forløb, kernesamples med alle seks baggrunde samt alle270kontraster fordelt på dato, anker og baggrund. Et synligt afvigende sample nær−0.5Å iF5/0071 bevares; det fjernes ikke og promoveres ikke til en ny kandidat i denne målrettede analyse. Ingen bestemt fysisk årsag til samples eller modelafvigelser tildeles.

## Efterregning og databevaring

Begge numeriske audits består. D067 efterregner387,225,961transportbytes, alle15HDUs,30checksums og860arkivposter. D068 kontrollerer15profiler og15,000gemte numeriske profilværdier mod de faktiske FITS-arrays, inklusive de bevaredeNaN-fejlkolonner. Ankre og masker dannes separat, og polynomier og summer efterregnes medQR og `math.fsum` mod produktionens least squares og lineære operatorer. Største uafhængige sumforskel er **2.91e-16produkt-fluxenheder**. Alle810sumchecks består.

Begge audits er genkørt i rækkefølge med kanoniske auditkvitteringer bevaret byte for byte. Det er interne separate beregninger udført af samme assistent, ikke ekstern fagfællebedømmelse. Ingen fysisk støjmodel, laserrespons eller falsk-alarmrate kalibreres af disse checks.

Alle **91.441tidligere tabelceller** bevares eksakt i de samme37+141rækker. Hver fase tilføjer otte kolonner; nu **94.289celler**. Den gamle0061-rho-fejl, blåCOMB-mangel,6.marts' sekundære status og alle tidligere oprindelsesvurderinger er uændrede. De tre tidligere aktive rodpegere er gemt eksakt iD067/FROZEN_PARENT.

Alle gamle videnskabelige hovedarkivmedlemmer bevares med identiske dekomprimerede bytes. For at holde projektet under filstørrelsesgrænsen anvendes tabsfriZIP-bzip2-kompression på én eksisterende katalog-JSON; indhold ogSHA256 ændres ikke. Øvrige gamle medlemmer bevares indholdseksakt. Kompressionskontrollen og fuld medlemsbevaring er dokumenteret separat. Python-standardbibliotekets `zipfile` understøtter beggeZIP-kompressionsmetoder.

Resultatpakken indeholder alle15modtagne inputfiler, pipelinearkiverne, headers/inventarer, alleprofiler/operatorer/tabeller, fulde state-tabeller, metoder, kode, audits og de tre figurer. Den eksterne releasebeskrivelse refereres medURL ogSHA256; den omfordeles ikke. Direkte ældre input uden for hovedarkivet medtages uændret. Se REPRODUCTION og EVIDENCE_MANIFEST.

## Fortsættelse og begrænsning

D069 foreslås som en særskilt låst gennemgang af de eksisterende pipelinefilers formater, ekstraktionsmåder og individuelle ordener ved alle fem datoer og tre steder. Den skal skelne standard-, optimum- og kosmisk-stråle-behandling, fladfeltning og ordensoverlap samt verificere hver fils egen WCS/bølgelængderamme. RED-/REB-ordener kan allerede være omprøvede og må ikke uden kontrol kaldes rådetektorprofiler. D069 er endnu ikke låst eller udført.

De nye data er fra2019; de tidligere hændelser er fra2021. Der er ingen samtidig bekræftelse, valideret stjernerestframe-registrering eller fysisk persistensudelukkelse. Analysen gælder de tre kendte positioner; der er ikke udført en fuld ny spektralsøgning. Alle tre oprindelser forbliver uafklarede,0 kvalificerede lasersignaler og ingen kalibreretFAP. Den gamle141råkø er lukket,90-/Rubinspor stoppet og offentlig upload udskudt. Ingen udgifter, eksterne personkontakter eller baggrundsberegninger.
