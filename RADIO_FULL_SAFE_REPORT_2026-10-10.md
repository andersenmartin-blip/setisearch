# SETI: driftsøgning i det sikre gemte frekvensudsnit

**10. oktober 2026.** Begge fastlåste kørsler er gennemført én gang.
Der er gemt **642 af 642 scanningsfelter** og **18 af 18 faste top-3-profiler**. Grupperne har hver deres ranglister; profilidentiteten er kombinationen af gruppe og track-ID.

Alle seks scanninger stammer fra ét besøg den 17. marts 2016. Dette er eksplorativ analyse af allerede eksponerede data med 763 lineære drifthastigheder fra −4 til +4 Hz/s og bredde 1 og 3. A/B er fortsat FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og gamle holdouts er lukkede.

## Dækning og kontrol

| Gruppe | Gemte felter / 321 | Faste profiler / 9 | Kørselsstatus | Uafhængig QA |
| --- | ---: | ---: | --- | --- |
| 1 | 321 | 9 | COMPLETE_107_FULL_SAFE_CORE_BATCH_EXPLORATORY_ONLY | PASS_COMPLETE_SAVED_BATCH_OUTPUTS |
| 2 | 321 | 9 | COMPLETE_107_FULL_SAFE_CORE_BATCH_EXPLORATORY_ONLY | PASS_COMPLETE_SAVED_BATCH_OUTPUTS |

En særskilt kildecellekontrol matcher **alle 222.912 råceller i 18 profiludklip byte for byte** mod de seks hashkontrollerede kompakte HDF5-kilder. Kontrollen omfatter 96 afkodede kilderækker, 108 scanningsprofiler og 1.728 profilrækker. Den bekræfter udklippenes råcelleidentitet og placering. De originale større kilders fulde fil-MD5 er fortsat ikke verificeret.

| ON | Tidligere + nye gemte referencekanaler | Andel af udsnittet |
| --- | ---: | ---: |
| ON1 | 1.040.384 | 99,21875 % |
| ON2 | 1.040.384 | 99,21875 % |
| ON3 | 1.040.384 | 99,21875 % |

De gemte checkpoints dokumenterer, at **2.629.632 ON-referencekanal/originkombinationer** er evalueret med **1.526 gyldige grid-/breddehypoteser hver**, i alt **4.012.818.432 hypotesekombinationer**. For hver referencekanal gemmes scoremaksimum, vindende drift og bredde samt det verificerede hypoteseantal.
Disse tællinger er beregningsdækning, ikke uafhængige statistiske forsøg.
Ved to komplette kørsler er den samlede referencekanaldækning **254 af 256 felter, 99,21875 %**, inklusive de tidligere 40 felter. Kun dette grid og disse to bredder er omfattet. Randfelterne [0,4096) og [1044480,1048576) er usøgte; læse- og sporhaloer kan overlappe.
Endelig integritetskontrol fremgår af QA-kvitteringerne; denne sammenfatning genkører ikke detektoren og åbner hverken rå HDF5 eller NPZ.

## Hvad de højeste profiler viser

De 18 profiler er udvalgte spor og udgør ikke 18 uafhængige fysiske signaler. Deres referencefrekvenser samler sig i to snævre områder:

| Gruppe | Udvalgte spor | Native q | Referencefrekvensinterval, MHz |
| --- | ---: | --- | ---: |
| 1 | 9 | 64 | 1426,757801–1426,757824 |
| 2 | 9 | 215 | 1425,004485–1425,004524 |

Den højeste profil i alle tre ON-scanninger i gruppe 1 bruger samme stationære reference ved **1426,757812 MHz**. Dens gemte middelresidualer er **3,755606–3,924245** på tværs af alle seks scanninger. Den stærke stationære struktur er dermed til stede i både alle ON- og alle OFF-scanninger. Det fastslår ikke dens oprindelse. De seks profiler med drift forskellig fra nul i gruppe 1 har denne stationære kanal uden for deres trekanals centrum i alle 288 OFF-rækkeforekomster, men inden for hvert gemt ±64-kanals udklip, med en afstand på 2–32 kanaler. Små værdier på driftsporet kan derfor eksistere samtidig med den stærke stationære OFF-struktur.

Gruppe 2 indeholder også markant struktur på flere af de faste OFF-forløb; de præcise middelværdier for hver profil står nedenfor. Nærliggende profiler og gentagne udvælgelser af samme struktur er afhængige beskrivelser.

## De gemte faste profiler

Tallene nedenfor er gemt normaliseret centereffekt minus rækkens median af bevægelige flankkanaler med absolut offset større end tre inden for ±64. De er ikke kalibreret SNR. Alle OFF-værdier følger den oprindeligt valgte, uændrede driftmodel ved de faktiske scanningstider. ON2 og ON3 vises med både den forudgående og efterfølgende OFF; ON1 har kun den efterfølgende OFF i denne seks-scans sekvens. Alle seks scanningsforløb bevares i sammenfatningsfilen. Detektorens robuste rangscore og profilens middelresidual er forskellige størrelser.

