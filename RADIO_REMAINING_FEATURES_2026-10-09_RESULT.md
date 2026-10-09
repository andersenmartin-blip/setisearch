# HIP98505: tidsopløst kontrol af to resterende prioriterede frekvensfamilier

De to resterende distinkte familier blandt den afsluttede brede maksimumprioritering er nu kontrolleret i alle seks autentiske scanninger. Analysen genbrugte to frosne 250-kanalsvinduer fra den lokale cache; ingen nye data, detektorscorer, drifthastigheder eller bredder blev åbnet.

## 1424,439182 MHz

Den stærke linje har en gemt gruppe i alle tre ON-scanninger og står på samme kanal gennem hele besøget.

| Scanning | Rolle | Median-rækkemaksimum over rækkemedianen | Median maksimum minus lokale flanker |
| --- | --- | ---: | ---: |
| ON1 | ON | 1,544298 | 1,526065 |
| OFF1 | OFF | 1,521860 | 1,498077 |
| ON2 | ON | 1,567073 | 1,553631 |
| OFF2 | OFF | 1,594189 | 1,570419 |
| ON3 | ON | 1,694301 | 1,655127 |
| OFF3 | OFF | 1,605568 | 1,592901 |

Linjen er bevaret i samtlige 96 tidsrækker. OFF2 er en smule højere end ON2, og de øvrige OFF-målinger er sammenlignelige med ON. ON-eksklusivitet er ikke etableret.

## 1424,411711 MHz

Denne svagere linje gav oprindeligt kun én beskrivende ON-gruppe over score 10, men den tidsopløste kontrol viser den samme kanal i alle seks scanninger.

| Scanning | Rolle | Median-rækkemaksimum over rækkemedianen | Median maksimum minus lokale flanker |
| --- | --- | ---: | ---: |
| ON1 | ON | 0,335319 | 0,300979 |
| OFF1 | OFF | 0,297321 | 0,277596 |
| ON2 | ON | 0,338661 | 0,292931 |
| OFF2 | OFF | 0,312780 | 0,289250 |
| ON3 | ON | 0,292451 | 0,253876 |
| OFF3 | OFF | 0,319767 | 0,279245 |

Selv det mindste enkelt-rækkes maksimum ligger 0,095 over de lokale flanker. OFF3 er højere end ON3; OFF1/OFF2 er lidt lavere end ON, men klart til stede. At kun ON1 krydsede den tidligere beskrivende scoregrænse er derfor ikke OFF-fravær.

Begge dispositioner er `NO_ON_EXCLUSIVITY_STRONG_OFF_COUNTEREVIDENCE_ORIGIN_UNRESOLVED`. OFF-respons er mod-evidens mod målretning, ikke en oprindelsesklassifikation. De seks scanninger er ét historisk besøg, og A/B-kvalifikationen forbliver **FAIL_CLOSED**.

Kørslen læste 48.000 cachede power-værdier på applikationsniveau og brugte 1,351858 CPU-s, 1,352355 s wall og 156.708.864 bytes peak RSS. Den konservative 40-CPU-s-reservation refunderes ikke. Saldoen er **2.112,705145 CPU-s**, heraf **2.000 beskyttet til 20. oktober**. Pris: 0 DKK.

Evidens: [resultatkvittering](results/radio_quicklook_20261009/remaining_features/RESULT.json), [alle tidsrækker](results/radio_quicklook_20261009/remaining_features/ROW_PROFILES.csv), [1424,439182-MHz-figur](results/radio_quicklook_20261009/remaining_features/repeated_1424439182.png), [1424,411711-MHz-figur](results/radio_quicklook_20261009/remaining_features/single_group_1424411711.png), [frosset omfang](tools/radio_quicklook_20261009/remaining_features_scope.json) og [analyseprogram](tools/radio_quicklook_20261009/inspect_remaining_features.py).
