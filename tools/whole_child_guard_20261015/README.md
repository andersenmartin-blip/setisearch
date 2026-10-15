# Proceskontrol efter CPU-fejlen — 15. oktober 2026

**Den nye, separate procesvagt består 12 konkrete engineeringkontroller. Den er ikke integreret i eller adgangsgivende for nogen videnskabelig bank. Der er intet nyt signalresultat.** Den lukkede seks-scan-bank, dens CPU-fejl og oprindelig A/B `FAIL_CLOSED` bevares uændret.

Den oprindelige worker tog sin egen CPU-kvittering før JSON-skrivning, slut-hashing og procesafslutning. Koordinatoren målte derefter hele barnet med `wait4`, men brugte kun exitkoden til at stoppe indsendelsen. Ressourceoverskridelse med exit 0 var derfor en reel acceptfejl. Kilderne fra den lukkede bank ændres ikke; denne mappe indeholder en selvstændig komponent til senere integration.

`guard.py` anvender samme proces gennem launcher og `exec`, sætter CPU-/adresselofter før målprogrammet, overvåger barnets CPU-ur fra forælderen og tager den afgørende `wait4`-kvittering efter fuld afslutning. CPU-stop sker ved deklareret loft minus `max(1,5 s, 1 % af loftet)`; kernelens ekstra limit er `floor(loft − 1 s)`. Enhver watchdog, fejlkode, manglende launch-kvittering, ugyldig måling eller overskridelse af det deklarerede loft afvises. Der er ingen tolerance, fallback til workerens tal eller efterfølgende accept ud fra `COMMITTED` alene. Den lille serielle integration stopper før næste indsendelse og bevarer forsøgsmapper eksklusivt.

## Faktisk efterprøvning

Den endelige kørsel er [suite_process_clock/TEST_RESULT.json](results/suite_process_clock/TEST_RESULT.json). De 12 tests dækker almindelig afslutning, sen finalisering, CPU-burn, finalisering med ignoreret SIGXCPU, wall-stop og næste ikke-indsendte job, fejlkode, adressebegrænsning, gentaget forsøgsmappe, 22 ugyldige ressourcekvitteringer, den eksakte CPU-grænse inklusive C0147-regression, forælderafbrydelse og manglende CPU-reservation.

| Konkret procesforsøg | Målt resultat |
|---|---|
| Legacy-fixture med god tidlig kvittering og exit 0 | Tidlig CPU 0,021046618 s; endelig `wait4` 0,681474 s mod testloftet 0,35 s. CPU-gaten afviser. Denne bevidst uindpakkede fixture har også korrekt `launcher_verified=false`. |
| CPU-burn med ny forældervagt | Stoppet og reaped ved 0,510841 CPU-s; deklareret loft 2 s, forældrestop 0,5 s. |
| Uendelig `atexit`-finalisering | Stoppet og reaped ved 0,508837 CPU-s med samme uændrede loft. |
| Wall-stop i sekvens | Første job afvist; næste identitet aldrig indsendt og ingen resultatmappe oprettet. |

## Fejlede udviklingsforsøg er bevaret

Den første kørsel bestod, men en evidenspræcisering var nødvendig: den bevidst uindpakkede legacy-fixture havde først et konstrueret `launcher_verified=true` for at isolere CPU-gaten. Den rettede fixture registrerer faktisk manglende launcher. [Noten](results/RECEIPT_PRECISION_NOTE.json) og de oprindelige kvitteringer bevares.

Den efterfølgende kørsel fandt to fejl: et nominelt kernel-CPU-loft på 1 s standsede først ved **2,021513 og 3,340172 CPU-s**, over det uændrede acceptloft på 2 s. Kernelgrænsen alene var utilstrækkelig i dette miljø. Ressourcegaten afviste begge; fejlede tests er ikke ommærket til pass.

Første forældreovervågning via `/proc/<pid>/stat` fejlede også. Python/syscall-PID og procfs-mount-PID var forskellige: forælderen 5/774, barnet 6/775. Den metode gav én forkert tidlig afbrydelse og manglede målinger for andre børn. Forsøget er forkastet. Den endelige kode bruger `clock_getcpuclockid` med det faktiske unreapede barn og `clock_gettime`; ingen PID-opslag i procfs. Backend kontrolleres før launch, og vedvarende utilgængeligt børneur giver lukket fejl.

Alle fire suiteforsøg, inklusive de to fejlede versioner, er bevaret. De tidligere kildeversioner i [history](history) blev rekonstrueret nøjagtigt mod deres før-kørsel-SHA256-pins; de er evidens, ikke alternative driftsversioner. Der er 12 forskellige engineeringtests, ikke 48 uafhængige valideringer.

## Ressourcer og grænser

De fire hele suites brugte tilsammen **18,600335 målte CPU-s**, inklusive deres reaped børn, og under 16 MiB maksimal RSS pr. suite. Et separat CPU-ur-probejob målte 0,546226 CPU-s og debiteres konservativt med 1 s. De samlede 19,600335 s er derfor blandet måling og konservativ debitering, ikke fuldt målt forbrug. Den før første test fastsatte særskilte **120-CPU-s engineeringreservation beholdes fuldt**, herunder 60 s til metadata/levering; ingen umålt komponent refunderes. Gamle ledgers, den lukkede 260.000-s ramme og slutreserven nulstilles eller genbruges ikke. Pris og nye teleskoprequests/-bytes er 0.

Koden gælder kooperative enkeltprocesser på den efterprøvede Linux-platform, inklusive deres egne tråde. Den er ingen adversarial sandbox eller process-tree-begrænsning. Scheduling kan forsinke overvågning og signalering; de små forsøg giver ikke en absolut CPU-grænsegaranti for enhver last. **Den endelige strenge `wait4`-gate må derfor aldrig fjernes.** En ressourcekompliant proces er heller ikke dataintegritet, uafhængig QA, godkendt signalgenfinding eller videnskabelig admission.

Ingen detektor, generator, råspektralarray, gammel resultatbank eller ny identitet er åbnet/kørt. Dette løser ikke det tidligere outputbudget. Genoptagelse af den lukkede bank er fortsat forbudt. Komponenten er **PREPARED_RESOURCE_GUARD_ONLY**; brug i et senere separat studie kræver egen prospektiv integration med fuldt payloadbudget og alle videnskabelige gates. Næste formelle projektcheckpoint er stadig **20. oktober 2026**.

Genkørsel af engineeringtests er kun til ændret kode eller ny konkret risiko og kræver særskilt reserveret plads; eksisterende forsøgsmapper må ikke slettes. Den offentliggjorte slutkørsel blev udført med `python run_engineering_suite.py process_clock`. Launcheren afviser samme label igen og kontrollerer den samlede fixture-ramme før start. Dette er ikke et science-dispatch-kommandoeksempel.

[Særskilt budget](ENGINEERING_SCOPE.json) · [Slutkvittering](FINAL_ENGINEERING_RECEIPT.json) · [Alle målte suitekvitteringer](results) · [Lukket videnskabelig bank](../../analysis/sixscan_burst_20261015/REPORT.md)
