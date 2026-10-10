# Beskrivende gennemgang af seks S2017-interiørfamilier

Ingen kvalificeret SETI-detektion er etableret (`qualified_claim=false`). Rapporten bevarer alle seks jobfamilier med hver deres tre lokale ON-top20-lister. De 54 faste top3-profiler giver 324 scanningmålinger og 5.184 gemte tidsrækker. Alt stammer fra samme besøg den 28. april 2017.

Native 170 og 172 blev valgt før deres egne nye spektralværdier, mens resultaterne fra native 171 allerede var kendt. Ranglister og profiler blev derimod udvalgt efter søgningen på de samme ON-data. De er ikke blind eller uafhængig bekræftelse.

De valgte 54 profilscores spænder fra 5.71424 til 26778.7. Dette er en række-MAD-standardiseret boksbanescore maksimeret over korrelerede drift/bredde-kombinationer. Den er ikke kalibreret SNR eller falskalarm-sandsynlighed. Der er ikke lavet en samlet top360-rangliste.

Udvælgelses-ON har den største faste middelværdi i 50/54 profiler og positive middelværdier i begge halvdele i 48/54. Positive rækker i udvælgelses-ON spænder fra 10 til 16 ud af 16. De øvrige ON-scanninger har positive halvdele i 41/108 målinger; OFF i 56/162.

9/54 faste spor har positive halvdele i alle tre ON-scanninger. Af disse har 7 også positive halvdele i mindst én OFF. Signer, halvtider og rangdominans er beskrivende egenskaber ved efterudvalgte spor og fungerer ikke som kandidatkrav eller veto.

ON/OFF-profiler bruger nøjagtigt den gemte frekvens, drift og bredde ved de faktiske scanningtider. Små residualer på disse præcise OFF-baner kan ikke udelukke nærliggende OFF-struktur. Der er ikke udført OFF-søgning, ny optimering, fit, frekvensforskydning eller astronomisk oprindelsesklassifikation.

| Job | ON | Lokale top20 scores, min–maks | Referencefrekvens, MHz, min–maks | Bredde 1/3 | Drift, Hz/s, min–maks |
|---|---|---:|---:|---:|---:|
| native170_batch01 | epoch1_on | 5.56259–6.95394 | 2303.808248229–2304.753469862 | 16/4 | -3.81633–3.60204 |
| native170_batch01 | epoch2_on | 5.56146–6.0994 | 2303.809980489–2304.682505876 | 15/5 | -3.77551–2.85714 |
| native170_batch01 | epoch3_on | 5.56362–6.45335 | 2303.843840584–2304.717243277 | 11/9 | -3.39796–3.90816 |
| native170_batch02 | epoch1_on | 1741.06–26634.6 | 2303.319926932–2303.320457786 | 6/14 | -3.94898–2.11224 |
| native170_batch02 | epoch2_on | 1433.93–21775.6 | 2303.320209123–2303.320714831 | 3/17 | -3.68367–0.418367 |
| native170_batch02 | epoch3_on | 1441.85–22041.5 | 2303.319940902–2303.320410289 | 5/15 | -0.44898–3.38776 |
| native170_batch03 | epoch1_on | 5.59793–6.53137 | 2301.964025572–2302.708757669 | 14/6 | -3.90816–3.63265 |
| native170_batch03 | epoch2_on | 5.58096–6.05043 | 2301.918500662–2302.768716216 | 13/7 | -3.95918–3.7551 |
| native170_batch03 | epoch3_on | 5.56054–6.23018 | 2301.867723092–2302.715435252 | 17/3 | -3.39796–3.77551 |
| native172_batch01 | epoch1_on | 5.59556–6.09486 | 2297.943223827–2298.910143413 | 16/4 | -3.87755–3.96939 |
| native172_batch01 | epoch2_on | 5.63561–6.36539 | 2298.028233089–2298.827400059 | 17/3 | -3.95918–3.89796 |
| native172_batch01 | epoch3_on | 5.55706–6.58966 | 2297.974060848–2298.892245255 | 13/7 | -3.88776–3.68367 |
| native172_batch02 | epoch1_on | 1773.31–26778.7 | 2297.460574284–2297.461035289 | 5/15 | -0.428571–3.96939 |
| native172_batch02 | epoch2_on | 1447.92–21999.4 | 2297.459884174–2297.461038083 | 5/15 | -0.377551–3.84694 |
| native172_batch02 | epoch3_on | 1458.02–22093.6 | 2297.460836917–2297.461133078 | 4/16 | -3.55102–0.408163 |
| native172_batch03 | epoch1_on | 5.61769–6.66206 | 2296.060419269–2296.898436360 | 14/6 | -3.61224–3.77551 |
| native172_batch03 | epoch2_on | 5.55977–6.56143 | 2296.088182926–2296.960345097 | 15/5 | -3.77551–3.7449 |
| native172_batch03 | epoch3_on | 5.58485–6.35632 | 2296.015911363–2296.954639815 | 16/4 | -3.68367–3.88776 |

