# S2017: efterfølgende matchning af gemte ON-maksimummer

Dette er en ny, deskriptiv association af eksisterende resultater fra samme
2017-besøg. Koden er prospektiv og må først køres efter offentlig frysning,
præcis readback og root GO. Der er ingen nye teleskoprequests, rå-HDF5-læsning,
detektorkørsel, preprocessing, driftfit eller signalprofiler i denne fase.

Alle 254 allerede søgte indre cores q1..254 bruges én gang, inklusive den
oprindelige q128. Det giver 762 kort og 1.040.384 carrier-vindere pr. ON,
3.121.152 i alt. q0/q255 samt andre kilder og holdouts er uden for familien.
Hver carrier har kun sin oprindelige vindende drift og bredde. De 1.570
underliggende hypoteser kan ikke genskabes fra et maksimumkort.

## Faste koordinater og matchregel

Referenceøjeblikket er midten mellem ON1 og ON3's første integrationsmidter,
beregnet fra de eksakte seks scanheaders med det oprindelige MJD-anker.
Sekunder fra ankeret bruges i regningen; MJD vises kun som metadata.
For hvert gemt maksimum bruges uden kanalafrunding:

`fstar = FCH1 + DF * absolute_source_channel + saved_drift * (common_ref - original_ON_ref)`.

DF er negativ. Fysisk frekvens er i Hz, drift i Hz/s. Det oprindelige grid er
præcis NumPy 2.3.5 `np.linspace(-4.0, 4.0, 785, dtype=np.float64)`. Scope pinner
dets little-endian float64-bytes samt alle korts bytes. Hvert korts grid og hver
gemt vinder skal passe bit for bit til dette grid; der bruges intet nyt gridfit.
Medlemsbredder 1/3 beholdes uændret og behøver ikke være ens mellem ON.

Alle seks ordnede ON-retninger bruger samme regel: højst ét driftindeks i
forskel og frekvensgap højst
`tau = 3*abs(DF) + 0.5*(8/784)*(t_ON3-t_ON1)`.
Tolerancen er en fast geometrisk associationsregel, cirka15,44Hz, og er ikke
en kalibreret fejlgrænse for støjende drift-/frekvensvindere.

Målrekorder grupperes efter driftindeks og sorteres efter transporterede Hz,
derefter absolut kildekanal. Der undersøges forgænger/efterfølger i hver af
højst tre nabogrupper: højst seks rekorder pr. forespørgsel. Ved identiske Hz
bruges gruppens mindste kanal, også for forgængeren. Nærmeste vælges
leksikografisk efter frekvensgap, driftindeksgap og målkanal; score bruges ikke
til denne association. Alle seks links skal være gensidige og konsistente om
samme ON1/ON2/ON3-triple. Den fulde triples max-min-frekvens og driftindeks
skal også ligge inden for de samme vinduer. Der enumereres ingen kartesiske
par eller triple.

Hver rekord kan derfor højst indgå i én beholdt triple. Hele relationen gemmes
som en N×3 little-endian int32 NPY med indeks til de tre kanalordnede ON-vektorer.
Et indeks i betyder absolut kildekanal `179306496 + 4096 + i`. Logiske
kildekanaler valideres først som int64; kun de sikkert afgrænsede vektorindeks
lagres som int32. Der er højst1.040.384 triple, cirka12,5MB relation.

Triple rangeres alene til visning efter den mindste af deres tre allerede
gemte scores, faldende, derefter ON1/ON2/ON3-kildevectorens kanaltriple.
Top1.000 er fast, med alle oprindelige medlemsnøgler, scores, widths, gridindeks,
drifts, referencefrekvenser, transporterede frekvenser og tre parvise gaps.
Der bruges ingen scorethreshold eller kvalifikation. Fuld matchcount og
visnings-trunkering rapporteres også, inklusive nul matches.

## Input og livscyklus

`prepare_scope.py` er metadata- og opaque-byte-only. Den er skrevet til senere
én root-invokation efter peer review og faktisk varig ejerlevering; den er ikke
kørt som del af kildeforberedelsen. Den kontrollerer de oprindelige fire
COMPLETE-receipts, begge faktiske QA PASS, alle 762 aktuelle kortpins og
759 separate tile-normalization-pins. q128 har tre indlejrede normalization-
rekorder i sit checkpoint; der kræves ikke tre ikkeeksisterende separate filer.
Normaliseringerne genberegnes eller anvendes ikke af matcheren.

