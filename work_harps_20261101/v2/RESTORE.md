# Gendannelse og fortsættelse af HARPS-arbejdet

Start i [CONTINUE_SETI.md](../../CONTINUE_SETI.md) og [aktuel maskinlæsbar tilstand](../../work_harps_20261103_c021_context/CONTINUATION_STATE.json). Hent seneste GitHub og sammenlign kildehashes. Branch: `optical-harps-week-20261101`; fortsættelsespunktet spejles på `main`.

Alle 669 V2-poster har første råbilledgennemgang: **403 A / 46 O / 185 U / 35 M / 0 N**. Ældre 333: uændret 209 A / 25 O / 95 U / 4 M. Nye 336: 194 A / 21 O / 90 U / 31 M. Batch05 ændrer kun V2E2-0332 og V2E2-0333 fra N til foreløbig A; øvrige 667 poster bevares. Gennemgang er ikke sikker ophavsbestemmelse.

Hovedprøven er fortsat 300 eksponeringer af 20 stjerner, 70.874650833 timer. V1 har 22 foreløbige træf i 300 eksponeringer; V2 har 669 poster i de sidste 200. Ingen kvalificeret laserkandidat eller kalibreret nulresultat.

[Den afsluttede mapping-kontrol](extension02/mapping_followup_remaining_20261102/README.md) omfatter alle 35 M-poster i 21 eksponeringer: 1.512 ordener og 7.517 målte referencevinduer. Alle 35 forbliver M. Ingen tilsvarende rådiagnose mangler længere i denne kø; gentag den ikke ved fortsættelse.

[Normaliseringsopfølgningen](extension02/normalization_context_20261102/README.md) af V2E2-0092 og V2E2-0104 er afsluttet: 28 profiler, 8 fokuserede vinduer og 12 native/råkontekster. Begge forbliver U; den lave lokale flux ligger i en senere referenceobservation, og korrelation er invariant under positiv skalering alene. En lokal trace-usikkerhed bevares.

[De 90 nye U-poster](extension02/unresolved_context_20261102/README.md) har en udtømmende opfølgningskø og grupper af overlappende profiler. Ældre 95 U-poster er bevaret uden ny gruppering. Gruppetal er ikke uafhængige signaler. Epokekontrollen er afsluttet: 2.185 par og 4.370 profiler.

Rubin er fremrykket til 2.–8. november. [Første hovedanalyse](../../work_rubin_20261102/main_analysis/README.md) er afsluttet med 188 udvalgte objekter, men kun 2 numerisk vurderbare i hovedsporet og separat 3 i forced-sporet. Minimum 50 er ikke opfyldt. Ingen tærskelpasserende måling og intet kvalificeret nulresultat. Den efterfølgende metadata/Gaia-udvidelse er også gennemført helt til analyse. Samlet Rubin-status er 190 udvalgte objekter, 2 numerisk vurderbare i hovedsporet og separat 4 i forced-sporet. Brug det fælles fortsættelsespunkt til næste afgrænsede datamulighed.

## Afsluttet C021-kontekst på HD114783

Kernen: 30 af 30 epoke/reference-par har højere barycentrisk korrelation og 0 højere topocentrisk korrelation; normaliseret RMS er lavest barycentrisk i 30 og topocentrisk i 0. Omgivelserne: 30 af 30 epoke/reference-par har højere barycentrisk korrelation og 0 højere topocentrisk korrelation; normaliseret RMS er lavest barycentrisk i 30 og topocentrisk i 0. Alle fem poster forbliver U. Par med genbrugte og gensidige referencer er afhængige; der er fortsat kun syv observationer. 0 af 24 profilrækker har bevarede ikke-positive originalpunkter. 3 af syv forudsagte fælles centre ligger inden for den faste topocentriske kerne og 4 udenfor; det er forventede centerpositioner, ikke fuld målt profildækning.

[C021-resultatet](../../work_harps_20261103_c021_context/README.md) bevarer 24 profiler, 160 sammenligninger, alle fem discovery-referencer og V2E2-0116/0121/0126/0130/0139 som U. Fælles midtpunkt, originale katalogmarkører og originale kerner står særskilt; fælles kerne er ikke hele foreningen af de individuelle kerner. Der er kun syv observationer, selv om hver reference sammenlignes med seks andre epoker. De fem oprindelige orden-19-kontekster bevares med lokale/baseline-begrænsninger for 0116/0126/0130 og understøttede felter for 0121/0139. Globale og senere diagnoser er understøttet for alle fem. For 0130 står oprindelig I/M-normaliseret-I/adoption-I og senere U-historik særskilt; uafhængig bekræftelse eller ophavsbestemmelse følger ikke.

