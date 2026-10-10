# Datatilgængelighed og reproduktion — 10. oktober 2026

**Status:** De to 2016-grænsesøgninger, S2017 q128 og alle tre S2017-udvidelsesbatches er faktisk afsluttet og deres output-/kildekontroller er PASS. RAW-identiteterne er byteverificerede. Resultatarkivets navn er `SETI_FULL_POWER_RESULTS_2026-10-10.zip`; ekstern ZIP-størrelse, SHA og pakkekontrol dokumenteres i `DATA_PACKAGES.json` efter pakning. Dette dokument er ikke en upload- eller publiceringskvittering.

## Byteverificerede råarkiver

De fire 2016-arkiver blev restaureret fra eksisterende, gemte arkiver. Det skaber ingen nye teleskopsamples. ZIP-filerne er hash-kontrolleret i dette arbejdsrum og matcher deres oprindelige RAW-manifester.

| Arkiv | Bytes | SHA256 |
|---|---:|---|
| `SETI_NATIVE154_RAW_2026-10-10.zip` | 306093326 | `62425c70dc903a425e9b0a1837f9ddbf1654b0af057c97695c690e56ec657ce3` |
| `SETI_NATIVE155_RAW_2026-10-10.zip` | 306160238 | `e461a39d378a3397022febb99a922a29d375654072ad573fe847a174728e7082` |
| `SETI_NATIVE157_RAW_2026-10-10.zip` | 303960152 | `ffc61097a4deb417fec2b985a189aabb510646f7f87b7c1a904ebe5acbdd64ab` |
| `SETI_NATIVE158_RAW_2026-10-10.zip` | 300926307 | `2a317a1673e74d4fbd557c2cc8935a0376e06a6eac17738359073ca4f68c8b5c` |
| `SETI_S2017_NATIVE171_RAW_2026-10-10.zip` | 466351822 | `6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786` |

Lokalt ligger de fire første i `sources/raw/` og det nye arkiv i `output/`. De oprindelige 2016-identiteter er dokumenteret i `analysis/repo_state/results/**/chunkNNN/raw_checkpoint/RAW_CHECKPOINT_ARCHIVE_MANIFEST.json`. Det nye arkiv er dokumenteret i `analysis/delivery/RAW_PACKAGE_RECEIPT.json`: `PASS_ARCHIVE_CRC_AND_ALL_MEMBER_SHA256`, 593 medlemmer, 592 payloadfiler, 471787372 ukomprimerede bytes.

S2017-RAW indeholder seks bevarede delvise HDF5-filer fra den fejlede oprindelige indlæsning og seks korrigerede komplette HDF5-filer samt kilde/headermetadata, kode, scopes, fejlevidens og integritetskvitteringer. Det indeholder **ingen NPZ-science-output**. De 96 komprimerede raw-range-sidecars er redundante med HDF5-blokkene og gemmes derfor ikke alle dobbelt i ZIP'en. Deres eksakte stier, størrelser og SHA'er findes i den korrigerede acquisition-receipt og kan genskabes uden HTTP eller afkodning af observationsværdier.

Efter udpakning med bevarede relative stier, fra arkivets rod:

```sh
python3 analysis/delivery/reconstruct_raw_sidecars.py
```

Vejledningen `analysis/delivery/RAW_REPRODUCTION.txt` har SHA256 `ea163f612ed534e90d20458b29c0a13e840813b01204ad01552007bf9f2a0e41`. Rekonstruktionen bruger h5py til at læse de allerede gemte komprimerede HDF5-blokke og kontrollerer deres SHA; den foretager ingen netværkshentning og ingen science-søgning.

Alle 27 oprindeligt modtagne S2017-payloads overlevede, heraf den sidste som en uindekseret suffix. Kun 69 tidligere uafprøvede kilde-ranges blev hentet senere. Det kumulative forbrug er 96 GETs, 298238620 modtagne telescope BODY-bytes og 298238716 reserverede upper-bound BODY-bytes. Der var nul gentagne GETs. Hele oprindelige telescope-file MD5'er er uverificerede; metadata, stærke ETags, eksakte HTTP206-ranges, komprimerede blokhashes og afkodede rækkehashes autentificerer de bevarede udsnit.

