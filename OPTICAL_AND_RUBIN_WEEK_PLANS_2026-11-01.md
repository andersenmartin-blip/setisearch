# SETI ugeplaner for optiske lasere og Rubin data

## Fremskyndelse godkendt 2. november 2026

Martin bad om mest mulig fortsættelse og foreslog at fremskynde Rubin. Første rågennemgang af alle 669 HARPS V2-poster er afsluttet. Rubin-adgangsarbejdet starter derfor **2. november**, parallelt med afgrænset HARPS-opfølgning; den fremrykkede syvdagesramme er **2.–8. november 2026**. Oprindelige kalenderdatoer nedenfor bevares som historisk plan. Den nye dato er ingen baggrundsautomatik: kun faktisk udført arbejde tæller.

Finks offentlige Rubin REST-API er kontrolleret tilgængeligt. Første trin er et separat metadataudvalgt udviklingssæt på højst 20 objekter. Datatilgængelighed, korrekt science-fotometri, fejl, filtre, tidsskalaer, historik og billedkontrol bestemmer, hvor langt analysen kan gennemføres. Udviklingsdata er ikke en gennemført hovedsøgning.

Alle øvrige videnskabelige begrænsninger bevares: højst 500 hovedobjekter med entydig Gaia-stjernematch; oktober 2026 som primært hændelsesvindue; højst én alternativ afsluttet måned valgt ud fra adgangsmetadata før hovedflux; metadatafastlagt rækkefølge; separat udvikling; detektor og kontrolplaceringer fastlagt før hovedanalysen. Minimum 50 vurderbare hovedforløb kræves fortsat for en lille fuldført pilot. Udgiftsrammen er fortsat 0 DKK, og ingen betalt tjeneste, konto eller forskerkontakt indgår.

Adgang, dataproveniens og de faktisk gennemførte trin dokumenteres under `work_rubin_20261102/`. De 35 HARPS-mappingbegrænsninger og 185 uafklarede strukturer bevares; fremskyndelsen er ikke en ophavsbestemmelse eller afslutning af disse sager.


**Udført 2. november:** Alle 35 HARPS-mappingtilfælde har nu den faste rådiagnose over 21 eksponeringer, og de to normaliseringsopfølgninger er afsluttet uden ændrede klassifikationer. Rubin er nået gennem adgang, separat udvikling, 36 kontrolinjektioner og en offentliggjort metode før hovedanalysen af 188 Gaia-associerede objekter. Kun 2 objekter er numerisk vurderbare i hovedsporet og separat 3 i forced-sporet; minimum 50 er ikke nået. Der er ingen tærskelpasserende målinger, men heller intet kvalificeret nulresultat. En separat, fast afgrænset metadataundersøgelse af et større felt vurderer næste datamulighed. Se [aktuel fortsættelse](CONTINUE_SETI.md).


**Afsluttet feltudvidelse samme dag:** 940 nye metadataforløb gav 104 tids-/kvalitetsmuligheder, derefter 2 Gaia-kvalificerede stjerner. Begge er nu analyseret efter separat offentlig metodefrysning. Samlet 190 udvalgte objekter, 861 source- og 130 forced-målinger; stadig 2 vurderbare hovedobjekter og separat 4 forced-objekter. Ingen træf, minimum 50 ikke nået. Denne afgrænsede prøve er afsluttet som forstudie. Det næste datatrin skal være en separat plan med bedre stjernedækning, inden flere hovedfluxdata åbnes.

**Datavejskontrol efter forstudiet:** Én alternativ broker (Lasair) blev undersøgt i officiel dokumentation. Dens API kræver personlig token, og den nødvendige Rubin-direct-science/quality-adgang blev ikke etableret. En fastlagt Fink-statistikforespørgsel for september gav HTTP 200 og ingen rækker; det beviser ikke fravær af observationer, men begrunder ingen ny prøve. Denne datagren er stoppet. HARPS-opfølgningen kan fortsætte fra den konkrete kø, mens Rubin genåbnes ved tilstrækkelig dokumenteret adgang/dækning.

