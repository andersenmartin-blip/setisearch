# Klargøring af den gemte METHOD-verifikation den 19. oktober

Udarbejdet 8. oktober 2026. **Status: statisk input- og proveniensinventar færdigt; selve verifikationen er fortsat planlagt til19.oktober og er ikke kørt.** Alle 21 adgangskrav fra den oprindelige admission findes i den fastlåste Git-kilde og matcher deres oprindelige SHA256, Git-blob og byteantal. De to nødvendige arkivers Git-metadata matcher deres publicerede manifest og uploadindeks. Der er ikke fundet manglende inputs i denne kilde.

Kilde: `andersenmartin-blip/setisearch`, gren `m43-support-qualification`, uforanderlig commit `a7b086156d55bbfe7678b960d313d03823cf630c`. Den eneste planlagte case er `SETI_RADIO_PILOT_20261008_METHOD_STUDY:method_signal:000`.

Ingen arkivkroppe eller numeriske kort er hentet eller åbnet i denne klargøring. Ingen generator, detektor eller NumPy er importeret eller kørt. Der er ingen nye scores, syntetiske træk, teleskopværdier eller åbning af de historiske 112+128 holdouts. A/B er fortsat fejlet, og qualification er fortsat false. Dette dokument er hverken `PASS_BOUNDED_SAVED_RESULT_VERIFICATION` eller en teleskopkvalifikation.

## Det konkrete restaureringssæt

Den valgte kodegren kræver 54 filer på deres oprindelige relative pladser: 21 adgangskrav, én oprindelig admission, ét verifikationsprogram, 22 case000-medlemmer og 9 udvalgte koordinatormedlemmer. Tilsammen fylder deres deklarerede/restaurerbare bytes 1.896.541. Dokumentation og pakkemanifester kan beholdes til proveniens, men er ikke ekstra runtime-afhængigheder i dette 54-filers sæt.

Restaurér kun de nødvendige medlemmer fra nedenstående to arkiver. Der kræves ingen øvrige METHOD-casearkiver, intet nyt panel og ingen B-casearkiver. B's allerede publicerede afslutningsfiler indgår som adgangskrav. Verifikationsprogrammet læser fem overordnede METHOD-filer, men i den valgte gren kræves hverken `full_panel_plan.json` eller `controller_claim.json`.

| Arkiv | Bytes | Git-blob SHA1 | Deklareret SHA256 |
|---|---:|---|---|
| `pilot_protocol_20261008/method_study_archives/case_000.tar.gz` | 528.777 | `45d95f79d78cbf785960d3fc41dbda8ee135c109` | `905f07f9f9446775120b5a2f1338999071ab187b40be5d77a25d5c7c26c4b245` |
| `pilot_protocol_20261008/method_study_archives/coordinator_evidence.tar.gz` | 79.878 | `c7439d7e7f25a33f277aed3c9c52e044130316d7` | `7602c6b870ad89be4f7198253bcc380c08a5f56b9dec3c926e5bd193edba012e` |

Det samlede komprimerede input er 608.655 bytes. Git-eksistens, blobidentitet og størrelser er kontrolleret nu. Arkivernes SHA256 og medlemmernes SHA256/bytes er **deklarationer fra det autentificerede originale manifest**; de er ikke genberegnet fra arkivkroppe i denne opgave. Genberegningen hører til restaureringen den 19. oktober, før forsvarlig udpakning. Manglende lokale scratch-filer er almindelig restaurering, ikke en ny videnskabelig fejl.

De 9 nødvendige medlemmer i koordinatorevidensen er:

| Medlem | Bytes |
|---|---:|
| `COMMITTED_PANEL.json` | 586 |
| `outcomes.json` | 103,755 |
| `summary.json` | 142,145 |
| `resource_receipt.json` | 27,873 |
| `rolling_cpu_ledger.json` | 429 |
| `closure_000.json` | 391 |
| `reservation_000.json` | 377 |
| `admission_000.json` | 5,427 |
| `f2d8446487e360965ff60dfeef99e5b29e39db6bb285523861fa4eb6c64c0f47.json` | 477 |

De første 8 placeres under `results/radio_pilot_method_study_20261008/`. Caseclaim placeres som `pilot_protocol_20261008/method_study_claims/f2d8446487e360965ff60dfeef99e5b29e39db6bb285523861fa4eb6c64c0f47.json`. Dets filnavn er SHA256 af den faste ASCII-caseidentitet; dets indholds-SHA256 er `4ad9acd960ad2b72dc1ce7db23c1707a195a9482c6d8190dad71c3d0158783f4`. Claim og admission skal bevares byteidentiske.

Casearkivet indeholder 22 originale medlemmer under `results/radio_pilot_method_study_20261008/case_000/`. Alle 22 skal restaureres, inklusive metadata, sandhed, hitliste, recovery, ressourcer, outcome, COMMITTED og artifactmanifest; den valgte verifikation genkontrollerer hele det originale 20-hash artifactmanifest. Den åbner seks gemte scorekort og én separat NPZ med geometriske hjælpearrays:

| NPZ-medlem | Bytes | Original deklareret SHA256 |
|---|---:|---|
| `geometry_arrays.npz` | 26,787 | `75aaca0c3f77d8911ab0400b56f24525bdb4df5497d13e1e31c19401e6362c81` |
| `scan_00_full_map.npz` | 66,441 | `6dcf7d87fac99f03cf6148911b79a69fe6b121bd9bd3485246cfed8c227141f4` |
| `scan_01_full_map.npz` | 74,603 | `76d4c443fab69a1b3b0c284f2efec5e5dba4444bbfc6ef9690da9fc0f3cc5fa5` |
| `scan_02_full_map.npz` | 68,223 | `b25c5c60176a0fcb2a2273ebf3e974f41c542907290bda3351c34fcb5d5d966f` |
| `scan_03_full_map.npz` | 75,813 | `48de5c704dbc15d874c4404e441d9aa2551b2fb8650a8b7e2e22dae0ad11f159` |
| `scan_04_full_map.npz` | 67,206 | `d99d14dd15959e09cf06a0ec923f5d5787c4fed0c4fb8b035b7671966f6fc761` |
| `scan_05_full_map.npz` | 74,075 | `6b537a307865084d8b8e57fe1842e682817c42e0414a9b46addbe2a2ff460dcf` |

Det historiske fuldpanelreview angiver for case000: seks kort, 20 artifacthashes, 32 ON-threshold-carriers og 32 overlevende carriers. Det er et allerede publiceret resultat og et sammenligningspunkt; der er ingen ny reproduktion eller genberegning bag dette inventar.

## De 21 admission-afhængigheder

Programmet hasher **samtlige** `master['paths']`, også filer hvis indhold den valgte casegren ikke ellers fortolker. Generator, detektor og hjælpekode skal derfor findes i restaureringssættet med oprindelige bytes; de bliver ikke importeret eller udført af verifikationsprogrammet. Hver fil nedenfor er fuldlæst som tekst til statisk provenienskontrol og matcher SHA256 fra den uændrede admission samt uforanderlig Git-SHA1/størrelse. Den maskinlæsbare manifestfil indeholder alle hashes og præcise oprindelige stier.

| Admissionnøgle | Repo-sti | Bytes |
|---|---|---:|
| `a_outcomes` | `pilot_protocol_20261008/validation_a_complete_outcomes.json` | 69,734 |
| `a_summary` | `pilot_protocol_20261008/validation_a_complete_summary.json` | 3,225 |
| `b_completion` | `results/radio_pilot_val_b_20261008/COMMITTED_PANEL.json` | 474 |
| `b_integrity_review` | `pilot_protocol_20261008/review/COMPLETE_VAL_B_OUTPUT_REVIEW.json` | 111,523 |
| `b_outcomes` | `results/radio_pilot_val_b_20261008/outcomes.json` | 75,611 |
| `b_resource_receipt` | `results/radio_pilot_val_b_20261008/resource_receipt.json` | 59,375 |
| `b_summary` | `results/radio_pilot_val_b_20261008/summary.json` | 3,097 |
| `contract` | `pilot_controls_20261008/control_contract.json` | 4,540 |
| `detector` | `pilot_engine_20261008/detector.py` | 22,819 |
| `dev_helpers` | `pilot_engine_20261008/run_dev.py` | 13,297 |
| `development_cases` | `pilot_controls_20261008/development_cases.json` | 11,067 |
| `generator` | `pilot_controls_20261008/generator.py` | 17,484 |
| `method_cases` | `pilot_method_study_20261008/method_cases.json` | 40,467 |
| `post_b_ledger` | `pilot_method_study_20261008/post_b_ledger.json` | 2,388 |
| `post_development_ledger` | `pilot_runtime_correction_20261008/post_development_ledger.json` | 1,188 |
| `runtime_cases` | `pilot_runtime_correction_20261008/development_runtime_cases.json` | 1,014 |
| `science_protocol` | `pilot_method_study_20261008/METHOD_STUDY_PROTOCOL.json` | 11,191 |
| `scope` | `pilot_method_study_20261008/METHOD_STUDY_SCOPE.md` | 6,058 |
| `summarizer` | `pilot_controls_20261008/summarize.py` | 4,884 |
| `validation_a_cases` | `pilot_controls_20261008/validation_a_cases.json` | 63,414 |
| `validation_b_cases` | `pilot_controls_20261008/validation_b_cases.json` | 63,414 |

Den oprindelige admission er 9.176 bytes, Git-blob `45fd47847039c99ac4095a7cabe04f38e87fe9fa`, SHA256 `62554e1a1328c7ab3b27d10a4a77c356ebfbe78aed8dc26545b39e5b3ca35011`. Verifikationsprogrammet er 26.084 bytes, Git-blob `1dcb92a599c192745da17b77fc478ed0577b1944`, SHA256 `5a502551614d8bb5943da550664d2cc88ba06a04bd6a0d52543a8041e82f0891`. I alt er 27 tekstkilders byteantal og Git-blob genberegnet i denne statiske kontrol; 21 af dem har admission-bundne SHA256.

