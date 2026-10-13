# SETI: målstjernens nye faste spor

13. oktober 2026. HIP98505 / HD189733; historisk besøg fra 28. april 2017.

Alle **9.412.608** gemte ON-carrier-vindere i **2.298** kort er nu globalt kontrolleret mod de tre faste DC-bins. **7.083** vinderbaner har kontakt; **9.405.525** passerer geometrireglen. Der er valgt TOP3 per ON-scanning med original score, drift, bredde og fast tieorden. De tre ON-scanninger holdes adskilt, selv om målstjernen er den samme.

**48 nye faste råprofiler** og **48 fulde normaliseringer** er nu beregnet i de eksisterende seks scanninger. Seks profiler genbruges ved eksakt kanalgeometri, normaliseringskerne og bytehash for den tidligere kendte 2300 MHz-komponent. De otte nye valgte skabeloner er forskellige fra den tidligere OFF-opfølgning.

| Gruppe for de otte nye valg | Antal profiler | Mindste faste score | Største faste score |
| --- | ---: | ---: | ---: |
| Egen udvælgelsesscanning | 8 | 6.541930 | 6.953942 |
| Andre ON-scanninger mod samme stjerne | 16 | -1.338782 | 0.939185 |
| OFF-scanninger mod tre andre stjerner | 24 | -2.447680 | 1.290806 |

Ingen fast-banegenfinding er etableret i de andre ON-scanninger. Det er en beskrivende sammenligning efter optimering i egen scanning og giver ikke en kalibreret falskalarmrate, uafhængig signifikans eller generel sky-nuldetektion. Den faelles 2300 MHz-komponent er fortsat positiv i alle seks scanninger; stjerneeksklusivitet er ikke etableret. De otte nye valg forbliver ubekræftede.

Deres egne profiler har 14-16 positive rækker, med 12,1-18,0 procent af det samlede positive bidrag i den største række. Alle rækker indgik allerede i udvælgelsen. Dette er beskrivende tidsfordeling og ikke ekstra signalevidens. Alle 54 transporterede originale bokse er uden DC-kontakt.

Rå TOP700 og TOP100 samt en separat TOP100 med mere end tre referencebins mellem valgene er bevaret for hvert ON-origin. Det 100. afstandsvalg forekommer ved rå rang 107, 109 og 105, under det dokumenterede maksimum 694. Kanalafstand dokumenterer ikke forskellige fysiske kilder. De to yderste referencekerner er udeladt i de oprindelige kort.

Udvaelgelses-QA bestod 231.099 eksakte checks af alle 2.298 kort og ranglister. Raa-QA verificerede 18 kompakte kildefiler, 288 originale decoded rækkehashes, 48 nye fulde normaliseringer med 3.145.728 separate median501-positioner, 48 profiler og 386.304 rå503-celler bit for bit. Den største forskel i egen originalscore er 1,07e-14. Seks gamle profiler er genbrugt med hashes og ikke genberegnet.

En første kontekst-QA-formatfejl i en census-metadata-gate stoppede før arrays eller scorer blev læst. Kode, scope og fejlkvittering er bevaret. Den snævre formatrettelse ændrede ingen numerisk formel eller producentdata. Den faktiske videnskabelige QA-kørsel fandt nul afvigelser.

Bærbar NumPy-reproduktion bestod 6.239 checks med nul afvigelser. Den genberegner kun de 48 nye normaliseringer og profiler fra bevarede crops uden HDF5 eller detektorimport. De tidligere 54 referenceprofiler bevares med deres originale tal og hashes; deres scorer genberegnes ikke i denne kørsel. Tidligere baseline-reproduktionskode og dens PASS-kvittering bevares separat.

[Alle ni valg og 54 kontekster](delivery/SELECTED9_CONTEXT54.csv) · [Kort rapport](delivery/SETI_MAALSTJERNE_2026-10-13.pdf) · [Reproduktionsvejledning](reproduction/README.md)

Kun den allerede gemte vindende drift-/breddehypotese per carrier undersøges. En vinder med DC-kontakt kan stadig skjule en ren ikke-vindende hypotese. Dette er en ny global udvælgelse og fast raakontekst i eksisterende data, ingen ny observation, frekvensdækning eller detektorgridsøgning.

**Ingen kvalificeret SETI-detektion. 0 DKK; nul nye teleskoprequests. Original A/B: FAIL_CLOSED. Beskyttede 2016-kontroller og den lukkede 2019-adgangsrute er uændrede. Formelt checkpoint: 20. oktober 2026.**
