# Fast frekvenskontekst for de ni gap-driftprofiler — 10. oktober 2026

Alle ni origin-ON-sammenligninger har negativ statisk-minus-bevægelig middelforskel, fra −0,193264 til −0,045825. De bevægelige spor blev tidligere valgt efter driftmaksima i netop deres origin-ON; dette resultat kan derfor ikke bruges som uafhængig støtte for drift eller oprindelse.

Ved de ni oprindelige referencefrekvenser har 5/9 af origin-ON-profilerne positive faste middelværdier i begge tidsmæssige halvdele. Blandt de 15 forekomster af tilstødende OFF-kontroller gælder det 2/15. De statiske middelværdier spænder fra -0,026900 til 0,054964 i origin-ON og fra -0,043941 til 0,036954 i de tilstødende OFF-forekomster. Det er beskrivende tal efter udvælgelse; positivitet er ikke en kalibreret detektion.

Der er et konkret eksempel på OFF-kontekst, som det bevægelige center ikke beskriver: for ON2 rang 3 er det faste OFF1-middel 0,034722 mod origin-ON2's faste 0,033165, mens det kopierede bevægelige OFF1-center på samme baggrund er −0,016682. OFF1's faste halvdele er begge positive, 0,042074 og 0,027370. Det dokumenterer forskellig fast og bevægelig frekvenskontekst; det fastslår ikke, at de to forløb har samme årsag.

Diagnosen undersøger, om en lille tidligere OFF-værdi langs det valgte driftspor overså struktur på dets faste begyndelsesfrekvens. Referencesystemet er hvert spors oprindelige kanal ved origin-ON-scanningens første midpoint, ikke et tilpasset centrum for en stationær linje. De nye faste vinduer dækker derfor en bestemt fysisk kontekst og kan ikke afgøre, om der findes OFF-struktur andre steder langs hele driftsporet.

## Beregningen og dens afgrænsning

Alle ni tidligere offentliggjorte gap-drift rang 1–3-spor blev medtaget med deres oprindelige referencekanal og bredde 1 eller 3. For hvert spor blev samme 129 fysiske kanaler, reference ±64, udtrukket i alle seks scanninger og alle 16 tidsrækker. Normaliseringen bruger de tidligere gemte fuld-bånds rækkemedianer. Fast baggrund er medianen af de 122 rækkenormaliserede kanaler med absolut offset >3 inden for ±64.

S betegner det faste centers middel ved oprindelig bredde minus den faste baggrund. D betegner det uændret kopierede, oprindelige bevægelige centers normaliserede middel minus præcis samme faste baggrund. Den gemte signerede forskel er Δ = statisk center minus kopieret bevægeligt center; fælles baggrund bortfalder algebraisk. Originalsporets residual med dets oprindelige bevægelige baggrund er bevaret separat.

Ingen frekvens, drift, bredde, rang, maksimum, tærskel eller lokal forskydning blev søgt eller tilpasset. Kilde- og tidligere gap-værdier/rangeringer var allerede eksponeret; kun denne afledte diagnose blev fastlåst før beregningen. Det er ikke blind eller uafhængig validering. De seks scan-labels betegner ét historisk besøg ved HIP98505/HD189733 den 17. marts 2016, ikke tre uafhængige epoker.

## Alle 54 faste scan-midler

Tallene er additive forskelle i rækkenormaliseret effekt, afrundet til seks decimaler. Fuldpræcision, medianer, positive rækketal, begge halvdele og alle 16 rækker findes i JSON og CSV. Halvdelene er fast rækker 0–7 og 8–15.

