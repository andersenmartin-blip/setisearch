# Næste metodeudvikling: konkrete forsøg, 8. oktober 2026

Den afsluttede undersøgelse giver et konkret valg til en senere plan: mål først, hvordan et hit fordeler sig over tid, og gem en på forhånd fastlagt bane-statistik. Undersøg derefter én RFI-familieprototype sammen med dens tab af nærliggende ON-signaler. Et nyt veto bør først vælges, når disse sammenligninger kan vise, hvad det fjerner og hvad det mister.

Dette er et gennemgået udviklingsforslag og en statisk klargøring. Ingen nye syntetiske data, detektorscores, metodeændringer eller kvalifikation er udført. A/B forbliver `FAIL_CLOSED`, og teleskoppiloten er ikke admitted. Den nuværende plan afsluttes stadig20.oktober uden automatisk forlængelse.

## Hvad der konkret foreslås

| Prioritet | Senere udviklingssammenligning | Afgrænset første design | Målepunkt |
|---|---|---|---|
| 1 | Tidsprofiler med samme fuld-scan idealprojektion og med samme amplitude pr. aktiv række | 24 arrayversioner i4 parrede støjblokke; første/sidste række, fuld linje og støj; bredde og drift krydses | Gem hele rækkeprofilen og skeln den observerede støtte fra ekstrapolation over hele scannet. |
| 2 | Idealprojektion, én fast sandbane-statistik og udvalgt søgemaksimum | 40 arrayversioner i8 parrede støjblokke, idealniveau0/8/10/12/16 | Gem statistikken også under tærsklen; mål grid-mismatch og tabstrin separat. |
| 3 | Én observerbar RFI-familieprototype mod baseline, samtidig med nær-OFF-signalbevarelse | 84 arrayversioner i6 parrede støjblokke; drift−4/0/+4, bredde1/3, offset0/+2/+8 | Opgør RFI-rester, bevarede ON-komponenter, tab og uafklarede sammenfald hver for sig. |

Det samlede forslag er148 arrayversioner i18 støjblokke. Versioner med fælles støj er parrede udviklingskontroller og må ikke tælles som148 uafhængige forløb. Antallet af baseline- og prototype-scorepasses er en særskilt omkostning. De nye kørslers faktiske tid og byteforbrug er ukendt; de148 versioner er derfor hverken en budgetteret jobbank eller en tilladelse til udførelse. En senere plan må først måle den afgrænsede baselineomkostning og indsnævre designet før udfald, hvis det ikke passer. Familieprototypen forudsætter brugbare tids-/baneoutputs og et særskilt budget.

Nuldrift er medtaget for at konfrontere den oprindelige nær-OFF-fejl direkte. En kort, ægte smalbåndsudsendelse og et kort artefakt med identiske observerede arrays er ikke identificerbare ved deres labels. Kort varighed eller én ON-forekomst er derfor ikke alene en afvisningsgrund. Ved sammenfaldende ON/OFF-komponenter kan den korrekte disposition være uafklaret; det må ikke bogføres som dokumenteret adskillelse.

De fulde kontrolsammenligninger, manglende artefakter, udækkede forhold og beslutninger før freeze står i [det videnskabelige design](SCIENTIFIC_DESIGN.md). Rå syntetisk power, rækkeprojektioner, faste bane-statistikker og separate OFF-oracles findes ikke i den nuværende evidenspakke. De fremstilles ikke nu.

## Hvad stærkere statistiske påstande koster

Under en hypotetisk model med uafhængige forløb og samme hændelsessandsynlighed inden for én klasse kræver en ensidig95% øvre grænse på10%,5% eller1% henholdsvis29,59 eller299 forløb med nul hændelser. Fire samtidige klassekrav kræver med Bonferroni42,86 eller437 pr. klasse:168,344 eller1748 i alt. Hændelsen skal være defineret pr. helt forløb efter hele kæden. Carriers og scans er ikke ekstra uafhængige forsøg.

Ved de afsluttede panelers målte jobgennemsnit ville allerede én klasses1%-eksempel svare til cirka25.262 CPU-sekunder, og fire samtidige klasser til cirka147.685. Det er retrospektive omkostningseksempler, som ikke forudsiger en ændret metodes tid og ikke inkluderer dens udvikling, kontroloutputs, figurer eller audits. Modellen antages ikke at gælde for de eksisterende heterogene celler eller teleskopdata; ingen sky-falskalarmrate er kalibreret.

Det taler for en senere plan med konkrete, beskrivende udviklingskontroller og en særskilt beslutning om frisk kvalifikation efter freeze. Små beståede paneler må ikke omdøbes til en procentpræcis himmel-fejlrate. [Beregninger](DESIGN_BOUNDS.md) og en [uafhængig90-cifret Decimal-kontrol](NUMERIC_DESIGN_REVIEW.md) dokumenterer minimumskrav og naboværdier.

## Den planlagte verifikation er klargjort

Den19.oktobers eneste gemte METHOD-case kræver54 restaurerede filer:21 admitted adgangskrav, original admission, verifier,22 case-medlemmer og9 koordinatormedlemmer. De deklarerede restaurerede bytes er1.896.541; de to arkiver er tilsammen608.655 komprimerede bytes. Ingen manglende inputs er fundet i den uforanderlige Git-kilde. Adgangskravene matcher de oprindelige SHA256, og arkivernes Git-blob/byte-metadata er kontrolleret.

Arkivkroppe og kort er ikke åbnet her; manifesternes arkiv-/medlemshashes er endnu ikke genberegnet fra deres bytes i denne klargøring. Den faktiske restaurering, bibliotekernes indlæsning og den friske proces venter til19.oktober. Inventaret er ikke en ny reproduktionskvittering eller bestået kvalifikation. [Præcist restaureringssæt](SAVED_VERIFICATION_PREFLIGHT.md) · [Maskinmanifest](READINESS_MANIFEST.json) · [Rodkontrol af bindings- og layoutaritmetik](ROOT_STATIC_REVIEW.json).

## Aktuel saldo og fortsættelse

Den nye konservative100-CPU-sekunders reservation til design, beregninger, statisk inventar og udgivelse efterlader6.212,705144981004 CPU-sekunder. Mindst2.000 bevares til rapport og reproduktion. De metrede beregningskomponenter debiteres ikke igen; setup, API, dokumentation og udgivelsesbogføring hævdes ikke fuldt målt. Tidligere reservationer og ukendt historisk forbrug ændres ikke. [Aktuel ledger](DESIGN_LEDGER.json) og [bevarede korrigerede forberedelsesfejl](PREPARATION_EVENTS.json) gør opgørelsen eksplicit.

Den9.oktober afsluttes den gamle26.september–9.oktober-periode ud fra det allerede gemte daterede udkast og seneste status. Den19.oktober køres én gemt case i en frisk proces; den20.oktober udgives slutrapporten. De afsluttede diagnostiske audits gentages ikke som dagligt fremskridt. Forslaget til148 versioner aktiverer ingen senere kampagne, seeds, regelændringer eller teleskopsøgning.

Primær kilde for dette beslutningsgrundlag er commit `a7b086156d55bbfe7678b960d313d03823cf630c`; [kildebindingslisten](SOURCE_REPORT_BINDINGS.json) og [historiske CPU-inputs](HISTORICAL_COST_INPUTS.json) identificerer de gennemsete rapporter og jobopgørelser.
