# Gemte outputs fra tre interne båndgrænser

Denne nye familie søger kun de sammenføjede referencefelter q255/q256 i de fastlagte par 153+154, 154+155 og 157+158. De svarer til venstre native q255 og højre native q0. Ingen tidligere referencekanal genberegnes, og der modtages ingen nye teleskopbytes. De oprindelige scopes, gemte outputs og afslutningsstatusser bevares, herunder tidligere CPU-grænsefejl.

Detektoren bruger uændret rå float32-kontekst, 763 drifthastigheder fra −4 til +4 Hz/s og bredderne 1/3. De nye faste profiler bruger en særskilt normalisering: hver rækkes median af hele det sammenføjede par på 2.097.152 rå float32-kanaler, efterfølgende promoveret til float64. De to tidligere native medianer genbruges ikke. Detektorens score og profilens middelresidual er forskellige størrelser. Nye profiltal kan ikke behandles som identiske mål med tidligere native profiler.

Den nye scope og alle kilder og kontrolværktøjer skal publiceres og læses tilbage før særskilt GO. Hvert par har sin egen oprindelige, én gang udførte numeriske kørsel, seks gemte maksimumkort, seks felt-normaliseringsfiler, 60 top20-poster og ni faste profiler. Profilidentiteten er `(pair_id, track_id)`, og rangorden holdes separat pr. par og ON-origin. Opsummeringen kræver oprindelig `COMPLETE_TWO_JOINED_BOUNDARY_CORES_EXPLORATORY_ONLY` for alle tre par, tre matchede gemte-output-QA-kvitteringer og særskilt bitvis kildecelle-QA. En oprindelig fejlstatus bliver ikke gjort til COMPLETE.

Efter kontrollerne har bestået, fastlåses præcis alle krævede JSON-inputs i `results/radio_internal_boundaries_20261010/SUMMARY_INPUT_PINS.json`. Brug absolutte projektstier, den faktiske offentlige scope-SHA256 og den faktiske freeze-commit:

```sh
python3 "$PROJECT_ROOT/tools/radio_internal_boundaries_20261010/summarize_saved.py" \
  --root "$PROJECT_ROOT" \
  --pins "$PROJECT_ROOT/results/radio_internal_boundaries_20261010/SUMMARY_INPUT_PINS.json" \
  --expected-scope-sha256 "$BOUNDARY_SCOPE_SHA256" \
  --freeze-commit "$BOUNDARY_FREEZE_COMMIT" \
  --root-go-after-all-pairs-QA
```

Opsummeringen læser kun hashpinnede JSON-filer og skriver rapport, JSON, CSV og en særskilt input-/outputkvittering. Den åbner ingen HDF5/NPZ og genberegner ingen søgning, normalisering, rangliste eller profil. Den har grænser på 20 CPU-sekunder, 1.800 sekunders vægtid og 2 GiB RAM og deler den sidste 60-CPU-sekunders allokering med pakkens 40 CPU-sekunder i den nye 600-CPU-sekunders fase.

Efter rapportkontrol bygges den enkelte resultatsamling én gang med SHA256 for de faktiske færdige outputs:

```sh
python3 "$PROJECT_ROOT/tools/radio_internal_boundaries_20261010/package_saved.py" \
  --root "$PROJECT_ROOT" \
  --archive "$ARTIFACT_DIR/SETI_INTERNAL_BOUNDARIES_RESULTS_2026-10-10.zip" \
  --expected-scope-sha256 "$BOUNDARY_SCOPE_SHA256" \
  --freeze-commit "$BOUNDARY_FREEZE_COMMIT" \
  --expected-summary-sha256 "$SUMMARY_SHA256" \
  --expected-summary-receipt-sha256 "$SUMMARY_RECEIPT_SHA256" \
  --expected-report-sha256 "$REVIEWED_REPORT_SHA256" \
  --root-go-after-all-pairs-QA
```

Hvis rapportens tekst skal rettes efter den videnskabelige gennemgang, bevares den genererede rapport først uændret som `results/radio_internal_boundaries_20261010/summary/GENERATED_REPORT.md`. En særskilt `summary/EDITORIAL_RECEIPT.json` binder status `PASS_EDITORIAL_REPORT_REVIEW_NO_NUMERIC_RERUN`, scope/freeze, `original_generated_report_sha256`, `preserved_generated_report_path`, `preserved_generated_report_sha256`, `reviewed_report_sha256`, `summary_sha256`, `summary_receipt_sha256`, `no_numeric_rerun: true` og `scientific_JSON_changed: false`. Kun ved sådan tekstredigering tilføjes `--expected-editorial-receipt-sha256 "$EDITORIAL_RECEIPT_SHA256"` til pakkekommandoen. Den oprindelige opsummeringskvittering og alle videnskabelige JSON-filer forbliver uændrede; både rapportversioner og redaktionskvitteringen medtages. En uændret rapport bruger ingen redaktionskvittering.

Pakningen læser videnskabelige arrayfiler som ufortolkede bytes. Alle nye maksimumkort, normaliseringer, råprofiludklip, terminal- og kontrolkvitteringer samt kode, scope, inputpins, rapport og CSV bevares. SHA256, byteantal og CRC kontrolleres for hvert ZIP-medlem efter skrivningen. ZIP'ens egen SHA256 ligger kun i den eksterne pakkekvittering; manifestet refererer ikke til sig selv. Rå HDF5-bodies, originale RAW-arkivbodies, miljø-wheels og private overførselsoplysninger indgår ikke. De allerede gemte originale kildeidentiteter og fil-/rækkehashes forbliver bundet via scope og kontrolkvitteringer. Pakningen har grænser på 40 CPU-sekunder, 1.800 sekunders vægtid, 4 GiB RAM og 8 GiB arbejdsplads og deler den sidste 60-CPU-sekunders allokering med opsummeringens 20 CPU-sekunder. Den øvrige fase reserverer 360 CPU-sekunder til de tre numeriske par, 120 til kontrol (tre gemte-output-QA-kørsler på 20 og én kildecellekontrol på 60) og 60 til forberedelse.

Den fulde nye familie omfatter 18 ON-feltkort, 73.728 referencekanal/originposter og 112.508.928 evaluerede drift/breddehypotesekombinationer. De 27 profiler giver 162 scanningsprofiler, 2.592 tidsrækkeforekomster og 334.368 råcelleforekomster. Tællingerne angiver korrelerede beregninger og gemte forekomster, ikke uafhængige fysiske signaler eller forsøg. Alle scanninger stammer fra ét historisk besøg, og par 153+154 og 154+155 deler hele native bånd 154.

De nye grænsefelter kan kun forenes med tidligere dækning, når de tidligere 254 referencefelter pr. berørt native bånd er særskilt verificeret, og den nye familie har gennemført sine kontroller. En sådan betinget union giver 255/256 felter for 153, 155, 157 og 158 og 256/256 for 154, alene for det fastlåste grid og bredderne 1/3. Opsummeringen udleder ikke denne tidligere verifikation af de nye outputs. Grænser mod beskyttet 156/159 og andre ungemte naboer forbliver lukkede. Originalernes fulde MD5 er fortsat ikke verificeret.

Dette er en ny udforskende familie i allerede eksponerede data. ON-udvalgte profiler og små værdier langs et præcist OFF-spor giver ingen kalibreret SNR, falskalarmrate, flux, EIRP, følsomhed, oprindelsesbestemmelse, kvalificeret SETI-kandidat eller generelt nulresultat. A/B forbliver FAIL_CLOSED, og gamle holdouts genåbnes ikke.