12 kildevinduer, 24 profiler og 5 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c021_context/preservation/README.md) beskriver præcise inputs fra eksisterende arkiver og separat reproduktion. Målets egne januar 2022–juli 2023-epoker og alle fem referencer bruges; C018/C019-observationerne genbruges ved en anden bølgelængde; juli-reference erstatter maj-reference, mens marts- og maj-epokerne bevares som øvrige observationer.

Det aktuelle næste trin er [C022 på HD114783 med medlemscentre 4312,2375–4312,245 Å](../../work_harps_20261103_c021_context/NEXT_ACTION.json), oprindelig kø-række 36. De præcise observationer, reference-produkter og historiske begrænsninger står i handoff. Afsluttede normaliseringsdiagnoser og C021 gentages ikke. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C019-kontekst på HD114783

Kernen: 30 af 30 epoke/reference-par har højere barycentrisk korrelation og 0 højere topocentrisk korrelation; normaliseret RMS er lavest barycentrisk i 30 og topocentrisk i 0. Omgivelserne: 30 af 30 epoke/reference-par har højere barycentrisk korrelation og 0 højere topocentrisk korrelation; normaliseret RMS er lavest barycentrisk i 30 og topocentrisk i 0. Alle fem poster forbliver U. Par med genbrugte og gensidige referencer er afhængige; der er fortsat kun syv observationer. 6 af 34 profilrækker har bevarede ikke-positive originalpunkter. 3 af syv forudsagte fælles centre ligger inden for den faste topocentriske kerne og 4 udenfor; det er forventede centerpositioner, ikke fuld målt profildækning.

[C019-resultatet](../../work_harps_20261103_c019_context/README.md) bevarer 34 profiler, 180 sammenligninger, alle fem discovery-referencer og V2E2-0115/0120/0125/0129/0135 som U. Fælles midtpunkt, originale katalogmarkører og originale kerner står særskilt; fælles kerne er ikke hele foreningen af de individuelle kerner. Der er kun syv observationer, selv om hver reference sammenlignes med seks andre epoker. De ti oprindelige mapping-kontekster for orden 3/4 er understøttet. Otte senere felter er understøttet, mens de to ældre 0129-felter er null/ikke vurderet. Alle fem oprindelige U bevares; ingen historik fra C018/0128 overføres til 0129. Uafhængig bekræftelse eller ophavsbestemmelse følger ikke.

17 kildevinduer, 34 profiler og 10 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c019_context/preservation/README.md) beskriver præcise inputs fra eksisterende arkiver og separat reproduktion. Målets egne januar 2022–juli 2023-epoker og alle fem referencer bruges; C018-observationerne genbruges ved en anden bølgelængde med fem referencer; marts- og juli-epokerne bevares som øvrige observationer.

Det daværende næste trin var [C021 på HD114783 med medlemscentre 4309,825–4309,8275 Å](../../work_harps_20261103_c019_context/NEXT_ACTION.json), oprindelig kø-række 35. De præcise observationer, reference-produkter og historiske begrænsninger står i handoff. Afsluttede normaliseringsdiagnoser og C019 gentages ikke. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C018-kontekst på HD114783

Kernen: 42 af 42 epoke/reference-par har højere barycentrisk korrelation og 0 højere topocentrisk korrelation; normaliseret RMS er lavest barycentrisk i 42 og topocentrisk i 0. Omgivelserne: 42 af 42 epoke/reference-par har højere barycentrisk korrelation og 0 højere topocentrisk korrelation; normaliseret RMS er lavest barycentrisk i 42 og topocentrisk i 0. Alle syv poster forbliver U. Par med genbrugte og gensidige referencer er afhængige; der er fortsat kun syv observationer. 12 af 42 profilrækker har bevarede ikke-positive originalpunkter. 3 af syv forudsagte fælles centre ligger inden for den faste topocentriske kerne og 4 udenfor; det er forventede centerpositioner, ikke fuld målt profildækning.

