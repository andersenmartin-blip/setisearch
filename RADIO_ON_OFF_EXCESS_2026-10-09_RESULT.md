# SETI: syv uafklarede ON-overskud, 9. oktober 2026

En ny stationær sammenligning har fremhævet **syv svage ON-overskud**, som nu er gennemgået tidsopløst i alle seks gemte HIP98505-scanninger. De bevares som uafklarede spor. Ved **1424,079070 MHz i ON2** ligger den valgte kanal over de faste lokale flanker i alle 16 tidsrækker. De nærmeste OFF-scanninger har ikke et sammenligneligt gennemsnitligt overskud på samme kanal. Der er endnu ingen uafhængig bekræftelse, kalibreret falskalarmrate eller begrundet klassifikation af oprindelsen.

| Udvalgt målscanning | Frekvens, MHz | Positive tidsrækker | Gennemsnitligt lokalt overskud |
| --- | ---: | ---: | ---: |
| ON1, rang 1 | 1422,455934 | 15/16 | 0,080559 |
| ON1, rang 2 | 1424,242591 | 14/16 | 0,132511 |
| ON1, rang 3 | 1422,176121 | 13/16 | 0,096605 |
| ON2, rang 1 | 1424,079070 | 16/16 | 0,139187 |
| ON2, rang 3 | 1422,279163 | 15/16 | 0,093948 |
| ON3, rang 1 | 1424,054588 | 13/16 | 0,143539 |
| ON3, rang 3 | 1423,250530 | 15/16 | 0,148762 |

Sidste kolonne er relative effektenheder: den valgte kanals rå effekt minus medianen af de faste flanker, begge divideret med den tidligere gemte rækkemedian for hele frekvensstykket. Det er hverken SNR, procent af flankebaggrunden eller fysisk flux. Flankerne bruger kanalafstande ±4 til ±64; centrum og de tre nærmeste kanaler på hver side er udeladt. Ingen frekvens eller tidsrække blev flyttet eller valgt om under tidskontrollen.

For ON2-sporet ved 1424,079070 MHz er gennemsnittet 0,139187 og medianen 0,129651. De tilstødende OFF1 og OFF2 har gennemsnit −0,001747 og −0,016272 i samme definition. OFF-profilerne har også udsving over flanker i enkelte rækker; dette er ikke en påstand om OFF-fravær. Den største positive ON-række bidrager 14,28 % af summen af de positive residualer, og de fire største bidrager 47,84 %. Overskuddet er således fordelt gennem scanningen frem for alene at komme fra én række. Alle syv spor har 13–16 positive ON-rækker; største enkeltrækkes bidrag ligger mellem 14,19 og 20,52 %.

## Hvad blev analyseret

Den nye søgning sammenlignede hver ON selvstændigt med dens nærmeste OFF-scanninger. For hver kanal og bredde 1/3 blev den tidligere gemte tidsmiddelværdi divideret med sin løbende medianbaggrund og fratrukket 1. Den signerede kontrast er ON-overskuddet minus det største OFF-overskud ved samme bredde inden for ±32 kanaler. ON1 bruger OFF1, ON2 bruger OFF1/OFF2, og ON3 bruger OFF2/OFF3. Dermed fastholdes begivenheder i en enkelt ON, mens forskudte kontrollinjer inden for nabovinduet indgår i sammenligningen.

Der blev analyseret **1.048.010 kanaler pr. ON over 2,971636 MHz**, inden for det allerede hentede fysiske frekvensstykke. Alle signerede kontrastværdier for begge bredder og den vindende bredde er bevaret. De 20 højest rangerede frekvenser pr. ON blev gemt med mindst 33 kanalers afstand mellem valgte centre; de tre øverste pr. ON fik seks-panels spektralfigurer. To af disse ni profiler ligger ved den allerede tidskontrollerede stærke OFF-linje omkring 1424,43918 MHz. De står fortsat i rangeringen og figurerne, men den afsluttede tidskontrol blev ikke gentaget.

De resterende **syv** profiler fik én samlet, fast tidskontrol: 129 kanaler × 16 rækker i alle seks scanninger, i alt **86.688 bevarede rå effektværdier**. Alle syv tidsprofiler og alle syv vandfald er visuelt gennemgået. De nye resultater omfatter tre fulde kontrastarrays, ni spektralfigurer, syv rå/normaliserede tidsudsnit og 14 tidsfigurer. De øvrige 53 af de 60 rangerede profiler er ikke tidskontrolleret i dette job.

