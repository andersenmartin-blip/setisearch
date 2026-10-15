# Fuldt numerisk payload-footprint efterprøvet — 15. oktober 2026

**498 arrays og samtlige 612.781.396 rå arraybytes er skrevet og separat genlæst under procesvagt.** Den konstruerede pakke fylder **120.484.899 bytes** inklusive de genbrugte tætte recordmetadata. Alle NPY-headere, dtypes, former, arrayrækkefølger og komplette rå bytehashes består kontrollen. Status er **FULL_CASE_ENGINEERING_TRANSPORT_ONLY**. Dette er ingen videnskabelig case, signalgenfinding eller QA-kvalifikation.

## Hvad der faktisk er transporteret

Layoutet er udledt af offentlig kildekode og kontraktgeometri, uden at åbne gamle videnskabelige arrays eller engangsidentiteter. Numrene er deterministiske array-indeksmønstre, ikke en støjmodel, indsprøjtning eller teleskopmåling.

| Numeriske felter | Rå bytes |
|---|---:|
| Seks float32 inputfelter, hver 16 × 12.096 | 4.644.864 |
| Alle 14 numeriske mapfelter for tre ON- og tre OFF-scans | 10.737.252 |
| Alle seks normaliseringsfelter i hver scan | 200.448 |
| Tre OFF-inventarer, hver 2.000.000 rækker og alle ni felter | 576.000.000 |
| Alle 5.723 driftværdier og 6 × 16 rækketider | 46.552 |
| Alle 84 aliasblokke ved konservativt maksimum 5.723 stier | 21.152.208 |
| To ekstra IEEE/endian-bit-fixtures | 72 |
| **I alt** | **612.781.396** |

De 498 arrays omfatter **460 felter, som er NumPy-arrays i den gamle payloadstruktur, 36 numeriske normaliseringslistefelter repræsenteret som arrays i dette adapterforsøg og to ekstra bit-fixtures**. Det er ikke en påstand om, at den gamle fil havde 498 NPZ-medlemmer. De oprindelige listetyper skal håndteres eksplicit i en fremtidig videnskabelig adapter.

Hvert OFF-inventar har syv int64-søjler, en float64-score og fire int64-centre pr. række: 96 bytes pr. række, i alt seks millioner rækker. Aliasgrænsen er et sikkert antal transportpladser ud fra det fulde driftgitter; der er ikke udført en ny geometrisøgning for at fylde den.

De tidligere **61.440 ON-records og 184.320 OFF-kvitteringer** blev genbrugt fra deres pinnede engineeringcache. De blev ikke genereret eller søgt igen. Deres komprimerede metadata er byteidentiske; den sammensatte pakke blev kontrolleret med de ekstra numeriske assets. Dette er fortsat formatdata uden ny signalevidens.

## Hukommelse, integritet og forbrugeradapter

`array_adapter.py` skriver ét array ad gangen som pickle-fri NPY inde i ZIP. Rå inputbytes hashes før skrivning. Den separate verifikator kontrollerer hele medlemsinventaret, hvert begrænset NPY-headerfelt og alle rå bodybytes i blokke, inklusive CRC-afslutning. Den behøver ikke materialisere alle arrays samtidigt. Tomme `(0,4)`-inventarer, 0-D skalarer, endian-forskel, signed zero, NaN-payloadbits og infinities er særskilt bevaret som transporttests; de er ikke godkendte videnskabelige inputværdier.

Producenten brugte **8,770314 målte CPU-s** og peak-RSS **217.518.080 bytes**. Verifikatoren brugte **16,945062 CPU-s** og peak-RSS **409.038.848 bytes**. Begge havde 240 CPU-s og 1 GiB adressegrænse, og begge blev målt efter fuld afslutning med den SHA-pinnede procesvagt. Den komplette NPZ er 115.713.711 bytes; kompressionen gælder kun de erklærede indeksmønstre og kan ikke antages for andre data.

`load_case_field` kan hente et enkelt typed felt via dets entydige kildefeltsti. Den separate `legacy_bridge.py` blev efterprøvet mod **de uændrede funktioner `decode` og `array_sha`** fra den offentlige QA-kilde. Kun disse AST-funktioner blev udvalgt; QA-modulet, `main`, admission, RNG og numerisk QA blev ikke kørt. Seks arrays, inklusive et int64 `[2000000,4]` på 64 MB, bestod 18 eksisterende descriptor-checks og ekstra bitkontrol. Tre ændrede descriptors blev afvist.

