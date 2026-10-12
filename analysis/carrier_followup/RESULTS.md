# SETI: global udvælgelse af alle gemte kanalmaksima

12. oktober 2026.

Alle **9.375.744** allerede gemte kanalmaksima er gennemgået i de **2.289** eksisterende kort. **5.901** gemte vinderbaner har DC-kontakt; **9.369.843** passerer den fastlåste geometriregel. De tre globalt bedst rangerede valg pr. OFF-stjerne er **præcis de samme ni tupler og scorer** som ved den tidligere udvælgelse blandt kernemaksima.

Der genfindes 55.539 vinderbaner uden DC-kontakt i de 15 kerner, hvis gamle kernemaksimum ramte DC. Ingen overtager en top-3-plads. Der er ingen ny detektorsøgning, observation eller frekvensdækning.

| OFF-stjerne | Genfundne vinderbaner | Bedste genfundne score | Tredje valgte score | Rå rang for 100. afstandsvalg |
| --- | ---: | ---: | ---: | ---: |
| HIP97319 | 18513 | 5.423506 | 6.843413 | 110 |
| HIP97461 | 18513 | 5.556631 | 6.377130 | 104 |
| HIP97663 | 18513 | 5.903766 | 6.579220 | 105 |

Den rå TOP700 og TOP100 og en separat TOP100 med mere end tre referencebins mellem valgene bevares pr. stjerne. Ved unikke referencekanaler kan hvert tidligere valg blokere højst syv carriers. Derfor skal det 100. afstandsvalg være nået senest ved rå rang 694; de observerede rangtal er 110, 104 og 105. Den fastlagte TOP700 er tilstrækkelig. Kanalafstand dokumenterer ikke forskellige fysiske sendere.

En uafhængig rækkevis geometri- og rangberegning verificerede alle kort og vinderbaner med 197.106 eksakte sammenligninger uden afvigelser. De ni valg matcher de tidligere otte normaliserede måleskabeloner; alle 54 logiske kontekstprofiler genbruges med eksakte hashes. Ingen nye råprofiler eller normaliseringer er beregnet.

Den første kontekst-QA fandt 72 formatforskelle i geometri-ID; numeriske kanalcentre, tidligere profiler og de ni egne gemte scorer stemte allerede. Første kvittering og rettelse er bevaret. Metadata, hashes og ni sammenligninger med gemte scorer blev kontrolleret igen med rettet QA-format; ingen producentdata eller råscore blev genberegnet. Slutkontrollen bestod.

En bærbar kontrol med Python og NumPy verificerede 54 kontekstlinks og ni originale per-carrier-scorer, samt 48 gamle normaliseringscrops og 768 rækkehashes som lagrede bytes. 2.048 sammenligninger bestod. Det er en dokumentationskontrol med nul nye normaliseringer eller råscoreberegninger. Det tidligere numeriske replay af de gamle 48 normaliseringer bevares separat med kode, scope, inputs og PASS-kvittering.

Den tidligere komponent ved 2300 MHz er fælles for de seks scanninger på fire stjerneretninger. Stjerneeksklusivitet er ikke etableret. Syv øvrige spor er stadig ubekræftede. Deres egne valg er påvirket af udvælgelsen over frekvens, drift og bredde.

Kun den gemte vinder pr. carrier undersøges. En vinder med DC-kontakt kan skjule en ren ikke-vindende hypotese ved samme carrier. De oprindeligt udeladte kerner forbliver uden for domænet. Scorer er empiriske robuste box-scorer, ikke kalibreret SNR, sigma eller falskalarmrate. Ingen kvalificeret SETI-detektion er etableret.

**0 DKK; nul nye teleskoprequests. Original A/B: FAIL_CLOSED. Beskyttede 2016-kontroller forbliver lukkede. Formelt checkpoint: 20. oktober 2026.**
