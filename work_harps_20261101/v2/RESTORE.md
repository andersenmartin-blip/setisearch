# Gendannelse og fortsættelse af HARPS-arbejdet

Start i [CONTINUE_SETI.md](../../CONTINUE_SETI.md) og [aktuel maskinlæsbar tilstand](../../work_seti_20261102_accelerated/CONTINUATION_STATE.json). Hent seneste GitHub og sammenlign kildehashes. Branch: `optical-harps-week-20261101`; fortsættelsespunktet spejles på `main`.

Alle 669 V2-poster har første råbilledgennemgang: **403 A / 46 O / 185 U / 35 M / 0 N**. Ældre 333: uændret 209 A / 25 O / 95 U / 4 M. Nye 336: 194 A / 21 O / 90 U / 31 M. Batch05 ændrer kun V2E2-0332 og V2E2-0333 fra N til foreløbig A; øvrige 667 poster bevares. Gennemgang er ikke sikker ophavsbestemmelse.

Hovedprøven er fortsat 300 eksponeringer af 20 stjerner, 70.874650833 timer. V1 har 22 foreløbige træf i 300 eksponeringer; V2 har 669 poster i de sidste 200. Ingen kvalificeret laserkandidat eller kalibreret nulresultat.

[Den afsluttede mapping-kontrol](extension02/mapping_followup_remaining_20261102/README.md) omfatter alle 35 M-poster i 21 eksponeringer: 1.512 ordener og 7.517 målte referencevinduer. Alle 35 forbliver M. Ingen tilsvarende rådiagnose mangler længere i denne kø; gentag den ikke ved fortsættelse.

[Normaliseringsopfølgningen](extension02/normalization_context_20261102/README.md) af V2E2-0092 og V2E2-0104 er afsluttet: 28 profiler, 8 fokuserede vinduer og 12 native/råkontekster. Begge forbliver U; den lave lokale flux ligger i en senere referenceobservation, og korrelation er invariant under positiv skalering alene. En lokal trace-usikkerhed bevares.

[De 90 nye U-poster](extension02/unresolved_context_20261102/README.md) har en udtømmende opfølgningskø og grupper af overlappende profiler. Ældre 95 U-poster er bevaret uden ny gruppering. Gruppetal er ikke uafhængige signaler. Epokekontrollen er afsluttet: 2.185 par og 4.370 profiler.

Rubin er fremrykket til 2.–8. november. [Første hovedanalyse](../../work_rubin_20261102/main_analysis/README.md) er afsluttet med 188 udvalgte objekter, men kun 2 numerisk vurderbare i hovedsporet og separat 3 i forced-sporet. Minimum 50 er ikke opfyldt. Ingen tærskelpasserende måling og intet kvalificeret nulresultat. Brug det fælles fortsættelsespunkt til den aktuelle metadataopfølgning.

## Input og reproduktion

Klon/hent `andersenmartin-blip/setisearch` og gå til `work_harps_20261101`. Input er linket i hver gruppes checkpoint og aktuel tilstand. [Batch05](extension02/raw_followup_batch05/README.md) har seneste originale rå/ancillary-par; [inputregisteret](extension02/raw_followup_batch05/checkpoints/LIBRARY_INPUTS.json) registrerer hashes og filidentitet. Originale 1D-spektre ligger i de tidligere extension02-inputpakker.

Udpak til staging først, verificér arkiv- og medlemshashes og kopier kun kanoniske payloads og kvitteringer. `v2/extension02/` er relativt til `work_harps_20261101`. Gamle arkivrapporter må ikke erstatte nyere resultater. Ufuldstændige filer er aldrig analyseinput.

Batch05-evidens gendannes med `python3 restore_evidence.py` inde i gruppens mappe. Epokeprofiler gendannes med `python3 restore_profile_archive.py` inde i `extension02/epoch_followup`. Begge verificerer hashes. Følg hver README ved audit og brug en separat kopi, da rapporter skrives igen. Mapping-diagnosen har sit eget tidligere kildepar og en fast metode; der kræves ingen ny hentning fra teleskoparkivet for reproduktion.

Registrerede versioner: Python 3.12, NumPy 2.3.5, SciPy 1.17.0, Astropy 8.0.2 og Matplotlib 3.10.8. Bevar publicerede originaler og tidsstempler ved reproduktion.

Alle ophavsvurderinger er foreløbige. Agentkontrol er ikke menneskelig fagfællebedømmelse. Historiske mapping-metoder er heterogene; der foreligger ingen samlet følsomhed, falsk-alarm-rate eller sikker laser-eksklusion. Ingen automatisk baggrundssøgning er konfigureret.

## Nye evidenspakker og Rubin

I `extension02/mapping_followup_remaining_20261102` gendanner `python3 restore_evidence.py` 20 komplette diagnosticeringsfiler fra tre ordnede dele. I `extension02/normalization_context_20261102` gendanner samme kommandonavn 28 originale udvalgte profiler og 20 afledte arrays fra én del. Begge kontrollerer størrelser og SHA-256 før skrivning. De større originale teleskopprodukter har fortsat deres eksisterende gemte identiteter; `REQUIRED_INPUTS.json` og `SOURCE_PRODUCTS.json` angiver præcise medlemmer.

Rubin-mappen bevarer de originale offentlige API-svar, forespørgsler, kvitteringer, Gaia-kataloget og fulde analyser direkte i Git. Genkør ikke acquisition-scriptet blot for at gendanne et checkpoint. `ROOT_RELEASE.json` angiver den verificerede publicering før hovedflux. `MAIN_METHOD_FREEZE.json` binder kontrolpakken; `METHOD_FREEZE.json` er acquisition/analysis-guardens metodefil. Reproducer i en separat kopi, da stopguards beskytter allerede afsluttede kørsler.
