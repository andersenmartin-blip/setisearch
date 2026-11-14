# SETI D052–D054: to septemberkontroller ved 5730.715 Å

**11. november 2026.** Grundlag: gemt projektversion 51, SHA256 `1ddd4654a9265643294e82727854a4773ab8126cf052f1ad18b7c11507501314`. Alle observationstider er UTC.

## Resultat

De to på forhånd udpegede observationer af **HD 43629 fra 6. og 18. september 2021** er nu identificeret, hentet og analyseret ved den kendte **5730.715 Å**-position, D002-0071. Originalen er fra 9. september. Begge kontroller består de fastlagte header-, geometri- og intensitetskrav.

Det signerede, kontinuumsnormaliserede lokale **3-sampleoverskud i originalen er større end i begge kontroller i alle 48 deklarerede parslots**. I den primære barycentriske NEAREST-visning spænder kontrol/original-forholdene over de seks baggrundsvalg fra **−0.467707 til −0.018332** før originalen og **+0.006487 til +0.219210** efter den. De er beskrivende resultater, ikke konfidensintervaller, laserstyrkegrænser eller uafhængige statistiske forsøg.

Den nye kontrol viser en forskel mellem de undersøgte datoer under den fastlagte metode. Den identificerer ikke årsagen til originalens smalle udsving og udelukker ikke et vedvarende signal under andre fysiske antagelser. **Fortsat 0 kvalificerede lasersignaler; alle tre oprindelige fysiske årsager er uafklarede.**

## D052: præcis identitet og egne instrumentheaders

Udvælgelsen fra D051 blev fastholdt uden erstatningsdato, nyt katalogvindue eller signalbaseret rangordning. En ny metodelås fastlagde seks metadataforespørgsler: produktheader, DataLink og råheader pr. kandidat, ét forsøg hver. Grænserne var 2,000,000 bytes pr. header, 1,000,000 pr. DataLink og timeout 40 s. Alle seks lykkedes første gang, i alt **583,867 bytes**.

Den faktisk fungerende `hdr?ADP...` / `hdr?HARPS...`-repræsentation og den tidligere afprøvede card-bevarende parser fra D044 blev genbrugt. D044's historiske fejlede URL-varianter er ikke gentaget. Den kendte ORIGFILE-regel klipper kun et udvidet displaykommentarfelt efter den komplette citerede værdi; der skete ingen ny parseramendment.

| Rolle | Produkt-id | Entydig råprogenitor | Egen headerstart, UTC | Eksponering, s | Timer fra originalens eget midtpunkt |
| --- | --- | --- | --- | ---: | ---: |
| BEFORE | `ADP.2021-09-07T01:01:49.355` | `HARPS.2021-09-06T09:29:48.465` | 2021-09-06T09:29:48.465 | 1799.9965 | -71.800487 |
| AFTER | `ADP.2021-09-19T01:08:28.151` | `HARPS.2021-09-18T09:18:51.849` | 2021-09-18T09:18:51.848 | 1799.9965 | +216.017119 |

Originalens rå-id er `HARPS.2021-09-09T09:12:50.220`, egen headerstart **2021-09-09T09:12:50.219**, eksponering **2399.9965 s**. Rå-id og header kan afvige 1 ms; de fastlagte 2 ms-tolerancer består. ADP-id'ets genereringsdato er ikke observationsdatoen. De afrundede katalogeksponeringer på 1799.996 s er holdt adskilt fra kontrolfilernes egne 1799.9965 s.

For hvert produkt blev én rå-PROV, én tilsvarende DataLink-progenitor og én entydig ancillary-tar verificeret. Rå-id'erne er forskellige fra hinanden, originalen og de tidligere verificerede projektidentiteter. Target, koordinater, start, varighed, CCD-former, HDU-tider, BERV og BARYCENT-produktramme består.

Alle **14 deklarerede instrumentfelter** matcher originalens egen råheader: INS MODE, DPR CATG/TECH/TYPE, MIRR1, OPTI4/5/6/7 samt readout-clock/mode/speed og binning X/Y. Blandt andet er A/B-selectorerne NONE/NONE, MIRR1 NONE, iodinecelle OUT og polarimeter OUT. Egne source-nativeheaders bekræfter samme værdier. Manglende lampestrøm/-tilstand står fortsat som ukendt; headerlighed beviser ikke identisk faktisk belysning.

En separat stdlib-parser kontrollerede **7,894 tildelte headerkortværdier** mod produktionsparseren, relationer og tids-/positionsberegning. Audit: PASS. Ingen FITS-bodies eller fluxarrays blev hentet/læst i D052.

## D053: fire faste filhentninger, derefter kun headers

En særskilt adgangslås fastlagde netop de to verificerede råfiler og hver sin ancillary-tar. Fire body-forespørgsler lykkedes i første forsøg, i alt **39,522,078 bytes**. Råfilgrænsen var 25,000,000 bytes, tar-grænsen 12,000,000 og timeout 50 s. Alle annoncerede længder og hashes består. Der blev ikke hentet noget nyt 1D-spektrumprodukt.

