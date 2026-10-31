# BU — første delanalyse af HIP44295

31. oktober 2026. **Afsluttet: fem komplette scanninger, 366,2109375 kHz, ingen tærskeloverskridelser.**

Dette er den første detektorsøgning i de fem komplette, tidligere hentede scanninger fra besøget HIP44295/65133 den 29. september 2016. Dataene er tidligere dekodet; der er ikke foretaget nye observationer eller nye arkivforespørgsler. Brugerens prioritet om analyse af endnu ikke signalsøgte data er fulgt. Den tungere historiske HIP45688-kontrolfase er ikke aktiveret i denne fortsættelse.

## Faktisk analyseret omfang

- Native chunk 171, q1–32 i fire på forhånd fastlagte portioner. 131.072 bærefrekvenskanaler;2301,477816514671–2301,844024658203 MHz ved scanningsmidtpunktet. Kanalernes samlede binbredde er 0,3662109375 MHz.
- Fem scanninger med16 tidsrækker hver: tre ON og to OFF. 839 driftshastigheder fra −4 til +4 Hz/s; bredder 1/3/9/33 kanaler; strides 1/1/2/8.
- **1.443.348.480 korrelerede sporberegninger**, heraf 866.009.088 i ON-scanninger. Antallet er ikke uafhængige statistiske forsøg.
- Fuld native AC-normalisering før udskæring; de præcise, uændrede BN-søgefunktioner og lokal ESS. Detektionsgrænse 10. ESS er ikke et kalibreret antal standardafvigelser eller en falsk-alarm-sandsynlighed.

| Scanning | Arkiv-ID | Rolle/mål | Største lokale ESS | Fund ≥10 |
|---|---:|---|---:|---:|
| 0 | 65133 | ON HIP44295 | 6.592147 | 0 |
| 1 | 65135 | OFF HIP43151 | 5.895744 | 0 |
| 2 | 65137 | ON HIP44295 | 5.805085 | 0 |
| 3 | 65139 | OFF HIP43162 | 5.952771 | 0 |
| 4 | 65141 | ON HIP44295 | 6.106403 | 0 |

Alle 1.720.320 gemte maksimumværdier pr. bærefrekvens og bredde er endeligt kontrolleret som endelige tal under 10. Hvert maksimum omfatter de 839 driftshastigheder. Der opstod derfor ingen ON-startpunkter til sammenkædning på tværs af scanningerne. Den største lokale ESS var 6,592147; den er ikke en kandidat.

## Kontrol og reproducerbarhed

Plan og numerisk kildekode blev offentliggjort og læst tilbage før første scoring: [freeze 0fbd6ce](https://github.com/andersenmartin-blip/setisearch/commit/0fbd6ce37f1427475dd009b8fb0a884334d8fe88). Planens SHA-256 er `f681d59f37a205bf0448736137bdfce37e04a1e18e6a4654899f2e1df342aefd`.

Alle fire kørselstrin afsluttede med faktisk exitkode 0, observeret stdout-EOF, bestået ressourcekontrol og verificeret ZIP-eksport. Den oprindelige kildekode og alle inputhashes blev kontrolleret før og efter. Store aktive resultater blev skrevet i isoleret tmpfs; kun lukkede, kontrollerede arkiver blev eksporteret. Proceskald, der oversteg det første 30-sekunders ventetidspunkt, blev fulgt gennem samme session; der blev ikke startet andre executor-kald under produktionen.

Den separate reviewer importerede ingen produktionsnumerik og bestod 5.760 udvalgte direkte skalarsummer og 1.920 kalibreringsvektorer uden observeret forskel. Første portion omfattede desuden uafhængig udtrækning af 20.480 median/MAD-ankerpar og præcis rekonstruktion af 3.276.800 normaliserede støtteværdier; interpolationsprimitivet var fælles NumPy. Det er en afgrænset kontrol, ikke en anden fuld 839-rate-søgning. Der var nul ikke-tomme astronomiske sammenkædninger at efterprøve. Syntetiske tests dækker derfor fortsat selve klassifikationens ikke-tomme tilfælde.

Fil-, payload- og 16 rækkehashes pr. scanning matcher BB-dokumentationen. Faktiske header-starttider bruges; katalogtiden var cirka ét sekund tidligere i scan0 og 2. Den nedarvede fælles TREE/codec-begrænsning består; ingen ny uafhængig originalafkodning eller fuld fil-MD5-kvalifikation hævdes.

## Hvad resultatet betyder

Dette er et nulresultat ved den fastlåste tærskel i det konkrete deludsnit. **Den sjette OFF-scanning mangler stadig som komplet input**, og fuld besøgsbedømmelse er `NOT_EVALUABLE_MISSING_OFF5`. Ingen global FAP, astronomisk følsomhed, fuldstændighed eller ekstraterrestrisk oprindelse er kvalificeret. De oprindelige BB/BC/BE-gates og historiske BP/BQ/BR/BS-fejl er ikke omskrevet.

BA-autoriteten er uændret: 486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg; BU giver nul ny fuld-besøgsdækning, og køen er ikke rykket. Alle fem native arrays blev normaliseret, også uden for søgekernerne. q33–253 er stadig uden detektorsøgning, men må derfor ikke beskrives som usete rådata eller holdout.

Næste afgrænsede analysestykke er q33–64 under en ny forud fastlagt scope. Den manglende scan5 og den oprindelige komplette inputdokumentation skal fortsat indhentes via den normale godkendte arkivadgang før en fuld seks-scanningsbedømmelse. Alle processer er afsluttet.

Maskinlæsbare resultater: [SUMMARY_BU.json](work_bu/SUMMARY_BU.json). Inputhenvisninger: [INPUT_LINEAGE_BU.json](work_bu/provenance/INPUT_LINEAGE_BU.json). Kode, plan, numeriske audits, proceskvitteringer og eksportkontroller ligger under `work_bu/`.

