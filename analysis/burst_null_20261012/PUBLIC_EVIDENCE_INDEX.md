# Offentligt evidensindeks · Gamma51-modelkontrol, 12. oktober 2026

Otte uafhængige modelrealiseringer af hele den 96-kerne burst4-pilot er færdige: 768 kort, 3.145.728 carrier-maksima, 7.002.390.528 korrelerede skabelonforekomster, 3.096 scoreaudits og 24 sammenbundne TOP3-ordensdiagnoser. Alle otte TOP1 og alle 24 TOP3 får strengt størst score i kronologien. Familien er modelenheden, ikke det enkelte udvalgte spor. TOP1-scorerne ligger fra 6,534836 til 7,247618 med median 7,014702. Det viser kronologifordelen efter udvælgelse også under den fastlåste rene støjmodel; ingen teleskop-FAP, modelvalidering eller SETI-kvalifikation følger.

Kode, scope og reviews blev offentliggjort og læst tilbage før modelværdier ved commit `682281a0f5eee08af620f06f36bdb1918d825952`. Scope SHA256: `91578ba6dbc6ab815ef04408aaa58374019ca216aa07b88b2e91735d3af2ff74`. To afviste startkontroller skyldtes en manglende arkivgrænse i rodens GO, før numeriske imports/modelgeneration/outputmapper. Den afviste version og metadatarettelsen er bevaret. Ingen afsluttet modelkørsel eller testbank er gentaget.

| Evidens | Fil |
|---|---|
| Resultat og modelgrænser | [Rapport](delivery/SETI_BURST_NULL_FINAL_2026-10-12.md) |
| Otte uafhængige modelenheder | [FAMILY8.csv](delivery/FAMILY8.csv) |
| 24 sammenbundne vindere | [SYNTHETIC_TOP24.csv](delivery/SYNTHETIC_TOP24.csv) |
| Ni tidligere datavindere, separat | [REAL_REFERENCE_TOP9.csv](delivery/REAL_REFERENCE_TOP9.csv) |
| Samlet optælling | [SUMMARY.json](delivery/SUMMARY.json) |
| Uafhængig numerisk kontrol | [QA_RECEIPT.json](QA_RECEIPT.json) |
| Rapportbindinger | [REPORT_RECEIPT.json](delivery/REPORT_RECEIPT.json) |
| Figur- og fortolkningsreview | [VISUAL_AND_INTERPRETATION_REVIEW.json](VISUAL_AND_INTERPRETATION_REVIEW.json) |
| Model/protokol og scope | [PROTOCOL.md](PROTOCOL.md), [scope.json](scope.json) |
| Reproduktion og bevarede inputs | [REPRODUCTION.md](REPRODUCTION.md) |
| Arkividentitet | [RESULT_PACKAGE_RECEIPT.json](RESULT_PACKAGE_RECEIPT.json) |
| Målte ressourcekomponenter | [PHASE_RESOURCE_LEDGER_FINAL.json](PHASE_RESOURCE_LEDGER_FINAL.json) |

QA-receipt SHA256: `7e3a0f99cb13b5bfafc1505db06a0b40bc85b8dfe4146a25d95babd9f30c2563`. Alle 768 generatorstreams og 12.288 rækkehashes/rå kernemedianer stemmer. Alle 24 vindende kerners fulde median501/MAD/lokation er uafhængigt rekonstrueret fra råcrop; maksimal parameterafvigelse er 4,68×10⁻¹⁷. De øvrige auditkerners MAD/lokation er betingede, gemte termer. QA genmaksimerer ikke hele søgegitteret og tilføjer ingen nye modelreplikater.

Arkivet **SETI_BURST_NULL_RESULTS_2026-10-12.zip** er 101,270,902 bytes, med 4,801 medlemmer og SHA256 `d77e54fac6cfd2a212904a9ad89ead144a20c248117a5ac614041bafbd06fa6c`. Alle medlemmer har bestået CRC, alle 4,800 payloadhashes er kontrolleret, og inputidentiteterne er uændrede. Det indeholder alle nye modelkort/audit- og ordenskapsler, 24 fulde råvindercrops, kode og rapportmetadata. Øvrige fulde modelråbytes kan reproduceres fra frø/versioner, men er ikke alle gemt. Tidligere virkelige arrays/H5 er eksterne. Den fulde arraypakke er bevaret separat; denne gren publicerer kode, tekstmetadata, normaliseringer, scorer, figurer og kvitteringer.

Kendte målte proceskomponenter inklusive pakning: 1148.976702 CPU-s; dette er ingen komplet sessionsmåling. Faseallokering 6.000 CPU-s er ikke en abonnementsgrænse, og tidligere reservationer refunderes ikke. Nul nye teleskoprequests og 0 DKK. Original A/B er FAIL_CLOSED, ingen holdouts er åbnet, og checkpointet den 20. oktober er fortsat udestående.
