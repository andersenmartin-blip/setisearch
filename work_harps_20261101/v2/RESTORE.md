# Gendannelse og fortsættelse efter300 HARPS-eksponeringer

Start i [CONTINUE_SETI.md](../../CONTINUE_SETI.md) og [den aktuelle maskinlæsbare tilstand](extension02/raw_followup_batch02/CONTINUATION_STATE.json). Hent seneste GitHub-version før arbejde; tidligere sessioner og arkivrapporter kan være historiske.

Hovedprøven er300 unikke eksponeringer af20 stjerner,255.148,743 sekunder (70,874651 timer). V1 har22 træf på300 eksponeringer. V2 har333 oprindelige og336 nye poster på200 eksponeringer; de første100 er ikke genkørt med V2. Originale detektorkoder, indstillinger og kataloger er uændrede.

## Aktuel videnskabelig status

Oprindelige333:209 A,25 O,95 U,4 M i `followup_synthesis/CUMULATIVE_333.csv`. Deres epokekontrol omfattede117 relevante eksponeringer blandt de tidligere200:91 barycentrisk vedvarende,3 med kalibreringsrefleks-hypotese,1 svag O I-hypotese. Det er beskrivende kontekst, ikke automatiske oprindelsesvetoer.

Nye336: 80 A, 13 O, 27 U, 7 M, 209 N i `extension02/raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv`. Alle669 er samlet i `CURRENT_V2_DISPOSITIONS.csv` med eksplicit kohorte og evidenskilde. Første rågruppe omfattede59 V2+6 V1-poster i8 eksponeringer; den senere billedkobling er bevaret separat. Batch02 udvalgte68 V2-poster i16 yderligere eksponeringer. Historiske baseline-felter skal ikke fortolkes som gældende status.

Den nye epokekontrol af alle336 poster mod samme mål i de nye100 spektre er afsluttet:2.185 par,4.370 profiler, uafhængig numerisk kontrol bestået. Genkør den ikke blot for at fortsætte. Næste opgave er restkøen på209 poster/69 eksponeringer, efterfulgt af uafklarede strukturer og billedkoblinger. Rubin-ugen8.–14. november er endnu ikke analyseret.

## Input og evidens

Klon/hent `andersenmartin-blip/setisearch`, branch `optical-harps-week-20261101`, og gå til `work_harps_20261101`. De oprindelige input er linket i [V2-rapporten](README.md) og råinput i [batch01](triage_batch01/README.md), [batch02](triage_batch02/README.md) samt `triage_followup/`.

De fire første extension02-inputpakker indeholder100 1D-FITS og16 oprindelige RAW/TAR-produkter; se [gemte input](extension02/checkpoints/SAVED_INPUTS.md). Batch02's nye råinput skal gendannes fra det særskilte checkpoint i dens tilstandsfil. Kontroller arkiv- og medlemshashes. Udpak til separat stagingmappe; `v2/extension02/`-medlemmer er relative til `work_harps_20261101`. Kopier ikke historiske statusrapporter oven på nyere filer. Ufuldstændige diagnostiske overførselsfiler er aldrig analyseinput.

Evidensarkiver for ældre opfølgninger ligger i deres respektive mapper. Alle336 nye1D-udsnit er i `extension02/review1d/EXTENSION02_REVIEW1D_EVIDENCE.zip`; første rågruppe i `extension02/raw_followup/RAW_BASELINE_EVIDENCE.zip`. Batch02's README beskriver den nye evidens. Alle4.370 epokeprofiler rekonstrueres fra18 GitHub-dele med `python3 restore_profile_archive.py` inde i `extension02/epoch_followup`; scriptet kontrollerer dele og samlet SHA-256 før udpakning.

## Reproduktion

Brug Python3 med NumPy, SciPy, Astropy og Matplotlib; de seneste registrerede kørsler bruger Python3.12.14, NumPy2.3.5, SciPy1.17.0 og Astropy8.0.2. Brug aktuelle installerede pakker, ikke tidligere sessioners absolutte runtime-stier. Følg hver analyses registrerede versioner ved eksakt numerisk reproduktion.

Kør audits i en separat kopi med hashverificerede input, da de skriver nye rapporter. Fra `work_harps_20261101`:

```bash
python3 v2/extension02/audit/run_audit.py
python3 v2/extension02/raw_followup/audit/run_numeric_audit.py
python3 v2/extension02/epoch_followup/independent_audit/check_epochs.py
```

Se batch02's README for dens kontrolkommando. Fuld produktionsreproduktion er valgfri og kræver separate outputmapper. Bevar publicerede metadata og timestamps ved kildehashkontrol; en reproduktions nye tidsstempler er ikke ændret videnskab.

Visuelle vurderinger er foreløbige agentvurderinger, ikke en fysisk classifier eller menneskelig fagfællebedømmelse. Historiske billedkoblingsregler er heterogene. Opfølgningen giver ikke global følsomhed, falsk-alarm-rate eller et kvalificeret fravær af lasersignaler. Ingen automatisk baggrundssøgning er konfigureret.
