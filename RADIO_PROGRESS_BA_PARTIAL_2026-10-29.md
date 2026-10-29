# SETI · delvist BA-kontrolpunkt · 29. oktober 2026

**Den delvise AZ-pakke og det tidligere blokerede metadata-interval er gendannet. Den efterfølgende rådatahentning stoppede ved en lokal kontrol af datalinjen og er fortsat ufuldstændig.** Ingen ny gennemført SETI-søgning eller kandidatvurdering er etableret af denne genopretning.

## Seneste afsluttede videnskabelige status

Den seneste publicerede GitHub-status stod ved 20. oktober. Den gemte afsluttede AY-status fra 28. oktober angiver **480 unikke arkiv-ID'er, 265,594482421875 tekniske MHz-besøg og 0 accepterede SETI-kandidater**. Disse er arvede historiske tællinger; denne offentliggørelse efterprøver ikke alle tidligere søgninger på ny. Uafklarede tidligere sager bevarer deres dispositioner.

AY omfatter HIP92270, besøg 65085, med den oprindeligt fastlagte metode og arkivdata fra 29. september 2016. Den gemte status bevarer også et oprindeligt fejlet dokumentkontrolforløb og en særskilt dokumenteret, deterministisk gendannelse af en afkortet log før kontrolversion V2. Loggendannelsen var ingen ny videnskabelig søgning. Detaljer og kildeidentiteter fremgår af [publiceringsevidensen](results/radio_ba_partial_20261029/PUBLIC_EVIDENCE.json).

MHz-besøg er teknisk bogføring af behandlede bånd pr. besøg. Tallet er ikke sammenhængende unik frekvensdækning, antal uafhængige mål eller en kalibreret astronomisk følsomhed. Antallet af arkiv-ID'er er heller ikke antallet af uafhængige stjerner eller bekræftende epoker.

## AZ og BA: hvad der faktisk er gennemført

AZ for HIP92283, besøg 65097, stoppede 28. oktober med en tunnel-fejl 403. Tre af de seks nødvendige scan-udsnit var komplette: 48 af 96 rådata-rækker. Alle seks filhoveder og en på forhånd fastlagt prepower-plan var bevaret. Der blev ikke kørt SETI-søgning, ON/OFF-triage eller kandidatopfølgning for AZ. Det ufuldstændige besøg er derfor intet analyseret nulresultat.

BA gendannede fem fortsættelses-ZIP-filer og den særskilte lukningspakke med korrekte kontrolsummer. **419 medlemmer med 530.851.276 ukomprimerede bytes** i fortsættelsespakken er verificeret; de fem lukningsmedlemmer er registreret separat. De tre komplette scan-arrays og **115 gemte transportkvitteringer** er kontrolleret uden nye teleskopforespørgsler. Dette verificerer bevaringen af de eksisterende bytes, ikke uafhængigt hele det videnskabelige projekt.

En separat lokal BA-plan blev fastlagt kl. **05:55:49 dansk tid**, og en efterfølgende offline-gennemgang kontrollerede de bundne kilde-/tilstandshashes samt, at det fejlede interval ikke allerede lå i cachen. Planen tillod kun ét GET til præcis samme URL, vært og byteinterval som den oprindelige nul-byte-fejl. Søgeregler, normalisering, tærskler, driftsområde og kandidatgates var uændrede. Ingen omdirigering, alternativ adgangsvej eller automatisk gentagelse var tilladt. Denne GitHub-offentliggørelse sker efter udførelsen; der påstås ingen offentlig forhåndsregistrering.

| Måling i BA-metadataunderfasen | Udfald |
|---|---|
| Arkivfil og scan | 65103, scan 3, HIP91233 som OFF-kontekst til HIP92283 |
| Byteinterval, inklusive endepunkter | 380354560–380370943 |
| Enkeltforsøg | HTTP 206; præcis 16.384 bytes |
| Identitetskontrol | Oprindelig ETag og Content-Range matcher |
| Faktisk procesexit | 0 |
| Nye power-rækker og søgninger | 0 og 0 |
| Ny krediteret dækning | 0 arkiv-ID'er og 0 MHz-besøg |

