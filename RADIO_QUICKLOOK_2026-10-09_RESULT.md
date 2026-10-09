# SETI: faktisk signalanalyse, 9. oktober 2026

Seks autentiske radiooptagelser er hentet og analyseret: tre målscanninger (ON) af HIP98505 og tre tilhørende kontrolscanninger (OFF). Driftsøgningen dækker nu **2,950012 MHz pr. ON-scanning**, med 1.040.384 sammenhængende frekvenskanaler i hver. Der er ikke påvist et overbevisende signal, som kan tilskrives en udenjordisk sender.

Den stærkeste linje ligger ved **1423,828125 MHz** og findes tydeligt i alle seks scanninger. Det er konkret modbevis mod at behandle den som et signal, der alene følger målretningen. Observationen er forenelig med fælles interferens eller instrumentstruktur; dens fysiske oprindelse er ikke fastslået.

| Målscanning | Højeste gemte driftsøgningsscore | Sammenhængende grupper med score ≥10 |
| --- | ---: | ---: |
| ON1 | 143,746857 | 94 |
| ON2 | 145,381107 | 74 |
| ON3 | 148,084632 | 52 |

Alle tre maksimummer ligger på samme stationære linje. I den særskilte, gemte nuldriftsprojektion har linjen værdier 153,88–157,29 i ON og 154,70–157,12 i OFF. Disse projektionsværdier og driftsøgningsscorer har forskellige normaliseringer og må ikke sammenlignes som kalibreret SNR.

De 220 grupper er beskrivelser af korrelerede kanaler, ikke 220 uafhængige hændelser. 218 har mindst én OFF-projektion ≥10 inden for det undersøgte sporinterval. De sidste to er udtaget til individuel inspektion ved **1423,953494 MHz** og **1422,573052 MHz**, med søgescore henholdsvis 11,1091 og 10,2665. Deres gemte ON-projektioner er 7,06 og 9,13; OFF når henholdsvis 9,04 og 9,39. En OFF-værdi under den beskrivende grænse 10 betyder derfor ikke fravær af struktur. Den individuelle gennemgang er gemt i [REVIEW.json](results/radio_quicklook_20261009/flagged_review/REVIEW.json).

Ved 1423,95456 MHz findes også en kraftig stationær linje i både ON og OFF. Skrå søgespor kan få høj score, når de krydser en sådan linje i én ON-scanning, selv om deres ekstrapolerede OFF-spor rammer en anden frekvens. Derfor bevares både rå billeder og kontrolmålinger, og en lav score langs det ekstrapolerede OFF-spor bruges ikke alene som kandidatbevis.

En efterfølgende tidsopløst kontrol gennemgik den stærkeste resterende gentagne ON-gruppe efter gemt ON-score/største OFF-projektion. Sporet ved **1423,954061 MHz** er synligt i alle seks scanninger. Medianen af de 16 lokale rækkemaksima over den gemte rækkemedian er 0,855/0,953/0,835 i ON og 0,985/0,895/0,901 i OFF. Det etablerer ikke ON-eksklusivitet og giver stærk OFF-mod-evidens; oprindelsen forbliver uafklaret. Sporet ligger 499,049 Hz under den stærke 1423,954560-MHz-kontrollinje. Se [det konkrete resultat](RADIO_REPEATED_TRACK_1423954061_2026-10-09_RESULT.md).

Den næste distinkte gentagne familie ved **1422,596235 MHz** er også kontrolleret tidsopløst. Linjen er bevaret på samme kanal i alle 96 tidsrækker fordelt over de seks scanninger. Parrede median-rækkemaksima er 0,433/0,439, 0,381/0,401 og 0,495/0,419 i ON/OFF. Kandidatmaksimum ligger over de lokale flanker i samtlige rækker, også OFF. Det er konkret stærk mod-evidens mod ON-eksklusivitet, men ingen fysisk oprindelsesklassifikation. Se [den anden individuelle kontrol](RADIO_REPEATED_FEATURE_1422596235_2026-10-09_RESULT.md).

De to øvrige distinkte familier fra maksimumprioriteringen er derefter kontrolleret. Den stærke linje ved **1424,439182 MHz** står i alle ON/OFF-tidsrækker med median-rækkemaksima 1,522–1,694 over rækkemedianen. Den svagere **1424,411711 MHz**-linje gav oprindeligt kun én ON-gruppe over den beskrivende scoregrænse, men tidsprofilen viser den på samme kanal i alle seks scanninger; OFF-medianerne 0,297/0,313/0,320 er sammenlignelige med ON 0,335/0,339/0,292. Begge mangler ON-eksklusivitet og bevarer uafklaret oprindelse. Se [den samlede individuelle kontrol](RADIO_REMAINING_FEATURES_2026-10-09_RESULT.md).

