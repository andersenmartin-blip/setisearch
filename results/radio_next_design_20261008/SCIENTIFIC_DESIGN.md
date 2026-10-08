# Videnskabeligt udviklingsdesign til en senere SETI-plan

**Status 8. oktober 2026: forslag, ikke en aktiveret forsøgsbank eller kvalifikation.** Dokumentet beskriver, hvad en senere metodeudvikling skal afgøre. Ingen nye seeds er tildelt, ingen data er genereret, ingen score er beregnet, og ingen regel eller tærskel er ændret. A/B forbliver `FAIL_CLOSED`; den ene tilladte operationelle rettelse er brugt. Udarbejdelsen af dette design er autoriseret arbejde i den nuværende periode. De foreslåede nye simuleringer og metodeændringer er derimod ikke tilladt i den godkendte periode 7.–20. oktober, låner ikke dens restbudget og starter ingen ny kampagne automatisk.

Den nuværende [godkendte plan](../../RADIO_TWO_WEEK_PLAN_2026-10-07.md) bevarer enkeltstående ON-forekomster og intermittens. Det princip fastholdes: kort varighed eller manglende tilbagekomst kan beskrive en hændelse, men kan ikke alene begrunde, at den slettes som falsk.

## Grundlaget og de tre spørgsmål

[Diagnostikken](../radio_diagnostics_20261008/DIAGNOSTIC_REPORT.md) viste 8.114 overlevende carriers fra 12 stærke indsprøjtninger i én tidsrække. [Pulsgeometrien](../radio_diagnostics_20261008/PULSE_GEOMETRY.md) viser, at 8.103 passerer nær pulsen ved dens aktive integrations midtpunkt, mens 428 opfylder lokalisering ved begge ender af hele ON-scannet. Det er korrelerede sporsvar, ikke 8.114 uafhængige hændelser eller en målt tidsprofil.

De samme diagnostikker viste 66 initialt lokaliserede ON-hits i 11 nær-OFF-forløb; alle blev vetoet i den efterfølgende kontaminerede OFF. Et yderligere forløb kom aldrig over ON=10. [RFI-analysen](../radio_rfi_alias_analysis_20261008/RFI_ANALYSIS_REPORT.md) viste samtidig 14 rester fra to RFI-forløb: den præcise indsprøjtede drift lå geometrisk uden for resternes OFF-matchfamilier. En generel udvidelse af OFF-tolerancen risikerer derfor at forværre det dokumenterede signaltab.

[METHOD-dækningen](../radio_diagnostics_20261008/METHOD_COVERAGE.md) skiller idealniveau fra det gemte globale søgemaksimum: 13 af 128 aktive ON-scans nåede ikke ON=10. Der er ingen gemt, på forhånd fastlagt sandbane-statistik under tærsklen. Næste udvikling bør besvare tre særskilte spørgsmål:

| Spørgsmål | Testbar hypotese | Hvad forsøget ikke kan afgøre |
|---|---|---|
| Tidsstøtte | Mange forskellige fuld-scan-spor får respons fra samme korte power-hændelse; en beskrivelse pr. aktiv integration kan vise den manglende tidslige information og reducere dobbeltfortolkning. | Om en identisk kort smalbåndshændelse stammer fra en sender på himlen eller et instrumentelt artefakt. |
| RFI og nærliggende OFF | En observerbar RFI-familie kan omfatte både den stærke kerne og forskudte ON-responser, selv om deres vinderdrift ikke matcher. En separat ON-komponent skal samtidig kunne bevares ved nærliggende interferens. | En kausal RFI-andel i de allerede gemte scores eller sikker adskillelse af komponenter med identiske observerede profiler. |
| Måleskala | Støj, behandling, grid-mismatch og udvælgelse af søgemaksimum bidrager forskelligt til afvigelsen fra idealprojektionen. Parrede kontroller kan skille disse trin. | En flux-/EIRP-kalibrering eller himmel-falskalarmrate fra små syntetiske paneler. |

## 1. Beskriv tidsstøtte uden at afvise ægte korte udsendelser