| Oprindelig case | Referencekanal | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ON1 r1 (w3) | 158358343 | 0,031258 | -0,022945 | -0,000364 | 0,023607 | 0,001824 | 0,009348 |
| ON1 r2 (w3) | 158355634 | 0,018574 | -0,043941 | 0,020431 | 0,029246 | 0,002041 | -0,002181 |
| ON1 r3 (w3) | 158879966 | 0,021080 | -0,012105 | -0,014027 | 0,002362 | 0,013194 | 0,003240 |
| ON2 r1 (w1) | 159145548 | -0,000980 | 0,036954 | -0,020997 | -0,011139 | -0,008167 | -0,019725 |
| ON2 r2 (w1) | 159144660 | 0,009717 | -0,001223 | 0,048534 | 0,008368 | -0,008475 | -0,020903 |
| ON2 r3 (w1) | 159014473 | -0,000416 | 0,034722 | 0,033165 | 0,002083 | 0,001536 | -0,021637 |
| ON3 r1 (w1) | 158489515 | -0,010944 | -0,008316 | -0,005401 | -0,019992 | 0,054964 | 0,004894 |
| ON3 r2 (w1) | 158490607 | 0,034834 | 0,000663 | -0,001739 | 0,025724 | -0,026900 | -0,011555 |
| ON3 r3 (w1) | 159145372 | 0,015383 | 0,046504 | 0,024241 | -0,004613 | 0,000166 | 0,004254 |

## Origin-ON og de observerede nabokontroller

ON1 har ingen forudgående OFF i dette seks-scan-udsnit; det markeres som ikke observeret. ON2 bruger OFF1 og OFF2, og ON3 bruger OFF2 og OFF3. Der vælges ingen efterfølgende kontrol ud fra resultaterne.

| Case | Origin S | Origin D | Origin Δ | Origin mindste halvdel | Forudgående OFF S | Efterfølgende OFF S |
|---|---:|---:|---:|---:|---:|---:|
| ON1 r1 (w3) | 0,031258 | 0,095194 | -0,063937 | 0,009209 | Ikke observeret | -0,022945 |
| ON1 r2 (w3) | 0,018574 | 0,091227 | -0,072653 | 0,012217 | Ikke observeret | -0,043941 |
| ON1 r3 (w3) | 0,021080 | 0,092707 | -0,071628 | -0,001783 | Ikke observeret | -0,012105 |
| ON2 r1 (w1) | -0,020997 | 0,095553 | -0,116551 | -0,034828 | 0,036954 | -0,011139 |
| ON2 r2 (w1) | 0,048534 | 0,094359 | -0,045825 | 0,042584 | -0,001223 | 0,008368 |
| ON2 r3 (w1) | 0,033165 | 0,141604 | -0,108439 | 0,005629 | 0,034722 | 0,002083 |
| ON3 r1 (w1) | 0,054964 | 0,163119 | -0,108155 | 0,032388 | -0,019992 | 0,004894 |
| ON3 r2 (w1) | -0,026900 | 0,166364 | -0,193264 | -0,035830 | 0,025724 | -0,011555 |
| ON3 r3 (w1) | 0,000166 | 0,097500 | -0,097335 | -0,026764 | -0,004613 | 0,004254 |

## Signeret fast minus bevægelig forskel

Alle 54 scan-middelforskelle er bevaret. En positiv Δ fortæller, at det fastlagte statiske center har højere normaliseret effekt end det oprindelige bevægelige center ved denne scanning. En negativ Δ fortæller det modsatte. Forskellen klassificerer ikke et signal og er ikke en signifikansstatistik.

| Case | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |
|---|---:|---:|---:|---:|---:|---:|
| ON1 r1 (w3) | -0,063937 | 0,010071 | 0,001019 | 0,029466 | -0,005534 | 0,029381 |
| ON1 r2 (w3) | -0,072653 | -0,055060 | 0,032716 | 0,032899 | -0,006244 | -0,021393 |
| ON1 r3 (w3) | -0,071628 | -0,036435 | -0,036846 | -0,007132 | -0,014382 | -0,000422 |
| ON2 r1 (w1) | 0,026520 | 0,052006 | -0,116551 | -0,006724 | 0,003766 | -0,010442 |
| ON2 r2 (w1) | 0,017113 | -0,012323 | -0,045825 | 0,014976 | -0,049375 | -0,042445 |
| ON2 r3 (w1) | -0,018816 | 0,051404 | -0,108439 | 0,016433 | -0,027585 | -0,026261 |
| ON3 r1 (w1) | 0,016999 | -0,007184 | 0,017583 | 0,006329 | -0,108155 | -0,040493 |
| ON3 r2 (w1) | 0,043118 | 0,000254 | 0,012164 | 0,002676 | -0,193264 | -0,015617 |
| ON3 r3 (w1) | -0,004184 | 0,032032 | 0,039695 | 0,004753 | -0,097335 | 0,004616 |

