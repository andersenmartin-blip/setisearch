# SETI, 31. oktober 2026 — BT: alle 24 begrænsede kontroller kvalificeret

**Den sidste kontrol, A04, er nu afsluttet og uafhængigt kvalificeret i en ny isoleret kørsel.** Samlet er de 24 planlagte kontrolcases kvalificeret: 23 fra BP og den fulde nye A04-pair fra BT. BP's oprindelige kørsel forbliver FAIL; ingen tidligere fejl er omskrevet til PASS.

## Resultatet

| Kontrol | Current | Legacy |
|---|---:|---:|
| Stærke testsignaler genfundet | 6/6 | 6/6 |
| Svage testsignaler genfundet | 2/6 | 2/6 |
| Fulde flag i otte baggrundscadencer | 0 | 0 |
| A04-associationer genberegnet og kontrolleret | 43.306 | 43.845 |
| A04: afvist på tre-ON-kravet | 33.637 | 34.029 |
| A04: afvist ved OFF-veto | 9.669 | 9.816 |
| A04: fulde flag / unsupported | 0 / 0 | 0 / 0 |

Der er ingen svag legacy-genfinding, som current mister i disse tests. Alle fire forstyrrelseskontroller A01–A04 er nu kvalificeret. A04's kendte forstyrrelse har understøttet OFF-veto i begge metoder.

Den uafhængige BT-audit genberegnede **alle 87.151 associationer** og 22 truth-poster fra de fastlåste scoredata, verificerede samtlige arkivmedlemmer og bekræftede den nøjagtige filoversigt efter afslutning. Kørslens faktiske exit var 0, child-wait, naturlig EOF og oprydning var bekræftet. Inklusive parent-kontrol tog den 32,54 sekunder med cirka 130,51 MiB maksimal child-RSS. 36 source-pins og 68 historiske/input-pins bestod.

## Hvad der løste blokeringen i denne kørsel

BS fandt genskabte pending-filer på andre inoder og midlertidig kopieringsaktivitet, herunder `.rsync-tmp`, omkring det fælles arbejdsområde. BR-sekventieltesten forbliver FAIL, også fordi filoversigten ændrede sig efter terminalrapporten. Samtidig læsning alene forklarede ikke fejlen. Den ansvarlige proces og den præcise historiske BQ/BR-årsag er fortsat uafklaret.

BT holdt alle aktive resultatfiler i et privat, eksklusivt tmpfs-område. Først efter beregning, lukning og fuld kontrol blev én lukket ZIP eksporteret. Medlemsnavne, CRC, bytes og SHA256 blev kontrolleret både før og efter eksport, derefter af parent og en uafhængig audit. En særskilt fixture med 90.000 poster bestod denne kæde, før A04 blev startet.

A04 varede længere end den planlagte indledende executor-ventetid på 30 sekunder. Der blev derfor brugt én statusaflæsning af samme session, som protokollen tillod; ingen anden executor-kommando eller agentarbejde overlappede. Aktive filer forblev i tmpfs. Denne afvigelse er registreret, og den eksporterede evidens bestod fortsat alle kontroller.

Der blev hverken sammenstykket filer fra tidligere forsøg eller ændret numerik, tærskler, input eller associationsregler. De tidligere komplette stream-hashes var kun fastlagte deterministiske forudsigelser. Den nye komplette pair blev produceret samlet i BT.

## Bevarede fejl og afgrænsning

| Identitet | Uændret status |
|---|---|
| BP oprindelig kørsel | FAIL: 23 cases bestod; A04 ramte RSS-grænsen |
| BQ | EVIDENCE_FAIL: afkortet current-fil |
| BR | FAIL: filændring under kontrol |
| BS, BR-sekventieltest | FAIL: genskabte filer og ændret afslutningsoversigt |
| BT, separat fixture | PASS_ISOLATED_FIXTURE |
| BT, ny A04-pair | PASS_ISOLATED_A04 |

Kvalifikationen omfatter fortsat **fem rater og fem q-kerner**. Den er ikke den fulde 839-rate-kontrol, astronomisk datakvalifikation, FAP- eller følsomhedsmåling. Ingen astronomiske powers blev åbnet, ingen nye scorearrays eller RNG-træk blev udført i denne fortsættelse, og ingen observationer, arkivforespørgsler eller dækningskreditter blev tilføjet. De historiske 24 HIP45688-M-raw-sum-fejl, full-QA=false og BP's 124 nye brud på den gamle legacy-grænse bevares.

16 BS-tests og 21 BT-tests bestod før deres respektive fuldskalaforsøg. Alle ejede processer er afsluttet.

## Gemte resultater og næste skridt

- [BT: komplet isoleret fixture, A04-pair, kode, protokol og reviews](https://chatgpt.com/library?file_id=libfile_e454c1932ebc8191a900399be114a83a&account_id=personal) — 24.523.530 bytes, SHA256 `52e0c3753aa7e584e77090c2f4fa9586855215d328be69e839db5651787fa44d`.
- [BS: bevarede diagnostiske filer og fejlspor](https://chatgpt.com/library?file_id=libfile_9bf50b90e41c819185553e50628d18d1&account_id=personal) — 4.178.960 bytes, SHA256 `b28b33a79c5e6c831f43c232dbe3225b1ba7c81468a0be880341efdc9183a040`.
- [Forrige BP–BR-indeks med grundarrays og scanresultater](https://chatgpt.com/library?file_id=libfile_40c2243ceab8819182b7752e1b3fadb7&account_id=personal).
- [Offentlig BT-fastlåsning](https://github.com/andersenmartin-blip/setisearch/commit/25477008e7c941ddca69da416541643e4b95ce58).

Næste trin er at implementere og budgettere den allerede foreslåede særskilte fulde kontrol: **839 rater, fire bredder og alle 253 sikre q-kerner**, på seed3-baggrunden uden signal og med det på forhånd angivne stærke ON-signal. Udkastet i `work_bt/next_scope/BU_FULL839_SCOPE_DRAFT.json` bevarer den oprindelige BN-proposal. Det er ikke aktiveret eller budgetreserveret. Første nye score kræver en særskilt fastlagt ressource- og kontrolplan; derefter følger særskilt optagelse af astronomiske data.
