# SETI: verificeret 2017-søgning, 10. oktober 2026

Søgningen i det indhentede S-båndsudsnit fra **28. april 2017** er afsluttet og kildekontrolleret. Den omfatter **4.900.208.640 korrelerede drift-/breddekombinationer**, inklusive det tidligere afsluttede første felt. Der er fortsat **ingen kvalificeret SETI-detektion**.

| Afsluttet søgning | Forskellige referencefelter pr. ON | Gemte ON-kort | Evaluerede kombinationer |
|---|---:|---:|---:|
| Første felt, q128 | 1 | 3 | 19.292.160 |
| Nye batch 01 og 02 | 168 | 504 | 3.241.082.880 |
| Ny batch 03 | 85 | 255 | 1.639.833.600 |
| **I alt** | **254** | **762** | **4.900.208.640** |

Det er **99,21875 % af de 256 referencefelter i ét native frekvensudsnit** på 2,9296875 MHz, omtrent 2298,926–2301,855 MHz. De to yderste referencefelter er udeladt. Procenten beskriver referencekanaler; den er ikke en målt følsomhed, komplet dækning af teleskopets bånd eller sandsynlighed for at finde et signal. Der er én historisk observation med tre ON/OFF-par, og maksimummerne over drift og bredde er afhængige.

Alle tre nye batches har faktisk COMPLETE-status. Den samlede QA har faktisk PASS-status for **759 kort, 27 faste profiler og 334.368 råcelleforekomster**, som matcher kilden bit for bit. Med q128 omfatter de faste profiler 36 cases, 216 scan-profiler og 445.824 kontrollerede råcelleforekomster. Det er forekomster, ikke nødvendigvis forskellige fysiske celler.

Den nye observations seks komplette kildefiler indeholder **100.663.296 float32-celler** og 96 autentificerede rækker. q128-kontrollen genmålte alle 96 fulde række-medianer. Den nye batchkontrol autentificerede disse medianer og genmålte kerne-medianerne for alle 759 kort; den genkørte ikke detektorscorerne. En særskilt gennemgang binder alle 1.545 nye måle-/normaliseringsfiler til SHA256 og størrelse samt de faktiske COMPLETE-/QA-kvitteringer til fastlåst kode og scopes. Hele de oprindelige teleskopfiler har fortsat ikke verificeret MD5.

## Hvad resultaterne viser

De største scorer ligger ved den stationære struktur omkring **2300,390625 MHz**, som er stærk i alle seks ON- og OFF-scanninger. Batch 02's største scorer bruger en bredde på tre kanaler med center én kanal ved siden af den allerede kendte q128-struktur. Boksen kan derfor indeholde den samme fysiske struktur, selv om referencecentrene er nye. Det etablerer ikke et nyt, uafhængigt signal.

Flere højt rangerede bevægende bokse rammer også den stationære struktur senere i deres oprindelige ON-scan. De store rangscorer er derfor ikke i sig selv bevis for et bevægende signal på himlen. Batch 01 og 03 har svagere udvalgte profiler med primært overskud i udvælgelsens ON-scan; deres øvrige faste ON/OFF-profiler etablerer ingen kvalificeret gentaget himmelkilde.

Scorerne er **ikke kalibreret SNR, falsk-alarm-sandsynlighed, flux eller EIRP**. Der hævdes ingen generel nuldetektionsgrænse, kvalificeret OFF-veto eller bekræftelse af de tidligere L-båndsspor ved samme frekvens. De oprindelige A/B-fejl og beskyttede holdouts er uændrede.

## Ressourcer og bevaring

Den nye udvidelse genbrugte de komplette 2017-kildefiler: **0 nye teleskop-GETs, 0 nye teleskop-BODY-byte og 0 DKK**. De tre numeriske processer brugte tilsammen 1.402,763934233 process-CPU-sekunder; den samlede QA brugte 4,464805467 sekunder. Tallene gælder disse numeriske processer og den særskilte QA.

Den oprindelige 2017-indhentnings HDF5-fejl og dens partialfiler er bevaret. Recovery genbrugte 27 modtagne blokke og hentede kun 69 endnu ikke forsøgte blokke. Hele 2017-payloaden er 298.238.620 BODY-byte, uden gentagne teleskop-GETs. Den oprindelige fejl omklassificeres ikke.

Eksakte afslutnings- og QA-kvitteringer findes i `receipts/`; det eksisterende, gennemgåede resumé findes i `summary/FULL_BAND_SUMMARY.json`. Scope og kode blev fastlåst før udvidelsen i commit `76fb1da5a0af22d6182daed90e4bdca92f2470f8`. Det historiske grænsesnapshot er særskilt bevaret i commit `04db46b92e86cf695255992611d186274b44e919`.

Dette tillæg opdaterer den faktiske søgestatus. Den tidligere rapports ordlyd fra før q128-/batchkontrollen er bevaret uændret og mærket som et historisk snapshot.