Referencefrekvenser fra forskellige ON-scanninger gælder forskellige første integrationsmidtpunkter. JSON angiver både gentagne referencekanaler og eksakt gentagen frossen boksgeometri: samme 96 afrundede kanalcentre ved de seks scanningers tidsrækker og samme bredde. Der bruges ingen lighedstolerance eller ny tilpasning; dette er geometri og ikke en test af fysisk oprindelse.

| Job | Gentagne eksakte 96-center/breddegrupper på tværs af ON | Faste top3-spor med konstant center i alle 96 rækker |
|---|---:|---:|
| native170_batch01 | 0 | 0 |
| native170_batch02 | 1 | 3 |
| native170_batch03 | 0 | 0 |
| native172_batch01 | 0 | 0 |
| native172_batch02 | 1 | 3 |
| native172_batch03 | 0 | 0 |

q128 starter i hvert tilfælde ved den geometriske native-chunks frekvensmidte. Den tidligere native 171-linje ved 2300,390625 MHz var kendt før valget af de tilstødende chunks. De geometriske midter er adskilt med 2,9296875 MHz; det er en egenskab ved kildegitteret, ikke en klassifikation af fysisk eller instrumentel årsag.

| Native | q128 midterfrekvens, MHz | Eksisterende top20-punkter i q128, ON1/ON2/ON3 | Gemte top3-profiler i q128 | Eksakt stationære ved midterkanalen |
|---|---:|---:|---:|---:|
| 170 | 2303.320312500 | 9/9/12 | 6 | 3 |
| 172 | 2297.460937500 | 12/12/9 | 6 | 3 |

Gemte q128-profiler fra native 170, epoch1_on rang 1: reference 2303.320312500 MHz, drift -4.44089e-16 Hz/s, bredde 1. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 678.37, 517.029, 555.512, 537.177, 562.425, 545.173. Første/sidste halvdel: 678.901/677.838; 517.507/516.551; 554.613/556.411; 537.518/536.837; 563.339/561.511; 544.118/546.228.

Gemte q128-profiler fra native 170, epoch1_on rang 2: reference 2303.320301324 MHz, drift 0.0510204 Hz/s, bredde 3. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 112.978, 0.00885838, -0.00782996, 0.022719, 0.00225757, -0.020631. Første/sidste halvdel: -0.00223873/225.958; -0.010443/0.0281598; 0.00184901/-0.0175089; 0.053726/-0.00828794; -0.00331852/0.00783365; 0.0142723/-0.0555344.

Gemte q128-profiler fra native 170, epoch2_on rang 1: reference 2303.320312500 MHz, drift -4.44089e-16 Hz/s, bredde 1. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 678.37, 517.029, 555.512, 537.177, 562.425, 545.173. Første/sidste halvdel: 678.901/677.838; 517.507/516.551; 554.613/556.411; 537.518/536.837; 563.339/561.511; 544.118/546.228.

Gemte q128-profiler fra native 170, epoch2_on rang 3: reference 2303.320301324 MHz, drift 0.0510204 Hz/s, bredde 3. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 0.0102728, 0.0127103, 92.7281, 0.0165228, 0.0111928, 0.0325387. Første/sidste halvdel: 0.00868915/0.0118564; -0.0105042/0.0359248; -0.00544608/185.462; 0.0140383/0.0190073; -0.00341902/0.0258047; 0.046709/0.0183683.

Gemte q128-profiler fra native 170, epoch3_on rang 1: reference 2303.320312500 MHz, drift -4.44089e-16 Hz/s, bredde 1. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 678.37, 517.029, 555.512, 537.177, 562.425, 545.173. Første/sidste halvdel: 678.901/677.838; 517.507/516.551; 554.613/556.411; 537.518/536.837; 563.339/561.511; 544.118/546.228.

Gemte q128-profiler fra native 170, epoch3_on rang 2: reference 2303.320301324 MHz, drift 0.0510204 Hz/s, bredde 3. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: -0.00121804, 0.0248035, -0.0133061, -0.0134896, 93.5787, -0.00180556. Første/sidste halvdel: -0.0211013/0.0186652; 0.0249645/0.0246426; -0.007983/-0.0186293; 0.0103817/-0.037361; -0.0015187/187.159; -0.000849839/-0.00276128.

Gemte q128-profiler fra native 172, epoch1_on rang 1: reference 2297.460937500 MHz, drift -4.44089e-16 Hz/s, bredde 1. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 689.617, 526.695, 566.573, 549.216, 570.319, 554.653. Første/sidste halvdel: 689.118/690.115; 524.892/528.498; 565.143/568.003; 548.132/550.3; 569.119/571.519; 554.473/554.832.

