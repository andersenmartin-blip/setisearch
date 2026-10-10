# Gemte resultater fra fortsatte native driftsøgninger

De fælles værktøjer sammenfatter én fastlagt fase ad gangen: `rolling155157` eller `native158`. `POSTPROCESSING_SCOPE.json` binder hver fases oprindelige kode, scope, offentlige fastlåsning, kanalvalg og kontrolværktøjer. Værktøjerne åbner ingen nye resultatværdier før særskilt GO og de konkrete inputpins. Alle numeriske grupper skal have deres oprindelige COMPLETE-status, matchede output-QA-kvitteringer og en bestået særskilt kildecellekontrol. Disse værktøjer kan ikke godkende outputs fra en oprindelig fejlstatus.

Hver native kilde opdeles i q1..127 og q128..254, med 381 ON-referencefelter og ni faste profiler pr. gruppe. De oprindelige numeriske grænser er 2.000 CPU-sekunder, 2.400 sekunders vægtid og 4 GiB RAM. Ingen tidligere fase eller fejlsti antages at være genbrugt; hver ny gruppe har sin egen oprindelige kørsel og sine egne pins.

Efter alle krævede kontroller har bestået, genereres et hashkort over præcis de nødvendige gemte JSON-inputs ved `results/<fase>/SUMMARY_INPUT_PINS.json`: 36 inputfiler for udsnit155/157, 20 for udsnit158. Kortet indeholder postprocesseringsscope, aktiveringsscope, oprindeligt numerisk scope, særskilt kildecellekvittering, modtagelse+modtagelses-QA pr. udsnit samt de syv faste metadatafiler pr. numerisk gruppe.

```sh
python3 "$PROJECT_ROOT/tools/radio_saved_stages_20261010/summarize_saved.py" \
  --root "$PROJECT_ROOT" \
  --stage-id "$STAGE_ID" \
  --pins "$PROJECT_ROOT/$STAGE_RESULTS/SUMMARY_INPUT_PINS.json" \
  --expected-postprocessing-scope-sha256 "$POSTPROCESSING_SCOPE_SHA256" \
  --postprocessing-freeze-commit "$POSTPROCESSING_FREEZE_COMMIT" \
  --root-authorized-summary-read
```

Den enkeltstående opsummering skriver `summary/SAVED_SUMMARY.json`, `PROFILE_SUMMARY.csv`, `SUMMARY_EXECUTION_RECEIPT.json` og den fasebestemte rodrapport. Den læser kun hashpinnede JSON-filer, har en grænse på 40 CPU-sekunder/1.800 sekunders vægtid/4 GiB RAM og bevarer den separate rangorden pr. native udsnit, gruppe og ON. Profilidentiteten er `(source_chunk_id,batch_id,track_id)`. Rapporten beskriver kun gemte tal og kontrollernes dokumenterede rækkevidde.

Figurerne læser de samme præcise JSON-pins og de samme COMPLETE-/QA-kontroller som opsummeringen. Kør rendereren én gang efter særskilt GO:

```sh
python3 "$PROJECT_ROOT/tools/radio_saved_stages_20261010/plots_saved_stages.py" \
  --root "$PROJECT_ROOT" \
  --stage-id "$STAGE_ID" \
  --pins "$PROJECT_ROOT/$STAGE_RESULTS/SUMMARY_INPUT_PINS.json" \
  --expected-postprocessing-scope-sha256 "$POSTPROCESSING_SCOPE_SHA256" \
  --postprocessing-freeze-commit "$POSTPROCESSING_FREEZE_COMMIT" \
  --root-authorized-plot-read
```

Rendererens PNG-bytes skrives først til en buffer. `png_publish.py` kontrollerer PNG-chunks, CRC og en fuld billedafkodning med Pillow, skriver og fsync'er en midlertidig fil og publicerer den atomisk. Den dokumenterer de to færdige PNG-filers SHA256 og størrelser i `figures/PLOTTING_RECEIPT.json`; billedfremstilling genkører ingen detektor, signalprofil eller kildekontrol.

Efter rapport- og figurkontrol fastlåses desuden SHA256 for de to figurer, deres fælles `PLOTTING_RECEIPT.json` og det eksterne RAW-arkivmanifest pr. udsnit i en særskilt `PACKAGE_EXTRA_PINS.json`. Pakning kræver SHA256 af dette kort og de endelige opsummerings-, kvitterings- og rapportfiler:

```sh
python3 "$PROJECT_ROOT/tools/radio_saved_stages_20261010/package_saved.py" \
  --root "$PROJECT_ROOT" \
  --stage-id "$STAGE_ID" \
  --archive "$ARTIFACT_DIR/$STAGE_ARCHIVE_FILENAME" \
  --expected-postprocessing-scope-sha256 "$POSTPROCESSING_SCOPE_SHA256" \
  --postprocessing-freeze-commit "$POSTPROCESSING_FREEZE_COMMIT" \
  --expected-summary-sha256 "$SUMMARY_SHA256" \
  --expected-summary-receipt-sha256 "$SUMMARY_RECEIPT_SHA256" \
  --expected-report-sha256 "$REVIEWED_REPORT_SHA256" \
  --extra-pins "$PROJECT_ROOT/$STAGE_RESULTS/PACKAGE_EXTRA_PINS.json" \
  --expected-extra-pins-sha256 "$PACKAGE_EXTRA_PINS_SHA256" \
  --root-authorized-package-read
```

Den én gang udførte pakning bevarer samtlige maksimumkort, normaliseringsfiler, råprofiludklip, opsummering, CSV, rapport, figurer, kontroller og reproduktionsværktøjer. NPZ-filer læses kun som bytes. Hvert ZIP-medlem verificeres med SHA256, byteantal og CRC. Pakningen har grænser på 120 CPU-sekunder/1.800 sekunders vægtid/4 GiB RAM og kontrollerer 8 GiB arbejdsplads. ZIP'ens SHA256 findes i den eksterne kvittering; manifestet refererer ikke til sin egen hash. HDF5-kildekompakter og RAW-ZIP-bodies holdes eksterne og deres arkivmanifester bindes til de faktiske modtagelseskontroller. Originalernes fulde MD5 er fortsat ikke verificeret.

Ved fuldførelse af udsnit155/157 er der 1.524 maksimumkort, 36 faste profiler og 9.525.755.904 evaluerede hypotesekombinationer. Udsnit158 har 762 kort, 18 profiler og 4.762.877.952 kombinationer. Tællingerne er beregningsdækning, ikke uafhængige forsøg. Kortene gemmer maksimum og vindende drift/bredde pr. referencekanal, ikke hver hypoteses score. De 99,21875 % gælder 254/256 referencefelter pr. udsnit, alene det frosne grid på 763 lineære drifthastigheder og bredde1/3. Alle scanninger er fra ét historisk besøg, og ingen af værktøjerne etablerer signaloprindelse, kalibreret SNR/falskalarmrate, generelt nulresultat eller en kvalificeret SETI-kandidat.
