# Arkitektur- og mappeoversigt for `setisearch`

Dette dokument forklarer opbygningen af repositoriet på tværs af dets fire historiske og aktive forskningsspor, så både forskere og reproducerbarheds-tjek hurtigt kan orientere sig.

---

## 1. Overblik over mapper og filer på `main`

| Sti / mønster | Spor | Rolle og status |
| --- | --- | --- |
| [`README.md`](../README.md) | Alle | Kortfattet hovedindgang, aktuel status på tværs af alle spor og reproduktionsvejledning. |
| [`CONTINUE_SETI.md`](../CONTINUE_SETI.md) | Optisk (aktivt) | Autoritativ teknisk overdragelse, faglige guardrails og aktiv køreplan (`D078` → `V3`). |
| [`docs/OPTICAL_HD43629_INDEX.md`](OPTICAL_HD43629_INDEX.md) | Optisk (`D001`–`D077`) | Samlet indeks og bindeled fra `D001`/`D002` til alle 22 danske delrapporter i [`docs/reports_d035_d077/`](reports_d035_d077/SETI_D077_FEROS_WLC_METADATA_GATE_2026-11-14.md). |
| [`docs/history/`](history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) | Historisk arkiv | Ubeskåret arkiv af tidligere omvendt-kronologisk `README.md`, `CONTINUE_SETI.md` samt gren-oprydningskvittering. |
| [`progress/`](../progress/2026-11-14-feros-d077/REPORT.md) | Optisk (`FEROS`) | Maskinlæsbare offentlige leverancer (`METHOD.json`, `SOURCES.json`, `SUMMARY.json`, `NUMERICAL_AUDIT.json`, `REPORT.md`) fra `D075` og frem. |
| [`work_seti_20261105_d001_delivery/`](../work_seti_20261105_d001_delivery/README.md) | Optisk (`HARPS`) | Konsolideret audit af de 300 oprindelige HARPS-eksponeringer (20 stjerner) + udvælgelse af 54 friske eksponeringer (`D001`). |
| `work_harps_20261101_*` .. [`work_harps_20261105_c037_context/`](../work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md) | Optisk (`HARPS`) | Forseglede kontekst- og BERV/topocentriske analyser (`C001`–`C037`) for den lukkede `90`-rækkers kø (`6.320` filer). |
| `work_rubin_20261102/` | Optisk fotometri | Lukket Rubin/Fink-feasibility-forstudie (`STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET`). |
| `src/seti_repeater/`, `tests/`, `scripts/`, `config/` | Radio (`M8`–`M41`) | Python/C-pakke (`seti-repeater`) til multi-epoke smalbånds-de-Doppler-søgning, syntetiske injektioner og sandheds-lokal kalibrering; testes automatisk af [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). |
| `results_m10/` .. `results_m36/`, `DATA_MANIFEST_M*.sha256`, `RESULTS_MANIFEST_M*.sha256`, `validation_m*.json` | Radio (`M10`–`M41`) | **Forseglede rod-artefakter.** Disse stier kontrolleres direkte af CI-testsuiten (`tests/test_m36_*` .. `test_m41_*`) og må efter [`CONTRIBUTING.md`](../CONTRIBUTING.md) ikke flyttes eller omskrives. |

---

## 2. Historiske specialgrene (bevaret urørt)

Under oprydningen den 14. november 2026 blev **16 fuldt indmergede midlertidige arbejdsgrene** (`codex/*` og `optical-harps-week-20261101`, dokumenteret med eksakte SHA-værdier i [`MERGED_BRANCH_CLEANUP_2026-11-14.json`](history/MERGED_BRANCH_CLEANUP_2026-11-14.json)) fjernet fra remote-listen, mens samtlige ikke-mergede forskningsgrene bevares som forseglede referencer:

- **`m43-support-qualification`:** Indeholder det afsluttede `M43AF` (502-optagelsesstudie), `M43AI` native validering samt `LS7B`–`LS7E` TESS-lysglimt- og pixelkovarians-studier.
- **`ls1-light-sail-search` .. `ls6-next-target-metadata`:** Historiske radio/optiske light-sail udviklingsgrene (`HD 260655`, `HD 63433`, `LHS 1140`, `TRAPPIST-1`).
- **`radio-bp-paired-controls-20261031` m.fl.:** Oktober 2026 radio-opfølgning (`BA`–`CB`, herunder `HIP 44295` og `HIP 35136`).
- **`codex/seti-d002-fresh-20261105`:** Forberedelsesgren fra overgangen til `D002`.

---

## 3. Kompakte numeriske kompagnonarkiver (optisk spor)

For at holde git-kloning hurtig opbevares større mellemliggende `.npz`-arrays og udpakkede FITS-udsnit for `D069`–`D077` i kompakte, SHA-256-låste kompagnonarkiver (kan verificeres med `restore_d077_workspace.py` og `verify.py --recompute`):

| Arkiv | Størrelse (bytes) | SHA-256 |
| --- | ---: | --- |
| `SETI_D069_D074_FEROS_VELOCITY_CONTEXT_RESULTS_2026-11-13.zip` | `45.920.303` | `b9bd142de7bdbf98b88d87dd5889cee3b1f1b43d93c17c4e711e6ed8a2e11820` |
| ↳ indlejret `SETI_D069_D071_FEROS_EXTRACTION_AND_ORDERS_RESULTS_2026-11-13.zip` | `35.469.693` | `4bdc74a115f087fcbc04b88d2be35b4bbefa1df1c52d5258b6a88f0d388f024e` |
| `SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_RESULTS_2026-11-13.zip` | `28.329.072` | `2b7c5b48ee2f3b62ec7c3b6b65c150af4fed80b1930355d4d6b212b0d262fa31` |
| `SETI_D077_FEROS_WLC_METADATA_GATE_RESULTS_2026-11-14.zip` | `659.654` | `828466e2c8ede7897be98d38d247fb18def0e5acdb40754656c8d2517c27c818` |

---

## 4. Konventioner for fremtidige faser (`D078` og frem)

1. **Sammenhængende videnskabelige faser frem for mikro-trin:** Hver ny fase samler en hel, selvstændig fysisk problemstilling (med prospektiv `METHOD_LOCK.json`, kørsel, uafhængig audit og syntese i én samlet leverance).
2. **Normaliserede resultattabeller:** De historiske 141- og 37-rækkers CSV-tabeller (`107.105` celler ved `D077`) bevares urørte som historiske snapshots, mens nye faser udgiver egne slanke, normaliserede JSON/CSV-tabeller uden at tilføje sparsomme ekstra kolonner på tværs af urelaterede rækker.
3. **Ingen uforseglede rå teleskop-binaries i git-træet:** Git-træet rummer kode, metodelåse, audit-kvitteringer, tabeller og rapporter; eventuelle større datapakker udgives som hash-låste Release-arkiver.