**Afsluttet HARPS BERV-opfølgning samme dag:** 18 nye metadataepoker på HD122640 gav to kontrollerede sæsonreferencer fra maj 2017 og januar 2018. Begge spektre er bevaret og sammenlignet efter fastlagt metode: 12 hændelse/epoke-par og 24 profiler, uafhængigt efterregnet. BERV-spændet vokser fra 2,24 til 40,36 km/s, men lav lokal blå flux i den stærkt forskudte majreference begrænser ophavstesten. Alle ti udvalgte poster forbliver U; HD135204 har ingen ny epoke under forespørgslen. En separat senere kvalitetsopfølgning er konkretiseret ud fra de 16 ubrugte metadataepoker, uden nye forespørgsler eller ændringer i den afsluttede analyse. Se [rapporten](work_harps_20261102_berv_followup/README.md) og [næste trin](work_harps_20261102_berv_followup/next_followup/README.md).

**Afsluttet separat kvalitetsopfølgning:** En ubrugt majreference med højere gennemsnitlig metadata-SNR er udvalgt efter den støjplagede første sammenligning og analyseret under egen offentlig metodefrysning. Tolv nye profiler, ingen lav-kontinuum-markering, og fem blå poster med barycentrisk r=0,956–0,979 ved cirka 14 opløsningselementers forskydning. Den særskilte 5548,09 Å-top genfindes ikke med sammenlignelig amplitude. Alle ti labels bevares; næste trin er en ny kvantitativ rumlig diagnose af V2E2-0235 i det allerede gemte råbillede. Se [den afsluttede fase](work_harps_20261102_may_quality/README.md).

**Afsluttet rumlig diagnose:** V2E2-0235 er undersøgt i 8.275 gemte native detektorpixels med 232 træningsrækker, otte adskilte kontroller og tre på forhånd fastlagte profilmodeller. Alle 27 udfald er målt og uafhængigt efterregnet. Målområdets større, koncentrerede modelafvigelse ligger overvejende inden for ±3 pixels af spektrets spor; den beviser hverken ladningsophav eller fotonophav. Posten forbliver U. Ingen nye arkivprodukter blev hentet, og den afsluttede metode ændres ikke. Se [rapport og næste afgrænsede trin](work_harps_20261102_spatial_0235/README.md).

**Afsluttende baggrundskontrol:** Begge særskilt fastlagte side-estimatorer er kørt på de samme gemte pixels; alle 18 udfald og 198 rækkefit er efterregnet. Den større, koncentrerede afvigelse nær sporet består. V2E2-0235 afsluttes som U uden flere varianter i denne fortsættelse. Næste afgrænsede arbejde er fælles profil-/ordenskontekst for den eksisterende køs første gruppe C001 på HD103991, ikke flere referenceepoker til 0235.

**Afsluttet C001-gruppekontekst:** De to HD103991-poster ved3852Å er sammenlignet i seks eksisterende epoker og begge native ordener.20 profiludfald og64 sammenligningsudfald er bevaret og efterregnet. Det brede mønster er generelt mere barycentrisk sammenfaldende; kernen afhænger mere af referencevalget. Orden3 mangler venstre referenceområde og har svagt signal. Begge poster forbliverU. Næste hele gruppe i original køorden er C003 med fem HD106515A-poster; tidligere analyser genkøres ikke. Se [rapporten](work_harps_20261102_c001_context/README.md).

To selvstændige arbejdsuger for Martin Andersens SETI-projekt. Første prioritet er en optisk lasersøgning i HARPS-spektre; anden prioritet er en søgning efter usædvanlige stjernedæmpninger i Rubin-data. Hver uge skal ende med en afsluttet, afgrænset analyse eller en præcis opgørelse af, hvorfor den blev delvis eller blokeret.

**Godkendt start:** 1. november 2026. HARPS-ugen løber 1.–7. november, og Rubin-ugen 8.–14. november, Europe/Copenhagen. Arbejdet er startet efter Martins godkendelse. Der er ikke oprettet automatisk baggrundskørsel; fremdrift dokumenteres fra de faktisk udførte arbejdssessioner.

# Fælles arbejdsregler

- Første rigtige data skal være indlæst senest dag 2; hovedanalysen gennemføres senest dag 4.

- Brug eksisterende arkivprodukter og offentlig software. Ingen ny generel analyseplatform eller egen fuld instrumentreduktion i disse uger.

