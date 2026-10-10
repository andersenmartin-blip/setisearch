# Forslag: søg resten af det sikre frekvensudsnit

**10. oktober 2026 · IKKE GODKENDT · IKKE KØRT**

Forslaget er at bruge **3.600 ekstra CPU-sekunder (én time)** på en driftsøgning i de **214 resterende sikre delbånd** i de allerede gemte teleskopdata. Hvis begge planlagte kørsler gennemføres, vokser dækningen af referencekanaler fra **15,625 % til 99,21875 %** af det ene native frekvensudsnit. De to yderste delbånd forbliver usøgte. Dette er et konkret forslag til godkendelse; dokumentet reserverer ingen ny CPU-tid og starter ingen analyse.

Den hidtil godkendte CPU-ramme er 43.200 sekunder, svarende til 12 timer. Forslaget kræver, at brugeren godkender en udvidelse til **46.800 sekunder, svarende til 13 timer**. Efter den aktuelle statiske kontekstkontrol er der kun **2,705144981 CPU-sekunder** tilbage under den eksisterende reservationsmodel. Tidligere reservationer bevares uden tilbageførsel; den nye aktivitet kan derfor først begynde efter udtrykkelig godkendelse. Den gældende planperiode slutter fortsat 20. oktober 2026.

## Den præcise søgning

Hvert delbånd har 4.096 referencekanaler. Sæt den relative start til `q × 4096`. Med den eksisterende læsehalo på 4.000 kanaler er **q = 1 til 254** geometrisk mulige inden for det gemte udsnit på 1.048.576 kanaler. Første halo begynder ved relativ kanal 96. Sidste delbånd er `[1040384, 1044480)`, og dets halo slutter ved 1.048.480, altså 96 kanaler før udsnittets afslutning.

De tidligere 32 delbånd bruger `q = 1 + 8j`, hvor `j = 0…31`. De otte senest søgte bruger `q = 5 + 8k`, hvor `k = [0,4,8,12,16,20,24,28]`. De to lister overlapper ikke. Derfor resterer **254 − 32 − 8 = 214** delbånd. Listen sorteres efter q og deles på forhånd i to kørsler på 107 delbånd: første kørsel går fra q=2 til q=127 med de tidligere søgte delbånd udeladt; anden går fra q=128 til q=254 med samme udeladelse. Samtlige q-værdier og fysiske kanalintervaller er angivet i `PROPOSAL.json`. Deres kanoniske metadataudvalg har SHA256 `81bdd9b01d32c5d1fffd54df30d036a2aab29035c8d9e29d21b564e166d67120`.

Den uændrede detektor undersøger fortsat **763 lineære drifthastigheder fra −4 til +4 Hz/s ved bredde 1 og 3**, altså 1.526 hypoteser pr. referencekanal. Hver ON-scanning bruger sit eget første integrationsmidtpunkt som reference. Den største uafrundede forskydning inden for 16 rækker er cirka 380,593 kanaler; den eksisterende halo på 4.000 bevares. Faktisk gyldighed skal alligevel verificeres i resultatfilerne: geometri alene erstatter ikke kontrollen af alle 1.526 gyldige hypoteser pr. kanal.

De faste top-3-profiler projiceres desuden over alle seks scanninger ved deres faktiske header-tider. Den største absolutte tidsafstand fra en ON-reference til en gemt række er **1918.793361407 sekunder**. Ved ±4 Hz/s svarer det til højst **2706.811565 uafrundede kanaler**, konservativt begrænset til **2707 afrundede kanaler**. Med udklippets ±64 kanaler er den samlede grænse **2771 kanaler**, under den eksisterende halo på 4.000. Selv de yderste sikre referencekanaler får således gyldige profiler i alle seks scanninger: en konservativ samlet projektionsgrænse er relativ kanal **1325 til 1047250**, begge inklusive, inden for det gemte udsnit. Alle faktiske scanningsmidtpunktgrænser står i `PROPOSAL.json`.

Detektorens normalisering, 501-kanals medianfilter, empiriske MAD-skala, score, bredder, grid, tie-regler og top-20-afstandsundertrykkelse på tre kanaler ændres ikke. De tidligere 40 delbånd og deres resultater bevares uændrede. De nye 214 delbånd svarer til **876.544 nye referencekanaler pr. ON-scanning**, fordelt over tre ON-scanninger. Alle **642 nye scanningsfelter** gemmer samtlige 4.096 maksimale scores samt vindende drift, bredde og gyldige hypoteseantal.

