# SETI: B06 er gendannet eksakt, men den strenge QA fejlede

**Der er fortsat 8/9 fuldt verificerede bånd inklusive B00. Den oprindelige otte-båndskohorte står på 7/8; B06 og det separate QA-forløb bevarer deres fejlstatus.**

I de otte fuldt verificerede bånd findes **0 bevarede ON-hypoteser med score ≥10** og **0 OFF-nativeidentiteter med score ≥8**. Højeste verificerede ON-score er **7.031163159**. B06 tælles ikke som en nulobservation og indgår ikke i disse summer.

B06s numeriske payload er nu gendannet med **eksakt samme størrelse og SHA-256 som før datatabet**. De 454 komplette afledte komprimerede ZIP-poster blev kopieret uændret; kun de seks oprindelige rå inputposter og ZIP-mappen blev genskabt fra autentificerede kildebytes. Der blev udført **0 nye primære detektorkørsler**.

Den oprindelige fejlramte fil på **7.378.998 bytes**, SHA-256 `f5332374aff54027ea8e1cfa25738deee7631a61d5a83f88e556b68f4e3f3bed`, bevares uændret. Den gendannede fil er **8.723.230 bytes**, SHA-256 `b96e21059e3d5480c55aad7788488ba5a49f1f4c05bb59ac14224b5cd09a143a`. Eksakt gendannelse af bytes er gennemført; den efterfølgende samlede numeriske QA har ikke PASS.

Den separate QA genberegnede og kontrollerede **alle seks komplette scanningskort og OFF-inventarer** før stop, med **847.481 kontrolchecks**. Slutkontrollen af det globale ON-maksimum kræver præcis nul afvigelse. Den oprindelige producer havde **7.450294835423308**, og den uafhængige beregning havde **7.450294835423307**. Forskellen er **8.881784197001252e-16**, én ULP i binary64. Det fastlagte nulkrav er dermed ikke opfyldt. Tolerancen er ikke ændret efter udfaldet, og der foretages ingen ny kørsel i dette forløb.

| B06-scanning | Rolle | Oprindelig retning | Producer-maksimum | Uafhængigt maksimum |
|---|---|---|---:|---:|
| epoch1_on | ON | HIP98505 | 6.335690265778414 | 6.335690265778414 |
| epoch1_off | OFF | HIP97319 | 6.257966751246546 | 6.257966751246546 |
| epoch2_on | ON | HIP98505 | 6.037851000640693 | 6.037851000640693 |
| epoch2_off | OFF | HIP97461 | 5.804196210242864 | 5.804196210242864 |
| epoch3_on | ON | HIP98505 | 7.450294835423308 | 7.450294835423307 |
| epoch3_off | OFF | HIP97663 | 5.763832691165751 | 5.763832691165751 |

Tabellen er **delvis kontroldiagnostik for B06**, ikke en bestået samlet verifikation. B06-producerens bevarede ON≥10-antal er **0**; de tre uafhængigt genberegnede OFF≥8-inventarer har hver 0 poster. Disse diagnostikker holdes adskilt fra de otte fuldt verificerede bånd. Der er ingen kalibreret falskalarmrate, SNR, fysisk følsomhed eller målt injektions-recovery-rate.

Søgningen bruger uændret 5.723 drifthastigheder over ±4 Hz/s, syv fire-række-vinduer og bredder 1, 3, 9 og 33 kanaler. ON-antal omfatter de bevarede samlede topfem pr. referencekanal med score ≥10, ikke alle afprøvede ON-hypoteser over 10. OFF-inventarerne er udtømmende for score ≥8-nativeidentiteter og deres aliaser i den erklærede familie. Snittene 10 og 8 er beskrivende numeriske snit.

De otte fuldt verificerede referencekerner udgør **32.768 kanaler og 91.552734375 kHz**. Alle ni planlagte kerner udgør 36.864 kanaler og 102.996826171875 kHz, men det er ikke fuldt verificeret dækning. Kernerne ligger i adskilte frekvensintervaller med mellemrum; breddernes sum er ikke et sammenhængende frekvensinterval.

Alle data stammer fra **ét allerede eksponeret, efterudvalgt besøg den 28. april 2017**. Tre ON-scanninger er rettet mod HIP98505/HD189733, og de tre OFF-scanninger mod HIP97319, HIP97461 og HIP97663. De fire oprindelige retninger er bevaret; der er ingen ny observation eller uafhængig genobservation af et fund. Tidligere ukendte kørsler kan allerede have forsøgt samme hypotesefamilie.

| Afgrænset forløb | Reserveret CPU-tid | Målt CPU-tid for hele børneprocesser |
|---|---:|---:|
| B00 | 1.300 s | 250.141154 s |
| Oprindelig kohorte, inklusive fejlede processer | 10.500 s | 2220.700376 s |
| Eksakt gendannelse og fejlet streng QA | 760 s | 111.096797 s |
| I alt for disse tre forløb | 12.560 s | 2581.938327 s |

Reservationer er forud fastlagte lofter, ikke målte forbrugstal. Ingen gamle reservationer eller fejlede procesomkostninger er frigivet eller genbrugt. Udgiften er 0 DKK, med 0 nye teleskopforespørgsler og 0 nye teleskopbytes. Koordinering og rapportering er særskilt fra børneprocessernes målte CPU-tid.

Dette supplement ændrer ingen tidligere scopes, rapporter eller fejlstatusser. A/B forbliver FAIL_CLOSED, 2016-/2019-ruterne forbliver lukkede, og kontrolpunktet er 20. oktober 2026. Rapporten er afledt af metadata og procesbilag; rapportgeneratoren åbner ingen rå- eller payload-arrays.
