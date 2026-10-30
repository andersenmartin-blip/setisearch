# SETI BM — alle resterende native170-bånd gennemgået

30. oktober 2026. **28 af 28 faste batches er afsluttet med faktisk exit 0 for både søgning og afgrænset resultatkontrol.** Det svarer til 221 ekstra carrierbånd i native170. Antal beskrivende ON/OFF-flag: 0. Ingen kvalificeret SETI-detektion påstås.

**Sammen med BL er alle 253 valgte sikre carrierbånd i native170 nu gennemgået i denne lokale ESS-familie.** q0/q128/q255 er fortsat udeladt som søgecentre. Den tidligere afsluttede native171-blok er ikke genkørt.

| Størrelse | BM, afsluttet og kontrolleret del |
|---|---:|
| Carrierbånd | 221 |
| Scan/bånd-søgninger | 1,326 |
| Carrierkanaler | 905,216 |
| Teknisk kanalbredde | 2.529144287 MHz |
| Korrelerede sporkombinationer, inklusive OFF | 11,961,750,528 |
| ON-katalogrækker med lokal ESS ≥10 | 51,652 |
| OFF-katalogrækker med lokal ESS ≥10 | 52,346 |
| Udløste ON/OFF-målepladser | 309,912 |
| Understøttede målepladser | 309,912 |
| Målepladser uden for support | 0 |
| Beståede beskrivende ON/OFF-flag | 0 |
| Udvalgte uafhængige skalarsummer | 47,736 |
| Kalibreringsgenberegninger med delt kernel | 15,912 |