Det første isolerede interfaceforsøg manglede NumPy-bindingen, som den gamle hashfunktion forventer i sit globale namespace. Det fejlede og er bevaret med nøjagtig kilde og scope i `history/compatibility_attempt01` og `results/legacy_interface_process`. En særskilt revision rettede namespace-opsætningen og bestod. De gamle dekoderfunktioner blev ikke ændret; intet fejlet videnskabeligt resultat er ommærket til pass.

En rapporteringsfejl blev fundet før publicering: en genbrugt kommandoliste får producentfeltet i de oprindelige `STATE.json` og `SUMMARY.json` til at vise `verify`. Den særskilt gemte og hashbundne producentkvittering viser korrekt `produce`; CPU-, byte- og verifikationsresultater er uændrede. Originalfilerne og suitekilden bevares. Fremtidige kald tager nu en dyb kopi af kvitteringen. Dette er kildeinspiceret; den afsluttede fulde suite er ikke gentaget. Se [præcis begrænsning](results/REPORTING_LIMITATION.json).

Fem hovedgrupper består: komplet layout, tomme/skalar/endian-felter, fem konkrete korruptions-/kvotefejl, matematisk kapacitetsafvisning og fuld bevogtet transport. Derudover består den afgrænsede gamle descriptor-interfacekontrol. Alle fejl og partials er bevaret.

## Hvad lagergrænsen fortæller

Den fysisk håndhævede, betingede casegrænse er **752.315.732 bytes**. Den omfatter rå arraystørrelser, eksplicit NPY/ZIP-headerplads, metadata-/descriptorgrænser og øvrige faste tillæg. Hvis kompression eller et headerloft ikke kan holde denne ramme, afvises forsøget; tallet er ikke en universel kompressions- eller færdiggørelsesgaranti.

En ren matematisk sammenligning viser, at 3 GiB kan reservere fire sådanne maksimumpladser. 428 ens maksimumpladser ville være 321.991.133.296 bytes. **Det er ikke målt behov eller et budgetforslag for et nyt studie.** Den oprindelige QA skriver andre kvitteringer og er ikke identisk med en fuld producentpayload. Et rigtigt nyt budget skal afgrænse primær-, QA-, eksponeret- og eksponeret-QA-faser separat. Ingen gammel ledger blev åbnet, nulstillet eller anvendt som fri kapacitet i sammenligningen.

## Ressourcer og fortsættelsespunkt

Den store suite og begge interfaceforsøg brugte tilsammen **27,910018 målte CPU-s** uden dobbeltoptælling af indre kvitteringer. Den særskilte **900-CPU-s engineeringreservation** beholdes fuldt, inklusive 300 s til metadata/levering uden måling eller refundering. Alle tidligere 120-/600-s engineeringreservationer, gamle studieledgers og reserven til 20. oktober bevares. Pris og nye teleskoprequests/-bytes er **0**.

Denne fortsættelse lukker den erklærede numeriske transportopgave. Den kvalificerer ikke den videnskabelige worker eller uafhængig QA ved maksimal geometri. Den gendanner ikke en fuld gammel videnskabelig case med kildeproveniens, truth, fase-admission og alle forbrugersemantikker. Den gamle QA's samlede hukommelsesbehov og normaliseringslistetyper er heller ikke kvalificeret af seks array-interfaceeksempler.

**Næste konkrete gate:** prospektiv, særskilt integration af den nye transport med videnskabelig worker, QA og summarizer, inklusive alle metadata-/listetyper, engangsidentiteter og faseopdelte kumulative outputreservationer. Først derefter kan en ny bank overvejes. En ny bank kræver egen offentlig frysning og admission; den lukkede bank må ikke genoptages eller genkøres.

Original A/B og seks-scan-banken forbliver **FAIL_CLOSED**. 2016, 2019 og alle øvrige HOLD/pauser bevares. Ingen ny observation, besked, booking eller køb. Det formelle checkpoint er stadig **20. oktober 2026**.

[Layout og bytegrænser](ARRAY_LAYOUT.json) · [Hovedresultat](results/suite/SUMMARY.json) · [Fuld verifikation](results/suite/complete_case/VERIFICATION.json) · [Descriptor-interface](results/LEGACY_INTERFACE_RESULT.json) · [Evidensindeks](EVIDENCE_INDEX.json) · [Binær pakkeidentitet](ARCHIVE_IDENTITY.json)
