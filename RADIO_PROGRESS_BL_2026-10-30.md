# SETI BL — første 32 bånd i native170 gennemgået

30. oktober 2026. **Alle fire batches med q1–q32 er afsluttet med faktisk exit 0 for både søgning og afgrænset resultatkontrol.** Ingen ON- eller OFF-katalogrækker nåede den faste lokale ESS-tærskel 10. Ingen kvalificeret SETI-kandidat.

| Størrelse | BL |
|---|---:|
| Nativeblok og carrierbånd | native170, q1–q32 |
| Faste carrierbånd | 32 |
| Carrierkanaler | 131.072 |
| Teknisk kanalbredde | 366,2109375 kHz |
| Scan/bånd-søgninger | 192 |
| Korrelerede sporkombinationer, inklusive OFF | 1.732.018.176 |
| ON-katalogrækker med lokal ESS ≥10 | 0 |
| OFF-katalogrækker med lokal ESS ≥10 | 0 |
| Udløste tvungne ON/OFF-målinger | 0 |
| Beståede beskrivende ON/OFF-flag | 0 |
| Udvalgte uafhængige skalarsummer | 6.912 |
| Kalibreringsgenberegninger med delt kernel | 2.304 |

Søgningen dækker frekvenscentrene **2.304,407504–2.304,773712 MHz** i de samme seks historiske scans af HIP98505 / HD189733 fra 28. april 2017. De tre ON- og tre OFF-scans har 16 rækker hver. Lokal ESS er ikke kalibreret sigma, SNR eller falsk-alarm-sandsynlighed. Sporkombinationerne er korrelerede og er ikke uafhængige statistiske prøver.

Planer og kode blev [offentliggjort og genlæst med identiske bytes før beregningen](https://github.com/andersenmartin-blip/setisearch/commit/3fc8990aa16a34b77326383de1e706b514ec0824). Numerikken er uændret fra BK: AC-normalisering over hele hver native-række før beskæring, bånd på 4.096 kanaler, halo på 4.096 kanaler, bredder 1/3/9/33 og 839 drifttrin over ±4 Hz/s. ON-tærskel 10 og OFF-veto 5 er uændrede. q0/q128/q255 er udeladt som carrierbånd; native172 indgår ikke i BL.

| Batch | Bånd | ON ≥10 | OFF ≥10 | Søgning, s | Kontrol, s |
|---:|---|---:|---:|---:|---:|
| 1 | q1–q8 | 0 | 0 | 68.36 | 1.88 |
| 2 | q9–q16 | 0 | 0 | 67.81 | 2.09 |
| 3 | q17–q24 | 0 | 0 | 75.25 | 1.99 |
| 4 | q25–q32 | 0 | 0 | 69.69 | 2.09 |

| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |
|---:|---:|---:|
| 1 | 5.798793418 | 6.444232805 |
| 3 | 5.754988507 | 5.896317372 |
| 9 | 5.731328369 | 6.735144349 |
| 33 | 5.118470475 | 5.565677936 |

Kampagnen tog 291.94 sekunder fra start til afslutningsmarkør. De fire søgekørsler tog tilsammen 281.10 sekunders vægtid og 280.03 CPU-sekunder. Kontrollerne tog 8.05 sekunders vægtid og 11.18 CPU-sekunder. Dette er målinger for BL, ikke projektets samlede forbrug.

De afgrænsede resultatkontroller består med største afvigelse 0 for både de 6.912 udvalgte `math.fsum`-summer og de 2.304 kalibreringsgenberegninger med delt kernel. Den særskilte afslutningskontrol genhashte alle 945 unikke auditerede artefakter. Alle 96 unikke dekodede native170-rækker matcher BK's tidligere kvittering i hver af de fire normaliseringer, i alt 384 sammenligninger. Loggenes observerede bytes, gemte hash, stdout-EOF og afsluttet procesventning stemmer. Dette er ikke uafhængig kontrol af alle spor, den oprindelige HDF5-kodek, normaliseringsmodellen eller astronomisk følsomhed.

Ingen ON-frø nåede tærsklen, så de tvungne ON/OFF-målinger blev ikke udløst. Der er ikke udført eller påstået positive efterfølgende spormålinger.

Dette er en beskrivende udvidet genanalyse af tidligere eksponerede data fra ét historisk besøg. Nogle native170-bånd blev tidligere søgt under en anden full-native-ESS-familie. Ingen nye/blinde observationer eller uafhængig validering påstås. Historiske A/B-fejl samt B06/native172/q81-fejl og no-retry-statusser bevares. HIP44295 og de beskyttede 2016-/2019-data er ikke åbnet.

Der blev foretaget **0 nye forespørgsler til teleskoparkivet**, tilføjet **0 nye observationer** og brugt **0 DKK**. BA-opgørelsen forbliver 486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg. Tidligere native171-resultater ændres ikke.

Binære resultater og genoptagelsesoplysninger er gemt i [SETI_BL_SEARCH_RESULTS_2026-10-30.zip](https://chatgpt.com/library?file_id=libfile_d177425d85cc8191ac30471061ad17e3&account_id=personal): 90,305,090 bytes, 657 medlemmer. CRC og SHA-256 er kontrolleret for alle medlemmer; arkivets SHA-256 er `7d1a7eb40faff47d5c7be00fea498b289d1a7b3a92d7681ef27038f462161415`. Kildedata findes fortsat i de tidligere gemte native170/172-rådatadele, som genoptagelsesfilen henviser til. Programkode, planer, proceslogfiler og tekstlige resultater ligger på GitHub.

**Næste trin:** native170/q33–q40 under en særskilt på forhånd fastlagt plan med samme metode og kontrollogik. Native172 kræver egen afgrænsning med de gamle fejl bevaret. Ingen signalsøgning kører videre i baggrunden efter BL.

- [Samlet resultat](work_bl/results/REAL_SEARCH_SUMMARY_BL.json)
- [Faktisk afslutningsmarkør](work_bl/results/CAMPAIGN_COMPLETE_BL.json)
- [Særskilt afslutningskontrol](work_bl/review/INDEPENDENT_CLOSED_REVIEW_BL.json)
- [Faste planer](work_bl/plans) og [forhåndsfastlagt scope](work_bl/PREREG_BL.md)
- [Kørslernes proceskvitteringer og logfiler](work_bl/execution)
- [Leverance og fortsættelsespunkt](work_bl/DELIVERY_BL.json)
