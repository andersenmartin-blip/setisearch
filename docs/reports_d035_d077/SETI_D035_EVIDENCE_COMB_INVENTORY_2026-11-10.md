# D035: nye COMB-kontroller og samlet evidens

10. november 2026. **14 laserfrekvenskam-optagelser er nu kontrolleret via deres fulde instrumentoplysninger. Otte er udvalgt som mulige nye kontroller for 0061 og 0063.** Der er endnu ikke hentet billeddata fra dem eller målt deres lokale linjer. De tre oprindelige strukturers fysiske oprindelse er fortsat uafklaret; kvalificerede laserfund er nul.

## Nyt resultat: en anden kalibreringskilde

De allerede fastlagte D031-vinduer indeholder 182 kalibreringsposter. Heraf opfylder 14 katalogbetingelserne for COMB i HARPS-tilstand: seks omkring 0061, otte omkring 0063 og ingen omkring 0071. Alle 14 er nu kontrolleret med fulde headers, inklusive nøjagtigt ARCFILE, dato, eksponering, instrumenttilstand, template, detektoridentitet, udlæsningsindstillinger og chipgeometri.

Begge fiberselektorer er COMB. Udlæsning og binning matcher de respektive oprindelige science-oplysninger; begge CCD-udvidelser har 2148 × 4096 pixels. Det er adgangsbetingelser for en fremtidig kontrol, ikke bevis for brugbare, umættede linjer ved den relevante bølgelængde.

| Struktur | COMB-poster / komplette headers | Udvalgte optagelser | Primær før originalens midtpunkt | Primær efter midtpunktet |
|---|---:|---:|---:|---:|
| D002-0061 | 6 / 6 | 4 | −4,66673 timer | +18,63768 timer |
| D002-0063 | 8 / 8 | 4 | −4,83594 timer | +19,86512 timer |
| D002-0071 | 0 / 0 | 0 | Ingen post i vinduet | Ingen post i vinduet |

For hvert martstilfælde vælges nærmeste kvalificerede optagelse før og efter science-midtpunktet samt nærmeste gentagelse på samme side inden for 120 sekunder. Dermed fås otte forskellige ARCFILE-identiteter. Gentagelserne er cirka 70 sekunder fra deres primære optagelse. De deler instrument- og kalibreringssystematik og er ikke otte statistisk uafhængige nulprøver. Alle 14 poster, også de seks ikke udvalgte, er bevaret i `ALL_COMB_HEADERS14.csv`.

Én af de første 14 headerforespørgsler gav HTTP 503. Den oprindelige ufuldstændige liste blev bevaret, og udvalget for 0061 blev holdt tilbage. Ét særskilt, på forhånd afgrænset genforsøg lykkedes. Den samlede historik er 15 forespørgsler, 14 succeser og én bevaret 503-fejl. Ingen regel, tidsgrænse eller fysisk kvalitetsbetingelse blev lempet.

## Hvad den eksisterende evidens viser

| Evidens fra D024–D034 | 0061 | 0063 | 0071 |
|---|---|---|---|
| Primær rå r3-bredde | 1,42379 pixels | 1,18030 pixels | 1,69882 pixels |
| Historisk native DRS A-bredde, separat udtræk | 1,88774 pixels | 1,46311 pixels | 1,69256 pixels |
| Fuld lampemodelscore over tre kalibreringer og seks baggrunde | 0,49298–0,65492 | 0,45105–0,55532 | 0,38079–0,49939 |
| Svageste samme-lampelinje-kontrol | 0,08807 | 0,07569 | 0,22797 |
| Største ændring ved D034-referenceudvalg | +0,05197 | +0,00348 | +0,07249 |
| Andre stjerners observationer i D024/D025 | 4; ingen præcis før-kontrol | 9; ingen præcis før-kontrol | Ikke del af denne kontrolgruppe |
| Oprindelig D016-korrespondance | Kvalitetsfejl bevaret | Understøttet i den metode | Understøttet i den metode |

Tabellen sammenfatter eksisterende målinger. Den indeholder ingen ny fitberegning eller flere science-observationer. Scoreintervallerne er beskrivende, uvejede residualforhold og kan ikke sammenlignes som fysiske sandsynligheder. Et mindre referenceudvalg kan kun bevare eller øge en minimumsscore. De svage lampetilfælde og alle tidligere udefinerede eller begrænsede målinger består.