- Vælg hovedprøven efter metadata. Brug særskilte udviklingsdata til tilpasning, og fastlås reglerne, før hovedprøvens signalværdier undersøges.

- Gem alle hits over de fastlagte grænser, også enkeltstående og senere forkastede hændelser. Hvert hit får en begrundelse og status.

- Et korrekt dokumenteret nulresultat er en brugbar leverance. Manglende data, en ufuldført søgning eller utilstrækkelig følsomhed må ikke beskrives som en nuldetektion.

- Nyhed vurderes pr. observation og signaltype. Brug betegnelserne dokumenteret overlap, uden for den dokumenterede søgning eller ukendt overlap; undgå at love, at ingen andre har undersøgt data.

- Udgiftsramme: 0 DKK. Hent små udvalg trinvist og råbilleder efter behov. Ingen betalt regnekraft, teleskopbooking eller kontakt til forskere indgår.

- Højst to timers aktiv fejlsøgning på dataadgangen og én dokumenteret alternativ adgang pr. uge. Derefter reduceres prøven efter de beskrevne regler eller registreres som blokeret.

- Hver uge afsluttes på dag 7 uden automatisk forlængelse. Rubin-ugen er selvstændig og starter på sin planlagte plads, også hvis HARPS ender med begrænsninger. Gamle fejludfald og den tidligere radioplan ændres ikke.

# Uge 1 Optiske lasere i HARPS

**Videnskabeligt spørgsmål:** Findes der uopløste eller næsten uopløste emissionslinjer i individuelle stjerneeksponeringer, som ikke forklares af instrument, Jordens atmosfære eller kendte stjerneprocesser?

