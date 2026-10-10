# SETI-resultater — 10. oktober 2026

**De to nye 2016-grænsesøgninger og hele den fastfrosne S2017-fortsættelse er afsluttet, og de faktiske output-/kildekontroller er PASS.** S2017 dækker 254 af 256 referencekerner i ét erhvervet native171-udsnit: **99,21875 % af 2,9296875 MHz**, ikke hele teleskopets S-bånd. De stærkeste nye q127-bokse deler støtte med den allerede kendte stationære struktur i både ON og OFF. Der foreligger ingen kvalificeret SETI-detektion, fysisk oprindelsesafgørelse, kalibreret falsk-alarm-sandsynlighed eller generel nuldetektionsgrænse. A/B-status er uændret `FAIL_CLOSED`.

Målet er HIP98505 / HD189733. De bevarede 2016-data er fra besøget den 17. marts 2016; S2017 er det særskilte besøg den 28. april 2017 (`AGBT17A_999_55`), native-udsnit 171 af 343 i kildefilen. Ingen ny observation er gennemført.

## Faktisk afsluttet dækning

| Arbejde | Referencekanaler pr. ON | Kort / ON-kanal-maksima | Korrelerede drift-bredde-kombinationer | Faste profiler / scan-profiler | Bitpræcise rå profilcelle-forekomster |
|---|---:|---:|---:|---:|---:|
| 2016: grænserne 154/155 og 157/158 | 16.384 | 12 / 49.152 | 75.005.952 | 18 / 108 | 222.912 |
| S2017: første kerne q128 | 4.096 | 3 / 12.288 | 19.292.160 | 9 / 54 | 111.456 |
| S2017: 253 nye kerner | 1.036.288 | 759 / 3.108.864 | 4.880.916.480 | 27 / 162 | 334.368 |
| S2017 samlet | 1.040.384 | 762 / 3.121.152 | 4.900.208.640 | 36 / 216 | 445.824 |

2016 og S2017 tilsammen giver 774 kort, 3.170.304 ON-kanal-maksima, 4.975.214.592 korrelerede kombinationer, 54 faste profiler, 324 scan-profiler, 5.184 integration-række-forekomster og 668.736 bitkontrollerede rå profilcelle-forekomster. Forekomster er ikke unikke kildeceller; udvalgte patches kan overlappe. Hypoteserne er heller ikke uafhængige statistiske tests.

Grænsesøgningerne tilføjer 46.456,888 Hz referencebåndbredde pr. ON i allerede erhvervede 2016-data. Kontrollen omfattede 24 kompakte kildefiler og 384 afkodede rækkehashes. De 18 valgte top-3-scores ligger i 5,071838–5,841220; de 120 top-20-scores i 4,753874–5,841220. To valgte spor har positive gemte halvdelmiddelværdier i alle tre ON-scans; OFF1 er også positiv i begge halvdele for det ene eksempel. Dette er beskrivelse efter ON-udvælgelse, ikke uafhængig bekræftelse.

S2017s samlede referencebåndbredde er 2.906.799,31640625 Hz pr. ON. q1–q254 er afsluttet; q0 og q255 er usøgte. q128 blev ikke genkørt under udvidelsen. Dækningen tæller referencekanaler; drift-/preprocesseringshaloer eller adgang til hele kildeudsnittet udvider ikke nævneren. Der er ikke bestemt følsomhed, fluxgrænse eller kalibreret nuldetektionsgrænse.

S2017 har 240 gemte top-20-rækker fra fire separate familier: q128 og tre administrative batches, hver med tre ON-ranglister. Det er ikke en ny samlet global top-240-rangordning eller 240 uafhængige signaler.

## Hvad det første S2017-felt viser

Den højeste rang i alle tre ON-scans ligger ved samme fysiske kanal, 179.830.784, svarende til **2300,390625 MHz**. Det valgte grid har drift −4,44×10⁻¹⁶ Hz/s; de gemte kanalcentre er konstante. Den smalle struktur findes i samtlige ON- og OFF-scans.

| Scan | Gemt middel for det faste stationære spor |
|---|---:|
| ON1 | 691,125 |
| OFF1 | 528,464 |
| ON2 | 568,476 |
| OFF2 | 550,248 |
| ON3 | 573,675 |
| OFF3 | 556,762 |

