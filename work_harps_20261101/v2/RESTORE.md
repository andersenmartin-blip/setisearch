# Gendannelse og fortsættelse efter V2

Aktuel status: 200 hovedeksponeringer analyseret med V1; kun de ekstra 100 med V2. V2-metoden, konfigurationen, udvalg og kontrolplan må ikke omskrives som følge af de nu kendte resultater. Det oprindelige V1-materiale er bevaret. Ny metodeudvikling kræver en særskilt version og nye kontroller.

## Gendan eksisterende resultater

1. Hent branch `optical-harps-week-20261101` fra `andersenmartin-blip/setisearch`. Gå til `work_harps_20261101`.
2. Hent de to inputcheckpoints via [V2-rapportens links](README.md). Pak de nye input ud med projektmappen som rod; arkivet indeholder `v2/data/...` og `triage_followup/products/...`. Det oprindelige checkpoint leverer `data/main/...` og øvrige oprindelige filer. Kontrollér arkivernes SHA-256 før udpakning.
3. Pak `v2/V2_ANALYSIS_EVIDENCE.zip` ud med samme projektrod. Alle store per-spektrum-JSON og `v2/production/V2_ALL_SCREENED_EVENTS.csv` ligger her. Arkivet fastholder resultatversionen fra commit8212c365; senere statusdokumenter i repository kan være opdateret. Pak først ud i en separat mappe, kontrollér hvert medlem mod `v2/EVIDENCE_ARCHIVE.json`, og kopier de nødvendige numeriske resultater uden at overskrive nyere statusdokumenter.
4. Brug Python 3.12.14, NumPy 2.5.4, SciPy 1.17.0 og Astropy 8.0.2. Matplotlib anvendes til figurer. Kør `python v2/review/check_results.py` for numerisk reproduktion på gemte input; dette skriver kontrollens nye tidspunkt og skal derfor ske i en arbejdskopi.
5. Regenerér figurer med `python v2/review/make_review_atlas.py`, `python triage_followup/map_native_products.py` og `python triage_followup/inspect_overlaps.py`. Visuelle dispositioner er eksplicitte vurderinger i `triage_followup/VISUAL_REVIEW.json`, ikke et resultat af en automatisk classifier.

## Frisk fuld reproduktion

Brug en særskilt kopi og bevar det publicerede resultat som reference. Omdøb den kopierede `v2/validation/results` og `v2/production` til separate referencekataloger. Kør først `python v2/validation/run_validation.py`, derefter `python v2/code/run_main.py`. Begge kræver, at deres nye outputmappe ikke findes, og kontrollerer de frosne kode- og inputhashes. Sammenlign semantiske resultater og optællinger; tidsstempler og runtime forventes at ændre sig.

## Gendan den komplette første rågennemgang

Hent de to batch01-inputarkiver fra [første rågennemgang](triage_batch01/README.md) og de seks batch02-inputarkiver fra [anden rågennemgang](triage_batch02/README.md). Kontrollér SHA-256 mod de respektive `INPUT_CHECKPOINTS.json`. Arkiverne bruger projektmappen som rod. De giver rå/native-produkter for alle92 eksponeringer med mindst ét V2-hit.

Pak `triage_batch01/TRIAGE01_EVIDENCE.zip`, `triage_batch02/TRIAGE02_EVIDENCE.zip`, `mapping_followup/MAPPING_FOLLOWUP_EVIDENCE.zip` og `mapping_followup_additional/ADDITIONAL_MAPPING_EVIDENCE.zip` ud i en separat mappe. Kontrollér medlemmer mod de tilhørende arkivmanifester; overskriv ikke nyere dokumenter. De to mapping-arkiver genbruger batch01-råinput. Den aktuelle tabel er `triage_batch02/CUMULATIVE_DISPOSITIONS.csv`; alle tidligere tabeller bevares.

Fra en arbejdskopi kan `python v2/triage_batch02/audit_numerical.py` gentage metadata-/hashkontrol og tre metadatavalgte eksponeringers udtræk. `python v2/triage_batch02/finalize_review.py` og `python v2/triage_batch02/combine_followup.py` gendanner dispositionstabeller fra gemte manuelle noter; dette genskaber ikke en ny visuel vurdering.

## Næste faglige arbejde

Alle **333 V2-profilhits har nu en dokumenteret første rågennemgang**: 201 sandsynlige detektorartefakter, 25 forenelige med atmosfærisk O I, 64 uafklarede spektralstrukturer og 43 med utilstrækkelig lokal råbilledkontrol. Ingen identificeret laser eller kvalificeret SETI-kandidat. Vurderingerne er foreløbige; HARPS-ugen er fortsat delvis.

Fortsæt med lokale referencemangler for43 hændelser og alle-epoke-sammenligning/linjeidentifikation for64 uafklarede strukturer.53 af de64 har et andet accepteret hit inden for±0,03Å barycentrisk; det er ikke en fuld epokekontrol. V2-0205 har en efterfølgende O I6363,776-hypotese, som ikke ændrer det oprindelige to-linje-flag eller den bevarede uafklarede status.

Batch01 og batch02 bruger forskellige opfølgningskontroller; sammenfat ikke klassetællinger som en kalibreret falsk-alarm-rate. Den fastlåste detektor må ikke tilpasses de nu kendte udfald. De200 hovedeksponeringer er uændrede. Råprodukterne giver ingen ny eksponeringstid. Rubin-data er endnu ikke analyseret.
