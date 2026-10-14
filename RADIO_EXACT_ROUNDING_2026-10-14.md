# SETI: fuldstændig lokal familie af afrundede spor — 14. oktober 2026

Den lokale sporgeometri er nu fuldstændigt gennemgået inden for den erklærede fire-række-model. **Alle 19 tidligere manglende testgeometrier er med**, og den stærke betingede indsprøjtning genfindes fuldt i **1.512/1.512** tilfælde mod tidligere **1.493/1.512**. Svage indsprøjtninger viser samtidig et tab ved at beholde alene den største score: fuldt match falder fra **1.067 til 1.036 af 1.512**. **Ingen kvalificeret SETI-detektion er etableret.**

## Hvad der faktisk er undersøgt

De ni allerede udvalgte ON-spor ved HIP98505/HD189733 følges i de samme seks scanninger fra **28. april 2017**: 54 profiler og syv overlappende fire-række-vinduer pr. profil, i alt **378 vinduesfamilier**. Det er ét tidligere eksponeret besøg med tre ON-scanninger af målstjernen og tre oprindelige OFF-retninger; ingen ny observation eller frekvensdækning er tilføjet.

Hvert spor beholder sin oprindelige frekvensreference og første integrationsmidte i det oprindelige vindue. Familien tillader driftændring **±0,0253164556962 Hz/s**, referencefase **±0,5 native kanal**, bredde én kanal og de faktiske tidsmellemrum. Native kanalbredde er 2,7939677238464355 Hz. Eksakt rationel geometri gennemgår alle fire-række-baners afrundingsceller, inklusive kanter og hjørner med ties-to-even. Fuldstændigheden gælder denne afgrænsede lineære kvantiseringsmodel.

Der er **22.235 nativebaner opgjort pr. vinduesfamilie ved nul forskydning** og **200.115 gemte scorer** inklusive de otte faste frekvenskontroller ved ±256/512/768/1024 kanaler. Alle **800.460 rækkebidrag** er bevaret. Overlappende vinduer, kontroller og baner er korrelerede; tallene er ikke antal uafhængige forsøg eller fysiske signaler. Alle tidligere 405-gridbaner er indeholdt i den nye familie.

## Afrundingsfejlen og indsprøjtningerne

Det tidligere gitter missede 19 af 1.512 forskellige fire-række-testgeometrier: 17 havde højst tre rækker i samme native spor, to højst to. De kontinuerte sandhedspunkter lå alle inden for parameterboksen. En koordinatfejl under en halv kanal sikrer ikke samme afrunding, når sandheden ligger tæt ved en halvheltalsgrænse. Den mindste målte geometriske afstand til en sådan grænse var **0,00013347 kanal**. Den eksakte familie repræsenterer nu alle 1.512 sandhedsgeometrier.

De **3.024 betingede indsprøjtninger** bruger to additive niveauer i standardiserede residualer, en delta i én afrundet native bin og fire aktive rækker. De genbruger de eksponerede baggrunde og den uændrede oprindelige normalisering; rå preprocessing og instrumentets linjerespons er ikke afprøvet.

| Diagnostik | Tidligere 405-grid | Eksakt familie |
|---|---:|---:|
| Sandhedsgeometri repræsenteret, pr. niveau | 1.493/1.512 | 1.512/1.512 |
| Stærkt niveau 8: støjende maksimum matcher alle fire aktive rækker | 1.493/1.512 | 1.512/1.512 |
| Svagt niveau 2: støjende maksimum matcher alle fire aktive rækker | 1.067/1.512 | 1.036/1.512 |

Ved det svage niveau går **43** tidligere fulde maksimumsmatch over til delvise match, mens **12** går den anden vej: netto **−31**. De nye delvise vindere har højere score; den mindste målte fordel i de 43 tab er **0,0101296**. Den korrekte fulde bane findes stadig i familien. Dette er et problem med valg af maksimum under støj, ikke manglende geometrisk repræsentation. Alle scorer beholdes til opfølgning.

## Observationsresultat og kontrol

De ni egne ON-maksima er uændrede og ligger **6,638491–7,450295**. Øvrige ON-maksima ligger **2,444902–4,543590**, OFF-maksima **2,010474–3,828783**. Det større lokale udvalg forbedrer ét af 18 øvrige ON-maksima og fire af 27 OFF-maksima. Scorer og kontrolrækker er beskrivende efter udvælgelse; der er ingen kalibreret SNR/FAP, kvalificeret OFF-veto eller uafhængig besøgsreplikation.

Alle ni egne ON-vindere har reelle todimensionale parameterområder. Blandt 54 nul-forskydningsmaksima findes én OFF-vinder kun i et parameterpunkt (`epoch3_on_rank1_epoch2_off`); de øvrige 53 har todimensionale områder.

Uafhængig numerisk QA består. Den bruger en anden kandidat-/feasibilitetsmetode med **110.136 kandidat-tupler**, rekonstruerer alle 54 fulde normaliseringskerner og kontrollerer alle 200.115 scorer og 3.024 indsprøjtninger. Største kontrollerede numeriske afvigelse er **5,33×10⁻¹⁵**. Den separate geometri, produktion og QA brugte henholdsvis **8,58 / 26,12 / 44,99 målte process-CPU-sekunder**; dette er ikke en samlet sessionsopgørelse.

**14 waterfallfigurer** og den endelige fire-siders PDF er fremstillet og visuelt kontrolleret. Den første figurlayoutversion er bevaret; rettelsen flytter kun akser, legend og billedtekster. Scorer og geometri er ikke genkørt for layoutrettelsen. De endelige figurer ligger i `waterfalls_v2/`.

## Næste afgrænsede diagnostik

Undersøg de svage tilfælde ud fra de allerede gemte scorer: rang og scoreafstand for kendte fulde sandhedsbaner, samt hvilke delvise vindere der fortrænger dem. Fastlæg derefter en eventuel regel for at bevare flere kandidater **før frisk validering**. Bevar også de målte udfald, hvor den svage bane taber. Figurernes morfologi kan undersøges uden at tilpasse en detektionsgrænse til disse eksponerede resultater.

**0 DKK, nul nye teleskopforespørgsler. Original A/B er FAIL_CLOSED; beskyttede 2016-data og lukkede 2019-data er uændrede. Formelt checkpoint: 20. oktober 2026.**

Offentligt grundlag: [SUMMARY.json](analysis/rounding_followup_20261014/SUMMARY.json), [geometrisk kvittering](analysis/rounding_followup_20261014/exact_geometry_results/GEOMETRY_RECEIPT.json), [produktionskvittering](analysis/rounding_followup_20261014/results/EXECUTION_RECEIPT.json), [uafhængig QA-oversigt](analysis/rounding_followup_20261014/qa_results/QA_RECEIPT_SUMMARY.json), [19-cellernes diagnose](analysis/rounding_followup_20261014/geometry_results/DIAGNOSIS19.json), [486 scoreoversigter](analysis/rounding_followup_20261014/results/SCORES_COMPACT.csv), [3.024 indsprøjtninger](analysis/rounding_followup_20261014/results/INJECTIONS_COMPACT.csv), [fulde kildehashes](analysis/rounding_followup_20261014/PUBLIC_EVIDENCE.json), [reproduktion og dens afgrænsning](analysis/rounding_followup_20261014/REPRODUCE.txt), den danske PDF `SETI_native_spor_2026-10-14.pdf` i den komplette ZIP. Den komplette ZIP indeholder den fulde QA-kvittering, alle JSON-resultater, scorearrays, originale råcrops og normaliseringer; de kompakte offentlige tabeller erstatter ikke disse reproduktionskilder.