Enheden er bredde-middel af rå power divideret med rækkens median over hele native-udsnittet, minus den faste flankemedian. Tallene er hverken flux eller kalibreret SNR. Alle 16 rækker er positive i hver af de seks scans.

De valgte rank-2-spor starter fire kanaler fra denne struktur og har drift +0,051020408 Hz/s og bredde 3. Deres faste bokse krydser den stationære kanal i række 8–15 af den oprindelige ON-scan. Rank-3 starter otte kanaler væk og krydser den samme kanal senere. Eksempelvis har ON1/rank2 middel 0,01237 i første halvdel og 230,07581 i anden halvdel. Denne gemte geometri viser, hvorfor en stor score på et bevægende spor og små tal langs det præcise OFF-spor ikke dokumenterer en særskilt, målrettet signalkilde. Der foretages ingen afgørelse om strukturens fysiske oprindelse.

Alle 60 top-20-referencekanaler fra q128 ligger inden for 261 kanaler, ca. 729,23 Hz, af den fælles struktur. Antallet af valgte ranks er ikke antallet af uafhængige fysiske signaler.

2017-materialet er et **andet historisk besøg i et andet frekvensbånd**. Det reproducerer ikke de tidligere 2016 L-båndsspor ved samme frekvens. ON1/2/3 er tre scan-positioner inden for hvert besøg, ikke tre uafhængige besøg.

## Nærliggende OFF-kontekst

En separat beskrivende analyse af 90 tidligere gemte profiler omfattede 540 scan-profiler. I et eksempel ved 1406,250011 MHz var eksakt OFF-spormiddel 0,081 og 0,305, mens middel af nærliggende, frit valgte række-peaks var ca. 40.153 og 40.663. Sådanne lokale maksima er udvælgelsesbiasede og udgør ingen statistisk veto-test. Analysen viser behovet for lokal OFF-kontekst; den er ikke en måling af de 18 nye grænseprofiler og klassificerer ingen kilde.

## Bevaret fejl- og erhvervelsesevidens

| Hændelse | Bevaret udfald og afgrænsning |
|---|---|
| Tidligere workspace-tab | Årsagen er ukendt. Historiske COMPLETE/QA-receipts for 153/154 eksisterer, men de fulde outputbytes var ikke tilgængelige. Det historiske job er ikke rekonstrueret som en ny afslutning. |
| Oprindeligt 154/155-forsøg | `FileExistsError` på en eksisterende `NUMERIC_ACTIVE.lock`; nul kort og nul profiler. Fejlkvitteringen er uændret. |
| Første 157/158-fortsættelse | Samme eksistenslåsfejl før datalæsning; nul kort og profiler. Et separat fastfrosset kontrolspor bruger kernel-`flock`. Kun den hidtil ustartede numeriske søgning blev derefter gennemført. |
| Oprindelig S2017-indlæsning | `H5Dwrite_chunk` fejlede lokalt efter 27 succesfulde HTTP-ranges: 83.845.205 modtagne BODY-bytes, 26 afkodede rækker, ingen komplet kompakt fil og ingen videnskabelig søgning. Årsagen fastslås ikke. |
| Rettet S2017-indlæsning | Alle 27 modtagne blokke blev bevaret, heraf én som en uindekseret, byteidentisk suffix. Kun 69 tidligere uafprøvede ranges blev hentet: 214.393.415 nye BODY-bytes. I alt 96 GETs og 298.238.620 teleskop-BODY-bytes; **nul gentagne GETs**. Råblokke blev sikret før HDF5-skrivning; alle seks skrivere lukkede før afkodning. |

Mellemudgaven af den rettede indlæsningskode blev erstattet før de 69 resterende indlæsnings-GETs; dens fastfrysning er forberedelsesevidens, ikke en ekstra numerisk kørsel. De eksisterende A/B-kvalifikationsfejl og beskyttede historiske holdouts er uændrede. Lokal kode-, profil- eller kildekontrol er ikke en bestået videnskabelig A/B-kvalifikation.

## Målte afsluttede proceskomponenter

