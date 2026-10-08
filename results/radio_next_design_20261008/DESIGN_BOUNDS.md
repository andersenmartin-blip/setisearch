# Forsøgsantal og ressourcer — betinget regneeksempel, 8. oktober 2026

Tallene nedenfor er planlægningsmatematik. De eksisterende heterogene forsøg eller himmeldata antages ikke at opfylde modellen. Ingen nye data genereres, og der er ingen ny kvalifikation.

For n uafhængige forløb med samme hændelsessandsynlighed p er P(nul)=(1−p)^n. Efter nul hændelser er den ensidige modelgrænse 1−α^(1/n). Det mindste n til en øvre grænse p₀ er ceil(log α / log(1−p₀)). Hændelsen skal på forhånd defineres pr. helt forløb efter hele analysen; carriers og scans er ikke ekstra uafhængige forløb.

| Antal særskilte klasser | Ønsket øvre hændelsesgrænse | Nul-hændelsesforløb pr. klasse | Forløb i alt | Illustrativ CPU, normal / stress×2 |
|---:|---:|---:|---:|---:|
| 1 | 10% | 29 | 29 | 2,450.1 / 4,900.3 s |
| 1 | 5% | 59 | 59 | 4,984.8 / 9,969.6 s |
| 1 | 1% | 299 | 299 | 25,261.9 / 50,523.8 s |
| 4 | 10% | 42 | 168 | 14,194.0 / 28,387.9 s |
| 4 | 5% | 86 | 344 | 29,063.8 / 58,127.7 s |
| 4 | 1% | 437 | 1748 | 147,684.9 / 295,369.8 s |

Én klasse bruger α=0,05. Fire klasser bruger α=0,0125 pr. klasse, så Bonferroni giver mindst95% samlet modeldækning. Det kræver ikke uafhængighed mellem klasser, men den erklærede Bernoulli-model inden for hver klasse. De fire eksisterende støjlove pooles ikke. Regnestykket er ikke en sky-falskalarmkalibrering.

Hvis alle signalforløb genfindes, bliver den tilsvarende nedre modelgrænse α^(1/n). 29/29 succeser understøtter mindst90%, og59/59 mindst95%, ved ensidig95% under samme hypotetiske model. Det ændrer ingen af de gamle kvalifikationskrav eller resultater.

B142 brugte 11676.036546 hele CPU-sekunder og METHOD64 5407.226987. Panelgennemsnittene er 82.225609479 og 84.487921672 CPU-sekunder pr. forløb. Tabellen bruger det største gennemsnit samt en særskilt stressfaktor2; ingen af dem er en per-case-cap eller en prognose for en ændret metode. Udvikling, figurer, arkiver, audits og ukendt setup kommer oveni.

Efter den nye100-CPU-reservation resterer 6212.705144981004 CPU-sekunder. Mindst2000 bevares til rapport og reproduktion. De resterende 4212.705144981004 ville rent aritmetisk svare til 49 gennemsnitsforløb eller 24 stressforløb, før øvrig overhead. Det er et kontrafaktisk budgeteksempel; nye forsøg er ikke admitted i denne periode.

En senere plan bør først demonstrere den konkrete forbedring med små udviklingskontroller, måle den nye omkostning og derefter beslutte, hvilken beskrivende eller inferentiel påstand budgettet kan bære. Et lille bestået panel kan ikke omdøbes til en procentpræcis himmel-fejlrate.

[Maskintal](DESIGN_BOUNDS.json) · [Primære CPU-inputs](HISTORICAL_COST_INPUTS.json) · [Scope](DESIGN_SCOPE.json).
