# Review af den gemte METHOD-verifikation, 8. oktober 2026

**Status: PASS_PEER_SAVED_VERIFICATION_RECEIPT_AND_SCOPE_REVIEW.** Den nye kvittering, de oprindelige tekstinputs, restaureringens hashbindinger og de målte procesgrænser er indbyrdes konsistente. Der er gennemført én afgrænset verifikation af den fastlåste case `SETI_RADIO_PILOT_20261008_METHOD_STUDY:method_signal:000` i en frisk proces. A/B står fortsat som fejlet, og qualification er fortsat false.

Dette er et særskilt review af kode, tekstbeviser og ressourceafslutning. Revieweren har ikke åbnet arkiver eller numeriske kort, kørt verifikationsprogrammet eller udført en anden numerisk replay. De seks gemte kort blev åbnet af rodopgavens ene dokumenterede verifikationsproces.

## Adgang og afgrænsning

Den originale kode og dokumentation blev læst direkte fra uforanderlig Git-kilde `b4cb5d9d8ebe17f5651e8b59f46f97f89858b278`. Dokumentationen kræver, at hele METHOD-panelet på 64 cases er varigt afsluttet før denne ene gemte-case-kørsel. Den kræver ikke kalenderdatoen 19. oktober. Den godkendte plans kalender er arbejdsmilepæle. Arbejdet er derfor dokumenteret som faktisk gennemført 8. oktober efter panelets afslutning, fremrykket fra milepælen 19. oktober. Det skal ikke gentages 19. oktober.

Den valgte kodegren kræver det autentificerede fuldpanelmarker og den originale admission, kontrollerer de 21 admitted prerequisite-hashes og vælger præcis én af de 64 frosne identiteter. Den læser kun denne cases seks scorekort, geometriarrays og gemte tekstoutputs. Kun NumPy og standardbiblioteket importeres; generatoren, detektoren og hjælpekoden findes som hashbundne inputs og importeres eller udføres ikke.

Verifikationsprogrammet matcher sin oprindelige SHA256 `5a502551614d8bb5943da550664d2cc88ba06a04bd6a0d52543a8041e82f0891` og Git-blob `1dcb92a599c192745da17b77fc478ed0577b1944`. Den originale admission matcher SHA256 `62554e1a1328c7ab3b27d10a4a77c356ebfbe78aed8dc26545b39e5b3ca35011`. Original admission, caseadmissions, reservationer og claim er bevaret. Roden er uændret, og alle 21 prerequisite-path-mappings har samme oprindelige og restaurerede sti samt samme admitted og observerede SHA256. Der blev ikke brugt rebasering.

Wrapperen kontrollerer outputfravær inden invocation, skriver et eksklusivt engangsclaim og afviser et eksisterende jobreceipt. Det originale program afviser også overskrivning og skriver sit nye JSON-output eksklusivt. `VERIFIER_INVOCATION.json`, kommandoen i `resource_verification.json`, verifierloggen og den nye outputkvittering angiver den samme case. Der findes ingen anden verifier-invocation i denne arbejdspakke.

## Restaurering og transportfejl

Den første restaureringsproces fejlede korrekt på koordinatorarkivets hashkontrol. Den lokale overførsel var afkortet til 72.000 dekodede bytes mod de originale 79.878 bytes. Fejlen blev bevaret i `job_restoration.log` og `resource_restoration.json`; verifikationsprogrammet var endnu ikke invokeret. Case000-arkivet havde bestået autentificeringen, men den delvise struktur blev ikke brugt til en verifikationspåstand.

Efter rettelse af alene koordinatortransporten bestod det originale byteantal, SHA256 og Git-blob. Den særskilte korrigerede restaureringsproces bestod. Det er en dokumenteret transportkorrektion af de samme frosne inputs, ikke en ny scientific draw eller en gentagelse af verifikationsprogrammet. Ingen hashkontrol blev omgået.

`RESTORATION_RECEIPT.json` beskriver 54 filer på 1.896.541 bytes og de to autentificerede arkiver på tilsammen 608.655 komprimerede bytes. Alle 54 filbindinger i kvitteringen matcher preflightens forventede bindinger og tekstoverførslens bindinger. Revieweren genberegnede selv byteantal og SHA256 for de 47 restaurerede tekstfiler, tilsammen 1.443.393 bytes, inklusive original admission, claim, verifier og alle 21 prerequisites. Alle matcher. De syv NPZ-filers og de to arkivkroppes autentificering vurderes her via rodopgavens restaureringskvittering og den gennemsete hashkontrolkode; revieweren har ikke genåbnet disse kroppe.

