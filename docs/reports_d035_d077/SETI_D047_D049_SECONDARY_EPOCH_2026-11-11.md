# SETI D047–D049: lysvej og sekundær kontrol fra 6. marts

**11. november 2026.** Alle observationstider er UTC. Grundlaget er gemt projektversion 49, SHA256 `685f89deceea2a11fe1315a5eaa44c2436a811fe8125da71a631ceaaee9b1801`.

## Resultat

Optagelsen af HD 43629 fra **6. marts 2021 kl. 01:16:40.899** er nu analyseret som en på forhånd defineret **sekundær kontrol med afvigende selectorfelter**. Dens faste kontinuumsnormalisering er **1.020966315557** gange originalens, og den består de uændrede geometri- og intensitetskrav. Det signerede lokale 3-sampleoverskud er mindre end i originalen fra 5. marts i alle seks baggrundsmodeller og alle 24 deklarerede sammenligningsslots.

I den primære barycentriske NEAREST-visning spænder det signerede normaliserede kontrol/original-forhold fra **-40.53 % til 22.32 %**. Det største positive tal blandt de seks baggrundsvalg er 22.32 %. Det er **en beskrivende modelvariation, ikke en statistisk øvre grænse eller laserstyrkegrænse**.

Den oprindelige D044-afvigelse består: optagelsen er ikke omklassificeret til gruppen med identiske headerfelter. **Den fysiske årsag er fortsat uafklaret. Kvalificerede lasersignaler: 0.**

## D047: hvad selectorafvigelsen betyder

De tre allerede gemte råheaders er sammenlignet på 39 felter, i alt 117 feltceller. De eneste afvigelser mellem 5. og 6. marts i dette udvalg er ID, navn og nummer for de to lampeselectorer. Originalen og 4. marts er ens på alle de udvalgte felter.

| Egen headeroplysning | Original, 5. marts | Kontrol, 4. marts | Sekundær, 6. marts |
| --- | --- | --- | --- |
| DPR TYPE | STAR,SKY,K3 | STAR,SKY,K3 | STAR,SKY,K3 |
| INS MODE | HARPS | HARPS | HARPS |
| MIRR1 NAME | NONE | NONE | NONE |
| OPTI4 NAME, iodinecelle | OUT | OUT | OUT |
| OPTI5 NAME, A-selector | NONE | NONE | TUN1 |
| OPTI6 NAME, B-selector | FP | FP | TUN1 |
| OPTI7 NAME, polarimeter | OUT | OUT | OUT |
| LAMP1 ST, faktisk tænd/sluk | mangler | mangler | mangler |

