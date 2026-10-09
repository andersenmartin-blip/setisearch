# SETI-radio: rapportleverance og reproduktionspakke klar 9. oktober 2026

**Status: REPORT_DELIVERABLE_COMPLETE_ASOF_2026_10_09.** Den samlede rapportleverance er færdiggjort 9. oktober ud fra afsluttede beregninger og gemte resultater. Den godkendte periode er fortsat 7.–20. oktober, med et afsluttende checkpoint den 20. oktober; denne faktiske dato flyttes ikke bagud eller registreres som allerede passeret. Rapport- og pakningsarbejdet er fremrykket, fordi det kan afsluttes nu.

## Konklusion og faktisk fremdrift

Planens hovedmål, en ny søgning i en offentlig seks-scans ON/OFF-sekvens, er endnu ikke opnået og er blokeret af fejlet validering. Den autentiske Voyager-reference blev gennemført. Det godkendte metodealternativ er også faktisk beregnet og afsluttet: 64 nye syntetiske forsøg, efterfulgt af analyser af bevarede resultater om interferens, korte signaler, OFF-tab og støj. Ét gemt resultat er kontrolleret én gang i en frisk proces. A og B forbliver **FAIL_CLOSED**.

Undersøgelsen dokumenterer bestemte styrker og svagheder ved den frosne metode. Den giver ingen ny konklusion om tilstedeværelse eller fravær af udenjordiske signaler. En blokeret sky-pilot er ikke en nuldetektion.

| Leverance | Faktisk status pr. 9. oktober |
|---|---|
| Autentisk reference | Voyager-carrier demonstreret 7. oktober på den anden og sidste engineering-rute |
| Ny seks-scans sky-pilot | Ikke admitted; spektrumpayload uåbnet; 0 gennemførte pilotsekvenser |
| Udvikling | DEV: 24/24 fulde forsøg med beståede udviklingskontroller |
| Frisk validering A | 142 identiteter forsøgt; 140 afsluttede, 2 CPU-afbrudte; FAIL_CLOSED |
| Den ene udviklingsrettelse | Kun kørselsallokering; 2 nye DEV_RUNTIME-forsøg afsluttet; videnskabelig kode uændret |
| Frisk validering B | 142/142 afsluttet; faglige delkrav fejler; FAIL_CLOSED |
| Metodealternativ | 64/64 afsluttede, deskriptive forsøg; ingen kvalifikationsmyndighed |
| Gemte fejlanalyser | RFI-geometri, transienter, nær-OFF og støj afsluttet og gennemgået |
| Frisk-proces-verifikation | Gennemført 8. oktober; milepælen fra 19. oktober gentages ikke |
| Gammel periode | Formelt lukket 9. oktober; gamle faglige udfald uændrede |
| Samlet ny rapport og pakke | Rapportleverance afsluttet 9. oktober; periodens checkpoint 20. oktober afventer |

## Reference og sky-dækning

Den lokale reference læste den offentlige, kendte Voyager-1 FIL-fil på 67.109.246 bytes. Alle 16 × 1.048.576 = 16.777.216 float32-power-værdier blev kontrolleret som endelige og ikke-negative. Søgningen omfattede 28.633 native bærefrekvenser gennem alle 16 integrationer, 785 driftforsøg i ±4 Hz/s og kanalcentre fra 8419,260002207011 til 8419,339999090880 MHz. Første til sidste integrationsmidtpunkt spænder 273,80416512 s.

Det stærkeste kendte carrier-spor havde referencefrekvens 8419,297027867287 MHz, drift −0,377551020408164 Hz/s og maksimal robust engineering-trackscore 1004,1205388466. De 2.369 kanaler over tærsklen 10 er korrelerede svar, ikke 2.369 uafhængige signaler; de 116 repræsentative frekvenspeaks er en beskrivende gruppering. Analysekommandoen brugte 3,747761 CPU-s og 3,750069 s vægtid, med peak RSS 224.813.056 bytes. Dette er kommandomålinger, ikke fuldt målt reference- eller kampagneforbrug inklusive kildehentning og forberedelse.