| Gruppe | ON/rang | Frekvens, MHz | Drift, Hz/s | Bredde | ON-middel | OFF før | OFF efter |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | ON1/1 | 1426,757812 | 0,000000 | 1 | 3,796242 | — | 3,853003 |
| 1 | ON1/2 | 1426,757801 | 0,052493 | 3 | 0,640392 | — | -0,002202 |
| 1 | ON1/3 | 1426,757824 | -0,052493 | 3 | 0,641279 | — | 0,016833 |
| 1 | ON2/1 | 1426,757812 | 0,000000 | 1 | 3,796472 | 3,853003 | 3,924245 |
| 1 | ON2/2 | 1426,757801 | 0,052493 | 3 | 0,649523 | -0,024970 | -0,008953 |
| 1 | ON2/3 | 1426,757824 | -0,052493 | 3 | 0,647762 | 0,028743 | -0,017322 |
| 1 | ON3/1 | 1426,757812 | 0,000000 | 1 | 3,848509 | 3,924245 | 3,755606 |
| 1 | ON3/2 | 1426,757801 | 0,052493 | 3 | 0,639947 | 0,004026 | -0,009879 |
| 1 | ON3/3 | 1426,757824 | -0,052493 | 3 | 0,622156 | -0,015916 | 0,026899 |
| 2 | ON1/1 | 1425,004496 | 0,000000 | 3 | 1,581854 | — | 1,009708 |
| 2 | ON1/2 | 1425,004485 | 0,062992 | 3 | 0,948542 | — | 0,239236 |
| 2 | ON1/3 | 1425,004507 | -0,041995 | 3 | 0,927393 | — | 0,311938 |
| 2 | ON2/1 | 1425,004504 | 0,031496 | 3 | 1,484933 | 1,412548 | 0,783236 |
| 2 | ON2/2 | 1425,004516 | -0,020997 | 3 | 0,935458 | 0,417606 | 0,616498 |
| 2 | ON2/3 | 1425,004493 | 0,094488 | 3 | 0,905616 | -0,006222 | 0,187679 |
| 2 | ON3/1 | 1425,004513 | 0,000000 | 3 | 1,573156 | 1,559645 | 1,577535 |
| 2 | ON3/2 | 1425,004524 | -0,052493 | 3 | 1,002133 | 0,837941 | 0,149600 |
| 2 | ON3/3 | 1425,004502 | 0,062992 | 3 | 0,939651 | -0,019308 | 0,306839 |

Profilerne er udvalgt efter ON-score inden for hver gruppe. De forbliver uafklarede. Positive rækker og halvdele er efter udvælgelse; en lille værdi ved et præcist OFF-spor fastslår ikke fravær af en nærliggende OFF-feature. Der er ingen optimeret OFF-forskydning eller kvalificeret OFF-veto og ingen oprindelsesklassifikation.

## Målt kørsel

| Gruppe | CPU, sekunder | Vægtid, sekunder | Maksimal RSS, bytes |
| --- | ---: | ---: | ---: |
| 1 | 981,484 | 981,776 | 606896128 |
| 2 | 1005,745 | 1006,141 | 609185792 |

Hver numerisk kørsel har højst 1.200 CPU-sekunder, 1.800 sekunders vægtid og 4 GiB RAM. Fasens 3.600 CPU-sekunder er arbejdsplanlægning, ikke en abonnementsbalance eller ny global stopgrænse. Historiske reservationer bevares uden tilbageførsel. Beløbet er 0 kr., og fasen har 0 nye teleskoprequests og 0 nye teleskopbytes. Arbejdsplads- og kumulative byteregnskaber føres særskilt af projektets ressourceledger.

## Begrænsninger og reproduktion

Kildeværdierne var allerede åbnet. Den prospektive fastlåsning vedrører de nye driftudfald; arbejdet er hverken blind validering eller en ny uafhængig besøgsobservation. Der er ikke beregnet kalibreret falskalarmrate, flux, EIRP eller følsomhed, og der påstås hverken generelt nulresultat eller uafhængighed mellem hypoteser. Ingen barycentrisk korrektion, ikke-lineære spor, andre bredder eller injektionskalibrering er tilføjet.
Kode og fælles kørselscope blev fastlåst offentligt i commit `73168f5f1b2d9d154b10eb381c17b8185c18a880` og læst eksakt tilbage før nogen af de to kørsler. Scope-SHA256 er `1e77f78f5c957082da3eebdb1c70641b6ba7687ce2996578ccb5a9caf0287d22`. De kompakte inputfiler og 96 afkodede rækker er hashbundne; de originale større kilders fulde fil-MD5 er ikke verificeret. Det begrænser filproveniensen og ændrer ikke de deklarerede lokale checksums.
Eksakte scopes, begge checkpoints, top-20-lister, profiler og kørsels-/QA-kvitteringer følger resultatpakken. Sammenfatningskvitteringen angiver hash og størrelse for hvert faktisk læst JSON-input. Publiceringscommit og pakkens endelige checksum tilføjes i projektstatus efter gemning og verificeret offentliggørelse.