| Beskrivende udvalg | Forekomster | S middel >0 | S begge halvdele >0 | Δ>0 / =0 / <0 | Median Δ | Δ min. / maks. |
|---|---:|---:|---:|---:|---:|---:|
| Alle | 54 | 30 | 12 | 24 / 0 / 30 | -0,005889 | -0,193264 / 0,052006 |
| ON, alle cases | 27 | 16 | 7 | 10 / 0 / 17 | -0,014382 | -0,193264 / 0,043118 |
| OFF, alle cases | 27 | 14 | 5 | 14 / 0 / 13 | 0,000254 | -0,055060 / 0,052006 |
| Origin-ON | 9 | 7 | 5 | 0 / 0 / 9 | -0,097335 | -0,193264 / -0,045825 |
| Tilstødende OFF | 15 | 7 | 2 | 9 / 0 / 6 | 0,004616 | -0,055060 / 0,052006 |

Disse udvalg overlapper. De ni rangvalgte cases deler scanninger og normalisering; de 15 nabokontrolforekomster genbruger tre fysiske OFF-scanninger. Antal er derfor case×scan-forekomster, ikke uafhængige forsøg. ON/OFF-pegeretninger og observationstider er forskellige og giver ikke en udskiftelig nulfordeling.

## Hvad diagnosen kan og ikke kan afgøre

Det faste vindue strækker sig kun ±181,472219 Hz fra den oprindelige reference. De gamle bevægelige centers største udflugter fra disse referencer når 1.833 native kanaler, langt uden for ±64. Et svagt fast OFF-middel fastslår derfor ikke fravær af struktur langs hele det bevægelige spor, og et positivt fast OFF-middel fastslår ikke, at statisk og bevægelig struktur har samme årsag.

Baggrundens algebraiske bortfald i Δ retter ikke forskelle i continuum eller bandpass mellem fjerntliggende centerfrekvenser. De nye statiske profiler og de gamle bevægelige profiler skal vurderes med deres forskellige frekvensgeometri. Originalsporets bevægelige flankeresidualer er bevaret som separat kontekst og kan ikke uden videre erstatte den fælles-baggrunds-sammenligning.

Der er ingen kalibreret SNR, falsk-alarm-sandsynlighed, RFI-klassifikation, flux, følsomhed eller oprindelsesafgørelse. A/B-status er fortsat FAIL_CLOSED; ingen kvalificeret himmelpilot er optaget, og gamle holdouts er fortsat lukkede. Stærkere evidens kræver nye, uafhængige observationer med overlappende frekvensdækning og relevante kontroloplysninger.

## Figurer og reproduktion

Begge gemte figurer er kontrolleret visuelt i original opløsning; mærkater, tabeller og akser er læsbare. Den særskilte JSON-baserede figurfremstilling brugte 7,613889 CPU-s og overskred sin 6 CPU-s visningsgrænse. De to allerede fremstillede figurer og den faktiske kvittering er bevaret; der blev ikke tegnet igen. Den numeriske science-kørsel holdt sin 20 CPU-s grænse.