Root skriver først en admission, når ejerens RAW og RESULT er varigt gemt og
verificeret, alle fire numeriske og begge QA-processer er afsluttet, og et friskt
tværarbejder-check ikke finder samme matcher udført eller planlagt. Admission
har schema `SETI_S2017_CROSS_ON_ROOT_DURABLE_CLOSED_ADMISSION_V1`, status
`PASS_CLOSED_QA_DURABLE_RAW_AND_RESULTS_NO_DUPLICATE_MATCHER`, map_count762,
de fem eksplicitte true-booleans i koden, den præcise source_root, fælles disk-
rødder, og to verified RAW/RESULT-proofs med præcise path/SHA256/bytes-pins.
Feltet `all_numeric_and_QA_processes_closed` er root-attesteret fra faktiske
fire COMPLETE- og to QA PASS-pins samt proces-/kernelguard-kontrol; der kræves
ingen privat tool-session-identitet. Matcheren kontrollerer relevante `/proc`
command-paths og tager ikke-blokerende eksklusive flocks på de syv allerede
eksisterende ejer-kernelguards. Disse åbnes read-only, ændres ikke og holdes
gennem hele matchningen. Manglende eller ejet guard afvises. Matcheren åbner
ingen Library-session eller arkivkopi.

Admissionens `ordered_map_pins_sha256` er SHA256 af de 762 map-pin-objekter
i ON1/ON2/ON3, q1..254-rækkefølge serialiseret med JSON sort_keys=true og
separators=(',',':'). Hvert objekt har præcis `path` (absolut canonical),
`sha256` (64 lowercase hex) og `bytes` (heltal). Scopegeneratorens frisklæste
bytes skal matche dette. Admissionens `original_execution_and_QA_pins` har
de samme tre felter og fast rækkefølge: q128 EXEC, batch01 EXEC, batch02 EXEC,
batch03 EXEC, q128 QA, bulk QA. De seks facts læses fra de samme bytes, som
kontrolleres mod pins. Scopegeneratoren forbinder også hver QA til faktisk
scope, driver, QA-kode, public-freeze og execution-receipt SHA.
Alle oprindelige scope-/driver-/source-/checkpoint-/QA-pins bevares. Ejerens
allerede gemte RAW/RESULT-pakker genbruges; der bygges ingen duplikeret pakke.

Matcheren har én varig forsøgsmarkør og en proces-ejet flock på en stabil inode.
Forsøgsmarkøren fsync'es sammen med sin mappe før fuld admission og NumPy.
Låsen holdes gennem slutreceipt og lukkes uden unlink. Eksisterende output eller
forsøgsmarkør afvises. Fejl bevarer deloutput og får ingen automatisk retry/resume.
Checkpoints dokumenterer de seks færdige matchretninger, men er ikke genstartbare.

Faste grænser:120CPU-sekunder,1.800wall-sekunder og1GiB pr. proces. Et frisk
fælles filbyte-check plus64MiB outputreservation skal passe under8GiB før
scientific import/NPZ-læsning. Hele output og slutdisk forbliver inden for
reservation/cap. Dette er en kildebaseret ressourcevurdering, ikke en benchmark.
Færdig-status kræver slut-readback af scope, code, metadata, alle kort og norms
samt målt ressource-PASS. Der reserveres0,1CPU-sekund og2wall-sekunder til
terminalpublication. Fuld receipt serialiseres og fsync'es til en klargjort fil,
som offentliggøres lokalt med eksklusiv hardlink. Stdout-fejl efter terminalen
skaber ingen modstridende FAILURE. OS-kill uden COMPLETE er ufuldstændigt;
ingen rerun. Begge delte projekters kilde-, scope-, kode- og outputpaths skal
være omfattet af de deklarerede ikkeoverlappende disk-rødder.

Absolut CLI efter root-frysning (pladsholdere erstattes med faktisk frosne værdier):