Den første ændring, der bør undersøges, er et **diagnostisk output**, ikke et varighedsveto. For hvert hit gemmes tidsrække, frekvensområde og lineær projektion før aggregationen, både langs den udvalgte bane og langs en fast oracle-bane i udviklingsforsøg. Detektorscoren kan være ikke-additiv; rækkeprojektionerne må derfor ikke betegnes som en eksakt dekomposition af den endelige robuste score uden særskilt matematisk kontrol.

Et muligt beskrivende mål er koncentrationen i den stærkeste række og et effektivt rækkeantal beregnet på de positive rækkeprojektioner. Definition, nulnævner/`EMPTY` og behandling af negative projektioner skal fastlægges før nye udfald. Positiv klipning og udvalgt vinderbane giver selv støj- og selektionsbias; sådanne mål er ikke i sig selv sandsynligheder for signal eller artefakt. Hele rækkevektoren skal bevares, så et samlet tal ikke skjuler profilen.

Minimumssammenligningen er samme støjbaggrund med henholdsvis ingen indsprøjtning, én integration i første række, én i sidste række og en linje gennem alle 16 rækker. Bredde 1/3 og drift −4/+4 krydses, så den gamle kobling mellem bredde og drift fjernes. Aktiviteten placeres i ét fast ON-scan; der kræves ikke gentagne ON-forekomster. To amplitudekonventioner er nødvendige:

- Samme støjfri fuld-scan idealprojektion 24 for hver tidsprofil. Det efterprøver direkte den tidligere stærkt opskalerede enkelt-række-diagnostik.
- Samme amplitude pr. aktiv række som den fulde linje med idealprojektion 24. Det skiller tidsstøtte fra den energiforøgelse, som den første konvention kræver i en kort puls.

For fuld-linjen er de to konventioner identiske og køres kun én gang. Foreslået første udviklingstrin: fire bredde/drift-konfigurationer med én fælles ny støjrealisering i hver. Hver blok indeholder støj alene, første/ sidste række under begge amplitudekonventioner og fuld-linjen: **6 arrayversioner pr. blok, 24 i alt**. De er parrede udviklingskontroller, ikke 24 uafhængige valideringsforsøg. Der tildeles ingen identiteter eller seeds med dette dokument.

Derudover specificeres en ikke-identificerbar kontrol: præcis samme observerede array beskrives med henholdsvis »kort ægte udsendelse« og »identisk kort artefakt«. En algoritme må give samme observerbare resultat for begge; etiketten alene giver ingen ekstra evidens. Dette kræver ingen ekstra simulering. Det synliggør, hvor pointing, instrumentdiagnostik eller en senere uafhængig observation ville være nødvendig.

Trinnets endpoint er komplette rækkeprofiler og optælling af hændelser versus korrelerede carriers, samt særskilt lokalisering over **observeret aktiv støtte** og ekstrapoleret fuld-scan-geometri. De to lokaliseringer må ikke udskifte den nuværende recovery-definition bagudrettet. Der opstilles ingen regel om, at én række er falsk. En puls i en indre række, mellemvarigheder, anden ON-placering og anden støjlov er eksplicit udækkede i dette lille første trin.

## 2. Undersøg RFI-familier sammen med signalbevarelse

Den konkrete kandidat er at beskrive sammenhængende responser omkring en stærk ON/OFF-komponent som en familie ud fra deres **observerede frekvens- og tidsstøtte**, frem for alene at sammenligne hver ON-vinders drift med et separat OFF-template. En fælles punktkrydsning eller en frekvensafstand er utilstrækkelig: pulsforsøgene viser netop, at mange forskellige baner kan krydse én integration.

En senere prototype skal derfor gemme både kernens og resternes projektioner og fastlægge en observerbar associationsregel før sin udviklingskørsel. RFI-sandheden må bruges til evaluering, aldrig som input til selve familieafgørelsen. Alle ON-hits og begrundelser bevares. Hvis en separat ON-komponent ikke kan skelnes fra den OFF-associerede komponent, bør udviklingsoutput være en tydelig uafklaret disposition; det må ikke rapporteres som dokumenteret ægte signal eller dokumenteret korrekt RFI-afvisning.

Foreslået mindste parrede panel krydser bredde 1/3, drift −4/0/+4 og native frekvensoffset 0/+2/+8. Nuldrift er med for direkte at konfrontere den kendte fejl i de oprindelige nær-OFF-forsøg. Frekvensaksen er faldende: de positive native offsets svarer til negative fysiske frekvensforskelle. Hver af seks bredde/drift-blokke bruger samme støjbaggrund til disse scenarier:

| Scenarie | Antal versioner pr. blok | Sammenligningens formål |
|---|---:|---|
| Støj alene | 1 | Reference for nye falske responser. |
| Kun hovedsignalet i ét ON, idealniveau 12 | 1 | Initial og endelig genfinding uden interferens. |
| Kun RFI i ON og OFF, idealniveau 24, hvert af de tre offsets | 3 | Hvor mange kerne- og aliasfamilier resterer uden ægte ON-komponent? |
| Kun en linje i den efterfølgende OFF, idealniveau 24, hvert offset | 3 | OFF-komponentens egen respons og oracle, uden hovedsignal. |
| Hovedsignal plus ON/OFF-RFI, hvert offset | 3 | Bevares en separat ON-komponent, mens RFI-familien håndteres? |
| Hovedsignal plus OFF-linjen alene, hvert offset | 3 | Isolerer tabet fra den nærliggende OFF-kontamination. |

Det giver **14 versioner pr. blok, 84 i alt**. Hovedsignal og interferenskomponent har hver deres sandhed, amplitudekvittering og oracle-bredde i alle relevante scans. Offset 0 er en vigtig grænsekontrol: sammenfaldende komponenter kan være ikke-identificerbare. Den må ikke få en kunstig »korrekt separation« alene, fordi generatoren kender deres labels. Udækkede forhold er blandt andet modsat offsetretning, forskellige signal/RFI-drifter, andre styrkeforhold, båndkanter og flere interferenskomponenter.

Der evalueres højst **én på forhånd specificeret familieprototype mod den uændrede baseline** i dette trin. Endpoints er: alle rester i RFI-only, initialt lokaliseret ON-genfund, endeligt genfund, nye tab i signal-plus-interferens og antal uafklarede familier. Nævneren er støjblok/scenarie, ikke carrier. Et tomt kompatibelt OFF-resultat efter fuld traversal adskilles fra tidligt stoppede witnesses. Et familieveto, som fjerner RFI-rester ved også at miste de separate ON-signaler, er ikke en løsning.

## 3. Skil idealprojektion, fast bane og søgemaksimum

I en senere kørsel skal tre målinger gemmes for hver indsprøjtning før tærskelcensur: den erklærede støjfri idealprojektion; detektorstatistik på én bane fastlagt fra generatorens sandhed **før støjen ses**; og det globale maksimum over det frosne søgegrid. Den faste bane fastlægger også bredde og referencefrekvens uden efterfølgende maksimum over en sandhedsregion. Ellers er »sandbane-score« igen en udvalgt statistik.

Hvis scoren kun kan beregnes på det diskrete grid, låses én nærmeste grid-bane fra sandheden med en deterministisk tie-regel. Dens endepunktsmismatch gemmes. Den bliver en fast grid-bane-statistik, ikke en eksakt kontinuert oracle-score. En separat præcis oracle-evaluering kræver en på forhånd specificeret evaluator; de to må ikke blandes.

Foreslået panel: bredde 1/3 × drift −4/+4 × to nye støjrealiseringer × idealniveau 0/8/10/12/16, med samme støj i niveauerne inden for hver blok. Det er **8 støjblokke og 40 arrayversioner**. Aktivitet og frekvensplacering holdes faste i det første trin, og alle nulversioner føres som støjkontroller. De to realiseringer giver en første udviklingssammenligning, ikke en estimeret detektionskurve. Mere replikation eller bredere dækning må budgetteres og fryses senere, før nye udfald åbnes.

Endepoints er parrede ændringer i de tre målinger, forskellen mellem fast bane og søgemaksimum, grid-mismatch, tærskelpassage, initial lokalisering og endeligt genfund. Statistik ved sandheden gemmes også ved miss; globalt maksimum over ON=10 tæller ikke alene som korrekt lokalisering. Et større globalt maksimum kan skyldes udvælgelse; det bruges ikke som amplitude- eller SNR-estimat. Støjfri og støjtilsatte projektionskvitteringer skal gøre det muligt at adskille amplitudekonvention og behandling, uden at antage at robust normalisering er lineær.