| Komponent | CPU s | Wall s | Peak RSS bytes |
|---|---:|---:|---:|
| 154/155-søgning | 16,071806 | 16,031517 | 1.012.543.488 |
| 157/158-søgning | 15,139869 | 15,096126 | 1.011.879.936 |
| Fælles grænse-output/kildekontrol | 3,955581 | 3,910220 | 147.173.376 |
| Tidligere profilernes OFF-kontekst | 0,773870 | 0,776661 | 36.847.616 |
| Fejlet oprindelig S2017-indlæsning | 1,092329 | 36,525256 | 278.654.976 |
| Rettet S2017-indlæsning | 4,106500 | 91,448859 | 87.240.704 |
| S2017 q128-søgning | 8,057193 | 8,004157 | 542.978.048 |
| S2017 q128-output/kildekontrol | 3,082873 | 3,037644 | 218.918.912 |

Dette er de enkelte gemte procesmålinger; setup, API, rapportering og pakning er ikke samlet ende-til-ende CPU-målt. Færdige søgninger og kontroller angiver `cost_DKK=0`. Erhvervelse og afkodningskontrol beviser ikke de komplette oprindelige teleskopfilers katalog-MD5; de hele ca. 17-GB-kildefiler er ikke downloadet eller fuldt checksum-verificeret.

## Afsluttet S2017-udvidelse

Alle tre fastfrosne batches er COMPLETE, og den samlede uafhængige output/kildekontrol er PASS. Udvidelsen tilføjer 253 hidtil usøgte referencekerner, 759 ON-kort, 3.108.864 ON-kanal-maksima og 4.880.916.480 korrelerede drift-bredde-kombinationer. Der blev gemt 27 faste top-3-profiler, 162 scan-profiler og 2.592 integration-række-forekomster; alle 334.368 rå profilcelle-forekomster bestod bitpræcis kildekontrol. 12.144 ON-kernerækkemidianer blev kontrolleret. Ingen nye teleskop-GETs eller BODY-bytes blev brugt; udvidelsens angivne kost er 0 DKK.

Sammen med den tidligere afsluttede q128 er 254 af 256 referencekerner dækket: 1.040.384 referencekanaler pr. ON, 99,21875 % af det erhvervede native171-udsnit, nominelt 2.906.799,31640625 Hz pr. ON. Den nye udvidelse alene dækker 98,828125 %. Randkernerne q0 og q255 er fortsat usøgte. Det er referencekanaldækning; drift/preprocesseringshaloer og adgang til hele kildeudsnittet udvider ikke dette tal. Der er ikke bestemt en kalibreret detektionsfølsomhed, fluxgrænse eller generel nuldetektionsgrænse. Samlede q128+udvidelsesantal er 762 kort, 3.121.152 maksima, 4.900.208.640 korrelerede kombinationer og 36 faste profiler/216 scan-profiler.

## Fortolkning af de valgte spor

Batch02s 60 top-20-rækker ligger alle i q127, på referencekanaler 179.830.500–179.830.783, lige ved den tidligere fundne fælles kanal 179.830.784 (2300,390625 MHz). Alle 60 frosne bokse indeholder denne fælles kanal i mindst én integration af deres oprindelige ON-scan; det gælder også samtlige ni faste top-3-profiler. At q128 ikke er genkørt, forhindrer ikke en q127-referenceboks i at nå q128-kanalen gennem bredde/drift. Dette er samme kendte strukturs geometriske påvirkning, ikke 60 uafhængige signaler eller en ny bekræftelse.

De tre rank-1-spor starter én kanal fra den fælles linje og har små negative valgte driftsværdier. Deres bokse indeholder linjen i alle 16 oprindelige ON-rækker. Eksakte frosne OFF-profiler er markant positive: ON1-sporets OFF1-middel er 176,144631; ON2-sporets OFF1/2 er 43,946983 og 183,418388; ON3-sporets OFF3 er 11,514521, hvor boksen kun omfatter linjen i første OFF3-række. Små værdier i senere scans følger, at det frosne driftspor flytter væk fra den stationære linje. Den tidligere q128-måling viser linjen i alle seks scans. Små eksakte OFF-spormidler er derfor ikke et bevis på lokal OFF-fravær eller en kvalificeret OFF-veto.

Batch02s rank-2/3-bokse krydser linjen senere i oprindelig ON. Eksempelvis er ON1/rank2s gemte halvdelmidler 0,000520 og 201,175882; rank3s er −0,017017 og 115,066233. Disse store slut-halvdelbidrag kræver ikke en særskilt bevægende emission. Den fysiske oprindelse af den fælles stationære struktur fastslås ikke her.

