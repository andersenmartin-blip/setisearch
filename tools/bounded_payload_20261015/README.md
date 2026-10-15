# Kompakt payload og procesvagt integreret — 15. oktober 2026

**11 nye integrationskontroller består.** En tæt, konstrueret formatfixture med **61.440 ON-records og 184.320 OFF-kvitteringer** er skrevet, genlæst og kontrolleret felt for felt i en separat proces. Alle værdier, rækkefølger, identiteter og binary64-bits er bevaret. Der er intet nyt teleskop- eller signalresultat, og ingen videnskabelig bank er aktiveret.

## Det konkrete lagerresultat

| Repræsentation af samme konstruerede metadata | Bytes |
|---|---:|
| Indrykket/sorteret JSON som den tidligere metadatarepræsentation | 241.906.727 |
| Ny komplet pakke, inklusive et uændret 1 MiB-asset, nøglepulje og manifest | 4.560.903 |
| Metadata efter udpakning fra den nye repræsentation | 61.420.629 |

JSON-tallet er metadata alene. Pakkens tal omfatter også et opaque byte-asset på 1.048.576 bytes. Sammenligningen må derfor ikke læses som to identiske filinventarer. Ingen records eller kvitteringer er filtreret fra; float64, signed zero, int64/uint64-grænser, Unicode og feltrækkefølge er eksplicit efterprøvet.

De gentagne map-feltnavne lagres én gang i en pulje med 65 nøgler. Resten er den samme ordnede objektstruktur, skrevet som strømmet MessagePack med binary64 og gzip. Opaque assets kopieres byte for byte; formatet beregner eller afkoder ikke deres eventuelle tal. Det anvender ikke pickle. Den endelige verifikation var under den uændrede grænse på **128 MiB udpakkede metadata**.

Legacy-JSON blev talt og SHA256-målt gennem en sink, uden at skrive en ekstra 242 MB-fil. I den endelige producent brugte denne serialisering 14,506007 CPU-s; ny validering, semantisk hash, nøglepulje, pakning, filskrivning og filhashes brugte 17,301025 CPU-s. Arbejdet er forskelligt, så dette er **ingen påstand om hurtigere serialisering**. Den dokumenterede gevinst er plads og en afgrænset repræsentation uden tab.

## Faktisk integration

`executor.py` genbruger den nøjagtigt SHA256-pinnede [procesvagt](../whole_child_guard_20261015/guard.py). Begge child-fasers CPU-reservation og payloadens plads inklusive et særskilt kilde-/log-/kvitteringstillæg kontrolleres før producentstart. Et eksisterende forsøgsområde må ikke overskrives.

Producenten kan skrive en komplet pakke uden at opnå accept. Først efter hele producentens `wait4`-kvittering er accepteret, startes en særskilt overvåget verifikator. Den kontrollerer manifest, hvert filhash, udpakningsgrænse, alle dekodede metadata og alle konstruerede records; den rekonstruerer kun én forventet record ad gangen. Den efterregner også den fulde legacy-JSON-hash og det opaque assets bytehash. Forælderen binder derefter de uændrede slutbytes og begge proceskvitteringer i `ACCEPTED_ENGINEERING.json`.

Denne markør hedder udtrykkeligt **RESOURCE_AND_PAYLOAD_INTEGRITY_ONLY**. Ressource- og transportintegritet er ikke videnskabelig QA, recovery, kildeproveniens, FAP eller admission. API'et afviser `SCIENCE`; det kan alene sende de pinnede, konstruerede format-fixtures til udførelse.

De 11 kontroller dækker:

1. Eksakte edge-værdier, dictionary-/listerækkefølge og opaque bytes.
2. Hele det erklærede tætte recordantal gennem producent, vagt og separat verifikator.
3. Payloadkvote opbrugt midt i skrivning, med bevarede partials og ingen næste indsendelse.
4. Ændrede payloadbytes efter produktion, afvist af den separate verifikator.
5. CPU-stop efter en komplet payload; ingen verifikator, accept eller næste job.
6. Manglende outputreservation før launch.
7. Uunderstøttede værdier, cykler, nonfinite scalars og heltalsoverløb uden implicit casts.
8. Ekstra filer, afkortning, usikre navne og symlink med bevaret fejlevidens.
9. Ukendte extension-typer, dublerede nøgler og dekomprimeringsgrænse.
10. Afvist science-mode og afvist genbrug af et eksisterende forsøgsområde.
11. Reservation af begge CPU-faser før producentstart.

