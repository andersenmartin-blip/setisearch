# SETI BG — signalsøgningen er gennemført igen

29. oktober 2026. **En reel søgning på de gemte 2017-data er afsluttet med exitkode 0.** De otte på forhånd valgte bånd er gennemsøgt i alle seks scans, efterfulgt af en bestået, afgrænset resultatkontrol. Berkeley-arkivet blev ikke kontaktet.

Den praktiske løsning er nu afprøvet: brug de fuldt gemte rådata og gennemfør afgrænsede søgebatches, mens den ufuldstændige HIP44295-hentning holdes på pause. Beregningsmiljøet blev tilgængeligt igen i denne arbejdsrunde.

## Faktisk udført

| Størrelse | Resultat |
|---|---:|
| Datasæt | HIP98505 / HD189733, 28. april 2017 |
| Scans | 3 ON + 3 OFF fra samme historiske besøg |
| Faste bånd | native171, q1–q8 |
| Carrierkanaler | 32.768 |
| Frekvenscentre | 2301,752475–2301,844025 MHz |
| Teknisk kanalbredde i alt | 91,553 kHz |
| Tidsrækker pr. scan | 16 |
| Søgebredder | 1, 3, 9 og 33 kanaler |
| Driftgrid | 839 trin over ±4 Hz/s |
| Scan/bånd-søgninger | 48 |
| Korrelerede sporkombinationer, inklusive OFF | **433.004.544** |
| Faktisk køretid | **157,93 sekunder** |
| ON-spor over den faste ESS-tærskel 10 | **0** |
| Nye arkivanmodninger | **0** |

Sporkombinationerne er korrelerede beregninger, ikke så mange uafhængige statistiske prøver. De cirka 92 kHz er det undersøgte område; det fulde native input blev anvendt til normalisering, ikke til en ny søgning i alle frekvenser.

## Resultat

Ingen ON-spor nåede den fastlagte lokale ESS-tærskel. Der var derfor **ingen udløste spor at måle på tværs af ON/OFF**, og antallet af sådanne målinger er nul. Tomme katalogers beståede konsistenskontrol er ikke et selvstændigt fysisk ON/OFF-resultat.

| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |
|---:|---:|---:|
| 1 | 5,823 | 5,687 |
| 3 | 5,819 | 5,880 |
| 9 | 5,404 | 5,551 |
| 33 | 5,417 | 5,387 |

ESS er en empirisk score. Den må ikke læses som en kalibreret sigma-værdi, SNR eller falsk-alarm-sandsynlighed. Ingen ny SETI-kandidat er kvalificeret ved denne søgning.

## Metode og kontrol

Rådatapakken på 466.351.822 bytes blev hentet fra den eksisterende sikkerhedskopi. Arkivhash, ZIP-CRC og alle 592 payload-filers hashes blev kontrolleret. Kun de seks komplette recovery-HDF5-filer blev anvendt; de tidligere delvise staging-filer blev ikke brugt.

Den oprindelige AC-normalisering blev beregnet over hele hver native-række. Den uændrede sporkernel søgte derefter de otte faste bånd. **ESS blev kalibreret lokalt i hvert 4096-kanalers bånd for hvert drifttrin, hver bredde og hvert scan.** Det er en udtrykkeligt beskrivende ny analysefamilie på tidligere eksponerede data, ikke en identisk genkørsel af den historiske full-native ESS. De oprindelige klassifikationer og beskyttede holdouts ændres ikke.

Plan, inddata og kode blev fastholdt på GitHub før beregningen. Første start stoppede med exit 1 før rådataværdier blev læst, fordi en ny metadatakontrol brugte et forkert feltnavn. En særskilt V2 rettede kun attributnavnet; søgeberegningen blev ikke ændret. Både den første kildekode, plan og fejllog er bevaret.

V2 sluttede med faktisk exit 0, registreret stdout-EOF, afsluttet procesventning og identiske observerede/gemte loghashes. Resultatkontrollen sluttede også med faktisk exit 0. Den verificerede alle 48 søgningers output og optællinger, **1.728 udvalgte sporsummer med uafhængig `math.fsum`** samt **576 kalibreringsgenberegninger**. De største observerede afvigelser var 0. Kalibreringsgenberegningerne deler sporkernelen; kontrollen er ikke en uafhængig genberegning af alle 433 millioner hypoteser.

## Bogføring og fortsættelse

Dette er genanalyse af ét historisk besøg. Der tilføjes ingen nye observationer, arkiv-ID'er eller dækning til den tidligere BA-opgørelse på 486 ID'er og 268,50128173828125 tekniske MHz-besøg. Der er ingen kalibreret astronomisk følsomhed, global falsk-alarm-sandsynlighed eller oprindelsesbestemmelse.

HIP44295 bevares med 88 af 96 rækker og afventer fortsat normal arkivadgang. Det blokerer nu ikke genanalyse af de gemte data. Næste naturlige batch er de efterfølgende sammenhængende bånd, fastlagt i en ny plan før beregning og med de allerede afsluttede q1–q8 bevaret. Ingen beregning fortsætter i baggrunden efter denne aflevering.

## Reproduktion

- [Fastlåst V2-plan](work_bg/PLAN_BG_V2.json) og [søgekode](work_bg/bounded_search_bg_v2.py)
- [Præregistreret V2-kode og plan](https://github.com/andersenmartin-blip/setisearch/commit/33dd463b62939ce0321c461794ae8531d1404a85)
- [Samlet resultat](work_bg/results/REAL_SEARCH_SUMMARY_BG.json)
- [Faktisk procesafslutning](work_bg/execution_v2/SEARCH_ACTUAL_EXIT_BG_V2.json)
- [Uafhængig, afgrænset resultatkontrol](work_bg/review/REAL_RESULT_AUDIT_BG_V2.json)
- [Datapakke og fortsættelsespunkt](work_bg/DELIVERY_BG.json)

De binære score-, kalibrerings-, normaliserings- og katalogfiler er bevaret i den separate resultatpakke. Råkilderne og programkoden er ikke duplikeret i den pakke.
