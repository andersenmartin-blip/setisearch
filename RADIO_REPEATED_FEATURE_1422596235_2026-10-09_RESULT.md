# HIP98505: tidsopløst kontrol af linjen ved 1422,596235 MHz

Den næste distinkte gentagne frekvensfamilie efter de allerede afsluttede individuelle gennemgange blev undersøgt i de seks cachede autentiske scanninger. Familien har en gemt nuldriftsgruppe i hver ON-scanning og ligger ved **1422,596235 MHz** (kanal 160066324; ON3/OFF3 topper én kanal ved siden af).

Den frosne kontrol læste 250 kanaler × 16 tidsrækker i hver af de seks scanninger. Normaliseringen genbruger de allerede gemte hel-chunk-rækkemedianer. To kanalfanker på hver 40 kanaler giver kun lokal beskrivende kontekst; de er ikke en kalibreret støjmodel. Ingen nye data, detektorscorer, drifthastigheder eller bredder blev åbnet.

| Scanning | Rolle | Median-rækkemaksimum over rækkemedianen | Median maksimum minus lokale flanker |
| --- | --- | ---: | ---: |
| ON1 | ON | 0,432602 | 0,545158 |
| OFF1 | OFF | 0,438747 | 0,552065 |
| ON2 | ON | 0,380626 | 0,507314 |
| OFF2 | OFF | 0,400901 | 0,518439 |
| ON3 | ON | 0,495404 | 0,623853 |
| OFF3 | OFF | 0,418879 | 0,537058 |

Linjen er synlig på samme frekvens gennem alle seks scanninger. Selv den mindste enkelt-rækkes forskel mellem kandidatmaksimum og dens lokale flanker er positiv i hver scanning (0,307–0,389), så strukturen er bevaret i alle 96 tidsrækker. OFF1 og OFF2 har lidt højere median-rækkemaksimum end deres parrede ON, mens OFF3 er lidt lavere end ON3. **ON-eksklusivitet er derfor ikke etableret**, og OFF giver stærk konkret mod-evidens.

Disposition: `NO_ON_EXCLUSIVITY_STRONG_OFF_COUNTEREVIDENCE_ORIGIN_UNRESOLVED`. OFF-respons klassificerer ikke oprindelsen. Alle scanninger er fra det samme historiske besøg 17. marts 2016; der er ingen uafhængig genobservation. Den oprindelige A/B-kvalifikation forbliver **FAIL_CLOSED**.

Kørslen læste 24.000 cachede power-værdier på applikationsniveau og brugte 0,935857 CPU-s, 0,932930 s wall og 157.032.448 bytes peak RSS. Den konservative 30-CPU-s-reservation refunderes ikke. Saldoen er nu **2.152,705145 CPU-s**, heraf **2.000 beskyttet til 20. oktober**. Pris: 0 DKK.

Evidens: [resultatkvittering](results/radio_quicklook_20261009/repeated_1422596235/RESULT.json), [alle 96 tidsrækker](results/radio_quicklook_20261009/repeated_1422596235/ROW_PROFILES.csv), [seks-panels figur](results/radio_quicklook_20261009/repeated_1422596235/repeated_1422596235.png), [frosset omfang](tools/radio_quicklook_20261009/repeated_1422596235_scope.json) og [analyseprogram](tools/radio_quicklook_20261009/inspect_repeated_1422596235.py).
