# SETI D075–D076: FEROS-ordener og referencevalg

**13. november 2026. Aktuelt fortsættelsespunkt: D076.** HD43629/TIC34077285, de samme fem datoer 4., 7., 8., 10. og 14. november 2019 og tre kendte positioner. Grundlag: det gemte D074-checkpoint, version 0. Ingen nye teleskopobservationer eller FITS-sciencearrays.

## Resultat

Forskellene ved **0061 består i de individuelle ordener**, hvor valg af sidebånd og reference kan give større forskelle end i det samlede spektrum. Blandt alle fastlagte varianter afviger en ordens mønsterforskydning fra den tilsvarende samlede profils med op til **1,45 km/s**. Forskellen mellem rødt og blåt sidebånd i samme orden kan nå **1,35 km/s**. Begge er beskrivende metodeintervaller, ikke målt astrofysisk variation eller statistiske fejlgrænser.

En separat låst kontrol bytter reference- og målspektrum. I et af de fastlagte tilfælde ved 0061 fås **−0,90 km/s fremad og +1,85 km/s baglæns**. Det forventede modsatte resultat passer dermed ikke: forskydningerne giver tilsammen cirka **0,95 km/s** i den anvendte additive log-koordinat. Dette er et andet fastlagt tilfælde end eksemplet med den største ordens-/samleforskel; alle konfigurationer er bevaret.

Den lokale mønstertilpasning er derfor ikke en valideret fysisk stjernehastighed, som kan anvendes ens på kandidaterne. **Alle tidligere kandidatmålinger er uændrede. 0 kvalificerede lasersignaler; alle tre tidligere fysiske oprindelser er fortsat uafklarede.**

## D075: samme test i samtlige dækkende enkeltordener

Kode og metode låses før de nye ordensspecifikke hastighedstilpasninger. D074-profiler og resultater er kendt; dette er en begrundet opfølgning, ikke en blind uafhængig detektionstest. Alle **150 eksisterende ordensprofiler** bruges: fem datoer, tre positioner, tre ekstraktionsmetoder og med/uden fladfeltning. 0061 dækkes af HDU 29 og 30, 0063 af HDU 17 og 0071 af HDU 24 og 25. HDU-indekser er filafsnit, ikke fysiske diffraktionsordensnumre.

Alle ti uordnede datopar beholdes, med den tidligere dato som reference. Modellen og gridet er de samme som i D074: −10 til +10 km/s i trin på 0,05 km/s, en midlertidigt interpoleret reference samt fri skala, konstant og lineær baggrund. **Gridtrinnet er ikke en målt hastighedspræcision.** De oprindelige flux- og bølgelængdearrays omskrives ikke.

De faste træningsområder ligger 1–4 Å fra den gamle kandidatposition. Der tilpasses både begge sider, kun blå og kun rød side. Området inden for ±1 Å er udeladt. Den enkelte ordens træningssamples kobles via de fælles SDP-sampleindekser til D074-masken. **Alle 900 ordens-/samlemasker har eksakt de samme målkoordinater.** Der vælges ingen alternativ maske eller foretrukken orden efter resultatet.

Der er 300 datopar-/ordens-/reduktionskontekster, **900 kurver og 360.900 gridtilpasninger**. Alle kan beregnes, alle skalaer ved minimum er positive, og ingen minimumsværdi ligger ved gridgrænsen. Hele gridet, koefficienterne og alle kontroller bevares. Her og nedenfor er alle størrelser i km/s-enheder for lokal produktkoordinat-tilpasning; der er ingen absolut stjernehastighed eller fysisk nøjagtighedskalibrering.