## Stier og nye processer

Verifikationsprogrammet bestemmer den aktuelle projektrod som `Path(__file__).resolve().parents[2]`. Det skal derfor restaureres som `pilot_protocol_20261008/review/audit_retained_method.py`, ikke flyttes til en anden dybde. Resultatfilerne og claimfilen findes derefter fra deres faste relative placering under denne rod.

Den oprindelige admission bruger `/workspace/scratch/4763d9b286ba` som absolut projektrod. Under samme rod skal kommandoen køres uden rebaseringsflag. Hvis projektet ligger under en anden absolut rod, tilføjes eksplicit `--recorded-project-root /workspace/scratch/4763d9b286ba`. Programmet ommapper kun admitted prerequisite-stier under denne oprindelige rod til den aktuelle projektrod; alle bytes skal stadig matche deres oprindelige SHA256. Admission- og claimfiler redigeres ikke. Stier, som undslipper en af rødderne, afvises.

Output skal være en ny JSON-fil under den aktuelle rod. Programmet afviser overskrivning af eksisterende evidens. Den planlagte outputfil findes ikke i kildens Git-reviewtræ; dens lokale fravær skal kontrolleres igen umiddelbart før den ene kørsel den 19. oktober.

## Afhængigheder og ressourcegrænser

Statisk AST-gennemgang finder standardbibliotekerne `pathlib`, `argparse`, `hashlib`, `json`, `math` og ét lokalt `import numpy as np` i `verify_cases`. Ingen øvrig projektkode importeres. `Path.is_relative_to` kræver Python 3.9 eller nyere. Det gennemsete program fastlåser ikke en bestemt NumPy-version.

Dagens rent miljøinventar fra metadata viser Python 3.12.14, installeret NumPy-distribution 2.3.5 samt `/usr/bin/prlimit` og `/usr/bin/timeout`. NumPy er ikke importeret. Dette beviser ikke, at bibliotekerne kan indlæses, at NPZ-filer kan åbnes, eller at den friske proces den 19. oktober lykkes; det kan først afgøres af den planlagte afgrænsede kørsel.

Den bevarede kommando er dokumenteret til den 19. oktober og er **ikke kørt nu**:

```sh
prlimit --as=4294967296 --cpu=60 -- timeout 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python pilot_protocol_20261008/review/audit_retained_method.py --admission pilot_method_study_20261008/method_study_admission.json --case-id SETI_RADIO_PILOT_20261008_METHOD_STUDY:method_signal:000 --output pilot_protocol_20261008/review/METHOD_SAVED_CASE_000_REPRODUCTION.json
```

Grænserne er 4 GiB adresserum, 60 CPU-sekunder per proces og 120 sekunders timeout. BLAS/OpenMP/MKL/NumExpr sættes hver til én tråd. Hele processens CPU, vægtid og peak RSS skal registreres særskilt, og både succes og eventuel fejl skal bevares. Nutidige begrænsninger skal ikke forveksles med de historiske casechecks: oprindeligt 250 CPU-sekunder, 1.800 sekunders vægtid og 4 GiB RSS. Case000's historiske 73,064369 CPU-sekunder til fremstilling af resultatet bliver ikke genkørt; den nye kørsel kontrollerer gemte map/hit/veto/recovery-sammenhænge uden rå preprocessing eller nye numeriske detektorscores.

Denne klargøring er dækket af rodopgavens konservative 100 CPU-sekunders forberedelsesreservation. Her foretages ingen særskilt debitering eller refusion, og ingen historisk forberedelsesrest hævdes fuldt målt.

## Det, der fortsat skal gøres den 19. oktober

1. Restaurér det ovenstående byteidentiske sæt fra fastlåst Git og de to arkiver; kontroller arkivernes SHA256/bytes/blobidentitet og de udvalgte medlemmers SHA256/bytes før anvendelse.
2. Bevar oprindelig admission og claim; kontroller faktisk rod, programhash, alle 21 adgangskrav, NumPy/tooltilgængelighed og et friskt outputsted.
3. Kør præcis case000 én gang i en frisk, afgrænset proces. Registrér ressourceforbrug og luk succes eller fejl uden redraw eller genkørsel.
4. Medtag den faktiske receipt i slutrapporten den 20. oktober. Den gamle periodes afslutning den 9. oktober ændres ikke. Ingen automation er ændret af denne underopgave, og perioden forlænges ikke automatisk.

Der er ingen konstateret mangel i den fastlåste inputkilde. Det åbne spørgsmål er den faktiske restaurering og eksekvering i det fremtidige miljø; det er ikke løst af metadata eller det tidligere fuldpanelreview.