Søgningen brugte 763 lineære topocentriske drifthastigheder mellem −4 og +4 Hz/s og bredder på 1 og 3 kanaler. Kanalbredden er 2,835503 Hz. De 254 frekvensudsnit er valgt efter deres koordinater; hver ON er søgt selvstændigt, så et signal i kun én målscanning bliver bevaret. Det svarer til 4.762.877.952 nominelle, stærkt korrelerede sporhypoteser over de tre ON-scanninger. Den indledende smalle søgning overlapper den endelige dækning og lægges ikke oveni.

Det gennemgåede centerfrekvensinterval er **1421,570613–1424,520623 MHz**. De yderste 4.096 kanaler i hver ende af det hentede fysiske frekvensstykke er udeladt fra driftsøgningen af hensyn til spor- og normaliseringsmarginer. Hele det hentede stykke på 2,973241 MHz har en gemt nuldriftsoversigt for alle seks scanninger.

Optagelserne er én historisk observation fra 17. marts 2016, ikke seks uafhængige besøg. Samlet ON-integration er **863,34 sekunder (14,39 minutter)**. Analysen blev udvidet efter åbning af data og er eksplorativ. Scoregrænsen er beskrivende; falskalarmrate, følsomhed, flux og EIRP er ikke kalibreret. Kontrolprojektionen kan overse drivende eller kortvarige signaler. Resultatet udgør ikke en generel nuldetektion på himlen.

Den oprindelige A/B-kvalifikation forbliver **FAIL_CLOSED**, og den oprindelige kvalificerede pilot er fortsat blokeret. Den gamle plan er lukket. Dette er faktisk signalarbejde under den godkendte plan 7.–20. oktober, med særskilt eksplorativt omfang og uændrede beskyttede testdatasæt.

96 afgrænsede kildeforespørgsler modtog 305.133.821 bytes signaldata. De efterfølgende udvidelser og prioriteringen genbrugte disse data uden nye kildeforespørgsler. Originale komprimerede HDF5-stykker, kanalvise maksimummer, normaliseringer, sporfigurer og kontrolmålinger er bevaret.

Målte CPU-komponenter er 2,22 s for hentning, 25,00 s for første smalle søgning, 23,22 s for den brede oversigt, 433,11 s for de første 64 udsnit, 804,63 s for de øvrige 190, 0,65 s for prioritering af gemte resultater, 2,24 s for individuel gennemgang af de to flag, 1,34 s for 1423,954061-MHz-kontrollen, 0,94 s for 1422,596235-MHz-kontrollen og 1,35 s for de sidste to prioriterede familier. Installation, forberedelse, gemning og publicering er ikke samlet CPU-målt; tallene er ikke et totalregnskab. Den konservative reservation er 3.800 CPU-s. Saldo er **2.112,705 CPU-s**, heraf **2.000 beskyttet til 20. oktober**, uden refusion eller dobbelt debitering. Pris: 0 DKK.

Videre arbejde prioriterer konkrete, gemte signalspor og deres kontrolmålinger. De afsluttede søgninger, den gamle testbank og tidligere dokumentkontroller skal ikke køres igen. Ny bred søgning kræver plads i det eksisterende budget; det beskyttede slutbudget bruges ikke automatisk.

Reproducerbar evidens: [SIGNAL_TRIAGE.json](results/radio_quicklook_20261009/SIGNAL_TRIAGE.json), [SIGNAL_GROUPS.csv](results/radio_quicklook_20261009/SIGNAL_GROUPS.csv), [1423,954061-MHz-kontrol](results/radio_quicklook_20261009/repeated_1423954061/RESULT.json), [1422,596235-MHz-kontrol](results/radio_quicklook_20261009/repeated_1422596235/RESULT.json), [to sidste familier](results/radio_quicklook_20261009/remaining_features/RESULT.json), [RESOURCE_LEDGER.json](results/radio_quicklook_20261009/RESOURCE_LEDGER.json) og [EXTERNAL_DATA_ARCHIVES.json](results/radio_quicklook_20261009/EXTERNAL_DATA_ARCHIVES.json). Kode og frosne omfang ligger i [tools/radio_quicklook_20261009](tools/radio_quicklook_20261009).
