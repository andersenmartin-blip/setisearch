# SETI · delvist BC-kontrolpunkt · 29. oktober 2026

**BC har gendannet og dekodet én yderligere række i HIP44295 / 65133. Hentningen stoppede derefter igen ved tunnel-403: 88 af 96 rækker er nu bevaret, og otte mangler. Der er fortsat ingen gennemført seks-scan-søgning eller kandidatvurdering.**

Den afsluttede autoritet er uændret BA: **486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg**. BB og BC er delvise og giver ingen ny krediteret dækning. [Det tidligere BB-kontrolpunkt](RADIO_PROGRESS_BB_PARTIAL_2026-10-29.md), alle BA-rapporter, oprindelige fejl og kilder bevares uændret.

## En normal præcis anmodning og én ny dekodet række

En særskilt normal adgangsanmodning til samme URL og det oprindeligt fejlede interval **8154457534–8157560831** i arkivfil **65143**, scan 5, gav HTTP 206 og præcis **3.103.298 bytes**, med faktisk procesexit 0. Der blev ikke brugt en anden vært, rute eller adgangsomgåelse.

Det modtagne interval er et **prefix af komprimerede power-data**. De sidste **13.580 bytes** af den fulde chunk var allerede kontaktet og bevaret i BB. En eksplicit lokal byteunion af nyt prefix og tidligere tail gav den fulde **3.116.878-byte chunk for række 7**. Den er en afledt lokal chunk, ikke én ny HTTP-206-kvittering for en helt ny fuld chunk.

Den oprindelige resultatkvitterings tæller `new_compressed_power_chunks_received = 1` er bevaret. Et særskilt scope-addendum præciserer, at den tæller ét nyt prefix-range. Addendummet blev skrevet **efter den afsluttede GET og før nogen BC-dekodning**; det påstås ikke at være et review før afsendelsen. Den tidligere kontakt til tail-bytes og de 87 tidligere BB-rækker er åbenlyst bevaret, og de ommærkes ikke som friske eller held-out.

Den efterfølgende recovery rekonstruerede de syv gyldige tidligere rækker i scan 5 fra cachen og dekodede den nye række 7. Samlet er der **88 gyldige rækker**: fem tidligere komplette kanoniske arrays og otte gyldige rækker i scan 5-partial. **Række 8–15 er stadig ikke hentede data.** De fem tidligere gentagelseskontroller er bevaret; ingen ny gentagelseskontrol er gennemført.

## Nyt stop, bevaret proces og adgangsgrænse

Recovery-processen sluttede **12:46:01 UTC / 13:46:01 dansk tid** med faktisk exit 1, afsluttet child-wait og EOF på sin hashkontrollerede log. Dens første nye netværksanmodning var et **16.384-byte TREE-metadatainterval 9241886720–9241903103**, samme arkivfil. Den fejlede med `Tunnel connection failed: 403 Forbidden` og **0 modtagne bytes**. Der er ikke dokumenteret et fjern-HTTP-svar for den fejlede forbindelse.

Rodens separate pollingkvittering bevarer, at en netværksgodkendelse blev afbrudt **før en afgørelse**. Ingen reviewerafgørelse eller begrundelse blev returneret; dette beskrives ikke som automatisk reviewafvisning og blandes ikke sammen med tunnel-fejlen eller et svar fra teleskoparkivet.

Efter grænsen er der foretaget **0 yderligere arkivanmodninger**: ingen retry, eskalering, anden vært/rute, proxyændring eller alternativ adgang. Arbejdet er lukket ved bevaring og offline-kontrol.

## Deltakontrol og faktisk afgrænsning

Den afgrænsede offline-deltakontrol består med **faktisk exit 0, afsluttet child-wait, EOF og korrekt procesloghash**, afsluttet **12:54:11 UTC / 13:54:11 dansk tid**. Den arver BB's hashbundne, tidligere beståede proof for 87 rækker, gen-dekoder kun BC-række 7, kontrollerer dens nye prefix/tidligere tail og TREE-deskriptor og sammenligner de syv tidligere gyldige scan 5-rækker. Det giver 88 gyldige rækker i den bevarede tilstand, ikke en ny uafhængig dekodning eller fuld native-gate for alle 88. Originalproofens SHA-256 er `44e0ece723e7908f072dc5b5fc763a811793134df45412ee4e19fe2e4597777a`.

Kontrollen foretog ingen netværksanmodninger. Den deler den oprindelige bitshuffle-codec og TREE-v1-model/traversering; det er ingen uafhængig dekoder eller astronomisk kvalifikation.

Der er ikke gennemført fuld native-gate, inputbinding, detektor, ON/OFF-triage eller kandidatvurdering. Afbrudte inputs er ingen gennemført nulmåling. Ingen kandidatklassifikation eller tidligere uafklaret sag ændres, og køen er ikke rykket videre.

## Faktiske nye faser i BC

| Fase | Nye forespørgsler | Bytes | Faktisk exit |
|---|---:|---|---:|
| Det præcise oprindeligt fejlede power-prefix | 1 | 3.103.298 modtagne, HTTP 206 | 0 |
| Recoveryens første nye TREE-metadatainterval | 1 | 16.384 forespurgte, 0 modtagne | 1 |
| Offline deltakontrol | 0 | Ingen nye teleskopbytes | 0 |

Den separate prefixproces målte 22,671961 sekunder i faktisk parent-tid; den efterfølgende recoveryproces 11,061341 sekunder. Byte- og tidsmål er faseafgrænsede og omfatter også det fejlede forsøg; de er ikke totalforbrug eller HTTP-wire-byteforbrug for hele SETI-projektets historie. BB's tidligere ressourceforbrug og fejl forbliver dokumenteret i det bevarede BB-kontrolpunkt.

## Præcist fortsættelsespunkt

Køpunktet er fortsat **HIP44295 / 65133** med **88 validerede rækker, otte manglende rækker og én manglende gentagelseskontrol**. De fem komplette arrays og scan 5-partial med kun række 0–7 gyldige skal bevares. En eventuel senere netværksfortsættelse kræver normal autoriseret adgang og en særskilt prospektiv plan for det nu præcist fejlede metadatainterval, tidligere kontaktede powers og hele cachen; afsluttede faser må ikke bare genstartes.

Ingen fuld originalfil-MD5, uafhængig dekoder, astronomisk følsomhed, global falskalarmrate, fysisk signaloprindelse eller ny observationsepoke er etableret. De historiske optagelser er fra 29. september 2016. Fortsættelsesproceduren omfatter igen dateret GitHub-evidens, opdaterede statusfiler, præcis readback og commit-identiteter i resume; der påstås ingen automatisk baggrundskørsel.

[Offline deltakontrol](results/radio_bc_partial_20261029/DELTA_AUDIT_PUBLIC.json) · [Recovery, scope-rettelse og bevarede grænser](results/radio_bc_partial_20261029/RECOVERY_EVIDENCE_PUBLIC.json) · [SHA-256-kontrolsummer](results/radio_bc_partial_20261029/SHA256SUMS).

De offentlige JSON-filer er kompakte, saniterede metadata-afledninger med de oprindelige artefakters hashes. De indeholder ingen teleskop-arrays og er ikke alene en fuld reproduktionspakke.
