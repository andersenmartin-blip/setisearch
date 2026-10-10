# SETI-resultat: S2017 native 170/171/172, 10. oktober 2026

Den nye fase er afsluttet med 1536 gemte ON-kort og 72 faste profiler; både den indre og den sammenføjede faktiske output-/kildekontrol har PASS. Der er ikke etableret en kvalificeret SETI-detektion. De største nye scores tilhører stationære midterkanaler, som er positive i alle 16 rækker i samtlige tre ON- og tre OFF-scanninger. Scores og profilresidualer er beskrivende mål uden kalibreret SNR eller falskalarmssandsynlighed; materialet bestemmer ikke en fysisk oprindelse eller en generel nulkonklusion.

De nye native 170/172-frekvenser udvider den allerede undersøgte native 171 fra samme besøg den 28. april 2017, `AGBT17A_999_55`, mål `HIP98505/HD189733`. Områderne blev fastlagt før deres egne nye spektralværdier, men efter native 171-resultaterne var kendt. Ranglister og top3-profiler blev efterudvalgt på de samme ON-data. Udvidelsen er hverken en blind uafhængig bekræftelse, en ny observation eller samme-frekvens-replikation af de tidligere 2016 L-båndstilfælde. Oprindelige A/B-fejltilstande og beskyttede 2016-holdouts forbliver `FAIL_CLOSED`/lukkede.

## De stærkeste gemte profiler

Hvert nyt native-chunk har en stationær rang 1-profil i hver af de tre ON-lister i batch 02. Alle 96 fysisk afrundede centre over de seks scanninger ligger på samme midterkanal, bredde 1. Driftgitterets midterværdi er `-4.440892098500626e-16 Hz/s`, numerisk tæt på 0. De tre rang 1-udvælgelsesinstanser i samme native beskriver samme faste seks-scan-geometri; de er ikke tre uafhængige fund.

| Native | Midterfrekvens, MHz | ON 1-middel | OFF 1-middel | ON 2-middel | OFF 2-middel | ON 3-middel | OFF 3-middel |
|---|---:|---:|---:|---:|---:|---:|---:|
| 170 | 2303.320312500 | 678.369667 | 517.029134 | 555.512110 | 537.177422 | 562.425076 | 545.172728 |
| 172 | 2297.460937500 | 689.616605 | 526.695203 | 566.572889 | 549.216297 | 570.319296 | 554.652635 |

Tallene er gemte, normaliserede centrum-minus-flankemedian-midler uden fluxenhed. Begge profiler har 16/16 positive rækker i alle seks scanninger og positive midler i begge halvdele. De er dermed også tydeligt til stede i OFF på den samme faste geometri. Den tidligere native 171-linje ved 2300.390625 MHz var tilsvarende fælles for ON/OFF, og dens stærkeste udvalgte q127-haler krydsede den. Afstanden mellem de tre native-midterfrekvenser er 2.9296875 MHz; dette beskriver kildegitterets geometri og klassificerer ikke en fysisk eller instrumentel årsag.

Alle 120 gemte batch02-top20-posters boksbaner berører deres eget native-midtercenter i den ON-scanning, der udvalgte dem. De stærke, også drivende scorer i disse lister deler derfor støtte med den fælles stationære kanal; de kan ikke behandles som 120 uafhængige fysiske fund. Dette er et efterfølgende tjek af den gemte geometri, uden fit eller ny sporudvælgelse.

De 54 nye indre profilscores spænder fra 5.714241694 til 26778.722047715. Udvælgelses-ON har størst middel i 50/54 instanser og positive halvdele i 48/54. Andre ON-målinger har positive halvdele i 41/108, OFF i 56/162. Ni af 54 faste spor har positive halvdele i alle tre ON; syv af disse har også positive halvdele i mindst én OFF. Disse efterudvalgte egenskaber er hverken et kandidatkrav, et OFF-veto eller uafhængig replikation. Små residualer på en præcis fast OFF-bane udelukker ikke nærliggende OFF-struktur.

