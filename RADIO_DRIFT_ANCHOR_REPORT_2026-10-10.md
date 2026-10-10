# Fast stationær reference for driftfamilien — 10. oktober 2026

Den samme smalle frekvensstruktur er tydelig i alle tre ON-scanninger og alle tre OFF-kontroller, når de undersøges på samme faste fysiske kanaler. Ved bredde 1 er det nye middeloverskud 1,561473 i ON2 og 1,553348 i den tilstødende OFF1; forskellen er kun 0,008125. OFF1 overstiger ON1, og OFF3 overstiger ON3. Små tidligere værdier langs et ekstrapoleret driftspor kan derfor ikke læses som fravær af strukturen i OFF.

Dette er en beskrivende diagnose af ni allerede offentliggjorte ON-valgte rang 1–3-spor omkring 1426,282 MHz. De ni er afhængige varianter af samme frekvensområde og genbruger de samme råceller. Diagnosen fastslår ingen astronomisk, teknologisk, jordbaseret eller instrumentel oprindelse og kvalificerer ikke et SETI-fund.

## Hvad der blev fastlåst og beregnet

Ankeret er den tidligere publicerede ON2 drift rang 01: native kanal 158766416, præcis nul drift, svarende til 1426,2821284465203 MHz. Ankeret og denne nye beregningsafgrænsning blev fastlagt efter eksponering af de gamle værdier og rangeringer, men før den nye diagnose blev kørt. Det er ikke blind eller uafhængig validering.

De ni gemte råudsnit leverede hver en kopi af samme fysiske vindue, kanal 158766406–158766426, for alle seks scanninger og alle 16 tidsrækker. Alle ni kopier af de 2.016 float32-råceller og deres normaliserede float64-værdier var byte-identiske. Normalisering med de gemte fuld-bånds rækkemedianer reproducerede de kopierede normaliserede værdier præcist. Alle originale filhashes var uændrede bagefter. Ingen HDF5-fil eller ny teleskopkilde blev læst.

For hver række er den nye baggrund medianen af de 14 fysiske kanaler med offset ±4..±10 fra ankeret. Den faste reference er middelværdien af de centrerede bredder 1, 3, 5 eller 9 minus denne baggrund. Originalsporets gemte middel over dets oprindelige bredde 1 eller 3 blev kopieret og fik trukket præcis samme nye fysiske baggrund fra. Der blev ikke søgt, omrangeret eller tilpasset frekvens, drift eller bredde.

Alle tal nedenfor er additive forskelle i rækkenormaliseret effekt. De er ikke SNR, flux eller kalibreret følsomhed. Alle fuldpræcisionstal og 16 rækkers forløb findes i resultat-JSON og NPZ.

## Fast reference i alle seks scanninger

Tabellen viser middel, median og det mindste af de to fastlagte halvmidler, rækker 0–7 og 8–15. Begge bredder har 16/16 strengt positive residualer i hver scanning.

| Scan | Bredde 1 middel | Bredde 1 median | Bredde 1 min. halvdel | Bredde 3 middel | Bredde 3 median | Bredde 3 min. halvdel |
|---|---:|---:|---:|---:|---:|---:|
| ON1 | 1,329333 | 1,380529 | 1,288516 | 0,832037 | 0,825998 | 0,805141 |
| OFF1 | 1,553348 | 1,630806 | 1,491886 | 0,836950 | 0,840510 | 0,801807 |
| ON2 | 1,561473 | 1,541188 | 1,546491 | 0,891072 | 0,886956 | 0,887357 |
| OFF2 | 1,367921 | 1,423488 | 1,300863 | 0,862467 | 0,860827 | 0,839477 |
| ON3 | 0,990075 | 0,849639 | 0,844916 | 0,867187 | 0,827036 | 0,857544 |
| OFF3 | 1,136054 | 1,046060 | 1,064207 | 0,859101 | 0,858916 | 0,839892 |

Ved bredde 3 spænder alle seks middelværdier kun fra 0,832037 til 0,891072. OFF1 er 0,836950 mod ON1 0,832037; OFF2 er 0,862467 mod ON2 0,891072; OFF3 er 0,859101 mod ON3 0,867187. Kontrollerne indeholder dermed en stærk struktur på samme faste kanaler. ON og OFF kommer fra forskellige pegeretninger og tider; sammenligningen giver ikke en udskiftelig nulfordeling eller en forklaring på oprindelsen.