BEFORE-råfilen matcher 826 tildelte rå-headerværdier eksakt; AFTER matcher 812. Hver har desuden én DATASUM-streng med uændret numerisk tekst og forskellig indledende whitespace. Den allerede kendte repræsentationsregel var fastlagt inden adgang og er registreret; andre forskelle ville give fejl.

Begge tar-filer indeholder entydige egne e2ds-A/B-medlemmer med henholdsvis 72/71 ordener og 4096 samples. Egne datoer, eksponeringer og BERV matcher råfil/produkt. Hele medlemsmanifestet og hvert udvalgt medlems bytehash er bevaret. Ingen billed- eller fluxarrays blev dekodet i headerfasen.

En uafhængig binær FITS-headerparser efterprøvede **13,830 tildelte værdier**, tar-medlemmer og hashes. Audit: PASS. Begge observationer gik videre uden erstatning eller genhentning.

## D054: fast metode før nye kontrolpixels

Der bruges egen **A-orden 53**, fast detektoranker **2662** og alle native-indekser **2534–2790**. Hver egen trace vurderes ved rå række `4095−k`; den egne CCD2-kolonne er fysisk tracekolonne−2048+50. Rumlige referencer er de på forhånd fastlagte intervaller ±10..14 og ±26..30 pixels, med afstand over 8 pixels til alle egne A/B-traces. Mindst otte referencer og to på hver side kræves.

Den signerede radius-3-apertur bruger den uændrede repeated-median affine rumlige baggrund fra D049; funktionskoden er AST-identisk. **Martsgeometrien ved 6550.095 Å og dens COMB-respons er ikke overført.** Septemberens egne trace- og bølgelængdepolynomier, fase og gain/RON er anvendt. Originalens 257 råpixelrækker, referencemasker, native-A-samples og radius-3-kurve reproducerer D028 **eksakt**; tidligere bredde-/kalibreringsresultater ændres ikke.

Hver kurve normaliseres med sin egen faste median i det 257-samplevindue uden for `abs(k−2662)≤20`. Intensitetskravet for en kontrol er et positivt kontrol/original-medianforhold i [0.5,2]. Begge består, men den senere kontrol ligger tæt på den nedre grænse og har cirka halvt så mange lokale counts som originalen; det er ikke count-identiske observationer.

| Observation | Fast median, ADU | Median/original | Positive radius-6-rækker uden for kerne | Rumlig profilspids, pixel | Beskrivende egen rå/native-korrelation |
| --- | ---: | ---: | ---: | ---: | ---: |
| ORIGINAL | 4254.711206896552 | 1.000000000000 | 216/216 | 0.00 | 0.999412620826 |
| BEFORE | 2749.494154751892 | 0.646223449971 | 216/216 | 0.00 | 0.999320451558 |
| AFTER | 2247.614423076923 | 0.528264860711 | 215/216 | 0.00 | 0.991490594011 |

Geometrikravet er mindst 129 positive rækker og en medianprofilspids inden for ±1.5 pixel. Interpolation bruges kun til denne rumlige kontrol, ikke til spektrene. Korrelationerne ophæver ingen historisk kvalitetsfejl.

Den barycentriske luftkoordinat er egen observeret-luft-polynomium ganget med `(1+BERV/c)`, hvor c=299792.458 km/s. NEAREST er primær; FLOOR/CEIL er fastlagte afrundingsfølsomheder. Ingen tilpasset forskydning, luft/vakuumkonvertering, intrinsisk stjerne-RV eller valideret stjerneramme tilføjes.

| Observation | BERV, km/s | Fraktionelt eget indeks | Detektor | NEAREST | FLOOR | CEIL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ORIGINAL | +22.623619730359 | 2661.807709799961 | 2662 | 2662 | 2661 | 2662 |
| BEFORE | +22.214415875062 | 2662.331286044518 | 2662 | 2662 | 2662 | 2663 |
| AFTER | +23.432241513720 | 2660.771528045435 | 2662 | 2661 | 2660 | 2661 |

Alle affine og kvadratiske baggrunde på symmetriske sidebånd ±5..7, ±8..12 og ±12..20 indgår. Statistikken er signeret sum over anker±1, ±2 og ±7; 3-samplesummen er primær. Det diagnostiske maksimum i ±2 må ikke flytte anker eller udvælge baggrundsmodel.

## Alle fastlagte 3-samplekontraster

