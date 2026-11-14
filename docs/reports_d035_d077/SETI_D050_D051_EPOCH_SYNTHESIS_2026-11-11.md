# SETI D050–D051: martsoversigt og september-kontrolkandidater

**11. november 2026.** Grundlag: gemt projektversion 50, SHA256 `1c883398c1c2f2a8f4fcd643ec97f1019edb4e7bd87026eb9a11fe9cbe30890d`. Observationstider er UTC. De tre oprindelige lokale udsving er alle ved HD 43629, men ved forskellige bølgelængder og datoer.

## Det nye resultat

Martsresultaterne ved **6550.095 Å** er samlet uden ændring af de gemte målinger. Originalen fra 5. marts har større signeret normaliseret lokalt 3-sampleoverskud end hver kontrol i alle **72 deklarerede parslots**. Kontrollerne fra 4. og 9. marts beholder deres egne headergrupper; 6. marts forbliver en **sekundær kontrol med selectorafvigelse**. De 72 slots er ikke 72 uafhængige forsøg.

Derefter er september-sporet ved **5730.715 Å**, D002-0071, undersøgt med en separat fastlagt katalogforespørgsel. Der blev returneret **8 rækker: den kendte kilde og 7 yderligere metadata-kandidater**, alle uden for den tidligere 54-/141-kohorte undtagen kilden. De nærmeste kvalificerede metadata-kandidater på hver side er fra **6. og 18. september 2021**. Deres egne råidentiteter, headers og spektre er endnu ikke verificeret eller analyseret.

**0 kvalificerede lasersignaler. Alle tre fysiske årsager er fortsat uafklarede.** De syv metadata-kandidater er ikke syv nye signaler eller syv nye teleskopobservationer foretaget af projektet.

## D050: fire epoker, fastlagte eksisterende tal

Medlemskab, grupper, seks baggrundsvalg og fire visninger blev fastlagt før sammenstillingen. Alle tidligere resultater og det oprindeligt udvalgte signal var allerede kendt; dette er en målrettet evidensoversigt. Hver epoke bidrager med 24 slots: detektorens faste k421 samt barycentrisk luft med NEAREST, FLOOR og CEIL, hver kombineret med affine/kvadratiske sidebånd ±5..7, ±8..12 og ±12..20 samples.

Der kopieres kun eksisterende signerede 3-, 5- og 15-samplesummer, faste normaliseringer og kontraster fra D042, D046 og D049. Ingen nye pixels, spektrale arrays, baggrundsfit, resampling, bølgelængdeændring, Monte Carlo-træk eller statistisk model er indført.

**96 case-slots repræsenterer 54 forskellige native-fit; 72 parslots repræsenterer 48 forskellige native-par i 12 visningsgrupper.** Dubletter er eksplicit bevaret. Grupper og baggrundsvalg er ikke poolet eller gennemsnittet til en fælles nulfordeling. Originalens gemte positive 3sum er nævner; negative kontrolresidualer beholdes.

Den primære barycentriske NEAREST-visning giver følgende signerede normaliserede kontrol/original-forhold over alle seks baggrundsvalg:

| Kontroldato | Gruppe | Mindste til største forhold |
| --- | --- | ---: |
| 2021-03-04 | Egne deklarerede headerfelter matcher | -0.176138 til +0.318823 |
| 2021-03-06 | Sekundær: selectorafvigelse | -0.405305 til +0.223198 |
| 2021-03-09 | Egne deklarerede headerfelter matcher | -0.278899 til +0.100344 |

Tallene er beskrivende modelvariationer, ikke konfidensintervaller eller fysiske laserstyrkegrænser. Negative værdier er lokale residualer, ikke negativ luminositet. Det største positive primære forhold er 31.88 % for 4. marts, 22.32 % for den sekundære 6. marts og 10.03 % for 9. marts. Originalens faste kontinuumsmedian er reference 1; de tre kontrolmedianer er henholdsvis 0.778365200812, 1.020966315557 og 0.974342397153 gange originalens. Forskellige lysniveauer og ukendt belysningsækvivalens er stadig relevante begrænsninger.

