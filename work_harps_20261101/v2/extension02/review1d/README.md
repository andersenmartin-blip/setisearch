# Første gennemgang af 100 nye HARPS-eksponeringer

Alle **336 accepterede V2-hændelser** i den nye prøve er gennemgået i et komplet 1D-atlas: 42 sider med otte hændelser pr. side. Hændelserne findes i 93 af de 100 analyserede eksponeringer og på alle 16 stjerner. Alle 336 produktionsstatusser er fortsat **UNREVIEWED**. Gennemgangen tildeler ingen fysisk oprindelse fra 1D-formen.

**94 hændelser** ligger inden for ±0,03 Å barycentrisk af mindst ét tidligere accepteret hit fra samme stjerne. Der er 341 sådanne parforbindelser. Det er en positionssammenligning mellem udvalgte hits, ikke uafhængig validering eller fuld alle-epoke-kontrol. Et manglende match betyder ikke, at andre epoker mangler struktur på stedet. De gemte tidligere statusser i matchtabellen er kun kontekst fra den oprindelige 333-hændelsers tabel; efterfølgende råpixelopfølgninger ligger særskilt.

**22 hændelser** får det uændrede to-linje-nærhedsflag: 13 nær O I 5577,339 Å og ni nær 6300,304 Å i omtrentlige topocentriske luftkoordinater. 18 af de 22 har også et gammelt accepteret positionsmatch. Ingen af de nye accepterede hændelser ligger inden for det særskilte efterfølgende ±0,03 Å-vindue omkring O I 6363,776 Å. Dette er nærhedsflag, ikke bekræftet nattehimmelsemission eller frasortering.

## Næste evidens, hændelse for hændelse

[Alle opfølgningsruter](FOLLOWUP_ROUTES.csv) følger reglerne, som blev fastlagt før de nye hits blev læst. De er arbejdsruter, ikke en rangering af sandsynligheden for teknologi.

| Arbejdsrute | Hændelser | Nødvendig kontrol |
|---|---:|---|
| Ingen gammel accepteret positionspartner og intet O I-flag | 238 | Dækkende native-ordener, råpixelmorfologi og alle tilgængelige epoker |
| Gammel accepteret positionspartner, uden O I-flag | 76 | Sammenhold tidligere kontekst, og kontrollér den nye eksponering selvstændigt |
| O I-nærhedsflag | 22 | Samtidig skyfiber/kalibrering, flere iltlinjer og epokeadfærd |

Alle 336 paneler er visuelt inspiceret. De viser både brede blå/CH-nabolagsstrukturer, smalle eller asymmetriske kerner og mere jævne profiler. Nogle brede strukturer ligner hinanden på tværs af de accepterede epoker; dette atlas erstatter ikke den separate alle-epoke-metode. Mange spidse kerner er højere eller smallere end den gemte Gaussmodel, men 1D-formen alene afgør ikke, om signalet stammer fra detektoren, himlen, instrumentet eller kilden. Særligt dybe nabotrender er bevaret i figurerne og dokumenteret i [sidenoterne](VISUAL_PAGE_NOTES.json).

## Stjerneoversigt

| Stjerne | Analyserede epoker | Accepterede hændelser | Med gammel positionspartner | O I-to-linje-flag |
|---|---:|---:|---:|---:|
| HD103991 | 6 | 21 | 4 | 3 |
| HD106515A | 7 | 37 | 16 | 0 |
| HD109833 | 7 | 27 | 6 | 6 |
| HD112410 | 7 | 6 | 0 | 0 |
| HD114386 | 7 | 21 | 7 | 2 |
| HD114783 | 7 | 27 | 20 | 0 |
| HD118006 | 7 | 10 | 0 | 0 |
| HD120411 | 7 | 79 | 8 | 10 |
| HD122640 | 3 | 12 | 6 | 0 |
| HD124553 | 7 | 9 | 0 | 1 |
| HD126053 | 6 | 10 | 0 | 0 |
| HD126093 | 6 | 25 | 23 | 0 |
| HD128582 | 6 | 16 | 0 | 0 |
| HD135204 | 5 | 11 | 4 | 0 |
| HD1397 | 6 | 13 | 0 | 0 |
| HD141937 | 6 | 12 | 0 | 0 |

Hændelsesantal er ikke antal uafhængige kilder eller eksponeringer. HD120411 bidrager eksempelvis med 79 accepterede hændelser i syv eksponeringer. [Eksponeringstællinger](EXPOSURE_COUNTS.csv), [faste 100 Å-bølgelængdeintervaller](WAVELENGTH_COUNTS.csv) og [samtlige 341 positionsforbindelser](OLD_MATCHES.csv) gør tællingerne efterprøvbare.

## Metode og kontrol

[Planen](PLAN.json) blev frosset, før nye hitlister eller fluxværdier blev inspiceret. Atlaset bruger de gemte 101 samples omkring hvert seed, den gemte lineære baggrund og sidebåndets MAD-skala. Den orange kurve er den gemte faste Gaussmodel; der er ingen ny tilpasning af centrum, bredde eller tærskel. Visningen dækker ±0,5 Å. Det lyse felt markerer de centrale ±12 samples, ikke et statistisk konfidensinterval. Scores og A/MAD er ikke kalibreret statistisk signifikans.

Topocentriske koordinater bruger λ_top ≈ λ_bary/(1+BERV/c). Omregningen er en klassisk tilnærmelse og bruges kun til de beskrevne nærhedsflag. Ingen stjerne-RV antages, og ingen ny detektor eller oprindelsesklassifikation indføres.

Alle 336 udtræk har komplet sampleområde og positiv, endelig MAD-skala; ingen hændelser eller paneler blev udeladt. [Inputkontrollen](INPUT_CHECKS.json) verificerer filhash og metadata for alle 93 eksponeringer med hits samt uændrede hit- og dispositionstabeller. [Den numeriske kontrol](NUMERICAL_AUDIT.json) genberegner første, midterste og sidste kandidat direkte fra FITS med skalararitmetik og kontrollerer gamle matches og begge adskilte O I-flag. Den bestod. Dette er samme agents kontrol i en frisk proces, ikke uafhængig menneskelig validering.

[Hændelsesindekset](REVIEW_INDEX.csv) linker hver hændelse til dens panel og gemte NPZ-profil. [Den visuelle kontrol](VISUAL_REVIEW.json) registrerer alle 336 gennemgåede paneler. [Atlasindekset](ATLAS_INDEX.md) giver adgang til alle 42 sider. `build_atlas.py`, `audit_atlas.py` og `finalize_report.py` kan genskabe beregninger og rapport i en separat arbejdskopi med projektets Python-afhængigheder; de manuelle sidenoter indgår som kilde til rapporten. De frosne produktionsresultater og tidligere tabeller ændres ikke.
