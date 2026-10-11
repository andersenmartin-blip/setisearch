# Offentlig evidens — burstpilot 11. oktober 2026

**288 burst-søgekort, 1.179.648 gemte kanalmaksima og 54 faste kontekstprofiler er afsluttet. Begge numeriske QA-kørsler og rapportens figurer har bestået kontrollen.** Piloten anvender syv overlappende vinduer med fire integrationer (73,014 sekunder) i de eksisterende OFF-scanninger af HIP97319, HIP97461 og HIP97663 fra 28. april 2017. Hver retning omfatter 96 på forhånd fastlagte frekvenskerner, cirka 12,5 % af de 766 tidligere undersøgte kerner.

Det højeste gemte maksimum er **7,315816** i HIP97663 ved 2302,264352 MHz. Det er en empirisk søgescore; ingen kalibreret sigma-værdi eller falsk-alarm-sandsynlighed er etableret. Ni udvalgte spor er målt uden refit i alle seks oprindelige scanninger på fire retninger, med separate fire-række- og fulde 16-række-scorer. **Ingen kvalificeret SETI-detektion, ny frekvensdækning, ny observation eller blind validering er etableret.** Scanninger af andre stjerner er ikke gentagelser af samme mål.

Den uændrede detektor normaliserer fortsat på alle 16 rækker; ingen ny OFF-maske eller OFF-veto er anvendt. QA omfatter 1.161 gemte primære råscoreforespørgsler, 54 kontekstprofiler/108 scorer og ni match til de oprindelige fire-række-scorer. Kontrollen af den endelige score er betinget af de gemte normaliseringskonstanter og udgør ikke en uafhængig genkørsel af hele søgegitteret.

Resultatpakken er på **86.496.254 bytes**, med **1.939 arkivmedlemmer** kontrolleret med CRC og SHA256. Den indeholder alle nye kort og råkapsler; de 18 originale H5-kompakter er eksterne forudsætninger. Den offentlige gren indeholder kildekode, rapporter, figurer og kontrolkvitteringer, mens hele array-pakken er bevaret separat. Udgift: **0 DKK**.

Den prospektivt fastlagte primærkilde blev publiceret i commit `6bd6b6982ffeb2c9de4b834145fddc5316bf8d2a`. De ni udvalgte kontekstspor blev fastlagt i `0147020c1b61db278094a9414046f1599d63bf48`. Rapportforsøg 1 fejlede før leverance; kilden og fejlen er bevaret. Separate præsentationsversioner 2 og 3 ændrer ikke søgning, rangering eller numeriske resultater. Version 3 retter alene overlappende figurtekst.

## Indhold på denne gren

Tabellen identificerer de 71 kilde- og evidensfiler ved byteantal og SHA256. Hele 288-map-array-sættet, 1.161 primære råkapsler, 54 kontekstkapsler og per-core-normaliseringer findes i resultatpakken. De er ikke udlagt som arrays på GitHub i denne publicering. Dekoderhjul og nødvendige tidligere kildefiler er med i pakken; de oprindelige 18 H5-kompakter skal tilføres eksternt. Pakkeidentiteten er dokumenteret i den separate resultatpakkekvittering, der er oprettet efter arkivet og derfor ikke ligger inde i arkivet.

