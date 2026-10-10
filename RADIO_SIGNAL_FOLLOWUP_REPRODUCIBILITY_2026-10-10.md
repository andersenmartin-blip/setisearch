# Reproduktion af SETI-signalarbejdet 10. oktober 2026

Denne vejledning dokumenterer to allerede gennemførte numeriske jobs: en fast fysisk frekvensreference udledt af ni gamle driftudklip og en driftsøgning i otte hidtil usøgte referencekanalfelter. Hvert job blev kørt én gang efter offentlig fastlåsning i commit `ada64c4d46ead59b92f8e65ae2ce6aa4d13d0759`. Vejledningen er skrevet ud fra kode, scopes og kvitteringer; den medfører ingen ny numerisk kørsel, katalogsøgning eller åbning af kildeværdier. Der er ingen autoriseret numerisk retry i denne aktivitet.

Begge jobs bruger seks scanninger fra ét historisk besøg den 17. marts 2016 af HIP98505/HD189733. `epoch1/2/3` er scanningsnavne, ikke uafhængige besøg. Kildeeffekten var allerede åbnet i tidligere stationært arbejde. Fastlåsningen gælder de nye afledte mål og de nye driftresultater; den gør ikke arbejdet blindt eller uafhængigt. A/B forbliver FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og tidligere holdouts er lukkede.

## Gemte filer og mappestruktur

`SETI_SIGNAL_FOLLOWUP_2026-10-10.zip` indeholder denne vejledning, rapporter, ny kode og scopes, resultater og kontrolkvitteringer. Den indeholder også de ni oprindelige ON-drift-NPZ-inputudklip, det fulde oprindelige `FIXED_TOP3_PROFILES.json`, kilde- og anskaffelsesmetadata, `NORMALIZATION.json`, den oprindelige `fresh_search.py` med scope og den uændrede detektor. De seks kompakte HDF5-inputfiler og de to binære wheels genpakkes ikke i denne pakke.

De eksisterende arkiver identificeres med filnavn, byteantal og SHA256. Filreferencer i den oprindelige session er adgangsreferencer; nedenstående indholdspins kan kontrolleres efter flytning eller ny udpakning.

| Tidligere gemt arkiv | Bytes | SHA256 |
| --- | ---: | --- |
| `SETI_FRESH_BAND151_RAW_2026-10-09.zip` | 305428707 | `6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d` |
| `SETI_FRESH_BAND151_RESULTS_2026-10-09.zip` | 266354883 | `4e189934c09820e9dac82d791d78d82528dcd5655ee2874245350e6e27cd464b` |
| `SETI_STATIONARY_FAMILY_2026-10-10.zip` | 20369402 | `acb5e6fce192bd7962fdb7f96a4d075d80bda36bd39830ad2e1ea6a0ffa0a0ea` |

De seks kompakte filer gendannes fra det allerede gemte RAW-arkiv, efter kontrol af arkivets pin. Der skal ikke genhentes teleskopdata. Deres oprindelige relative placering er `results/radio_fresh_band_20261009/arrays/` under repository-roden. Arkivgendannelsen er dokumenteret i `results/radio_gap_drift_20261010/RECOVERY_RECEIPT.json`; de to øvrige arkiver er dokumenteret i ankerjobbets `RECOVERY_RECEIPT.json`.

Bevar repository-layoutet med `tools/`, `results/` og `pilot_engine_20261008/`. Begge nye scripts bruger præcis `ROOT = Path(__file__).resolve().parents[2]`. Eksempelvis ligger scriptet `tools/radio_drift_anchor_20261010/drift_anchor.py` to mappeniveauer under repository-roden; dets hashbundne inputstier fortolkes fra denne rod. Det samme gælder `tools/radio_gap_drift_20261010/gap_search.py`. De to scripts må ikke flyttes alene til en anden mappe.

## Runtime og eksakt HDF5-miljø

Den registrerede runtime var Linux x86_64 med Python **3.12.14**, executable `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python`. `python3` i de oprindelige kommandoer anvendte denne runtime. Antallet af BLAS/OpenMP-tråde var begrænset med `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`.