| Position | HDU | Fremad, begge sider | Største orden minus samlet: begge / alle masker | Største rød–blå-forskel | Største tre-dato-rest: begge / alle masker |
| --- | --- | ---: | ---: | ---: | ---: |
| D002-0061 | 29, 30 | -0,55 til 0,60 | 0,30 / 1,45 | 1,35 | 0,30 / 1,70 |
| D002-0063 | 17 | -0,40 til 0,60 | 0,00 / 0,00 | 0,20 | 0,10 / 0,15 |
| D002-0071 | 24, 25 | -0,35 til 0,45 | 0,35 / 0,40 | 0,45 | 0,20 / 0,20 |

En tre-dato-rest sammenligner den samlede forskydning via i→j→k med den direkte i→k. Der er 900 sådanne kontroller. Desuden er alle 900 ordens-/samlepar, 360 ordens-/ordenspar, 300 side-, 900 mode- og 450 fladfeltsforskelle gemt.

Ved 0063 giver den ene dækkende orden og det samlede spektrum **eksakt samme 180 komplette SSE-kurver**. Det er en nyttig kontrol af koblingen og implementeringen, men genbruger de samme data og er ikke en ny uafhængig astronomisk bekræftelse.

## D076: reference og mål byttes om

Efter D075-resultatet låses en ekstra kontrol, hvor den senere dato er reference og den tidligere dato er mål. Alle **240 eksisterende profiler** medtages: både samlede spektre og alle dækkende ordener, alle tre metoder og begge fladfeltsvarianter. Der kommer **1.440 kurver og 577.440 gridtilpasninger**. Alle slots kan beregnes med positive skalaer ved minimum og uden grænseminima.

De samme faste sidebånd og samme model bruges. Inden for den nuværende måldato er ordens- og samlesamples igen eksakt sammenfaldende. Når rollerne byttes, ændres samtidig hvilket spektrum der interpoleres, hvilket der får residualerne, og målgridets tilhørsdato. **Kontrollen isolerer derfor ikke interpolation alene.** Den måler den samlede afhængighed af retningen i denne konkrete tilpasningsprotokol.

For hvert matchende par beregnes

δ = c × [atanh(v_frem/c) + atanh(v_tilbage/c)].

Ved de små parameterværdier her er dette praktisk talt summen af frem- og tilbageparametrene. Ideelt gensidigt omvendte resultater giver nul. Der fastsættes ingen støjkalibreret acceptgrænse, og δ er ikke en fejlstreg, sigma eller FAP. Der gennemsnittes ikke mellem retningerne for at fremstille en ny »bedste« stjernehastighed.

| Position | Profiltype | Største absolutte δ, begge sider | Største absolutte δ, alle masker | Største baglæns tre-dato-rest: begge / alle masker |
| --- | --- | ---: | ---: | ---: |
| D002-0061 | Samlet | 0,05 | 0,15 | 0,10 / 0,55 |
| D002-0061 | Enkeltordener | 0,15 | 0,95 | 0,35 / 1,65 |
| D002-0063 | Samlet | 0,05 | 0,10 | 0,10 / 0,10 |
| D002-0063 | Enkeltordener | 0,05 | 0,10 | 0,10 / 0,10 |
| D002-0071 | Samlet | 0,05 | 0,05 | 0,10 / 0,10 |
| D002-0071 | Enkeltordener | 0,05 | 0,15 | 0,20 / 0,20 |

Den største retningsafvigelse findes ved 0061, HDU 30, optimumekstraktion med fladfeltning og rødt sidebånd, mellem F2 og F4. Værdierne er −0,90 og +1,85 km/s. Det er ikke en påvist ændring i en stjernes bevægelse: de to parametre kommer fra de samme to observationer med byttede roller. Den største fremadgående ordens-/samleforskel på 1,45 km/s er ved samme ordens- og datopar, men i en anden ekstraktions-/fladfeltskonfiguration. De to eksempler blandes ikke sammen som én måling.

Alle 1.440 frem-/tilbagepar, 1.440 baglæns tre-dato-kontroller, 900 baglæns ordens-/samlepar, 360 ordenspar og 480 sidepar er med. 0063's ordens-/samlekurver er også eksakt ens i den baglæns kontrol.

