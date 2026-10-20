# SETI: afsluttende kontrolpunkt for 7.–20. oktober 2026

**Afsluttet 20. oktober 2026. Ingen kvalificeret SETI-detektion. Den oprindelige kvalifikation er fortsat FAIL_CLOSED.** Perioden gav faktisk beregnede metodeudfald og eksplorative søgninger i autentiske data, men ikke den oprindeligt krævede, kvalificerede teleskoppilot.

Denne afslutning gælder den [godkendte 7.–20. oktober-plan](https://github.com/andersenmartin-blip/setisearch/blob/a0d6eba5114030b6b95baa2a1347041a2e009abd/RADIO_TWO_WEEK_PLAN_2026-10-07.md) og det publicerede kildegrundlag ved `a0d6eba5114030b6b95baa2a1347041a2e009abd`. Den afslutter ikke SETI-projektet og hverken aktiverer eller stopper andre særskilt godkendte perioder. Den gamle 26. september–9. oktober-afslutning er uændret. Der sker ingen automatisk planforlængelse.

## Faktisk opnåede resultater

| Del | Publiceret udfald | Begrænsning og slutstatus |
|---|---|---|
| Frisk validering A | 140/142 afsluttet; to transientdiagnostikker afbrudt | FAIL_CLOSED; manglende udfald er ikke nulresultater |
| Frisk validering B | 142/142 afsluttet; 45/48 fulde genfund på arbejdsniveau | FAIL_CLOSED: tredje ON alene 6/8, bredde 3 21/24 og RFI-overlevere i 2/24 forløb |
| 64-cellers metodeundersøgelse | 52/64 genfund i alle aktive ON; 59/64 i mindst én | Beskrivende syntetisk kontrol, ikke ny kvalifikation |
| HIP98505, 17. marts 2016 | Seks ON/OFF-scans; driftsøgning og stationær sammenligning gennemført; syv svage ON-overskud bevaret | Uafklarede, efterudvalgte spor; ingen kalibreret FAP eller uafhængig bekræftelse |
| HIP98505, 28. april 2017 | Ni tidligere efterudvalgte bånd søgt; otte fuldt verificeret | I de otte: 0 bevarede topfem-ON-hypoteser ≥10 og 0 OFF-nativeidentiteter ≥8; B06 er ikke med i summerne |

Kilder: [A](https://github.com/andersenmartin-blip/setisearch/blob/a0d6eba5114030b6b95baa2a1347041a2e009abd/RADIO_VALIDATION_A_2026-10-08_RESULT.md), [B](https://github.com/andersenmartin-blip/setisearch/blob/a0d6eba5114030b6b95baa2a1347041a2e009abd/RADIO_VALIDATION_B_2026-10-08_RESULT.md), [metodeundersøgelse](https://github.com/andersenmartin-blip/setisearch/blob/a0d6eba5114030b6b95baa2a1347041a2e009abd/RADIO_METHOD_STUDY_2026-10-08_RESULT.md), [2016-overskud](https://github.com/andersenmartin-blip/setisearch/blob/a0d6eba5114030b6b95baa2a1347041a2e009abd/RADIO_ON_OFF_EXCESS_2026-10-09_RESULT.md), [2017-bånd](https://github.com/andersenmartin-blip/setisearch/blob/a0d6eba5114030b6b95baa2a1347041a2e009abd/RADIO_NINE_BAND_STATUS_2026-10-16.md).

De 64 metodetests gav fulde genfund 6/16, 14/16, 16/16 og 16/16 ved de fire indsprøjtede idealniveauer 10, 12, 16 og 24. Niveauerne er modelparametre, ikke fysisk flux eller målt detektor-SNR. Samlede beståede tællinger kan ikke overtrumfe B's fejlede undergrupper og RFI-krav.

De otte verificerede 2017-referencekerner er 32.768 kanaler med en **sum af binbredder på 91,552734375 kHz** ved referencetidspunktet. De er adskilte intervaller, ikke ét sammenhængende bånd. Højeste verificerede ON-score i den offentliggjorte tabel er **7,031163159**. Søgningen brugte 5.723 driftværdier over ±4 Hz/s, syv overlappende fire-række-vinduer og bredder 1/3/9/33. ON-tallet gælder den bevarede samlede topfem pr. referencekanal, ikke samtlige afprøvede ON-hypoteser over 10. OFF-inventaret er udtømmende for den erklærede score≥8-nativefamilie.

De seks scanninger fra 2017 er ét allerede eksponeret historisk besøg med fire retninger. De er ikke seks uafhængige observationer eller en uafhængig bekræftelse af 2016-sporene. Hverken snit 10/8, kontroltællinger eller de lokale maksimummer etablerer kalibreret sigma/SNR/FAP, sky-følsomhed eller en generel nuldetektion. Svagere, kortere eller anderledes formede emissioner er ikke udelukket.

## B06 og alle tidligere fejl bevares

B06's oprindelige payload blev afkortet. En separat afsluttet bytegendannelse genskabte senere filens eksakte oprindelige størrelse og SHA-256 uden en ny primær søgning. Den efterfølgende uafhængige QA kontrollerede alle seks søgekort og OFF-inventarer, men fejlede ved det fastlagte nulkrav for globalt maksimum: **7,450294835423308 mod 7,450294835423307**, forskel **8,881784197001252 × 10⁻¹⁶**, én binary64-ULP.

Bytegendannelsen er ikke en bestået samlet videnskabelig QA. B06 tælles hverken som verificeret nulresultat eller med i det verificerede maksimum. Den oprindelige kohorte forbliver `INCOMPLETE_COHORT_RETAINED_NO_RETRY`; det separate QA-forløb forbliver `STOPPED_RETAINED_NO_RETRY`. Ingen tolerance, fejlet evaluering eller lukket identitet ændres af dette kontrolpunkt. [Præcis bevaret evidens](https://github.com/andersenmartin-blip/setisearch/blob/a0d6eba5114030b6b95baa2a1347041a2e009abd/tools/saved_payload_restore_20261016/report/RESULTS_SUPPLEMENT_DA.md).

## Hvad der blev kontrolleret 20. oktober

Slutkontrollen blev offentligt [fastlåst før udførelse](https://github.com/andersenmartin-blip/setisearch/blob/2e63749fe1d1a63c5cec35f395997a0fe22181db/results/radio_final_checkpoint_20261020/CHECKPOINT_SCOPE.json) og afsluttet kl. 08:56:25 Europe/Copenhagen. En særskilt begrænset proces kontrollerede **13 rapport-/JSON-kilders eksakte Git-byteidentitet og i alt 30 metadata- og regnskabskrav**. Alle består. Det er en afstemning af allerede publiceret evidens, ikke en ny detektorkørsel, ny videnskabelig QA, ny versionsaudit eller ny signalanalyse.

Kontrollen fastholder blandt andet otte-båndsafgrænsningen, B06's udelukkelse og fejlstatus, de publicerede nulsummer, 48 verificerede scanningskort, forskellen mellem målte CPU-komponenter og reservationer samt en eksisterende gemt-case-verifikations afgrænsning. Ingen råarrays, payload-arrays, holdouts eller arkiver blev åbnet eller hentet. Ingen gamle kontrolforsøg eller søgninger blev gentaget.

Det eksisterende [begrænsede reproduktionsbilag](https://github.com/andersenmartin-blip/setisearch/blob/a0d6eba5114030b6b95baa2a1347041a2e009abd/pilot_protocol_20261008/review/METHOD_SAVED_CASE_000_REPRODUCTION.json) dokumenterer seks gemte kort, 20 artefakthashes og 96 OFF-sammenligninger for én metodecase. Det blev ikke kørt igen nu. Bilaget reproducerer ikke rå preprocessing eller numeriske scores. Der påstås **ingen særskilt ny reproduktionskørsel 19. oktober** eller fuldstændig reproduktion i et andet miljø. Kalenderens milepæle er ikke automatisk dokumentation for udførelse.

Den lokale tekstkopiering til slutkontrollen tilføjede først et ekstra afsluttende linjeskift. Git-byteidentitetskontrollen opdagede dette før lancering; kopierne blev rettet til de originale bytes. Ingen repositorykilde eller videnskabelig værdi blev ændret. [Forberedelsesnotat](results/radio_final_checkpoint_20261020/SOURCE_PREPARATION.json).

Maskinlæsbar evidens: [slutresultat og 13 kildepins](results/radio_final_checkpoint_20261020/CHECKPOINT_RESULT.json), [procesmåling](results/radio_final_checkpoint_20261020/PROCESS_RECEIPT.json), [lukningsledger](results/radio_final_checkpoint_20261020/RESOURCE_LEDGER.json), [kode](tools/final_checkpoint_20261020/check.py).

## Reservationer og målte komponenter

| Afgrænsning | Reservation, bevaret uden refusion | Målte komponenter |
|---|---:|---|
| Den oprindelige 9. oktober-eksploration | 3.910 CPU-s | Delvise målinger i dens uændrede ledger; ikke hele periodens forbrug |
| Slutkontrollen 20. oktober | 2.000 CPU-s fra den beskyttede reserve | Ny metadata-child: 0,041417 CPU-s; 0,042687 s wall; peak-RSS 11.403.264 bytes |
| B00 + 2017-kohorte + B06-gendannelse/QA | 12.560 CPU-s, særskilte scopes | 2.581,938327 child-CPU-s inklusive fejlede processer |
| 2017-resultatlevering | 100 CPU-s, særskilt | 3,314751 child-CPU-s |

Slutkontrollens 2.000 CPU-s er **reserveret/debiteret, ikke målt brugt**. Heraf var højst 60 CPU-s afsat til den målte proces og 1.940 CPU-s til hidtil umålt klargøring, læsning, gennemgang og publicering. Hele reservationen beholdes; forskellen til den lille målte komponent frigives ikke. Den gamle eksplorationsledger ændres ikke. Dens særskilte efterfølger afskriver reserveandelen én gang og efterlader konservativt **2,705144981003997 CPU-s** uden ny aktivering eller overførsel.

De 3.910 + 2.000 = 5.910 CPU-s er kun disse to reservationers subtotal, **ikke hele periodens regnskab**. De senere særskilte scopes, A/B, metodearbejde, historisk ukendte kørsler og uafstemte gamle omkostninger nulstilles ikke. De delvise målinger og overlap tillader ikke et troværdigt samlet målt CPU-tal for hele projektet; dette er **ukendt**, ikke nul. Denne slutkontrol certificerer derfor ikke retrospektivt overholdelse af alle historiske globale CPU-lofter og skaber intet nyt frit budget.

Nye teleskopforespørgsler og -bytes i dette kontrolpunkt: **0**. Ekstern udgift: **0 DKK**. Ingen beskeder, bookinger eller observationer er foretaget.

## Bevaring og fortsættelse

De eksisterende kilde-/resultatpakker, kode, scopes, originale logs, hits, vetoer, fejl og delvise udfald er fortsat de primære reproduktionsartefakter. Denne afslutning kopierer eller kontrollerer ikke alle arkiver på ny. Blandt de eksisterende leverancer er `SETI_ON_OFF_EXCESS_2026-10-09.zip` (77.022.050 bytes, SHA-256 `893e1c804436bd46b36b4569eaff361621e5570e8257c82d27ae2a03570ee88c`) og `SETI_ALLE_NI_BAAND_2026-10-16.zip` (76.984.741 bytes, SHA-256 `ac59da20464780bbcb26251e9ce2dc631d361dfc82a868551125edbdd41584d4`). Identiteterne er overtaget fra deres publicerede kvitteringer, ikke frisk verificeret mod ZIP-bytes her.

**Slutdisposition:** metodeundersøgelse og begrænsede eksplorative teleskopresultater er gennemført; oprindelig pilotkvalifikation er ikke opnået. Syv 2016-ON-overskud bevares uafklarede, otte 2017-bånd har det erklærede verificerede udfald, og B06 er fortsat ufuldstændigt kvalificeret. Der er intet nyt signalresultat fra selve slutkontrollen.

A/B, M43/M43AI og alle lukkede banker bevarer fejl/lukning. HD1461's pointing-HOLD, M15/GJ581 og M33/HD3651's uafklarede status, GJ724's tidligere disposition, LS-pausen ved LS8BD–LS8BE, urørt LS8BF og usendt CHEOPS bevares. De originale 112+128 holdouts og øvrige NOT_ACTIVATED-banker er ikke åbnet.

Et senere bevistrin for uafklarede signaler kræver uafhængige observationer med kontroller eller korrelationsbevarende kalibrering af hele udvælgelsen. Eventuel ny metode eller dataanalyse skal have sin egen udtrykkeligt godkendte afgrænsning, autoriserede saldo og prospektive regler; den kan ikke bruge dette kontrolpunkt til at genåbne en lukket bank eller stemple et gammelt fejludfald bestået. Denne periodeopgave er afsluttet og forlænges ikke.
