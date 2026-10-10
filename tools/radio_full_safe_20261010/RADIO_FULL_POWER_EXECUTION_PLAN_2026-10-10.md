# SETI: fuld søgning i det sikre gemte frekvensudsnit

**10. oktober 2026 · Godkendt til klargøring og udførelse · Numeriske kørsler endnu ikke startet**

Den relevante del af Martins instruks den **10. oktober 2026 kl. 15:43:25 dansk tid** er:

> Du kører bare på full power. Vi skal igennem en masse data for bare at have en lille chance for success.

Instruksen aktiverer den allerede udarbejdede søgning i **214 resterende sikre delbånd**, fordelt på **107 + 107**, og autoriserer videre arbejde med de tilgængelige ressourcer til **0 kr.**

Den tidligere projektgrænse på 12 CPU-timer var en planlægningsgrænse i vores egen plan. Den beskriver ikke OpenAI-abonnementets forbrug eller restbalance. Det samme gælder det tidligere reservationsregnskabs 2,705144981 resterende CPU-sekunder. Den seneste brugerinstruks erstatter denne interne stopgrænse. Den nye fase har en **planlægningsallokering på 3.600 CPU-sekunder** til to konkrete analyser og deres kontrol og publicering; den er ikke en ny samlet kontogrænse. Vi indfører ikke nye godkendelsesstop alene ved udløbet af denne allokering, så længe fortsat arbejde ligger inden for den aktuelle autorisation til gratis ressourcer. Historiske reservationer og tidligere dokumenter bevares uden tilbageførsel.

## Det aktiverede udvalg

Udvalget er identisk med det tidligere offentlige metadataforslag. Delbånd har 4.096 referencekanaler og relativ start `q × 4096`. De sikre q-værdier er **1–254**. De tidligere 32 felter bruger `q = 1 + 8j`, hvor j=0…31; de otte efterfølgende bruger `q = 5 + 8k`, hvor k=[0,4,8,12,16,20,24,28]. De resterende 214 q-værdier er sorteret og delt i to uforanderlige grupper på 107 før nye udfald: første gruppe q=2…127 med de allerede søgte felter udeladt, anden q=128…254 med samme udeladelse.

Alle q-værdier og fysiske kanalintervaller står i `ACTIVATION_SCOPE.json`. Den kanoniske udvalgshash er **`81bdd9b01d32c5d1fffd54df30d036a2aab29035c8d9e29d21b564e166d67120`**. Begge grupper fastlåses før første kørsel og ændres ikke efter resultater fra den første.

Hvis begge kørsler gennemføres, tilføjes **876.544 referencekanaler pr. ON-scanning** og **642 scanningsfelter**. De tidligere og nye felter dækker samlet **1.040.384 af 1.048.576 referencekanaler, 99,21875 %**, i det gemte udsnit. Referenceintervallet bliver det sammenhængende sikre indre `[4096, 1044480)`; de to randfelter `[0,4096)` og `[1044480,1048576)` forbliver usøgte.

Den eksisterende halo på 4.000 kanaler bevares. Første sikre halo begynder ved relativ kanal 96; sidste slutter ved 1.048.480, 96 kanaler før udsnittets slutning. De faktiske tider i alle seks scanninger giver ved ±4 Hz/s en konservativ maksimal projiceret forskydning på 2.707 kanaler. Med profiludsnittenes ±64 er grænsen 2.771, under haloen. Profiludsnit er derfor geometrisk mulige for alle sikre referencekanaler. Faktisk gyldighed kontrolleres fortsat i outputs.

## Uændret søgning og gemte resultater

Detektoren er uændret: **763 lineære drifthastigheder fra −4 til +4 Hz/s ved bredde 1 og 3**, 1.526 hypoteser pr. referencekanal. Hver ON bruger sit eget første integrationsmidtpunkt. Der ændres ikke i normalisering, 501-kanals medianfilter, MAD-skala, winsorisering, score, tie-regler eller top-20-afstandsundertrykkelse på tre kanaler. Eksakte kode- og afhængighedshashes står i aktiveringsscopet; den endelige wrapper og kørselskontrakt gennemgås og offentliggøres før udførelse.