[C018-resultatet](../../work_harps_20261103_c018_context/README.md) bevarer 42 profiler, 252 sammenligninger, alle syv discovery-referencer og V2E2-0114/0119/0124/0128/0133/0134/0138 som U. Fælles midtpunkt, originale katalogmarkører og originale kerner står særskilt; fælles kerne er ikke hele foreningen af de individuelle kerner. Der er kun syv observationer, selv om hver reference sammenlignes med seks andre epoker. De fjorten historiske mapping-kontekster bevares med oprindelige lokale/baseline-fejl for orden 2 og understøttede trin for orden 3. For 0128 står oprindelig primær I, sekundær M (normaliseret til I), adoption I og senere U-historik særskilt; uafhængig bekræftelse eller ophavsbestemmelse følger ikke.

21 kildevinduer, 42 profiler og 14 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c018_context/preservation/README.md) beskriver præcise inputs fra eksisterende arkiver og separat reproduktion. Målets egne januar 2022–juli 2023-epoker og alle syv referencer bruges; ingen HD114386-produkter eller tidligere numerisk anchor overføres.

Det daværende næste trin var [C019 på HD114783 med medlemscentre 3881,6125–3881,615 Å](../../work_harps_20261103_c018_context/NEXT_ACTION.json), oprindelig kø-række 34. De præcise observationer, reference-produkter og historiske begrænsninger står i handoff. Afsluttede normaliseringsdiagnoser og C018 gentages ikke. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C015-kontekst på HD114386

Kernen stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. Omgivelserne stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. V2E2-0095 forbliver U. 4 af syv forudsagte centre ligger inden for den faste topocentriske kerne og 3 udenfor; centerpositioner er ikke fuld målt profildækning. 2 af 16 profilrækker indeholder bevarede ikke-positive originalpunkter, selv om de gyldige reference-medianer er positive. Profilform og skaleret amplitude varierer mellem epokerne.

[C015-resultatet](../../work_harps_20261103_c015_context/README.md) bevarer 16 profiler, 32 sammenligninger og V2E2-0095 som U. 8 kildevinduer, 16 profiler og 1 råpanel ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c015_context/preservation/README.md) beskriver præcise inputs fra eksisterende arkiver og separat reproduktion. Målets egne syv januar 2022–august 2023-epoker genbruges fra C016 med egen maj 2022-reference og særskilt bølgelængdespecifik anchor ved denne bølgelængde. Den oprindelige orden 3 er understøttet på alle fire historiske mapping-trin.

Det daværende næste trin var [C018 på HD114783 med medlemscentre 3869,3325–3869,335 Å](../../work_harps_20261103_c015_context/NEXT_ACTION.json), oprindelig kø-række 33. De præcise målspecifikke observationer og historiske begrænsninger står i handoff. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C016-kontekst på HD114386

Kernen: 24 af 24 epoke/reference-par har højere barycentrisk korrelation og 0 højere topocentrisk korrelation; normaliseret RMS er lavest barycentrisk i 24 og topocentrisk i 0. Omgivelserne: 24 af 24 epoke/reference-par har højere barycentrisk korrelation og 0 højere topocentrisk korrelation; normaliseret RMS er lavest barycentrisk i 24 og topocentrisk i 0. Alle fire poster forbliver U. Par med genbrugte og gensidige referencer er afhængige; der er fortsat kun syv observationer. 0 af 22 profilrækker har bevarede ikke-positive originalpunkter. 3 af syv forudsagte fælles centre ligger inden for den faste topocentriske kerne og 4 udenfor; det er forventede centerpositioner, ikke fuld målt profildækning.

[C016-resultatet](../../work_harps_20261103_c016_context/README.md) bevarer 22 profiler, 128 sammenligninger, alle fire discovery-referencer og V2E2-0094/0096/0098/0110 som U. Fælles midtpunkt, originale katalogmarkører og originale kerner står særskilt; fælles kerne er ikke hele foreningen af de individuelle kerner. Der er kun syv observationer, selv om hver reference sammenlignes med seks andre epoker. Alle fire historiske orden-19-kontekster har understøttede mapping-trin; uafhængig bekræftelse eller ophavsbestemmelse følger ikke.

11 kildevinduer, 22 profiler og 4 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c016_context/preservation/README.md) beskriver præcise inputs fra eksisterende arkiver og separat reproduktion. Målets egne januar 2022–august 2023-epoker og alle fire referencer bruges; ingen HD112410-produkter eller numerisk anchor overføres.

