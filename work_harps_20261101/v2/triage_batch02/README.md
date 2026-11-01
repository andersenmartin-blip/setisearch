# Rågennemgang af alle 333 HARPS V2 fund

Alle **333 V2-profilhits har nu en dokumenteret første rågennemgang**: 201 sandsynlige detektorartefakter, 25 forenelige med atmosfærisk O I, 64 uafklarede spektralstrukturer og 43 med utilstrækkelig lokal råbilledkontrol. Ingen identificeret laser eller kvalificeret SETI-kandidat. Vurderingerne er foreløbige; HARPS-ugen er fortsat delvis.

Denne levering gennemgår V2-0097–0333 i den eksisterende tabelrækkefølge: **237 hændelser fra 68 eksponeringer af 14 stjerner**. Desuden er seks tidligere usikre billedkoblinger undersøgt særskilt. Hovedprøven er fortsat **200 unikke eksponeringer af 20 stjerner, 46,750 timers samlet eksponering**. De ekstra råprodukter er kontrolmateriale til de samme observationer og giver ikke ekstra observationstid.

## Resultat og fuld hændelsesliste

| Foreløbig status | Nye 237 | Samlet 333 |
|---|---:|---:|
| Sandsynlig detektorartefakt | 140 | 201 |
| Forenelig med atmosfærisk O I | 14 | 25 |
| Uafklaret spektralstruktur | 40 | 64 |
| Utilstrækkelig lokal råbilledkontrol | 43 | 43 |


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

| Inputarkiv | Eksponeringer | Bytes |
|---|---:|---:|
| [SETI_HARPS_V2_TRIAGE02_INPUTS_PART1_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_cc64959dd4d8819180e9c9ecc9428768&account_id=personal) | 12 | 292,908,679 |
| [SETI_HARPS_V2_TRIAGE02_INPUTS_PART2_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_c53374f2fc888191a07efa9f7d12cd1c&account_id=personal) | 12 | 274,022,548 |
| [SETI_HARPS_V2_TRIAGE02_INPUTS_PART3_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_b0c31c3234208191be49669fe4001420&account_id=personal) | 12 | 287,299,384 |
| [SETI_HARPS_V2_TRIAGE02_INPUTS_PART4_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_dc21ae17ba448191aa486605cef4f4ed&account_id=personal) | 11 | 280,089,224 |
| [SETI_HARPS_V2_TRIAGE02_INPUTS_PART5_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_d0a23a24e8b881919ef38e54ff0db7fc&account_id=personal) | 11 | 290,571,060 |
| [SETI_HARPS_V2_TRIAGE02_INPUTS_PART6_2026-11-01.zip](https://chatgpt.com/library?file_id=libfile_3bbf0b5c05588191ae7ad16e8571079e&account_id=personal) | 10 | 206,344,472 |


De tidligere inputcheckpoints er fortsat nødvendige for de første 96 og de oprindelige spektre. Se [gendannelsesvejledning](../RESTORE.md). `TRIAGE02_EVIDENCE.zip` fastholder kode, metadata, alle 324 NPZ-udsnit, referencegitter og ekstra reviewmateriale; [arkivmanifest](EVIDENCE_ARCHIVE.json) angiver medlemmer og hashes. Hovedfigurerne ligger direkte i repository.

Arbejd altid i en separat kopi. Med de gemte input på deres manifeststier kan `python v2/triage_batch02/audit_numerical.py` efterprøve resultaterne. `extract_native.py`, `plot_native.py` og `plot_focus.py` genskaber udsnit og figurer. `finalize_review.py` og `combine_followup.py` samler de eksplicit gemte visuelle vurderinger; de udfører ikke selv en ny automatisk klassifikation. Afhængigheder er de samme som i [V2-rapporten](../README.md).

## Næste arbejde

1. Undersøg de 43 lokale kortlægningsbegrænsninger med særskilte, dokumenterede referenceområder; bevar alle hidtidige fejludfald.
2. Sammenlign de 64 uafklarede strukturer på tværs af alle tilgængelige epoker i relevante referenceframes og mod konkrete naturlige spektrallinjer.
3. Kontrollér de foreløbige atmosfære- og artefaktforklaringer med sky-, kalibrerings- og uafhængigt review, hvor data tillader det.

HARPS-ugen er delvist gennemført. Rubin-ugen er fortsat 8.–14. november og er endnu ikke analyseret. Der er ikke oprettet automatisk baggrundskørsel.