Dette er én kendt referencescan uden OFF. Den demonstrerer læsning og lineær driftsøgning, men opfylder ikke målet om en ny ON/OFF-søgning. Voyager-CI-rutens tidligere fejl bevares; ingen tredje engineering-rute aktiveres.

HD189733/HIP98505-kildens metadata identificerer seks historiske scanninger fra ét besøg den 17. marts 2016. De 96 udvalgte komprimerede payload-ranges er deklareret til 305.133.821 bytes; metadatatilgangen modtog 1.158.240 bytes inklusive det bevarede fejlforløb. **Ingen af de udvalgte spektrumpayloads er åbnet.** Codec-kompatibilitet med disse værdier er derfor ikke bevist. Den nye pilot har 0 søgte Hz og 0 analyseret ON-eksponering; planlagt dækning og referencebånd tælles ikke som pilotdækning.

## Hvorfor valideringen stopper piloten

DEV er softwareudvikling og kan ikke erstatte frisk validering. A registrerede alle 142 forsøgsidentiteter, men to nødvendige single-row-transientforsøg blev afbrudt ved deres 250-CPU-sekunders grænse. Afbrudte forsøg tælles hverken som genfund eller målte nuludfald. Den ene tilladte rettelse ændrede alene den løbende kørselsallokering. Detektor, generator, kontrakt, tærskler og OFF-regel blev bevaret før det helt friske B-panel.

| B-krav | Målt resultat | Frosset minimum / maksimum | Udfald |
|---|---:|---:|---|
| Komplette og intakte forsøg | 142/142 | Alle | Består |
| Stærke signaler, alle aktive ON | 14/14 | 14/14 | Består |
| Arbejdsniveau, alle aktive ON | 45/48 | Mindst 44/48 | Består samlet |
| Arbejdsniveau: kun tredje ON aktiv | 6/8 | Mindst 7/8 | **Fejler** |
| Arbejdsniveau: intrinsisk bredde 3 kanaler | 21/24 | Mindst 22/24 | **Fejler** |
| RFI-forløb med et hvilket som helst overlevende hit | 2/24 | 0/24 | **Fejler** |
| Støjforløb med overlevende kandidat | 0/32 | Højst 1/32 | Består i panelet |

Arbejdsniveau gav genfund i mindst ét aktivt ON i 46/48 forløb; dette alternative mål ophæver ikke kravet om genfund i alle aktive ON eller de fejlede delgrupper. B's RFI-hovedspor blev først lokaliseret og derefter afvist, men 14 andre carriers overlevede i to RFI-forløb. Gaten krævede nul rester af enhver placering. En vellykket afvisning af hovedsporet ændrer derfor ikke FAIL_CLOSED.

## Hvad metodeundersøgelsen viste

ALL betyder korrekt lokaliseret genfund efter OFF i hvert aktivt ON; ANY betyder genfund i mindst ét aktivt ON. Hver af de 64 præcise kombinationer af idealniveau, drift, bredde og aktivitet har én støjrealisering og én frekvensplacering. Placeringerne er balanceret i marginalerne, ikke gentaget fuldt i hver celle. Undersøgelsen blev valgt efter B's fejl og er eksplorativ.

| Indsprøjtet idealniveau | ALL | ANY |
|---|---:|---:|
| 10 | 6/16 | 12/16 |
| 12 | 14/16 | 15/16 |
| 16 | 16/16 | 16/16 |
| 24 | 16/16 | 16/16 |
| Samlet | **52/64** | **59/64** |