## Første afviste version er bevaret

Det første MessagePack/gzip-format komprimerede metadata og asset til 5.392.592 bytes, men det udpakkede objekt overskred 128 MiB. Verifikatoren afviste derfor korrekt den tætte fixture. De øvrige ti kontroller bestod. Grænsen, recordantallet, CPU-loftet og hukommelsesloftet blev ikke hævet. Nøglepuljen og strømmet pakning blev implementeret i en særskilt udviklingsversion, og alle 11 integrationskontroller blev efterprøvet på den ændrede kode.

Den første suites kilder og deres før-kørsel-pins findes i `history/attempt01`, dens logs og resultater i `results`. Slutversionens resultater ligger i `results_key_pool`. Den første afvisning er ikke ommærket til pass, og de to forsøg er ikke uafhængige videnskabelige valideringer.

Begge hele suites brugte tilsammen **104,074481 målte CPU-s**, inklusive reaped efterkommere. Slut-suiten brugte 69,378246 CPU-s og 69,110522 wall-s; dens peak-RSS var 395.575.296 bytes. Den særskilte **600-CPU-s engineeringreservation** beholdes fuldt, herunder 200 s til metadata/levering uden måling eller refundering. Den tidligere procesvagts 120-s reservation, alle gamle studieledgers og slutreserven genbruges ikke.

## Fortsættelsespunkt og begrænsninger

Dette er **PREPARED_BOUNDED_ENGINEERING_PATH_ONLY**. Den tætte fixture stresser `3 × 4096 × 5` beholdte ON-records og tre OFF-kvitteringer pr. record. Tallene er formatdata. Den udfører ingen driftsøgning, indsprøjtning, RNG, normalisering eller numerisk OFF-traversering. `inventory_rows` i fixturekvitteringerne er et konstrueret felt, ikke en faktisk beregning af to millioner OFF-rækker. Ingen gamle videnskabelige arrays eller holdouts er åbnet.

Dette ene lagerresultat beviser derfor **ikke**, at alle fulde cases, maksimale OFF-inventarer, numeriske kort, QA-payloads og hele et nyt studie kan rummes i en fremtidig ramme. Formatet er heller ikke integreret med den videnskabelige worker, summarizer og QA. Næste konkrete gate er et særskilt prospektivt afgrænset **fuldt per-case payload- og adapterforløb**, med komplette array-/inventory-bounds og kumulativt budget, før en ny videnskabelig bank overhovedet kan overvejes. Alle eksisterende engangskrav og videnskabelige gates skal med; den lukkede bank må ikke genoptages.

Koden gælder pinnede, kooperative enkeltprocesser. Den giver ingen adversarial filesystem- eller absolut scheduling-garanti. Konfigurationsgrænser er en del af kaldets faste engineeringpolitik. Outputkvoter gælder den kontrollerede bundle-writer, og forælderen kontrollerer det samlede output før accept. Reproduktion kræver en ny isoleret kopi og et særskilt reserveret forsøgsområde; gamle mapper og fejl skal bevares.

Original A/B og seks-scan-banken er fortsat **FAIL_CLOSED**. 2016, 2019 og alle øvrige pauser bevares; ingen beskeder, køb eller nye teleskoprequests/-bytes. **0 DKK.** Det formelle checkpoint er stadig **20. oktober 2026**.

[Frosset engineeringramme](ENGINEERING_SCOPE.json) · [Formatændring](FORMAT_CHANGE_01.json) · [Evidensindeks](EVIDENCE_INDEX.json) · [Payloadpakkeidentitet](ARCHIVE_IDENTITY.json)
