## 16. oktober 2026: alle ni bånd søgt, otte fuldt QA-verificeret

De otte resterende metadatafastlagte 2017-bånd er nu søgt med samme fulde seks-scan-detektor, drift-/bredde-/vinduesfamilie og snit 10/8 som B00. **7/8 nye bånd består hele den uafhængige QA; inklusive B00 er status 8/9.** De otte fuldt verificerede bånd har **0 bevarede ON-hypoteser ≥10**, **0 OFF-identiteter ≥8** og højeste ON-score **7,031163159**. De dækker otte adskilte referencekerner, i alt **91,552734375 kHz**; dette er ingen generel himmel-nuldetektion.

B06 fik først en afkortet resultatfil og er fortsat fejllukket i den oprindelige kohorte. En særskilt fastlåst bytegendannelse bevarede alle 454 beregnede komprimerede poster og genskabte rå input/katalog til **eksakt oprindelig størrelse og SHA-256**, uden ny primær søgning. Den efterfølgende uafhængige QA kontrollerede alle seks fulde søgekort og OFF-inventarer med **847.481 checks**, men stoppede ved det uændrede krav om eksakt lighed for globalt maksimum: **7,450294835423308 mod 7,450294835423307**, forskel **8,881784197001252 × 10⁻¹⁶**. Denne fejl tælles ikke som PASS; B06 indgår ikke i de otte verificerede bånds nuller eller maksimum. Begge oprindelige fejlforløb og den gendannede kopi er bevaret.

[Oprindelig 7/8-rapport](analysis/real_fullscan_cohort_20261016/report/RESULTS_DA.md) · [Eksakt gendannelse og bevaret QA-fejl](tools/saved_payload_restore_20261016/report/RESULTS_SUPPLEMENT_DA.md) · [Samlet status](RADIO_NINE_BAND_STATUS_2026-10-16.md)

Resultatpakken `SETI_ALLE_NI_BAAND_2026-10-16.zip` har **76.984.741 bytes**, **359 verificerede medlemmer** og SHA-256 `ac59da20464780bbcb26251e9ce2dc631d361dfc82a868551125edbdd41584d4`. Arrays ligger i den gemte ejerpakke; repositoryet bevarer kildekode, fastlåsninger og tekstbilag. De tre reelle forløb brugte **2.581,938327 målte børneproces-CPU-s**, inklusive begge fejlede QA-processer; pakning yderligere **3,314751 CPU-s**. Deres **12.560 CPU-s** prospektive reservationer samt særskilt **100 CPU-s** til levering beholdes uden refusion. Ingen nye teleskopforespørgsler/-bytes, **0 DKK**.

Data er stadig ét eksponeret, efterudvalgt besøg fra 28. april 2017 med fire retninger. Snittene er ikke kalibreret sigma/SNR/FAP; ingen kvalificeret SETI-detektion, fysisk følsomhed eller uafhængig genobservation er etableret. Original A/B forbliver **FAIL_CLOSED**, 2016 beskyttet og 2019-ruten lukket. De gennemførte søgninger gentages ikke som fremdrift. Den præcise numeriske QA-gate er et dokumenteret uløst metodepunkt; kontrolpunktet **20. oktober 2026** bevares.

---

| Bånd | Native/q | Fuld QA | Producerens ON-maksimum |
|---|---|---|---:|
| B00 | 170/131 | PASS | 6,961946174 |
| B01 | 170/252 | PASS | 6,916444045 |
| B02 | 171/55 | PASS | 6,812761874 |
| B03 | 171/231 | PASS | 6,638491350 |
| B04 | 172/12 | PASS | 6,749950807 |
| B05 | 172/48 | PASS | 6,996867084 |
| B06 | 172/81 | FAIL; beskrivende diagnostik | 7,450294835 |
| B07 | 172/94 | PASS | 7,031163159 |
| B08 | 172/168 | PASS | 6,744084984 |

B06-rækken er ikke en fuldt accepteret QA-observation. Oprindelig kohorte: `INCOMPLETE_COHORT_RETAINED_NO_RETRY`. Særskilt bytegendannelse: PASS; særskilt gemt-resultat-QA: `STOPPED_RETAINED_NO_RETRY`. De lukkede scopes og tolerancer er uændrede.