Af 128 aktive ON-scans gav 115 et lokaliseret overlevende genfund. De 13 tab i 12 forsøg skyldtes manglende ON-hit over tærsklen 10; ingen lokaliserede genfund blev mistet ved OFF i denne signalbank. Kun tredje ON gav ALL/ANY 27/32; alle tre ON gav ALL 25/32 og ANY 32/32. Forskellige støjtræk og forskellige genfundskrav forhindrer en kausal konklusion om sidste besøg.

Idealniveau er generatorens støjfri boksprojektion i Gamma16-støjmodellen, hverken målt SNR, flux eller EIRP. Niveau 16/24 bestod alle observerede celler; det er ingen universel følsomhedsgrænse eller estimeret genfindingssandsynlighed. Scan- og carrierantal er ikke ekstra uafhængige forsøgsreplikater.

## De bevarede fejl og deres betydning

**RFI:** Alle 14 overlevende B-spor udelukker den præcise indsprøjtede RFI-drift fra deres kompatible OFF-matchfamilie, selv med frit flyttet referencefrekvens. Bredeste OFF-tolerance tillader driftforskel højst 0,735693561 Hz/s; de observerede forskelle er 0,784632434–0,859992612 Hz/s. De 42 originale, udtømte OFF-sammenligningers kompatible maksimumscores var alle under 8, højest 7,926772881. Samtidig blev alle 472 sandhedslokaliserede ON-hits i de to forløb vetoet. Geometrien er dokumenteret; bidragene fra RFI, støj og preprocessing til de resterende ON-scores er ikke isoleret ved et kontrafaktisk forsøg.

**Korte signaler:** Alle 12 B-transientforløb overlevede. Indsprøjtningen er smal i frekvens og aktiv i én af 16 integrationsrækker, ikke et bredbåndsudbrud. De 8.114 overlevende ON-carriers er korrelerede svar; 428 er lokaliseret efter den frosne regel ved begge hele-ON-endepunkter. At et spor passerer tærsklen dokumenterer derfor ikke, at signalet varede hele scanningen. En kort eller enkelt-ON-forekomst kan stadig være et ægte signal og må ikke afvises alene på varighed eller manglende gentagelse.

**Nær-OFF:** 11 af 12 indsprøjtede ON-signaler blev genfundet før OFF; alle deres 66 lokaliserede carriers blev derefter vetoet af den følgende forurenede OFF. Det sidste forsøg havde intet ON-hit over 10 og blev mistet før OFF. Der er således 11 forløb med dokumenteret OFF-tab, ikke 12. Geometrien viser risikoen for signal-tab tæt på OFF-interferens; den retfærdiggør ikke en efterfølgende lempelse af den allerede frosne gate.

**Støj:** De 32 B-støjforløb, otte under hver af fire forskellige love, gav nul ON-threshold-hits. Fraværet af slutkandidater skyldes her, at intet nåede ON-gaten, ikke succesfuld OFF-afvisning. Det lille, heterogene syntetiske panel kalibrerer ingen falskalarmrate for teleskopdata.

Disse fund peger på et reelt udviklingsdilemma: bredere RFI-afvisning kan koste genfund af nærliggende signaler. Det allerede gemte forslag til 148 parrede arrayversioner i 18 støjblokke undersøger tidsprofiler, fast sandbane versus globalt maksimum og fælles RFI-/nær-OFF-kontroller. Det er et forslag til en senere separat protokol, ikke udførte eller admitted forsøg i denne periode. Identiske observerede arrays med forskellige oprindelseslabels kan ikke skelnes af en algoritme; sammenfald kan kræve status uafklaret.

## Afgrænset verifikation og reproduktionsgrænse

Den ene gemte METHOD-case000 blev verificeret i en frisk proces 8. oktober efter durabel afslutning af hele 64-case panelet. Resultatet er **PASS_BOUNDED_SAVED_RESULT_VERIFICATION**: 6 gemte scorekort, 20 artefakthashes og 96 OFF-sammenligninger stemmer med de oprindelige hits, dispositioner og recovery-records; 32/32 oprindelige carriers overlever.