Alle 18 lokale ON-top20-lister fra de seks indre job bevares separat. Der er ikke lavet en ny global top360-rangliste. Se [den indre fortolkning](../results/search/interpretation/INTERIOR_INTERPRETATION.json), [scanmidlerne](../results/search/interpretation/FIXED_SCAN_MEASURES.csv) og [den indre rapport](../results/search/interpretation/RAPPORT_DA.md) for hver identitet, drift, bredde, referenceepoch og signerede tidsrække.

## Sammenføjede grænser

De to nye grænsefamilier har 12 kort, 18 faste profiler og 108 scanmålinger. De valgte scores er 5.082361–5.719388. Udvælgelses-ON er størst i 18/18 profiler, og begge udvælgelseshalvdele er positive i 18/18; det er egenskaber ved spor, der blev valgt på netop disse ON-data. De 54 faste OFF-midler spænder fra cirka −0.028830 til +0.023155554339, og de 36 andre ON-midler fra cirka −0.029050 til +0.047042078113. Positive OFF-/andre-ON-værdier bevares; der påstås ikke manglende respons eller manglende gentagelse.

| Grænse | Native-skel, MHz | Referencekanalcentres interval, MHz |
|---|---:|---:|
| `pair170_171` | 2301.855468750 | 2301.844027452–2301.866912842 |
| `pair171_172` | 2298.925781250 | 2298.914339952–2298.937225342 |

Hver grænse dækker 8192 referencekanaler fordelt på to normaliseringskerner. Seks af 18 faste baner har gemte centre på begge sider af skellet gennem de seks scanninger; 42 af 1728 patch-rækker berører skellet med deres ±64-kanals vindue. Dette er geometri. Skellet er ikke kanten af det indlæste halo-udsnit eller et hul i data. Den kendte 2300.390625 MHz-linje ligger uden for begge smalle grænsereferencevinduer; dens tidligere observation forklarer ikke automatisk disse profiler. Se [grænserapporten](../boundaries/results/interpretation/RAPPORT_DA.md) og [de gemte grænsemidler](../boundaries/results/interpretation/FIXED_SCAN_MEASURES.csv).

## Dækning og faktisk kontrol

| Afsluttet familie | ON-kort | Faste profiler | Separate top20-poster | Kontrollerede rå patchcelleforekomster | Korrelerede drift-/breddekombinationer |
|---|---:|---:|---:|---:|---:|
| Seks nye indre job | 1524 | 54 | 360 | 668736 | 9800417280 |
| To nye sammenføjede grænser | 12 | 18 | 120 | 222912 | 77168640 |
| Ny fase i alt | 1536 | 72 | 480 | 891648 | 9877585920 |

Hvert kort har 4096 referencecarriers, 785 drifter fra −4 til +4 Hz/s og bredder 1/3 kanaler. De 6291456 gemte carrier/origin-maksima og hypotesekombinationerne er korrelerede; de er ikke uafhængige tests. Bredderne svarer til 2.793967724 og 8.381903172 Hz. Detektoren bruger separat 4096-kanals kerne-normalisering og række-MAD. Native-profiler bruger hele 1048576-kanals float32-rækkens median før float64-promovering; sammenføjede profiler bruger hele 2097152-kanals rækken. Profilmidler og rangscores har forskellige normaliseringer og må ikke pooles som kalibrerede styrker. Der er ikke udført fit, ny trackoptimering, OFF-søgning eller OFF-veto.

Med den tidligere native 171 er tripletdækningen 766 af 768 referencekerner à 4096 kanaler: 99.7395833333%, svarende til 8.76617431640625 MHz af de erhvervede 8.7890625 MHz. Kun de ydre 170 q0 og 172 q255 er udeladt. Dette er ikke hele teleskopets S-bånd. Samlet S2017 er der 2298 kort/108 profiler/1337472 patchcelleforekomster. Med de tidligere 2016-grænser er det 2310 kort/126 profiler/1560384 forekomster og 14852800512 korrelerede kombinationer. De 2016-kort anvendte 763 drifter, så totalen kan ikke beregnes med 785 drifter for alle 2310 kort. Ingen ny rangliste på tværs af de historiske familier er udvalgt.

