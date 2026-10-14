# SETI: bredere skabeloner på nye råeffektplaceringer

14. oktober 2026. **216 nye råeffekttests er færdige med uafhængig QA. Med én samlet liste på fem kandidater stiger medianen af den bedste bevarede banes referenceeffektandel fra 7,72 % til 77,17 % ved A8 og fra 7,81 % til 83,56 % ved A32. Ingen kvalificeret SETI-detektion.**

De faste bredder 1/3/9/33, alle identiteter, begge programmer og score-/tie-regler blev offentliggjort før råværdierne blev åbnet i [commit 4ba5e3a8152b](https://github.com/andersenmartin-blip/setisearch/commit/4ba5e3a8152b7460761fe7b21d7a4b46407c1d53). Ingen bredde, amplitude, k eller tærskel er tunet efter udfaldene.

## Samme fem pladser, større effektandel

108 placeringer ved hvert niveau, med samme integrationsudsmøringsmodel og samme samlede råreferenceeffekt for begge politikker:

| Referenceamplitude | Median: bedste bevarede boks, bredder 1/3/9/33 | Median: bedste bevarede enkeltkanalsbane |
|---|---:|---:|
| 8 | 77,17 % | 7,72 % |
| 32 | 83,56 % | 7,81 % |

Andelen beregnes fra de indsatte enhedsmasse-kerner i de fire aktive rækker. Den måler én faktisk bevaret hypoteses boks; overlappende top-5-bokse lægges ikke sammen. Den er referenceeffekt i den erklærede model, ikke fysisk flux, kalibreret SNR eller en detektionssandsynlighed.

Begge regler bevarer **præcis fem** hypoteser pr. liste. Den nye liste vælges på tværs af bredderne, ikke som fem pr. bredde. Søgefamilien får fire gange så mange skabeloner; dette kan ændre falskalarmbyrden, selv om antallet af opfølgningspladser er uændret. Ingen equal-FAP-påstand udledes.

## Effektfangst og score er forskellige mål

Den faste score er sum af standardiserede residualer over fire rækker og w kanaler, divideret med sqrt(4w). Den idealiserede signal-only-scorekoefficient er 2f/sqrt(w), hvor f er referenceeffektandelen. En smal boks kan derfor give højere forventet score end en boks med alle svage vinger. Det er en definition af denne score, ikke en kalibrering af korreleret baggrundsstøj.

Ved A8 er medianen af den bedste bevarede koefficient relativt til hele den kombinerede families signal-only-oracle **99,963 %**; ved A32 er den **100 %**. Mindste A32-forhold er **92,775 %** på tværs af alle 108 placeringer. Ved A8 forekommer stadig et nul-forhold; universel bevaring er ikke etableret. Sammenligningen er af koefficienter i en kendt indsat model, ikke en sky-recovery-rate.

Medianen af den faktiske scorestigning over uændret råbaggrund er 3,609 mod 1,202 ved A8 og 14,721 mod 4,907 ved A32, for den bedste stigning blandt de fem bevarede kandidater. Det er parrede scoreændringer, ikke den udvalgte scorers uafhængige signifikans.

Alle positive responsceller i de fire aktive rækker dækkes af mindst én bevaret boks i **24/108 A8**- og **38/108 A32**-lister, mod nul med enkeltkanalsbokse. Dette er geometrisk fuldstændighed. At en score-optimal boks udelader svage vinger er ikke bevis på et tabt fysisk signal. De på forhånd beregnede signal-only-optima bruger bredde 3/9/33 i henholdsvis 24/48/36 geometrier; bredde 1 er ikke optimal i dette panel.

## Fast råkæde og nye identiteter

Alle 54 eksisterende profiler får to nye placeringer: vært -384/rækker 4–7 med driftfraktion -31/100 og fase -7/100, samt vært +384/rækker 8–11 med driftfraktion 79/100 og fase 41/100. Ingen af de 108 placeringer eller deres 6561 positive responsceller overlapper tidligere indsprøjtningsbanker. Baggrunden er fortsat det eksponerede besøg fra 28. april 2017.

Kun den uændrede, idealiserede integrationsudsmøringskerne bruges: en intrinsisk en-kanals top-hat foldet med jævnt lineært sweep i hver 18,253611008-sekunders integration, omkring det kontinuerte frekvenscenter. Samme samlede råreferenceamplitude A8/A32 bruges før skabelonvalget; der kompenseres ikke for skabelonens bredde eller ideal-score. Det er en modelundersøgelse, ikke en målt instrumentrespons.

Råeffektadditionen og float32-rundingen, fuld median501/MAD/winsor-normalisering over 4096 kanaler og alle boksresidualer genberegnes. De fire ændrede rækker genberegnes for hver case; de 12 urørte rækker genbruger autentificeret, genberegnet baseline. 96 geometrier ligger helt i normaliseringskernen, 11 udenfor, og én har tre af fire centerbins inde; alle strata bevares. Alle 177.880 metadata-kontroller af boksstøtte og kendte DC-kanaler består; bredde 33 kan geometrisk dække hele kernen i alle 108 placeringer.

Den ene kombinerede top-5-liste sorteres efter score, bredde, vinduets første række og native-center-tuplen. Den fravælger ikke bredder eller cases efter udfald. Reflekteret drift, fysisk oprindelse, OFF-veto og yderligere kandidatklyngning tilføjes ikke her.

## Kontrol, omkostning og begrænsninger

Uafhængig QA bestod **4.411.843 kontroller** af **533.640 skabelonscorer**, 24.547.440 boks-celleværdier og samtlige 216 rekonstruerede råhashes. Råeffekt, operationel normalisering, boks-summer, scorer, udvælgelse og scoreændringer stemmer eksakt. Signal-only-geometriens numeriske afrunding afviger højst 2,22e-16; oprindeligt gemt normalisering afviger højst 3,82e-17. QA bruger særskilt median501, CDF- og boksberegning uden at importere producenten.

Målt proces-CPU er 47.80 s for producenten og 24.79 s for QA, med højeste målt RSS 111.7 MB. 1000 CPU-s er konservativt reserveret uden tilbageførsel eller nulstilling af tidligere forbrug. Setup, metadataarbejde, review, publicering og hele sessionen hævdes ikke fuldt målt. 0 DKK, 0 nye teleskopforespørgsler, 0 nye teleskopbytes og 0 nye observing visits.

De lokale hypoteser ligger omkring ni tidligere udvalgte spor og på korrelerede, eksponerede baggrunde. Den globale frekvensudvælgelse og den fulde seks-scan recovery-/OFF-/RFI-/null-kæde er ikke kvalificeret. Original A/B forbliver **FAIL_CLOSED**, 2016 er beskyttet og 2019-ruten lukket. Ingen kalibreret FAP, fysisk følsomhed eller astronomisk bekræftelse. Slutcheckpointet er 20. oktober 2026.

[Resultater](results/SUMMARY.json) · [Uafhængig QA](results/QA_RECEIPT.json) · [Frosset scope](SCOPE.json) · [Reproduktion](README.md).
