# Ét gemt METHOD-resultat verificeret i en frisk proces — 8. oktober 2026

Den ene afgrænsede kontrol af `SETI_RADIO_PILOT_20261008_METHOD_STUDY:method_signal:000` er udført og bestod med **PASS_BOUNDED_SAVED_RESULT_VERIFICATION**. Seks gemte scorekort,20 originale artefakthashes og96 OFF-sammenligninger stemmer med de bevarede hit-, veto- og recovery-records. Casens32 oprindelige ON-carriers er bevaret som32 overlevende carriers; disse er korrelerede svar fra ét gemt forløb.

## Tidspunkt og protokol

Kontrollen er fremrykket fra arbejdsmilepælen19.oktober til8.oktober. Den godkendte plan beskriver kalenderen som arbejdsmilepæle. Den særskilte [saved-result-protokol](../../pilot_protocol_20261008/review/METHOD_SAVED_RESULT_REPRODUCTION.md) tillader kontrollen efter durabel afslutning af hele64-case METHOD-panelet; den betingelse var opfyldt før denne kørsel. Den faktiske dato er registreret. Der udføres ingen ekstra kontrol af samme case den19.oktober.

Den gamle periodes afslutning9.oktober og den nye periodes slutrapport20.oktober er uændrede. Dette fremrykker en allerede godkendt reproduktionsopgave og aktiverer ingen ny metodeudvikling, forsøgsbank eller kampagne.

## Hvad der faktisk blev kontrolleret

Programmet blev startet én gang i en ny child-proces med uændrede argumenter til den frosne case og original admission. En wrapper satte de samme afgrænsninger som den dokumenterede prlimit/timeout-kommando:60 child-CPU-sekunder,120 sekunders vægtid,4GiB adresserum og én tråd for BLAS/OpenMP/MKL/NumExpr. Den målte hele child-/wrapper-komponent blev lukket og gemt. Outputfilens fravær og alle54 originale inputhashes blev efterkontrolleret umiddelbart før invocation.

| Kontrol | Resultat |
|---|---:|
| Gemte scorekort | 6 |
| Originale artefakthashes | 20 |
| OFF-sammenligninger | 96 |
| Kvalificerende OFF-veto-witnesses i denne case | 0 |
| Oprindelige ON-carriers / overlevende | 32 / 32 |
| Verifier-invocations | 1 |
| Nye signaltræk eller detektorscores | 0 |

Det er en konsistenskontrol fra gemte kort til hits, kompatibel OFF-klassifikation, lokalisering og tabstrin. Rå syntetisk power, preprocessing og de oprindelige numeriske detektorscores blev ikke genskabt. Ingen generator eller detektor blev importeret eller kørt. Det er heller ikke en ny uafhængig signalrealisering eller en gentagelse af alle64 METHOD-forsøg. A/B forbliver `FAIL_CLOSED`, og teleskoppiloten er fortsat ikke admitted.

## Originale bytes og transportfejl

Alle54 nødvendige runtimefiler blev restaureret fra immutable commit `b4cb5d9d8ebe17f5651e8b59f46f97f89858b278`, originalt case000-arkiv og udvalgte koordinatormedlemmer. Deres samlet deklarerede og verificerede bytes er1.896.541. Begge komprimerede arkiver er autentificeret med SHA256, Git-blob-SHA1 og byteantal:528.777 og79.878 bytes, i alt608.655 unikke arkivbytes. Admission, claim og øvrige originalfiler er byteidentiske. Ingen modstridende originalfil blev overskrevet.

Første restaureringsjob stoppede ved koordinatorarkivet: den lokale base64-staging gav kun72.000 dekodede bytes mod79.878 og fejlede derfor alle relevante identitetskontroller. Ingen verifier var startet, og ingen koordinatorfil blev udtrukket fra de afkortede bytes. Fejllog og ressourcekvittering er bevaret.

Koordinatortransporten blev hentet igen fra samme immutable kilde og skrevet til en ny stagingfil med eksplicit flush og bytekontrol pr. del. Hele det korrigerede arkiv matchede original SHA256 og Git-blob. Det korrigerede restaureringsjob bestod alle54 filer. Den første stagingfil og de oprindelige transferbindinger blev bevaret; original admission og claims blev ikke ændret. Rettelsen er transportrestaurering, ikke en ny udviklingsrettelse eller en verifier-retry.

De608.655 bytes angiver unikke arkivinputs. Med den ekstra koordinatorhentning er de deklarerede dekodede arkivpayloads fra API-hentninger688.533 bytes; dette er ikke en fuld måling af HTTP/base64-wrapper-overhead. Tekstinput og metadata er opgjort særskilt i bindingsfilerne. Ingen nye teleskopkildebytes er åbnet.

## Målt forbrug og saldo

| Job | Udfald | Målt child + wrapper CPU | Vægtid |
|---|---|---:|---:|
| Første restaurering | Stoppet ved afkortet lokal transport | 0,045484 s | 0,064855 s |
| Korrigeret restaurering | PASS,54 filer | 0,065338 s | 0,065149 s |
| Én frisk verifier | PASS | 0,151945 s | 0,166062 s |
| Metrede komponenter samlet | Første fejl inkluderet | 0,262767 s | — |

Verifier-child brugte0,150676 CPU-sekunder og havde peak RSS30.187.520 bytes. Casens73,064369 CPU-sekunder i den originale outputrecord er den historiske fremstilling af resultatet; de er ikke dagens verifikationstid og blev ikke genkørt.

En ny konservativ150-CPU-sekunders reservation til restaurering, verifier, review, API, rapport og udgivelse efterlader6.062,705144981004 CPU-sekunder. De målte0,262767 er komponenter af reservationen og debiteres ikke igen. Mindst2.000 bevares til slutrapportens arbejde. Tidligere reservationer refunderes ikke, og ukendt historisk/setup-/publiceringsforbrug hævdes ikke fuldt målt.

[Original frisk-proces-kvittering](../../pilot_protocol_20261008/review/METHOD_SAVED_CASE_000_REPRODUCTION.json) · [Restaureringskvittering](RESTORATION_RECEIPT.json) · [Transportrettelse](TRANSPORT_CORRECTION.json) · [Invocation](VERIFIER_INVOCATION.json) · [Ressourceledger](VERIFICATION_LEDGER.json) · [Review](REPRODUCTION_REVIEW.md) · [Scope](SCOPE.json).

De tidligere preflightfelter i INPUT_MANIFEST.json er historisk planlægningsproveniens og kan stadig angive19.oktober/pending. Dagens RESTORATION_RECEIPT, originale verifier-output og denne rapport dokumenterer den faktiske8.oktober-kørsel. Fremover bruges den aktuelle verifikationsledger og denne PASS-kvittering; kontrollen gentages ikke som dagligt fremskridt.
