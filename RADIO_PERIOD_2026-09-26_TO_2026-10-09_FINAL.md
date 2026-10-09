# SETI: afslutning af perioden 26. september–9. oktober 2026

**Status: CLOSED_2026_10_09_SKY_PILOT_BLOCKED. Faktisk slutlukning: 9. oktober 2026.** Den gamle periodes faglige arbejde og lukkede forsøg var allerede afsluttet. Denne rapport afslutter den sidste formelle konsolidering; den indleder ingen ny fejlfinding. Hovedmålet er NOT_ACHIEVED, ikke en nuldetektion.

Den daterede gennemgang læste det aktuelle science-head `76405d84b096f1dea4ce9aded0e9aeb792bef220`, dets status/retning og den særskilte 7.–20. oktober-plan. De gamle primærkilders Git-blob-hashes er uændrede mod 8.-oktober-udkastets immutable grundlag `13131757641c06d7bfcb10790a79811c750b1178`. Der er ingen nye originale resultater, som ændrer den gamle gate eller dispositionerne. Originale rapporter, fejl, reservationer og uåbnede testpaneler bevares. Ingen spektre, holdouts, kodekørsler eller lukkede tests genåbnes ved denne afslutning.

Den gamle plans hovedmål er ikke opnået: der er ikke gennemført en ny, uafhængig ON/OFF-sky-pilot under dens kontrakt. Den nyttige afslutning er derfor en dokumenteret, afgrænset blokering med bevaret evidens. Det er et udfald, som den [oprindelige plan](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_TWO_WEEK_PLAN_2026-09-26.md) udtrykkeligt tillader ved manglende kildeadgang eller faglig godkendelse.

## Hvad perioden faktisk gav

| Forpligtelse | Bevaret resultat | Grænse for konklusionen |
|---|---|---|
| Vælge en ny ON/OFF-sekvens efter metadata | HD189733/HIP98505, cadence 85030, session AGBT16A_999_97, ON 0003/0005/0007 og OFF 0004/0006/0008 blev valgt. | Kildevalget og metadata er ikke en gennemført spektralsøgning. Den oprindelige preparation-kontrakt forbliver ikke klar til udførelse. |
| Kvalificere den oprindelige syntetiske kalibrering | Alle tre kalibreringer blev beregnet; ingen opfyldte kravet om endelige null-maksima i alle 127 resampling-rækker. De 381 rækker gav 201 endelige og 180 EMPTY-maksima. | Det er korrelerede resamplings, ikke 381 uafhængige støjkontroller. Der blev ikke udstedt en operationel tærskel. |
| Forklare kalibreringsfejlen inden for den ene tilladte diagnose | Uafhængig optælling af de gemte scores reproducerede samtlige tomme og ikke-tomme udfald. Kravet om samtidig S/N over 3 i mindst to aktive epoker efterlod lovlige EMPTY-udfald. | Den lukkede diagnose kvalificerer ikke en ændret kalibreringsregel. Gamle evalueringer har 0 udførte runs og 0 åbnede værdier. |
| Demonstrere komponenter til læsning og eksekvering | F observerede afgrænset child-IO. G overførte og dekodede ét kontrolleret 16-rækkers codec-handoff. H–P leverede afgrænsede forberedelser og kildeinterfaces. | Kontrollerede data og source-tests er ikke de tolv krævede handoffs, fuld native/runtime-kvalifikation eller adgang til sky-piloten. |
| Gemme en forklaring, som kan bruges ved periodens lukning | Q samlede 232 rapport-/metadata-bodies, heraf 214 root RADIO-rapporter, og tydeliggjorde resultater, mangler og reservationer. | Q er en efterprøvbar rapportoversigt; den genanalyserer ikke alle oprindelige arkiver og genskaber ikke historisk runtime-custody. |

Kilder: [Q-afslutningsforberedelsen](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_CLOSURE_2026-10-07_PREPARATION.md), [den oprindelige kalibrering og lukkede diagnose](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_HD189733_PANEL_2026-09-28_RESULT.md).

## De konkrete blokeringer

Det gamle kalibreringsforsøg er lukket uden bestået faglig gate. Den særskilte 127-reference/24-evaluerings-proposal er fortsat **NOT_ACTIVATED**, uden genererede værdier eller tildelt forsøgsbudget; native8 er ureserveret. Originale preparation-felter og lukkede allocations bliver ikke opdateret til bestået af senere komponentarbejde.

Den gamle runtime-rute mangler stadig 136 autentiske originalmedlemmer ifølge K. M's eneste faktiske namespace-observation stoppede ved `ns/pid` med EACCES før maps/auxv/exe/vDSO-læsninger og er lukket uden retry. P er afsluttet som **SOURCE_ACTIVITY_MODEL_COMPLETE_NO_NATIVE_ACTIVATION**. Disse mangler kræver nye autentiske input og tilladt observeradgang, samt en separat prospektiv, integreret kontrakt; en gentagelse af P/O/M/K leverer dem ikke. Kilder: [Q](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_CLOSURE_2026-10-07_PREPARATION.md) og [P-resultatet](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_ACTIVITY_2026-10-07P_RESULT.md).