Bredde 5 og 9 var også fastlagt og er bevaret i resultaterne. Deres seks middelværdier ligger henholdsvis mellem 0,506082–0,581185 og 0,288355–0,325009; der vælges ingen vinderbredde. Bredde 9 inkluderer offset ±4, som også indgår i baggrundsflanken, så center og baggrund er afhængige. De fire bredder er i øvrigt overlappende beskrivelser af samme celler.

## Stationær minus oprindelig drift, med fælles baggrund

Fortegnet er Δ = fast stationær reference minus det kopierede oprindelige driftspor, ved det pågældende spors oprindelige bredde. Tabellen opsummerer de 54 gemte scan-middelforskelle; antal er case×scan-forekomster, ikke uafhængige signaler eller forsøg.

| Udvalg | Antal | Δ>0 / Δ=0 / Δ<0 | Middel Δ | Median Δ | Mindste Δ | Største Δ |
|---|---:|---:|---:|---:|---:|---:|
| Alle | 54 | 45 / 6 / 3 | 0,598851 | 0,834133 | -0,031808 | 0,904241 |
| ON | 27 | 22 / 3 / 2 | 0,543408 | 0,818371 | -0,031808 | 0,904241 |
| OFF | 27 | 23 / 3 / 1 | 0,654293 | 0,840986 | -0,015628 | 0,874247 |
| OFF, oprindelig drift ≠0 | 21 | 21 / 0 / 0 | 0,829689 | 0,848185 | 0,511981 | 0,874247 |

For alle 21 OFF-sammenligninger fra de syv oprindelige spor med ikke-nul drift er den faste reference større: Δ=0,511981–0,874247. Det viser, at de oprindelige forudsigelser kan bevæge sig væk fra den fælles struktur ved OFF-tiderne. Det er en konkret geometrisk begrænsning ved at bruge en lille OFF-værdi langs netop det ekstrapolerede spor som fraværstest. De 21 forekomster genbruger tre kontroller og overlappende celler; fortegnene giver ingen falsk-alarm-sandsynlighed.

ON2 rang 01 har præcis Δ=0 i alle 16 rækker i alle seks scanninger, fordi dens nul-drift-kanal og bredde 1 er identiske med ankeret. Det er en identitetskontrol, ikke ny evidens. ON3 rang 01 har også nul drift, men centerkanal 158766417 og bredde 3. Dets vindue er forskudt én kanal; dér er Δ=−0,031808 i ON3 og −0,015628 i OFF3. Ankeret blev ikke flyttet for at maksimere værdierne.

Alle 54 middelforskelle er vist her, afrundet til seks decimaler. Rækkerne identificeres ved den oprindelige ON-rang og bredde:

| Oprindelig case | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |
|---|---:|---:|---:|---:|---:|---:|
| ON1 r1 (w3) | -0,002561 | 0,511981 | 0,849399 | 0,840462 | 0,864988 | 0,840986 |
| ON1 r2 (w3) | 0,378500 | 0,782167 | 0,878735 | 0,846327 | 0,904241 | 0,859737 |
| ON1 r3 (w3) | 0,398362 | 0,836301 | 0,864226 | 0,862044 | 0,862594 | 0,862150 |
| ON2 r1 (w1) | 0,000000 | 0,000000 | 0,000000 | 0,000000 | 0,000000 | 0,000000 |
| ON2 r2 (w3) | 0,842254 | 0,814306 | 0,430404 | 0,874247 | 0,858444 | 0,873100 |
| ON2 r3 (w3) | 0,821088 | 0,846406 | 0,462997 | 0,831966 | 0,872897 | 0,860753 |
| ON3 r1 (w3) | 0,086383 | 0,168092 | 0,156133 | 0,089984 | -0,031808 | -0,015628 |
| ON3 r2 (w3) | 0,823217 | 0,853599 | 0,880463 | 0,848185 | 0,319619 | 0,848558 |
| ON3 r3 (w3) | 0,818371 | 0,816746 | 0,868277 | 0,858142 | 0,464807 | 0,855299 |

