# Opfølgning på alle 333 oprindelige V2 profiltræf

De 107 fund, der tidligere enten var uafklarede eller havde usikker billedkobling, er nu undersøgt videre. Den udvidede kontrol understøtter koblingen mellem spektrum og råbillede for 39 af de 43 kortlægningsproblemer uden at ændre koordinaterne. Otte af disse ligner detektorartefakter, mens 31 er spektralstrukturer. Det giver følgende aktuelle, fortsat foreløbige status:

| Status | Antal |
|---|---:|
| Sandsynlige detektorartefakter | 209 |
| Forenelige med atmosfærisk O I | 25 |
| Uafklarede spektralstrukturer | 95 |
| Utilstrækkelig billedkobling | 4 |
| I alt | 333 |

[Den samlede tabel](CUMULATIVE_333.csv) bevarer både tidligere status, den nye vurdering og henvisninger til underliggende evidens. Det oprindelige søgekatalog og dets 333 godkendte profiltræf er uændrede. Den særskilte udvidelse med 100 nye eksponeringer ligger under [extension02](../extension02/); den tælles ikke ind i denne tabel.

## Hvad de 95 spektraltræf nu viser

Alle relevante epoker fra projektets eksisterende 200 hovedeksponeringer er inddraget: **117 unikke eksponeringer af 11 stjerner**. De to opfølgningsudvalg giver 938 frameprofiler i 43 separat fastlagte, delvist overlappende bølgelængdegrupper. Disse er ikke 938 uafhængige observationer.

**91 af de 95 fund gentager sig som strukturer i det barycentrisk korrigerede stjernespektrum.** Sammenholdt med de omkringliggende absorptionsstrukturer og overensstemmelser mellem flere stjerner støtter det en almindelig spektral forklaring. Gentagelse er dog ikke alene en linjeidentifikation eller et bevis på naturlig oprindelse. Analysen er efterfølgende og bruger kendte fund som udgangspunkt.

De tre fund **V2-0001, V2-0103 og V2-0104** passer bedre til observatørens referenceframe. I de kontrollerede råbilleder ses skrå rækker af lyse pletter, som krydser stjernens spektralspor. En tilpasning uden brug af selve kandidatens rækker placerer krydsningen tæt på fundet. Sammen med den samtidige Fabry–Pérot-kalibrering og den dokumenterede HARPS-mekanisme gør dette en intern refleksion af kalibreringslys til en stærk forklaring. Den præcise oprindelige orden og optiske overførsel er endnu ikke identificeret; de tre står fortsat som uafklarede med denne evidens tilføjet. Nærliggende fund V2-0125 og V2-0139 følger stjernespektret og er bevaret som modbeviser mod at klassificere alt i dette bølgelængdeområde som kalibreringslys.

**V2-0205** er fortsat svagt og uafklaret. Samtidige linjer ved alle tre undersøgte O I-bølgelængder styrker en atmosfærisk hypotese, men denne eksponering har kalibreringslys i fiber B og derfor ingen uafhængig himmelmåling. I en anden eksponering findes en faktisk himmelfiber med alle tre O I-linjer. Den understøtter de atmosfæriske fortolkninger dér og viser, at V2-0165 kan indeholde både himmellys og et detektorhit.

Den beskrivende breddeanalyse omfatter alle 95 fund i 156 komplette native ordener. **50 af 95** er bredere end to gange detektorens referencebredde i alle komplette ordener og med begge baggrundsmodeller. Referencebredden er antaget, ikke målt; et bredt eller blandet maksimum kan rumme en smal komponent. Resultatet bruges ikke som automatisk frasortering.

## Resterende arbejde og afgrænsning

De fire fortsatte kortlægningsbegrænsninger er **V2-0149, V2-0231, V2-0232 og V2-0333**. De bredere referencevinduer opfylder ikke den fastlagte kvalitetsregel for mindst én dækkende orden. De er derfor bevaret som utilstrækkeligt kontrollerede.

Der er endnu ingen kvalificeret laserkandidat eller målt global falsk-alarm-rate. Fravær af en kvalificeret kandidat er ikke et følsomhedskalibreret nulresultat. CN/CH-båndplacering, CCF-korrigerede sammenfald mellem stjerner og profilbredder er kontekst, ikke identifikation af individuelle overgange. Billedkoblingsreglerne blev udvidet for de 43 begrænsede fund; de historiske gennemgange bruger derfor ikke helt ens kontrolregler.

## Evidens og reproduktion

- [Udvidet råbilledkontrol for 43 fund](../mapping43_followup/README.md), med to analyseagenters separate billedgennemgang.
- [Alle epoker for de første 64](../epoch64_followup/README.md) og [de yderligere 31 samt samlet 95-tabel](../epoch31_followup/README.md).
- [Spektral kontekst og sammenligning mellem stjerner](../line_identification/README.md).
- [O I og himmelfiber](../oi_followup/README.md).
- [Kalibreringslys og skrå råbilledstrukturer](../blue_calibration_followup/README.md).
- [Profilbredder for 64](../profile_widths/README.md) og [31 yderligere fund](../profile_widths31/README.md).
- [Syntesekode](build.py) og [maskinlæsbar opsummering med inputhashes](SUMMARY.json).

Numeriske kontroller er udført i friske processer og på udvalgte beregninger med separat implementering. Analyseagenternes kontroller er ikke uafhængig menneskelig validering.

Den instrumentelle fortolkning er sammenholdt med Cretignier m.fl. (2021), [YARARA, afsnit 2.6 og figur 6](https://arxiv.org/html/2106.07301v1), som beskriver Fabry–Pérot-reflekser i HARPS omkring 3822 og 3851 Å. Vores konkrete fortolkning bygger også på egne epoker og råbilleder; litteraturens bølgelængdeområde alene er ikke et klassifikationskriterium.
