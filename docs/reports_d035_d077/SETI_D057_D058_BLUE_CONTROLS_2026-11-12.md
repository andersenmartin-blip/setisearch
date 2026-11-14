# SETI D057–D058: det blå udsving og fire faste martsobservationer

12. november 2026. Grundlag: gemt projektversion **53**, SHA256 `c1d8ba79f2505f84c14eb9b68abbbc2c97f34d00f16b2e4c65b55e185e5b4e35`. HD 43629, D002-0063, kendt barycentrisk luftbølgelængde **4826.6475 Å**, original **9. marts 2021**; kontroller **3., 4., 5. og 6. marts 2021**. Alle datoer og klokkeslæt er UTC.

## Resultat

Originalens normaliserede lokale overskud er større end kontrollernes i **alle 96 fastlagte parslots**: **72** mod de tre observationer med matchende headerfelter og **24** mod den særskilte sekundære kontrol fra 6. marts. Det svarer til **72 forskellige native-par**, fordi nogle koordinatvisninger genbruger samme pixels. Der er ikke 96 uafhængige hændelser.

I den primære barycentriske NEAREST-sammenligning ligger kontrol/original-forholdene over de seks faste baggrunde mellem **−0.035175 og +0.197990** for de tre kontroller med matchende headerfelter. Kontrollen fra 6. marts ligger mellem **+0.101470 og +0.163735**, men har en særskilt selectorafvigelse og dårligere rå/native-overensstemmelse. Den indgår ikke i hovedgruppen.

Forholdene beskriver signerede, lokalt baggrundssubtraherede 3-samplesummer divideret med hver observations faste median. De er **ikke konfidensgrænser, lysstyrkegrænser, p-værdier eller lasersandsynligheder**. Fysisk årsag er fortsat uafklaret. **0 kvalificerede lasersignaler.**

## D057: identitet, instrumentfelter og egen blå geometri

Alle fem råfiler og egne native A/B-produkter er verificeret mod tidligere gemte bytes og SHA256-hashes. Tre manglende lokale inputpar er gendannet fra de allerede gemte pakker, med seks medlemmers hashes kontrolleret; ingen ny teleskopforespørgsel eller observation er foretaget. RECOVERY_RECEIPT og FROZEN_INPUTS5 angiver hver oprindelig pakke, filidentitet og medlemssti.

Efter fastlåsning af metadatareglerne blev kun FITS-headere læst. En separat streng 80-tegns FITS-kortlæser reproducerer **34,635 tildelte headerværdier** eksakt. Alle tre rå-HDU-tider, identitet, HD 43629, instrument HARPS, egne A72/B71 ×4096, egen eksponering/BERV, bølgelængdegrad, nul drift, overscan og positiv gain/RON er kontrolleret. Der er ikke krævet identisk eksponering på tværs af datoer; her er alle fem faktisk **1799.9965 s**.

De 14 sammenligningsfelter er instrumentmode; DPR-kategori/teknik/type; spejl; OPTI4–7; read-clock/mode/speed; og binning X/Y. Kontrollerne 3., 4. og 5. marts matcher alle 14. Den 6. marts afviger OPTI5/6 (TUN1/TUN1). D047's tidligere nominelle STAR/SKY-routingkontrol støtter dens særskilte sekundære anvendelse; den beviser ikke samme fysiske belysning eller lampeeffekt.

Hver observation bruger sin **egen orden 34**, trace- og bølgelængdepolynomier samt BERV. Native-indekser **2446–2702**, rå række **4095−k**, fysiske kolonner round(trace)±32 og **blå CCD1-indeks = fysisk kolonne +50** er fastlagt. Kolonnerne er 1394–1459 fysisk; ingen rød CCD2-geometri, gain eller COMB-respons overføres.

Alle egne 72 A- og 71 B-traces udelukker referencepixels inden for 8 pixels. Referencerne ligger ved abs(offset)10–14 eller26–30, med mindst8 pr. række og mindst2 på hver side. Den primære aperture er signeret radius3. Geometri og referenceadgang er tilstrækkelig i alle fem observationer, før intensiteter blev analyseret.

| Observation | Headergruppe | Fraktionelt målindeks | Fast median, ADU | Kontrol/original-median | Rå/native Pearson uden for41 |
| --- | --- | ---: | ---: | ---: | ---: |
| 2021-03-09 | original | 2574.261893133 | 2199.870884 | — | 0.999179 |
| 2021-03-03 | 14 felter matcher | 2573.318678791 | 1800.999848 | 0.818684 | 0.999087 |
| 2021-03-04 | 14 felter matcher | 2573.430952194 | 1745.940714 | 0.793656 | 0.998819 |
| 2021-03-05 | 14 felter matcher | 2573.419723331 | 2291.927709 | 1.041846 | 0.999225 |
| 2021-03-06 | sekundær: selectorafvigelse | 2573.728695762 | 2329.269231 | 1.058821 | 0.532874 |