**Data:** ESO HARPS, kalibrerede enkeltspektre med tilhørende eksponeringsmetadata og adgang til rå 2D-billeder for efterkontrol. Fields og Goodman undersøgte indledningsvis ét spektrum af hver af 2.821 stjerner fra et katalog med cirka 212.000 observationer; ekstra epoker blev kun undersøgt for otte udvalgte mål. Derfor prioriteres andre eksponeringer og datoer, efter konkret overlapkontrol. [HARPS-undersøgelsen](https://arxiv.org/html/2508.08628v1) · [ESO-dataadgang](https://archive.eso.org/programmatic/).

**Målprøve:** 20 stjerner med 5–10 brugbare eksponeringer hver, helst over mindst tre nætter. To særskilte stjerner anvendes til udvikling. Udvælgelsen bruger metadata om eksponering, kvalitet og kontrolmuligheder. Mangler den tidligere undersøgelses præcise eksponeringsliste, registreres overlap som ukendt uden at standse selve analysen.

| Dag og dato | Arbejde | Leverance ved dagens slutning |
|---|---|---|
| 1 · søndag 1/11 | Kontrollér HARPS-adgang og tidligere søgedækning. Udvælg mål, eksponeringer og udviklingsstjerner. | Måltabel med observations-ID, dato, eksponeringstid, overlapstatus og adgang til kontroller. |
| 2 · mandag 2/11 | Hent spektre. Kontrollér bølgelængdeenhed, luft/vakuum, referenceframe og kvalitet. Afprøv eksisterende søgekode på udviklingsstjernerne. | Første analyserede udviklingsspektre og et låst hovedudvalg. |
| 3 · tirsdag 3/11 | Fastlås linjemodel, tærskel, bølgelængdeområde og masker. Mål genfinding i nye kontrolpositioner uden efterfølgende tilpasning til disse udfald. | Frosset konfiguration, kontrolresultat og kendte blinde områder. |
| 4 · onsdag 4/11 | Kør søgningen på alle hovedprøvens enkelte eksponeringer. Opgør søgt tid og bølgelængdedækning. | Komplet hitliste og dækningsregnskab, også ved nul hits. |
| 5 · torsdag 5/11 | Undersøg hits i råbilleder og relevante kontrolspektre. Kontrollér kosmiske stråler, airglow, naturlige emissionslinjer og kalibreringslys. | Begrundet disposition for hvert hit; manglende kontroller markeres. |
| 6 · fredag 6/11 | Sammenlign epoker i korrekte referenceframes. Reproducer et repræsentativt analyseudsnit fra gemte input i en frisk proces. | Kontrollerede figurer, hændelsestabel og reproduktionsresultat. |
| 7 · lørdag 7/11 | Afslut rapport, kode, dataliste og kørselsvejledning. Opdatér projektets GitHub-status med det faktiske udfald. | Dansk slutrapport og en samlet reproducerbar leverance. |

**Kontroller og fortolkning.** Planlæg 48 signalindsættelser på friske positioner, fordelt over linjestyrke og bølgelængdeområder, samt uændrede kontroludsnit. Linjeformen skal passe til instrumentets opløsning. De numeriske styrker og detektorens grænser fastlægges på udviklingsdata før kontrollen. Rapportér genfinding pr. styrke og område; et lille samlet gennemsnit må ikke skjule tabte stærke signaler. Indsættelser i reducerede 1D-spektre tester vores søgealgoritme, ikke tab i den oprindelige rådatareduktion.

Enkeltstående linjer bevares; manglende gentagelse er ikke i sig selv en forklaring. Status er instrumentelt eller jordisk, sandsynlig naturlig emission, uafklaret eller utilstrækkelige kontroloplysninger. En uafklaret linje er ikke en påvist laser. Langtidseksponerede spektre giver heller ikke nanosekunders pulstiming.

**Minimum og stop.** En gennemført lille pilot kræver mindst 10 stjerner og 50 brugbare eksponeringer, den fulde hitliste, målt genfinding, dispositioner og et reproduceret eksempel. Hvis 20 stjerner ikke kan klargøres dag 2, reduceres udvalget efter den allerede fastlagte metadatarækkefølge. En mindre prøve rapporteres som forstudie. Ingen brugbare data betyder blokeret.

Hvis kontrollen afslører væsentlige tab, afsluttes analysen med den målte følsomhedsbegrænsning; den giver ikke et kvalificeret fravær af signaler i det berørte område. Hvis alle hits ikke kan vurderes inden dag 7, leveres hele listen med resterende hits markeret ikke færdigvurderet. Søgetærsklen hæves ikke efterfølgende for at reducere arbejdsbyrden.

# Uge 2 Rubin data

**Videnskabeligt spørgsmål:** Findes der markante stjernedæmpninger i et afgrænset udvalg af Rubins offentlige alerts, som kræver mere forklaring end almindelig variabilitet eller billedfejl?

**Data:** Rubins offentlige alerts via Fink, med lyskurver, tilgængelig forced photometry og science-, template- og difference-billedudsnit. Gaia bruges til stjerneidentifikation og egenbevægelse; ZTF bruges som historisk kontekst. [Rubin-adgang](https://rubinobservatory.org/for-scientists/data-products/alerts-and-brokers) · [Fink-tjenester](https://doc.lsst.fink-broker.org/services/summary/).

**Målprøve:** Op til 500 Rubin-objekter med entydig Gaia-stjernematch. Primært observationsvindue er 1. oktober kl. 00.00 UTC til 1. november 2026 kl. 00.00 UTC. Objekterne vælges i en dokumenteret metadatarækkefølge uden sortering efter anomalistyrke; nærliggende stjerner prioriteres. Et separat udvalg på op til 20 objekter bruges til udvikling. Hvis oktober ikke er tilgængelig, må én anden afsluttet måned vælges på grundlag af adgangsmetadata senest dag 2, før hovedprøvens fluxværdier undersøges.

Dette er en prøve af objekter, som allerede har udløst alerts. Den er ikke en fuldstændig overvågning af 500 tilfældigt valgte stjerner.

| Dag og dato | Arbejde | Leverance ved dagens slutning |
|---|---|---|
| 1 · søndag 8/11 | Hent en lille Rubin-prøve. Kontrollér objektidentiteter, tider, filtre, fluxenheder, historik og adgang til billedudsnit. | 10–20 faktiske objektforløb og en beslutning om de brugbare datatyper. |
| 2 · mandag 9/11 | Fastlæg periode og hovedudvalg. Hent minimale nødvendige felter og tilgængelig historik. Opgør mangler og dubletter. | Objektliste, første lyskurver og tælling af vurderbare forløb. |
| 3 · tirsdag 10/11 | Fastlås kvalitetsregler, baseline og dæmpningsfilter på udviklingsudvalget. Afprøv nye indsatte dæmpninger uden efterfølgende optimering til kontrollen. | Frosset konfiguration og betinget genfinding ved den tilgængelige sampling. |
| 4 · onsdag 11/11 | Kør hovedanalysen og gem alle udvalgte hændelser, også enkeltstående. | Komplet hændelsesliste og antal objekter og målinger før og efter hvert snit. |
| 5 · torsdag 12/11 | Undersøg hændelser i billedudsnit, masker og varians. Kontrollér nabostjerner, bevægelse, sammenblandede kilder og objektassociation. | Begrundet klassifikation af hændelser og resterende datamangler. |
| 6 · fredag 13/11 | Sammenhold overlevende hændelser med Gaia, relevante variabelkataloger og ZTF, hvor der er dækning. Reproducer hovedanalysen fra gemte input. | Kontrollerede figurer, endelig hændelsestabel og reproduktionsresultat. |
| 7 · lørdag 14/11 | Afslut rapport og dokumentation. Opdatér GitHub med faktisk dækning, resultater og vurdering af videre arbejde. | Dansk slutrapport og en samlet reproducerbar leverance. |

**Signal og kontroller.** Udgangspunktet er dæmpninger på mindst 0,3 magnituder relativt til en brugbar baseline i samme filter; den endelige fejl- og kvalitetsregel fastlægges på udviklingsudvalget. Brug flux og fejl direkte, og beregn kun en dæmpningsstørrelse, når baseline og datakvalitet tillader det. Forløb uden en brugbar baseline er ikke vurderbare efter dette kriterium.

Planlæg 36 signalindsættelser med tre dybder og tre varigheder på fire friske placeringer pr. kombination. Dybder og varigheder fastlægges før hovedanalysen ud fra den faktiske tidsdækning; medtag hændelser mellem observationer, så samplingstab bliver synlige. Sammenlign med uændrede kontrolforløb. Resultatet beskriver vores efterbehandling af de hentede lyskurver; det måler ikke fuldstændigheden af Rubins billed- og alertpipeline.

**Datakvalitet.** En negativ differenceflux er ikke alene et mål for, hvor meget stjernen er dæmpet. Science-, template- og differencefotometri holdes adskilt, filtre blandes ikke, og gentagne alertpakker tælles ikke som nye observationer. Tidsstempler og tidsskalaer normaliseres dokumenteret. Fink advarer om manglende felter, opsplittede objekt-ID’er og en endnu usikker reliability-score; billedkontrol og konkrete kvalitetsflag er derfor nødvendige. [Fotometri](https://doc.lsst.fink-broker.org/data/photometry/) · [Datakvalitet](https://doc.lsst.fink-broker.org/data/quality/) · [Kendte fejl](https://doc.lsst.fink-broker.org/data/issues/).

Opgør særskilt: forespurgte objekter, objekter med Rubin-data, vurderbare forløb, brugbare observationer og hændelser. Manglende alerts eller manglende historik betyder ikke, at stjernen var konstant. Status for hændelser er artefakt, sandsynlig naturlig variabilitet, uafklaret eller utilstrækkelige data. Anomalier betegnes ikke solsejl eller teknologi på grundlag af lyskurven alene.

**Minimum og stop.** En gennemført lille pilot kræver mindst 50 vurderbare objektforløb med faktisk Rubin-fotometri, den fulde hændelsesliste, betinget genfinding og dokumenteret gennemgang. Færre objekter kan give et forstudie. Hvis 500 ikke er realistisk, bruges et mindre udvalg i den fastlagte metadatarækkefølge. Hvis nødvendige Rubin-data ikke kan hentes senest dag 2 inden for fejlsøgningsrammen, registreres ugen som blokeret; ZTF alene opfylder ikke Rubin-målet.

Hvis en del af hændelserne ikke kan færdigvurderes, markeres analysen som delvis. Ingen tidsperiode, målgruppe eller tærskel udvides efterfølgende alene for at finde et interessant resultat.

**2. november — C003 afsluttet:** [Den fælles HD106515A-analyse](work_harps_20261102_c003_context/README.md) omfatter7eksisterende epoker,30profiler og172sammenligningsudfald. Kernen og omgivelserne har høj barycentrisk formoverensstemmelse; alle fem poster forbliverU. Otte dækkende ordensammenhænge, seks profiler uden normalisering og to strukturelt manglende orden2-kontekster er registreret særskilt. Uafhængig kontrol består med117.053skalarsammenligninger. Næste faste gruppe erC005ved3882,04Å. Ingen ny arkivhentning eller Rubin-forespørgsel.

**2. november — C005 afsluttet:** [Analysen ved 3882 Å](work_harps_20261102_c005_context/README.md) omfatter syv eksisterende epoker, 34 profiler og 180 sammenligninger. Alle profiler har fuld dækning og positiv normalisering; to orden 4-profiler har lave referenceflag. Kernen og omgivelserne har høj barycentrisk formoverensstemmelse. Alle fem poster forbliver U. Uafhængig efterregning består med 135.577 skalarsammenligninger. Næste faste gruppe er C006 med tre poster fra to unikke discovery-eksponeringer. Ingen ny arkivhentning eller Rubin-forespørgsel.

**2. november — C006 afsluttet:** [Analysen ved 4310 Å](work_harps_20261102_c006_context/README.md) omfatter syv epoker, 18 profiler og 64 sammenligninger med to unikke discovery-referencer. Alle tre poster forbliver U. Fuld dækning og positiv normalisering, ingen lave referenceflag; tidligere mapping-forbehold for 0025 er bevaret. Uafhængig efterregning består med 71.701 skalarsammenligninger. Næste faste punkt er C007 ved 4312,7 Å, som overlapper det allerede sete vindue. Ingen ny arkivhentning eller Rubin-forespørgsel.

**2. november — C007 afsluttet:** [Den individuelle analyse ved 4312,7 Å](work_harps_20261102_c007_context/README.md) omfatter syv eksisterende epoker, 16 profiler og 32 sammenligninger med én fast discovery-reference. V2E2-0026 forbliver U; tidligere lokale mapping-forbehold og overlap med C006 er bevaret. Uafhængig efterregning består med 64.179 skalarsammenligninger. Næste faste gruppe er C004 ved 3872,245 Å med tre discovery-referencer; dens kerne overlapper C003. Ingen ny arkivhentning eller Rubin-forespørgsel.

**2. november — C004 afsluttet:** [Den fælles analyse ved 3872,245 Å](work_harps_20261102_c004_context/README.md) omfatter syv eksisterende epoker, 20 profiler og 96 sammenligninger med tre faste discovery-referencer. Alle tre poster forbliver U; tidligere mapping-diagnoser og overlap med C003 er bevaret. Uafhængig efterregning består med 79.803 skalarsammenligninger. Næste faste punkt er C002 ved 3868,6025 Å med én reference; dens kerne var allerede synlig i C003. Ingen ny arkivhentning eller Rubin-forespørgsel.

**2. november — C002 afsluttet:** [Den individuelle analyse ved 3868,6025 Å](work_harps_20261102_c002_context/README.md) omfatter syv eksisterende epoker, 18 profiler og 36 sammenligninger med én fast discovery-reference. V2E2-0033 forbliver U; tidligere mapping-diagnoser samt overlap med C003 og C004 er bevaret. Uafhængig efterregning består med 71.071 skalarsammenligninger. Næste faste punkt er C008 ved 5182,005 Å med én reference. Ingen ny arkivhentning eller Rubin-forespørgsel.

**2. november — C008 afsluttet:** [Den individuelle analyse ved 5182,005 Å](work_harps_20261102_c008_context/README.md) omfatter syv eksisterende epoker, 16 profiler og 32 sammenligninger med én fast discovery-reference. V2E2-0047 forbliver U; tidligere mapping-diagnoser og genbrug af oprindelige observationer er bevaret. Uafhængig efterregning består med 63.374 skalarsammenligninger. Næste faste punkt er C009 ved 6802,02 Å med én reference og bevaret uafklaret råmorfologi. Ingen ny arkivhentning eller Rubin-forespørgsel.

**3. november — C009 afsluttet:** Den centrale spektralform afviger fra alle seks andre epoker, mens omgivelserne stemmer bedst overens barycentrisk. [Den individuelle analyse ved 6802,02 Å](work_harps_20261103_c009_context/README.md) omfatter syv eksisterende epoker, 16 profiler og 32 sammenligninger med én fast discovery-reference. V2E2-0050 forbliver U; tidligere mapping-diagnoser og genbrug af oprindelige observationer er bevaret. Uafhængig efterregning består med 63.354 skalarsammenligninger. Næste faste punkt er C010 på HD112410 ved 3823,065 Å med målets egne syv epoker, én april 2025-reference og bevarede historiske mapping-begrænsninger. Ingen ny arkivhentning eller Rubin-forespørgsel.

# Leverancer og opfølgning

Hver uge leverer:

1. En kort dansk resultatrapport med konklusion og begrænsninger.

2. En maskinlæsbar liste over alle planlagte, hentede, analyserede og udeladte observationer med årsager.

3. Hele hit- eller hændelseslisten med begrundede dispositioner og eventuelt resterende gennemgang.

4. Figurer af repræsentative data og samtlige uafklarede hændelser.

5. Kodeversion, afhængigheder, fast konfiguration, kildehenvisninger, filhashes og en reproduktionskommando.

6. En GitHub-status, der skelner mellem gennemført, delvist gennemført og blokeret.

**Beslutning efter hver uge:** Fortsæt, hvis de faktiske data og kontroller giver et klart næste videnskabeligt spørgsmål. Prioritér mere data med samme fungerende metode, når det giver værdi. Planlæg en særskilt metodeændring, hvis en dokumenteret følsomhedsbegrænsning kræver det. Antallet af kodefiler og tests tæller ikke som observationsdækning.

# Fagligt udgangspunkt

- [Fields og Goodman 2025 om HARPS og tidligere tidsdækning](https://arxiv.org/html/2508.08628v1).

- [Offentlig optisk søgekode fra samme projekt](https://github.com/goodmanj/optical_seti).

- [ESO programmatisk arkivadgang](https://archive.eso.org/programmatic/).

- [Gallay med flere 2025 om SETI med alertbrokere](https://arxiv.org/html/2506.14744v1).

- [Rubin seneste dataudgivelser](https://rubinobservatory.org/for-scientists/data-products/recent-data-releases).

- [Fink adgang til portal og API](https://doc.lsst.fink-broker.org/services/summary/).

Prøvestørrelser, tidsfrister og kontrolomfang ovenfor er den godkendte arbejdsramme fra 1. november 2026. Konkrete downloads, analyser og resultater registreres i projektets løbende status.

**3. november — C010 afsluttet:** Kernen stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. Omgivelserne stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. V2E2-0086 forbliver U. 16 af 16 profilrækker indeholder bevarede ikke-positive originalpunkter, selv om de gyldige reference-medianer er positive. Profilform og skaleret amplitude varierer mellem epokerne. [Den individuelle analyse på HD112410 ved 3823,065 Å](work_harps_20261103_c010_context/README.md) omfatter syv eksisterende målspecifikke epoker, 16 profiler og 32 sammenligninger med én april 2025-reference. Uafhængig efterregning består med 63.469 skalarsammenligninger. Historiske begrænsninger og alle U bevares. Næste punkt i den oprindelige kø er C012 på HD112410 ved 3869,2675 Å, oprindelig kø-række 24. Dets præcise mål, epoker, discovery-reference og historiske begrænsninger bevares i overdragelsen. Gruppenumre bestemmer ikke rækkefølgen. Ingen ny observatorie- eller Rubin-forespørgsel.


**3. november — C012 afsluttet:** Kernen stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. Omgivelserne stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. V2E2-0087 forbliver U. 4 af 18 profilrækker indeholder bevarede ikke-positive originalpunkter, selv om de gyldige reference-medianer er positive. Profilform og skaleret amplitude varierer mellem epokerne. [Den individuelle analyse på HD112410 ved 3869,2675 Å](work_harps_20261103_c012_context/README.md) omfatter syv eksisterende målspecifikke epoker, 18 profiler og 36 sammenligninger med én april 2025-reference. Uafhængig efterregning består med 70.371 skalarsammenligninger. Historiske begrænsninger og alle U bevares. Næste punkt i den oprindelige kø er C011 på HD112410 ved 3865,6775 Å, oprindelig kø-række 25. Dets præcise mål, epoker, discovery-reference og historiske begrænsninger bevares i overdragelsen. Gruppenumre bestemmer ikke rækkefølgen. Ingen ny observatorie- eller Rubin-forespørgsel.