`INPUT_MANIFEST.json` er en semantisk provenienskopi af den historiske preflight. Dens oprindelige pending-/19. oktober-felter beskriver den tidligere forberedelse og bruges ikke som dagens eksekveringskvittering. Reviewet hævder ikke byteidentitet mellem denne kopi og den oprindelige `READINESS_MANIFEST.json`.

## Faktisk resultat og ressourcer

Den nye outputkvittering har status `PASS_BOUNDED_SAVED_RESULT_VERIFICATION`: seks gemte kort, 20 artifacthashes og 96 OFF-sammenligninger for én case. De 32 originale ON-threshold-carriers overlever alle, og der er ingen veto-witnesses i denne case. De er korrelerede svar fra én syntetisk signalcase, ikke 32 uafhængige fund. Case000 har kun aktivitet i tredje ON-scan; den gemte recovery angiver 32 lokaliserede carriers før og efter OFF.

| Proces | Exit | Målt CPU-komponent, sekunder | Vægtid, sekunder | Peak child RSS, bytes |
|---|---:|---:|---:|---:|
| Første restaurering, transportfejl bevaret | 1 | 0,045484 | 0,064855199 | 13.295.616 |
| Korrigeret restaurering | 0 | 0,065338 | 0,065149088 | 13.299.712 |
| Én gemt-case-verifikation | 0 | 0,151945 | 0,166062351 | 30.187.520 |

De målte child-/wrapper-komponenter summerer til 0,262767 CPU-sekunder. Verifierbarnet brugte 0,150676 CPU-sekunder og afsluttede under de effektive grænser på 60 CPU-sekunder, 120 sekunders vægtid og 4 GiB adresserum. Restaureringsbørnene havde hver 30 CPU-sekunders grænse og samme adresserumsgrænse. Wrapperen satte de fire trådmiljøvariabler til én tråd, og børnene blev reapet. CPU-/adresserumsgrænserne håndhæves med `setrlimit`; vægtiden håndhæves af wrapperen med process-group-kill og reaping ved timeout.

De originale `whole_CPU_s=73,064369` og `peak_RSS_bytes=75.288.576` inde i case-reviewet er historiske caseproduktionsværdier, som den nye verifier kontrollerer mod original closure. De er ikke dagens ressourceforbrug og er ikke genkørt.

Den konservative reservation på 150 CPU-sekunder dækker begge restaureringsforsøg, verifieren og opsætning, review, API, rapport og publicering. Resten går fra 6.212,705144981004 til 6.062,705144981004 CPU-sekunder. De målte komponenter trækkes ikke fra igen, og der gives ingen refusion. Wrapperopstart før målepunktet, efterfølgende serialisering og øvrigt overhead hævdes ikke fuldt målt; det er dækket af reservationen. Den beskyttede rapport-/reproduktionsmargin på mindst 2.000 CPU-sekunder er bevaret.

## Hvad PASS betyder

Kørslen bekræfter konsistens mellem allerede gemte map-vindere, threshold-hitliste, OFF-dispositioner, lokaliseret recovery, tabsmærkning, original artifactintegritet og historisk resource closure. Den har ikke rekonstrueret rå preprocessing eller beregnet nye numeriske detektorscores. Den har heller ikke gentaget OFF-familiens originale template-søgning; den kontrollerer autentificerede gemte sammenligninger og deres frosne relationer. Reviewkvitteringens eksisterende `independent_audit=true` gør ikke dette tekst-/ressourcereview til en ekstra uafhængig numerisk replikation eller et andet miljø.

Der er ingen nye syntetiske identiteter, thresholdændringer, ny kvalifikation, sky-pilot, teleskopværdier eller åbning af de historiske 112+128 holdouts. Den gamle periodes afslutning 9. oktober og slutrapporten 20. oktober står uændret. Milepælen 19. oktober kan nu pege på dette afsluttede resultat og må ikke udløse en ny verifier-kørsel. Perioden forlænges ikke automatisk.