Det daværende næste trin var [C015 på HD114386 ved 3869,915 Å](../../work_harps_20261103_c016_context/NEXT_ACTION.json), oprindelig kø-række 28. De præcise observationer, egen reference og historiske begrænsninger står i handoff. Afsluttede normaliseringsdiagnoser og C016 gentages ikke. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C011-kontekst på HD112410

Kernen stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. Omgivelserne stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. V2E2-0089 forbliver U. 6 af 18 profilrækker indeholder bevarede ikke-positive originalpunkter, selv om de gyldige reference-medianer er positive. Profilform og skaleret amplitude varierer mellem epokerne. 2 profilrækker har flag for lavt referenceniveau (native orden 2); deres gyldige positive normaliseringer og flag bevares.

[C011-resultatet](../../work_harps_20261103_c011_context/README.md) bevarer 18 profiler, 36 sammenligninger og V2E2-0089 som U. 9 kildevinduer, 18 profiler og 2 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c011_context/preservation/README.md) beskriver præcise inputs fra eksisterende arkiver og separat reproduktion. Målets egne syv epoker genbruges fra C010/C012 med egen maj 2025-reference og særskilt bølgelængdespecifik anchor. Det brede vindue overlapper C012 på de samme observationer, mens C011-kernen ligger uden for C012-vinduet. Orden 2 og 3 er begge understøttet på alle fire historiske mapping-trin.

Det daværende næste trin var [C016 på HD114386 med medlemscentre 4303,785–4303,79 Å](../../work_harps_20261103_c011_context/NEXT_ACTION.json), oprindelig kø-række 27. De præcise målspecifikke observationer og historiske begrænsninger står i handoff. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C012-kontekst på HD112410

Kernen stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. Omgivelserne stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. V2E2-0087 forbliver U. 4 af 18 profilrækker indeholder bevarede ikke-positive originalpunkter, selv om de gyldige reference-medianer er positive. Profilform og skaleret amplitude varierer mellem epokerne.

[C012-resultatet](../../work_harps_20261103_c012_context/README.md) bevarer 18 profiler, 36 sammenligninger og V2E2-0087 som U. 9 kildevinduer, 18 profiler og 2 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c012_context/preservation/README.md) beskriver præcise inputs fra eksisterende arkiver og separat reproduktion. Målets egne syv epoker og april 2025-reference genbruges fra C010 med en særskilt bølgelængdespecifik anchor. Numerisk overlap med HD106515A deler ingen pixels eller observationer. Orden 2s oprindelige lokale/baseline-begrænsninger bevares, mens orden 3 er understøttet på alle fire trin.

Det daværende næste trin var [C011 på HD112410 ved 3865,6775 Å](../../work_harps_20261103_c012_context/NEXT_ACTION.json), oprindelig kø-række 25. De præcise målspecifikke observationer og historiske begrænsninger står i handoff. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C010-kontekst på HD112410

Kernen stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. Omgivelserne stemmer bedst overens i barycentriske koordinater i alle 6 sammenligninger, målt med både korrelation og normaliseret RMS. V2E2-0086 forbliver U. 16 af 16 profilrækker indeholder bevarede ikke-positive originalpunkter, selv om de gyldige reference-medianer er positive. Profilform og skaleret amplitude varierer mellem epokerne.

[C010-resultatet](../../work_harps_20261103_c010_context/README.md) bevarer 16 profiler, 32 sammenligninger og V2E2-0086 som U. 8 kildevinduer, 16 profiler og 1 råpanel ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c010_context/preservation/README.md) beskriver præcise inputs fra eksisterende arkiver og separat reproduktion. Målets egne syv epoker og april 2025-reference bruges; ingen HD106515A-produkter eller numerisk anchor overføres. Orden 1s oprindelige lokale/baseline-begrænsninger bevares.

Det daværende næste trin var [C012 på HD112410 ved 3869,2675 Å](../../work_harps_20261103_c010_context/NEXT_ACTION.json), oprindelig kø-række 24. De præcise målspecifikke observationer og historiske begrænsninger står i handoff. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C009-kontekst på HD106515A

Den centrale C009-form er negativt korreleret med kernen fra fundobservationen i marts 2023 i alle seks andre epoker i barycentriske koordinater. Omgivelserne har bedst barycentrisk overensstemmelse i alle seks sammenligninger. V2E2-0050 forbliver U.

