"""Build current Danish reports from saved, checked descriptive results."""
from pathlib import Path
import json,csv
OUT=Path(__file__).resolve().parent;V2=OUT.parent;BASE=V2.parent
s=json.loads((OUT/'CUMULATIVE_SUMMARY.json').read_text());b=json.loads((OUT/'SUMMARY.json').read_text())
c=s['disposition_counts'];bc=b['disposition_counts']
labels={'PROVISIONAL_DETECTOR_ARTIFACT':'Sandsynlig detektorartefakt','PROVISIONAL_ATMOSPHERIC_OI':'Forenelig med atmosfærisk O I','UNRESOLVED_SPECTRAL_FEATURE':'Uafklaret spektralstruktur','INSUFFICIENT_RAW_MAPPING':'Utilstrækkelig lokal råbilledkontrol'}
table='| Foreløbig status | Nye 237 | Samlet 333 |\n|---|---:|---:|\n'+''.join(f'| {label} | {bc.get(key,0)} | {c[key]} |\n' for key,label in labels.items())
status=f"Alle **333 V2-profilhits har nu en dokumenteret første rågennemgang**: {c['PROVISIONAL_DETECTOR_ARTIFACT']} sandsynlige detektorartefakter, {c['PROVISIONAL_ATMOSPHERIC_OI']} forenelige med atmosfærisk O I, {c['UNRESOLVED_SPECTRAL_FEATURE']} uafklarede spektralstrukturer og {c['INSUFFICIENT_RAW_MAPPING']} med utilstrækkelig lokal råbilledkontrol. Ingen identificeret laser eller kvalificeret SETI-kandidat. Vurderingerne er foreløbige; HARPS-ugen er fortsat delvis."
parts=json.loads((OUT/'INPUT_CHECKPOINTS.json').read_text())['parts']
links='| Inputarkiv | Eksponeringer | Bytes |\n|---|---:|---:|\n'+''.join(f"| [{x['filename']}]({x['library_url']}) | {x['spectra']} | {x['bytes']:,} |\n" for x in parts)
report=f'''# Rågennemgang af alle 333 HARPS V2 fund

{status}

Denne levering gennemgår V2-0097–0333 i den eksisterende tabelrækkefølge: **237 hændelser fra 68 eksponeringer af 14 stjerner**. Desuden er seks tidligere usikre billedkoblinger undersøgt særskilt. Hovedprøven er fortsat **200 unikke eksponeringer af 20 stjerner, 46,750 timers samlet eksponering**. De ekstra råprodukter er kontrolmateriale til de samme observationer og giver ikke ekstra observationstid.

## Resultat og fuld hændelsesliste

{table}

[Aktuel tabel for alle 333](CUMULATIVE_DISPOSITIONS.csv) · [samlet resultat](CUMULATIVE_SUMMARY.json) · [de nye 237 dispositioner](FOLLOWUP_DISPOSITIONS.csv) · [alle individuelle begrundelser](MANUAL_REVIEW_NOTES.json) · [figurer](FIGURES.md).

Den oprindelige søgning, grænser, 333-hitliste og oprindelige `UNREVIEWED`-status er uændrede. Efterfølgende vurderinger ligger separat. En første gennemgang med uafklarede tilfælde er ikke en afsluttet nuldetektion eller endelig ophavsbestemmelse.

## Hvad rådata viser

Mange skarpe toppe ledsages af skrå eller tværgående ladningsspor i CCD-billedet. I flere overlappende ordener findes spidsen kun i én orden; råsporet understøtter en foreløbig detektorforklaring. Bredere strukturer, som ses i flere ordener, bevares som uafklarede. Store normaliserede udsving i svagt blåt kontinuum må ikke læses som tilsvarende stor fysisk emissionsstyrke.

**53 af de 64 uafklarede spektralstrukturer** har et andet allerede accepteret V2-hit fra samme stjerne og en anden eksponering inden for ±0,03 Å i barycentriske luftbølgelængder. Det er en efterfølgende nærhedskontrol blandt udvalgte hits; alle epokers flux er ikke målt, og en stjerneidentifikation eller naturlig forklaring følger ikke automatisk. [Hele sammenligningen](CUMULATIVE_REPEAT_PROXIMITY.json).

V2-0205 har et yderligere spor til en jordisk forklaring. Efter den visuelle vurdering som uafklaret blev det sammenholdt med en tredje iltlinje: den omtrentlige topocentriske position er 6363,77416 Å, 0,00184 Å fra O I 6363,776 i luft. [NBS-tabellen](https://www.govinfo.gov/content/pkg/GOVPUB-C13-8e601b629710db9963b4d618c9a1192a/pdf/GOVPUB-C13-8e601b629710db9963b4d618c9a1192a.pdf) angiver bølgelængden; [ESO beskriver 630,0/636,4 nm-dobbeltlinjen som nattehimmelsemission](https://www.eso.org/observing/dfo/quality/FORS1/qc/skybrightness/mess-nightsky.pdf). Dette er en **efterfølgende hypotese**, ikke bekræftelse. V2-0165 ligger også tæt på linjen, men har kompakt råpixelstruktur og beholder sin foreløbige artefaktvurdering. De oprindelige to O I-flag og begge dispositioner er bevaret. [Kontrol og begrænsninger](OI6363_FOLLOWUP.json).

## Billedkobling og usikkerhed

Alle 68 eksponeringer består den nye kontrol over 24 faste områder i seks spektralordener; laveste median-korrelation er 0,918. Lokalt kræves to kandidatfri kontinuumintervaller med tilstrækkeligt mange pixels og topplacering inden for én pixel af den forudsagte fiber. Et utilstrækkeligt udsnit i blot én dækkende orden bevarer hele hændelsen som kortlægningsusikker. Kriterierne er konservative geometrikontroller, ikke en kalibreret ophavsclassifier.

Af de **43 usikre hændelser** mangler 39 tilstrækkelig lokal referenceunderstøttelse. Fire har en målt afvigelse over én pixel: V2-0149, 0186, 0221 og 0284. Svagt kontinuum kan påvirke denne måling; et flag er ikke i sig selv bevis for forkert position. To ordener er randafskåret, og de brugbare overlappende ordener er bevaret. [Fastlagt kontrol](MAPPING_PLAN.json) · [lokale mangler](LOCAL_MAPPING_WARNINGS.json).

De seks tidligere kortlægningsproblemer har fået særskilt opfølgning: **fem foreløbige artefakter og én O I-forenelig hændelse**. Den rigtige polynomiumretning flytter V2-0046/0047 med −9,876/−7,884 råkolonner. Enkelte ekstreme pixels forstyrrede det gamle referenceområde. Lokale kontinuumpositioner passer nu inden for 0,153 pixel, men svage lokale spektralkorrelationer for især V2-0046/0065 er fortsat dokumenteret. To beslægtede positioner, V2-0045/0048, er også kontrolleret; deres tidligere O/A-vurderinger er bevaret. [Geometribevis](../mapping_followup/README.md) · [yderligere to](../mapping_followup_additional/README.md) · [separate nye dispositioner](../mapping_followup_review/FOLLOWUP_DISPOSITIONS.csv).

Den første gruppe på 96 havde ét globalt referenceområde plus lokal visuel kontrol; denne gruppe bruger den udvidede faste kontrol. Optællingerne beskriver de faktiske vurderinger med disse forskellige kontroller og er ikke kalibrerede klassehyppigheder.

## Kontrol af analysen

Alle **136 nye rå- og ancillary-produkter**, i alt 1.787.921.922 bytes, blev hentet. Identitet, dato, BERV og SHA-256 blev kontrolleret. Udtrækket rummer 324 komplette native/råudsnit og to randafskårne ordener, fordelt på alle 237 hændelser.

To analyseagenter gennemgik hver sin del af de 237, inklusive dækkende ordener og lokale råprofiler. Hovedagenten krydstjekkede 63 hændelser på 11 systematisk fordelte sider; alle 63 foreløbige koder stemte. De to 6363 Å-tilfælde fik særskilte detaljer. Dette er ikke uafhængig menneskelig eller fagfællevalidering. [Gennemgangskontrol](ROOT_VISUAL_QC.json).

En særskilt agent efterprøvede udtrækket i en frisk proces: alle 136 produkt-hashes, alle hændelses-/ordenregistre og alle 324 arrays blev kontrolleret. For første, midterste og sidste eksponering i metadatarækkefølgen blev ti udsnit rekonstrueret med præcist samme rådata, baggrund, excess, native flux, bølgelængder og koordinater. Referencegitteret blev også reproduceret, her med fælles modul. [Numerisk efterkontrol](INDEPENDENT_NUMERICAL_AUDIT.json) · [kode](audit_numerical.py).

## Gemte input og reproduktion

Alle input er fastholdt i seks verificerede arkiver, samlet 1.631.235.367 bytes. Hvert råprodukt indgår præcis én gang; hvert arkivs CRC og alle fil-hashes er kontrolleret. [Inventar med SHA-256 og medlemmer](INPUT_CHECKPOINTS.json).

{links}

De tidligere inputcheckpoints er fortsat nødvendige for de første 96 og de oprindelige spektre. Se [gendannelsesvejledning](../RESTORE.md). `TRIAGE02_EVIDENCE.zip` fastholder kode, metadata, alle 324 NPZ-udsnit, referencegitter og ekstra reviewmateriale; [arkivmanifest](EVIDENCE_ARCHIVE.json) angiver medlemmer og hashes. Hovedfigurerne ligger direkte i repository.

Arbejd altid i en separat kopi. Med de gemte input på deres manifeststier kan `python v2/triage_batch02/audit_numerical.py` efterprøve resultaterne. `extract_native.py`, `plot_native.py` og `plot_focus.py` genskaber udsnit og figurer. `finalize_review.py` og `combine_followup.py` samler de eksplicit gemte visuelle vurderinger; de udfører ikke selv en ny automatisk klassifikation. Afhængigheder er de samme som i [V2-rapporten](../README.md).

## Næste arbejde

1. Undersøg de 43 lokale kortlægningsbegrænsninger med særskilte, dokumenterede referenceområder; bevar alle hidtidige fejludfald.
2. Sammenlign de 64 uafklarede strukturer på tværs af alle tilgængelige epoker i relevante referenceframes og mod konkrete naturlige spektrallinjer.
3. Kontrollér de foreløbige atmosfære- og artefaktforklaringer med sky-, kalibrerings- og uafhængigt review, hvor data tillader det.

HARPS-ugen er delvist gennemført. Rubin-ugen er fortsat 8.–14. november og er endnu ikke analyseret. Der er ikke oprettet automatisk baggrundskørsel.
'''
(OUT/'README.md').write_text(report)
figs='# Figurer til anden rågennemgang\n\nAlle 237 i tabelrækkefølge. Cyan angiver forudsagt fiber/dispersion. `LOCAL MAPPING UNCERTAIN` omfatter både manglende referencepixels og målt lokal afvigelse.\n\n'
for n in range(1,41):
    lo=97+(n-1)*6;hi=min(lo+5,333)
    figs+=f'## V2-{lo:04d} til V2-{hi:04d}\n\n![Native og rådata {lo}–{hi}](figures/REVIEW_{n:02d}.png)\n\n'