Audit genforbinder tabellerne uafhængigt, kontrollerer **792 oprindelige skalarværdier eksakt** og beregner forhold/forskelle med 60-cifret Decimal. Største afvigelse er 5.55e-17. Alle dublet- og gruppetal er kontrolleret, og 6. marts er ikke flyttet ind i den eksakte gruppe. To figurer viser alle seks baggrunde og alle 72 slots; de endelige figurer er visuelt gennemgået.

Der udledes ingen kalibreret FAP, p-værdi, duty cycle, persistensudelukkelse, stjerneramme-korrektion eller bestemt fysisk årsag. Originalens historiske `rho=0.7806562435869904<0.8`-fejl består; senere lokale korrelationer ophæver den ikke.

## Arbejdsprioritet efter martsoversigten

Dette er en planlægningsvurdering ud fra informationshuller, ikke en rangordning af sandsynligheden for kunstigt lys:

| Prioritet | Oprindeligt udsving | Barycentrisk luft, Å | Næste spørgsmål |
| ---: | --- | ---: | --- |
| 1 | D002-0071 | 5730.7150 | Nærliggende september-epoker; gennemført metadata i D051 |
| 2 | D002-0063 | 4826.6475 | Afgræns egen blå respons eller kontrolmulighed |
| 3 | D002-0061 | 6550.0950 | Bevar martsoversigt og historisk kvalitetsfejl |

D002-0071 har allerede tre egne lampekalibreringsbanker fra D031, men disse er ikke observationer af stjernen tæt på i tid. De tidligere fem stjerneepoker er allerede undersøgt i projektet; der fremsættes ingen påstand om første tidslige inspektion. D002-0063's blå COMB-geometri og respons er fortsat uvalideret, og rød kalibrering overføres ikke til blå.

## D051: afgrænset septemberinventar

Kilden er `ADP.2021-09-10T01:01:01.007`, råprogenitor `HARPS.2021-09-09T09:12:50.220`. Egen header angiver start 2021-09-09T09:12:50.219 og eksponering **2399.9965 s**. Det korrekte eget midtpunkt, MJD **59466.39780344039**, er brugt som udvælgelsesreference. Den afrundede katalogvarighed er gemt separat, ikke erstattet af 1800 s.

Før nye svar blev der låst et vindue på ±30 døgn omkring dette midtpunkt og en **30 buesekunders katalogkegle** omkring RA 94.167764°, deklination −13.98754°. Keglen dækker den på forhånd kendte pegespredning blandt de fem gamle target-epoker; den er ikke den fysiske fiberåbning. Der skete ingen udvidelse efter svarene.

