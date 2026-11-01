# HARPS extension02: gennemført og kontrolleret

Alle **100 nye eksponeringer** er hentet, metadatakontrolleret og analyseret med de uændrede, frosne V1- og V2-algoritmer. Udvidelsen giver **6 V1-træf og 336 V2-profiltræf**. De er foreløbige søgetræf; dette er ikke identifikationer af lasere.

## Omfang og samlede tal

De nye data dækker 16 mål og 86.849,578 sekunders observation (**24,124883 timer**). Der er ingen genbrugte ADP-ID'er, rå eksponeringer eller mål/starttidskombinationer fra de 209 tidligere hoved-, udviklings- og valideringsinputs. Alle 100 frosne eksponeringer blev analyseret; ingen blev erstattet eller udeladt.

| Delmængde | Hovedeksponeringer | V1-træf | V2-profiltræf |
|---|---:|---:|---:|
| Oprindelig hovedserie | 100 | 10 | Ikke kørt |
| Første udvidelse | 100 | 6 | 333 |
| Extension02 | 100 | 6 | 336 |
| Total for den respektive metode | V1: 300; V2: 200 | 22 | 669 |

Projektets hovedserier omfatter nu **300 unikke eksponeringer af 20 forskellige mål**, med samlet eksponeringstid **255.148,743 sekunder = 70,874651 timer**. Udviklings-/valideringsdata er ikke medregnet. De 669 V2-træf stammer fra **200** eksponeringer; V2 er ikke kørt på den oprindelige hovedserie på 100.

De nye 336 events har stabile ID'er `V2E2-0001`–`V2E2-0336` og bevarer `UNREVIEWED` i deres uændrede produktionskatalog. De oprindelige 333 har deres egne opfølgningsresultater. Vi sammenlægger ikke deres forskellige vurderingsstadier til én fælles oprindelsesklassifikation. Nye beskrivende og rådata-baserede opfølgninger ligger separat fra produktionen.

## Prospektiv frysning og hentning

Udvalg, protokol og kode blev publiceret og verificeret **før hentning** ved commit [13bb29d3c3a730cdb50610f4ed46c882e8448cfb](https://github.com/andersenmartin-blip/setisearch/commit/13bb29d3c3a730cdb50610f4ed46c882e8448cfb). `FREEZE.json` har SHA256 `837255ab49b1902f0f6dad8d4b3714d7edd6e68f36ef443b871bd5c4b96c4cbb`. Den oprindelige frosne README, udvælgelse og kode er uændret; denne resultatfil er oprettet efter kørslen.

Hentningen tog **244,42 sekunder** og overførte **526.334.400 response-body-bytes**, under den frosne grænse på 700.000.000 bytes. HTTP/TLS-overhead er ikke med i byteopgørelsen. Hver fil var under 10.000.000 bytes. Der var **103 forsøg: 100 vellykkede og tre HTTP 503-fejl**, hver efterfulgt af ét vellykket forsøg. Fejlforsøgene registrerede nul læste response-body-bytes. Ingen observationer blev udskiftet, og der blev ikke startet en ny uregistreret hentning.

| Eksponering | Første forsøgs fejl | Vellykket forsøg | Endelig headerstatus |
|---|---|---:|---|
| `ADP.2022-05-17T01:02:16.724` | HTTP Error 503: Service Unavailable | 2 | Bestået |
| `ADP.2025-06-08T01:03:30.157` | HTTP Error 503: Service Unavailable | 2 | Bestået |
| `ADP.2025-05-31T01:00:40.760` | HTTP Error 503: Service Unavailable | 2 | Bestået |

Den maskinlæsbare fejlliste er `FAILED_ATTEMPTS.csv`; samtlige forsøg, tider, svarmetadata og filhashes findes i `acquisition/receipts/` og `acquisition/DOWNLOAD_MANIFEST.json`. Root-verificeringen af publiceringen er bevaret som `acquisition/ROOT_PUBLICATION_VERIFICATION.json`.

## Kontroller og analyse

Alle **100/100** filer bestod kontroller for hash, format, instrument, mål, tid, eksponeringstid, position, tilsigtede koordinater, observation/proposal, ADP-ID, præcist rå progenitor-ID fra metadataforespørgslen, bølgelængdeenheder, luftbølgelængde, barycentrisk reference og endelig BERV. Alle **55 frosne kildehashes** stemmer fortsat, inklusive de oprindelige algoritmer, konfigurationer og kataloger.

Den uændrede produktion afsluttede 100/100 inputs uden fejl. V1 søgte i **30.650.654 samples**. V2 søgte i **30.618.855 samples** og bevarede alle **23.242** screenede events: 22.885 afviste, 21 dubletfits og 336 accepterede profiltræf. Selve analyseberegningen tog **14,27 sekunder**. Hentning, filkontroller og efterfølgende vurderinger indgår ikke i denne beregningstid.

Den uafhængige numeriske audit bestod. Den kontrollerede alle 100 inputhashes og headers, identiteter, eksklusioner, bytes, tabelserialiseringer og totalsummer. Den første, midterste og sidste eksponering i den frosne rækkefølge blev genkørt med begge algoritmer: **seks eksakte matches** til gemte fulde resultater og inputmetadata. Auditens genkørsel bruger de samme frosne algoritmer; den er ikke en ny, uafhængigt implementeret detektor. Se `audit/SUMMARY.json`.

## Fortolkning og begrænsninger

Ingen tærskler eller detektorkonfigurationer blev ændret efter adgang til de nye spektraldata. Der er **ingen særskilt følsomhedsmåling for extension02**. De tidligere 192 injektionsforsøg er betingede valideringsresultater og må ikke omfortolkes som denne udvidelses målte følsomhed, fuldstændighed eller falskalarmrate.

Udvælgelsen bygger fortsat på det oprindelige alfabetisk afgrænsede metadataudtræk og er ikke repræsentativ for hele HARPS-arkivet. Fravær af match i det fastlåste litteraturprojekts ADP-/rå-ID-inventar er ikke bevis for, at observationerne aldrig tidligere er blevet undersøgt. Oprindelsen af de nye søgetræf kræver den separate opfølgning.

`RESULTS.json` indeholder de samme totalsummer og kildehashes. `production/SUMMARY.json`, de komplette hændelsestabeller og per-spektrum-resultater bevarer den faktiske produktion. `acquisition.log` og `analysis.log` bevarer kørselsloggene.