Gemte q128-profiler fra native 172, epoch1_on rang 3: reference 2297.460926324 MHz, drift 0.0510204 Hz/s, bredde 3. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 115.013, -0.00267304, 0.0202109, -0.00669607, -0.0212746, 0.0264991. Første/sidste halvdel: -0.0277313/230.053; 0.0149058/-0.0202518; 0.0278135/0.0126084; -0.0148636/0.00147142; -0.0207017/-0.0218474; 0.0386895/0.0143088.

Gemte q128-profiler fra native 172, epoch2_on rang 1: reference 2297.460937500 MHz, drift -4.44089e-16 Hz/s, bredde 1. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 689.617, 526.695, 566.573, 549.216, 570.319, 554.653. Første/sidste halvdel: 689.118/690.115; 524.892/528.498; 565.143/568.003; 548.132/550.3; 569.119/571.519; 554.473/554.832.

Gemte q128-profiler fra native 172, epoch2_on rang 2: reference 2297.460926324 MHz, drift 0.0510204 Hz/s, bredde 3. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: -0.00574813, 0.0124704, 94.6553, 0.00511044, 0.0165963, 0.00467352. Første/sidste halvdel: -0.0160444/0.00454813; -0.00123343/0.0261743; -0.0161439/189.327; 0.01231/-0.00208908; 0.0237931/0.00939946; 0.0152837/-0.00593665.

Gemte q128-profiler fra native 172, epoch3_on rang 1: reference 2297.460937500 MHz, drift -4.44089e-16 Hz/s, bredde 1. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: 689.617, 526.695, 566.573, 549.216, 570.319, 554.653. Første/sidste halvdel: 689.118/690.115; 524.892/528.498; 565.143/568.003; 548.132/550.3; 569.119/571.519; 554.473/554.832.

Gemte q128-profiler fra native 172, epoch3_on rang 3: reference 2297.460926324 MHz, drift 0.0510204 Hz/s, bredde 3. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: -0.00817352, 0.0154282, 0.0207805, -0.000833229, 95.2601, 0.0235319. Første/sidste halvdel: -0.00393913/-0.0124079; 0.0134363/0.0174202; 0.0406025/0.000958515; -0.0125121/0.0108457; 0.0098239/190.51; 0.0220123/0.0250514.

q128-beskrivelsen læser kun eksisterende lokale top20-punkter og gemte top3-profiler. Manglende valg er ikke bevis for stille q128-data. Der er ingen nye patches, justeringer eller fits, og eventuelt fælles ON/OFF-struktur er ikke uafhængig replikation eller en kildeklassifikation.

De 54 profiler er udvælgelsesinstanser, ikke nødvendigvis 54 forskellige kildekanaler eller uafhængige fysiske spor. Geometriske dubletter beholdes synligt i materialet.

Hver ny native-chunk dækker q1–254 én gang: 1.040.384 referencekanaler pr. ON, svarende til 99,21875% af 1.048.576-kanals chunken. De seks job giver 1.524 ON-kort, 6.242.304 carrier/origin-maksima og 9.800.417.280 korrelerede drift/bredde-kombinationer; tallene er ikke uafhængige forsøg. De nye 192 eksakte kilderanges gav 597.792.529 BODY-bytes. Boundary-profilerne og den tidligere native 171-familie behandles separat.

Profilresidualer bruger hele den native float32-rækkes median før float64-promovering og en fast flankemedian uden for ±3 kanaler inden for ±64. Detektorscores bruger den enkelte 4.096-kanals kerne og række-MAD. De to størrelser har forskellige normaliseringer og er ikke fluxmål. Driftgitteret er −4 til +4 Hz/s i 785 trin, bredder 1 og 3 kanaler (2,793968 og 8,381903 Hz).

FROZEN_TRACK_SCAN_CONTEXT.png viser alle 324 middelværdier med hver sin fulde skala pr. job; rammer markerer den ON-scanning, der udvalgte sporet. LOCAL_TOP20_REFERENCE_TRACKS.png viser de eksisterende lokale top20-punkter. CSV og JSON bevarer alle identiteter, signerede residualer, positive rækkeantal, halvmidler, tidsrækker og faktisk læste input-byte-pins.

Provenance: faktisk interiør-QA `03bea3023fb1a08528a1a8acc0f2bbe40c3944e3a9f48a6e92803810c7b14bdc`; kilde-QA `21a8edaf91e9a60d3209d33e4620a5f93038aabfafd3910094bd25e0fd66318a`; acquisition `2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e`. Søgefreeze `2ba6ee3497abf3d24e5190df8630133f8a04bcb0`; QA-freeze `3eabb0e7582fc4a8c0bbb7975561128e008a7019`. Den empiriske QA kontrollerede 668.736 patch-celler bitvist. Denne rapport læser kun de QA-autentificerede JSON-resultater og åbner ingen H5/NPZ eller teleskopkilder.

Der foreligger ingen blind bekræftelse, kalibreret falskalarmrate eller generel nulkonklusion. S2017-frekvenserne er ikke samme-frekvens-replikation af 2016 L-band. Tidligere fejltilstande og beskyttede 2016-holdouts er bevaret.