Metadata-intervallets SHA-256 er `53e3ae720ee023d5d774327663b41985bb4d7261d66f0e060261440e3e226289`. Den bevarede fejl blev ikke omskrevet; det nye vellykkede forsøg har egne plan-, review-, resultat- og proceskvitteringer. Et korrekt metadata-interval etablerer hverken en komplet cadence, hele originalfilens MD5, astronomisk oprindelse, følsomhed eller en kandidat.

## Delvis fortsættelse og præcist næste trin

Dette kontrolpunkt dækker til den dokumenterede procesafslutning **29. oktober kl. 06:04:40 dansk tid**. Eventuelle senere resultater kræver et særskilt dateret tillæg.

Efter den vellykkede metadataanmodning blev der fastlagt og gennemgået en særskilt plan for de 48 manglende rækker i scan 3–5. Den brugte den bevarede cache og tillod kun hentning af manglende byteintervaller med de oprindelige identitetskontroller og uændrede videnskabelige regler. De tre allerede komplette scan-udsnit blev ikke hentet igen.

Den første udførelse registrerede **6 nye rækker, 13 nye forespørgsler og 21.730.775 forespurgte bytes**, men lukkede med **faktisk exitkode 1** før nogen ny scan var komplet. Fejlen var `Selected chunk must match exactly one new receipt`.

Den valgte komprimerede chunk for række 6 overlappede et allerede bevaret metadata-interval på 16.384 bytes. Transportlaget hentede kun den manglende del, som cachepolitikken krævede. Den efterfølgende lokale kontrol krævede imidlertid, at hele chunken svarede til præcis én ny HTTP-206-kvittering. Det krav kunne ikke opfyldes af den sammensatte lokale bytekæde. Dette er en dokumenteret engineeringfejl i grænsefladen for proveniens; det vellykkede nye netværkssvar omskriver ikke den fejlede proces til bestået.

**V2-korrektionen af rådatahentningen er afventende ved dette kontrolpunkt.** Den skal fastlåses og gennemgås særskilt og bevare en eksplicit forbindelse fra hvert lokalt sammensat payload til de faktiske cache- og netværkssegmenter. Et sammensat lokalt payload må ikke udgives som én HTTP-206-response. Den oprindelige fejl, dens kilder, log og proceskvittering bevares. Her påstås ingen vellykket V2-kørsel, fuldført seks-scan-inddata, bestået numerisk QA eller ny krediteret dækning.

Næste kilde er fortsat HIP92283, besøg 65097. Det konkrete næste trin er den prospektive V2-korrektion og kontrol af den uafsluttede erhvervelse, før en eventuel særskilt frigivelse af den uændrede søgekæde. De 6 rækker fra det fejlede forsøg er ingen afsluttet inddata-kontrol, søgning eller nulresultat.

[Fejl, faktisk procesexit og eksplicit afgrænsning](results/radio_ba_partial_20261029/ACQUISITION_FAILURE_PUBLIC.json).


## Evidens og bevarede begrænsninger

[Publiceringsevidens](results/radio_ba_partial_20261029/PUBLIC_EVIDENCE.json) · [Gendannelseskontrol](results/radio_ba_partial_20261029/RESTORE_AUDIT_PUBLIC.json) · [Cache-tilstand](results/radio_ba_partial_20261029/CACHED_STATE_PUBLIC.json) · [BA-plan](results/radio_ba_partial_20261029/RECOVERY_PROTOCOL_PUBLIC.json) · [Forudgående review](results/radio_ba_partial_20261029/RECOVERY_REVIEW_PUBLIC.json) · [Målt BA-resultat](results/radio_ba_partial_20261029/RECOVERY_RESULT_PUBLIC.json) · [SHA-256-kontrolsummer](results/radio_ba_partial_20261029/SHA256SUMS)

De offentlige JSON-filer er udvalgte, saniterede afledninger med de oprindelige artefakters kontrolsummer. Repositoryet publicerer metadata og dokumentation; teleskop-arrays, rå payloads og programmeringskilder fra den nye genopretning er ikke med i denne opdatering. Disse bilag kan ikke alene genskabe hele projektets historiske analyser.

Tidligere kvalifikationsfejl, lukkede banker, HOLD og uafklarede spor bevares uændret. Ingen kalibreret global falskalarmrate, fysisk fluxgrænse eller uafhængig bekræftelse etableres af denne tekniske genopretning.
