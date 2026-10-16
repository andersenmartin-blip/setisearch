# SETI: fuld seks-scanningsanalyse af ét gemt 2017-bånd

**Uafhængig numerisk QA: PASS. Begge procesafslutninger er godkendt.**

Den gennemførte søgning finder **0 bevarede ON-hypoteser med score ≥10** i dette bånd. Største ON-score er **6.961946174**. De tre komplette OFF-inventarer indeholder hver **0 hypoteser med score ≥8**. Der er derfor ingen ON-hypotese over det fastlagte snit at følge videre fra denne kørsel.

Det er en beskrivende måling på allerede eksponerede data. Scorerne er robuste residualsummer; **10 og 8 er numeriske snit, ikke kalibrerede sigma-, SNR- eller sandsynlighedsniveauer**. Resultatet dokumenterer ikke fravær af svagere eller anderledes signaler.

| Scanning | Rolle | Oprindelig retning | Referencekanaler | Største score |
|---|---|---|---:|---:|
| 1 | ON | HIP98505 | 4.096 | 5.900988598 |
| 2 | OFF | HIP97319 | 6.652 | 6.443575096 |
| 3 | ON | HIP98505 | 4.096 | 6.961946174 |
| 4 | OFF | HIP97461 | 6.652 | 5.915718459 |
| 5 | ON | HIP98505 | 4.096 | 6.094034449 |
| 6 | OFF | HIP97663 | 6.652 | 6.045194755 |

Det valgte bånd er **native170 / q131**, det første i den gamle kanonisk sorterede liste over ni bevarede, tidligere efterudvalgte bånd. Den nye kørsel bruger **4.096 ON-referencekanaler**, kildeintervallet `[178794496,178798592)`, ved ét fælles referencetidspunkt. Referencekanalernes centerfrekvenser spænder fra **2303.274538927 til 2303.285980225 MHz**; deres nominelle samlede binbredde er **11.444091796875 kHz**.

OFF-søgningen har en halo på **1.278 referencekanaler i hver side**, i alt **6.652 kanaler**, med centerfrekvenser **2303.270968236–2303.289550915 MHz** og nominel samlet binbredde **18.585473299026 kHz**. Drivende spor kan bevæge sig uden for referenceintervallet inden for den gemte inputhalo. Dette er referencegeometri i ét udsnit, ikke ny teleskopdækning eller survey-komplethed. De præcise affine koordinater og binrande er gemt i `FREQUENCY_GEOMETRY.json`.

Alle seks scanninger kommer fra **ét besøg den 28. april 2017**: tre ON-scanninger mod HIP98505/HD189733 og tre OFF-scanninger mod HIP97319, HIP97461 og HIP97663. De fire retninger er bevaret i deres oprindelige roller. De er ikke nye observationer eller en uafhængig genobservation af et fund. Kun det første af de ni gamle bånd er genberegnet med dette nye dokumenterede scope. Ældre ukendte kørsler kan allerede have forsøgt samme hypotesefamilie.

Søgningen omfatter alle **5.723 drifthastigheder fra −4 til +4 Hz/s**, syv overlappende fire-række-vinduer og bredder **1, 3, 9 og 33 kanaler**. Hver referencekanal bevarer en samlet topfem af forskellige native spor/bredder/vinduer. ON-listen indeholder alle disse **bevarede topfem-hypoteser**, som når 10; den er ikke en liste over samtlige scorer over 10 blandt alle afprøvede ON-hypoteser. OFF-inventaret er derimod udtømmende for alle score ≥8-nativeidentiteter i den erklærede OFF-familie, inklusive deres driftaliaser. Kanaler, vinduer, bredder og aliaser er korrelerede.

`rank_status` er **NOT_APPLIED_NO_CALIBRATION**. Ingen Gamma16-rang, p-værdi, injektionsvalidering, fysisk følsomhed, RFI-populationskvalifikation eller dokumenteret himmeloprindelse er etableret. Recovery-metadata angiver alene, at injektions-recovery **ikke er relevant** for de virkelige data. Ingen recovery-rate er målt.

Uafhængig QA genberegner alle seks komplette søgninger, preprocessing, bevarede kort, OFF-inventarer og relevante matchregler. Primær- og QA-processerne bruger henholdsvis **142.946756** og **107.194398 CPU-sekunder**, i alt **250.141154 CPU-sekunder**. Største målte RSS er **102,432,768 bytes**. Ingen ny teleskopforespørgsel eller teleskopbyte er hentet; udgiften er **0 DKK**.

Kildekode og scope blev offentliggjort og læst tilbage før kørslen ved commit `c721a789db23649b85ef8d01a6e5d4b801966679`. Det nye case-ID er `SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00`. Begge gamle bankforløb, pensionerede eksponerede case-ID’er, A/B-status FAIL_CLOSED og lukkede 2016-/2019-ruter er uændrede. Kontrolpunktet er fortsat 20. oktober 2026.

Den bevarede payload indeholder alle **460 numeriske arrays**, inklusive seks originale rå arrays, fulde søgekort, aliasgeometri og OFF-inventarer; den fylder **8,851,111 bytes**. Payload, præcise kildepins og uafhængige kontrolbilag indgår i reproduktionspakken. `SCAN_MAXIMA.csv` og denne rapport er direkte afledt af procesbilagene; rapportgeneratoren åbner ingen rådata og udfører ingen ny søgning.
