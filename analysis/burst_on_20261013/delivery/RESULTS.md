# SETI: 73-sekunders søgning i målstjernens ON-scanninger

13. oktober 2026. HIP98505 / HD189733; samme historiske besøg 28. april 2017.

288 nye kombinerede kort, 1.179.648 carrier-vindere og 54 faste kontekstprofiler er færdige. Syv fire-række-vinduer per kerne, 159 drifter og bredder 1/3 giver 2.625.896.448 korrelerede skabelonforekomster, ikke uafhængige statistiske forsøg.

De ni egne udvalgte scorer ligger fra 6.242 til 6.916. Samme frosne baner i andre ON-scanninger ligger fra -1.583 til 1.648, og i OFF fra -2.922 til 1.590. Ingen fast-banegenfinding er etableret i de andre ON-scanninger.

Hver ON-scanning blev rangeret separat. De tre ON-scanninger peger mod samme stjerne i ét besøg. Egne scorer var allerede optimeret over frekvens, drift, bredde og vindue. Ingen kalibreret SNR, falskalarmrate eller kvalificeret SETI-detektion er etableret.

Referencekernerne q=4+8k i tre native-bånd dækker 1,0986328125 MHz per scanning, 12,5 procent af tripletens referencekanaler. De er på forhånd geometrisk langt fra de tre DC-bins; DC-kontrollen ændrer derfor ingen rangliste. Nyheden er den korte tidsfamilie i ON-scanningerne, ikke DC-fravalget, ny frekvensdækning eller observation.

## Alternative hypoteser ved DC

Den allerede klargjorte fase er også afsluttet: alle 7.083 tidligere DC-ramte carrier-vindere blev undersøgt over deres oprindelige 785 drifter, bredder 1/3 og 16 rækker. 7.074 fik en tilladt alternativ hypotese; ni havde ingen. Alle 11.120.310 lokale hypoteser er beregnet og uafhængigt kontrolleret. Den samlede TOP9 er uændret. Ingen nye kontekstprofiler er nødvendige for disse uændrede geometrier.

## Kontrol og fortolkning

Primær-QA undersøger alle 288 kort og 1.170 raw503-scoreforespørgsler, og genberegner fulde median501-normaliseringer i de valgte kerner. Kontekst-QA genberegner normaliseringer og alle 54 profiler fra gemte raw12096-crops; den fulde kilde-QA åbner også de originale HDF5-kompakter. Den efterprøver profilerne; den gentager ikke hele søgegitterets maksimum. DC-QA genmaksimerer alle lokale alternative hypoteser uafhængigt. De eksakte kvitteringer er knyttet i SUMMARY.json.

Faste svage andre-scanning-scorer beviser ikke fravær eller stjerneeksklusivitet: det grove driftgrid kan forskyde en faktisk mellem-grid-bane mange kanaler efter lange pauser. Samme fire-række-position benyttes i hver kontekst; et udbrud kan forekomme på et andet tidspunkt. Full16-profiler og bidrag er bevaret. Scorer er efter udvælgelse og observationerne er allerede eksponeret.

0 DKK; nul nye teleskoprequests. Original A/B: FAIL_CLOSED. Beskyttede 2016-kontroller er lukkede; den lukkede 2019-rute er uændret. Formelt checkpoint: 20. oktober 2026.