Batch01s top-20-scores ligger i 5,591634–6,356479, batch03s i 5,556727–6,201318; batch02s ligger i 1.418,778509–15.458,566496. Alle er maksimale robuste rangstatistikker efter en stor, korreleret søgning, ikke kalibreret SNR eller falsk-alarm-sandsynligheder. Batch01/03s 18 valgte profiler har oprindelige ON-midler 0,058809–0,166323 og positive gemte midler i begge halvdele. Deres andre ON-midler spænder −0,038532–0,049777, og OFF-midler −0,039084–0,048383: de er små, men ikke alle nul.

Over alle 27 profiler er 25/27 oprindelige ON-profiler positive i begge gemte halvdele, mod 18/54 andre ON-profiler og 25/81 OFF-profiler. Tre valgte spor er positive i begge halvdele af alle tre ON-scans: batch01 ON2/rank3 samt batch02 ON1/rank2 og ON3/rank2. Det ene batch01-eksempel har ON-midler 0,042741/0,153596/0,029045; dets OFF2-halvdelmidler er 0,057044 og −0,037279. Tegn og halvdelmidler er beskrivelser fra de samme ON-udvalgte data, ikke nye uafhængige tests, en detektionstærskel eller kalibreret persistens. Alle 162 scan-midler, halvdelmidler og positive-række-antal findes i CSV/JSON uden at nulstille andre ON- eller OFF-værdier.

De tre batches er administrative opdelinger af ét historisk besøg den 28. april 2017. Der er ingen ny observation eller blind uafhængig validering. S-båndsbesøget reproducerer ikke de gamle L-båndsspor ved samme frekvens. Der foreligger ingen kvalificeret SETI-detektion, fysisk oprindelsesafgørelse, kalibreret falsk-alarm-sandsynlighed eller generel nuldetektionsgrænse.

## Rank1: alle seks eksakte gemte midler

Midlerne er bredde-middel af rå power divideret med rækkens median over hele native-udsnittet, minus den faste flankemedian. De er dimensionløse beskrivende mål; scores har en særskilt uændret kerne-median/MAD-normalisering. Tabellen er afrundet; JSON/CSV bevarer de gemte værdier.

| Batch | Valgt ON | MHz ved reference | Drift Hz/s | Score | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| batch01 | epoch1_on | 2301.269515045 | 0.336734694 | 6.160813 | 0.091451 | -0.019401 | -0.005640 | -0.008366 | 0.006022 | 0.017494 |
| batch01 | epoch2_on | 2301.795672253 | -0.948979592 | 6.188912 | -0.005027 | 0.004491 | 0.089477 | -0.026871 | -0.000102 | 0.011583 |
| batch01 | epoch3_on | 2301.035984047 | -2.938775510 | 6.356479 | -0.020238 | 0.004203 | 0.022096 | 0.001742 | 0.097547 | 0.004584 |
| batch02 | epoch1_on | 2300.390627794 | -0.010204082 | 15458.566496 | 230.396937 | 176.144631 | -0.009474 | -0.011129 | 0.022507 | -0.028582 |
| batch02 | epoch2_on | 2300.390627794 | -0.010204082 | 12813.739287 | 0.008896 | 43.946983 | 189.506116 | 183.418388 | 0.007931 | -0.015741 |
| batch02 | epoch3_on | 2300.390627794 | -0.020408163 | 12942.460482 | 0.002847 | 0.018148 | -0.001419 | -0.016114 | 191.241516 | 11.514521 |
| batch03 | epoch1_on | 2299.051501416 | 3.887755102 | 6.121757 | 0.058809 | 0.003673 | 0.011460 | -0.006593 | 0.002212 | 0.001508 |
| batch03 | epoch2_on | 2299.603231810 | -1.867346939 | 6.005318 | 0.012404 | -0.002264 | 0.091747 | 0.002960 | 0.010846 | 0.005075 |
| batch03 | epoch3_on | 2299.071958847 | 1.091836735 | 6.201318 | 0.025065 | 0.002694 | -0.011871 | -0.010735 | 0.104572 | 0.009871 |

## Faktiske procesmålinger

