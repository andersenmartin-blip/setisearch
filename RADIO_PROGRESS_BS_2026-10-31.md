# SETI, 31. oktober 2026 — BS: filfejlen afgrænset

BS er en teknisk undersøgelse med kunstige tekstposter. Den giver ingen ny astronomisk dækning og ændrer endnu ikke status: **23 af 24 kontrolforløb er kvalificeret; A04 er fortsat blokeret**.

| Fastlagt forsøg | Faktisk exit | Integritetsstatus |
|---|---:|---|
| BQ-skriver, sekventielt | 0 | PASS |
| BR-skriver, sekventielt | 2 | FAIL: slettet pending-fil genskabt på en anden inode |
| BR-skriver med samtidig, læsende kontrol | 0 | PASS |

Alle seks færdige filer indeholdt præcis de forventede 45.000 poster og kontrolsummer: 270.000 uafhængigt kontrollerede poster i alt. Der var ingen ny støjgenerering, scoreberegning eller åbning af astronomiske powers. 16 målrettede kodetests bestod før den offentlige fastlåsning.

## Hvad fejlen viste

BR slettede den første pending-fil efter normal publicering. Senere registrerede filovervågningen en midlertidig fil med tilfældigt suffiks, aktivitet i `.rsync-tmp` og en flytning tilbage til det slettede pending-navn. Den genskabte fil havde en ny inode; den oprindelige færdige fil og den bevarede filbeskrivelse fandtes samtidig. Det er ikke almindelig hardlink-bogføring.

Efter terminalrapporten ændrede filoversigten sig igen. En registreret midlertidig fil på 30.146.560 bytes manglede, mens en anden prefix-fil på 47.972.352 bytes og en ekstra pending-fil var dukket op. De aktuelt bevarede BR-filer fyldte 408.880.521 bytes, over forsøgets 384 MiB-grænse; den oprindelige capture registrerede 288.023.246 bytes under grænsen. Begge observationer bevares. Den manglende fil er **ikke rekonstrueret**.

Mønstret er foreneligt med kopiering eller synkronisering omkring arbejdsområdet. Vi har ikke identificeret den ansvarlige proces eller bevist den præcise årsag til de tidligere BQ/BR-afkortninger. Sekventiel fejl og bestået overlapforsøg viser, at samtidig kørsel ikke alene forklarer problemet. Systemkaldssporing var utilgængelig; Python-audit kan kun dokumentere programmets egne registrerede operationer.

## Evidens og fortsættelse

Den uafhængige gennemgang har status `RETAINED_BYTES_VERIFIED_POST_TERMINAL_INVENTORY_FAILED`. To tidligere fejlede kontrolforsøg, de faktisk bevarede midlertidige filer og hele fejlhistorikken er gemt. Evidenspakken omfatter 56 filer og 770.127.338 ukomprimerede bytes; alle arkivmedlemmer er kontrolleret med CRC og SHA256.

[Gemte BS-resultater](https://chatgpt.com/library?file_id=libfile_9bf50b90e41c819185553e50628d18d1&account_id=personal). [Offentlig forsøgsfastlåsning](https://github.com/andersenmartin-blip/setisearch/commit/e107e514cd3fb0bd5da09712c422bf071f0f29c0).

Næste afprøvning skal bruge et isoleret tmpfs-arbejdsområde og én uafbrudt kørsel. Først efter afslutning og fuld kontrol eksporteres én lukket evidenspakke. Det skal afprøves på kunstige tekstposter før en ny, særskilt A04-afslutning. Ingen tidligere FAIL omklassificeres, og den fulde 839-rate-kontrol samt astronomisk søgning er fortsat ikke aktiveret.