| Komponent | Version | Brug og kontrol |
| --- | --- | --- |
| Python | 3.12.14 | Registreret executable og runtime |
| NumPy | 2.3.5 | Begge jobs; eksisterende installation bevaret |
| SciPy | 1.17.0 | Uændret detektor i gap-jobbet |
| Matplotlib | 3.10.8 | Fastlåst runtime; ankerfigurer |
| h5py | 3.15.1 | Gap-jobbets kompakte HDF5-input |
| HDF5 | 1.14.6 | Bibliotek bundtet i den kontrollerede h5py-wheel |
| hdf5plugin | 7.1.0 | Samme tidligere dokumenterede codec |

Ankerscriptet kontrollerer NumPy- og Matplotlib-versionerne. Gap-scriptet kontrollerer NumPy, SciPy, Matplotlib, h5py og hdf5plugin før analyse. Python- og HDF5-versionerne er registreret i miljøkvitteringen; de er ikke yderligere versionstests i de nye scripts.

Efter rydning af arbejdsområdet blev præcis den tidligere dokumenterede h5py/hdf5plugin-installation gendannet i en isoleret målmappe, `/workspace/scratch/a8d1e29996d0/seti_drift_context_work/deps`. Den eksisterende NumPy-installation blev ikke ændret. Det var samme versioner og samme wheels som i den tidligere miljøkvittering, uden et nyt decodeformat eller en alternativ installationsrute.

| Wheel | Bytes | SHA256 |
| --- | ---: | --- |
| `h5py-3.15.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` | 5109965 | `25c8843fec43b2cc368aa15afa1cdf83fc5e17b1c4e10cd3771ef6c39b72e5ce` |
| `hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` | 46397731 | `9d4cf36434819fae53e4da432f0287ebaeb02386ab97b73d261092efbab12247` |