Målindekset kommer fra egen observerluft-polynomium ganget med `(1+BERV/299792.458)`. 60-cifret Decimal-inversion reproducerer ankre med største afvigelse **6.28e-11 pixel**. Hele det faste ±20-sidebånd er understøttet. Der er ingen stjerneradialhastighedskorrektion eller fysisk valideret stjerneramme.

## D058: særskilt låst råsammenligning

Metode, auditkode og inputhashes blev låst **efter D057's audit, før de nye målrettede blå udtræk og kontraster**. De blå pixels og originalhændelsen var tidligere set i bl.a. D016/D020/D026; datoerne er allerede kendte. Dette er en målrettet videreanalyse af gemte observationer, ikke en blind opdagelsestest eller fire nyfundne epoker.

Der læses kun rå CCD1 og den egne native A-flux; native B-flux, rå CCD2 og CCF læses ikke. Egen gain er **1.33 e/ADU**, header-RON **6.08 e**. Rå/native-korrelationen er beskrivende og ændrer ingen tidligere kvalitetsflag.

Den rumlige baggrund er den uændrede repeated-median affine model. Den rå radius3-kurve normaliseres med egen median over alle257samples **uden for abs(k−2574)≤20**. Alle216 udenfor-rækker har positiv radius6sum i alle fem observationer; den samlede medianprofil har top ved0.00pixel. Alle fire kontrol/source-medianforhold ligger i det på forhånd valgte interval0.5–2 og består den lokale intensitetsregel. Det beviser ikke identisk støj eller fysisk belysning.

De fire koordinatvisninger er detektorens faste k2574 samt egen barycentrisk luft NEAREST/FLOOR/CEIL. De seks spektrale baggrunde er affine/kvadratiske fit på ±5–7, ±8–12 og ±12–20 native-samples i delta/20. Alle valg er beholdt. Der tilpasses ingen fri forskydning, linjeprofil, bølgelængde eller foretrukken baggrund efter udfaldet.

Der er **120 cases**, **60 forskellige native-fit**, **96 parslots** og **72 forskellige native-par**. Signerede 3-, 5- og 15-samplesummer, baggrundskoefficienter, referenceindekser, lineære operatorer og alle negative værdier er gemt. 3-samplesummen er den primære kontrast; sammenligninger med bredere summer er bevaret uden at erstatte det primære resultat.

| Kontroldato | Gruppe | Source/kontrol NEAREST-anker | Signeret normaliseret kontrol/original-3sum |
| --- | --- | ---: | ---: |
| 3. marts | matchende headerfelter | 2574 / 2573 | -0.035175 til +0.103655 |
| 4. marts | matchende headerfelter | 2574 / 2573 | +0.055180 til +0.197990 |
| 5. marts | matchende headerfelter | 2574 / 2573 | +0.058602 til +0.147732 |
| 6. marts | sekundær | 2574 / 2574 | +0.101470 til +0.163735 |

Samtlige visninger, hver over alle seks baggrunde:

| Kontrol | Visning | Source/kontrol-anker | Forholdsinterval | Positive source−kontrol |
| --- | --- | ---: | ---: | ---: |
| CONTROL3MAR | FIXED_K2574 | 2574 / 2574 | +0.058158 til +0.139791 | 6/6 |
| CONTROL3MAR | NEAREST | 2574 / 2573 | -0.035175 til +0.103655 | 6/6 |
| CONTROL3MAR | FLOOR | 2574 / 2573 | -0.035175 til +0.103655 | 6/6 |
| CONTROL3MAR | CEIL | 2575 / 2574 | +0.059344 til +0.139451 | 6/6 |
| CONTROL4MAR | FIXED_K2574 | 2574 / 2574 | +0.007067 til +0.097403 | 6/6 |
| CONTROL4MAR | NEAREST | 2574 / 2573 | +0.055180 til +0.197990 | 6/6 |
| CONTROL4MAR | FLOOR | 2574 / 2573 | +0.055180 til +0.197990 | 6/6 |
| CONTROL4MAR | CEIL | 2575 / 2574 | +0.008445 til +0.102252 | 6/6 |
| CONTROL5MAR | FIXED_K2574 | 2574 / 2574 | -0.020080 til +0.163697 | 6/6 |
| CONTROL5MAR | NEAREST | 2574 / 2573 | +0.058602 til +0.147732 | 6/6 |
| CONTROL5MAR | FLOOR | 2574 / 2573 | +0.058602 til +0.147732 | 6/6 |
| CONTROL5MAR | CEIL | 2575 / 2574 | -0.023997 til +0.167249 | 6/6 |
| CONTROL6MAR | FIXED_K2574 | 2574 / 2574 | +0.101470 til +0.163735 | 6/6 |
| CONTROL6MAR | NEAREST | 2574 / 2574 | +0.101470 til +0.163735 | 6/6 |
| CONTROL6MAR | FLOOR | 2574 / 2573 | +0.075182 til +0.180060 | 6/6 |
| CONTROL6MAR | CEIL | 2575 / 2574 | +0.103187 til +0.167288 | 6/6 |

