# SETI · delvist BB-kontrolpunkt · 29. oktober 2026

**HIP44295 / 65133 er delvist hentet og er ikke søgt. Payloadfasen lukkede med faktisk exitkode 1 efter 87 af 96 rækker.** Den afsluttede BA-status er fortsat autoriteten: **486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg**. BB giver ingen ny krediteret søgedækning eller kandidatvurdering.

## Verificeret afgrænsning før powers

Kataloget og alle seks faktiske filhoveder er kontrolleret. De valgte arkiv-ID'er er 65133, 65135, 65137, 65139, 65141 og 65143, adskilte fra de tidligere krediterede 486 ID'er. Alle optagelser er fra **29. september 2016** med fælles instrumentkonfiguration. Headerne fastlagde native-chunk 171, global startkanal 179306496 og kernen **2298,9372281357646–2301,844024658203 MHz**, før nye powers.

Et oprindeligt FOLLOWUP_FREEZE-forsøg afsluttede med faktisk exit 1 på grund af en manglende metadataforudsætning. Det producerede ingen plan eller powers. Den særskilte metadatarettelse og FOLLOWUP_FREEZE_READY afsluttede med faktisk exit 0 før powers, uden numerisk kodeændring. Den oprindelige fejl er bevaret.

Den lokale metodeafgrænsning og prepower-plan blev fastlagt før payloadfasens start **07:38:25 UTC**. Numeriske udtryk, normalisering, tærskler, driftsområde og regler er uændrede. Denne efterfølgende GitHub-publicering er ikke en påstand om offentlig forhåndsregistrering.

## Faktisk stop og bevarede inddata

Payloadprocessen sluttede **07:55:48 UTC / 08:55:48 dansk tid** med faktisk exit 1, afsluttet child-wait og EOF på den bevarede log. Den registrerede **87 komplette rådata-rækker, fem komplette kanoniske scan-arrays og fem gentagelseskontroller**. Den sidste af de seks scanninger er ufuldstændig.

Den fejlende anmodning vedrørte scan 5, arkiv-ID **65143**, byteinterval **8154457534–8157560831**, inklusive endepunkter. Fejlen var `Tunnel connection failed: 403 Forbidden`; **0 bytes blev modtaget**, og der foreligger intet fjern-HTTP-svar for dette forsøg. Et tunnelproblem er derfor ikke dokumentation for, at teleskoparkivet returnerede HTTP 403. En ventende netværksgodkendelse blev afbrudt før en afgørelse; dette registreres ikke som automatisk afvisning.

Der blev ikke foretaget automatiske gentagelser eller forsøg via en anden vært, rute eller adgangskontrol. Fejl, præcist interval, delvise filer, kilder, transportkvitteringer og proceslog er bevaret.

Den særskilte offline-kontrol af de delvise inddata består med **faktisk exit 0, fuld EOF og en hashkontrolleret proceslog**, afsluttet **08:06:36 UTC / 09:06:36 dansk tid**. Den har verificeret 87 komprimerede chunks, 87 bevarede TREE-deskriptorer, 240 eksisterende HTTP-kvitteringer og de erklærede gyldige power-bytes. Fem arrays er komplette. I scan 5 er kun **række 0–6 gyldige: syv rækker**; de øvrige **ni allokerede rækker er ikke hentede data**, er ikke valideret og tælles ikke.

Kontrollen bruger den oprindelige bitshuffle-codec og den delte TREE-v1-model/traversering. Det er en afgrænset bevarings- og inddata-kontrol, ikke en uafhængig dekoder. Den foretog ingen nye netværksanmodninger eller detektorsøgninger. Originalproofens SHA-256 er `cce5225ebb425c18bc0da910f80161efdc25151de702db5e81e8aa2451b210dd`.

En delvis inddata-kontrol er ingen gennemført seks-scan-søgning. Der er ikke kørt detektor, ON/OFF-triage eller kandidatopfølgning for BB. Kandidatvurderingen er **ikke udført**; det afbrudte besøg er ikke et analyseret nulresultat. Tidligere uafklarede sager bevarer deres dispositioner.

## Faktiske ressourcefaser

| Fase | Forespørgsler | Byteafgrænsning | Faktisk exit |
|---|---:|---|---:|
| Katalog | 1 | 10.900 modtagne bytes | 0 |
| Seks filhoveder | 12 | 122.880 forespurgte bytes | 0 |
| Delvis payload, inklusive fejlet anmodning | 229 | 291.589.560 forespurgte bytes | 1 |
| Offline delvis inddata-kontrol | 0 | Ingen nye teleskopbytes | 0 |

Payloadkørerens egen fasevarighed er 1042,765395 sekunder; den faktiske parent-målte procesvarighed er 1043,133194 sekunder. Forespurgte bytes er ikke det samme som modtagne bytes eller HTTP-wire-byteforbrug; den fejlede anmodning modtog nul. Forberedelsesfejlen og det fejlede payloadforsøg er medtaget og bevares. Dette er intet samlet regnskab for hele projektets historie.

## Fortsættelsespunkt og begrænsninger

Næste køpunkt er fortsat **HIP44295 / 65133**. Før en eventuel ny netværksanmodning kræves en særskilt prospektiv genopretningsplan, der identificerer de allerede læste metadata/powers, den bevarede cache og det præcist fejlede interval. Afsluttede katalog-, header- og rådatafaser må ikke bare genstartes. Ingen ny kandidatregel, tærskel eller status ændres af dette kontrolpunkt.

Denne dokumentation giver ingen kalibreret global falskalarmrate, astronomisk følsomhed, komplethed, fysisk signaloprindelse eller ny observationsepoke. Ved en senere afsluttet fortsættelse skal dateret evidens og status igen publiceres på GitHub, læses præcist tilbage og bindes til resume-metadata. Proceduren er ingen påstand om automatisk baggrundsarbejde.

[Offline delvis inddata-kontrol](results/radio_bb_partial_20261029/PARTIAL_AUDIT_PUBLIC.json) · [Publiceringsevidens og bevaret fejl](results/radio_bb_partial_20261029/PUBLIC_EVIDENCE.json) · [SHA-256-kontrolsummer](results/radio_bb_partial_20261029/SHA256SUMS).

De offentlige JSON-filer er kompakte, saniterede metadata-afledninger med originalartefakternes hashes. De indeholder ingen teleskop-arrays og er ikke alene en fuld reproduktionspakke.
