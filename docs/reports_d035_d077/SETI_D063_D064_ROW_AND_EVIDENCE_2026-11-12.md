# SETI D063–D064: native rækker og evidensen for tre udsving

**12. november 2026.** Grundlag: projektversion **56**, SHA256 `e7329ef9fee9d68e5400b87a5cfebf6918555e227065f9ac351dd634550387b4`. Alle tre kilder er observationer af HD 43629. Der er ikke hentet nye observationer eller foretaget nye arkivforespørgsler i disse to faser.

## Resultat

D063 forklarer præcist, hvorfor det målte ydre bidrag til det blå udsving ændres så meget mellem to allerede fastlagte tre-samplevinduer: det kraftige nabosample **k2573** indgår i NEAREST-vinduet, men falder udenfor CEIL-vinduet. Udskiftningen med k2576 ændrer den signerede ydre kontrast med **−5.384 til −5.375 tusind ADU**. Den nye baggrundstilpasning bidrager samtidig med **−17.690 til +234.580 ADU**. Dette er et regnskab over vinduesforskellen, ikke en fysisk forklaring på nabosamplet.

D064 samler evidens og datamangler for alle tre kilder. Den peger på uafhængige instrumentdata som næste informationsbehov. Flere valgfrie varianter på de samme optiske eksponeringer sættes derfor på pause. **Alle tre fysiske oprindelser er uafklarede; ingen kilde kvalificerer endnu som lasersignal.**

## De tre kilder

Bølgelængderne er de tidligere kendte positioner i barycentrisk luft. Kontrastslots genbruger modeller, baggrunde og pixels; de er ikke uafhængige observationer eller forsøg.

| Kilde | Originaldato, UTC | Bølgelængde | Understøttet evidens | Afgørende begrænsning |
| --- | --- | ---: | --- | --- |
| D002-0061 | 5. marts 2021 | 6550.095 Å | Alle 72 fastlagte tidskontraster mod tre kontroller er positive; betinget afvigelse fra egen COMB-profil. | Den oprindelige kvalitetskontrol fejler stadig: rho=0.7806562435869904<0.8. Stjerne-/laseroverførsel og fuld støjkovarians er uvaliderede. |
| D002-0063 | 9. marts 2021 | 4826.6475 Å | Alle 1.152 fastlagte udtrækskontraster mod fire kontroller er positive. Rumlig afvigelse og stort ydre nabosamplebidrag. | Den ydre brøk afhænger stærkt af det konkrete tre-samplevindue. Blå COMB-respons og lampens overførsel til en laser er uvaliderede. |
| D002-0071 | 9. september 2021 | 5730.715 Å | Alle 48 fastlagte tidskontraster mod to septemberkontroller er positive. Egen rumlig rest-RMS 60.93–65.25 ADU, 4.86–5.58 gange egen referencemedian. | Rumlige referencer og efterkontrol har afvigelser. Laserrespons, støjkovarians, FAP og persistensudelukkelse er uvaliderede. |

6. marts er fortsat sekundær kontrol med selectorafvigelse, både i den røde og blå sammenligning. Den rå/native blå korrelation på omkring 0.533 og kontrolafvigelsen bevares. Overskud i originalen i forhold til kontroller viser en lokal forskel ved disse tidspunkter; det udelukker ikke en vedvarende fysisk kilde og påviser ikke en kunstig årsag.

For 0061 ligger det tidligere betingede profil-R over 0.3198–0.5552 mod en langt mindre kalibreringsværdi. Instrumentbelysning, intensitet og støj er ikke valideret overført til en stjerne eller laser. For 0063 er egen rumlig rest-RMS 182.82–188.52 ADU og central/egen referencemedian 19.41–20.89. Disse forhold er **modeldiagnostik, ikke sigma, sandsynligheder eller en rangorden mellem kilderne**. 0061's R og de andre kilders RMS måler forskellige ting.

## D063: alle faste native rækker beholdes

Analysen bruger udelukkende gemte D061-båndkurver. Den fastholder alle fem observationer (original 9. marts og kontroller 3., 4., 5. og 6. marts), rå baggrundssubtraherede data plus alle otte gamle rumlige residualmodeller, fire bånd, fire koordinatvisninger og seks spektrale baggrunde. Båndene er abs(x)≤3, 3<abs(x)≤5, 5<abs(x)≤6 og 6<abs(x)≤7. Det native interval er 2446–2702 i egen blå orden34.