[C009-resultatet](../../work_harps_20261103_c009_context/README.md) bevarer 16 profiler, 32 sammenligninger og V2E2-0050 som U. 8 kildevinduer, 16 profiler og 1 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261103_c009_context/preservation/README.md) beskriver 10 eksakte inputs fra de eksisterende arkiver og separat reproduktion.

Det daværende næste trin var [C010 på HD112410 ved 3823,065 Å](../../work_harps_20261103_c009_context/NEXT_ACTION.json), en enkelt post fra oprindelig kø-række 23. Målets egne syv epoker og tidligere epoke-/råanalyse findes allerede. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C008-kontekst på HD106515A

[C008-resultatet](../../work_harps_20261102_c008_context/README.md) bevarer 16 profiler, 32 sammenligninger og V2E2-0047 som U. 8 kildevinduer, 16 profiler og 1 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261102_c008_context/preservation/README.md) beskriver 10 eksakte inputs fra de eksisterende arkiver og separat reproduktion.

Det daværende næste trin var [C009 ved 6802,02 Å](../../work_harps_20261102_c008_context/NEXT_ACTION.json), en enkelt post fra oprindelig kø-række 18. Tidligere epoke-/råanalyse og de samme observationer findes allerede. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C002-kontekst på HD106515A

[C002-resultatet](../../work_harps_20261102_c002_context/README.md) bevarer 18 profiler, 36 sammenligninger og V2E2-0033 som U. 9 kildevinduer, 18 profiler og 2 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261102_c002_context/preservation/README.md) beskriver 11 eksakte inputs fra de eksisterende arkiver og separat reproduktion.

Det daværende næste trin var [C008 ved 5182,005 Å](../../work_harps_20261102_c002_context/NEXT_ACTION.json), en enkelt post fra oprindelig kø-række 17. Tidligere epoke-/råanalyse og de samme observationer findes allerede. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C004-kontekst på HD106515A

[C004-resultatet](../../work_harps_20261102_c004_context/README.md) bevarer 20 profiler, 96 sammenligninger og alle tre U-statusser. 10 kildevinduer, 20 profiler og 3 råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261102_c004_context/preservation/README.md) beskriver 16 eksakte inputs fra de eksisterende arkiver og separat reproduktion.

Det daværende næste trin var [C002 ved 3868,6025 Å](../../work_harps_20261102_c004_context/NEXT_ACTION.json), en enkelt post fra oprindelig kø-række 10. Kernen var allerede synlig i C003; det foreslåede bredere vindue overlapper C004. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C007-kontekst på HD106515A

[C007-resultatet](../../work_harps_20261102_c007_context/README.md) bevarer 16 profiler, 32 sammenligninger og V2E2-0026's U-status. Otte kildevinduer, seksten profiler og ét råpanel ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261102_c007_context/preservation/README.md) beskriver ti eksakte inputs fra to eksisterende arkiver og separat reproduktion.

Det daværende næste trin var [C004 ved 3872,245 Å](../../work_harps_20261102_c007_context/NEXT_ACTION.json), tre poster fra oprindelig kø-række 8 og frem. Kernen overlapper allerede sete C003-referenceområder. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C006-kontekst på HD106515A

[C006-resultatet](../../work_harps_20261102_c006_context/README.md) bevarer 18 profiler, 64 sammenligninger og alle tre U-statusser. Ni kildevinduer, 18 profiler og tre råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261102_c006_context/preservation/README.md) beskriver 14 eksakte inputs fra to eksisterende arkiver og separat reproduktion.

Det daværende næste trin var [C007 ved 4312,7 Å](../../work_harps_20261102_c006_context/NEXT_ACTION.json), en enkelt post fra oprindelig kø-række 6. Kernen overlapper allerede sete C006-referenceområder. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C005-kontekst på HD106515A

[C005-resultatet](../../work_harps_20261102_c005_context/README.md) bevarer 34 profiler, 180 sammenligninger og alle fem U-statusser. De 17 kildevinduer, 34 profiler og ti råpaneler ligger direkte i repository. To lave referenceflag er bevaret, uden manglende dækning eller udeladelser. [Gendannelsesvejledningen](../../work_harps_20261102_c005_context/preservation/README.md) beskriver fuld gendannelse af 27 inputs fra tre eksisterende arkiver og separat reproduktion.