## Afsluttede execution- og QA-kvitteringer

Alle stier er relative til det rekonstruerede arbejds-/arkivtræ.

| Kvittering | SHA256 |
|---|---|
| `analysis/continuation/project/results/continuation_boundaries_20261010/pair154_155/measurement/EXECUTION_RECEIPT.json` | `ca768196efcd1ee360f2da352ab10c6d8a247d8eb92e3b89390d4103313bc55e` |
| `analysis/continuation/project/results/continuation_boundary_recovery_20261010/pair157_158/measurement/EXECUTION_RECEIPT.json` | `71896ef39541d3f03ff0a9a184d4f2f5416583f50f4bbf0fb377c4da2eaec83f` |
| `analysis/continuation/project/results/continuation_boundaries_20261010/review/QA_RECEIPT.json` | `c76932358e8bc5d3f53b3a66e0086c44287c4f81e76cb3b4d6c313cffcb8a97d` |
| `analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json` | `e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf` |
| `analysis/new_visit_recovery/results/search/EXECUTION_RECEIPT.json` | `3fe2b007a552b149a68f5d81bde3f9911c8d4ba0d3a31695356c76706cf7f27f` |
| `analysis/new_visit_recovery/results/review/QA_RECEIPT.json` | `e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f` |
| `analysis/s2017_full_band/results/batch01/EXECUTION_RECEIPT.json` | `b94f5b640fd73f36dfe04c3f362b7e76e0dc7d0f9aa56e90def9f879bb2672d8` |
| `analysis/s2017_full_band/results/batch02/EXECUTION_RECEIPT.json` | `ef5ac61e4a2a949fc9d056561f91d3c130755abe8254264fecb4ca3edb21ca81` |
| `analysis/s2017_full_band/results/batch03/EXECUTION_RECEIPT.json` | `639643106f3aeffbd88bff1d88326f6a91ce1ebcf291d518198bc418d9a56d92` |
| `analysis/s2017_full_band/results/review/QA_RECEIPT.json` | `e1d77ef88fa7a47965bd783b09258b36578c476cd5788ffc94924f3e03d1bc6f` |
| `analysis/s2017_full_band/summary/FULL_BAND_SUMMARY_RECEIPT.json` | `5387e497d6654590ee23a48d39bb681d250bb082029d0d810e8c0b0909ddf43c` |
| `analysis/s2017_full_band/summary/FULL_BAND_SUMMARY.json` | `d7ffd5c831b46649cebfc6e85aa05c11a701a8fada382ad290c79cb9f7da62c2` |
| `analysis/s2017_full_band/summary/FULL_BAND_PROFILE_MEANS.csv` | `c0cc85517398267102a0cbfb3b9e953be06a9bd836ad0cd3938ca48900dbde8b` |
| `analysis/s2017_full_band/FULL_BAND_SCIENTIFIC_REVIEW.json` | `6d2712b842b766f47d1344ab16b2505341b0ae26641dc74aee5c670db1796b03` |

Den bevarede oprindelige S2017-fejl ligger i `analysis/new_visit_search/results/acquire/ACQUISITION_RESULT.json` og `FAILURE_RECEIPT.json`, begge SHA `37e2fcdb66dfe4187dd6a43f067879cdc4e6cf3bfb7dae6c877cb0fcafdf33f6`. Den oprindelige 154/155-låsfejl har SHA `734461b686eadae88454d96f2b4b9e360fab5f5a3769546ddd6af1ae11b9778e`; fortsættelsens 157/158-låsfejl har SHA `854cf95f2dd130ab3d19da992be008212ac55229d25f13ab3acc92b53f326a98`. Gamle fejlede eller afsluttede namespaces må ikke genbruges, redigeres eller ommærkes som nye execution-receipts.

## Kode, scopes og offentlige fastfrysninger