For hver kombination gemmes samtlige 15 rækker fra anker−7 til anker+7. Hver række har en signeret serie og separate serier fra positive og negative pixels. Serien fra positive pixels kan få en negativ spektral residual efter baggrundstilpasning; den må ikke læses som en positiv fysisk energideponering. Alle fortegn og alle baggrunde beholdes.

Der er **4.320 cases, 64.800 native rækker og 194.400 delserie-værdier**. De svarer til 2.160 forskellige native casekombinationer og 6.480 native serie-/fitkombinationer. Samme heltalsanker i flere koordinatvisninger genbruger værdier; dubletterne bevares og tælles ikke som uafhængig evidens. De faste 3-, 5- og 15-samplesummer reproducerer **38.880** gamle D061-statistikker.

Ingen ny peakfinder, interpolation, klipning, tilpasset forskydning, ny rumlig model eller rensning anvendes. Ingen pixel eller række fjernes. Det målrettede regnskab er udført efter, at vinduesforskellen var kendt; det er ikke en blind test eller en ny observation.

### Udskiftning af samples og ændret baggrund

A er NEAREST med anker2574 og tre rækker k2573,2574,2575. B er CEIL med anker2575 og tre rækker k2574,2575,2576. Med resA og resB som de to faste baggrundsresidualer gælder:

- Samplebidrag: resA(k2576)−resA(k2573).
- Baggrundsbidrag: summen af resB−resA over k2574,2575,2576.
- Samlet forskel: B's tre-samplesum minus A's tre-samplesum = samplebidrag + baggrundsbidrag.

Identiteten kontrolleres for alle ni datagrene, fire bånd, seks baggrunde og tre serier: **216 krydsvinduesrækker og 648 delseriechecks**. Følgende tabel viser alle seks baggrunde for rådata; alle tal er signerede ADU. Ydre betyder 3<abs(x)≤7.

| Fast baggrund | Ydre: sampleskift | Ydre: baggrund | Ydre: samlet | Indre≤3: sampleskift | Indre≤3: baggrund |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5_7_affine | -5380.638096 | -17.689827 | -5398.327923 | -139.488799 | -55.757143 |
| 5_7_quadratic | -5374.858790 | 234.580207 | -5140.278583 | -144.955850 | -559.127221 |
| 8_12_affine | -5383.531535 | 15.644682 | -5367.886853 | -117.215563 | 53.600424 |
| 8_12_quadratic | -5383.100715 | 56.197946 | -5326.902769 | -115.091345 | 38.467881 |
| 12_20_affine | -5382.895301 | 1.194410 | -5381.700891 | -98.576298 | 20.133963 |
| 12_20_quadratic | -5383.063410 | 0.904035 | -5382.159376 | -98.253600 | 107.618937 |

Sampleudskiftningen dominerer ændringen i **de ydre bånd**. Konklusionen gælder ikke automatisk det indre bånd: ved ±5–7 kvadratisk er det indre baggrundsbidrag −559.127 ADU mod samplebidrag −144.956 ADU. Begge dele er vist, så en ændret baggrund ikke skjules bag en samlet kurve.

Den tidligere ydre radius3/radius7-brøk på 56.03–60.95 % i det primære vindue og 7.27–9.01 % i CEIL bevares uændret. De beskriver to konkrete signerede tre-samplekontraster, ikke hele hændelsens energi eller positive fotonandele. Vinduerne erstatter ikke hinanden efter resultatet, og den tilbageværende kurve betegnes ikke som et rent lasersignal.

### Lampereferencen forbliver begrænset

D062's ene gamle lampeeksponering med 17 faste features, heraf ni med gamle primærflag, ændres ikke. Primærgruppens indre/radius7-brøker er 0.9669–1.1136 over 54 linje-/baggrundsslots. Signerede brøker kan overstige1 eller være negative. Otte af 408 deklarerede båndslots mangler fortsat støtte; de er ikke udfyldt eller fjernet.

Lampen blev eksponeret cirka284.172 minutter før source. Arvet geometri, belysning, pixelphase, linjeblanding og proveniens begrænser sammenligningen. Den er en lokal reference fra ét billede, ikke en valideret lasersvarfunktion eller en fysisk veto. Blå sciencegeometri er kontrolleret; blå COMB-geometri/respons er fortsat uvalideret, og rød respons overføres ikke.

