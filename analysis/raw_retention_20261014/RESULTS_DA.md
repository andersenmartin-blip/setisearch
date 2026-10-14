# SETI: råeffekt, normalisering og integrationsudsmøring

14. oktober 2026. **648 nye råeffekttests er færdige med uafhængig efterregning. Den væsentlige begrænsning er signalets bredde: en perfekt enkeltkanalsbane kan i udsmøringsmodellen opsamle højst 3,91–30,58 % af den indsatte referenceeffekt, median 7,80 %. Normaliseringens ændring er lille i dette panel. Ingen kvalificeret SETI-detektion.**

Kode, regler og inputidentiteter blev offentliggjort før råværdierne blev åbnet i [commit 2e80a6ad9a92](https://github.com/andersenmartin-blip/setisearch/commit/2e80a6ad9a920632c6ec943748e2d2963c8b656d). Top 5, score, kanalgeometrier, råformat og kerner er uændrede efter udfaldene.

## Det målte resultat

Hver tabelcelle har 108 parrede placeringer. Tallene viser, om **den udpegede centrale fire-bin-bane** er med, når én eller fem lokale hypoteser bevares. De er ikke antal fysiske signaler fundet.

| Effektsfordeling | A2: top 1 → top 5 | A8: top 1 → top 5 |
|---|---:|---:|
| Én kanal | 77 → 105 | 108 → 108 |
| Tre kanaler | 11 → 37 | 86 → 108 |
| Integrationsudsmøring | 0 → 3 | 4 → 16 |

For udsmøring kan andre baner ligge på samme brede plateau og være lige så gode fysisk. Ved A8 opsamler den bedste faktisk bevarede top-5-bane median 7,77 % af referenceeffekten, mod median 7,80 % for den bedste mulige enkeltkanalsbane i hele familien. I 89/108 A8-cases når en bevaret bane præcis familiens signal-only-effektloft, selv om den udpegede centerbane kun bevares i 16. Ved A2 er medianerne 4,13 % og 7,80 %, og 40/108 når loftet. Det er beskrivende modelgeometri, ikke en ny recovery-gate eller FAP.

Selve den nye normalisering ændrer den udpegede banes score med under 0,027 i alle modeller/cases i forhold til samme modificerede råeffekt med fast gammel normalisering. Ved udsmøring A2 er intervallet -0,00422 til +0,00468, mens medianløftet over baggrunden er 0,306. Ved A8 er medianløftet 1,214. Det peger inden for dette panel på mismatch mellem enkeltkanalsstatistik og effektsfordeling som større begrænsning end normaliseringens ekstra ændring. Den lokale median501 kan stadig ændre responsen; dens effekt er med i de gemte råprofiler og responsdiagnoser.

## Hvad der faktisk blev ændret og genberegnet

Alle 54 eksisterende profiler gennemløbes med to på forhånd valgte placeringer: vært -640 kanal/rækker 0–3 og vært +640/rækker 12–15, med nye rationelle drift/fasepar. De 108 placeringer og alle deres positive responsceller er forskellige fra tidligere indsprøjtningsbanker. Den samme placering gentages parret ved A=2/8 og tre effektsfordelinger:

- Én bin med vægt 1.
- Tre bins med vægt 1/4, 1/2 og 1/4.
- En intrinsisk, en-kanals top-hat foldet med et jævnt lineært frekvenssweep over integrationen. Den kontinuerte fase bevares før afrunding. Dette er den tidligere generators idealiserede eksponeringsmodel, ikke en målt instrumentrespons.

Samme **samlede** positive råeffekttilførsel pr. aktiv række bruges i alle tre modeller: A × oprindelig rækkemedian × oprindelig residual-MAD-skala. A er en referenceamplitude, ikke SNR eller kalibreret flux; A8 er derfor ikke samme detektorstyrke i de tre modeller. Der foretages ingen kompensation for bredere signalers lavere top. Additionen beregnes i float64 og rundes tilbage til kildens float32-format. Hver modificeret hel råmatrix får SHA256.

Udsmøringen er |drift| × 18,253611008 s / 2,7939677238464355 Hz og spænder 3,2699–25,5821 native kanaler i dette panel. Samtlige 4096 oprindelige normaliseringskanaler genberegnes i de fire modificerede rækker: median501, residualmedian, MAD og winsoriseret middel. De 12 urørte rækker genbruger genberegnet og autentificeret baseline. Hele den eksakte lokale fire-række-familie over syv vinduer scores med den uændrede bredde-1-formel.

92 geometrier har alle centerbins i normaliseringskernen; 16 ligger udenfor. Kerne-, halo- og helt udenfor-støtte-klasser er gemt særskilt, også for udsmøringens vinger. Ingen geometri fravælges efter udfaldene.

## Kontrol og afgrænsning

Uafhængig QA bestod **2,089,334 kontroller**, 648 rekonstruerede råmatrixhashes og 311,290 kanalbanescorer. Score-, normaliserings- og rangafvigelserne var nul. De 54 fulde baseline-normaliseringer og 2592 ændrede række-normaliseringer blev kontrolleret med en særskilt sorteret median501-implementering, som ikke importerer producenten. De oprindeligt gemte normaliseringstal afveg højst 3,82e-17 fra ny beregning.

Målt proces-CPU var 94.73 s for producenten og 23.94 s for QA. 600 CPU-s er konservativt reserveret og tilbageføres ikke; det er en ny reservation uden nulstilling af tidligere forbrug. Største målte RSS var 128.6 MB. Setup, review, hele sessionen og publicering hævdes ikke fuldt målt. 0 DKK, 0 nye teleskopforespørgsler og 0 nye teleskopbytes.

Baggrunden er stadig det tidligere eksponerede besøg fra 28. april 2017. Det er lokal metodekontrol omkring ni tidligere udvalgte spor, med korrelerede geometrier/modeller/amplituder. Global frekvensudvælgelse og den fulde seks-scan OFF/RFI/null-kæde er ikke testet her. A0's 108 markerede tomme centerbaner er sham-mål, med 0/2 i top 1/top 5, uden støj-FAP-fortolkning.

Original A/B forbliver **FAIL_CLOSED**; beskyttede 2016-data og den lukkede 2019-rute bevares. Ingen fysisk følsomhed eller universel signalgenfinding udledes. Slutcheckpointet er 20. oktober 2026.

[Resultater](results/SUMMARY.json) · [QA](results/QA_RECEIPT.json) · [Frosset scope](SCOPE.json) · [Reproduktion](README.md).
