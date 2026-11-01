# Gendannelse og fortsættelse af HARPS-arbejdet

Start i [CONTINUE_SETI.md](../../CONTINUE_SETI.md) og [den aktuelle maskinlæsbare tilstand](extension02/raw_followup_batch03/CONTINUATION_STATE.json). Hent seneste GitHub-version før arbejde; tidligere sessioner og arkivrapporter kan være historiske.

Hovedprøven er uændret: 300 unikke eksponeringer af 20 stjerner, 70.874650833 timer. V1 har 22 foreløbige træf i 300 eksponeringer. V2 har 669 poster i 200 eksponeringer. Originale detektorer, indstillinger og kataloger er bevaret.

## Aktuel status

Ældre kohorte: 209 A / 25 O / 95 U / 4 M / 0 N, bevaret i `followup_synthesis/CUMULATIVE_333.csv`. Ny kohorte: 142 A / 20 O / 61 U / 19 M / 94 N, i `extension02/raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv`. Alle 669 poster er samlet i `CURRENT_V2_DISPOSITIONS.csv` med kohorte og evidenskilde.

Seneste rågruppe omfatter 115 poster i 32 eksponeringer og bevarer alle 133 tidligere udvalgte V1/V2-afgørelser. Restkøen rummer 94 poster i 37 eksponeringer. Next: **V2E2-0243**, exposure **ADP.2022-03-16T01:08:24.041**, target **HD124553**.

Den nye epokekontrol er afsluttet: alle 336 poster blandt de nye 100 spektre, 2.185 par og 4.370 profiler. Tidligere 200 eksponeringer indgår ikke i denne kontrol. Genkør ikke afsluttede rå- eller epokebatcher blot for at fortsætte. Uafklarede strukturer og billedkoblinger står som særskilt opfølgning efter restkøen; Rubin-ugen 8.–14. november er endnu ikke analyseret.

## Input og evidens

Klon/hent `andersenmartin-blip/setisearch`, branch `optical-harps-week-20261101`, og gå til `work_harps_20261101`. Ældre input er linket i [V2-rapporten](README.md), [første rågruppe](triage_batch01/README.md), [anden rågruppe](triage_batch02/README.md) og `triage_followup/`.

De første extension02-inputpakker er i [gemte input](extension02/checkpoints/SAVED_INPUTS.md); senere rågrupper har separate checkpoints i den aktuelle tilstandsfil. Kontroller både arkiv- og medlemshashes. Udpak til staging; medlemstier under `v2/extension02/` er relative til `work_harps_20261101`. Kopier kun verificerede payloads og kvitteringer; erstat ikke nyere status med historiske arkivrapporter. Ufuldstændige `.part`-filer er ikke analyseinput.

[Seneste gruppes README](extension02/raw_followup_batch03/README.md) beskriver evidensarkiv, billedudsnit og kontrollen. Ældre evidensarkiver bevares i deres egne mapper. Epokeprofiler gendannes fra 18 dele med `python3 restore_profile_archive.py` inde i `extension02/epoch_followup`; scriptet verificerer dele og samlet SHA-256.

## Reproduktion

Brug Python 3 med NumPy, SciPy, Astropy og Matplotlib i de registrerede versioner fra gruppens `SUMMARY.json`. Undgå gamle absolutte runtime-stier. Kør audits i en separat kopi med gendannede, hashverificerede input, da rapporterne skrives igen. Fra `work_harps_20261101`:

```bash
python3 v2/extension02/epoch_followup/independent_audit/check_epochs.py
python3 v2/extension02/raw_followup_batch03/independent_audit/check_batch03.py
```

Følg hver gruppes README ved fuld reproduktion; bevar originale resultater og tidsstempler som historisk evidens. Ny reproduktion kan have andre tidsstempler uden ændret videnskab.

Alle oprindelsesvurderinger er foreløbige. Agentkontrol er ikke menneskelig fagfællebedømmelse; historiske billedkoblingsregler er heterogene. Der foreligger ingen global følsomhed, falsk-alarm-rate eller kvalificeret laser-eksklusion. Ingen automatisk baggrundssøgning er konfigureret.