## D064: sporbar evidens og næste informationsbehov

Syntesen har **34 faktaceller**, hver bundet til kildefil, SHA256 og eksplicit JSON-selector eller kandidatnøglet CSV-celle. To afledte intervaller bruger præcis de otte deklarerede source/NEAREST-poster. `GROUNDED_FACTS`, `EVIDENCE_MATRIX3` og `INFORMATION_GAPS3` indeholder tallene og deres kilder. Der er ingen nye fits, simuleringer, pixels, arkiv- eller litteraturforespørgsler i D064.

Den næste prioritet er en **metadataoversigt for HD43629 fra uafhængige instrumenter**, med ESPRESSO og UVES som første kandidattags. Det er en arbejdsprioritering ud fra informationsmanglerne, ikke en sandsynlighedsrangering af signalerne. **Eksistensen af egnede observationer er endnu ikke verificeret.**

Før arkivsøgningen skal kanonisk identitet, aliaser og astrometri opløses i et autoritativt primærkatalog. Gamle teleskoppegninger må ikke uden videre bruges som kanoniske stjernekoordinater. Aktuel officiel arkiv-/skemadokumentation skal læses, og begrænsede forespørgsler samt identitetsregler fastlægges før resultaterne. Nulresultater, fejl, tvetydige identiteter og dækningsbegrænsninger skal gemmes. Der vælges ikke efter SNR eller ønsket udfald.

Dette næste D065-arbejde er **foreslået, endnu ikke metodisk låst eller udført**. Planen medfører ingen automatisk rådatahentning; ny rådataanalyse kræver en separat forudgående metode og inputkontrol. Flere valgfrie varianter på de samme optiske eksponeringer er sat på pause, mens ny information prioriteres.

## Verifikation og bevaring

Begge afsluttede audits består. D063 efterregner med manuelt polynomiedesign, QR og `math.fsum` mod produktionens SVD/NumPy-beregning. Alle64.800 CSV-rækker serialiserer deres gemte arrays eksakt. Største sumforskel mod QR og gamle D061-summer er **1.36e-11 ADU**, langt under den på forhånd fastlagte tolerance1e−8 ADU. Største uafhængige krydsvindues-lukningsfejl er **5.58e-13 ADU**.

D064 efterregner alle34 faktaceller, to filtrerede intervaller samt tre evidens- og mangelrækker. Den oprindelige0061-rho-fejl, de tre uafklarede oprindelser,0 kvalificerede signaler og manglende FAP bevares. Audits er separate beregninger udført af samme assistent, ikke ekstern fagfællebedømmelse. Genkørsel af begge audits er afprøvet og lader de kanoniske auditkvitteringer byte-identiske.

Alle **85.745 tidligere tabelceller** bevares eksakt i de samme37+141rækker. D063 og D064 tilføjer otte kolonner hver; nu **88.593 celler**. De mellemliggende og endelige fulde tabeller gemmes. Alle gamle videnskabelige hovedarkivmedlemmer bevares byte for byte. De tre tidligere aktive rodpegere er gemt eksakt i D063/FROZEN_PARENT; nye kortere rodpegere peger på den fulde rapport og resultatpakke.

Fire endelige figurer er visuelt kontrolleret: alle native sourcerækker i fire bånd og to vinduer; alle seks rå baggrundsbidrag for indre/ydre/hele aperturen; alle otte residualmodeller plus rådata; samt samtlige fem observationers faste radius7-rækker. Aksernes egne ADU-skalaer og 6. marts' sekundære status er synlige.

Resultatpakken indeholder begge faser, kode, metode-/inputlåse, arrays, samtlige nye tabeller, faktaproveniens, audits, fuld state og figurer. Alle direkte input til de to nye audits, som mangler i hovedarkivet, medtages uændret. Se `REPRODUCTION.md`, `REPRODUCTION_CHECK.json` og `EVIDENCE_MANIFEST.json`. Tidligere fasehistorik og auditbegrænsninger ændres ikke.

Ingen kalibreret FAP, fysisk kovarians, lasersvarfunktion, persistensudelukkelse eller bestemt fysisk årsag etableres. Den gamle141kø forbliver lukket,90-/Rubinspor stoppet, offentlig upload udskudt. Ingen udgifter, eksterne kontakter eller baggrundsberegninger.