Repository: [andersenmartin-blip/setisearch](https://github.com/andersenmartin-blip/setisearch), analysegren `m43-support-qualification`. En fastfrysning dokumenterer prospektiv kode/scope; afslutning kræver de faktiske execution- og QA-receipts ovenfor.

| Afsluttet familie | Public freeze commit | Scope SHA256 | Driver SHA256 |
|---|---|---|---|
| 2016 grænse 154/155 | `627d5254ae218f272ea81a2008ada77ca87a6dd2` | `8127b5c5d11c157395f4f91816397a1875cdbc8e2b2812b174963ca93887ca6e` | `c98ab98bf425a0f15813682ebdd58cd14f737d7c86e5e6b79790523c1372ae60` |
| 2016 grænse 157/158 | `1ce3be5a57c53279702e1604165e037636e9e68b` | `143c2262ebe72bb99a92aac137bd1ef5eb1fc85be2804b5a098e0635f725985e` | `38cf4220413eca40959971c76a9bfebed06d5ffa7eaa71ff1af0326e6a2fb0e7` |
| S2017 rettet acquisition og q128 | `e8ada3c888d1f07b33d25dccb9f7ddc0c7d23995` | `a93d6dda3f813b84be2452928fe42be76b6de3cb96cf4f85c9beda47adc9ea86` | `ca9c3890a8be325061e62c03b05aa795a582fc7d10012f0a565d8779920e6bf6` |

S2017-udvidelsen er offentligt fastfrosset i commit `76fb1da5a0af22d6182daed90e4bdca92f2470f8`, med fælles driver `analysis/s2017_full_band/driver.py`, SHA256 `5ce9d5f861e06691183cf43fd4351bfe8a09b97763c3bd23add82ad338864554`.

| Udvidelsesscope | Kerner pr. ON | Scope SHA256 |
|---|---:|---|
| `analysis/s2017_full_band/scopes/batch01.json` — q1–84 | 84 | `551083a9ba56bf960fa49e8868047f8016ba9a70a3a7b1df1a54333af8d56c9c` |
| `analysis/s2017_full_band/scopes/batch02.json` — q85–127 og q129–169 | 84 | `d9b499662e8766058a74ac794225fd95a34d208a07f5a7e289ce306e8c957d68` |
| `analysis/s2017_full_band/scopes/batch03.json` — q170–254 | 85 | `72c82c8fb36c26ce2f22d68d5e57a34e7c841ab7e0c83050f5b67e8f1459f759` |

Stier: `analysis/continuation/continue_boundaries.py`, `scope.json`, `recovery157158.py`, `recovery157158_scope.json`; `analysis/new_visit_recovery/driver.py`, `raw_acquire.py`, `scope.json`. Metadata-pins i scopes binder det uændrede detektor-, profil- og reader-kodesæt.

De faktiske output/kildekontroller bruger `analysis/continuation/qa_continuation.py` (SHA `8bd4b8a0b7851ac2c5f20bf168716b7e67c6bb66694d6691b1bdd7613ed19d35`) og `analysis/new_visit_search/qa_saved_outputs.py` (SHA `2f70b95aec9237e5a7bec689e339980893ececee4bc8d9373cfdf636059b8b00`). Udvidelsen bruger `analysis/s2017_full_band/qa_saved_outputs.py`, SHA256 `a1573fd36df4ee685cbafbaec429c0dd7b63efc9586e41825cbef3e2857340e3`. De rekonstruerer gemte top-ranks, validerer profiler og rå kildeceller og gør ingen detektor-/score-genkørsel. `QA_SOURCE_REVIEW.json` er statisk kodegennemgang; den faktiske numeriske kvittering hedder `QA_RECEIPT.json`.

2016 bruger 763 driftværdier fra −4 til +4 Hz/s og bredder 1/3. S2017 bruger 785 værdier og samme bredder. Geometrien bruger oprindelige absolutte source-kanaler, negativ df, `numpy.rint` og faktiske tstart/tsamp-headerdata. Detektorens normalisering er kernebaseret; den gemte profilnormalisering er median over alle 2097152 joinede kanaler for de nye grænseprofiler og alle 1048576 native-kanaler for S2017, beregnet på rå float32 før profilernes float64-promotion. Disse forskellige nævnere må ikke blandes.

## Fastlåst runtime og lokal reproduktion

`analysis/runtime/EXACT_DEPENDENCY_RESTORATION.json` (SHA `68ada62fc8d95d4b6337933f404dd6370ec7aac6fb9fe358bbb0bbd04224a918`) dokumenterer Python3.12.14, NumPy2.3.5, h5py3.15.1, HDF51.14.6 og hdf5plugin7.1.0. S2017-execution binder desuden SciPy1.17.0; de eksisterende figurer anvender Matplotlib3.10.8.

RESULTS-pakkens payloadspecifikation medtager hele `analysis/runtime/`, herunder de to eksakte wheels (tilsammen 51507696 bytes), installationsreceipt, log og restore-script. Den endelige ZIP-kontrol dokumenteres eksternt i `DATA_PACKAGES.json` efter pakning. Python3.12.14, NumPy2.3.5, SciPy1.17.0 og Matplotlib3.10.8 samt et kompatibelt Linux x86_64-miljø skal fortsat leveres udenfor disse to wheels. Der hævdes **intet fuldt hermetisk runtime-arkiv**.

De to uændrede officielle wheels er:

| Wheel | Bytes | SHA256 |
|---|---:|---|
| `h5py-3.15.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` | 5109965 | `25c8843fec43b2cc368aa15afa1cdf83fc5e17b1c4e10cd3771ef6c39b72e5ce` |
| `hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` | 46397731 | `9d4cf36434819fae53e4da432f0287ebaeb02386ab97b73d261092efbab12247` |

Installationsreceipt giver de officielle URL'er og det faktiske argv: `pip install --no-index --no-deps --no-cache-dir --no-compile --target analysis/deps <de to eksakte wheels>`. NumPy blev bevaret. Brug det dokumenterede miljø med `PYTHONPATH=<rekonstrueret-rod>/analysis/deps`; hdf5plugin er nødvendigt for afkodet power-kontrol, h5py alene kan læse direkte komprimerede blokke.

Praktisk rækkefølge: verificér ZIP-SHA og det relevante payloadmanifest. Det nye S2017-arkiv bruger `PACKAGE_MANIFEST.json`; de fire 2016-RAW-arkiver bruger deres indlejrede `RAW_CHECKPOINT_PAYLOAD_MANIFEST.json` og eksterne `RAW_CHECKPOINT_ARCHIVE_MANIFEST.json` til ZIP-identiteten. Pak ud i et særskilt træ med bevarede relative stier; rekonstruér S2017-sidecars; verificér kode/scopes/runtime og komplette inputhashes; inspicér de eksisterende execution/QA-receipts og gemte kort/profiler. 2016-RAW-arkivernes `RAW_CHECKPOINT_REPRODUCTION.md` dokumenterer deres oprindelige native-search-kommandolinjer.

En særskilt offline beregningsreproduktion skal bruge en ny tom outputkopi og beholde alle oprindelige receipts urørte. De bevarede one-shot-driveres directory-gates og root-GO-parametre er historiske eksekutionskontroller; de er ikke en blanketinstruktion til at genkøre de historiske jobs. Ingen ny HTTP-erhvervelse eller genkørsel er nødvendig for at verificere eller se de allerede gemte resultater. Historiske absolutte workspace-stier i receipts forbliver bevaret; ved læsning på en anden maskine kan deres gamle rod fortolkes i det udpakkede træ uden at ændre arkivbytes eller claimede checksums.

## Faktiske tællere og reproduktionsafgrænsning

Udvidelsens tre COMPLETE-jobs giver 759 kort, 3.108.864 gemte ON-kanal-maksima, 4.880.916.480 korrelerede drift-bredde-kombinationer, 180 separate top-20-rækker og 27 faste profiler/162 scan-profiler. Faktisk samlet QA er `PASS759_S2017_MAPS27_FIXED_PROFILES_AND334368_BITWISE_SOURCE_CELLS`: alle 334.368 rå celle-forekomster, 96 kilde-rækkehashes og 12.144 ON-kernerækkemidianer blev kontrolleret. De 96 fuldrækkemidianer var allerede genberegnet i den faktiske q128-QA og blev hashautentificeret i udvidelses-QA. Hver kontrol rekonstruerer saved ranks og profilregning; ingen af dem genkører detektorscores.

q128 plus udvidelsen giver 254 referencekerner pr. ON, 762 kort, 1.040.384 referencekanaler pr. ON, 3.121.152 ON-kanal-maksima, 4.900.208.640 korrelerede kombinationer, 36 faste profiler/216 scan-profiler og 445.824 bitkontrollerede rå celle-forekomster. De 240 top-20-rækker stammer fra fire separate familier; der er ingen ny samlet global rank-udvælgelse. Referencebåndbredden er 2.906.799,31640625 Hz, 99,21875 % af ét erhvervet native171-udsnit på 2.929.687,5 Hz. q0/q255 er usøgte. Tallet beskriver ikke fuldt teleskop-S-bånd eller følsomhed.

2016 og S2017 tilsammen: 774 kort, 3.170.304 maksima, 4.975.214.592 korrelerede kombinationer, 54 faste profiler/324 scan-profiler, 5.184 integration-række-forekomster og 668.736 bitkontrollerede rå celle-forekomster. Forekomster er ikke unikke kildeceller. De 90 ældre profiler i den separate OFF-kontekst er ikke medregnet som nye søgninger.

Batch01/02/03 bruger faktisk henholdsvis 468,237484036/465,514561239/469,011888958 CPU-s; summen er 1.402,763934233 CPU-s. Den samlede udvidelses-QA bruger 4,464805467 CPU-s, 4,414700554 wall-s og 156.336.128 peak RSS-bytes. Jobs var begrænset til 1.000 CPU-s, 1.800 wall-s og 2 GiB AS pr. proces med højst to samtidige jobs, samlet 4 GiB AS. QA havde 180 CPU-s / 1.800 wall-s / 4 GiB AS-loft. AS-lofter er ikke målt RSS, og batchernes summerede wall-tider er ikke et målt ende-til-ende elapsed-tal. q128 og udvidelsen brugte ingen ny HTTP under søgning eller QA, og q128 blev ikke genkørt under udvidelsen.

Den afsluttede rapport `RADIO_FULL_POWER_2026-10-10_RESULT.md` beskriver ON/OFF-kontekst og begrænsninger. S2017 er ét andet historisk besøg i et andet frekvensbånd, ikke samme-frekvens-replikation af 2016. Ingen scorekalibrering, qualified OFF-veto, fysisk oprindelsesafgørelse eller generel nuldetektionsgrænse følger af filintegritetskontrollen. A/B-status er uændret `FAIL_CLOSED`.

## Pakkeidentitet og historik

Det nye resultatarkiv hedder `SETI_FULL_POWER_RESULTS_2026-10-10.zip`. Dets ZIP-størrelse og SHA256 skal stå i den eksterne `DATA_PACKAGES.json` ved siden af rapporten, sammen med paknings-/medlemskontrol. Resultatarkivets egen checksum indlejres ikke i dets payload. Det indlejrede medlemsmanifest autentificerer payloadfilerne; den eksterne ZIP-SHA autentificerer arkivet. Dette dokument gør ingen påstand om gennemført arkivoprettelse, upload eller publicering.

De tidligere saved-result ZIPs under `sources/` er bevaret evidens for 2016-konteksten. RAW-pakkerne holdes adskilt fra science-NPZ-output. Originale COMPLETE-, FAIL- og static-review-receipts samt mellemfastfrysninger bevares med deres oprindelige bytes/status; den aktuelle afslutning afgøres af de faktiske nyere execution-/QA-/science-kvitteringer. Historiske statusfiler skrevet før QA er ikke nye fejl eller slutadmissioner. De to tidligere tekstversioner med suffix `_DRAFT`/`report_draft` er bevaret som arbejdshistorik og er ikke slutrapporten.