```sh
PYTHONPATH=/workspace/scratch/a8d1e29996d0/seti_fullpower_work/deps python -u /workspace/scratch/a8d1e29996d0/setisearch_fullpower/tools/radio_s2017_cross_on_recovery_20261010/match_saved.py --scope /workspace/scratch/a8d1e29996d0/setisearch_fullpower/tools/radio_s2017_cross_on_recovery_20261010/scope.json --expected-scope-sha256 SCOPE_SHA256 --expected-admission-sha256 ADMISSION_SHA256 --freeze-commit PUBLIC_FREEZE_COMMIT --root-go-after-closed-durable-QA
```

## Videnskabelige grænser

Gensidige nærmeste naboer udelader andre geometrisk mulige associationer.
Maksimumkompressionen kan skjule et sammenhængende signal, hvis en anden
hypotese vandt. Støj, blandede features og stationære receiverfrekvensmønstre
kan samtidig skabe ON-coincidences. Relationer og rangtal er korrelerede og
giver ingen FAP, kalibreret SNR, global null-test eller oprindelsesklassifikation.
Ingen barycentrisk transformation eller fysisk frekvensramme ud over den
oprindelige receiverfrekvens er indført. Samme besøg er ikke en holdout.

En eventuel senere profilfase kræver ny afgrænset og offentligfrosset scope.
Den skal genbruge enhver allerede gemt identisk profil blandt de oprindelige36
og kun måle tidligere ugemte medlemsnøgler. Der er ingen autorisation til
profilering, refit eller OFF-veto i denne matchfase. Hel-original-source-MD5 og
det gamle A/B FAIL_CLOSED forbliver uafklaret/uændret.

Forberedelseslog: en tidlig, afgrænset checkpointlæsning viste utilsigtet nogle
allerede gemte q128 row-power-medianer. Ingen NPZ, carrier-score, kandidat- eller
profilværdier blev åbnet. Reglerne ovenfor var fastlagt før dette og blev ikke
ændret. Familien kaldes efterfølgende/deskriptiv, aldrig blind validering.


## Afgrænset recovery efter pre-array startfejl

Denne recovery-familie er særskilt fra den oprindelige
`radio_s2017_cross_on_20261010`. Root startede den oprindelige launcher én gang
under public freeze `96deeac6f68c58996c87896f1d3686e12884befa`. Launcherens
preexec satte hard RLIMIT_CPU til121sekunder, mens den uændrede matcher bad om
120soft/122hard. Barnet sluttede med exit1 og `ValueError: not allowed to raise
maximum limit`, før load_contract, forsøgsmarkør, NumPy, arrays eller matchning.
Den målte fejlstart brugte0,038567CPU-sekunder; der blev ingen videnskabelig
passage eller matchoutput. Originalens status og bytes forbliver uændrede.

Oprindelig matcher SHA256:
`8ec587be2e0cccd7a443373dbb5b466da9554576beeb019c91b59a3eee746a62`.
Oprindelig scope SHA256:
`dd96f3b30de939accd607fe5bedeca3c4450bedbeb80e5b284a0fc4651cbe5e5`.
Bevaret `ROOT_OUTER_EXECUTION_RECEIPT.json` SHA256:
`4894ea493ac5be47ed24a015b2fcd11369fecc109c73d7b44d222c000ffdc2be`.
Bevaret `ROOT_OUTER_STARTED.json` SHA256:
`38603c461123b5d28c1de205d64fffbd8af53aa0aadaaf3eb8b12c2e5f584e0f`.

Koden her er en præcis kopi med kun familie-/path-namespace ændret. De rene
matchfunktioner, grid, tolerancer, sortering, widths, alle caps og inputregler
er uændrede. Der tillades én ny invokation i det særskilte outputnamespace
efter ny admission, peer delta-review, ny offentlig freeze/readback og root GO.
Den korrigerede ydre launcher skal sætte CPU soft120/hard122, samme1GiB og
1.800wall-grænser samt thread-env1. Der autoriseres ingen automatisk retry
af den gamle familie. Tidligere kunstige testcase- og NumPy-importbeviser
genbruges via kodeidentitet; de gentages ikke. Ingen ny source BODY eller
detektorkørsel er autoriseret. Hvis den nye passage faktisk fuldføres, er
regnskabet to startinvokationer og én faktisk matchningspassage, aldrig to
videnskabelige passes. Alle fremtidige resultatpåstande er betinget af dette.
