# SETI: svage sandhedsspor rangeret og morfologien gennemgået — 14. oktober 2026

Den kendte komplette fire-bin-bane er nu rangeret i alle **1.512** svage,
betingede indsprøjtninger fra den eksakte native-sporfamilie. Analysen
genbruger de 54 gemte scorearrays; ingen søgning eller teleskopfil er åbnet
igen. En separat implementering efterregnede **21.189** tabel- og
aggregatværdier uden afvigelse. **Ingen kvalificeret SETI-detektion eller
kalibreret falsk-alarm-sandsynlighed er etableret.**

## Rangresultat

Hver test har præcis én opnåelig komplet sandhedsbane. Ved det svage niveau
er den globale maksimumsbane komplet i 1.036/1.512 tilfælde og delvis i 476.
Den komplette bane ligger således:

| Bevarede kandidater | Komplet sandhedsbane bevaret | Andel |
|---:|---:|---:|
| 1 | 1.036/1.512 | 68,52 % |
| 2 | 1.255/1.512 | 83,00 % |
| 3 | 1.340/1.512 | 88,62 % |
| 5 | 1.400/1.512 | 92,59 % |
| 10 | 1.455/1.512 | 96,23 % |
| 20 | 1.491/1.512 | 98,61 % |
| 50 | 1.507/1.512 | 99,67 % |
| 100 | 1.511/1.512 | 99,93 % |

De **43** tilfælde, hvor det gamle 405-gitter havde en fuld maksimumsvinder,
men den større eksakte familie fik en delvis vinder, er nu konkret forklaret:
den komplette bane har rang 2 i 27 tilfælde, rang 3 i 15 og rang 4 i ét.
Alle 43 ville derfor være bevaret med top 5. Vinderens scorefordel over den
komplette bane har median **0,243159** og spænder **0,010130–1,299931**.
Vinderne rammer 3/2/1/0 aktive bins i henholdsvis 22/11/3/7 tilfælde.

På hele den svage bank er top 5 ikke komplet: 112 sandhedsbaner ligger lavere,
og den værste har rang 165. En enkel udviklingsregel er derfor fastlagt som
**bevar de fem højest scorende, tilladte unikke (vindue, fire-bin-bane)-hypoteser**.
Reglen blev valgt efter at disse udfald var eksponeret. Den er
`DEVELOPMENT_ONLY`, omskriver ingen tidligere fejl til bestået og skal
fastfryses før vurdering på friske identiteter.

## Gemte vandfald

De 14 allerede fremstillede og hashbundne residualvandfald er gennemgået
deskriptivt. I de ni kildescanninger ses valget som kompakte fire-række-
episoder; ingen figur viser en utvetydig varm, smal ryg gennem alle 16 rækker.
For det stærkeste spor flytter det lokale eksakte maksimum i samtlige fem
andre scanninger til et andet fire-række-vindue og en anden native-bane.
Den faste oprindelige bane scorer her **−0,5924 til 2,3061**, mens de lokalt
genmaksimerede baner scorer **2,4822 til 3,4091**. De lokale maksimummer følger
visuelt isolerede varme cellekombinationer i blandede residualfelter; de er
ikke genfinding af den faste kildebane.

Morfologien er en kvalitativ kontrol efter udvælgelse. Den indfører ingen ny
scoregrænse, sandsynlighedsmodel eller fysisk oprindelsesklassifikation og kan
ikke bruges som fraværsbevis i andre scanninger.

## Ressourcer og bevarede gates

Aktiviteten var konservativt afgrænset til 120 CPU-s for analyse og separat
QA. De målte processer brugte **0,73 + 2,02 CPU-s**, højeste RSS var cirka
61 MB, og reservationen tilbageføres ikke. Der blev foretaget **0 nye
teleskopforespørgsler, 0 nye teleskopbytes og 0 DKK**.

Original A/B forbliver `FAIL_CLOSED`; beskyttede 2016-data og lukket
2019-rute er uændrede. Resultatet kommer fra det samme eksponerede besøg den
28. april 2017. Slutcheckpointet gennemføres fortsat først 20. oktober 2026.

[Frosset scope](analysis/weak_truth_rank_20261014/SCOPE.json) ·
[samlet resultat](analysis/weak_truth_rank_20261014/results/SUMMARY.json) ·
[alle 1.512 rangeringer](analysis/weak_truth_rank_20261014/results/TRIAL_RANKS.csv) ·
[uafhængig QA](analysis/weak_truth_rank_20261014/results/QA_RECEIPT.json) ·
[morfologigennemgang](analysis/weak_truth_rank_20261014/MORPHOLOGY_REVIEW.json) ·
[reproduktion](analysis/weak_truth_rank_20261014/README.md)
