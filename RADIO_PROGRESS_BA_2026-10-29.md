# SETI · BA afsluttet · 29. oktober 2026

**HIP92283, arkivbesøg 65097, er færdiganalyseret under de uændrede regler. Den afsluttende artefaktkontrol består med faktisk exitkode 0. Ingen SETI-kandidat er accepteret.**

Dette er et nyt dateret tillæg efter [det bevarede delvise kontrolpunkt](RADIO_PROGRESS_BA_PARTIAL_2026-10-29.md). PARTIAL-rapporten, AZ's oprindelige netværksfejl og alle efterfølgende fejlede forsøg er bevaret uændret. Slutkontrollen blev afsluttet **29. oktober kl. 06:44:12 dansk tid**.

## Teknisk dækning og konkret udfald

Med AY som arvet historisk baseline er den afsluttede tekniske status nu **486 unikke arkiv-ID'er og 268,50128173828125 MHz-besøg**. BA tilføjer seks arkiv-ID'er og **2,90679931640625 MHz-besøg** for én seks-fil-cadence. Bredden ganges ikke med seks. Disse mål er ikke antal uafhængige stjerner, unik sammenhængende frekvensdækning, fysisk følsomhed eller nye observationsepoker. Arkivoptagelserne er fra **29. september 2016**; der er ikke foretaget en ny teleskopobservation.

| Resultat i den afsluttede BA-søgning | Udfald |
|---|---:|
| Kontrollerede native-rækker / kanoniske scan-arrays | 96 / 6 |
| Afsluttede detektorkørsler med faktisk exit 0 | 6 |
| Korrelerede ON-katalogrækker | 101.188 |
| Rækker med mindst ét OFF-flag | 456 |
| Tvungne målepladser med fuld støtte | 607.128 |
| Alle tre ON over grænsen uden OFF-flag, center / nabolag | 0 / 0 |
| Frekvensgrupper med præcis 1 / 2 / 3 ON | 7 / 0 / 0 |
| Hovedopfølgning / supplerende kontekster gennemgået | 1 / 6 |
| Afventende kontekstgrupper | 0 |
| Accepterede SETI-kandidater | 0 |

De mange katalogrækker og hypoteser er korrelerede og er ikke uafhængige signaler. Syv grupper med præcis én ON er ikke syv accepterede kandidater. Tidligere uafklarede sager bevarer deres dispositioner.

Alle seks søgninger, den afgrænsede numeriske gennemgang, hovedopfølgning med review, supplerende kontekst med review og kontrol af ti bevarede PNG-figurer er afsluttet. De 121 kopierede videnskabelige kildefiler bevarer deres oprindelige bytes; normalisering, detektor, tærskler, driftsområde, udvælgelse og gates er uændrede. Slutkontrollen afstemmer disse artefakter og proceskvitteringer; den genberegner ikke hele det historiske projekt eller AY på ny.

## Gendannelse, fejl og datalinje

Den tidligere blokerede metadataanmodning lykkedes først med præcis 16.384 bytes. Den næste rådatafase stoppede med faktisk exit 1 efter seks registrerede rækker: transporten havde korrekt genbrugt en cache-del, men den efterfølgende provenienskontrol krævede fejlagtigt én ny HTTP-206-kvittering for hele den sammensatte chunk. Denne fejl blev bevaret.

En separat prospektiv V2-korrektion repræsenterer lokalt sammensatte byteforløb med deres faktiske cache- og netværkssegmenter. Den efterfølgende inddatareview V4 fejlede også med faktisk exit 1 ved en Content-Range-skema-kontrol. En særskilt V5 skelner korrekt mellem afledt lokal byteidentitet og de HTTP-206-felter, der kun tilhører reelle gentagelsessvar. V5 består alle 96 rækker, seks arrays og de seks bevarede gentagelseskontroller. Ingen af de fejlede processer er omdøbt til bestået, og et sammensat lokalt payload udgives ikke som én HTTP-response.

Af de 96 rækker var 48 allerede læst i AZ og seks yderligere i BA's fejlede første rådatafase. Række 6 i scan 3 blev desuden dekodet under offline-fejlundersøgelsen. V2-kørerens tæller på 42 nominelle førstegangsdekodninger omfatter derfor kun **41 globalt hidtil udekodede rækker**; de seks tidligere BA-rækker blev rekonstrueret igen fra cachen. Dette er gendannelse med åben datalinje, ikke en ny held-out-søgning eller 96 friske downloads.

| Netværksfase i BA, inklusive fejlet arbejde | Forespørgsler | Registrerede bytes |
|---|---:|---:|
| Enkelt metadatarecovery | 1 | 16.384 modtagne |
| Første rådatafase, faktisk exit 1 | 13 | 21.730.775 forespurgte |
| V2-rådatafase, faktisk exit 0 | 104 | 137.206.198 forespurgte |

V2-køreren målte **602,875118 sekunder**. De viste byte-/tidsmål har deres oprindelige faseafgrænsninger; de er ikke et samlet historisk projektregnskab eller HTTP-wire-byteforbrug. Fejlede forsøg og gentagelser er medtaget.

## Begrænsninger og fortsættelse

Denne afslutning etablerer en gennemført teknisk søgning med dokumenteret gendannelse. Der foreligger ingen ny kvalifikation af astronomisk følsomhed, global falskalarmrate, komplethed, hele originalfilens MD5 eller fysisk signaloprindelse. Codec/interpolation deles fortsat, og rådatahentning og native-deskriptorkontrol deler TREE-v1-modellen; det er ingen uafhængig kvalifikation af hele indhentningsmodellen. Alle seks kanoniske arrays skal bevares direkte eller via de præcise oprindelige arkivreferencer; ingen array-udeladelsesgate er godkendt.

Efter denne afslutning er næste uændrede køpunkt **HIP44295 / 65133**. Før videre arbejde læses det afsluttede checkpoint og den bevarede kø. Nye søge- eller kandidatregler skal fastlægges før ny spektralkontakt; tidligere læste powers må ikke ommærkes som friske.

**Arbejdsgangen fremover omfatter GitHub-publicering ved hver afsluttet fortsættelse:** en dateret rapport med evidens, opdateret science-status og main-oversigt, præcis readback-kontrol og commit-identiteter i resume-metadata. Dette er en fortsættelsesprocedure og ingen påstand om automatisk baggrundsarbejde.

[Afsluttende audit](results/radio_ba_completed_20261029/FINAL_AUDIT_PUBLIC.json) · [Gendannelse og bevarede fejl](results/radio_ba_completed_20261029/RECOVERY_HISTORY_PUBLIC.json) · [Publiceringsevidens og fortsættelsesprocedure](results/radio_ba_completed_20261029/PUBLIC_EVIDENCE.json) · [Kontrolsummer](results/radio_ba_completed_20261029/SHA256SUMS).

Disse offentlige bilag er kompakte metadata-afledninger med originalartefakternes kontrolsummer. De publicerer ikke teleskop-arrays eller private arbejdsdata og er ikke alene en fuld reproduktionspakke for alle historiske analyser.
