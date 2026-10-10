# Reproduktion af kontrol af gemte outputs

Denne efterfølgende kontrol ændrer ikke de oprindelige numeriske kørsler. Native udsnit 153/gruppe 2 sluttede `COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY`. De øvrige tre sluttede `INCOMPLETE_RESOURCE_LIMIT_NO_RETRY`, fordi afslutningskontrollen konstaterede en CPU-overskridelse efter lagring af 381 søgefelter og ni faste profiler pr. gruppe. De oprindelige terminalkvitteringer og de tidligere fire fejl før arrayindlæsning bevares byte for byte.

`SAVED_OUTPUT_ACCEPTANCE_SCOPE.json` fastlåser de oprindelige input- og outputidentiteter samt de nye kontrolværktøjer før kontrollen. Verificeret betyder, at gemte outputs består de afgrænsede integritets- og kildekontroller. Det ændrer ikke en oprindelig fejlstatus til COMPLETE og fastslår ingen signaloprindelse eller kvalificeret SETI-kandidat.

Ingen detektor, normalisering, rangliste eller profil genmåles. Der modtages ingen nye teleskopbytes. De to tidligere RAW-ZIP-arkiver er eksterne kildeinputs og indgår kun som hashbundne manifestreferencer i resultatpakken; deres HDF5-filer kopieres ikke ind i resultat-ZIP'en. Originalernes fulde MD5 er fortsat ikke verificeret.

Efter den offentlige fastlåsning og særskilt GO køres de nye outputkontroller én gang i mapper under `results/radio_next_bands_20261010/acceptance/`. Hver gruppe får egne `QA_RECEIPT.json` og `SAVED_OUTPUT_ACCEPTANCE_RECEIPT.json`. Den fælles kildecellekontrol ligger under `acceptance/review/`. Ingen original terminalkvittering erstattes eller fremstilles på ny.

Når alle fire outputkontroller, begge eksisterende modtagelseskontroller og den særskilte kontrol af 36 råprofiludklip har bestået, kan JSON-opsummeringen køres én gang. Brug absolutte stier og de faktiske offentlige scope- og commithashes:

```sh
python3 "$PROJECT_ROOT/tools/radio_next_bands_20261010/summarize_verified_saved.py" \
  --root "$PROJECT_ROOT" \
  --pins "$PROJECT_ROOT/results/radio_next_bands_20261010/acceptance/SUMMARY_INPUT_PINS.json" \
  --output-dir "$PROJECT_ROOT/results/radio_next_bands_20261010/acceptance/summary" \
  --report-path "$PROJECT_ROOT/RADIO_NEXT_BANDS_VERIFIED_SAVED_REPORT_2026-10-10.md" \
  --expected-acceptance-scope-sha256 "$ACCEPTANCE_SCOPE_SHA256" \
  --acceptance-freeze-commit "$ACCEPTANCE_FREEZE_COMMIT" \
  --joint-source-cell-receipt results/radio_next_bands_20261010/acceptance/review/SOURCE_CELL_QA_RECEIPT.json \
  --root-authorized-summary-read
```

Opsummeringen kræver præcis 51 hashpinnede JSON-inputs. Den læser kun JSON, beholder separat rangorden pr. udsnit/gruppe/ON og bruger identiteten `(source_chunk_id, batch_id, track_id)`. CSV'en og rapporten viser den oprindelige numeriske status særskilt fra den senere verifikationsstatus. Den har en afgrænset grænse på 40 CPU-sekunder, 1.800 sekunders vægtid og 4 GiB RAM.

Efter rapport- og figurkontrol kan resultatpakken køres én gang med de konkrete SHA256-værdier fra den færdige opsummering og den gennemgåede rapport:

```sh
python3 "$PROJECT_ROOT/tools/radio_next_bands_20261010/package_verified_saved.py" \
  --root "$PROJECT_ROOT" \
  --archive "$ARTIFACT_DIR/SETI_NEXT_BANDS_VERIFIED_SAVED_RESULTS_2026-10-10.zip" \
  --expected-scope-sha256 60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4 \
  --expected-acceptance-scope-sha256 "$ACCEPTANCE_SCOPE_SHA256" \
  --acceptance-freeze-commit "$ACCEPTANCE_FREEZE_COMMIT" \
  --expected-summary-sha256 "$SUMMARY_SHA256" \
  --expected-summary-execution-receipt-sha256 "$SUMMARY_RECEIPT_SHA256" \
  --expected-report-sha256 "$REVIEWED_REPORT_SHA256" \
  --root-authorized-package-read
```

Pakningen læser NPZ som ufortolkede bytes og bevarer alle 1.524 maksimumkort, 1.524 normaliseringsfiler og 36 råprofiludklip. Hvert medlem verificeres med SHA256, byteantal og CRC efter ZIP-skrivningen. ZIP'ens egen SHA findes kun i den eksterne pakkekvittering, så manifestet ikke refererer til sig selv. Pakningen har en afgrænset grænse på 120 CPU-sekunder, 1.800 sekunders vægtid og 4 GiB RAM samt kontrol af 8 GiB arbejdsplads. Den kan ikke genkøres over samme destinationsmapper efter en fejl.

Tællingen 9.525.755.904 er antallet af evaluerede kombinationer: 6.242.304 ON-referencekanal/originkombinationer med 1.526 gyldige drift/breddehypoteser hver. Kortene gemmer maksimum og vindende drift/bredde pr. referencekanal, ikke hver enkelt hypoteses score. Dækningen 99,21875 % gælder referencefelter i hvert af disse to native udsnit og alene det frosne grid på 763 drifthastigheder og bredde 1/3. Alle scanninger er fra samme historiske besøg.