Planer, kode og inputhashes blev [fastholdt og genlæst med identiske bytes før BM-beregningen](https://github.com/andersenmartin-blip/setisearch/commit/82277dbb08d2d93b2bbd8acdad304cdb7de0fb49). Den lange kørsel dækkede i fast rækkefølge q33–q127 og q129–q254. Tidligere BL q1–q32 bevares. Native172, herunder den historisk fejlede B06/q81, indgår ikke i BM.

Målet er HIP98505 / HD189733, samme seks scans fra 28. april 2017 med tre ON, tre OFF og 16 rækker per scan. Fysisk native170-origin er kanal 178257920, første frekvens 2304.78515625 MHz, kanaltrin −2.7939677238464355 Hz og tidsinterval 18.253611008 s. Normalisering beregnes over hele hver native-række før beskæring. Den numeriske metode er uændret fra BL: AC-normalisering, 4096-kanals carrierbånd og halo, bredder 1/3/9/33, strides 1/1/2/8, 839 drifttrin over ±4 Hz/s, lokal ON-tærskel 10 og fast OFF-veto 5. Drift/frekvensbaner måles kun på samme historiske besøg.

| Batch | Bånd | ON ≥10 | OFF ≥10 | Flag | Søgning, s | Kontrol, s |
|---:|---|---:|---:|---:|---:|---:|
| 1 | q33–q40 | 0 | 0 | 0 | 69.88 | 2.08 |
| 2 | q41–q48 | 0 | 0 | 0 | 73.21 | 2.06 |
| 3 | q49–q56 | 0 | 0 | 0 | 69.52 | 1.98 |
| 4 | q57–q64 | 0 | 0 | 0 | 68.20 | 1.98 |
| 5 | q65–q72 | 0 | 0 | 0 | 71.69 | 1.94 |
| 6 | q73–q80 | 0 | 0 | 0 | 70.03 | 1.95 |
| 7 | q81–q88 | 0 | 0 | 0 | 67.44 | 1.96 |
| 8 | q89–q96 | 0 | 0 | 0 | 69.51 | 2.19 |
| 9 | q97–q104 | 0 | 0 | 0 | 67.80 | 2.00 |
| 10 | q105–q112 | 0 | 0 | 0 | 67.28 | 2.12 |
| 11 | q113–q120 | 0 | 0 | 0 | 71.08 | 2.02 |
| 12 | q121–q127 | 51,652 | 52,346 | 0 | 71.83 | 2.12 |
| 13 | q129–q136 | 0 | 0 | 0 | 74.55 | 2.12 |
| 14 | q137–q144 | 0 | 0 | 0 | 75.99 | 2.31 |
| 15 | q145–q152 | 0 | 0 | 0 | 73.25 | 2.03 |
| 16 | q153–q160 | 0 | 0 | 0 | 71.29 | 1.98 |
| 17 | q161–q168 | 0 | 0 | 0 | 69.60 | 2.02 |
| 18 | q169–q176 | 0 | 0 | 0 | 66.91 | 1.98 |
| 19 | q177–q184 | 0 | 0 | 0 | 68.88 | 1.90 |
| 20 | q185–q192 | 0 | 0 | 0 | 69.89 | 2.05 |
| 21 | q193–q200 | 0 | 0 | 0 | 74.89 | 2.46 |
| 22 | q201–q208 | 0 | 0 | 0 | 73.23 | 2.23 |
| 23 | q209–q216 | 0 | 0 | 0 | 76.30 | 2.17 |
| 24 | q217–q224 | 0 | 0 | 0 | 76.23 | 1.99 |
| 25 | q225–q232 | 0 | 0 | 0 | 73.47 | 2.16 |
| 26 | q233–q240 | 0 | 0 | 0 | 71.70 | 2.08 |
| 27 | q241–q248 | 0 | 0 | 0 | 73.81 | 1.98 |
| 28 | q249–q254 | 0 | 0 | 0 | 54.36 | 1.57 |

| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |
|---:|---:|---:|
| 1 | 8640.7148265061 | 6759.285239621378 |
| 3 | 15726.267999023828 | 12087.037367181661 |
| 9 | 9063.041224827219 | 7287.4662204814485 |
| 33 | 4520.573790772924 | 4219.920543811231 |

Kampagnens faktiske vægtid til terminalmarkøren var **34.30 minutter**. De krediterede søgninger brugte 1981.83 sekunders vægtid og 1975.12 CPU-sekunder. De afgrænsede kontroller brugte 57.43 sekunders vægtid og 80.04 CPU-sekunder. Dette er BM-målinger, ikke samlet forbrug for projektet.

Udvalgte uafhængige `math.fsum`-summer har største afvigelse 1.4551915228366852e-11; kalibreringsgenberegninger med den delte kernel har største afvigelse 0.0. Samtlige gemte normaliseringskvitteringer blev sammenholdt med BK's 96 unikke native170-rækkehashes, i alt 2,688 sammenligninger. Alle bevarede kilde-, plan-, input- og auditerede artefakthashes kontrolleres igen før og efter pakning. Faktiske exitkoder, stdout-EOF, afsluttet procesventning samt observerede/gemte logbytes og loghashes bevares.

En særskilt afslutningskontrol genhashte 6.515 evidensfiler uden uoverensstemmelser. [Kontrolresultat](work_bm/review/INDEPENDENT_CLOSED_REVIEW_BM.json). Den største forskel i de udvalgte skalarsummer var 1,4552 × 10⁻¹¹, inden for den på forhånd fastsatte grænse.

Det er afgrænset numerisk konsistenskontrol, ikke en uafhængig genberegning af alle spor eller en kvalifikation af den oprindelige rådatakodek, normaliseringsmodellen, astronomisk følsomhed eller falsk-alarm-sandsynlighed. Lokal ESS er ikke kalibreret sigma, SNR eller FAP; sporkombinationerne er korrelerede. Et bestået beskrivende flag ville udløse stop og særskilt vurdering, ikke automatisk en SETI-detektion.

Alle 51,652 ON-sporforslag i batch12 ligger i q127 ved det udeladte DC-bånd. Af dem når 31 tærsklen i alle tre ON-scans; alle 31 har også OFF-udslag over veto-grænsen og fravælges. De øvrige 51,621 opfylder ikke kravet i alle tre ON-scans. Det er korrelerede sporforslag, ikke et tilsvarende antal forskellige signaler. [Fordeling fra allerede gemte målinger](work_bm/results/Q127_TRIAGE_DISPOSITION_BM.json).

Der er tale om genanalyse af tidligere eksponerede data fra ét historisk besøg. Nogle native170-bånd blev tidligere søgt med en anden full-native-ESS-familie. Ingen nye/blinde observationer, uafhængig validering eller ny oprindelig dækning påstås. A/B- og B06-fejlstatusser bevares; HIP44295 og de beskyttede 2016/2019-data er ikke åbnet. Der blev foretaget 0 nye forespørgsler til teleskoparkivet og brugt 0 DKK. BA forbliver 486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg.

Den kontrollerede resultatpakke har **631,607,700 bytes og 4,536 medlemmer**. Hvert medlems CRC og SHA-256 er kontrolleret. Arkivets SHA-256 er `cfee86e82dccc6f2a38a5ee2cb04f430ebb657d63d4c6c06bc0e1375fbb08622`. Pakken er opdelt i følgende fortløbende byte-dele; de skal samles i rækkefølge før udpakning:

- [SETI_BM_SEARCH_RESULTS_2026-10-30.zip.part01](https://chatgpt.com/library?file_id=libfile_c852024fc4f481918b944b1a4ea05e9b&account_id=personal): 209,715,200 bytes, SHA-256 `47683f794bb3ec9d204a14e1fc118c7af1600cd2edbca7fadb37c5eb4c688476`.
- [SETI_BM_SEARCH_RESULTS_2026-10-30.zip.part02](https://chatgpt.com/library?file_id=libfile_90b7699964e08191a3bf5e75647c57e7&account_id=personal): 209,715,200 bytes, SHA-256 `3b938d0f7c3e7cb7e93be76c7512c0e289da42475676a2398c425c9d29e08874`.
- [SETI_BM_SEARCH_RESULTS_2026-10-30.zip.part03](https://chatgpt.com/library?file_id=libfile_ce93ac4a70b48191b269b38aafd9ccc1&account_id=personal): 209,715,200 bytes, SHA-256 `7cf1b627f93c6cf650140dbc0021673fe1f476384033d81d81d0777a5fbc703f`.
- [SETI_BM_SEARCH_RESULTS_2026-10-30.zip.part04](https://chatgpt.com/library?file_id=libfile_da2caf8eae08819184dcfc8a0bb71b5e&account_id=personal): 2,462,100 bytes, SHA-256 `17e90c8954c7b2c07ff3bd27ffbdcec3e000f021fe2958576ad8d3365bb80cf1`.

Den samlede bytefølge er verificeret mod arkivets hash. Genoptagelsesfilen bevarer rådatadelenes tidligere identiteter og kontrolsummer. Programkode, planer, proceslogfiler, tekstlige resultater og kontrolpunkter ligger på GitHub. Binære arrays ligger i den gemte resultatpakke.

**Næste trin:** fastlæg en særskilt beskrivende søgeplan for native172 med den historiske B06/q81-fejl og no-retry-status bevaret. Ingen signalsøgning kører i baggrunden efter denne afslutning.

- [Samlet resultat](work_bm/results/REAL_SEARCH_SUMMARY_BM.json)
- [Afslutnings- og fejllogik](work_bm/run_campaign_bm.py)
- [Faste planer](work_bm/plans) og [forhåndsfastlagt scope](work_bm/PREREG_BM.md)
- [Gemte kontrolpunkter](work_bm/checkpoints)
- [Proceskvitteringer og logfiler](work_bm/execution)
- [Resultatkontroller](work_bm/review)
- [Leverance og fortsættelsespunkt](work_bm/DELIVERY_BM.json)
