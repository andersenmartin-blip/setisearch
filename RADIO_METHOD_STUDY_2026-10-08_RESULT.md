# Metodeundersøgelsen er gennemført — 8. oktober 2026

Alle 64 friske syntetiske forsøg er afsluttet én gang med uændret detektor, generator og tærskler. Den uafhængige gennemgang har godkendt 384 gemte kort, 1280 artefakthashes og 21153 OFF-sammenligninger. Ingen nye himmelspektrer er åbnet. A og B forbliver fejlet; undersøgelsen kan ikke godkende teleskoppiloten.

| Indsprøjtet idealniveau | Genfund i alle aktive ON | Genfund i mindst ét aktivt ON |
|---|---:|---:|
|10|6/16|12/16|
|12|14/16|15/16|
|16|16/16|16/16|
|24|16/16|16/16|
|Samlet|52/64|59/64|

Idealniveauet er generatorens støjfri box-projektion i den erklærede Gamma16-model, ikke målt detektor-SNR eller flux. Hver præcis kombination af niveau, drift, bredde og aktivitet har én realization og én balanceret frekvensplacering. Tallene beskriver disse forsøg; de giver ikke en kalibreret genfindingschance, sikker følsomhedsgrænse eller falsk alarm-rate for himmeldata.

Alle 12 forsøg uden fuldt genfund mistede mindst ét aktivt scan allerede under ON-tærsklen 10: 13 af 128 aktive scans havde ingen ON-carrier over tærsklen. Der blev ikke mistet lokaliserede genfund ved OFF-kontrollen i denne signalbank. Niveau 16/24 gav fuldt genfund i alle observerede celler, men det etablerer ingen universel grænse.

Tredje ON alene gav 27/32 fulde genfund. Alle tre ON gav 25/32 fulde genfund og 32/32 med mindst ét genfund. Første, andet og tredje ON har forskellige eksponeringstal i designet, og aktiviteterne har uafhængige støjtræk; sammenligningen viser ikke en kausal sidste-besøgsbias. Båndkanterne gav 14/16 hver og de to indre placeringer 12/16 hver; der ses ingen kantmangel i disse celler.

B's afsluttede 142 forsøg bidrager med de øvrige metodefund:2/24 RFI-forløb lækker i alt 14 ikke-truth-lokaliserede carriers, selv om RFI-hovedsporet afvises; 12/12 single-row-transienter overlever; 11/12 nær-OFF-signaler genfindes initialt og alle 12 mister deres endelige genfund. Støjbanken har 0/32 forløb med kandidat. B fejler fortsat kravene til tredje ON alene, bredde 3 og nul RFI-overlevere. Ingen af disse tal kalibrerer en sky-falsk-alarm-rate.

Undersøgelsen belastes med 5407,226987 hele CPU-sekunder under allokeringen 6000. Der resterer 6612,705145 i periodens regnskab efter tidligere omkostninger og den uændrede 1200-sekunders forberedelsesreservation. Rapportens rendering brugte 5,800888 hele child-CPU-sekunder og 163999744 bytes maksimal RSS, som en komponent af den eksisterende reservation. Ingen reservation er tilbagebetalt; ukendte historiske målinger er fortsat markeret som ukendte.

Den godkendte plan fortsætter til 20. oktober: konkret analyse af de gemte fejlmekanismer og afgrænsning af konklusionerne; særskilt gammel periodeafslutning 9. oktober; én afgrænset verifikation af et gemt resultat i en frisk proces 19. oktober; slutrapport 20. oktober. Reproduktionen kontrollerer gemte kort til hits/veto/genfund og gentager ikke rå preprocessing eller scores. Ingen anden rettelse, ny kvalifikationsbank, gentagelse af eksponerede signalforsøg eller automatisk forlængelse.

[Samlet rapport med seks figurer og fulde tabeller](results/radio_pilot_method_report_20261008/METHOD_STUDY_REPORT.md) · [64-cell CSV](results/radio_pilot_method_report_20261008/method_cells.csv) · [Uafhængig gennemgang](pilot_protocol_20261008/review/COMPLETE_METHOD_STUDY_OUTPUT_REVIEW.md) · [Faktisk budget](pilot_method_study_20261008/post_method_ledger.json) · [Gemte resultaters reproduktion](pilot_protocol_20261008/review/METHOD_SAVED_RESULT_REPRODUCTION.md).
