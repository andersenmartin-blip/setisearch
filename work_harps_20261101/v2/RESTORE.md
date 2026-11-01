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

## Næste faglige arbejde

Det oprindelige 333-hitkatalog er uændret `UNREVIEWED`. [Første gennemgang](triage_batch01/README.md) har særskilte foreløbige dispositioner for V2-0001–0096: 56 sandsynlige detektorartefakter, 10 forenelige med atmosfærisk O I, 24 uafklarede spektralstrukturer og seks utilstrækkeligt kortlagte råbilleder. Fortsæt med V2-0097, og bevar de uafklarede tilfælde i opfølgningskøen. Nye råinput til gennemgangen findes i de to arkiver i samme rapport. Der er et komplet [atlasindeks](review/REVIEW_INDEX.csv), 28 figursider og 25 beskrivende sammenfald med to O I-linjer. O I-flag alene må ikke bruges som veto. Fortsæt i dokumenteret tabelrækkefølge med native ordener og råkontrol i afgrænsede grupper; gem alle dispositioner og begrundelser separat fra de frosne detektorresultater. Ved overlappende ordener skal begge undersøges.

De oprindelige ti har syv foreløbige detektorartefakt-vurderinger og tre foreløbige atmosfæriske O I-vurderinger. En uafhængig visuel gennemgang og relevant sky-/kalibreringskontrol mangler. Den nye numeriske kontrol er udført af hovedagenten; den særskilte agentreview blev afbrudt af kontobrugsgrænsen.

Udvid ikke automatisk hovedprøven igen, før kontrolbyrden er vurderet. De 200 er en reel udvidelse af dækningen; antallet af foreløbige profiler er ikke antallet af teknologiske signaler. HARPS-ugen er delvis; Rubin-data er endnu ikke analyseret.