- [Alle 54 S-, D- og Δ-midler på samme faste baggrund](results/radio_gap_static_context_20261010/figures/STATIC_MOVING_SAME_BACKGROUND_MEANS.png).
- [Alle ni faste 129-kanalprofiler i samtlige seks scanninger](results/radio_gap_static_context_20261010/figures/STATIC_PHYSICAL_FREQUENCY_PROFILES.png). De ni paneler har separate y-skalaer; frekvenserne er fysiske, og alle 129 gemte samples er bevaret.
- [Tabsfri gzip af fuld resultat-JSON](results/radio_gap_static_context_20261010/measurement/STATIC_CONTEXT_PROFILES.json.gz), [54 scan-oversigter](results/radio_gap_static_context_20261010/measurement/STATIC_CONTEXT_54_SCAN_SUMMARIES.csv) og [864 tidsrækker](results/radio_gap_static_context_20261010/measurement/STATIC_CONTEXT_864_TIME_ROWS.csv). CSV bruger Python-floatens round-trip tekstværdi uden afrunding.
- Den binære fil `ALL_NINE_STATIC_AND_COPIED_MOVING_PROFILES.npz` indeholder rå/normaliserede faste profiler og uændrede bevægelige arrays; filens størrelse og SHA256 står i [eksekveringskvitteringen](results/radio_gap_static_context_20261010/measurement/EXECUTION_RECEIPT.json). Binær levering dokumenteres med den afsluttende resultatpakke.

Offentlig fastlåsning før numerisk kørsel: Git-commit `1fbb2fcf328581a7ceffda97d6db36850c4ba8ea`. [Numerisk kode](tools/radio_gap_static_context_20261010/static_context.py), SHA256 `5a72c346151123aa52d59d3b2c1fdc0e2e301a5537ffd752a0bb7109d84fc0d9`; [scope](tools/radio_gap_static_context_20261010/scope.json), SHA256 `d5e3f9981e564ea6f933184d9de63aaf2edc28ae29f0c5e061885b2dc7387881`. Scope indeholder alle input- og afhængighedshashes og de ni uændrede referencekanaler/bredder.

Den eneste numeriske kørsel er COMPLETE: CPU 4,580136 s, vægtid 4,175947 s og maksimal RSS 476.180.480 bytes. Grænser: 20 CPU-s, 1.800 s og 4 GiB; ingen genkørsel. Runtime-pins er numpy 2.3.5, h5py 3.15.1 og hdf5plugin 7.1.0 med den uændrede loader.

Reproduktionsgrundlaget er de seks gendannede kompakte chunk151-filer, deres 96 afkodede rækkepins, de gemte normaliseringer, de ni gamle gap-NPZ og kilde-/analysemetadata. Hashverificering af kompaktene og de 96 rækker validerer disse gemte dele. Hele de oprindelige teleskopfiler er ikke gendannet, og deres fulde MD5 er fortsat uverificeret; delvise pins må ikke læses som validering af hele originalkilderne.

Arkivgendannelsen hentede 311.847.026 bytes; de samme præcist pinnede afhængighedswheels krævede 51.507.696 bytes. Det konservative samlede kilde-, gendannelses- og afhængighedsregnskab er 2.002.313.292 bytes. Denne aktivitet foretog 0 nye teleskop-HTTP-requests og hentede 0 nye teleskop-body-bytes. Den reserverer 60 CPU-s, heraf 20 til beregning og 40 til klargøring, kontrol og publicering, inden for uændrede 43.200 CPU-s. Tidligere reservationer refunderes ikke; efter reservationen resterer 2,705145 CPU-s.

På en separat, komplet kopi med de samme pakkeversioner og verificerede input kan den fastlåste kode køres i en ny tom resultatmappe. Kommandoen nedenfor beskriver reproduktion; den blev ikke kørt igen i dette arbejde.

```bash
PYTHONPATH=seti_gap_static_work/deps python setisearch_checkpoint/tools/radio_gap_static_context_20261010/static_context.py \
  --scope setisearch_checkpoint/tools/radio_gap_static_context_20261010/scope.json \
  --expected-scope-sha256 d5e3f9981e564ea6f933184d9de63aaf2edc28ae29f0c5e061885b2dc7387881 \
  --compact-dir setisearch_checkpoint/results/radio_fresh_band_20261009/arrays \
  --acquisition-summary setisearch_checkpoint/results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json \
  --outdir NY_TOM_RESULTATMAPPE
```