Den faktiske indre QA kontrollerede 1524 gemte kort, alle 54 profiler/324 scanprofiler, 192 afkodede kilderækker, 192 fuldrækkemedianer, 24384 ON-kernemedianer og 668736 rå patchcelleforekomster bitvist. Den faktiske grænse-QA kontrollerede 12 kort, 18 profiler/108 scanprofiler, 18 distinkte kompakte filer/288 distinkte rækker, 192 sammenføjede rækkemedianforekomster og 222912 rå patchcelleforekomster. Forekomster er ikke unikke fysiske celler. Begge QA rekonstruerede gemt rangordning, driftkvantisering, fysisk tids-/frekvensgeometri og fast profilaritmetik uden at genkøre detektoren eller foretage nye kilde-GETs.

## Ressourcer og data

| Faktisk afsluttet arbejde | Proces-CPU, sekunder | Proces-wall, sekunder | Peak RSS, bytes |
|---|---:|---:|---:|
| Acquisition | 10.743632 | 373.610748 | 80240640 |
| Kilde-QA | 3.695415 | 3.647809 | 73281536 |
| Seks indre science-job | 2788.608304 i alt | Se de seks kvitteringer; to samtidige job pr. bølge | 544337920, største job |
| To grænse-science-job | 32.222053 i alt | 16.859596 og 15.288853 | 1014013952, største job |
| Indre gemte-output-QA | 10.572936 | 10.530957 | 233955328 |
| Grænse gemte-output-QA | 8.326086 | 8.265364 | 561192960 |

Ny science-CPU er 2820.830356624 s i alt. Kvitteringerne angiver `cost_DKK=0`. Den nye acquisition gav 192 præcise GETs/597792529 BODY-bytes uden gentagne GETs eller retries. RAW-arkivet er faktisk sikret i tre eksakte dele; et enkelt 604399781-byte arkiv blev ikke gemt som én fil. Efter de tre gemninger og ny chunkhash-kontrol blev kun de 192 redundante nye sidecars fjernet. Alle deklarerede HDF5/science-input er bevaret.

De to mislykkede forberedelser til gemning af ét stort arkiv, midlertidig frigivelse og identisk genetablering af del 1/2 samt byteverificerede præfikskopier er dokumenteret. En 44 MB-kopi dukkede igen op byteidentisk før planlagt manuel genetablering; dens ophav er ukendt, og manuel genetablering påstås ikke. Kopierne blev ikke science-input; der blev hverken udført reruns eller gentagne kilde-GETs som følge af kapacitetsarbejdet.

Se [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md) for de tre faktisk gemte RAW-dele, samlekommando, tidligere native 171-RAW, runtime og reproduktionsgrænser. RESULTS-pakkens størrelse/SHA, faktiske gemning og afsluttende Git-readback dokumenteres i separate autoritative kvitteringer og det eksterne `DATA_PACKAGES.json`; denne rapport påstår ikke en gemning, som først udføres efter dens admission/pakning.

## Evidens

De bytepinnede evidensfiler er [acquisition](../results/acquire/ACQUISITION_RESULT.json), [kilde-QA](../results/source_review/QA_RECEIPT.json), [alle otte faktiske output-identiteter](../ACTUAL_SEARCH_ADMISSION_REVIEW.json), [indre faktisk QA](../results/search/review/QA_RECEIPT.json), [grænse faktisk QA](../boundaries/results/review/QA_RECEIPT.json), begge fortolkningskvitteringer og de uafhængige [indre](../review/INTERIOR_SCIENTIFIC_REVIEW.json)/[grænse](../review/BOUNDARY_SCIENTIFIC_REVIEW.json) gennemgange. [FINAL_REPORT_EVIDENCE_REVIEW.json](FINAL_REPORT_EVIDENCE_REVIEW.json) binder denne rapport og data-noterne til disse faktiske inputs. Den senere [videnskabelige syntese](../review/FINAL_SCIENTIFIC_SYNTHESIS_REVIEW.json) binder også evidensgennemgangen uden en cirkulær checksum.
