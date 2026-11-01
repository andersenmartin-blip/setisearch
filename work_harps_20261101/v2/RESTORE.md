# Gendannelse og fortsættelse efter 300 HARPS eksponeringer

Aktuel status: 300 unikke hovedeksponeringer af 20 stjerner, 255.148,743 sekunder (70,874651 timer). V1 har 22 træf på 300 eksponeringer. V2 har 333 oprindelige og 336 nye profiltræf på 200 eksponeringer. Det første 100-udvalg er ikke genkørt med V2. Alle detektorkoder, konfigurationer og oprindelige kataloger bevares; ny metodeudvikling kræver en særskilt version og nye kontroller.

## Hvor arbejdet står

- Oprindelige 333: den aktuelle tabel er `followup_synthesis/CUMULATIVE_333.csv`: 209 foreløbige detektorartefakter, 25 O I-fortolkninger, 95 uafklarede spektralstrukturer, 4 kortlægningsbegrænsninger. De oprindelige batch-tabeller er historiske og uændrede.
- De 95 har alle-epoke- og breddekontekst.91 følger det barycentriske spektrum, 3 har en stærk kalibreringsrefleks-hypotese, 1 har en svag O I-hypotese. Denne kontrol omfatter117 relevante eksponeringer fra de tidligere200, ikke de seneste 100. Ingen af disse beskrivelser er et automatisk oprindelsesveto.
- Nye 336: hele kataloget og alle 42 figursider findes i `extension02/production/` og `extension02/review1d/`. Den uændrede produktionsstatus er `UNREVIEWED`; efterfølgende råvurderinger ligger separat.
- 59 nye V2-træf og alle 6 nye V1-træf er rågennemgået i 8 eksponeringer. De 6 V1 har V2-match og er ikke6 ekstra uafhængige fysiske hændelser. Den første råtabel er `extension02/raw_followup/BASELINE_SELECTED_EVENT_DISPOSITIONS.csv`; alle 336 inklusive277 ikke-rågennemgåede står i `BASELINE_V2_ALL336_DISPOSITIONS.csv`. Den vedtagne bredere billedkobling ligger særskilt i `mapping_followup/` med bevaret baseline. Aktuel tabel: `CURRENT_V2_ALL336_DISPOSITIONS.csv` (44 A, 8 O, 6 U, 1 M, 277 ikke rågennemgåede); alle 669 V2-poster er samlet i `v2/CURRENT_V2_DISPOSITIONS.csv` med eksplicit kohorte og evidenskilde.
- Næste hovedopgave er de 277 resterende nye V2-træf, efterfulgt af kontrol af de fortsat usikre forklaringer. Udvid ikke søgetærsklen for at reducere arbejdsbyrden. Rubin-data er endnu ikke analyseret; den godkendte Rubin-uge er8.–14. november.

## Hent og gendan input

Hent branch `optical-harps-week-20261101` fra `andersenmartin-blip/setisearch` og gå til `work_harps_20261101`.

De oprindelige inputcheckpoints er fortsat linket i [den første V2-rapport](README.md). De to første råinputdele ligger i [batch01](triage_batch01/README.md), de seks næste i [batch02](triage_batch02/README.md). Disse råprodukter dækker92 eksponeringer med oprindelige V2-træf. Derudover findes de oprindelige V1-råkontroller under `triage_followup/`.

De fire nye inputdele med 100 1D-FITS og 16 rå/TAR-produkter er linket i [gemte input](extension02/checkpoints/SAVED_INPUTS.md). De bruger `work_harps_20261101/` som udpakningsrod; medlemmerne starter med `v2/extension02/`. Kontrollér alle arkiv- og medlemshashes mod checkpointindeksene. Tre ubrugte delvise filer med ukendt overlevelsesårsag er bevaret som diagnostik i rådel1; de er præcise præfikser af verificerede produkter og er udelukket fra videnskabsinput. Det dokumenterer ikke deres netværksproveniens.

## Gendan numerisk evidens

Pak arkiver ud i en separat mappe og kontrollér hvert medlem før kopiering. Undgå at overskrive nyere statusdokumenter med rapportversioner inde i historiske arkiver.

- Det oprindelige `V2_ANALYSIS_EVIDENCE.zip` indeholder blandt andet store per-spektrum-JSON og alle oprindelige screenede events; følg `EVIDENCE_ARCHIVE.json`.
- De historiske råarkiver ligger under `triage_batch01/`, `triage_batch02/`, `mapping_followup/` og `mapping_followup_additional/`.
- De nye opfølgninger på oprindelige 333 har evidensarkiver under `mapping43_followup/`, `epoch64_followup/`, `epoch31_followup/`, `line_identification/`, `oi_followup/` og `blue_calibration_followup/`. Deres manifester angiver præcis udpakningsrod og medlemshashes. Profilbredderne ligger direkte under `profile_widths/` og `profile_widths31/`.
- De nye 100 hovedresultater er gemt direkte under `extension02/production/`. De 336 1D-udsnit ligger i `extension02/review1d/EXTENSION02_REVIEW1D_EVIDENCE.zip`; råudsnittene i `extension02/raw_followup/RAW_BASELINE_EVIDENCE.zip`. Figursiderne ligger separat i repository.

## Kontroller i en arbejdskopi

Brug Python 3.12.14, NumPy 2.5.4, SciPy 1.17.0, Astropy 8.0.2 og Matplotlib. I den eksisterende runtime findes pakkerne via `PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps`; på en ny maskine installeres de dokumenterede versioner lokalt.

```bash
python v2/extension02/audit/run_audit.py
python v2/extension02/raw_followup/audit/run_numeric_audit.py
```

Disse kontroller skal køres i en kopi, da auditrapporter får nye tidspunkter. De reproducerer fast valgte eksponeringer samt kontrollerer alle relevante inputs og optællinger. De bekræfter beregninger, ikke signalernes fysiske ophav.

En fuld ny hovedkørsel bruger `v2/extension02/run_main.py` i en kopi uden eksisterende `production/`-output. Bevar den publicerede produktion særskilt som reference. Sammenlign semantiske udfald og optællinger; tidspunkter og køretid vil ændre sig. Brug originale publicerede metadata, når råopfølgningens kildehashes skal valideres; nye tidsstempler fra en genkørsel må ikke forveksles med ændrede videnskabelige resultater.

Visuelle vurderinger er gemte, foreløbige agentvurderinger, ikke resultatet af en automatisk fysisk classifier. Billedkoblingsreglerne er ikke ens gennem alle historiske stadier, og hver efterfølgende udvidelse er bevaret som et særskilt lag. Der er ingen global følsomheds- eller falsk-alarm-kalibrering og intet kvalificeret nulresultat for lasere.