Det daværende næste trin var [C006 omkring 4310 Å](../../work_harps_20261102_c005_context/NEXT_ACTION.json): tre katalogposter, men kun to forskellige discovery-produkter. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C003-kontekst på HD106515A

[C003-resultatet](../../work_harps_20261102_c003_context/README.md) bevarer30profiler,172sammenligningsudfald og alle femU-statusser. De15præcise kildevinduer,30profiler og8råpaneler ligger direkte i repository; to ikke-dækkende orden2-kontekster er særskilt metadata. [Gendannelsesvejledningen](../../work_harps_20261102_c003_context/preservation/README.md) beskriver fuld gendannelse af25inputs fra tre eksisterende arkiver og separat reproduktion. Ingen ny ESO-hentning kræves.

Det daværende næste trin var [C005 nær3882,04Å](../../work_harps_20261102_c003_context/NEXT_ACTION.json), valgt fra oprindelig kø-række4. Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet C001-kontekst på HD103991

[Den fælles analyse](../../work_harps_20261102_c001_context/README.md) har20 profiludfald og64 sammenligningsudfald fra seks allerede arkiverede spektre og begge discovery-ordenpar. Begge poster forbliverU; orden3's manglende referenceflank holdes eksplicit adskilt fra lave fluxværdier. De ti præcise kildevinduer før interpolation, tyve profiler og fire råpaneler ligger direkte i repository. [Gendannelsesvejledningen](../../work_harps_20261102_c001_context/preservation/README.md) dokumenterer også fuld gendannelse af14 inputs fra tre eksisterende arkiver, uden ny ESO-hentning. Bevar afsluttede udfald og engangsguards; reproduktion sker i en separat kopi.

Det daværende næste trin var [C003-gruppen på HD106515A](../../work_harps_20261102_c001_context/NEXT_ACTION.json). Ældre næste-trin-formuleringer nedenfor er historiske.

## Afsluttet rumlig diagnose af V2E2-0235

[Den kvantitative rumlige undersøgelse](../../work_harps_20261102_spatial_0235/README.md) er afsluttet: 8.275 native pixels, tre faste profilmodeller og 27 mål-/kontroludfald. Alle målte pixels og deres koordinater ligger direkte i `analysis/results/SELECTED_NATIVE_PIXELS.npz`; `SPATIAL_ARRAYS.npz` indeholder også modeller og residualer. [Gendannelsesvejledningen](../../work_harps_20261102_spatial_0235/preservation/README.md) binder de kompakte filer til de allerede arkiverede fulde rådata. Ingen ny ESO-hentning er nødvendig. Bevar de publicerede udfald og kør eventuel reproduktion i en separat kopi.

Den afsluttende `background_sensitivity/`-fase genbruger kun det gemte `SELECTED_NATIVE_PIXELS.npz`; dens to side-estimatorer, 18 vinduer og 198 rækkefit er færdige og publiceres separat fra den oprindelige måling. Alle dens modeller/residualer ligger i eget `results/SPATIAL_ARRAYS.npz`. Reproduktion behøver ingen ny rådetektorindlæsning; bevar begge fasers engangsguards og resultater.

V2E2-0235 forbliver U: afvigelsen ligger hovedsageligt nær spektrets spor, og oprindelsen er ikke afklaret. Fortsættelsespunktet står i [den aktuelle overdragelse](../../work_harps_20261102_spatial_0235/scientific_review/NEXT_STEP.md).

## Afsluttet separat maj-kvalitetsopfølgning

[Den tredje referenceepoke](../../work_harps_20261102_may_quality/README.md) er færdiganalyseret med tolv profiler. Fra repository-roden gendanner `python3 work_harps_20261102_may_quality/preservation/restore_archive.py SCIENCE_INPUTS_MANIFEST.json` det nye FITS-input fra to arkivdele. Kør derefter `restore_reference_cache.py` i samme mappe for de tyve discovery-referencer og de 24 tidligere kontekstprofiler, og `restore_archive.py PROFILE_EVIDENCE_MANIFEST.json` for de tolv nye profiler. Alle hashes verificeres; afvigende filer bevares. Ingen ESO-hentning eller genkørsel af den oprindelige søgning er nødvendig.

