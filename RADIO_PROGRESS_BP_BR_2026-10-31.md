# BP–BR: 23 kontroller godkendt; sidste kontrol blokeret af filintegritet

**23 af de 24 planlagte parrede syntetiske kontrolforløb er godkendt. A04 er fortsat ikke afsluttet som et kvalificeret parret forløb.** Den seneste BR-kørsel stoppede korrekt, da en fil ændrede sig under verificering. Ingen astronomiske HIP45688-powers er åbnet, og ingen ny teleskopsøgning er udført.

| Kontrol | Resultat for begge metoder | Status |
| --- | --- | --- |
| Otte baggrundscadencer | Ingen fuldt understøttede tre-ON/no-OFF-flag | 8 bestået |
| Seks stærke indlagte signaler | Alle seks genfundet ved den kendte bane | 6 bestået |
| Seks svage indlagte signaler | To stationære signaler genfundet; fire driftende signaler ikke genfundet. Ingen legacy-only genfinding tabt af current | 6 bestået efter den fastlagte sammenligningsregel; ikke seks genfundne signaler |
| A01/A02: signal i alle scans | Understøttet OFF-veto | 2 bestået |
| A03: signal kun i første ON | Understøttet tre-ON-afvisning | 1 bestået |
| A04: bred gain/burst | Delresultater bevaret; parret afslutning ikke kvalificeret | Blokeret |

BP blev præregistreret i `ee9ff94abfaa56055f947036b80133393cf209f8`, før første RNG-kald. Alle 48 syntetiske grundarrays og 144 parrede scanberegninger er bevaret. Begge metoder får identiske, skrivebeskyttede float32-input. Legacy beholder global kalibrering over hele sit oprindelige interior inklusive q128; current kalibrerer lokalt i q63/64/65/127/129. Kontrollen bruger fem på forhånd valgte driftrater og bredderne 1/3/9/33. Association følger den særskilt erklærede BP-regel med destinationsbåndets kalibrering, ikke BN's tidligere source-q-regel.

Der er 43.200 udvalgte current-summer mod uafhængig `math.fsum`, med nul målt afvigelse, og lige så mange kontroller af legacy's trinvise float32-regning. **124 nye overskridelser af den oprindelige absolutte 5e-5-guard står fortsat som FAIL.** Den særskilte BP-gennemgang kontrollerede 14.400 lokale kalibreringsvektorer, 28.800 ESS-vektorer og alle 144 fælles input. De historiske 24 HIP45688-M-fejl og fuld-QA=false ændres ikke.

## Tre adskilte kørselsidentiteter

**BP: FAIL med 23 beståede kontroller.** A04 afsluttede alle seks scanberegninger, men ramte den oprindelige 2 GiB RSS-grænse under opbygning af associationslisten. Det faktiske child-exit var −9; stop, wait, EOF og oprydning er bevaret. Hele BP tog 522,58 vægsekunder. Ingen automatisk genkørsel af BP-identiteten er foretaget.

**BQ: proces-exit 0, men effektiv evidensstatus FAIL.** En særskilt præregistreret streaming-afslutning (`f23febded4d6e49fea898e32db509f9241557455`) brugte kun de gemte A04/N04-scorer. Den aktuelle resultatfil indeholdt 36.857 af de 43.306 erklærede linjer: 6.449 manglede, og størrelse/hash stemte ikke med resultatets egen afslutningskvittering. Terminalen bandt allerede den kortere fil. Alle bevarede current-linjer er verificeret som det korrekte præfiks; alle 43.845 legacy-linjer er komplette og verificerede. BQ's oprindelige capture-PASS bevares som en historisk proceskvittering, men giver ingen gyldig parret afslutning.

**BR: korrekt stop med faktisk exit 2.** Ny kode til atomisk publicering samt kontrol ved child-/parent-afslutning blev præregistreret i `afe631ffd7bb9d3002938be6680a9963fcfb450d`. Den består 21 deterministiske tests, oven i BP's 22 og BQ's 11. Under den særskilte BR-identitet opdagede kontrollen en ændring af den endnu ikke publicerede legacy-fil under verificering og afviste afslutningen. Den komplette current-strøm har 43.306 verificerede linjer; legacy-præfikset har 33.743, og 10.102 mangler. De manglende linjer er ikke fyldt ind. Den nye kontrol giver ingen falsk effektiv PASS.

**Årsagen til filændringerne er uafklaret.** Den uafhængige BR-gennemgang bekræftede de bevarede bytes, præcist exit, naturlig EOF, oprydning samt alle 25 kilde- og 62 inputbindinger. Ingen af de tidligere fejl, filer eller identiteter er slettet eller omklassificeret til PASS. Ingen manglende evidens er rekonstrueret for at få en kontrol godkendt.

## Evidens og fortsættelsespunkt

De komplette grundarrays, BP-kontrolevidens og begge fejlede afslutninger er gemt i kontrollerede arkiver. Alle 16 leverede filer er genhashkontrolleret efter lagring. Filidentiteter og links findes i [leveringsoversigten](work_br/DELIVERY_BP_BR.json); den kompakte autoritative status findes i [SUMMARY_BP_BR.json](work_br/SUMMARY_BP_BR.json). Kode, præregistreringer, reviewrapporter og proceskvitteringer ligger i `work_bp`, `work_bq` og `work_br`.

**Næste trin er en særskilt afgrænset teknisk undersøgelse af filstabiliteten.** Ingen yderligere automatisk A04-genkørsel er startet. A04 skal have en fuldt dokumenteret afslutning, før den særskilte fulde 839-rate-kontrol, DATA-admission og en senere HIP45688-søgning kan aktiveres. Alle ejede processer er afsluttet.

Dette arbejde tilfører 0 nye observationer, 0 teleskoparkivforespørgsler og 0 ny dækningskredit. BA's tællere forbliver uændrede. De afgrænsede syntetiske kontroller er ikke en kalibreret falsk-alarm-sandsynlighed, generel recovery-rate, astronomisk følsomhed, flux/EIRP eller et astronomisk fund/ikke-fund.