## Hvad resultatet kan bære

Tidsprofilerne blev udvalgt efter de samme tidsmidlede data, der viste overskuddene. Udvælgelse blandt over en million kanaler gør 16/16 positive rækker til en beskrivelse af et udvalgt spor, ikke en binomial signifikanstest eller en uafhængig bekræftelse. Støj, variabel interferens og instrumentstruktur er fortsat mulige forklaringer; ingen af dem er fastslået. De syv spor hverken afvises som støj eller ophøjes til kvalificerede SETI-kandidater.

Den beskrivende opfølgningsliste er ON2 rang 1, ON2 rang 3 og ON3 rang 3. Den er ikke en sandsynlighedsrangering. Et faktisk næste bevistrin skal være en uafhængig observation med egnede kontroller eller en kalibrering af hele den anvendte udvælgelsesfamilie, som bevarer korrelationerne. En gentagelse af de samme udvalgte tidsprofiler kan ikke levere dette.

De seks scanninger er fortsat **ét historisk besøg fra 17. marts 2016**, med samlet ON-integration 863,34 sekunder. Den nye stationære analyse giver ikke ekstra eksponering eller et nyt uafhængigt frekvensbånd. Stationære middelværdier og faste kanaler kan udtynde drivende eller kortvarige emissioner. Den tidligere driftsøgning over 2,950012 MHz, dens stærke OFF-linjer og de allerede afsluttede individuelle kontroller er uændrede. Den oprindelige A/B-kvalifikation forbliver **FAIL_CLOSED**, og den kvalificerede pilot er fortsat blokeret. Dette resultat tilhører den særskilte eksplorative inspektion efter åbning af data.

## Ressourcer og bevaret evidens

Den nye stationære sammenligning brugte **14,327 CPU-s**, og tidskontrollen **11,954 CPU-s**: i alt 26,281 CPU-s i disse to målte processer. Sammenligningens maksimale RSS var 328.966.144 bytes og tidskontrollens 157.573.120 bytes. Installation, forberedelse, gemning og publicering er ikke samlet CPU-målt; disse tal er ikke hele aktivitetens forbrug. Der blev ikke hentet nye teleskopdata. To eksisterende cachearkiver på tilsammen 515.126.101 bytes blev materialiseret.

Dette fortsættelsesarbejde reserverede konservativt **110 CPU-s** (60 + 30 + 20), inklusive forberedelse, gennemgang og publicering. Samlede reservationer er nu **3.910 CPU-s**. Saldo er **2.002,705 CPU-s**, heraf **2.000 beskyttet til slutcheckpunktet 20. oktober**. Kun **2,705 CPU-s** er ubeskyttede. Ingen reservation refunderes ud fra de delvist målte processer, og afsluttede job debiteres ikke igen. Pris: 0 DKK. Der er ikke plads til endnu et væsentligt analysejob før slutcheckpunktet under det eksisterende budget.

Målinger og omfang: [stationær receipt](results/radio_excess_20261009/STATIONARY_CONTRAST_RECEIPT.json), [rangering](results/radio_excess_20261009/top20_per_on.json), [faste udvalgte profiler](results/radio_excess_20261009/SELECTED_TIME_REVIEW.json), [alle tidsmålinger](results/radio_excess_20261009/time_review/TIME_REVIEW.json), [tidsreceipt](results/radio_excess_20261009/time_review/TIME_REVIEW_RECEIPT.json), [visuel fortolkning](results/radio_excess_20261009/TIME_INTERPRETATION.json) og [ledger](results/radio_quicklook_20261009/RESOURCE_LEDGER.json). Kode og frosne omfang ligger i [tools/radio_excess_20261009](tools/radio_excess_20261009).

Arrays og figurer er bevaret i **SETI_ON_OFF_EXCESS_2026-10-09.zip**, 77.022.050 bytes, SHA256 `893e1c804436bd46b36b4569eaff361621e5570e8257c82d27ae2a03570ee88c`. Identitet og genfinding: [EXTERNAL_DATA_ARCHIVE.json](results/radio_excess_20261009/EXTERNAL_DATA_ARCHIVE.json). Kildearkiverne er uændrede; Git-opbevarede JSON-resultater, kode og rapporter er ikke duplikeret i dette arkiv.