[Templateguiden fra 2. marts 2006](https://www.eso.org/sci/facilities/lasilla/instruments/harps/doc/manual/3M6-TRE-HAR-33110-0008_v4.pdf) beskriver separate lampeselectorer, lampestrøm og kalibreringsspejl. `objAB` har nominelt stjerne i A, himmel i B og MIRR1=NONE. Den faste `objAB`-reference angiver ikke OPTI5/6. Dens tabel 2.2 viser dog NONE/NONE i den kanoniske teleskop/teleskop-række; ingen af vores tre fulde selectorpar matcher den række bogstaveligt.

[Brugermanualen, udgave 2.4 fra 15. august 2019](https://www.eso.org/sci/facilities/lasilla/instruments/harps/doc/manual/HARPS-UserManual2.4.pdf), tabel 5.1, angiver også stjerne/himmel for `objAB`. [ESO's manualoversigt](https://www.eso.org/sci/facilities/lasilla/instruments/harps/doc.html) placerer denne udgave fra periode 104 til mindst 109.

**Vores fortolkning:** den nominelle STAR/SKY-lysvej har dokumentationsstøtte. Et selectorvalg er ikke i sig selv en måling af lampestrøm eller af lys, der faktisk når fiberen. En forklaring med uvirksomme selectorpositioner er understøttet som fortolkning, men fuldstændig identisk belysning i 2021 og fravær af strølys er ikke bevist. Det manglende LAMP1-felt er bevaret som ukendt, ikke sat til OFF. Det begrunder en afgrænset sekundær sammenligning, mens D044's eksakte feltkrav og udfald forbliver uændret.

### Dokumentkontrol

Gennemgangen var fastlagt før nye web-/dokumentopslag: fire søgeforespørgsler og fire forskellige primære dokumenter. Webtjenestens første PDF-skærmbilleder gav kun tekstmarkører. En dokumenteret amendment tillod derfor én direkte hentning af hver af de to allerede udvalgte PDF'er for at kontrollere tabellernes kolonner visuelt. Ingen ekstra søgning eller ændring af fortolkningskriterierne fulgte af dette.

De to PDF'er udgør 2,768,744 bytes. SHA256 er henholdsvis `647730391a1b2727d1654f676ce1eccd3fa6e9914939cd4bdb821ff1fbf4bc22` og `251d197383cc902d6890c8a13ee76bdc7a9c13ad17915589e3c5438682cdf91f`. PDF-sider 16, 22 og 47 i templateguiden samt side 35 i 2019-manualen blev gennemgået som faktiske lokale gengivelser. Versioner, præcise sider og normaliserede fakta er registreret i DOCUMENT_EVIDENCE.json. De fulde manualer og lange rå webudtræk er ikke resultatfiler.

D047 læste ingen nye astronomiske arrays og foretog ingen arkivforespørgsler efter teleskopdata. Det frosne versions-49-rodinput er bevaret i ROOT_BEFORE_D047; PARENT_INPUT_BINDING.json beskriver genafspilning af den tidligere rodpeger i en separat arbejdskopi.

## D048: præcist forhåndsvalgt sekundært input

Arkivprodukt: `ADP.2021-03-07T01:02:15.648`. Råprogenitor: `HARPS.2021-03-06T01:16:40.899`. Der er ikke valgt en erstatningsobservation. Identiteten og de entydige DataLink-forbindelser stammer fra D044 og blev genbrugt uden nye metadataopslag.

En separat adgangslås fastlagde præcis to body-forespørgsler: råfilen på 13,406,441 bytes og dens ancillary-tar på 6,963,200 bytes. Begge lykkedes i første forsøg. Alle 824 tildelte rå-header-værdier er afstemt: 823 eksakt, og én DATASUM-streng med samme værdi 0 men forskellig indledende whitespace. Den allerede kendte repræsentationsregel var fastlagt før body-adgangen. Ingen ny parseramendment eller genhentning var nødvendig.

Egne e2ds-A/B-headers giver 72/71 ordener med 4096 samples og egne observationsdatoer, BERV-, bølgelængde- og tracepolynomier. Ingen fluxarrays blev læst i headerfasen. Der blev ikke hentet noget nyt 1D-spektrumprodukt.

## D049: fast metode før nye pixels

Den kendte barycentriske luftbølgelængde er fortsat **6550.095 Å**. Der bruges egen observeret-luft-polynomium ganget med `(1 + BERV / c)`, hvor `c=299792.458 km/s`. Ingen intrinsisk stjerne-RV, luft/vakuum-konvertering, tilpasset forskydning eller spektral resampling indføres.

Kontrollens BERV er **−22.5045648786894 km/s** og dens beregnede fraktionelle native-position **421.657807812719**. NEAREST er 422, FLOOR 421 og CEIL 422. Detektorvisningen fastholder 421. Originalens gemte ankre er 421 for detektor/NEAREST/FLOOR og 422 for CEIL.

Udtrækning, referencemasker og statistik genbruger D046-algoritmerne. De kodemæssige forskelle, inputidentitet og den særskilte sekundære gruppe er bevaret i ALGORITHM_REUSE.json og de to forskelsfiler. Metoden og auditkoden er låst før kontrollens første nye arrayadgang. D046-resultaterne og den tidligere udvalgte original var allerede kendt; dette er en målrettet sammenligning, ikke en blind opdagelsestest.

Alle native-indekser **293–549** bevares. Rå række er 4095−k, rumlig trace er kontrollens egen A-orden 67, radius-3-summen er signeret, og den robuste rumlige baggrund bruger alle på forhånd definerede referencepixels væk fra alle egne A/B-traces. Medianen uden for `abs(k−421)≤20` normaliserer hvert spektrum.

| Kvalitets-/normaliseringsmål | Resultat |
| --- | ---: |
| Originalens faste median | 3666.929769392033 ADU |
| Kontrollens faste median | 3743.811776061776 ADU |
| Kontrol/original | 1.020966315557 |
| Positive radius-6-rækker uden for central 41 | 216 af 216 |
| Medianprofilens maksimum | 0.0 pixel fra egen trace |
| Uændrede geometri-/intensitetskrav | består, inden for ±1.5 pixel og [0.5,2] |
| Egen lokal rå/native-korrelation | 0.989805055956 |
| D044-gruppe med identiske selectorfelter | fortsat **false** |

Den nye lokale korrelation ændrer ikke originalens historiske fejlede `rho=0.780656<0.8`-krav. Kontrollens lampeside-usikkerhed og uvaliderede faktiske belysning bliver stående.

## Alle fastlagte kontraster

De seks baggrunde er affine og kvadratiske polynomier på symmetriske sidebånd ±5..7, ±8..12 og ±12..20 native samples. De primære signerede residualsummer omfatter anker−1, anker, anker+1; også 5- og 15-samplesummer bevares. Det diagnostiske maksimum i ±2 må ikke flytte ankeret eller udvælge en model.

| Visning / regel | Kontrolanker | Kontrol-3sum, ADU | Signeret normaliseret kontrol/original-3sum | Original minus kontrol positiv i alle 6? |
| --- | ---: | ---: | ---: | --- |
| DETECTOR_NATIVE / FIXED_K421 | 421 | -377.221689 til +428.551176 | -0.315908 til +0.443870 | ja |
| BARYCENTRIC_AIR / NEAREST | 422 | -483.969167 til +215.494608 | -0.405305 til +0.223198 | ja |
| BARYCENTRIC_AIR / FLOOR | 421 | -377.221689 til +428.551176 | -0.315908 til +0.443870 | ja |
| BARYCENTRIC_AIR / CEIL | 422 | -483.969167 til +215.494608 | -0.411806 til +0.225595 | ja |

Der er **24 kontrolcase-slots, 12 forskellige kontroltilpasninger og 18 forskellige kilde/kontrol-par** i de 24 parslots. Detektor og FLOOR dublerer samme par. NEAREST og CEIL deler kontrolanker, men bruger forskelligt originalanker og er derfor forskellige par. Ingen dubletter er fjernet eller talt som ekstra uafhængig evidens.

De negative tal er negative lokale residualer for bestemte baggrundsvalg, ikke negativ fysisk luminositet. Summersammenligningen er ikke en fælles præcis bølgelængdeintegral, ækvivalentbredde eller kalibreret statistisk test. Ingen FAP, p-værdi, duty cycle, persistensudelukkelse eller bestemt fysisk årsag tildeles.

## Uafhængig verifikation og faktisk arrayadgang

**Audit: PASS.** De 16,705 lokale råpixels, 25,700 overscanpixels og 257 bevarede native-A-samples er reproduceret eksakt. En separat skalær rumlig baggrund giver største r3-afvigelse 9.09e-13 ADU. En 60-cifret Decimal-inversion af bølgelængden afviger 1.46e-11 pixel.

72 kontrolsummer og 72 genbrugte originalsummer er kontrolleret med QR mod produktionens least squares. 72 lineære kontrastoperatorer reproducerer summerne og annihilerer deres baggrundspolynomier. Største kontrolsumafvigelser er 1.91e-11 ADU ved QR og 2.14e-11 ADU ved operatorerne. Største afvigelse i de signerede forhold er 5.32e-15.

FITS-læsningen dekodede hele CCD2-arrayet på 8,798,208 pixels og det native-A-array på 72×4096=294,912 samples, hvorefter kun det fastlagte vindue blev analyseret/bevaret. Blå CCD-array, native-B-flux og CCF-arrays er ikke læst. Ingen nye Monte Carlo-træk eller ekstra dataforespørgsler er foretaget i D049. Alle tre endelige figurer er visuelt gennemgået.

## Bevaring og fortsættelse

Alle **62,961 tidligere tabelceller** er bevaret eksakt. Tre faser tilføjer hver otte kolonner til de samme 37+141 rækker; nu i alt **67,233 celler**. D044's tidligere eksakte selectorafvigelse og D046's daværende status er historiske resultater og er ikke overskrevet. Den aktive rodpeger angiver nu korrekt, at 6. marts er analyseret som sekundær kontrol. Alle tidligere videnskabelige arkivmedlemmer bevares; kun rodens tre pegefiler opdateres, med eksakte forgængere bevaret.

D002-0061's gamle kvalitetsfejl og D002-0063's blå status består. Alle tre oprindelige fysiske årsager er uafklarede; 0 kvalificerede lasersignaler. Ingen valideret stjerneramme, belysningsækvivalens, fysisk kovarians, kalibreret FAP eller blå/rød COMB-overførsel udledes. D039–D046-resultater ændres ikke. Den gamle 141-kø er lukket; de gamle 90-/Rubinspor er stoppet. Offentlig upload er fortsat udskudt. Ingen udgifter, eksterne kontakter eller baggrundsberegninger.

Næste foreslåede trin, D050, er en fastlagt evidensoversigt over de allerede analyserede 4., 5., 6. og 9. marts med gruppemærker og alle baggrundsvalg, efterfulgt af prioritering af den næste konkrete uafklarede opgave. Der er ikke her lavet et nyt samlet fire-epoke-fit eller en hypoteseprøve. D050 er ikke udført eller låst endnu.

Udpak den nye resultatpakke sammen med hovedprojektet. Resultatpakken bevarer den nye råfil/ancillary, alle egne headers, alle nye arrays og operatorer, 24 cases/par, tabeller, metoder, audits og tre fulde figurer. Det kompakte hovedprojekt peger på den nødvendige resultatpakke; de nye binære analysearrays og fulde figurer ligger dér. Dokumentationens URL'er, versioner, SHA256 og præcise sider er registreret; fulde primærmanualer er tilgængelige via de officielle links ovenfor.