Præcis to sekventielle GET-forespørgsler til [ESO TAP ObsCore](https://archive.eso.org/tap_obs/sync) blev udført: COUNT og maksimalt 50 rækker med 17 metadatafelter, sorteret efter t_min og dp_id. Grænsen var 1,000,000 bytes pr. svar, timeout 45 s og ét forsøg pr. forespørgsel. Begge lykkedes første gang, HTTP 200, henholdsvis 10 og 2263 bytes. Råsvar, præcise ADQL-forespørgsler, tidsstempler, hashes og kvitteringer er bevaret.

COUNT=8 matcher alle 8 rækker. Inventaret er derfor komplet **inden for de to fastlagte forespørgslers kriterier**, ikke komplet for hele arkivet. Alle otte har kanonisk target HD43629, HARPS, n_obs=1, positiv varighed, passende bølgelængdedækning samt koordinater/tider inden for grænserne. Ingen navnealiaser er automatisk promoveret. Ingen potentielle samme-start-dubletter forekom efter den forud fastlagte metadatagruppering; faktisk råuafhængighed er endnu ikke bekræftet.

Alle returnerede rækker er bevaret her. Starttiderne er omregnet fra de afrundede katalog-MJD, ikke egne verificerede råheaders. ADP-id'ets dato og frigivelsesdato er ikke observationsdatoen.

| Katalogstart, UTC | Produkt-id | Timer fra kildens eget midtpunkt | Metadatarepræsentant | Rolle |
| --- | --- | ---: | --- | --- |
| 2021-08-16T10:00:05.077Z | `ADP.2021-08-17T01:01:30.644` | -575.295873 | True | Øvrig metadata-kandidat |
| 2021-08-17T09:29:42.945Z | `ADP.2021-08-18T01:03:49.329` | -551.802021 | True | Øvrig metadata-kandidat |
| 2021-08-18T09:25:47.100Z | `ADP.2021-08-19T01:03:42.939` | -527.867533 | True | Øvrig metadata-kandidat |
| 2021-09-04T08:28:41.059Z | `ADP.2021-09-05T01:01:40.943` | -120.819211 | True | Øvrig metadata-kandidat |
| 2021-09-05T08:47:26.897Z | `ADP.2021-09-06T01:01:44.938` | -96.506478 | True | Øvrig metadata-kandidat |
| 2021-09-06T09:29:48.465Z | `ADP.2021-09-07T01:01:49.355` | -71.800487 | True | BEFORE |
| 2021-09-09T09:12:50.219Z | `ADP.2021-09-10T01:01:01.007` | +0.000000 | True | Kendt kilde |
| 2021-09-18T09:18:51.848Z | `ADP.2021-09-19T01:08:28.151` | +216.017119 | True | AFTER |

De fastlagte BEFORE/AFTER-valg er **−71.800487 timer** og **+216.017119 timer**, cirka 2.99 døgn før og 9.00 døgn efter. Valget bruger katalogets t_min + t_exptime/2 og entydigt dp_id ved lighed; ikke SNR, visuelt signal eller efterfølgende fund. De to katalogeksponeringer er hver 1799.996 s, mod kildens egne 2399.9965 s. En eventuel senere sammenligning skal derfor bruge egne udtræk og normaliseringer.

D051-audit reparsede begge CSV'er, kontrollerede antal, rækkefølge, kilde-midtpunkt, egne kvitteringshashes, metadataidentitet og nærmeste-valgene. Uafhængig positionsberegning afviger højst 6.27e-10 buesekund. **PASS.** Ingen nye rå-FITS-bodies, ancillary-tar, 1D-spektrum, headers eller fluxarrays er hentet i dette trin.

## Bevaring og konkret fortsættelse

Alle **67,233 tidligere tabelceller** er bevaret eksakt. D050 og D051 tilføjer hver otte kolonner til de samme 37+141 rækker; samlet nu **70,081 celler**. De historiske resultater, usikkerheder og klassifikationer er ikke omskrevet. Tidligere arkivmedlemmers bytes bevares; de tre aktive rodpegere har eksakte snapshots i D050/ROOT_BEFORE_D050.

Resultatpakken indeholder al D050/D051-kode, metodelåse, rå katalogsvar, kvitteringer, 96 cases, 72 par, 12 grupper, prioriteter, alle otte metadataudfald, to udpegninger, tabeller, audits, rapporter og de to figurer. Udtræk den under samme projektrod som hovedprojektet. De nye fulde figurer ligger i resultatpakken; hovedprojektet indeholder skalarresultater og en hashbundet reference til pakken.

**Næste foreslåede fase er D052:** kontrollér netop de to udpegede septemberprodukters egne råprogenitorer, entydige ancillary-forbindelser og instrumentheaders mod septemberkilden. Metode, adgangsgrænser og parsning skal fastlægges før forespørgslerne. Ingen erstatningsdato eller pixelanalyse i denne identitetsfase. Først efter et tilfredsstillende gate-resultat kan en separat inputadgang og dernæst en fastlagt 5730.715 Å-sammenligning gennemføres. D052 er endnu ikke udført eller låst.

De tre oprindelige fysiske årsager forbliver uafklarede; **0 kvalificerede lasersignaler**. Der er ingen kalibreret FAP, fysisk kovarians, identisk belysning eller overført blå/rød COMB-respons. D039–D049-resultaterne ændres ikke. Den gamle 141-kø forbliver lukket; de gamle 90-/Rubinspor forbliver stoppet. Offentlig upload er fortsat udskudt. Ingen udgifter, eksterne kontakter eller kørende baggrundsberegninger.
