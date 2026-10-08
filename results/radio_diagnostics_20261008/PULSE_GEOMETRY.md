# Geometri for gemte enkeltintegrationspulser

De 12 oprindelige B-transienter gav 8,114 overlevende ON-responser. 428 af dem opfyldte den oprindelige sandhedslokalisering ved begge ender af hele ON-scannet (5.3%). Ved den kendte indsprøjtede integrations midtpunkt ligger 8,103 gemte vinderbaner inden for den samme breddeafhængige geometriske tolerance; med en fast tolerance på 18,5 kanalbredder er tallet 8,103.

Sammenligningen viser, hvor de allerede gemte rette vinderbaner passerer i forhold til den kendte puls. Den måler ikke pulsens tidsprofil eller bidrag til scoren: råeffekt, standardiserede residualer og scorebidrag pr. række er ikke gemt. Et punktmatch er en beskrivende geometri og erstatter ikke den oprindelige lokalisering over hele ON-scannet.

Pulsen blev indsprøjtet i første eller sidste integration; derfor er dens midtpunkt også en af de to tidskoordinater i den oprindelige lokalisering. En bane kan ligge tæt på pulsen ved dette tidspunkt og afvige ved den anden ende. Mange nabocarrieres responser er korrelerede og udgør ikke selvstændige hændelser.

| B-case | ON | Pulsrække | Gemte overlevere | Hele ON lokaliseret | Ved pulstid, breddeafhængig tolerance | Absolut fejl ved pulstid: min / median / maks, kanalbredder |
|---|---|---:|---:|---:|---:|---|
| 000 | epoch1_on | 0 | 20 | 19 | 19 | 2.2499 / 9.7500 / 19.2500 |
| 001 | epoch1_on | 0 | 19 | 19 | 19 | 2.2498 / 8.7500 / 18.2500 |
| 002 | epoch1_on | 15 | 1042 | 74 | 1042 | 0.0051 / 2.7944 / 16.7500 |
| 003 | epoch1_on | 15 | 1043 | 71 | 1043 | 0.0032 / 2.3363 / 17.7500 |
| 004 | epoch2_on | 0 | 19 | 19 | 19 | 3.0265 / 8.7500 / 18.3741 |
| 005 | epoch2_on | 0 | 20 | 18 | 18 | 1.6861 / 9.4840 / 18.7500 |
| 006 | epoch2_on | 15 | 123 | 17 | 120 | 0.0423 / 3.4792 / 19.8117 |
| 007 | epoch2_on | 15 | 122 | 21 | 120 | 0.0620 / 2.9245 / 18.9660 |
| 008 | epoch3_on | 0 | 1037 | 24 | 1036 | 0.0075 / 3.0881 / 18.5431 |
| 009 | epoch3_on | 0 | 1037 | 19 | 1037 | 0.0009 / 2.2802 / 18.3552 |
| 010 | epoch3_on | 15 | 1815 | 64 | 1815 | 0.0019 / 3.0085 / 18.2500 |
| 011 | epoch3_on | 15 | 1817 | 63 | 1815 | 0.0088 / 2.4789 / 19.1687 |

Fortegnet i CSV-tabellen er en fysisk frekvensforskel divideret med den positive kanalbredde. Det er ikke den native kanalindeksforskel, eftersom frekvensaksen er faldende. Bredden 1 er koblet til indsprøjtet drift -4 Hz/s, og bredden 3 til +4 Hz/s; disse data giver ikke en selvstændig effektmåling af bredde, drift, placering eller rækkenummer.

Inddata er kontrolleret mod de oprindelige case-manifester og COMMITTED-markører samt hashbindingerne i DIAGNOSTIC_EVIDENCE.json. Ingen effektdata er genskabt eller scorer beregnet. A og B forbliver fejlede; denne analyse er ikke en ny kvalifikation.