Hver kørsel bevarer top-20-listen for hver ON og projicerer de tre højeste profiler pr. ON ved uændret frekvens, drift og bredde i alle seks scanninger. De **ni profiler pr. kørsel** bruger den hidtidige faste udklipsbredde ±64, de allerede gemte fulde rækkemedianer og ingen efterfølgende frekvensforskydning. Alle profiler og ranglister er beskrivelser efter udvælgelse. Der indføres ikke et kvalificeret OFF-veto.

## Ressourcer og gennemførelse efter godkendelse

| Aktivitet | CPU-sekunder |
| --- | ---: |
| Første 107 delbånd inklusive indlæsning og profiler | 1.200 |
| Anden 107 delbånd inklusive indlæsning og profiler | 1.200 |
| Klargøring, eventuel gendannelse og miljø | 400 |
| Uafhængig resultatkontrol | 400 |
| Pakning og offentliggørelse | 400 |
| **I alt** | **3.600** |

Den seneste kørsel brugte 73,861583 CPU-sekunder på otte delbånd inklusive fælles indlæsning og ni profiler. En enkel lineær fremskrivning giver cirka **988 CPU-sekunder pr. 107 delbånd**. Det er et planlægningsskøn, ikke en garanti; grænsen på 1.200 sekunder giver plads til variation. Hver numerisk kørsel får højst **1.800 sekunders vægtid og 4 GiB RAM**. Arbejdspladsgrænsen forbliver **8 GiB**, beløbet **0 DKK**, og den samlede kildegrænse **4,25 GiB (4.563.402.752 bytes)**.

Der bruges kun tidligere gemte kompakte HDF5-filer. **Nye teleskoprequests: 0. Nye teleskopbytes: 0.** Eksisterende lokale input og miljø genbruges, når de er tilgængelige. Hvis tidligere arbejdsfiler er ryddet, kan det kræve gendannelse af gemte arkiver og eksakte afhængigheder. Op til to gendannelser af det kendte RAW-arkiv svarer til 610.857.414 arkivbytes; det foreløbige øvre skøn for fremtidig gendannelse og afhængigheder er 700.000.000 bytes. Det samlede regnskab skal beregnes fra de aktuelle kvitteringer inden hver overførsel og forblive under den eksisterende kildegrænse. Skønnet er ikke en verificeret slutmåling.

Efter godkendelse fastlåses de to delbåndslister før nye resultater, og præcis kode samt endeligt scope får uafhængig gennemgang, offentlig fastlåsning og eksakt læsning tilbage før kørsel. Kompakte filhashes og alle 96 afkodede rækkers hashes kontrolleres. Hver kørsel gennemføres højst én gang. Ved fejl eller overskridelse bevares allerede afsluttede felter og markeres ufuldstændige; der genkøres ikke for at få et bedre udfald. Resultater, kontroller, figurer, kode og reproduktionsvejledning offentliggøres og gemmes samlet.

## Videnskabelig betydning og begrænsning

Udvidelsen flytter indsatsen fra udvalgte delbånd til næsten hele det geometrisk sikre indre af det samme gemte udsnit. **99,21875 %** beskriver dækning af referencekanaler for netop dette grid og disse to bredder; det er hverken fuldstændig survey-dækning eller dokumenteret følsomhed. Det manglende randareal er `[0,4096)` og `[1044480,1048576)`, tilsammen 8.192 referencekanaler.

Alle seks scanninger tilhører fortsat **ét besøg den 17. marts 2016**. Dataværdierne er allerede blevet åbnet i tidligere arbejde. Nye driftresultater er fremtidige, men kildeinput er ikke blinde eller uafhængige. Læse- og sporhaloer samt korreleret signalstruktur kan overlappe. Topscorer og profiler giver ingen kalibreret falskalarmrate, SNR, flux, EIRP eller følsomhed, og der fremføres ikke et generaliseret nulresultat eller en oprindelsesklassifikation. Små værdier ved et forudsagt OFF-spor fastslår ikke fravær af nærliggende OFF-struktur.

A/B forbliver **FAIL_CLOSED**, den kvalificerede himmelpilot forbliver blokeret, og tidligere holdouts forbliver lukkede. Forslaget tilføjer ikke barycentrisk korrektion, ikke-lineære spor, andre bredder, injektionskontrol eller falskalarmkalibrering.

**Godkendelsestekst:** Godkender du 3.600 ekstra CPU-sekunder (én time) til at søge de resterende 214 sikre delbånd i de allerede gemte data? Det vil udvide den samlede CPU-ramme fra 12 til 13 timer; beløbet forbliver 0 kr., og øvrige grænser ændres ikke.
