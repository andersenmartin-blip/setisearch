# HIP98505: tidsopløst kontrol af sporet ved 1423,954061 MHz

Den stærkeste endnu ikke særskilt gennemgåede gentagne ON-gruppe efter det på forhånd valgte, beskrivende forhold mellem gemt ON-score og største gemte OFF-projektion blev undersøgt i de allerede hentede autentiske data. Gruppen gentages i alle tre ON-scanninger nær **1423,954061 MHz**. Den ligger **499,049 Hz under** den stærke stationære kontrollinje ved 1423,954560 MHz.

Den snævre kontrol læste 260 kanaler × 16 tidsrækker i hver af de seks scanninger fra den lokale HDF5-cache. Normaliseringen genbruger de tidligere gemte hel-chunk-rækkemedianer. Der blev ikke hentet nye data, beregnet nye detektorscorer eller afprøvet nye drifts-/breddekombinationer.

| Scanning | Rolle | Median af de 16 lokale rækkemaksima over rækkemedianen | Kollapset medianmaksimum (MHz) |
| --- | --- | ---: | ---: |
| ON1 | ON | 0,854713 | 1423,954064 |
| OFF1 | OFF | 0,985343 | 1423,954067 |
| ON2 | ON | 0,953089 | 1423,954058 |
| OFF2 | OFF | 0,894963 | 1423,954061 |
| ON3 | ON | 0,834990 | 1423,954058 |
| OFF3 | OFF | 0,901024 | 1423,954061 |

Sporet er tidsmæssigt synligt i både ON og OFF gennem samme historiske besøg. OFF er ikke svagere på en ensartet måde: OFF1 og OFF3 har højere median-rækkemaksimum end deres parrede ON-scanninger, mens OFF2 er lidt lavere end ON2. Dette er stærk konkret mod-evidens mod **ON-eksklusivitet**. Dispositionen er derfor `NO_ON_EXCLUSIVITY_STRONG_OFF_COUNTEREVIDENCE_ORIGIN_UNRESOLVED`.

Resultatet identificerer ikke signalets fysiske oprindelse. OFF-respons beviser ikke interferens, og den dataudvalgte inspektion er ikke en kalibreret signifikanstest, SNR eller falskalarmrate. Alle seks scanninger er fra én observation den 17. marts 2016, ikke uafhængige genbesøg. Den oprindelige A/B-kvalifikation forbliver **FAIL_CLOSED**.

Kørslen læste 24.960 cachede power-værdier på applikationsniveau og brugte 1,341838 CPU-s, 1,346886 s wall og 156.835.840 bytes peak RSS. Den konservative 30-CPU-s-reservation refunderes ikke. Saldoen er nu **2.182,705145 CPU-s**, heraf **2.000 beskyttet til det afsluttende checkpoint 20. oktober**. Pris: 0 DKK.

Evidens: [resultatkvittering](results/radio_quicklook_20261009/repeated_1423954061/RESULT.json), [alle tidsrækkers lokale maksimummer](results/radio_quicklook_20261009/repeated_1423954061/ROW_PROFILES.csv), [seks-panels tids-/frekvensfigur](results/radio_quicklook_20261009/repeated_1423954061/repeated_1423954061.png), [frosset omfang](tools/radio_quicklook_20261009/repeated_1423954061_scope.json) og [analyseprogram](tools/radio_quicklook_20261009/inspect_repeated_1423954061.py).
