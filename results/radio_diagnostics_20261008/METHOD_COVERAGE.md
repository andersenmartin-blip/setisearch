# Gemte METHOD-maksima og dækningsgrænser — 8. oktober 2026

De 64 allerede afsluttede METHOD-forsøg indeholder 128 aktive ON-scans. I 13 scans fordelt på 12 forsøg ligger det gemte globale maksimum under den oprindelige ON-grænse på 10. Derfor blev ingen ON-bærer udvalgt i disse scans. Det samlede resultat er fortsat ALL 52/64 og ANY 59/64; der er ingen yderligere tab gennem OFF-kontrollen i METHOD.

ALL kræver et sandhedslokaliseret overlevende hit i hvert aktivt ON-scan; ANY kræver mindst ét aktivt ON-scan med et sådant hit. Single-third-ON har ét aktivt scan per forsøg, all-three-ON har tre. Scan-tællinger og forsøgs-tællinger har forskellige nævnere.

Det nominelle idealniveau er generatorens støjfri boksprojektion. De observerede tal her er det **gemte globale maksimum af den robuste detektorstatistik over de søgte skabeloner** i hvert aktivt scan. Maksimum er udvalgt efter en søgning og er derfor ikke et ubetinget estimat af den indsprøjtede linjes amplitude, en sandhedslokaliseret statistik, målt SNR eller flux. Forholdet maksimum/ideal nedenfor er udelukkende en beskrivende sammenligning af disse to forskellige størrelser.

| Nominelt idealniveau | ALL/forsøg | ANY/forsøg | Overlevende aktive ON-scans | Scans under ON=10 | Gemt globalt maksimum, min / median / max | Maksimum/ideal, min / median / max |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 6/16 | 12/16 | 21/32 | 11/32 | 8.556 / 10.330 / 12.091 | 0.856 / 1.033 / 1.209 |
| 12 | 14/16 | 15/16 | 30/32 | 2/32 | 9.631 / 12.422 / 13.999 | 0.803 / 1.035 / 1.167 |
| 16 | 16/16 | 16/16 | 32/32 | 0/32 | 13.828 / 15.746 / 17.862 | 0.864 / 0.984 / 1.116 |
| 24 | 16/16 | 16/16 | 32/32 | 0/32 | 20.188 / 24.090 / 27.071 | 0.841 / 1.004 / 1.128 |

Tabene findes ved idealniveau 10 og 12 i dette konkrete panel. Niveaustrinnene 16 og 24 genfindes i alle deres aktive ON-scans, men 16/16 forsøg er ingen dokumentation for garanteret genfinding eller en generel detektionssandsynlighed. Tallene forklarer ikke, hvilken del af forskellen der skyldes støj, skabelonvalg eller behandling af data; de originale rapportprodukter indeholder ikke en sandhedslokaliseret statistik under ON-grænsen.

| Aktivitet | ALL/forsøg | ANY/forsøg | Overlevende aktive ON-scans | Scans under ON=10 |
|---|---:|---:|---:|---:|
| single_third_ON | 27/32 | 27/32 | 27/32 | 5/32 |
| all_three_ON | 25/32 | 32/32 | 88/96 | 8/96 |

De to aktivitetsgrupper er forskellige støjrealiseringer med forskellige eksponeringer; de er ikke parrede målinger. Der er én realisering per celle af idealniveau × drift × intrinsisk bredde × aktivitet. De fire frekvensplaceringer er balanceret i marginalerne, men ikke gentaget fuldt inden for hver celle. Grupper efter drift, bredde, placering og aktivitet findes med begge nævnere i maskinfilerne; de fastslår ingen kausal effekt. Scans fra samme forsøg og de 7.051 overlevende bærere er heller ikke uafhængige forsøg.

De 13 mistede aktive ON-scans:

| Forsøgsnummer | ON-scan | Idealniveau | Gemt globalt maksimum | Afstand under ON=10 | Drift (Hz/s) | Intrinsisk bredde (kanaler) | Aktivitet |
|---:|---|---:|---:|---:|---:|---:|---|
| 001 | epoch3_on | 10 | 9.523700 | 0.476300 | -4 | 1 | all_three_ON |
| 002 | epoch1_on | 10 | 9.530470 | 0.469530 | -4 | 3 | all_three_ON |
| 002 | epoch3_on | 10 | 9.736125 | 0.263875 | -4 | 3 | all_three_ON |
| 003 | epoch1_on | 10 | 8.566153 | 1.433847 | -1.25 | 3 | all_three_ON |
| 004 | epoch1_on | 10 | 8.555767 | 1.444233 | 1.25 | 3 | all_three_ON |
| 006 | epoch3_on | 10 | 9.272677 | 0.727323 | -1.25 | 1 | all_three_ON |
| 007 | epoch2_on | 10 | 8.591658 | 1.408342 | 1.25 | 1 | all_three_ON |
| 009 | epoch3_on | 10 | 9.326335 | 0.673665 | -1.25 | 1 | single_third_ON |
| 011 | epoch3_on | 10 | 8.986564 | 1.013436 | 1.25 | 3 | single_third_ON |
| 012 | epoch3_on | 10 | 9.492378 | 0.507622 | 4 | 3 | single_third_ON |
| 014 | epoch3_on | 10 | 9.212916 | 0.787084 | 1.25 | 1 | single_third_ON |
| 027 | epoch3_on | 12 | 9.630511 | 0.369489 | -1.25 | 3 | single_third_ON |
| 030 | epoch1_on | 12 | 9.956025 | 0.043975 | 4 | 3 | all_three_ON |

Alle 13 dispositioner er oprindeligt NO_ON_THRESHOLD_HIT. I netop dette panel stemmer globalt maksimum ≥10 overens med den gemte lokaliserede scan-genfinding i de øvrige 115 aktive ON-scans; dette er en kontrolleret egenskab ved disse resultater og ingen generel regel, der sidestiller globale og lokaliserede statistikker.

I en senere, særskilt godkendt plan er prioriteten at skille den støjfri idealprojektion, en på forhånd fastlagt statistik ved den sande bane og det maksimum, en søgning udvælger. Friske gentagne realiseringer omkring ON-grænsen bør dække bredde, drift, aktivitet og placering med fastlagte gentagelser. Det ville kunne undersøge dækningsvariation og skabelonmismatch uden at kalde et udvalgt maksimum en fluxkalibrering. Denne analyse ændrer ingen tærskel eller skabelon, og en senere ændring kræver ny separat kvalifikation.

Kildecommit: `13131757641c06d7bfcb10790a79811c750b1178`. De tre inputprodukter er kontrolleret mod de faste Git-blob-SHA1, SHA256 og byteantal, deres restaureringskvittering og den oprindelige rapportmanifest. CSV og JSON er sammenlignet felt for felt for alle 64 celler. Ingen kortarkiver blev åbnet, ingen signaler eller støj blev genereret, og ingen score blev beregnet på ny. A/B-status forbliver fejlet; METHOD er et eksplorativt metodestudie.

Maskinfiler: `method_active_ON_scores.csv` (128 scans), `method_case_coverage.csv` (64 forsøg), `method_coverage_groups.csv` (beskrivende grupper), `method_missed_active_ON_scans.csv` (13 scans) og `METHOD_COVERAGE.json` (definitioner, nævnere, proveniens og fulde præcisionsværdier). Medianen er den almindelige stikprøvemedian: det midterste tal eller gennemsnittet af de to midterste ved et lige antal; der anvendes ingen kvantiler eller interpolerede detektionskurver.