Uden en gennemført pilot kan perioden ikke levere en sky-hitliste, empirisk skyfølsomhed, flux/EIRP-grænse eller en søgebaseret afvisning af kunstig emission. Fraværet af en analyse er ikke en nuldetektion.

## Den nye periode er særskilt

Den godkendte [plan 7.–20. oktober](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_TWO_WEEK_PLAN_2026-10-07.md) ændrede den prospektive reproducerbarhedskontrakt og begyndte straks. Dens fremdrift ændrer ikke udfaldet under den gamle kontrakt.

Der blev faktisk læst og analyseret autentiske teleskopværdier i den [lokale Voyager-reference 7. oktober](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_REFERENCE_LOCAL_2026-10-07_RESULT.md): ét kendt referencescan, 16 tidsrækker, 28.633 søgte bærefrekvenskanaler og bevaret output. Dets 2.369 tærskelkanaler er korrelerede kanalsvar, ikke 2.369 uafhængige kandidater. Denne reference har ingen OFF-data og kvalificerer ikke en ny sky-pilot. Den tæller derfor som reference/engineering i den nye periode og udfylder ikke den gamle plans seks-scans hovedmål. Den nye periodes validerings- og metodeudfald opgøres i dens egne rapporter og ressourceledger.

## Ressourcer og bevarede dispositioner

De historiske **2.920 s / 5.512 MiB** er seksten udvalgte, permanent debiterede reservationsrammer. De er hverken målt samlet tidsforbrug eller hele periodens ressourceforbrug. Fem separate process-AS-kontroller, K's administrative ramme og øvrig historik ligger uden for subtotalen. Periodens samlede målte forbrug forbliver **ukvalificeret/null**, ikke nul. Ingen gammel reservation refunderes eller nulstilles. [Q's ressourceafstemning](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_CLOSURE_2026-10-07_PREPARATION.md) er grundlaget.

- **HD1461/HIP1499:** `HOLD_POINTING_PROVENANCE_UNRESOLVED` bevares. Den offentlige mål-log giver ikke samme-scans pointing-proveniens; metadataanmodningen er usendt. Se [originalt log-resultat](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/RADIO_PUBLIC_LOG_CONTACT_2026-09-27_RESULT.md).
- **M43AI:** fejlet og lukket; modellen er ikke adopteret. De oprindelige 112+128 M43AF-holdouts forbliver uåbnede. Se [M43AI-resultat](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md) og Q's aktuelle dispositioner.
- **M15/GJ581 og M33/HD3651:** fortsat uafklarede; ingen ny disposition tildeles her. **GJ724** forbliver urørt reserve. Q bevarer disse statusser.
- **LS:** pauset ved LS8BD–LS8BE; LS8BF er urørt, gemt genstart. De 16 tidligere uafklarede hændelser bevares. **CHEOPS:** kalibrering NOT_READY; teknisk anmodning UNSENT. Se [den tidligere LS/CHEOPS-periodegennemgang](https://github.com/andersenmartin-blip/setisearch/blob/13131757641c06d7bfcb10790a79811c750b1178/TWO_WEEK_REVIEW_2026-09-26.md) og Q's senere pause-status. Den ældre reviews LS8BF-next-action er historisk og er overtaget af radio-planen.

## Slutlukningen er gennemført 9. oktober

Den aktuelle status, retning og nye plan er afstemt mod det bevarede udkast. Gammel periodes hovedmål og blokeringer er uændrede og nu afsluttet i denne daterede rapport. Perioden **26. september–9. oktober er lukket**. Senere arbejde tilhører den særskilte godkendte 7.–20. oktober-plan og kan ikke kvalificere den gamle kontrakt med tilbagevirkende kraft.

Der resterer ingen gamle source-tests, native-kontroller, kalibreringsforsøg eller spektralsøgninger til automatisk gentagelse. Q/P/O/M/K, reservationer og uaktiverede evalueringer ændres ikke. Nye autentiske input eller en ny faglig tilgang ville kræve en særskilt prospektiv kontrakt; denne lukning aktiverer ingen sådan kampagne. Der sendes ingen metadataanmodning, besked eller booking.

Dagens tekst-/paknings-/publiceringsarbejde indgår i en særskilt konservativ reservation under den nye periodes regnskab; det udfylder ikke ukendte målinger for den gamle periode. [Aktuel rapportledger](results/radio_report_package_20261009/REPORT_PACKAGE_LEDGER.json) · [Dateret kildeafstemning](results/radio_report_package_20261009/OLD_PERIOD_FINAL_PROVENANCE.json) · [Uafhængigt slutreview](results/radio_report_package_20261009/OLD_PERIOD_FINAL_REVIEW.md).