| Kontrol | Visning / regel | Original-/kontrolanker | Signeret normaliseret kontrol/original-forhold over alle 6 baggrunde | Original minus kontrol positiv i alle 6? |
| --- | --- | ---: | ---: | --- |
| BEFORE | DETECTOR_NATIVE / FIXED_K2662 | 2662 / 2662 | -0.467707 til -0.018332 | ja |
| BEFORE | BARYCENTRIC_AIR / NEAREST | 2662 / 2662 | -0.467707 til -0.018332 | ja |
| BEFORE | BARYCENTRIC_AIR / FLOOR | 2661 / 2662 | -0.515040 til -0.022323 | ja |
| BEFORE | BARYCENTRIC_AIR / CEIL | 2662 / 2663 | -0.039140 til +0.145808 | ja |
| AFTER | DETECTOR_NATIVE / FIXED_K2662 | 2662 / 2662 | -0.040342 til +0.150986 | ja |
| AFTER | BARYCENTRIC_AIR / NEAREST | 2662 / 2661 | +0.006487 til +0.219210 | ja |
| AFTER | BARYCENTRIC_AIR / FLOOR | 2661 / 2660 | -0.069050 til +0.492198 | ja |
| AFTER | BARYCENTRIC_AIR / CEIL | 2662 / 2661 | +0.006487 til +0.219210 | ja |

**72 case-slots repræsenterer 42 forskellige native-fit; 48 parslots repræsenterer 36 forskellige native-par.** Alle dubletter er bevaret og mærket; de er ikke ekstra uafhængig evidens. Negative forhold er negative lokale residualer for et baggrundsvalg, ikke negativ luminositet. Den fulde FLOOR-følsomhed efter originalen når +49.22 %, selv om den primære NEAREST højst når +21.92 %. Ingen model eller afrunding er udvalgt som vindende efter resultaterne.

Hverken de to kontroldatoer eller de seks baggrundsvalg er poolet til en nulfordeling. Der er ingen FAP, p-værdi, konfidensgrænse, duty cycle, persistensudelukkelse eller bestemt fysisk årsag tildelt.

## Uafhængig verifikation og adgangens omfang

**Audit: PASS.** Alle tre gange 16,705 lokale råpixels, 25,700 overscanpixels og 257 native-A-samples er reproduceret eksakt. En separat skalær rumlig baggrund afviger højst 1.82e-12 ADU. En 60-cifret Decimal-inversion af egen bølgelængde afviger højst 6.28e-11 pixel.

216 QR-summer er kontrolleret mod produktionens least squares, og 216 fulde lineære kontrastoperatorer reproducerer summerne og annihilerer baggrundspolynomierne. Største QR- og operatorafvigelse er henholdsvis 2.46e-11 og 2.27e-11 ADU. Forhold og forskelle afviger højst 4.3e-15 og 7.16e-15. Alle 48 par, 8 grupper og dubletantal er kontrolleret. To endelige figurer er visuelt gennemgået.

FITS-læsningen dekodede hele CCD2 på 8,798,208 pixels og hele native-A-arrayet på 294,912 samples for hver af tre eksisterende arkivobservationer, før de faste vinduer blev udvalgt. To af kontrolkonteksterne er nyanalyserede; source er genudtrukket fra allerede gemte filer. Blå CCD, native-B-flux og CCF-arrays er ikke læst. Ingen nye Monte Carlo-træk eller arkivforespørgsler er foretaget i D054.

## Bevaring og fortsættelse

Alle **70,081 tidligere tabelceller** er bevaret eksakt. Tre faser tilføjer hver otte kolonner til de samme 37+141 rækker; samlet nu **74,353 celler**. D002-0061's historiske `rho=0.7806562435869904<0.8`-fejl, D002-0063's blå status, 6. marts' sekundære selectorgruppe og alle D039–D051-resultater står uændret. Tidligere arkivmedlemmer bevares; de tre aktive rodpegere har eksakte snapshots i D052/ROOT_BEFORE_D052.

Den nye resultatpakke bevarer alle nye råfiler/ancillary, headers, rå metadata, kvitteringer, arrays, operatorer, 72 cases/48 par, tabeller, kode, låse, audits, rapporter og to fulde figurer. Udtræk den under samme projektrod som hovedprojektet. Hovedprojektets kompakte nye indhold og eventuelle companionplacering af mellem-tabeller/metadata er dokumenteret i INCREMENTAL_LAYOUT_POLICY.json. Ingen gamle videnskabelige medlemmer fjernes eller ændres for at tilpasse filstørrelsen.

Næste foreslåede fase, **D055**, bruger de nu målte egne septemberkontroller til en fastlagt rumlig sammenligning og vurdering af, hvilke usikkerhedsudsagn data kan understøtte. Kernen skal holdes ude af skabelontræning, og alle tidligere kilde-/kalibreringsfund genbruges som allerede kendte. Ingen nye datoer eller forespørgsler er nødvendige. Metoden er endnu ikke låst, og D055 er ikke udført.

**0 kvalificerede lasersignaler; alle tre oprindelige årsager er fortsat uafklarede.** Ingen fysisk stjerne/laser-respons, kovarians, belysningsækvivalens eller kalibreret FAP udledes. Den gamle 141-kø er lukket; de gamle 90-/Rubinspor forbliver stoppet. Offentlig upload er fortsat udskudt. Ingen udgifter, eksterne kontakter eller baggrundsberegninger.
