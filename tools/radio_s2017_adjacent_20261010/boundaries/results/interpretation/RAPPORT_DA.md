# Beskrivende gennemgang af S2017-kanalgrænser

Ingen kvalificeret SETI-detektion er etableret (`qualified_claim=false`). De to færdige grænsefamilier omfatter 12 gemte ON-kort, 120 top20-rækker og 18 faste profiler med 108 scanningmålinger. Alt kommer fra samme besøg den 28. april 2017; profilerne blev valgt efter søgningen på de samme ON-data.

De 18 valgte rangscores spænder fra 5.082361 til 5.719388. Scoren er en robust, række-MAD-standardiseret sum langs en boksbane, divideret med kvadratroden af antal rækker gange kanalbredde. Den er ikke kalibreret SNR eller falskalarm-sandsynlighed. De 49.152 gemte carrier-maksima kommer fra 77.168.640 korrelerede drift/bredde-kombinationer.

Den faste middelværdi (centrum minus medianen af de faste flanker efter normalisering) er størst i udvælgelses-ON for 18/18 profiler. Udvælgelses-ON har positive middelværdier i begge halvdele for 18/18 profiler og 13–16 positive rækker ud af 16. Det er beskrivende egenskaber ved efterudvalgte spor, ikke uafhængig bekræftelse.

Udvælgelses-ON-middelværdierne er 0.038598–0.077338; de øvrige 90 faste scanningmålinger er -0.029050–0.047042. ON og OFF følger uændret referencefrekvens, drift og bredde ved de faktiske scanningtider. Små værdier på disse præcise OFF-baner kan ikke udelukke nærliggende OFF-struktur. Der er ikke beregnet OFF-veto eller OFF-søgescores.

| Grænse | Frekvens ved native-skel (MHz) | Referencedækning (MHz, kanalcentre) | ON1/ON2/ON3 top20 på venstre/højre kerne |
|---|---:|---:|---|
| pair170_171 | 2301.855468750 | 2301.844027452–2301.866912842 | 11/9; 9/11; 12/8 |
| pair171_172 | 2298.925781250 | 2298.914339952–2298.937225342 | 13/7; 11/9; 9/11 |

Hver grænse dækker 8.192 referencekanaler (22.888,183594 Hz) fordelt på to 4.096-kanals normaliseringskerner. De gemte top20-rækker beskrives med 16 faste frekvensbins og nabogab samt 64-kanals grupper i JSON. Grupperne er deskriptive; der er ingen test af klyngebetydning eller klassifikation af instrumental oprindelse. ON-scanningernes referencefrekvenser gælder forskellige første integrationsmidtpunkter.

6/18 faste baner har gemte kanalcentre på begge sider af native-skellet gennem de seks scanninger; 42 af 1.728 patch-rækker berører skellet med deres ±64-kanals vindue. Skellet er også grænsen mellem de to reference-/normaliseringskerner. Det er ikke kanten af det indlæste halo-udsnit eller et hul i data. Afstandene er geometri, ikke evidens for årsag.

Profilværdier og rangscores har forskellige normaliseringer: profiler bruger hele den sammenføjede float32-rækkes median over 2.097.152 kanaler, mens detektoren bruger den enkelte 4.096-kanals kerne og række-MAD. Profilresidualerne har ingen fluxenhed. Driftgitteret er −4 til +4 Hz/s i 785 trin; bredder er 1 og 3 kanaler (2,793968 og 8,381903 Hz). Der er ikke udført fit, frekvensforskydning eller ny optimering.

Alle præcise sporidentiteter, værdier, tidsrækker og input-byte-pins findes i JSON og CSV. Figuren `FIXED_SIX_SCAN_CONTEXT.png` viser alle 108 middelværdier; rammerne markerer den scanning, der udvalgte hvert spor. `SAVED_MAXIMA_REFERENCE_FREQUENCY.png` viser alle gemte carrier-maksima og de allerede gemte top20-punkter.

Provenance: faktisk grænse-QA SHA256 `48153e180358319feb3906fc719eabc9f224200933aa69eccbe0e20cdb8f1b36`; kilde-QA `21a8edaf91e9a60d3209d33e4620a5f93038aabfafd3910094bd25e0fd66318a`; faktisk ny acquisition `2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e`. Søgefreeze `2ba6ee3497abf3d24e5190df8630133f8a04bcb0`; QA-freeze `3eabb0e7582fc4a8c0bbb7975561128e008a7019`. QA autentificerede 222.912 patch-celler bitvist; denne rapport åbner kun gemte grænseresultater og metadata, ingen kilde-H5 eller ufærdige interiører.

Native171 var undersøgt, før de tilstødende native170/172 blev valgt. Beskyttede 2016-holdouts og oprindelige fejltilstande er uændrede. Der foreligger ingen blind bekræftelse, kalibreret falskalarmrate eller astronomisk oprindelsesbestemmelse.