Det kontrollerer gemte kort → hits/veto/genfund. Rå power, preprocessing og detektorscores blev ikke genskabt; det er heller ikke en ny støjrealisering, et uafhængigt andet miljø eller en gentagelse af alle 64 forsøg. De 54 originale inputs på 1.896.541 bytes blev autentificeret. En lokal, afkortet koordinatortransport blev fanget før verifier-start og rettet ved én hentning af samme immutable arkiv. Begge restaureringsjobs og den ene verifier indgår i de målte 0,262767 CPU-s. Der var én verifier-invocation og ingen retry. Den historiske cases 73,064369 CPU-s er ikke dagens verifikationstid.

Kalenderens 19. oktober-opgave er dermed gennemført tidligere inden for protokollens afslutningsgate og gentages ikke. Ældre rapporters pending/19.-oktober-felter er historisk planlægningsproveniens; den faktiske verifikationskvittering fra 8. oktober er gældende.

## Ressourcer og ukendte målinger

Periodens loft er 43.200 CPU-s og 0 kr.; de fastlagte RAM-, jobtid-, kildebyte- og workspace-grænser ændres ikke. Følgende er udvalgte afsluttede paneldebiteringer, ikke et fuldstændigt målt totalforbrug:

| Post | CPU-s | Regnskabsbetydning |
|---|---:|---|
| DEV | 1.757,554301 | Hele proces-/parent-regnskabets debit |
| A, inklusive afbrydelser | 11.143,686462 | Konservativ afsluttet paneldebit |
| B | 11.676,036546 | Børn + controller, konservativ afsluttet paneldebit |
| METHOD | 5.407,226987 | Børn + controller, afsluttet paneldebit |
| Oprindelig forberedelse | 1.200 | Umålt, konservativ reservation; ingen refundering |
| Senere RFI / diagnostik / design / verifikation | 100 / 200 / 100 / 150 | Separate konservative reservationer; målte komponenter ikke debiteret igen |
| Samlet rapportudkast 8. oktober | 50 | Konservativ reservation; hele arbejdet ikke fuldt målt |
| Afslutning og reproduktionspakke 9. oktober | 100 | Ny konservativ reservation til tekst-/figurhentning, pakning, review og udgivelse; målte komponenter debiteres ikke igen |

8.-oktober-udkastets ledger havde 6.012,705144981004 CPU-s tilbage efter sin særskilte 50-sekunders reservation. Efter 9.-oktober-pakkens nye 100-sekunders reservation er saldoen **5.912,705144981004 CPU-s**, hvoraf mindst 2.000 bevares til det afsluttende checkpoint. Tidligere reserver og historiske ukendte målinger ændres ikke. Differencen mellem loft og saldo er regnskabsdebiteringer inklusive reservationer, ikke målt samlet fysisk CPU-forbrug.

Den tidligere CI-post på 4.800 CPU-s og engineering-byte-reservationen på 256 MiB er fortsat konservative/ufuldstændigt verificerede; nominel samlet engineering-byte-overholdelse hævdes ikke bevist. Fejl tælles, gamle reservationer tilbagebetales ikke, og ingen nye skydata eller gamle holdouts er åbnet ved rapportarbejdet.

## Rapportleverancen er afsluttet; periodens checkpoint består

Den gamle 26. september–9. oktober-periode er formelt lukket i [dens endelige rapport](RADIO_PERIOD_2026-09-26_TO_2026-10-09_FINAL.md). De gamle beregninger var allerede afsluttet, og den nye konsolidering ændrer ingen gammel gate, ukendt måling eller uaktiveret evaluering. Blokeringen er fortsat ingen nuldetektion.