## Baggrund, figurer og fortolkning

De gamle profilmidler brugte en median over track-aligned offset med |offset|>3 i et 129-kanalvindue, ±64. Den nye baggrund bruger 14 faste fysiske kanaler. De gamle middelværdier er bevaret separat og blev ikke genmålt. Eksempelvis var ON2 rang 01 tidligere 1,578749 i ON2 og 1,558537 i OFF1; på den nye fælles baggrund er tallene 1,561473 og 1,553348. En ændret baggrund skal derfor holdes adskilt fra forskellen mellem faste og bevægelige centergeometrier. I Δ-rækkerne bortfalder den fælles baggrund algebraisk.

Alle tre originale figurer er kontrolleret visuelt i fuld opløsning: titler, mærkater og farveskalaer er læsbare. Vandfaldet har samme fysiske frekvensakse og farveskala i alle seks paneler; tidsfiguren deler y-område og viser alle 16 rækker. Farver begrænses til de fastlåste visningsintervaller −0,5..3,0 og −2,5..2,5 med markerede farveskalaender; de gemte tal begrænses ikke.

- [Fælles fysiske 21-kanal-vandfald](results/radio_drift_anchor_20261010/measurement/COMMON_PHYSICAL_WATERFALL.png)
- [Faste bredder 1 og 3, alle tidsrækker](results/radio_drift_anchor_20261010/measurement/FIXED_REFERENCE_TIME.png)
- [Stationært og oprindeligt driftmiddel på samme baggrund](results/radio_drift_anchor_20261010/measurement/SAME_BACKGROUND_MEAN_DIFFERENCE.png)

Alle seks scanninger tilhører én historisk observation af HIP98505/HD189733 den 17. marts 2016, cadence 85030. Ni rangvalgte spor, flere bredder og de gentagne kontroller tilfører ingen uafhængige observationer. Den tidligere A/B-kvalifikation er fortsat FAIL_CLOSED. En ny, uafhængig observation med overlappende frekvensdækning og samtidige kontroloplysninger er den primære vej til stærkere evidens; denne diagnose erstatter den ikke.

## Reproduktion og gennemførelse

Den offentlige fastlåsning af kode og afgrænsning var Git-commit `ada64c4d46ead59b92f8e65ae2ce6aa4d13d0759` og blev læst tilbage med eksakt hashmatch før den eneste autoriserede numeriske kørsel.

- [drift_anchor.py](tools/radio_drift_anchor_20261010/drift_anchor.py): SHA256 `930a89ee67b4a417917e1874629a595a644f0727077af02bfb370f7f18f0dbb5`.
- [analysis_scope.json](tools/radio_drift_anchor_20261010/analysis_scope.json): SHA256 `f037f6b838ae964047584595b5ce79c5a3b7df4f2316c381c266c1c0d154ae0c`; indeholder alle 14 inputfilers størrelse/hash, ni oprindelige spor og de faste definitioner.
- Runtime: numpy 2.3.5 og matplotlib 3.10.8; ingen HDF5-afhængighed i denne diagnose.
- Beregning COMPLETE_DESCRIPTIVE_ONLY: CPU 1,61992847 s, vægtid 1,624173316 s, maksimal RSS 129.560.576 bytes; grænser 40 CPU-s, 1.800 s og 4 GiB. Nye kildedata: 0 bytes.
- [Original resultat-JSON](results/radio_drift_anchor_20261010/measurement/DRIFT_ANCHOR_RESULT.json) og [eksekveringskvittering](results/radio_drift_anchor_20261010/measurement/EXECUTION_RECEIPT.json). Den fælles rå-/normaliserings-/sammenlignings-NPZ leveres byte-exakt i `SETI_SIGNAL_FOLLOWUP_2026-10-10.zip` med samme mappeplacering; NPZ-filer er ikke lagt direkte på GitHub.
- [Beskrivende oversigt fra gemt JSON](results/radio_drift_anchor_20261010/measurement/DESCRIPTIVE_SUMMARY.json) og [rapporteringsscript](tools/radio_drift_anchor_20261010/summarize_saved_json.py). Oversigten læser gemte JSON-tal og udfører ingen profilberegning, ny søgning eller NPZ-genmåling.