Den efterfølgende rumlige råbilledanalyse er også afsluttet; følg det aktuelle fortsættelsespunkt ovenfor. De to afsluttede referencefaser må ikke automatisk udvides ved at vælge flere majprodukter.

## Afsluttet bredere HARPS BERV-opfølgning

[Den nye opfølgning](../../work_harps_20261102_berv_followup/README.md) har to nye HD122640-spektre og 24 profiler. De ti udvalgte hændelser bevarer U-status. Den afsluttede kørsel og dens engangsguards må ikke genstartes som ny forskning.

Fra repository-roden gendanner `python3 work_harps_20261102_berv_followup/science_acquisition/restore_inputs.py` begge præcise FITS-filer fra fire gemte arkivdele. `python3 work_harps_20261102_berv_followup/prospective_comparison/restore_profile_evidence.py` gendanner 20 oprindelige referenceprofiler og 24 nye sammenligningsprofiler fra det samlede profilarkiv. Begge hjælpekoder kontrollerer SHA-256 og overskriver ikke afvigende filer. Originaldata kræver ingen ny ESO-hentning. Reproduktion skal ske i en separat kopi, så tidsstempler, resultater og engangsguards i den publicerede kørsel bevares.

Den historiske [overdragelse](../../work_harps_20261102_berv_followup/next_followup/README.md) pegede på en særskilt kvalitetsopfølgning. Den er nu afsluttet som beskrevet ovenfor; gentag den ikke som en ny opgave.

## Input og reproduktion

Klon/hent `andersenmartin-blip/setisearch` og gå til `work_harps_20261101`. Input er linket i hver gruppes checkpoint og aktuel tilstand. [Batch05](extension02/raw_followup_batch05/README.md) har seneste originale rå/ancillary-par; [inputregisteret](extension02/raw_followup_batch05/checkpoints/LIBRARY_INPUTS.json) registrerer hashes og filidentitet. Originale 1D-spektre ligger i de tidligere extension02-inputpakker.

Udpak til staging først, verificér arkiv- og medlemshashes og kopier kun kanoniske payloads og kvitteringer. `v2/extension02/` er relativt til `work_harps_20261101`. Gamle arkivrapporter må ikke erstatte nyere resultater. Ufuldstændige filer er aldrig analyseinput.

Batch05-evidens gendannes med `python3 restore_evidence.py` inde i gruppens mappe. Epokeprofiler gendannes med `python3 restore_profile_archive.py` inde i `extension02/epoch_followup`. Begge verificerer hashes. Følg hver README ved audit og brug en separat kopi, da rapporter skrives igen. Mapping-diagnosen har sit eget tidligere kildepar og en fast metode; der kræves ingen ny hentning fra teleskoparkivet for reproduktion.

Registrerede versioner: Python 3.12, NumPy 2.3.5, SciPy 1.17.0, Astropy 8.0.2 og Matplotlib 3.10.8. Bevar publicerede originaler og tidsstempler ved reproduktion.

Alle ophavsvurderinger er foreløbige. Agentkontrol er ikke menneskelig fagfællebedømmelse. Historiske mapping-metoder er heterogene; der foreligger ingen samlet følsomhed, falsk-alarm-rate eller sikker laser-eksklusion. Ingen automatisk baggrundssøgning er konfigureret.

## Nye evidenspakker og Rubin

I `extension02/mapping_followup_remaining_20261102` gendanner `python3 restore_evidence.py` 20 komplette diagnosticeringsfiler fra tre ordnede dele. I `extension02/normalization_context_20261102` gendanner samme kommandonavn 28 originale udvalgte profiler og 20 afledte arrays fra én del. Begge kontrollerer størrelser og SHA-256 før skrivning. De større originale teleskopprodukter har fortsat deres eksisterende gemte identiteter; `REQUIRED_INPUTS.json` og `SOURCE_PRODUCTS.json` angiver præcise medlemmer.

Rubin-mappen bevarer de originale offentlige API-svar, forespørgsler, kvitteringer, Gaia-kataloget og fulde analyser direkte i Git. Genkør ikke acquisition-scriptet blot for at gendanne et checkpoint. `ROOT_RELEASE.json` angiver den verificerede publicering før hovedflux. `MAIN_METHOD_FREEZE.json` binder kontrolpakken; `METHOD_FREEZE.json` er acquisition/analysis-guardens metodefil. Reproducer i en separat kopi, da stopguards beskytter allerede afsluttede kørsler.