0061s gamle r6-korrelation på 0,780656 ligger fortsat under den oprindelige 0,8-regel. Senere geometri- og baggrundskontroller ophæver den ikke. 0063s centrale og off-trace-struktur er fortsat ikke kausalt forbundet. De tre fænomener på HD43629 behandles hver for sig med egne bølgelængder, ordener og observationer; en fælles årsag er ikke etableret.

## Litteraturens betydning for næste test

[Milaković og Jethwa (2024)](https://arxiv.org/html/2311.05240v2) offentliggør effektive 1D-profiler udledt af en COMB-kalibrering fra 7. december 2018, nominelt 500–690 nm. [Zhao m.fl. (2021)](https://arxiv.org/abs/2011.03391) undersøger profilændringer med detektorposition og intensitet med COMB-lys i begge fibre.

Vores nærmeste native observatorie-luftprøver er 655,057 nm, 482,701 nm og 573,029 nm. 0063 ligger uden for den førstnævnte models nominelle område. Dette er en grov dækningskontrol, ikke en afprøvning af lokale profiltabeller. Den publicerede models datatidspunkt ligger henholdsvis cirka 819, 823 og 1007 dage før vores science-midtpunter. Ingen tids-, koordinat-, belysnings- eller udtræksoverførsel er valideret her.

Vores slutning er derfor: en publiceret, udtrukket 1D-profil må ikke bruges som en færdig kalibrering af vores rå r3-udtræk eller 2D-masker. **Om de nye 2021-COMB-optagelser faktisk har brugbart signal ved 482,7 nm skal måles direkte.** Et snit i en anden undersøgelses modeldækning er ikke bevis for fysisk fravær i disse optagelser. Ingen publiceret modelarray er hentet eller fit til vores strukturer i D035. Mislykket adgang til Zenodo/CDS-formatmetadata er bevaret særskilt.

## Kontrol og næste afgrænsede trin

Den samlede evidensoversigt har 24 rækker og 87 kildehenførte oplysninger. En separat parser læser de originale headertekster med en anden strengfortolkning og Decimal-aritmetik. Kontrollen omfatter 10.692 tildelte headerfelter, alle 14 klassifikationer, hele 182-posters medlemskab, de otte valg og alle 87 oplysninger. Tiderne reproduceres præcist; største forskel i den separate bølgelængdeberegning er 1,14 × 10⁻¹³ nm. Det er kontrol i samme assistentforløb, ikke ekstern fagfællebedømmelse eller en ny fysisk responsmåling.

Alle 46.051 tidligere felter i 37- og 141-rækkers tabeller er bevaret nøjagtigt; syv D035-felter er tilføjet. Den endelige oversigtsfigur er direkte gennemset. En manglende softwareafhængighed før første forespørgsel blev løst med en kontrolleret headerparser; den første kode og nul-adgangsfejlen er bevaret. Det ændrede ingen videnskabelig udvælgelsesregel.

**Næste trin er D036: kontrollér lokal COMB-dækning, signal og mætning i de otte valgte optagelser, før en ny responsmodel bygges eller sammenlignes med originalerne.** Alle vinduer, geometri, adgangs- og retentionsregler skal fastlægges før pixeldata. 0071 kræver et særskilt fastlagt interval, hvis der skal søges ud over det bevarede 48-timersvindue. Denne næste målemetode er endnu ikke fastlagt eller udført.

`EVIDENCE_MATRIX24.csv`, `QUANTITATIVE_FACTS.csv`, `EXTERNAL_MODEL_COVERAGE3.csv` og `SELECTED_COMB_EXPOSURES8.csv` giver de præcise sammenhænge og filidentiteter. `METADATA_AND_SYNTHESIS_AUDIT.json` dokumenterer kontrollen. Figuren `D035_CONTROL_SELECTION.png` viser alle poster, tidsvalg og den grove eksterne dækningskontrol.

Ingen nye teleskopprodukter eller teleskoppixels er hentet. Budget 0 kr.; ingen eksterne kontakter. Den oprindelige råkø forbliver lukket med 139 fulde og to delvise tilfælde. Old90 og Rubin er stoppet, offentlig upload er udskudt efter gældende projektstatus, og ingen baggrundsberegning kører.
