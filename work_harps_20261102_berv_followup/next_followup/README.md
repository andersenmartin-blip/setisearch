Det næste mulige skridt er en **ny, særskilt opfølgning med fokus på referencekvalitet** for HD122640. Den foreløbige kandidat er `ADP.2017-05-21T01:01:50.278`, observeret 20. maj 2017: den har højest registreret gennemsnitlig SNR blandt de ni ubrugte majeksponeringer, **77,8**, mod **16,6** for den allerede undersøgte majreference. Ingen nye headers, spektre eller arrays er læst her; der er ingen ny udførelsesfrysning.

Valget er udtrykkeligt **posthoc**: spørgsmålet opstår, fordi den afsluttede majreference havde lav lokal kontinuumkvalitet i 10 af 12 profiler. Den oprindelige, faste undersøgelse er færdig med to ekstra arkiveksponeringer, seks HD122640-poster og 24 profiler. Den skal ikke udvides, erstattes eller genkøres. Januarreferencen gav barycentriske korrelationer 0,960855–0,974263 for de fem blå poster; posten V2E2-0235 ved 5548,09 Å havde svage sammenfald i begge epoker. Ingen af disse mål bestemmer fysisk ophav. Alle ti poster forbliver U.

Den gemte officielle ESO-schemabeskrivelse definerer `snr` som spektrets **gennemsnitlige** signal/støj-forhold. Tallet garanterer ikke bedre lokalt kontinuum ved 3866–3881 Å, kalibrerede fejl eller højere følsomhed. Den foreslåede kandidats BERV, mode, repræsentation og lokale flux er endnu ikke kontrolleret. Reglen bruger kun allerede gemte metadata: højeste endelige positive SNR blandt ubrugte HD122640-eksponeringer observeret i maj 2017; ved lighed vælges det leksikografisk første DP-id. Ingen linjeflux bruges til dette valg.

Det konkrete forslag til næste fortsættelse er først at skrive, kontrollere og publicere en særskilt plan for **én header og højst ét efterfølgende spektrum** med dette eksakte id og råforløber `HARPS.2017-05-20T02:21:45.847`. De foreslåede grænser er ét forsøg pr. trin, 30 sekunder / 512 KiB for headeren og 60 sekunder / 16 MiB for spektret, uden retries eller redirects. Identitet, mode, repræsentation og den tilsigtede store BERV-forskydning skal verificeres før payloadfrigivelse. Det er et kvalitetsforsøg; kandidaten behøver ikke udvide det allerede målte BERV-spænd på **40,363479 km/s**.

En eventuel ny sammenligning skal bevare alle seks HD122640-poster i begge rammer: højst 12 nye profilpladser, også V2E2-0235. Brug de uændrede centre, vinduer og beskrivende mål. Bevar begge tidligere referencer og alle svage eller blokerede udfald. Ved fejl stoppes den nye fase uden automatisk at tage den næstbedste majkandidat. Dette forslag er ikke tilføjet den afsluttede protokol og er ikke udført.

`UNUSED_METADATA_POOL.csv` indeholder alle **16 ubrugte produkter**: ni fra maj 2017 og syv fra januar 2018, med observationsdato, SNR, offentlig frigivelse, rå-id og identitetsmetadata. De er resten af den gemte pulje på 18 efter de to afsluttede eksponeringer. De ni majprodukter ligger mellem SNR 56,3 og 77,8.

| Ubrugt produkt | Gennemsnitlig metadata-SNR |
| --- | ---: |
| ADP.2017-05-21T01:01:50.278 | 77,8 |
| ADP.2017-05-21T01:01:50.250 | 72,7 |
| ADP.2017-05-21T01:01:50.260 | 56,3 |
| ADP.2017-05-22T01:02:00.516 | 61,6 |
| ADP.2017-05-22T01:02:00.514 | 72,3 |
| ADP.2017-05-22T01:02:00.520 | 70,4 |
| ADP.2017-05-22T01:02:00.550 | 59,8 |
| ADP.2017-05-23T01:01:52.445 | 73,9 |
| ADP.2017-05-23T01:01:52.427 | 72,8 |
| ADP.2018-01-17T01:01:37.361 | 74,3 |
| ADP.2018-01-19T01:01:35.335 | 72,5 |
| ADP.2018-01-19T01:01:35.353 | 72,6 |
| ADP.2018-01-20T01:01:32.863 | 76,2 |
| ADP.2018-01-20T01:01:32.889 | 86,3 |
| ADP.2018-01-21T01:01:37.751 | 68,5 |
| ADP.2018-01-21T01:01:37.771 | 74,0 |

De ti bevarede poster er **V2E2-0229, 0231, 0234, 0235, 0236, 0237** for HD122640 og **V2E2-0303, 0305, 0308, 0309** for HD135204; alle har præfikset `V2E2-`. `PRESERVED_TEN_EVENT_QUEUE.csv` bevarer de fulde id'er, discovery-identiteter og hashes. HD135204 fik ingen egnede rækker under den afsluttede, afgrænsede forespørgsel; det er ikke dokumentation for, at hele arkivet mangler andre observationer. Dets kendte BERV-spænd er fortsat 1,714121 km/s.

Den oprindelige hovedprøve forbliver 300 eksponeringer, med de to ekstra eksponeringer registreret særskilt som opfølgning. Status er stadig **403 A / 46 O / 185 U / 35 M / 0 N** for 669 V2-poster. Den færdige 24-profilanalyse, mapping-kontrollen af alle 35 M, normaliseringsopfølgningen af V2E2-0092/0104, de oprindelige 4.370 epokeprofiler og de afsluttede Rubin-forsøg skal ikke genstartes for at nå dette punkt.

`HANDOFF.json` angiver den maskinlæsbare fortsættelse. `SOURCE_HASHES.json` og `PRESERVATION_CHECK.json` binder de læste metadata og gemte resultater; `INDEPENDENT_CHECK.json` bekræfter uafhængigt puljen, den foreløbige SNR-regel og de uændrede labels. Reproduktion af denne handoff sker med `python3 build_handoff.py` og læser kun JSON-/CSV-metadata, ingen spektralarrays.