## Artefakter som mangler i den nuværende pakke

De eksisterende resultater indeholder ikke rå syntetisk power, standardiserede residualer, projektioner pr. række, fulde ikke-vindende template-responser eller en separat OFF-oracle for nær-OFF-linjen. De kan derfor ikke bruges til de foreslåede kontrafaktiske eller tidslige målinger uden ny data-generering og scoring. Den mangel er en begrundelse for et senere design, ikke tilladelse til at genskabe dem nu.

En senere lille udviklingspakke bør gemme rå input og indsprøjtede komponenter med hashes; tids-/frekvensakser og kanalretning; alle relevante sandheder; amplitudeskalering og oracle-bredde pr. komponent og scan; den fastlagte og den udvalgte banes rækkeprojektioner; tilstrækkelige ikke-vindende svar til den erklærede familieregel; fulde hits/dispositioner; samt komplette eller eksplicit tidligt stoppede OFF-records. Gem kun det afgrænsede bånd og de outputs, som hypoteserne kræver. Runtime, fejl og byteforbrug tælles sammen med vellykkede jobs.

## Beslutninger før en senere udførelse

Det foreslåede første omfang er **24 + 84 + 40 = 148 arrayversioner i 18 parrede støjblokke**, fordelt på tre særskilte udviklingstrin: fire tidsstøtteblokke, seks RFI/nær-OFF-blokke og otte fastbane-blokke. Det er en workloadsammenfatning, ikke en seedliste, bank, admission eller inferentiel kvalifikation. Blokke mellem trinnene skal have forskellige identiteter. Antal scans, grid og eventuelle baseline/prototype-scorepasses bestemmer den faktiske CPU-belastning; den er endnu ukendt. En senere plan må sætte et eget samlet loft og begrænse dimensioner før udfald, hvis omfanget ikke passer. Ingen fase forlænges efter attraktive eller skuffende resultater.

Før nye data eller nye scores skal en senere godkendt protokol fastlægge:

1. Den ønskede videnskabelige dækning: enkeltintegrationer, længere emissioner og enkelt-ON skal beskrives særskilt; afvisning af kort varighed alene accepteres ikke.
2. Tidsdescriptor, nulregler, event-/familiedefinition, den ene prototype og præcise støj-/amplitudekonventioner. Samme synlige data med forskellig oprindelseslabel skal have samme afgørelse.
3. Frekvensplacering, aktivitet, driftgrid, bredder, korrekt integration af driftudtværing, referencepunkter, maskering og alle lokaliseringsdefinitioner. Fast sandbane-statistik og søgeudvælgelse skal være forskellige felter.
4. Nye udviklingsidentiteter, rækkefølge, antal kørselspasses, komplet artefaktliste og målte ressourcegrænser. Ingen tidligere A/B/METHOD-case eller de gamle 112+128 holdouts bruges som frisk validering.
5. Hvilke resultater betyder stop, uafklaret eller videreudvikling. Der loves ikke nul RFI-rester og perfekt signalbevarelse på forhånd; kriterier til en efterfølgende kvalifikation skal være eksplicitte og kunne fejle.

Rækkefølgen er: accepter design og instrumentering → undersøg tidsprofiler → mål faste bane-statistikker og baselineomkostning → undersøg først derefter den ene familieprototype, hvis observerbarhed og budget er tilstrækkelige → dokumentér alle tradeoffs → vælg eller forkast én endelig metode → **ny freeze af kode, generator, score, tærskler, familier og endpoints** → senere, separat frisk kvalifikation. Ingen udviklingscelle bliver blind kvalifikation ved omdøbning. En sky-pilot kræver derefter bestået ny metodekvalifikation og sin egen kilde-/læserkontrol; dette dokument åbner ingen teleskopværdier.

De vigtigste uafklarede forhold er stadig: hvor meget af aliasernes ON-score den stærke RFI faktisk bidrager med; hvilke observerbare familiestrukturer der kan skelne separate komponenter; hvorvidt en kort hændelse har ekstern eller instrumentel oprindelse; behandlingens effekt på faste bane-statistikker; replikationsbehov; samt faktisk runtime og outputstørrelse. Den nuværende periode fortsætter med sine allerede fastlagte afslutnings-, reproduktions- og rapportmilepæle.
