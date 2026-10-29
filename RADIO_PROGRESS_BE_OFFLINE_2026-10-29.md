# SETI BE — genoptagelse implementeret og testet offline

29. oktober 2026. **HIP44295 / 65133 står fortsat på 88 af 96 datarækker.** BE implementerer en ny genoptagelse for de otte manglende rækker og tilpasser de efterfølgende kontroltrin. Der er ikke hentet nye teleskopdata eller gennemført en ny signalsøgning.

## Det konkrete fremskridt

Alle ni tidligere BB-pakker er gendannet fra det eksisterende checkpoint. Deres arkivhashes og alle **989 inventarposter, 1.052.460.787 bytes**, er kontrolleret. Det omfatter fysisk kontrol af de fem komplette scan-arrays, den gamle syv-rækkers partial-fil og de bevarede HTTP-/TREE-data. BC's otte-rækkers partial-fil og fejldokumentation er bevaret uændret. Den nye recovery-protokol binder 1.124 forskellige BB/BC-kilde- og evidensfiler.

Med den endelige BE-kode er alle **otte allerede hentede scan-5-rækker genskabt fra de bevarede komprimerede bytes**, kontrolleret mod deres HTTP-kildesegmenter og sammenlignet byte for byte med den gemte partial-fil. Den separate proces sluttede med faktisk exit 0, registreret EOF og afsluttet ventning på processen. Der blev foretaget **nul arkivanmodninger**. Det er genkontrol af tidligere kontaktede data; ingen række har fået ny eller uafhængig observationsstatus.

Dette er et videre skridt fra BD's kontrol af lagrede rækkehashes. BE bruger igen den oprindelige, fælles codec og TREE-model. Det giver ikke en uafhængig validering af disse modeller eller en fuld native-kontrol af hele cadencen.

## Implementeret genoptagelse

Den nye runner bevarer **BB87 + BC1 + senere8 = 96** og **5 tidligere + 1 senere gentagelseskontrol**. Den genskaber og sammenligner alle otte gamle scan-5-rækker med netværket slået fra. Kun rækker 8–15 kan derefter bruge den normale arkivtransport. Række 7 skal have én særskilt, ny HTTP-206-gentagelse af hele den komprimerede chunk.

Proveniens, arkiv-ID, URL, ETag, Content-Range, byteantal, hashes og sammenhængende kildesegmenter kontrolleres. Metadata, som også dækker en del af en komprimeret chunk, må fortsat genbruges som verificerede kildesegmenter; en afledt union beskrives ikke som en ny kvittering for hele chunken.

En færdig scan-5-fil og en afslutningsmarkør publiceres først efter alle rækkekontroller, gentagelsen, lukning af backend, kontrol af uændrede inddata og manifestvalidering. Ved en håndteret fejl fjernes en eventuelt ny publiceret canonical-fil og afslutningsmarkør; partial-filer og fejlevidens bevares. Forbrugere kræver altid den gyldige afslutningsmarkør, da flere filoperationer ikke udgør én atomisk transaktion. Ingen automatisk genstart eller overskrivning er indbygget.

Kørselsregistreringen binder den faktiske underproces, exitkode, log, kildekode, protokol, adgangsgrundlag og resultatmarkør. Loggen kontrolleres mod både det observerede byteantal og SHA-256 fra stdout. Delvise filskrivninger fuldføres; fejl eller en ufuldstændig log kan ikke give en godkendt afslutning. En underproces med exit 0 og ugyldig resultatmarkør registreres særskilt som en afvist afslutning.

Budgettet er højst 60 anmodninger, 64 MiB anmodede bytes, 8 MiB pr. anmodning og én forbindelse. En 600-sekunders Python-signalgrænse dækker hele produktionsforsøget. Signalbehandling kan være forsinket under C-kald; dette er ikke en eksternt håndhævet absolut vægurtidsgrænse. Første fejl stopper videre transport, uden alternativ rute eller automatisk retry.

## Efterfølgende kontroller

Der er implementeret særskilte BE-adaptere til native-kontrol, inputbinding og de uændrede numeriske analysefaser. De kræver den nye tredelte datalinje, begge gamle partial-filer, de oprindelige fejlede acquisition-kørsler og separate, hashbundne kørselsgrundlag. De **33 oprindelige analysefiler er kopieret byte-identisk** til BE's nye kildetræ; source preparation sluttede med faktisk exit 0. Søgeregler og numeriske udtryk er uændrede.

Simulerede testforløb har særskilt afslutningsmarkør og kan ikke optages som produktionsdata i native-, bindings- eller analysefaserne. Python-optimering afvises før brug af historiske helpers, hvis deres assertions ellers ville blive slået fra.

## Verifikation og begrænsninger