## Fysisk fortolkning og næste prioritet

Der er nu dokumenteret afhængighed af orden, sidebånd og referencevalg, især ved 0061. Den reproducerbare numeriske beregning validerer ikke en fysisk referenceramme. Linjeblandinger, profilvariation, datareduktion, ordensrespons, kalibrering og modellens asymmetri kan indgå; denne analyse bestemmer ikke en entydig årsag.

Kandidaternes gamle restsummer, oprindelige bølgelængder og status bevares. Ingen ny forskydning anvendes, ingen ekstra barycentrisk korrektion lægges til, og der udledes ingen fysisk persistensudelukkelse. De gamle hændelser er fra 2021, mens disse FEROS-kontroller er fra 2019. Kontrollen er ikke en samtidig bekræftelse af hændelserne.

Næste foreslåede fase, **D077**, er derfor en metadata- og proveniensgate for de **30 eksakte WLC-råreferencer**, som allerede er angivet i de fem kalibreringskæder. Alle 30 medtages uden udvælgelse efter resultat. Før eventuelle kalibreringspixels eller nye linjereferencer analyseres, skal deres identitet, instrumentkonfiguration, fiberkontekst, enheder og adgang bekræftes under en særskilt låst metode. D077 er endnu ikke låst eller udført; der er ingen nye arkivforespørgsler i det afsluttede arbejde.

## Efterregning og bevaring

Begge nye audits består. D075 efterregner alle 360.900 gridpunkter med selvstændig interpolation, QR og skalar summering; alle minima, 2.910 pardifferencer og 900 tre-dato-kontroller genfindes. D076 kontrollerer alle 577.440 gridpunkter, alle rollebytninger og masker, 1.440 frem-/tilbagepar, 1.740 andre pardifferencer og 1.440 baglæns tre-dato-kontroller. De største uafhængige SSE-forskelle er henholdsvis **1.16e-10** og **1.11e-10**. Det er interne alternative beregninger udført af samme assistent, ikke ekstern fagfællebedømmelse eller fysisk støjkalibrering.

Fire figurer er visuelt kontrolleret: alle 900 fremadgående ordens-/samleforskelle, alle 900 ordensminima og to visninger af samtlige 1.440 frem-/tilbagepar. Punkter kan falde sammen, fordi samples og parameterværdier genbruges. Alle kurver, koefficienter, masker og afvigende tilfælde ligger i JSON/CSV/NPZ. Hver kurves SSE er en beskrivende uvægtet restsum; ERR-pladsholderen bliver ikke til en usikkerhed, og ingen ny kovarians, laserrespons eller FAP kalibreres.

Alle **102.833 tidligere tabelceller** bevares eksakt i samme 37+141 rækker. To faser tilføjer otte kolonner hver: nu **105.681 celler**. Den gamle 0061-rho-fejl, blå COMB-mangel, 6. marts' sekundære status og alle tidligere oprindelsesvurderinger er uændrede. Den historiske version 59 og den tidligere resultatpakke bevares byteeksakt. Det aktive SETI_ACTIVE_CONTINUATION.json opdateres med versionskontrol fra det læste checkpoint version 0; den store historikfil omskrives ikke.

Resultatpakken indeholder al ny kode, låste metoder, 2.340 kurver med i alt **938.340 nye gridtilpasninger**, kontroller, komplette state-tabeller, figurer og næste inputforslag. Den kræver det præcist identificerede D069–D074-kompagnonarkiv samt de tidligere fastholdte input. Se REPRODUCTION.md og manifestet for udpakning og genkørsel.

**0 kvalificerede lasersignaler; alle tre oprindelser uafklarede.** Ingen ny rå CCD-analyse, nye FITS-sciencearrays, nye arkivhentninger, udgifter, personkontakter eller baggrundsberegninger. Den gamle 141-råkø er lukket, 90-/Rubinspor stoppet og offentlig upload udskudt.
