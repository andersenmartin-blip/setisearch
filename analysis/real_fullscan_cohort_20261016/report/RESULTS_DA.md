# SETI: gennemgang af de ni gemte 2017-bånd

**7/8 nye bånd har fuld godkendt afslutning og QA. Sammen med B00 er 8/9 bånd verificeret. Ufuldstændige bånd tælles ikke som nulobservationer.**

I de **8 verificerede bånd** findes **0 bevarede ON-hypoteser med score ≥10**. Højeste ON-score er **7.031163159**. Der er derfor ingen ON-hypotese over det fastlagte snit at følge videre i disse kørsler. De komplette OFF-inventarer indeholder tilsammen **0 nativeidentiteter med score ≥8**.

QA for B06 stoppede med **BadZipFile**, da den gemte numeriske NPZ-payload skulle åbnes. Det er en fejl i den efterfølgende datakontrol, ikke et målt negativt signalresultat.

**B06 er uverificeret og er ikke med i ovenstående nulantal, maksimum eller øvrige videnskabelige summer.** Primærkørslen kan være afsluttet, selv om efterfølgende payload- eller QA-kontrol fejler; en sådan ufuldstændig dokumentation er ikke en målt nulobservation. Den oprindelige fejlstatus og alle delvise filer bevares uden genkørsel.

Scorerne er robuste residualsummer. **Snittene 10 og 8 er ikke kalibrerede sigma-, SNR- eller sandsynlighedsniveauer.** Resultatet dokumenterer ikke fravær af svagere eller anderledes signaler og fastslår ingen fysisk oprindelse.

| Bånd | Native / q | Maks. ON | Maks. OFF | Bevarede ON ≥10 | OFF ≥8-identiteter | QA |
|---|---|---:|---:|---:|---:|---|
| B00 | 170 / 131 | 6.961946 | 6.443575 | 0 | 0 | PASS |
| B01 | 170 / 252 | 6.916444 | 6.436202 | 0 | 0 | PASS |
| B02 | 171 / 55 | 6.812762 | 6.522810 | 0 | 0 | PASS |
| B03 | 171 / 231 | 6.638491 | 5.703960 | 0 | 0 | PASS |
| B04 | 172 / 12 | 6.749951 | 6.208108 | 0 | 0 | PASS |
| B05 | 172 / 48 | 6.996867 | 6.182675 | 0 | 0 | PASS |
| B06 | 172 / 81 | — | — | — | — | Ufuldstændig |
| B07 | 172 / 94 | 7.031163 | 6.093332 | 0 | 0 | PASS |
| B08 | 172 / 168 | 6.744085 | 5.905744 | 0 | 0 | PASS |

Hvert bånd indeholder **4.096 ON-referencekanaler** med nominel samlet binbredde **11.444091796875 kHz**, og **6.652 OFF-referencekanaler**, inklusive 1.278 kanaler i hver halo, med samlet binbredde **18.585473299026 kHz**. De verificerede disjunkte ON-referencekerner udgør tilsammen **32.768 referencekanaler og 91.552734375000 kHz** ved det fælles referencetidspunkt. Det er ikke ekstra dækning, når driftbaner eller læsehaloen overlapper andre frekvenser. Alle præcise centerfrekvenser, binrande og kildeintervaller står i `REFERENCE_FREQUENCY_GEOMETRY.json`.

Alle data kommer fra **ét allerede eksponeret og efterudvalgt besøg den 28. april 2017**. Tre ON-scanninger er rettet mod HIP98505/HD189733; tre OFF-scanninger mod HIP97319, HIP97461 og HIP97663. Fire retninger og tre gentagelser mod målet er bevaret i deres oprindelige roller; de er ikke nye observationer eller en uafhængig genobservation af et fund. De ni bånd blev tidligere valgt ud fra prominente spor. Den nye gennemgang følger den gamle kanoniske båndrækkefølge; tidligere ukendte kørsler kan allerede have forsøgt samme hypotesefamilie.

Den uændrede søgning bruger **5.723 drifthastigheder over ±4 Hz/s**, syv overlappende fire-række-vinduer og bredder 1, 3, 9 og 33 kanaler. ON-listen bevarer en samlet topfem pr. referencekanal og tager herfra alle scorer ≥10. Det er **ikke** et udtømmende ON-inventar over alle afprøvede hypoteser ≥10. OFF-inventaret er derimod udtømmende for native-fire-række-identiteter med score ≥8 i den erklærede OFF-familie, inklusive alle relevante driftaliaser.

Uafhængig QA har genberegnet alle **48 verificerede komplette scanningssøgninger** og kontrolleret preprocessing, søgekort, OFF-inventarer, aliasgeometri og matchregler. Der er **6.779.904 registrerede kontrolchecks**; de er ikke uafhængige himmelforsøg. Per-bånds kontroltal og maksimale numeriske afvigelser er bevaret i `QA_SUMMARY.csv` og de originale QA-bilag. Ingen rangkalibrering, p-værdi, injektions-recovery-rate, fysisk følsomhed eller RFI-populationskvalifikation er etableret. Recovery-metadata angiver alene, at injektions-recovery ikke er relevant for disse virkelige data.

Kohortens målte numeriske børneprocesser, inklusive eventuelle fejlede processer, brugte tilsammen **2220.700376 CPU-sekunder**. Med B00 er det i alt **2470.841530 CPU-sekunder**; heraf stammer **2297.228972 CPU-sekunder** fra de 8 fuldt verificerede bånd. Dette er de målte numeriske børneprocesser; koordinering og rapportering er særskilt. Udgiften er **0 DKK**, med **0 nye teleskopforespørgsler og 0 nye teleskopbytes**.

Pakken bevarer **3.680 numeriske payload-arrays** fra de verificerede bånd, herunder 48 originale rå arrays, fulde søgekort, aliaser og OFF-inventarer. De verificerede payloads fylder **70.787.852 bytes**. Kildekode, fastlåste scopes, komplette proces- og QA-bilag samt de afledte tabeller gør resultaterne efterprøvelige. Rapportgeneratoren læser kun metadata og procesbilag og udfører ingen ny søgning.

B00 er ikke kørt igen eller ændret. De tidligere pensionerede og fejllukkede bankforløb forbliver uændrede, A/B er fortsat FAIL_CLOSED, og 2016-/2019-ruterne er fortsat lukkede. Det formelle kontrolpunkt er 20. oktober 2026.
