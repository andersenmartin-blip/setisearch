# SETI: afgrænset fejlforløb lukket 15. oktober 2026

Metodekontrollen lukkes **FAIL_CLOSED**. Der er bevaret 160 worker-commits af de
planlagte 205, men ingen uafhængig QA er kørt. De 45 resterende identiteter er
**NOT_RUN**. Der er ingen kvalificeret SETI-detektion og ingen godkendt genfindingsrate.

Koordinatoren stoppede indsendelsen ved den fastlagte reserve for arbejdsplads
eller resultatlager (`workspace_or_output_capacity_margin_exhausted`). Det er
et stop ved en adgangsmargen; bilaget dokumenterer ikke en overskridelse af
selve lagerloftet. Alle allerede startede børn blev afsluttet og reaped.

Den efterfølgende kontrol fandt desuden en særskilt brist i CPU-kravet:

| Bilag for C0147, matched_rfi:022 | CPU-sekunder |
|---|---:|
| Fastlagt loft for hele barnet | 600,000000 |
| Forælderens wait4-måling af hele barnet | 601,151447 |
| Workerens egen ressourcekvittering | 598,727962 |

Processen sluttede med exitkode 0. Den bindende wait4-måling ligger alligevel
1,151447 CPU-sekunder over loftet. Workerens snævrere egenkvittering og exitkode 0
kan ikke tilsidesætte kravet til hele barnet. Der ændres ikke på loftet bagefter.

En fremadrettet forlængelse med større resultatlager var forberedt, men dens
strenge adgangskontrol afviste netop denne CPU-overskridelse. Der blev ikke
oprettet noget admission-snapshot eller GO, ingen ændring blev publiceret, og
ingen forlængelsesproduktion eller nye RNG-forløb blev startet. Kode, skabeloner
og test-fixtures bevares alene som **PREPARED_NOT_ADMITTED**.

| Syntetisk familie | Planlagt | Worker-commit | NOT_RUN | Uafhængig QA |
|---|---:|---:|---:|---:|
| calibration | 63 | 63 | 0 | 0 |
| strong | 14 | 14 | 0 | 0 |
| operating | 48 | 48 | 0 | 0 |
| matched_rfi | 24 | 24 | 0 | 0 |
| null | 32 | 11 | 21 | 0 |
| single_row_transient | 12 | 0 | 12 | 0 |
| near_off_contamination | 12 | 0 | 12 | 0 |

De 160 commits fordeler sig på 63 støjreferencer og 97 øvrige kontrolforløb.
Indeks 160–204 er ikke indsendt og har hverken claim eller resultatmappe.
Worker-commit betyder, at producenten skrev et komplet resultatbilag; det er
ikke en uafhængig godkendelse af data, genfinding eller metode. Den oprindelige
SUMMARY står uændret med `integrity_gate=false`, `joint_gate=false`, 160 `FAIL`
og 45 `NOT_RUN`. De 160 `FAIL` er ikke 160 målte videnskabelige ikke-genfindinger.

De 63 støjreferencers foreløbige maksimum er **7,757931310134776** under den
syntetiske Gamma16-model. Kalibreringen har udtrykkeligt status afventende fuld
uafhængig QA. Tallet kan ikke bruges her som dokumenteret himmelsignifikans,
teleskopfølsomhed eller en godkendelse af en kandidat.

De ni allerede eksponerede historiske bånd er **NOT_RUN**. Den oprindelige
adgangsbetingelse er lukket; fraværet af en kørsel er ikke en målt nulobservation.

Der er registreret **30.911,989 CPU-sekunder** fra de 160 hele børneprocesser.
Med den bevarede metadatareservation på 1.000 sekunder er regnskabstallet
**31.911,989 CPU-sekunder** inden for det samlede nye loft på 260.000.
Det ophæver ikke overskridelsen af det enkelte barns loft. Den gamle uafstemte
90.000-sekunders reservation bevares særskilt uden nulstilling eller refundering.

Alle 160 bevarede primæridentiteter dækkes af 42 tidligere SHA-verificerede
checkpoint-arkiver med registreret vellykket lagring. Gemmekvitteringer og indeks
er bevaret; de eksterne payloads blev ikke downloadet igen til denne rapport.
Den samlede evidenspakke indeholder de lokale originale payloads, logs, claims,
fasebilag og kildepins. Denne rapport anvender metadata og fremsætter ingen
numeriske genfindings- eller interferensafvisningsrater uden QA.

Den oprindelige A/B-status forbliver **FAIL_CLOSED**. De beskyttede 2016-data og
den utilgængelige 2019-rute forbliver lukkede. Kontrolpunktet er fortsat
**20. oktober 2026**. Der er brugt **0 DKK**, og der er ingen nye
teleskopforespørgsler eller teleskopbytes.