| Fil | Bytes | SHA256 |
|---|---:|---|
| [analysis/burst4_20261011/PREPARATION_RECEIPT.json](../../analysis/burst4_20261011/PREPARATION_RECEIPT.json) | 460 | `79075d7e52ebd5059352ade72b245d0b68bb2113dd7d0df5301455f7ee6da952` |
| [analysis/burst4_20261011/PROTOCOL.md](../../analysis/burst4_20261011/PROTOCOL.md) | 3039 | `60826dcc34caa88b9e34a66cdae2cbe623f4f5e5e739617a93f971e7bd20fdac` |
| [analysis/burst4_20261011/PUBLIC_FREEZE.json](../../analysis/burst4_20261011/PUBLIC_FREEZE.json) | 4041 | `6c7e00276ec9f47dcc67d92a9aaafb9d935de2f17cd9e4ac3f62bbeffe0af160` |
| [analysis/burst4_20261011/REPRODUCTION_AND_DATA_AVAILABILITY.md](../../analysis/burst4_20261011/REPRODUCTION_AND_DATA_AVAILABILITY.md) | 12579 | `0647a519a57571fa978b2703eb6f6cb90d9412786ada857cd0e3016d73b70e5d` |
| [analysis/burst4_20261011/ROOT_GO.json](../../analysis/burst4_20261011/ROOT_GO.json) | 989 | `7ac0077bce0dee73915fa3b3a123215166ffb113e7b2a0eab83a5eb637f2d6b5` |
| [analysis/burst4_20261011/build_delivery.py](../../analysis/burst4_20261011/build_delivery.py) | 16555 | `ddbf3759ec3e5cfea1dfd968739fda3991f731d7842839b728671ae9564b57e5` |
| [analysis/burst4_20261011/driver.py](../../analysis/burst4_20261011/driver.py) | 30409 | `5cda139f404a29fa96659e46237bad2978588920da019198ba3e21009cea1d84` |
| [analysis/burst4_20261011/prepare_scope.py](../../analysis/burst4_20261011/prepare_scope.py) | 3723 | `0e8db7c6b32660f85187519e7dba2c4b7fc8abf1aac35e523e21974cf2e751b6` |
| [analysis/burst4_20261011/results/primary20170428_HIP97319/EXECUTION_RECEIPT.json](../../analysis/burst4_20261011/results/primary20170428_HIP97319/EXECUTION_RECEIPT.json) | 122142 | `85afe9fed2305dcc477908bc3101fca355a8f444f04a8a36c1dc8b35a947d9da` |
| [analysis/burst4_20261011/results/primary20170428_HIP97319/MAPS.json](../../analysis/burst4_20261011/results/primary20170428_HIP97319/MAPS.json) | 77646 | `7418aaec31dfeaf5098b5f556e40d0f5a034fab423175ffd43e474752642e408` |
| [analysis/burst4_20261011/results/primary20170428_HIP97319/SCORE_AUDITS.json](../../analysis/burst4_20261011/results/primary20170428_HIP97319/SCORE_AUDITS.json) | 429687 | `3a93bcd76fc58cc7daccb76edba279f86b71d4111af7cf2010bcc75a9036dad2` |
| [analysis/burst4_20261011/results/primary20170428_HIP97319/TOP20.json](../../analysis/burst4_20261011/results/primary20170428_HIP97319/TOP20.json) | 11228 | `7345331559a375a916a800fc53bc655744e6b331653325f4bf2a9c503c1d71ee` |
| [analysis/burst4_20261011/results/primary20170428_HIP97319/TOP3.json](../../analysis/burst4_20261011/results/primary20170428_HIP97319/TOP3.json) | 1945 | `bfc980e6c3cd327b2721af18eb185ab6857a797f437a26ed479a8182bc556e7a` |
| [analysis/burst4_20261011/results/primary20170428_HIP97461/EXECUTION_RECEIPT.json](../../analysis/burst4_20261011/results/primary20170428_HIP97461/EXECUTION_RECEIPT.json) | 122142 | `b77009df7413305060694396322c6859da1f65e860652052f0db987095032b26` |
| [analysis/burst4_20261011/results/primary20170428_HIP97461/MAPS.json](../../analysis/burst4_20261011/results/primary20170428_HIP97461/MAPS.json) | 77646 | `45e2b0794ab699a03cf11422cc29522254cc8e8394a6cd5428e66278b086dd24` |
| [analysis/burst4_20261011/results/primary20170428_HIP97461/SCORE_AUDITS.json](../../analysis/burst4_20261011/results/primary20170428_HIP97461/SCORE_AUDITS.json) | 429469 | `2d5fdf216509550c466efc2526986b880a44d107f984bb54a86dc7865e6919b8` |
| [analysis/burst4_20261011/results/primary20170428_HIP97461/TOP20.json](../../analysis/burst4_20261011/results/primary20170428_HIP97461/TOP20.json) | 11184 | `02ac80d9f089d353768333e3f7381448627d2ac4ef021bd4ec7b667fd423c02e` |
| [analysis/burst4_20261011/results/primary20170428_HIP97461/TOP3.json](../../analysis/burst4_20261011/results/primary20170428_HIP97461/TOP3.json) | 1927 | `bbbf6569c67176f41e074ac3ea21b206e22283b53a241dc1900b19710f78b054` |
| [analysis/burst4_20261011/results/primary20170428_HIP97663/EXECUTION_RECEIPT.json](../../analysis/burst4_20261011/results/primary20170428_HIP97663/EXECUTION_RECEIPT.json) | 122143 | `cf67139260c02ffbb1038d094245a555f04e1ce40a97a23c44696f8b268f0022` |
| [analysis/burst4_20261011/results/primary20170428_HIP97663/MAPS.json](../../analysis/burst4_20261011/results/primary20170428_HIP97663/MAPS.json) | 77646 | `71176fd163624a6fe0e974ed2809e353352a8a37cecf5948dc4ceff9f9103c7d` |
| [analysis/burst4_20261011/results/primary20170428_HIP97663/SCORE_AUDITS.json](../../analysis/burst4_20261011/results/primary20170428_HIP97663/SCORE_AUDITS.json) | 429650 | `65f1a684c140e038bb87f034175fa26a6a730f0653bc1b80cb37364d8f6be613` |
| [analysis/burst4_20261011/results/primary20170428_HIP97663/TOP20.json](../../analysis/burst4_20261011/results/primary20170428_HIP97663/TOP20.json) | 11205 | `fbe9d2a4aa77ff95cba91e8df684eb8ca6affdc1dc7b219e7b469ebc9db32de1` |
| [analysis/burst4_20261011/results/primary20170428_HIP97663/TOP3.json](../../analysis/burst4_20261011/results/primary20170428_HIP97663/TOP3.json) | 1937 | `0a4ac885972ef0dd4074ed6ffc7e5b22a7bee479581ca30b0ade70e00ccd36b1` |
| [analysis/burst4_20261011/scope.json](../../analysis/burst4_20261011/scope.json) | 44518 | `7352992e3f31e92267b12618cbe3a0d4c02fd022760a97ae30f0aeaf1a65da41` |
| [analysis/burst4_20261011_context/CONTEXT_FINISH_REPORT_V2_STATIC_REVIEW.json](../../analysis/burst4_20261011_context/CONTEXT_FINISH_REPORT_V2_STATIC_REVIEW.json) | 2256 | `4a68b291f970acc6d79f9145284465167e2bbffaa9ae2dac8a30fb0d2ca50e01` |
| [analysis/burst4_20261011_context/CONTEXT_QA_RECEIPT.json](../../analysis/burst4_20261011_context/CONTEXT_QA_RECEIPT.json) | 36619 | `a22113a685187032f320eff935871c0dad9203e91554fdf6f288ab2f2fd48e3e` |
| [analysis/burst4_20261011_context/CONTEXT_SCOPE_PUBLIC_FREEZE.json](../../analysis/burst4_20261011_context/CONTEXT_SCOPE_PUBLIC_FREEZE.json) | 1538 | `646edf98ce3bae63b7d1179459afc04cfc74842ad7fd9497bf788d116f682497` |
| [analysis/burst4_20261011_context/FINAL_REPORT_V3_VISUAL_REVIEW.json](../../analysis/burst4_20261011_context/FINAL_REPORT_V3_VISUAL_REVIEW.json) | 4047 | `4c7a25832abe328784adfe38e1a092494d58eebcf67dc0fe41cc230fc3f0bdf2` |
| [analysis/burst4_20261011_context/FINAL_REPORT_VISUAL_REVIEW.json](../../analysis/burst4_20261011_context/FINAL_REPORT_VISUAL_REVIEW.json) | 7248 | `2a8031e21e95bbb446e0ebe8e780cc9a9cf2f8d93559b766c4579ab54a30fc7e` |
| [analysis/burst4_20261011_context/METADATA_AUDIT_2016_RAW.json](../../analysis/burst4_20261011_context/METADATA_AUDIT_2016_RAW.json) | 4821 | `650fd0059cf3a63f5ac2be246dbb2dbb23c0cd39629a0085b757cf7951ea98eb` |
| [analysis/burst4_20261011_context/REPORT_ATTEMPT1_FAILURE.json](../../analysis/burst4_20261011_context/REPORT_ATTEMPT1_FAILURE.json) | 603 | `7b92db113b8b018201c622ee904cd468de8a8d82374723447e6870162ae1d495` |
| [analysis/burst4_20261011_context/REPORT_PRESENTATION_REVISION.json](../../analysis/burst4_20261011_context/REPORT_PRESENTATION_REVISION.json) | 686 | `241d3a6b7b356a84774decf02f4014089217d53f525e09e9e38bf9921988d284` |
| [analysis/burst4_20261011_context/REPORT_V2_PUBLIC_FREEZE.json](../../analysis/burst4_20261011_context/REPORT_V2_PUBLIC_FREEZE.json) | 1140 | `79b2645aad4a62521fd5f7d294b88815ea34a3194392076976f9f9f4fab50c54` |
| [analysis/burst4_20261011_context/REPORT_V2_REPRODUCTION.md](../../analysis/burst4_20261011_context/REPORT_V2_REPRODUCTION.md) | 1423 | `879a533708b79fd7686beceaf65923e6af4e2c4a5324c26f3080a3e732b2808f` |
| [analysis/burst4_20261011_context/REPORT_V3_PUBLIC_FREEZE.json](../../analysis/burst4_20261011_context/REPORT_V3_PUBLIC_FREEZE.json) | 679 | `7aa214429d6ce4b437358bb8aadbc66ae04f8af029ea7bce733f3eb9ec033f4b` |
| [analysis/burst4_20261011_context/ROOT_GO.json](../../analysis/burst4_20261011_context/ROOT_GO.json) | 523 | `941603e9978e31cb279326fdcccbf4ee4bd6093e7ce2d02be14bfc16c8e1cb5c` |
| [analysis/burst4_20261011_context/ROOT_V3_VISUAL_REVIEW.json](../../analysis/burst4_20261011_context/ROOT_V3_VISUAL_REVIEW.json) | 1922 | `28f5f7a75027ee4a49a8b5dd14ac6df14ccf3e0b44975a903a0a3a659bf4d4f9` |
| [analysis/burst4_20261011_context/ROOT_VISUAL_REVIEW.json](../../analysis/burst4_20261011_context/ROOT_VISUAL_REVIEW.json) | 1337 | `fd9fdc1aae237536c36930a0a621a3280aad600976aae2c123e2564fa6d1b038` |
| [analysis/burst4_20261011_context/context_profiles.py](../../analysis/burst4_20261011_context/context_profiles.py) | 27101 | `d27d8180754641ed15ae1ee260943f948c06edc0885be429a64ff3f4d56661c0` |
| [analysis/burst4_20261011_context/context_scope.json](../../analysis/burst4_20261011_context/context_scope.json) | 18413 | `2d7b4d26397fb834782a8eac20445757579b8af806a7be58770d4644262b3903` |
| [analysis/burst4_20261011_context/delivery/CONTEXT54.csv](../../analysis/burst4_20261011_context/delivery/CONTEXT54.csv) | 4693 | `acd92619b3ca6077b8a18534b74237307e00d55446663db5597407d96a879a57` |
| [analysis/burst4_20261011_context/delivery/REPORT_RECEIPT.json](../../analysis/burst4_20261011_context/delivery/REPORT_RECEIPT.json) | 4031 | `70b986d153f43a4b46138f0bbad4895fd8b8b0b830d558fbf68c6e8937d7a027` |
| [analysis/burst4_20261011_context/delivery/SETI_BURST4_CONTEXT54_2026-10-11.png](../../analysis/burst4_20261011_context/delivery/SETI_BURST4_CONTEXT54_2026-10-11.png) | 507603 | `a796003a16c37bae603475a4b5d5fbe80e2c1eeaac6d8b39c7b4a3587f1fcab0` |
| [analysis/burst4_20261011_context/delivery/SETI_BURST4_FINAL_2026-10-11.md](../../analysis/burst4_20261011_context/delivery/SETI_BURST4_FINAL_2026-10-11.md) | 5092 | `b4d8721707c4ba717c1de294649520d0b0436ac16b31b08e8559af66333f3d27` |
| [analysis/burst4_20261011_context/delivery/SETI_BURST4_ROW_CONTRIBUTIONS_2026-10-11.png](../../analysis/burst4_20261011_context/delivery/SETI_BURST4_ROW_CONTRIBUTIONS_2026-10-11.png) | 667154 | `b71bd0de8dda13cfb8ced86f4f2364c45e0c2801665af426649b7ecd7b20aa51` |
| [analysis/burst4_20261011_context/delivery/SUMMARY.json](../../analysis/burst4_20261011_context/delivery/SUMMARY.json) | 8867 | `f418178feb3feaea4be503dbd22b678c83430514cff33dfa4ff4699454eccf81` |
| [analysis/burst4_20261011_context/delivery/TOP9.csv](../../analysis/burst4_20261011_context/delivery/TOP9.csv) | 1765 | `233a09390db10f98ba41287c1c0467edb67017bd3bc19e45a6ecf0a61369bb28` |
| [analysis/burst4_20261011_context/delivery_v3/CONTEXT54.csv](../../analysis/burst4_20261011_context/delivery_v3/CONTEXT54.csv) | 4693 | `acd92619b3ca6077b8a18534b74237307e00d55446663db5597407d96a879a57` |
| [analysis/burst4_20261011_context/delivery_v3/REPORT_RECEIPT.json](../../analysis/burst4_20261011_context/delivery_v3/REPORT_RECEIPT.json) | 4072 | `35fabd4c798f0ae54290aab600afbe754536d4cb9a984b50668bd35475ce8c10` |
| [analysis/burst4_20261011_context/delivery_v3/RESULT_PACKAGE_RECEIPT.json](../../analysis/burst4_20261011_context/delivery_v3/RESULT_PACKAGE_RECEIPT.json) | 800 | `b9a5c8876bb8a3e7cd60d21058e61042acd6799d6ba8c578baddf4ff35c9b2a5` |
| [analysis/burst4_20261011_context/delivery_v3/SETI_BURST4_CONTEXT54_2026-10-11.png](../../analysis/burst4_20261011_context/delivery_v3/SETI_BURST4_CONTEXT54_2026-10-11.png) | 507603 | `a796003a16c37bae603475a4b5d5fbe80e2c1eeaac6d8b39c7b4a3587f1fcab0` |
| [analysis/burst4_20261011_context/delivery_v3/SETI_BURST4_FINAL_2026-10-11.md](../../analysis/burst4_20261011_context/delivery_v3/SETI_BURST4_FINAL_2026-10-11.md) | 5092 | `b4d8721707c4ba717c1de294649520d0b0436ac16b31b08e8559af66333f3d27` |
| [analysis/burst4_20261011_context/delivery_v3/SETI_BURST4_ROW_CONTRIBUTIONS_2026-10-11.png](../../analysis/burst4_20261011_context/delivery_v3/SETI_BURST4_ROW_CONTRIBUTIONS_2026-10-11.png) | 653286 | `5de85411881083690bcadcffa2ee8cb590b3ef13cc5ede5b85be7d8b763f250b` |
| [analysis/burst4_20261011_context/delivery_v3/SUMMARY.json](../../analysis/burst4_20261011_context/delivery_v3/SUMMARY.json) | 8867 | `f418178feb3feaea4be503dbd22b678c83430514cff33dfa4ff4699454eccf81` |
| [analysis/burst4_20261011_context/delivery_v3/TOP9.csv](../../analysis/burst4_20261011_context/delivery_v3/TOP9.csv) | 1765 | `233a09390db10f98ba41287c1c0467edb67017bd3bc19e45a6ecf0a61369bb28` |
| [analysis/burst4_20261011_context/make_report.py](../../analysis/burst4_20261011_context/make_report.py) | 22621 | `6bf92974bf23729976f8a427f3f68cf67ed6a18a7bb5e834632ce60c04632350` |
| [analysis/burst4_20261011_context/make_report_v2.py](../../analysis/burst4_20261011_context/make_report_v2.py) | 23640 | `9d62ef125295ee03245694839aea2db04f9037856010c1e4a790baf5979a08e1` |
| [analysis/burst4_20261011_context/make_report_v3.py](../../analysis/burst4_20261011_context/make_report_v3.py) | 23650 | `0fb88760269e9893766720f072c71bbf847ec3a12cd1af8ccc0e3dcb85156456` |
| [analysis/burst4_20261011_context/qa_context.py](../../analysis/burst4_20261011_context/qa_context.py) | 25203 | `e910975468c7998e8cbdd78d740d187649177a1eafc414c86f1ebdf71beaa39a` |
| [analysis/burst4_20261011_context/results/CONTEXT_PROFILES.json](../../analysis/burst4_20261011_context/results/CONTEXT_PROFILES.json) | 289117 | `f42c5bc3d1e49414ae9a5c23ea67c68c5ccd2d27b596f695fe2b7c022eed3f9b` |
| [analysis/burst4_20261011_context/results/EXECUTION_RECEIPT.json](../../analysis/burst4_20261011_context/results/EXECUTION_RECEIPT.json) | 25693 | `78dcfe131cd87b40a0cef9b61295acbc81d87f4aa00914ccff614a5253d77e74` |
| [analysis/burst4_20261011_qa/FINAL_CONTEXT_QA_REVIEW.json](../../analysis/burst4_20261011_qa/FINAL_CONTEXT_QA_REVIEW.json) | 8344 | `ce3c7dc5eaea2bdb501726a4459c94e41c10386b5d36825ce0f90d00a05496a6` |
| [analysis/burst4_20261011_qa/FINAL_CONTEXT_REPORT_V3_ADDENDUM.json](../../analysis/burst4_20261011_qa/FINAL_CONTEXT_REPORT_V3_ADDENDUM.json) | 3755 | `f5ba51ece169eb331f001dfcabaf5fb6b66644b6deb0f8005429cc2836998750` |
| [analysis/burst4_20261011_qa/FINAL_NUMERICAL_QA_REVIEW.json](../../analysis/burst4_20261011_qa/FINAL_NUMERICAL_QA_REVIEW.json) | 14403 | `f2eed03286918ffc1167c8714725ea914cd6e56287f84ff7727d2eb7ad6659ab` |
| [analysis/burst4_20261011_qa/README.md](../../analysis/burst4_20261011_qa/README.md) | 3115 | `a03e95a873452faf4ee34f4a4b35d86ecd01dff6fb745c8504840bb5102c61ca` |
| [analysis/burst4_20261011_qa/ROOT_GO.json](../../analysis/burst4_20261011_qa/ROOT_GO.json) | 1268 | `5fc5186a59dded50587701975959e63940840ffe87db4a43a0d15b53b9dbe4c7` |
| [analysis/burst4_20261011_qa/STATIC_CONTEXT_REVIEW.json](../../analysis/burst4_20261011_qa/STATIC_CONTEXT_REVIEW.json) | 2630 | `166112e9c2acf1f7d588a6b6dff03706542ea3c037ead170107e27dc32c15fe7` |
| [analysis/burst4_20261011_qa/STATIC_DRIVER_AND_QA_REVIEW.json](../../analysis/burst4_20261011_qa/STATIC_DRIVER_AND_QA_REVIEW.json) | 2608 | `6d53065157d7f46fdb32b2c5d5b6c00e1ab363b3779e9a56d0cbdad6081494c8` |
| [analysis/burst4_20261011_qa/qa_saved.py](../../analysis/burst4_20261011_qa/qa_saved.py) | 40580 | `3b4a6ddcb526fa3894a47f15019d8ee787de5a4772d4d3dc908ffcdb3d1f4cdd` |
| [analysis/burst4_20261011_qa/results/INPUT_ADMISSION.json](../../analysis/burst4_20261011_qa/results/INPUT_ADMISSION.json) | 688 | `e65d82444af14e3a2e2f0bca2f4bc99577b003ce513961a21441f5f8a27b24f6` |
| [analysis/burst4_20261011_qa/results/QA_RECEIPT.json](../../analysis/burst4_20261011_qa/results/QA_RECEIPT.json) | 392095 | `f1d8551cf1622480e4ee4db669379c9dacdbb882f84d5d36a13fe1767d07abc8` |