Denne periodes rapportleverance og den lille reproduktionspakke er færdiggjort 9. oktober. Kalenderen er arbejdsmilepæle; færdigt rapportarbejde behøver ikke vente til 20. oktober. Den 20. oktober udføres alene det afsluttende periodestatus-checkpoint ud fra faktisk foreliggende evidens. Uden nye autoriserede resultater genudgives denne rapport ikke som en ny analyse. Ingen yderligere detektorkørsel, nyt kvalifikationspanel, tærskelændring eller tredje engineering-rute aktiveres. Afsluttede audits og case000-verifikationen gentages ikke som dagligt fremskridt. De gamle 112+128 holdouts og øvrige uåbnede paneler forbliver uåbnede; historiske kandidat-/pointing-holds, LS og CHEOPS-status ændres ikke. Perioden forlænges ikke automatisk.

## Reproduktionspakken

Den lille [SETI_RADIO_REPORT_KIT_2026-10-09.zip](results/radio_report_package_20261009/SETI_RADIO_REPORT_KIT_2026-10-09.zip) samler den aktuelle rapport, den gamle slutlukning, frosne kode-/protokoltekster, A/B/METHOD-resultatmetadata, METHOD-tabeller, seks originale vektor-PDF-figurer og den faktiske 8.-oktober-verifikationskvittering. [Pakkevejledningen](results/radio_report_package_20261009/KIT_GUIDE.md) beskriver indhold og brug. Kode pakkes som inerte, historiske filer; ingen generator, detektor, rapport-renderer eller verifier udføres ved pakningen.

Casearkiver og scorekort ligger eksternt i immutable Git-publikationer; pakken er ikke et komplet offline-verifier-layout. Rå syntetisk power er ikke bevaret i disse artefakter, og ingen råscore-reproduktion hævdes. De originale PNG-figurer er eksterne; de seks originale PDF-figurer medtages uden genrendering. Manifest og SHA256SUMS gør de inkluderede bytes kontrollerbare, mens eksterne indeks identificerer de bevarede arkiver.

## Primært kildegrundlag

Rapporten bygger på det allerede gennemsete 8.-oktober-udkast og eksisterende resultater ved immutable kildecommit `76405d84b096f1dea4ce9aded0e9aeb792bef220`. Den tilføjer ingen nye data eller scores. [Oprindelige 19 kildebindinger](results/radio_period_report_draft_20261008/SOURCE_BINDINGS.json) og [pakkens aktuelle manifest](results/radio_report_package_20261009/KIT_MANIFEST.json) identificerer inputtene. [Aktuel rapportledger](results/radio_report_package_20261009/REPORT_PACKAGE_LEDGER.json) fastholder den nye saldo.

- [Godkendt plan](RADIO_TWO_WEEK_PLAN_2026-10-07.md) · [Voyager-reference](RADIO_REFERENCE_LOCAL_2026-10-07_RESULT.md) · [DEV](RADIO_PILOT_DEVELOPMENT_2026-10-08_RESULT.md).
- [Validering A](RADIO_VALIDATION_A_2026-10-08_RESULT.md) · [Validering B](RADIO_VALIDATION_B_2026-10-08_RESULT.md) · [METHOD-tabeller og seks figurer](results/radio_pilot_method_report_20261008/METHOD_STUDY_REPORT.md).
- [RFI-geometri](results/radio_rfi_alias_analysis_20261008/RFI_ANALYSIS_REPORT.md) · [Diagnostik](results/radio_diagnostics_20261008/DIAGNOSTIC_REPORT.md) · [Senere designforslag](results/radio_next_design_20261008/DECISION_BRIEF.md).
- [Faktisk 8.-oktober-verifikation](results/radio_saved_verification_20261008/VERIFICATION_REPORT.md) · [Dens ledger](results/radio_saved_verification_20261008/VERIFICATION_LEDGER.json) · [Original verifier-kvittering](pilot_protocol_20261008/review/METHOD_SAVED_CASE_000_REPRODUCTION.json).
- [Gammel periode: faktisk afslutning 9. oktober](RADIO_PERIOD_2026-09-26_TO_2026-10-09_FINAL.md).