figs+='## Centrale fiberudsnit\n\n[Indeks](FOCUS_INDEX.json). O I-flag og lokale kortlægningsbegrænsninger; selvstændig skalering af panelerne.\n\n'
for n in range(1,16):figs+=f'![Centrale detaljer {n}](figures/FOCUS_{n:02d}.png)\n\n'
(OUT/'FIGURES.md').write_text(figs)
old=(BASE/'README.md').read_text();historic=old[old.index('## Historisk første V1-prøve'):]
(BASE/'README.md').write_text('# HARPS analyser og status 1. november 2026\n\n**200 unikke eksponeringer af 20 stjerner, 46,750 timers samlet teleskopeksponering.** '+status+'\n\n'+table+'\nDe oprindelige ti V1-hits har fortsat syv foreløbige artefakt- og tre atmosfærevurderinger. De nye råprodukter øger kontrollen, ikke antallet af hovedeksponeringer.\n\n[Samlet rågennemgang og begrundelser](v2/triage_batch02/README.md) · [V2-metode og frisk validering](v2/README.md) · [Præcist fortsættelsespunkt](v2/RESTORE.md)\n\n'+historic)
old=(V2/'README.md').read_text();paras=old.split('\n\n');paras[1]='**1. november 2026: Hovedprøven rummer 200 unikke eksponeringer af 20 stjerner, samlet 46,750 timers teleskopeksponering.** '+status+' [Aktuel rågennemgang](triage_batch02/README.md).';old='\n\n'.join(paras)
old=old.replace('[efterfølgende dispositioner for de første 96](triage_batch01/FOLLOWUP_DISPOSITIONS.csv)','[aktuelle efterfølgende dispositioner for alle 333](triage_batch02/CUMULATIVE_DISPOSITIONS.csv)')
old=old[:old.index('## Status og næste konkrete arbejde')]+f'''## Status og næste konkrete arbejde

{status}

Alle 333 har fået første rå-/native-vurdering. Prioriteten er nu de 43 lokale kontrolbegrænsninger, alle-epoke-sammenligning og linjeidentifikation for de 64 uafklarede strukturer samt uafhængig kontrol af foreløbige forklaringer. Seks gamle kortlægningsproblemer er fulgt op separat; oprindelige tabeller er bevaret. [Rapport, figurer og verificerede input](triage_batch02/README.md).

Den nye V2-prøve kan ikke beskrives som en afsluttet nuldetektion. HARPS-ugen er 1.–7. november; Rubin-ugen er 8.–14. november. Rubin er ikke analyseret i denne levering.
'''
(V2/'README.md').write_text(old)
restore=(V2/'RESTORE.md').read_text();restore=restore[:restore.index('## Næste faglige arbejde')]+f'''## Gendan den komplette første rågennemgang

Hent de to batch01-inputarkiver fra [første rågennemgang](triage_batch01/README.md) og de seks batch02-inputarkiver fra [anden rågennemgang](triage_batch02/README.md). Kontrollér SHA-256 mod de respektive `INPUT_CHECKPOINTS.json`. Arkiverne bruger projektmappen som rod. De giver rå/native-produkter for alle92 eksponeringer med mindst ét V2-hit.

Pak `triage_batch01/TRIAGE01_EVIDENCE.zip`, `triage_batch02/TRIAGE02_EVIDENCE.zip`, `mapping_followup/MAPPING_FOLLOWUP_EVIDENCE.zip` og `mapping_followup_additional/ADDITIONAL_MAPPING_EVIDENCE.zip` ud i en separat mappe. Kontrollér medlemmer mod de tilhørende arkivmanifester; overskriv ikke nyere dokumenter. De to mapping-arkiver genbruger batch01-råinput. Den aktuelle tabel er `triage_batch02/CUMULATIVE_DISPOSITIONS.csv`; alle tidligere tabeller bevares.

Fra en arbejdskopi kan `python v2/triage_batch02/audit_numerical.py` gentage metadata-/hashkontrol og tre metadatavalgte eksponeringers udtræk. `python v2/triage_batch02/finalize_review.py` og `python v2/triage_batch02/combine_followup.py` gendanner dispositionstabeller fra gemte manuelle noter; dette genskaber ikke en ny visuel vurdering.

## Næste faglige arbejde

{status}

Fortsæt med lokale referencemangler for43 hændelser og alle-epoke-sammenligning/linjeidentifikation for64 uafklarede strukturer.53 af de64 har et andet accepteret hit inden for±0,03Å barycentrisk; det er ikke en fuld epokekontrol. V2-0205 har en efterfølgende O I6363,776-hypotese, som ikke ændrer det oprindelige to-linje-flag eller den bevarede uafklarede status.

Batch01 og batch02 bruger forskellige opfølgningskontroller; sammenfat ikke klassetællinger som en kalibreret falsk-alarm-rate. Den fastlåste detektor må ikke tilpasses de nu kendte udfald. De200 hovedeksponeringer er uændrede. Råprodukterne giver ingen ny eksponeringstid. Rubin-data er endnu ikke analyseret.
'''
(V2/'RESTORE.md').write_text(restore)
print('Current reports updated from verified counts')