| Proces | CPU s | Wall s | Peak RSS bytes |
|---|---:|---:|---:|
| batch01 | 468.237484 | 468.257866 | 543232000 |
| batch02 | 465.514561 | 465.509392 | 543346688 |
| batch03 | 469.011889 | 469.044300 | 543305728 |
| Samlet output/kilde-QA | 4.464805 | 4.414701 | 156336128 |

CPU-tallene summerer til 1.402,763934 s for de tre batch-processer; dette er ikke samlet ende-til-ende setup-, rapporterings- eller paknings-CPU. Hver proces havde 1.000 CPU-s / 1.800 wall-s / 2 GiB AS-grænse; to kernel-låsepladser begrænser samtidige udvidelsesprocesser til et samlet AS-loft på 4 GiB. AS-grænsen og målt RSS er forskellige størrelser.

## Hvad de faktiske kontroller beviser

Grænse-QA verificerer 12 kort, de gemte ranks, 18 profiler/108 scan-profiler og 222.912 rå celle-forekomster mod de 24 kildefiler. q128-QA verificerer tre kort, ni profiler/54 scan-profiler, 111.456 rå celle-forekomster, alle 96 komprimerede/afkodede kildeblokke og 96 rekonstruerbare råblokfiler. Den genberegner 96 medianer over hele native-rækker og 48 ON-kernerækkemidianer; de 26 tidligere afkodede rækker er uændrede.

Udvidelsens faktiske QA verificerer alle 759 kort/geometrier/normaliseringsposter, 3.108.864 gemte kanalmaksima, 4.880.916.480 gyldige hypotesetællere, 180 top-20-rækker, 27 profiler/162 scan-profiler og 334.368 rå celle-forekomster. Seks kildefiler og 96 afkodede rækkehashes matches igen; de tidligere kildekvalificerede fuldrækkemidianer autentificeres, og 12.144 ON-kernerækkemidianer genberegnes. Fuldrækkemidianerne genberegnes ikke i udvidelsens QA.

Kontrollerne rekonstruerer ranks fra gemte maksima og validerer fysisk kanal-/tidsgeometri, profilsummer og bitidentiske råceller. De genkører ikke detektoren eller de gemte detektorscores, foretager ingen ny sporoptimering og beviser ikke fysisk signaloprindelse eller videnskabelig A/B-kvalifikation. Statiske `QA_SOURCE_REVIEW.json`-filer er kodegennemgang; ovenstående PASS gælder de særskilte, faktisk udførte `QA_RECEIPT.json`-kontroller.

## Evidens og datatilgængelighed

Den afsluttede grænse-science findes i `analysis/continuation/SCIENTIFIC_REVIEW.json`; den stationære q128-struktur i `analysis/new_visit_recovery/SCIENTIFIC_REVIEW.json`. Udvidelsens afsluttede saved-value-opsummering er `analysis/s2017_full_band/summary/FULL_BAND_SUMMARY.json`, SHA256 `d7ffd5c831b46649cebfc6e85aa05c11a701a8fada382ad290c79cb9f7da62c2`. Alle 162 nye scan-profiler findes i `FULL_BAND_PROFILE_MEANS.csv`. Den endelige saved-science-gennemgang er `analysis/s2017_full_band/FULL_BAND_SCIENTIFIC_REVIEW.json`, SHA256 `6d2712b842b766f47d1344ab16b2505341b0ae26641dc74aee5c670db1796b03`.

Faktisk grænse-QA: `c76932358e8bc5d3f53b3a66e0086c44287c4f81e76cb3b4d6c313cffcb8a97d`. Faktisk q128-QA: `e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f`. Faktisk udvidelses-QA: `e1d77ef88fa7a47965bd783b09258b36578c476cd5788ffc94924f3e03d1bc6f`. Hver afslutning og kontrol er hashbundet til sine oprindelige scopes, kode- og inputbytes.

Se `DATA_AVAILABILITY.md` for de fem byteverificerede RAW-arkiver, eksakte checksums, execution-/QA-kvitteringer, scopes, kode og miljøkrav. Resultatarkivets navn er `SETI_FULL_POWER_RESULTS_2026-10-10.zip`; dets eksterne størrelse/SHA og pakkekontrol skal læses i `DATA_PACKAGES.json`, som oprettes efter pakningen. Denne rapport kvitterer for de afsluttede beregninger og kontroller; den kvitterer ikke for oprettelse, upload eller publicering af resultatarkivet.