De officielle fastbundne adresser er [h5py-wheel](https://files.pythonhosted.org/packages/3a/30/d1c94066343a98bb2cea40120873193a4fed68c4ad7f8935c11caf74c681/h5py-3.15.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl) og [hdf5plugin-wheel](https://files.pythonhosted.org/packages/26/56/3f788afb8d7fc451d20a66a64ea58bbe189f6f11780b28ba09148974fb33/hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl). Wheels er ikke bundtet. Den gemte officielle PyPI-metadata og HEAD-kvitteringer dokumenterer tilgængeligheden 10. oktober 2026; de er ikke et løfte om fremtidig tilgængelighed. Den efterfølgende miljøkvittering dokumenterer to faktiske GETs, hver én gang, med fuld byte- og SHA-kontrol før installation.

Miljøgendannelsen anvendte lokal wheel-installation med `--no-index --no-deps --no-cache-dir --no-compile --target`; ingen øvrige pakker blev installeret. Til en separat reproduktionskopi kan målmappe og wheelmappe placeres andetsteds, men de to wheelidentiteter, den øvrige runtime og kodepins skal bevares. Efter lokal kontrol af begge wheels var installationsformen:

```sh
python3 -m pip install --disable-pip-version-check --no-index --no-deps \
  --no-cache-dir --no-compile --target seti_drift_context_work/deps \
  seti_drift_context_work/wheels/h5py-3.15.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl \
  seti_drift_context_work/wheels/hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
```

Den faktiske installation brugte absolutte stier, registreret i `results/radio_gap_drift_20261010/ENVIRONMENT_RESTORATION.json`. Denne kvitterings SHA256 er `c4d5ffcf1bd6dd09549ff975cf6bb4b166c9d358b14703be2f8a5c2098da1c76`. Tilgængelighedsreviewets SHA256 er `417f2a466119458bf41c0b2c97f6599a6212e27ad42596a1044995c33815c77b`; det ligger i `results/radio_gap_drift_20261010/environment_evidence/EXACT_ENVIRONMENT_AVAILABILITY_REVIEW.json`. Samme mappe rummer metadata, HEAD-/GET-kvitteringer, gendannelseskode samt pip- og versionslog. Versionskontrollen importerer pakker via `PYTHONPATH` til den isolerede målmappe og åbner ingen HDF5- eller NPZ-værdier.

## Fastlåste kode- og metadataidentiteter

Alle stier i tabellerne er relative til repository-roden. Fuld SHA256 bruges i stedet for forkortede hashværdier.

| Fil | SHA256 |
| --- | --- |
| `tools/radio_drift_anchor_20261010/analysis_scope.json` | `f037f6b838ae964047584595b5ce79c5a3b7df4f2316c381c266c1c0d154ae0c` |
| `tools/radio_drift_anchor_20261010/drift_anchor.py` | `930a89ee67b4a417917e1874629a595a644f0727077af02bfb370f7f18f0dbb5` |
| `tools/radio_gap_drift_20261010/scope.json` | `c226ad41a87f344f71a642e0e7129657f00e44684db74d50124f075fd35d7a44` |
| `tools/radio_gap_drift_20261010/gap_search.py` | `b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58` |
| `tools/radio_fresh_band_20261009/source_manifest.json` | `d2e6c76b0d5fe50b26d45830e4b67e4780da97f33cfe8fcdf80c761f47aa3a4c` |
| `results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json` | `da165fe31ac4a70167b06f83b8f667fbb8604b595c642d3610fec68788bebf37` |
| `results/radio_fresh_band_20261009/stationary/NORMALIZATION.json` | `b7ec903775d522272607e83638adf68c02db95be5e2b613dd2f9ff839514fefc` |
| `results/radio_fresh_band_20261009/profiles/FIXED_TOP3_PROFILES.json` | `68bdf54dbabd7049954cf4ee625110aa122481cf57c3603854d77936e3decf1e` |
| `tools/radio_fresh_band_20261009/fresh_search.py` | `1a04ab1ea0d8b79b66ebc2a59a5c72b9c17b235f1a331ac19efeba90bade7102` |
| `tools/radio_fresh_band_20261009/analysis_scope.json` | `41f7bf4821a6f7da2e7c5b010fe26d20217db8e6ec7e02afc79ee23349df3271` |
| `pilot_engine_20261008/detector.py` | `1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45` |

### De ni gamle NPZ-input til ankerjobbet

Disse filer ligger i `results/radio_fresh_band_20261009/profiles/`. Hver er 165414 bytes. Det er de oprindelige tre valgte driftprofiler fra hver ON-scanning; der vælges ingen nye profiler til ankerjobbet.

| Fil | SHA256 |
| --- | --- |
| `epoch1_on_drift_rank_01.npz` | `a34fd16fe5a4b61cab99d0e97020f48cc4cc2a4c839eb91937b0d4bb45b530ce` |
| `epoch1_on_drift_rank_02.npz` | `93d8926b7a93828f9dc31f3d7374b08fcf3f2ceca9d461485b73fc953b12296a` |
| `epoch1_on_drift_rank_03.npz` | `8c40f5972dcb7106df5edb411aa6b59e238705545d0c8a5f7cbd8e9da009e3be` |
| `epoch2_on_drift_rank_01.npz` | `e5069d4df00a95dc46417348b340fbb96a3b00323a6106fdbb85066949c99877` |
| `epoch2_on_drift_rank_02.npz` | `b645c283961bf2407915e03309e6e14e2a88df054fbdef37833de8df4cefec8a` |
| `epoch2_on_drift_rank_03.npz` | `4c4d9179948fa331b8e1cd00536a2930678188b2e9b1f56b32c2d39a0e47a3c1` |
| `epoch3_on_drift_rank_01.npz` | `8398afd5c60f0b2b0f7515f743a9c57bb36ff940a964a2e531da8dcec35b7bc8` |
| `epoch3_on_drift_rank_02.npz` | `2e82687c296bed52241e8b8719b0d86d9e3d442f4d7a3a385b72e14bf635053c` |
| `epoch3_on_drift_rank_03.npz` | `85963980a7a8eccc2125562b4f8b82925d7a7b61deb930043fac8a506464b626` |

### De seks gemte HDF5-input til gap-jobbet

Filerne ligger i `results/radio_fresh_band_20261009/arrays/` og findes i det tidligere RAW-arkiv. Det uændrede indlæsningsled kontrollerer kompaktfilernes pins samt de dekodede rækkeidentiteter mod den gemte anskaffelsesmetadata.

| Fil | Bytes | SHA256 |
| --- | ---: | --- |
| `epoch1_on.compact.h5` | 50869783 | `d95d4b65bd8feb079f0c350ab09b26a912fcd3ecc89786f30400e1b288ec4a52` |
| `epoch1_off.compact.h5` | 50864012 | `cb544cee9d8fc67765c4c3b4a65372cf60b6fe7bbbbb9e3065a7448da2349689` |
| `epoch2_on.compact.h5` | 50867207 | `ed8bd68b502a79f0ce3bd45022149b1238d4f08e7b375ee9d6a91605a8ede78f` |
| `epoch2_off.compact.h5` | 50870439 | `07587eb15eab1f8128b31824837f6cc244106d3003c656aca585586cc22a15b3` |
| `epoch3_on.compact.h5` | 50866266 | `3d3187c9be44aee010c763da30ec95c2428a5525a0a46698ece0c857e8908eb0` |
| `epoch3_off.compact.h5` | 50867883 | `01b64853bcfd2b5418355d075ab40e66e83e7edd01bfaa0946797e53d837dc81` |

## De oprindelige numeriske kommandoer

Kommandoerne nedenfor blev kørt fra `/workspace/scratch/a8d1e29996d0`, som indeholder `setisearch_fresh/` og `seti_drift_context_work/`. De dokumenterer de allerede udførte jobs; de køres ikke igen som del af denne vejledning. En separat reproduktionskopi skal have samme relative inputlayout og eksakte pins. Begge scripts kræver, at outputmappen ikke allerede findes. Brug derfor særskilte, nye outputstier til en selvstændig reproduktion, så de gemte originalresultater bevares.

Det faste ankerjob:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 \
  setisearch_fresh/tools/radio_drift_anchor_20261010/drift_anchor.py \
  --scope setisearch_fresh/tools/radio_drift_anchor_20261010/analysis_scope.json \
  --expected-scope-sha256 f037f6b838ae964047584595b5ce79c5a3b7df4f2316c381c266c1c0d154ae0c \
  --outdir setisearch_fresh/results/radio_drift_anchor_20261010/measurement
```

Jobbet kopierer én fælles fysisk kontekst på `6 × 16 × 21` celler fra alle ni gamle udklip. Det kræver byte-identitet mellem alle ni rå og normaliserede kopier, eksakt gamle tider og kanalcentre samt eksakt normalisering med de gemte fuldudsnitsmedianer. De oprindelige driftcenterværdier kopieres uden genmåling. Den nye faste baggrund er medianen af 14 fysiske kanaler med absolut offset større end tre inden for ±10. Bredderne 1, 3, 5 og 9 er faste; ingen bedste bredde, drift eller frekvens findes. Bredde 9 overlapper baggrunden ved ±4. De gamle middelværdier med den oprindelige sporjusterede ±64-baggrund bevares i et separat felt.

Gap-jobbet:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=seti_drift_context_work/deps python3 \
  setisearch_fresh/tools/radio_gap_drift_20261010/gap_search.py \
  --scope setisearch_fresh/tools/radio_gap_drift_20261010/scope.json \
  --expected-scope-sha256 c226ad41a87f344f71a642e0e7129657f00e44684db74d50124f075fd35d7a44 \
  --compact-dir setisearch_fresh/results/radio_fresh_band_20261009/arrays \
  --acquisition-summary setisearch_fresh/results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json \
  --outdir setisearch_fresh/results/radio_gap_drift_20261010/measurement
```

De otte metadata-fastlåste gapindeks er `0, 4, 8, 12, 16, 20, 24, 28`. Relative startkanaler er `20480, 151552, 282624, 413696, 544768, 675840, 806912, 937984`, hver med 4096 referencekanaler. De er disjunkte fra de gamle 32 referencekanalfelter; læse- og sporhaloer kan overlappe. Detektoren og dens normalisering, ties, score og udvælgelsesregel er uændrede. Der søges 763 lineære drifthastigheder fra −4 til +4 Hz/s og bredder 1 og 3. Top-20 pr. ON gemmes; de tre øverste pr. ON giver ni nye profiler med frosset frekvens, drift og bredde i alle seks scanninger. Profilnormaliseringen bruger de allerede gemte fuldudsnitsmedianer; selve søgedetektoren bruger sin uændrede normalisering pr. referencekanalfelt. Ingen af disse to normaliseringer erstatter den anden.

## Kontrol af en reproduktion

Kontrollér først kode, scope, runtime og samtlige inputpins. SHA-feltet på kommandolinjen er obligatorisk og sammenholdes med det faktiske scope. Scripts kontrollerer også deres egen kodehash og de relevante inputafhængigheder. Hvis input, kontekst eller miljø afviger, stopper jobbet; der vælges ikke automatisk en erstatningsfil, en ny kanal, en ny version eller en retry.

Ankerjobbets originale `EXECUTION_RECEIPT.json` har status `COMPLETE_DESCRIPTIVE_ONLY`. Det registrerer alle ni inputhashes før og efter, byte-identiske fælles fysiske celler, eksakt bevarede normaliseringsmedianer og uændrede input efter kørsel. Resultaterne omfatter 24 faste scan/breddebeskrivelser, 54 oprindelige spor/scan-sammenligninger med alle 16 rækker, en NPZ med fulde arrays, JSON og tre figurer.

Gap-jobbets originale `EXECUTION_RECEIPT.json` har status `COMPLETED_EIGHT_GAP_DRIFT_CORES_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY`. Der skal være 24 færdige scan/felt-checkpoints med alle 4096 maksimumscores, vindende drift/bredde og gyldige hypoteseantal, tre top-20-lister og ni faste profiludklip. Den nye dækning er 32768 referencekanaler pr. ON; gammel plus ny dækning er 163840, dvs. 15,625 % af det gemte udsnit. Der produceres ingen figurer inde i gap-analysejobbet; eventuelle efterfølgende figurer har deres egen dokumenterede kontrol.

SHA-identitet kræves for indgange og frossen kode. PNG-, ZIP- eller kvitteringsbytes fra en selvstændig reproduktion kan variere med rendering, pakning og ressourcefelter; afvigende outputbytes må derfor undersøges efter deres betydning og må ikke alene behandles som en ændret videnskabelig måling. De oprindelige outputpins er bevaret i resultat- og pakningskvitteringerne.

## Ressourcer og fortolkningsgrænser

| Numerisk job | CPU-grænse, sekunder | Målt CPU, sekunder | Målt vægtid, sekunder | Maksimal RSS, bytes |
| --- | ---: | ---: | ---: | ---: |
| Fast anker | 40 | 1,61992847 | 1,62417332 | 129560576 |
| Otte nye felter og ni profiler | 90 | 73,861582975 | 73,896858674 | 491298816 |

Hvert job havde 1800 sekunders vægtidsgrænse og 4 GiB RAM-grænse. Frist- eller ressourceoverskridelse markeres som ufuldstændig uden numerisk retry. Tallene er processernes kvitteringsmål, ikke en måling af hele aktiviteterne; ankerets CPU-timer starter efter argumentbehandling, mens gap-kvitteringen medregner procesimporternes CPU.

Der blev reserveret 180 CPU-sekunder til ankeraktiviteten: 40 til analyse og 140 til klargøring, kontrol, pakning og offentliggørelse. Gap-aktiviteten reserverede 160: 90 til analyse og 70 til klargøring, miljøgendannelse, kontrol, pakning og offentliggørelse. Miljøgendannelsens målte lokale proceskomponenter var 9,162385 CPU-sekunder og 15,617521586 sekunders vægtid og indgår i denne klargøring; de debiteres ikke igen som en tredje aktivitet.

Den godkendte total er stadig 43200 CPU-sekunder, 4 GiB RAM, 8 GiB arbejdsplads og 0 DKK. Reservationerne er bevaret uden tilbageførsel. Efter de to nye reservationer resterer **62,705144981004196 CPU-sekunder**, hvoraf 60 er intern reserve til afsluttende kontrol. Lavere målte jobtider er ikke en tilbagebetaling af tidligere reservationer.

Gendannelse af de tre eksisterende arkiver overførte 592152992 arkivbytes. Miljøgendannelsen brugte 51507696 wheelbytes og 47145 officielle metadata-bodybytes; de to HEADs overførte nul bodybytes. Det konservative samlede kilde-, gendannelses- og afhængighedsregnskab er 1638958570 bytes. Det hidtidige teleskopkilde- og metadataregnskab for denne cadence er uændret, 611429683 bytes. De to jobs tilføjede **nul teleskoprequests, nul teleskopbytes og nul observationstid**. Arkivgendannelse og afhængighedsdownloads er ikke nye observationer.

Resultaterne er deskriptive og efter udvælgelse. Ni beslægtede gamle driftvarianter udgør ikke ni uafhængige signaler; korrelerede bredder, spor og delbånd er ikke uafhængige statistiske forsøg. Små værdier ved præcist forudsagte OFF-spor beviser ikke fravær af en nærliggende OFF-linje. Der er ikke implementeret et kvalificeret OFF-veto eller beregnet kalibreret SNR, falskalarmrate, flux, EIRP eller følsomhed. Den sparsomme driftsøgning er ikke en fuld søgning af frekvensudsnittet og kan ikke omsættes til et generelt nulresultat eller en bekræftelse af himmeloprindelse.