- **43 syntetiske tests består:** 25 for recovery-transaktionen og 18 for procesregistreringen. De omfatter beskadigede rækker, forkerte kvitteringer, falske gentagelser, ændrede forælderfiler, manifestudskiftning, fejl sent i forløbet, ændret adgangsgrundlag og mangelfulde logskrivninger.
- Adapterne består **12 målrettede tests** og et separat review med **52 syntetiske kontroller**, inklusive afvisning af simulation som produktionsgrundlag.
- Separat kildekodereview omfatter både de nye adaptere og recovery-/capture-koden. Fundne fejl er dokumenteret sammen med rettelserne.
- Ingen reel acquisition af de otte manglende rækker, intet komplet 96-rækkers native-forløb og ingen fuld numerisk søgning er kørt med BE.

## Aktuel blokering og næste trin

Det aktuelle miljø tillader ikke Berkeley-arkivet som netværksdestination. BE har derfor **ikke afprøvet arkivadgang**, foretaget nogen ny arkivanmodning eller oprettet en produktionsfrigivelse. Den fastholdte BE-protokol autoriserer nul netværksanmodninger. De tidligere 403-fejl bevares som historisk evidens.

Første kendte manglende interval er fortsat **9241886720–9241903103**, 16.384 bytes TREE-metadata i arkiv-ID 65143. Række 8's komprimerede payload-interval er endnu ukendt og skal udledes fra ægte metadata. Den allerede dekodede række 7 består fortsat af 3.103.298 prefix-bytes fra BC og 13.580 tidligere BB-tail-bytes.

Når normal arkivadgang er tilgængelig, kræves en ny gennemgået protokolvariant med aktuelle stier og et udtrykkeligt adgangsgrundlag, før runneren kan starte. Den aktuelle protokol er et fastholdt offline-kontrolpunkt med nul anmodninger. Efter reel acquisition kræves faktisk exit 0 bundet til resultatmarkøren, fuld native-kontrol, uændret signalsøgning, ON/OFF-triage, review og afsluttende artefaktkontrol, før ny dækning eller en køændring kan godkendes.

## Videnskabelig status

**BA er fortsat senest afsluttede autoritet: 486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg.** BE tilføjer 0 arkiv-ID'er, 0 tekniske MHz-besøg, 0 nye observationsepoker og 0 kandidatvurderinger. HIP44295 bliver ved køens hoved. Tidligere uafklarede klassifikationer ændres ikke. Teknisk dækning er ikke kalibreret astronomisk følsomhed, og ingen astronomisk oprindelse, global falsk-alarm-sandsynlighed eller fuldstændighed er kvalificeret.

Der fortsætter ingen analyse i baggrunden efter denne aflevering.

## Dokumentation

- [Ny recovery-kode](work_be/recover_missing_rows_be.py) og [kørselsregistrering](work_be/capture_recovery_be.py)
- [Fastholdt offline-protokol](work_be/PROTOCOL_RECOVERY_BE.json)
- [BB-gendannelsens resultat](work_be/results/BB_RESTORATION_BE.json)
- [Slutkontrol af otte bevarede rækker](work_be/results/CACHED_EIGHT_ROW_PROBE_FINAL_BE.json) og [faktisk procesafslutning](work_be/results/CACHED_EIGHT_ROW_PROBE_FINAL_ACTUAL_EXIT_BE.json)
- [De 43 recovery-/capture-tests](work_be/review/RECOVERY_IMPLEMENTATION_TEST_REVIEW_BE.json)
- [Review af recovery og procesregistrering](work_be/review/INDEPENDENT_RECOVERY_SOURCE_REVIEW_BE.json)
- [Slutreview af analyseadapterne](work_be/review/INDEPENDENT_SCIENCE_ADAPTER_SOURCE_REVIEW_BE_V2.json)
- [Adaptergrænseflade](work_be/science_handoff/INTERFACE_BE_V2.json)
- [Afsluttende artefaktkontrol](work_be/results/FINAL_ARTIFACT_AUDIT_BE.json) og [kontrolsummer](work_be/results/SHA256SUMS_BE.txt)
- [Uændret BD-status](https://github.com/andersenmartin-blip/setisearch/blob/a4e59b81ee5fa70429cf7e79fa5e9f6694f1ac42/RADIO_PROGRESS_BD_OFFLINE_2026-10-29.md)

Det offentliggjorte layout er `work_be/` under projektroden. Historiske absolutte stier kræver en eksplicit relocation-fil; den fastholdte protokol indeholder denne kørsels stier og skal håndteres som evidens. Runtime installeres alene fra de tidligere hashkontrollerede wheels. Kodeimport og standardkørsel opretter ingen netværksadgang. Testene køres med `python3 -m unittest discover -s work_be -p 'test_*.py' -v` og separat `python3 work_be/science_handoff/test_adapters_be.py`.
