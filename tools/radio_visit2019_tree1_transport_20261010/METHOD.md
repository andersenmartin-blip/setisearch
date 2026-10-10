# Fastlåst TREE/type1-metadata, uden signalværdier

Denne nye familie følger kun faktiske HDF5-indekspointere fra seks allerede kvalificerede header-metadata. Den gamle tekstlige metadata-transport forbliver uændret. Ingen HEAD, gammelt prefix, payloadpointer, spektralværdi, codec, HDF5-værdi-API, retry eller redirect er tilladt.

En header er præcis24 bytes fra en verificeret layoutrod eller en intern TREE-node med niveau over0. Resten af en nodes brugte metadata er64+48*n bytes, hvor n læses fra den faktiske cachede header og højst64 understøttes. Ingen adresse, faktisk node-længde, trædybde eller tidsrækkeantal overføres fra et andet observationsbesøg. Leaf-payloadadresser registreres kun af den rene planlægger; transporten følger dem aldrig.

prepare_scope.py læser kun UTF8 kode og JSON. Den fikser alle manglende metadatafragmenter fra en helt ren INCOMPLETE-plan med seks gyldige kilder. Runtime genverificerer cachepins, typed pointerbytes, hele planens proveniens, kvalifikationen, tidligere forsøg og overlap, før en request kan sendes. Initial/tekstlig cache indlæses gennem den uændrede c677-loader; separate TREE-runder indlæses gennem tree_cache_admission.py.

Per runde: højst192 GET, samlet faktisk fastlagt reservation højst1MiB,20 CPU-sekunder,600 sekunder væg,512MiB RAM,4MiB stdout og32MiB output. Den delte workspace-grænse er12GiB. Root reserverer hele det nye BODY-beløb før den ene eksekvering, uden refundering af gamle/lost/failure-forsøg. Beskyttet kilde- og uafhængighedskvalifikation forbliver blokeret.

Hver returbyte tælles før lokal skrivning og eksponeres straks i base64-stykker på højst1024 bytes med SHA. Alle partial/errorreceipts bevares; første fejl stopper resten. launch_once.py starter barnet præcis én gang, relayer stdout før logning og måler den faktisk reaped proces gennem interpreter-close med wait4. Resource PASS er separat fra oprindelig exit/status. Senere cacheadmission kræver exit0, full-resource PASS og præcise innerresult/EXEC-pins.

Root genererer scope, publicerer kilde/scope/peer og den sene ROOT_ADMISSION, genlæser bytepins, og giver kun derefter GO. Kildeklargøringen her udfører ingen HTTP eller faktisk cacheplan.

```sh
python tools/radio_visit2019_tree1_transport_20261010/prepare_scope.py --config ABSOLUTE_CONFIG --expected-config-sha256 CONFIG_SHA --root-go-source-only-scope
python tools/radio_visit2019_tree1_transport_20261010/launch_once.py --scope ABSOLUTE_SCOPE --expected-launcher-sha256 LAUNCHER_SHA --expected-wrapper-sha256 WORKER_SHA --expected-scope-sha256 SCOPE_SHA --public-freeze-commit SOURCE_FREEZE --launcher-public-freeze-commit SOURCE_FREEZE --expected-root-admission-sha256 ADMISSION_SHA --root-go-tree1-metadata-only
```