## Den sekundære kontrol fra 6. marts

Dens egen rå/native-Pearson er **0.5328736440484954**, mod cirka0.999 for source og de øvrige tre kontroller. Det fulde faste vindue er vist i BLUE_RAW_NATIVE_CROSSCHECK. Der ses en ekstra rå excursion uden for den centrale41zone, som ikke gengives tilsvarende i det behandlede native A-spektrum. Observationen og alle dens samples er bevaret uden efterfølgende klipning eller ny kvalitetsgrænse.

Det er en synlig rå/native-afvigelse, ikke en påvist fysisk årsag eller en dokumenteret pipelineforklaring. Headerafvigelsen og den lave beskrivende korrelation er særskilte begrænsninger; den nominelle routingkontrol fjerner dem ikke. D058's lokale intensitets-/geometriregler består, men de certificerer ikke kontrolobservationen som en ren nulprøve.

Den tidligere røde D002-0061-fejl `rho=0.7806562435869904<0.8` den5.marts består uændret. Den nye blå analyse er et andet vindue og omskriver ikke den gamle røde fejl. D002-0063's blå COMB-geometri/respons er fortsat uvalideret; D057 bekræfter sciencefilernes egen CCD1-geometri, ikke COMB-kalibreringen.

## Numerisk kontrol og figurer

**D057 audit: PASS. D058 audit: PASS.** D058 efterregner rå CCD1-koordinater med skalar pixeladgang, egne trace-polynomier med Horner, baggrund med separate skalar median-hældninger, og spektrale summer med QR mod produktionens least squares. **360 QR- og360 operatorchecks** består. Største sumafvigelse er **1.46e-11 ADU** (QR), **1.86e-11 ADU** (operator); største kontrol/source-forholdsafvigelse **9.85e-16**.

Originalens **257 fælles samples** reproducerer D016's råcounts, referencemasker og native A-flux eksakt. Radius3 reproducerer D020/D026's oprindelige robuste sourcekurve med største afvigelse **4.55e-13 ADU**. Tidligere bredde-/lampereferencer er bevaret; den nye faste normaliseringsmedian ændrer ingen tidligere måling.

Tre figurer er visuelt kontrolleret: egne native source-/kontrolkurver i detektor og barycentrisk luft; samtlige96kontraster inkl. negative værdier og dubletvisninger; samt hele rå/native-vinduet for source og den sekundære kontrol. Spektrale samples er ikke resamplet. Native A-kurvens egen median bruges kun til display i den sidste figur, aldrig i kontraststatistikkerne.

## Bevaring og fortsættelse

Alle **77,201 tidligere tabelceller** er bevaret eksakt. D057 og D058 tilføjer otte kolonner hver til de samme37+141rækker: nu **80,049 celler**. Tidligere filer, resultater og D055/D056's septemberdiagnostik bevares; ingen fysisk klassifikation er ændret.

Resultatpakken indeholder alle nye metoder, inputregistre, kode, egne headere, geometri-/pixel-/baggrundsarrays, de120cases/96par, alle nye fulde state-tabeller, audits og figurer. Den medtager også de seks eksakte tidligere gemte kontrolinputfiler, der blev gendannet fra ældre pakker, og de to uændrede D056-inputtabeller. Sammen med hovedprojektet er de blå audits dermed reproducerbare uden nye teleskopdownloads. Se EVIDENCE_MANIFEST og REPRODUCTION for præcise stier og hashes.

Hovedprojektet indeholder en kompakt fortsættelse og en hashbundet henvisning til resultatpakken. Nye fulde data og state-tabeller findes i resultatpakken. Alle tidligere hovedarkivmedlemmer bevares; de tre tidligere rodpegere er gemt eksakt i D057/FROZEN_PARENT. Den kompakte opdeling ændrer ingen videnskabelige data.

Næste afgrænsede opgave er **D059: egne blå rumlige pixelprofiler**, baseret på D058's gemte arrays og alle fem faste observationer. Kernen skal holdes ude af profiltræningen; alle tilbageholdte rækker og rå afvigelser bevares. Den skal fastlåses særskilt før beregning. D059 er **foreslået, ikke udført eller låst** i denne aflevering.

Kontrasterne alene udelukker ikke en vedvarende svagere kilde, variation eller nogen bestemt fysisk oprindelse. Ingen kalibreret FAP, kovarians, laserrespons eller stjerneramme er valideret. **Alle tre fysiske årsager er uafklarede;0kvalificerede lasersignaler.** Den gamle141kø er lukket, gamle90-/Rubinspor stoppet, offentlig upload udskudt. Ingen udgifter, eksterne kontakter eller baggrundsberegninger.
