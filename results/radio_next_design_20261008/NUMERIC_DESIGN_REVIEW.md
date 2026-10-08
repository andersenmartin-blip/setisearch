# Betingede stikprøvekrav til en senere SETI-plan

Kontrolleret 8. oktober 2026. Dette er aritmetik til planlægning; ingen nye forsøg er startet, og ingen kvalifikationspaneler eller seeds er oprettet.

Ved **nul uønskede hændelser** er den eksakte ensidige øvre grænse $p_U=1-\alpha^{1/n}$. Minimum er det første heltal $n$, hvor $(1-p_\mathrm{mål})^n\leq\alpha$. Beregningen søger over heltal og kontrollerer begge naboværdier med 90-cifret Decimal-aritmetik. Ingen flydende logaritme er brugt.

| Ønsket øvre grænse | Én klasse, 95 % | Fire klasser, samlet mindst 95 %, pr. klasse | Fire klasser, samlet antal |
|---|---:|---:|---:|
| 10 % | 29 | 42 | 168 |
| 5 % | 59 | 86 | 344 |
| 1 % | 299 | 437 | 1748 |

Fireklassetilfældet bruger Bonferroni med $\alpha=0,05/4=0,0125$ pr. klasse. Det kræver ikke indbyrdes uafhængighed mellem klasserne, men hver enkelt klasses interval skal være gyldigt. Minimumsbeviserne $n-1$ og $n$ er gemt fuldt i JSON-filen.

Ved **udelukkende succeser** er den ensidige nedre grænse $p_L=\alpha^{1/n}$. En nedre grænse på 90 % kræver 29 succeser i én klasse eller 42 pr. klasse ved fire samtidige klassekrav; 95 % kræver henholdsvis 59 og 86. Det er det samme minimumsbevis med hændelsen omvendt.

**Forudsætningerne er hypotetiske:** Uafhængige kadencer, ens og uændret hændelsessandsynlighed inden for hver klasse samt klassifikation og succeskriterium fastlagt før observationerne. De tidligere heterogene celler med én realisering og tusindvis af korrelerede carriers kan ikke tælles som sådanne forsøg. Støjkontroller med syntetiske love fastlægger heller ikke falskalarmraten på teleskopdata.

Gennemsnittene for de afsluttede panelers målte jobs, inklusive børn og koordinering, er B142: **82,225609478873… CPU-s pr. kadence** og METHOD64: **84,487921671875 CPU-s**. De betyder ikke, at al historisk forberedelse, arkivering, review eller offentliggørelse er fuldt målt. Grundlaget fremgår af [HISTORICAL_COST_INPUTS.json](HISTORICAL_COST_INPUTS.json). Tabellen bruger det største jobgennemsnit; en ekstra kolonne viser blot to gange dette gennemsnit.

| Krav | Kadencer i alt | Historisk gennemsnit, CPU-s | To gange gennemsnittet, CPU-s |
|---|---:|---:|---:|
| Én klasse, ≤10 % | 29 | 2450,150 | 4900,299 |
| Én klasse, ≤5 % | 59 | 4984,787 | 9969,575 |
| Én klasse, ≤1 % | 299 | 25261,889 | 50523,777 |
| Fire samtidige klasser, ≤10 % | 168 | 14193,971 | 28387,942 |
| Fire samtidige klasser, ≤5 % | 344 | 29063,845 | 58127,690 |
| Fire samtidige klasser, ≤1 % | 1748 | 147684,887 | 295369,774 |

Tallene er **hverken kørselstidslofter, prognoser eller adgang til at starte tests**. En ændret metode, dens kontrolforsøg, figurer, uafhængige audits, lagring, initialisering og offentliggørelse er ikke medregnet. Historiske gennemsnit beviser derfor ikke, at en ny udførelse kan rummes.

Efter den nye designreservation på 100 CPU-s er restsaldoen **6.212,705144981004 CPU-s**. Med mindst 2.000 CPU-s afsat til senere reproduktion og slutrapport er den aritmetiske forskel **4.212,705144981004 CPU-s**. Det svarer højst til 49 historiske gennemsnitskadencer eller 24 ved dobbeltgennemsnittet, før øvrige udgifter; det er ingen testbevilling. Denne komponents faktisk målte CPU er indeholdt i reservationen og trækkes ikke fra igen.

Allerede én klasses 5 %-krav overstiger den aritmetiske forskel ved det historiske gennemsnit; 10 %-kravet overstiger den ved dobbeltgennemsnittet. Et 1 %-krav kræver mindst 299 ideelt uafhængige kadencer i én klasse eller 1.748 i fire samtidige klasser. Den konkrete næste plan bør derfor formulere afgrænsede, beskrivende kontroller og dokumentere metodefejl, frem for at love procentniveau for falskalarmraten på himlen. Den nuværende metode er fortsat ikke kvalificeret.
