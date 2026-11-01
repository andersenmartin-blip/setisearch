# Opfølgning på 43 usikre HARPS billedkoblinger

**39 af de 43 hændelser har nu tilstrækkelig støtte fra bredere, faste referenceområder.** Ingen råkoordinater er flyttet. Efter to separate agentgennemgange er udfaldet otte sandsynlige detektorartefakter, 31 uafklarede spektralstrukturer og fire fortsat utilstrækkeligt kortlagte tilfælde. Alle ophavsvurderinger er foreløbige.

| Foreløbig status efter opfølgning | Hændelser |
|---|---:|
| Sandsynlig detektorartefakt | 8 |
| Uafklaret spektralstruktur | 31 |
| Utilstrækkelig råbilledkortlægning | 4 |

[Alle 43 dispositioner med to begrundelser](FOLLOWUP_DISPOSITIONS.csv) · [maskinlæsbar sammenfatning](SUMMARY.json) · [figurer](FIGURES.md).

## Hvad der er undersøgt

Gruppen var fastlagt som alle 43 hændelser med kortlægningsbegrænsning i den tidligere samlede tabel. De stammer fra 26 eksponeringer. Alle 52 tilhørende rå- og native-produkter er hashkontrolleret. Den fastlåste V2-detektor og dens oprindelige resultater er uændrede.

Den gamle lokale kontrol krævede to korte referenceintervaller på hver sin side af en hændelse. Mange lå tæt på en ordensrand eller andre kandidatpositioner, så der manglede referencepixels. Den nye plan blev skrevet før de bredere områder blev undersøgt: fem faste intervaller fordelt over hver dækkende orden, med alle gemte kandidaters nærmeste ±80 pixels udeladt. Mindst tre intervaller skal have tilstrækkelig støtte, median rå/native-korrelation over 0,8 og små kontinuumforskydninger. Fiberprofilen samles ved den flydende polynomiumposition, så skiftende heltalsafrunding ikke flytter den samlede profil. Koordinater og orientering er ikke tilpasset kandidatens kerne. [Plan](PLAN.json) · [alle referenceværdier](MAPPING_AUDIT.json).

Dette er en efterfølgende kontrol af kendte problemer. Den sletter ikke de gamle fejlede intervaller og giver ikke en kalibreret statistisk ophavstest. Kriterierne er kun anvendt på denne gruppe, så forskellige historiske opfølgningsmetoder skal fortsat fremgå af den samlede rapport.

## Resultatet af billedgennemgangen

De otte foreløbige artefakter er V2-0106, 0155, 0186, 0217, 0228, 0235, 0306 og 0326. De har kompakte eller skrå/tværgående råpixelspor og typisk en skarp top i kun den ene overlappende orden. De lyse nabofibersignaler er vist som kontekst og bruges ikke alene som forklaring.

De 31 uafklarede strukturer er hovedsagelig bredere toppe med fiberforenelig råprofil og ofte støtte fra overlappende ordener. Flere blå randudsnit har meget svagt kontinuum; store normaliserede udsving, især V2-0244, betyder derfor ikke tilsvarende stor fysisk emission. De kræver epokesammenligning og konkret naturlig linjeidentifikation. De er ikke påviste teknologiske signaler.

Fire hændelser forbliver kortlægningsusikre efter de fastlagte kriterier:

| Hændelse | Dækkende orden med begrænsning | Median rå/native-korrelation |
|---|---:|---:|
| V2-0149 | 1; orden 0 er randafskåret | 0,547 |
| V2-0231 | 3 | 0,766 |
| V2-0232 | 3 | 0,766 |
| V2-0333 | 70 | 0,768 |

Kontinuumpositionerne i disse bredere områder er tæt på den forudsagte fiber, men spektralkorrelationen opfylder ikke grænsen. Det er ikke bevis for forkerte headerkoordinater; det er en bevaret begrænsning. De fire gamle tilfælde med målt lokal forskydning var en anden delmængde: V2-0149, 0186, 0221 og 0284. De sidste tre støttes nu af de bredere faste referencer uden en koordinatændring.

## Kontrol og reproduktion

Der er 81 dækkende ordensregistreringer: 80 komplette udsnit og én bevaret randbegrænsning. To agenter har hver set samtlige 43 hændelser og alle tilgængelige ordener; alle 43 foreløbige koder stemmer. Det er ikke uafhængig menneskelig validering.

Alle 80 nye, bredere råudsnit indeholder de oprindelige 21×25 råpixels uændret, og alle 41 native spektralværdier/bølgelængder er identiske. En frisk proces genopbyggede fem bredere udsnit fra første, midterste og sidste eksponering i metadatarækkefølgen med præcis samme resultat. [Efterkontrol](OUTPUT_VERIFICATION.json).

Brug en separat arbejdskopi. Input ligger i de tidligere batch02-checkpoints; denne opfølgning henter ingen nye teleskopdata. Kør `python v2/mapping43_followup/run_mapping.py`, derefter `plot_mapping.py` og `verify_outputs.py`. De eksplicitte visuelle noter ligger i `VISUAL_NOTES_PRIMARY.json` og `VISUAL_NOTES_SECOND_AGENT.json`; `finalize.py` samler dem, men udfører ikke en ny automatisk ophavsvurdering. Afhængigheder er Python, NumPy, SciPy, Astropy og Matplotlib som i hovedprojektet.

`MAPPING43_EVIDENCE.zip` indeholder kode, planer, tabeller, noter, verificerede numeriske udsnit og referencekontroller. PNG-figurer publiceres separat. [Arkivmanifest](EVIDENCE_ARCHIVE.json).
