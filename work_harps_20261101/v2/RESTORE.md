# Gendannelse og fortsættelse af HARPS-arbejdet

Start i [CONTINUE_SETI.md](../../CONTINUE_SETI.md) og [aktuel maskinlæsbar tilstand](extension02/raw_followup_batch05/CONTINUATION_STATE.json). Hent seneste GitHub og sammenlign kildehashes. Branch: `optical-harps-week-20261101`; fortsættelsespunktet spejles på `main`.

Alle 669 V2-poster har første råbilledgennemgang: **403 A / 46 O / 185 U / 35 M / 0 N**. Ældre 333: uændret 209 A / 25 O / 95 U / 4 M. Nye 336: 194 A / 21 O / 90 U / 31 M. Batch05 ændrer kun V2E2-0332 og V2E2-0333 fra N til foreløbig A; øvrige 667 poster bevares. Gennemgang er ikke sikker ophavsbestemmelse.

Hovedprøven er fortsat 300 eksponeringer af 20 stjerner, 70.874650833 timer. V1 har 22 foreløbige træf i 300 eksponeringer; V2 har 669 poster i de sidste 200. Ingen kvalificeret laserkandidat eller kalibreret nulresultat.

[Mapping-diagnosen](extension02/mapping_followup_20261102/README.md) omfatter alle 35 M-poster samt en ny råkontrol af alle 72 ordener i første M-observation. V2-0149 er fortsat M; dens afsluttede diagnose skal ikke gentages. Næste endnu ikke tilsvarende rådiagnosticerede M-post er V2-0231. [De 90 nye U-poster](extension02/unresolved_context_20261102/README.md) har en udtømmende opfølgningskø og grupper af overlappende profiler. Ældre 95 U-poster er bevaret uden ny gruppering. Gruppetal er ikke antal uafhængige signaler; skabelonbredder er ikke målte linjebredder.

Epokekontrollen er afsluttet: 2.185 par og 4.370 profiler. Genkør ikke afsluttede analyser blot for at fortsætte. Rubin-ugen 8.–14. november er endnu ikke analyseret.

## Input og reproduktion

Klon/hent `andersenmartin-blip/setisearch` og gå til `work_harps_20261101`. Input er linket i hver gruppes checkpoint og aktuel tilstand. [Batch05](extension02/raw_followup_batch05/README.md) har seneste originale rå/ancillary-par; [inputregisteret](extension02/raw_followup_batch05/checkpoints/LIBRARY_INPUTS.json) registrerer hashes og filidentitet. Originale 1D-spektre ligger i de tidligere extension02-inputpakker.

Udpak til staging først, verificér arkiv- og medlemshashes og kopier kun kanoniske payloads og kvitteringer. `v2/extension02/` er relativt til `work_harps_20261101`. Gamle arkivrapporter må ikke erstatte nyere resultater. Ufuldstændige filer er aldrig analyseinput.

Batch05-evidens gendannes med `python3 restore_evidence.py` inde i gruppens mappe. Epokeprofiler gendannes med `python3 restore_profile_archive.py` inde i `extension02/epoch_followup`. Begge verificerer hashes. Følg hver README ved audit og brug en separat kopi, da rapporter skrives igen. Mapping-diagnosen har sit eget tidligere kildepar og en fast metode; der kræves ingen ny hentning fra teleskoparkivet for reproduktion.

Registrerede versioner: Python 3.12, NumPy 2.3.5, SciPy 1.17.0, Astropy 8.0.2 og Matplotlib 3.10.8. Bevar publicerede originaler og tidsstempler ved reproduktion.

Alle ophavsvurderinger er foreløbige. Agentkontrol er ikke menneskelig fagfællebedømmelse. Historiske mapping-metoder er heterogene; der foreligger ingen samlet følsomhed, falsk-alarm-rate eller sikker laser-eksklusion. Ingen automatisk baggrundssøgning er konfigureret.
