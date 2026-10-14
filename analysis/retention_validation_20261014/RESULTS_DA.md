# SETI: fastlåst top-5-regel kontrolleret på nye signalplaceringer

14. oktober 2026. **8.466 betingede cases er beregnet og efterregnet uafhængigt. Ved svagt indsat signal bevarer top 5 den komplette bane i 2.623/2.822 cases (92,95 %), mod 1.898/2.822 (67,26 %) med top 1. Det er 725 flere bevarede baner. Ingen kvalificeret SETI-detektion.**

Reglen og begge beregningsprogrammer blev offentliggjort før værdierne blev åbnet i [præregistreringscommit 0a6cf6578a1a](https://github.com/andersenmartin-blip/setisearch/commit/0a6cf6578a1a8f8ee2f46d5a9b834bda39222a60). Der er ikke ændret k, tie-regel eller scoregrænser efter udfaldene.

## Resultater

| Indsat amplitude pr. aktiv residualbin | Komplet bane med top 1 | Komplet bane med top 5 | Ekstra bevaret |
|---|---:|---:|---:|
| 2, svag | 1.898/2.822 | 2.623/2.822 | 725 |
| 8, stærk | 2.822/2.822 | 2.822/2.822 | 0 |

**199 svage baner ligger stadig uden for top 5.** Den værste svage sandhedsbane har rang 202. Resultatet støtter bevaring af flere lokale alternativer i denne model; det etablerer ingen universel genfinding.

På værtsforskydningerne -768/+768 er svag top-5-bevaring 1.315/1.411 og 1.308/1.411. For de 2.074 placeringer med et relativt native-bin-spor, som ikke var i den gamle indsprøjtningsbank, bevares 1.915 (92,33 %). De øvrige 748 har ny absolut placering men tidligere set relativ geometri; her bevares 708 (94,65 %).

## Fast panel og afhængigheder

54 eksisterende profiler, syv overlappende fire-række-vinduer og fire på forhånd valgte rationelle drift/fasepar på to andre værtsforskydninger giver 3.024 parametertræk. 202 geometriske aliaser fjernes før scoring, så der resterer 2.822 forskellige fysiske placeringer og tre parrede amplitudeniveauer 0/2/8. Ingen placering overlapper den gamle bank, heller ikke på tværs af profiler. Alle placeringer findes i den uændrede eksakte familie, har rå501-støtte og undgår de kendte DC-bins.

Driftfraktioner er -83/100 og 47/100 af det gamle halve drifttrin; faser er -41/100 og 13/100 kanal. Værterne er -768 og +768 kanaler. Top 5 sorteres efter score, derefter vinduets første række og fire-bin-tuplen. Faktisk medlemskab af de fem pladser afgør bevaringen; optimistiske tie-ranggrænser bruges ikke som erstatning.

Baggrunden er stadig det eksponerede besøg 28. april 2017. Nye indsprøjtningsplaceringer er ikke nye eller blinde teleskopdata. Modellen lægger signal til gemte standardiserede enkelt-bin-residualer med fast normalisering og omfatter kun lokal finanalyse omkring ni tidligere valgte spor. Den omfatter ikke den fulde globale udvælgelse, rå preprocessing, instrumentets linjerespons eller et fysisk emissionsmål. Vinduer, amplituder og baggrunde er afhængige.

## Kandidatbyrde og faktiske profiler

De 108 forskellige profil/vært-lister på uændret baggrund giver 108 kandidater med top 1 og 540 med top 5: **fem gange flere opfølgningspladser**. Dette er en arbejdsbyrde, ikke en falsk-alarm-rate. Ved amplitude 0 er de på forhånd markerede tomme målplaceringer med i top 1/top 5 i 9/39 af 2.822 cases; disse tilfældige sammenfald er ikke signalgenfinding eller en teleskop-FAP.

Alle 54 faktiske nul-forskydningsprofiler har nu fem bevarede lokale kandidater, i alt 270 listeposter. Blandt 540 par inden for samme profil deler 250 et til tre aktive måleceller; de 270 poster er derfor ikke 270 uafhængige signaler. Der er ingen ny fysisk klassifikation, genobservation eller kvalificeret OFF-veto.

## Kontrol, ressourcer og reproduktion

Uafhængig QA bestod **1,079,583** kontrolpunkter, herunder alle 8.466 cases, 42.330 kandidatposter, 66.705 gemte grundscorer, geometriske aliaser, nulbyrde og alle 270 observerede poster. Største numeriske scoreafvigelse er 8.88e-16. QA importerer ikke producentprogrammet. Den kontrollerer gemt score-/residualaritmetik; den genkører ikke teleskopernes rå preprocessing.

Producent og QA brugte henholdsvis 1.71 og 8.04 målte proces-CPU-sekunder. Den konservative reservation er 180 CPU-sekunder og tilbageføres ikke; dette er en ny afgrænset reservation, ikke en nulstilling af tidligere forbrug. Maksimal målt RSS var 151.8 MB. Setup, review, publicering og hele sessionens forbrug hævdes ikke fuldt målt. 0 DKK, 0 nye teleskopforespørgsler og 0 nye teleskopbytes.

Original A/B er fortsat **FAIL_CLOSED**. Den fulde seks-scan-kædes recovery-, RFI- og null-gates er ikke testet eller bestået her. Beskyttede 2016-data og den lukkede 2019-rute bevarer deres status; slutcheckpointet er 20. oktober 2026.

[Frosset scope](SCOPE.json) · [Resultater](results/SUMMARY.json) · [Uafhængig QA](results/QA_RECEIPT.json) · [270 lokale kandidater](results/OBSERVED_TOP5.csv) · [Reproduktion](README.md).
