# SETI BN — alle 253 valgte sikre bånd i native172 gennemgået

30. oktober 2026. **32 af 32 faste batches er afsluttet med faktisk exit 0 for både søgning og afgrænset resultatkontrol.** Det svarer til 253 carrierbånd i native172. Antal beståede beskrivende ON/OFF-flag i den afsluttede del: 0. Ingen kvalificeret SETI-detektion påstås.

**Alle 253 på forhånd valgte sikre carrierbånd i native172 er gennemgået i denne lokale ESS-familie.** q0, q128 og q255 er udeladt som søgecentre. De tidligere afsluttede native170- og native171-søgninger er ikke genkørt af BN.

| Størrelse | BN, afsluttet og kontrolleret del |
|---|---:|
| Carrierbånd | 253 |
| Scan/bånd-søgninger | 1.518 |
| Carrierkanaler | 1.036.288 |
| Teknisk kanalbredde | 2,895355225 MHz |
| Korrelerede sporkombinationer, inklusive OFF | 13.693.768.704 |
| ON-katalogrækker med lokal ESS ≥10 | 52.268 |
| OFF-katalogrækker med lokal ESS ≥10 | 52.459 |
| Udløste ON/OFF-målepladser | 313.608 |
| Understøttede målepladser | 313.608 |
| Målepladser uden for support | 0 |
| Beståede beskrivende ON/OFF-flag | 0 |
| Udvalgte uafhængige skalarsummer | 54.648 |
| Kalibreringsgenberegninger med delt kernel | 18.216 |