Hvert afsluttet felt gemmer samtlige 4.096 maksimale scores, vindende drift og bredde samt faktiske gyldige hypoteseantal. Alle tre ON-top-20-lister pr. gruppe bevares. De tre højeste pr. ON projiceres ved uændret frekvens, drift og bredde i alle seks scanninger: **ni profiler pr. gruppe, 18 ved to afsluttede grupper**. Alle 16 tidsrækker gemmes. Der foretages ingen frekvensforskydning, retuning eller optimering efter OFF-data, og der indføres ikke et kvalificeret OFF-veto.

## Arbejdsallokering og faste jobgrænser

| Arbejde | Planlagt CPU-allokering |
| --- | ---: |
| Gruppe 1: 107 delbånd, indlæsning og profiler | 1.200 sekunder |
| Gruppe 2: 107 delbånd, indlæsning og profiler | 1.200 sekunder |
| Klargøring, eventuel gendannelse og miljø | 400 sekunder |
| Uafhængig resultatkontrol | 400 sekunder |
| Pakning og offentliggørelse | 400 sekunder |
| **Fasen i alt** | **3.600 sekunder** |

Hver numerisk kørsel har en konkret grænse på **1.200 CPU-sekunder, 1.800 sekunders vægtid og 4 GiB RAM**. Den køres højst én gang. Det er et driftsværn for en afgrænset kørsel, ikke et estimat af abonnementsforbrug. Delvise resultater bevares ved fejl eller overskridelse og mærkes ufuldstændige; den samme kørsel gentages ikke. Den seneste otte-felts kørsel brugte 73,861583 CPU-sekunder. En enkel lineær fremskrivning giver cirka 988 sekunder pr. gruppe; det er et skøn, og gennemførelse bekræftes først af målte resultater.

Beløbet forbliver **0 kr.**, RAM-grænsen **4 GiB**, arbejdspladsgrænsen **8 GiB**, og den samlede grænse for modtagne kilde-, gendannelses-, afhængigheds- og metadata-bytes **4,25 GiB (4.563.402.752 bytes)**. Der bruges gemte kompakte HDF5-filer: **0 nye teleskoprequests og 0 nye teleskopbytes** i denne fase. Eksisterende verificerede input og codecs genbruges. Ved nødvendig gendannelse kontrolleres eksakte identiteter og det kumulative byteregnskab før overførsel. Brugerens instruks autoriserer ingen betalte maskiner, nye betalinger, teleskopbooking eller beskeder til andre.

Før de numeriske kørsler skal præcis wrapper og endeligt scope have uafhængig statisk kontrol, offentlig fastlåsning og eksakt læsning tilbage. Hver kørsel verificerer kompakte filhashes og alle 96 afkodede rækkers hashes med den uændrede loader. Resultatkontrollen gennemgår alle kanalmaxima og gyldige hypoteseantal, ranglister og faste profiler uden at gentage detektorsøgningen. Kode, rapporter, kontroller, figurer og reproduktionsvejledning publiceres og gemmes samlet. Ingen af disse trin udgør en ny tilladelsesrunde for det allerede autoriserede arbejde.

## Videnskabelig rækkevidde

Alle seks scanninger tilhører stadig **ét historisk besøg den 17. marts 2016**. Der tilføjes ingen ny observation. Kildeværdierne har tidligere været åbnet; udvalget er prospektivt for de nye driftudfald, og arbejdet er eksplorativt. **99,21875 %** er referencekanaldækning i dette ene udsnit for dette grid og disse bredder, ikke survey-komplethed eller dokumenteret følsomhed.

A/B forbliver **FAIL_CLOSED**, den kvalificerede himmelpilot forbliver blokeret, og tidligere holdouts forbliver lukkede. Ingen profil får automatisk himmel- eller oprindelsesklassifikation. Topscorer og profiler er efter udvælgelse og giver ikke kalibreret falskalarmrate, SNR, flux, EIRP eller følsomhed. Læse- og sporhaloer kan overlappe; kanaler og profiler erklæres ikke uafhængige forsøg. Små værdier ved et præcist OFF-spor fastslår ikke fravær af nærliggende OFF-struktur. Der tilføjes ikke barycentrisk korrektion, ikke-lineære spor, andre bredder eller injektionskalibrering.

Grundlaget er læst fra den offentlige gren ved **`0448a21297d9eef4adc54fab7b321185ce53c1da`**. Det tidligere forslag og den oprindelige plan bevares som historik; dette dokument registrerer den senere, eksplicitte brugerinstruks og den aktiverede udførelse. Det dokumenterer endnu ingen gennemført numerisk kørsel.