[Rapport-/CSV-scriptet](tools/radio_gap_static_context_20261010/summarize_saved_context.py) læser kun afsluttet JSON og serialiserer gemte tal; det genmåler ingen science-arrays og udfører ingen ny søgning. [Beskrivende oversigt](results/radio_gap_static_context_20261010/measurement/DESCRIPTIVE_FINDINGS.json) bevarer udvalg og fuldpræcisionstal. Den samlede resultatpakke er beskrevet nedenfor.

## Afsluttende kontrol og resultatpakke

[Uafhængig kontrol](results/radio_gap_static_context_20261010/measurement/QA_RECEIPT.json) består for alle 153 uændrede gamle arraykopier, 216 opsummeringer, 3.456 metrik-rækkeforekomster og 6.966 statiske frekvenssamples. Begge CSV-filer bevarer alle 54/864 rækkeidentiteter og flydende værdier ved bitpræcis round-trip. Kontrollen genlæste ingen HDF5-værdier og udførte ingen ny søgning. Kildens 111.456 råcelle-sammenligninger henføres til den eneste afsluttede målekørsel.

`SETI_GAP_STATIC_CONTEXT_2026-10-10.zip` samler rapport, figurer, originale JSON/CSV, den binære NPZ med alle nye og kopierede gamle arrays, alle 15 pinnede kode-/metadata-/profilinputs, scopes, kontrolkode, miljøkvitteringer og det ikke godkendte forslag. [Filmanifestet](results/radio_gap_static_context_20261010/BUNDLE_MANIFEST.json) angiver byteantal og SHA256. Det offentlige store JSON er tabsfrit gzip; pakken indeholder også det oprindelige ukomprimerede JSON. De kompakte HDF5-inputs leveres separat i det allerede gemte `SETI_FRESH_BAND151_RAW_2026-10-09.zip`, 305.428.707 bytes, SHA256 `6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d`. Hele teleskopfiler og wheels er ikke genpakket.

Pakningen afkoder ingen science-arrays og kontrollerer alle ZIP-medlemmers bytes, hashes og CRC. Den gentager ingen signalanalyse. På en separat reproduktionskopi udtrækkes resultatpakken i `setisearch_checkpoint`, og kun de seks `results/radio_fresh_band_20261009/arrays/*.compact.h5` fra RAW-pakken placeres ved de angivne stier. Installer de to SHA-verificerede wheels fra miljøkvitteringerne med `python3 -m pip install --no-deps --target seti_gap_static_work/deps WHEEL_H5PY WHEEL_HDF5PLUGIN`; NumPy 2.3.5 skal allerede være tilgængelig. Miljøgendannelsesscriptet er den historiske udførte kode med oprindelige arbejdsstier, ikke en generisk ny downloader. Reproduktion kræver en resultatsti, der endnu ikke eksisterer, og separat autoriseret CPU; der blev ikke kørt en reproduktion i dette checkpoint.

[Ressourceoversigten](results/radio_gap_static_context_20261010/RESOURCE_SUMMARY.json) skelner mellem reservationer og målte delprocesser. Plotgrænsen på 6 CPU-s blev overskredet med den bevarede måling 7,613889; ingen ny plotkørsel blev foretaget. Den videnskabelige kørsels 20 CPU-s-grænse blev overholdt. Der hævdes ikke en samlet ende-til-ende CPU-måling.

[Det konkrete næste forslag](results/radio_gap_static_context_20261010/RADIO_NEXT_COMPUTE_PROPOSAL_2026-10-10.md) anmoder om 3.600 ekstra CPU-s, så totalrammen kan blive 46.800 CPU-s efter udtrykkelig godkendelse. Det omfatter de 214 resterende sikre delbånd i to fastlagte grupper på 107. Status er **IKKE GODKENDT · IKKE KØRT**; det nuværende checkpoint udvider ikke CPU-rammen og reserverer ingen tid til forslaget. Omkostningen forbliver 0 DKK, og kvalifikation, holdouts og øvrige grænser ændres ikke.