Planer, kode og inputhashes blev [fastholdt og genlæst med identiske bytes før BN-beregningen](https://github.com/andersenmartin-blip/setisearch/commit/793a8adb2fee9bd7ce2d7998328de0ba169806e8). Den faste rækkefølge er q1–q127 efterfulgt af q129–q254. En stopmarkør betyder, at senere planlagte batches ikke automatisk medregnes.

Målet er HIP98505 / HD189733, de samme seks historiske scans fra **28. april 2017**, med tre ON, tre OFF og 16 rækker per scan. Fysisk native172-origin er kanal **180355072**, første kanalfrekvens **2298,92578125 MHz**, kanaltrin **−2,7939677238464355 Hz** og tidsinterval **18,253611008 s**. Normaliseringen beregnes over hele hver native-række før beskæring. Numerikken følger BL/BM-familien: AC-normalisering, carrierbånd og halo på 4.096 kanaler, bredder 1/3/9/33, strides 1/1/2/8, 839 drifttrin over ±4 Hz/s, lokal ON-tærskel 10 og fast OFF-veto 5.

**Afgrænsning af q81:** BN er en særskilt, på forhånd fastlagt lokal-q-familie med 16 tidsrækker og 839 drifttrin. Den oprindelige B06-identitet og dens efterfølgende restaurerings-/QA-identiteter forbliver lukkede, fejlede og brugte med deres no-retry-status bevaret. BN reparerer, gentager eller genkvalificerer ikke disse identiteter og giver ingen historisk påstand om et niende verificeret bånd. Allerede eksponerede rådata er ikke gjort til nye eller blinde data.

| Batch | Bånd | ON ≥10 | OFF ≥10 | Flag | Søgning, s | Kontrol, s |
|---:|---|---:|---:|---:|---:|---:|
| 1 | q1–q8 | 0 | 0 | 0 | 70,59 | 1,89 |
| 2 | q9–q16 | 0 | 0 | 0 | 67,95 | 2,14 |
| 3 | q17–q24 | 0 | 0 | 0 | 70,32 | 2,17 |
| 4 | q25–q32 | 0 | 0 | 0 | 70,09 | 1,86 |
| 5 | q33–q40 | 0 | 0 | 0 | 73,87 | 1,94 |
| 6 | q41–q48 | 0 | 0 | 0 | 68,61 | 2,18 |
| 7 | q49–q56 | 0 | 0 | 0 | 71,38 | 2,43 |
| 8 | q57–q64 | 0 | 0 | 0 | 75,42 | 2,09 |
| 9 | q65–q72 | 0 | 0 | 0 | 72,01 | 2,42 |
| 10 | q73–q80 | 0 | 0 | 0 | 68,79 | 2,08 |
| 11 | q81–q88 | 0 | 0 | 0 | 71,02 | 2,06 |
| 12 | q89–q96 | 0 | 0 | 0 | 70,15 | 1,91 |
| 13 | q97–q104 | 0 | 0 | 0 | 69,14 | 2,03 |
| 14 | q105–q112 | 0 | 0 | 0 | 70,43 | 2,17 |
| 15 | q113–q120 | 0 | 0 | 0 | 70,52 | 1,98 |
| 16 | q121–q127 | 52.268 | 52.459 | 0 | 70,05 | 2,09 |
| 17 | q129–q136 | 0 | 0 | 0 | 72,06 | 2,24 |
| 18 | q137–q144 | 0 | 0 | 0 | 71,71 | 1,97 |
| 19 | q145–q152 | 0 | 0 | 0 | 74,12 | 2,28 |
| 20 | q153–q160 | 0 | 0 | 0 | 68,28 | 2,01 |
| 21 | q161–q168 | 0 | 0 | 0 | 66,70 | 2,07 |
| 22 | q169–q176 | 0 | 0 | 0 | 68,83 | 1,95 |
| 23 | q177–q184 | 0 | 0 | 0 | 66,83 | 1,96 |
| 24 | q185–q192 | 0 | 0 | 0 | 68,39 | 1,85 |
| 25 | q193–q200 | 0 | 0 | 0 | 68,99 | 1,92 |
| 26 | q201–q208 | 0 | 0 | 0 | 75,78 | 1,91 |
| 27 | q209–q216 | 0 | 0 | 0 | 71,23 | 2,08 |
| 28 | q217–q224 | 0 | 0 | 0 | 72,91 | 2,26 |
| 29 | q225–q232 | 0 | 0 | 0 | 70,47 | 2,09 |
| 30 | q233–q240 | 0 | 0 | 0 | 68,99 | 2,11 |
| 31 | q241–q248 | 0 | 0 | 0 | 71,54 | 2,23 |
| 32 | q249–q254 | 0 | 0 | 0 | 51,61 | 1,53 |

| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |
|---:|---:|---:|
| 1 | 8619,793970592149 | 6754,237595446607 |
| 3 | 15767,655464816849 | 12486,345784654337 |
| 9 | 9501,9437281540304 | 7733,1467868203645 |
| 33 | 4877,1680091117614 | 4328,1743490305198 |

Kampagnens faktiske vægtid til terminalmarkøren var **38,77 minutter**. De krediterede søgninger brugte 2.238,80 sekunders vægtid og 2.231,22 CPU-sekunder. De afgrænsede kontroller brugte 65,89 sekunders vægtid og 91,85 CPU-sekunder. Dette er BN-målinger, ikke projektets samlede forbrug. Ved stop indgår eventuelle senere fejlede procesforsøg ikke i tallene for de krediterede batches.

De udvalgte uafhængige `math.fsum`-summer har største observerede afvigelse **0**. Kalibreringsgenberegninger med den delte kernel har største observerede afvigelse **0**. De afsluttede audits består deres fastlagte kontrolkrav; de faktiske afvigelser gengives her, også når de er forskellige fra nul.

De gemte komplette normaliseringskvitteringer er sammenholdt med BK's **96 unikke native172-rækkehashes**. Det gav 3.072 hash-sammenligninger, heraf 3.072 i de afsluttede, auditerede batches. En eventuel normaliseringskvittering fra et senere delvist forsøg giver ikke søgedækning. Alle bevarede kilde-, plan-, input- og auditerede artefakthashes kontrolleres igen før og efter pakning. Faktiske exitkoder, stdout-EOF, afsluttet procesventning samt observerede og gemte logbytes og loghashes bevares.

Den særskilte efterkontrol af de allerede gemte q127-målinger omfatter **52.268 ON-sporforslag**. 32 opfylder kravet i alle tre ON-scans; 32 af disse har også OFF-udslag ved veto-grænsen. 52.236 opfylder ikke kravet i alle tre ON-scans. q127 ligger ved det udeladte DC-bånd q128. Antallene er korrelerede sporforslag, ikke et tilsvarende antal forskellige signaler. [Fordeling fra de gemte målinger](work_bn/results/Q127_TRIAGE_DISPOSITION_BN.json).

Dette er afgrænset numerisk konsistenskontrol, ikke en uafhængig genberegning af alle spor eller en kvalifikation af den oprindelige rådatakodek, normaliseringsmodellen, astronomisk følsomhed eller falsk-alarm-sandsynlighed. Lokal ESS er ikke kalibreret sigma, SNR eller FAP; sporkombinationerne er korrelerede. Et bestået beskrivende flag udløser stop og særskilt vurdering, ikke automatisk en SETI-detektion.

Der er tale om genanalyse af tidligere eksponerede data fra ét historisk besøg. Ingen nye eller blinde observationer, uafhængig astronomisk validering eller ny oprindelig dækning påstås. A/B- og B06-fejlstatusser bevares. HIP44295 og de beskyttede 2016-/2019-data er ikke åbnet. Der blev foretaget **0 nye forespørgsler til teleskoparkivet** og brugt **0 DKK**. BA-opgørelsen forbliver 486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg.

Den validerede resultatpakke har **722.017.229 bytes og 5.192 medlemmer**. Hvert medlems CRC og SHA-256 er kontrolleret. Arkivets SHA-256 er `7096722fba6fdfceeff9935f6d9e8cb35923dab9551332313de90767da0010ca`. Pakken er opdelt i følgende fortløbende bytedele, som skal samles i rækkefølge før udpakning:

- [SETI_BN_SEARCH_RESULTS_2026-10-30.zip.part01](https://chatgpt.com/library?file_id=libfile_8ec9807c35f4819181a3cde0fd1de18b&account_id=personal): 209.715.200 bytes, SHA-256 `f559d4bf402a7ea491341234df2f795740c8dbeef4b1c022b8ef2868e53b9260`.
- [SETI_BN_SEARCH_RESULTS_2026-10-30.zip.part02](https://chatgpt.com/library?file_id=libfile_45fbbc5f18e4819192112b4398e59a38&account_id=personal): 209.715.200 bytes, SHA-256 `c4d60614c4ca1ae7f041207cdc8ba9b2661c4499dde12bceb9f76622aeff9c41`.
- [SETI_BN_SEARCH_RESULTS_2026-10-30.zip.part03](https://chatgpt.com/library?file_id=libfile_15ec5c8925148191a6e8858058f0600c&account_id=personal): 209.715.200 bytes, SHA-256 `11a79a3aa73c6b71159f97148dacc394e3a09840710b8168d7acf829a372ddcf`.
- [SETI_BN_SEARCH_RESULTS_2026-10-30.zip.part04](https://chatgpt.com/library?file_id=libfile_59801cee4064819189b693dbc80a7275&account_id=personal): 92.871.629 bytes, SHA-256 `af54c294d3d8bd433b924072a8533475d56b757c0e24c174afb085c7516ca4fe`.

Alle ovenstående resultatdele er gemt. Den samlede bytefølge er verificeret mod arkivets hash. Genoptagelsesfilen bevarer rådatadelenes tidligere identiteter og kontrolsummer. Programkode, planer, proceslogfiler og tekstlige resultater offentliggøres på GitHub; de binære arrays bevares i resultatpakken.

**Næste trin:** Vurder yderligere allerede gemte datagrundlag, mulighederne for kontrolleret adgang til flere arkivdata samt den manglende kvalifikation og kalibrering af søgemetoden. Fastlæg en særskilt plan før nye scores eller arkivforespørgsler. Bevar de historiske A/B- og B06-fejl og no-retry-statusser. Der udpeges ikke automatisk en ny nativeblok.

BN-kampagnens terminalkvittering angiver, at ingen BN-signalsøgning kører videre i baggrunden efter denne afslutning.

- [Samlet resultat](work_bn/results/REAL_SEARCH_SUMMARY_BN.json)
- [Afslutnings- og fejllogik](work_bn/run_campaign_bn.py)
- [Faste planer](work_bn/plans) og [forhåndsfastlagt scope](work_bn/PREREG_BN.md)
- [Proceskvitteringer og logfiler](work_bn/execution)
- [Resultatkontroller](work_bn/review)
- [Leverance og fortsættelsespunkt](work_bn/DELIVERY_BN.json)

En særskilt afslutningskontrol genhashte **7.489 evidensfiler** og sammenholdt **3.072 rækkehashes** uden uoverensstemmelser. [Kontrolresultat](work_bn/review/INDEPENDENT_CLOSED_REVIEW_BN.json).

De tre valgte blokke native170–172 fra dette samme 2017-besøg er nu gennemgået i den lokale ESS-familie, i alt 759 carrierbånd. Dette er genanalyse af gemte data og ændrer ikke BA's oprindelige dækningsopgørelse.

**Konkret næste forberedelse:** HIP45688 fra et andet, allerede eksponeret historisk besøg. Den præcise gamle kildekode og scope er genfundet; en særskilt ny familie kræver først en streng NPY-inputadapter og på forhånd fastlagte parrede metodekontroller. Den tidligere M-kørsels 24 raw-sum-fejl og full-QA=false bevares. Der er endnu ikke åbnet powers eller kørt scores på dette næste datasæt. [Metadata- og kildereview](work_bn/review/NEXT_FAMILY_HIP45688_SCOPE_REVIEW_BN.json) · [Kontroloplæg, ikke frosset eller aktiveret](work_bn/next_scope/HIP45688_PAIRED_CONTROLS_DRAFT.json).
