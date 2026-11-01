# Alle epoker for yderligere 31 HARPS-strukturer

De 31 hændelser, som den nye råpixelkortlægning flyttede fra utilstrækkelig kortlægning til uafklaret spektralstruktur, er nu sammenlignet med alle eksisterende udvalgte hovedeksponeringer for deres seks stjerner. Det omfatter 63 unikke spektre: 30 fra den oprindelige prøve og 33 fra V2. De 15 på forhånd fastlagte grupper giver 162 gruppe-epoke-par og 324 komplette profiler i to referenceframes.

Alle 31 indgår i gentagne barycentriske spektralstrukturer. Medianen af parvise kerneprofilkorrelationer spænder fra 0,883 til 0,999. Toppe og nabodale gentages også i epoker uden det oprindelige accepterede hit. Det er beskrivende støtte for vedvarende spektralstruktur; det afgør ikke, om en top er en emissionslinje eller et vindue mellem absorptionstræk, og det identificerer ikke en fysisk art eller oprindelse.

V2-0125 omkring 3852,68 Å er en nyttig kontrol: dens brede struktur gentages tydeligt barycentrisk (r = 0,967), mens den omtrentlige topocentriske sammenligning giver r = −0,046. Nærhed til andre blå kalibreringsproblemer er derfor ikke i sig selv grundlag for at give denne hændelse samme forklaring.

V2-0139 har ni epoker fordelt på kun tre nætter: syv på to nabonætter og to cirka en måned senere. De parvise medianer er derfor næsten ens i de to frames (0,883 og 0,864), fordi mange par har meget kort tidsafstand. De to senere epokers korrelation med de øvrige epokers medianprofil er over 0,88 barycentrisk, men negativ topocentrisk. Det understøtter barycentrisk persistens, med begrænset uafhængig tidsdækning. HD122640 har et lille BERV-spænd og god lighed i begge frames; her er persistens stærkere underbygget end en skarp adskillelse af frames. En lokal enkelt-epoke-spids i N08 bevares og eksisterer samtidig med den fælles brede profil.

## Hændelser og grupper

[Hændelsesoversigten](EVENT_FOLLOWUP.csv) bevarer både den oprindelige status og kortlægningens nye status. [Udvælgelsesproveniens](SELECTION_PROVENANCE.json) verificerer, at netop de 31 hændelser svarer til den endelige kortlægningstabel. Ingen oprindelige tabeller er overskrevet. Der er ingen ny automatisk oprindelsesklassifikation eller blind detektion.

| Gruppe | Stjerne | Bary. Å | Hændelser | Epoker | r bary. | r topo. |
|---|---|---:|---:|---:|---:|---:|
| [N01](figures/N01.png) | HD114386 | 3869.9100 | 1 | 11 | 0.901 | 0.141 |
| [N02](figures/N02.png) | HD114783 | 3852.6800 | 1 | 11 | 0.967 | -0.046 |
| [N03](figures/N03.png) | HD114783 | 3869.3325 | 6 | 11 | 0.993 | 0.056 |
| [N04](figures/N04.png) | HD114783 | 4309.8263 | 2 | 11 | 0.998 | 0.049 |
| [N05](figures/N05.png) | HD114783 | 4312.2375 | 2 | 11 | 0.999 | -0.109 |
| [N06](figures/N06.png) | HD115031 | 3852.3050 | 1 | 9 | 0.883 | 0.864 |
| [N07](figures/N07.png) | HD122640 | 3866.9550 | 1 | 11 | 0.975 | 0.929 |
| [N08](figures/N08.png) | HD122640 | 3868.9288 | 2 | 11 | 0.945 | 0.899 |
| [N09](figures/N09.png) | HD122640 | 4302.6850 | 1 | 11 | 0.994 | 0.948 |
| [N10](figures/N10.png) | HD126093 | 3866.1250 | 3 | 11 | 0.985 | -0.073 |
| [N11](figures/N11.png) | HD126093 | 3866.9450 | 2 | 11 | 0.987 | 0.112 |
| [N12](figures/N12.png) | HD126093 | 3867.3263 | 2 | 11 | 0.988 | 0.072 |
| [N13](figures/N13.png) | HD126093 | 3868.1500 | 4 | 11 | 0.947 | -0.047 |
| [N14](figures/N14.png) | HD126093 | 3869.3025 | 2 | 11 | 0.968 | -0.102 |
| [N15](figures/N15.png) | HD1397 | 3868.7250 | 1 | 10 | 0.943 | -0.140 |

r er medianen af Pearson-korrelationer mellem alle epokepar i den faste kerne, ikke en sandsynlighed eller statistisk signifikans. [Alle gruppemålinger](ALL_EPOCH_MEASUREMENTS.csv) og den eksplicitte [hændelse × epoke-eksport](EVENT_ALL_EPOCH_MEASUREMENTS.csv) gør hver hændelses fulde dækning efterprøvbar. Flere hændelser i samme gruppe deler den samme faste profil og må ikke tælles som uafhængige målinger.

## Metode og kontrol

[Planen](PLAN.json) blev låst før dette ekstra udtræk. Den genbruger den foregående 64-hændelsers metode. De 31 hændelser blev valgt efter råpixelgennemgangen, og nogle overlappende regioner var allerede set i den foregående analyse. Dette er derfor åbenlyst efterfølgende opfølgning, ikke en ny blind prøve.

Grupper dannes deterministisk pr. stjerne med højst 0,10 Å spænd og medianen af hitpositionerne som centrum. Alle udvalgte eksponeringer medtages. Profiler interpoleres lineært på et fast 0,01 Å gitter over ±1 Å uden ekstrapolation; manglende data og store gitterhuller maskeres. Hver epoke normaliseres med medianfluxen over ±2 Å. En lineær baggrund tilpasses de faste ydre områder, og formen sammenlignes inden for ±0,25 Å. Ingen forskydning, bredde eller centrum optimeres for at øge korrelationen.

Omtrentlige topocentriske bølgelængder bruger λ_top ≈ λ_bary/(1+BERV/c), med reference til gruppens laveste hændelses-ID. Det er en klassisk BERV-omregning, ikke en fuld drift- eller relativistisk HARPS-kalibrering. Der antages ingen konstant stjerne-RV, og ingen efterfølgende stjerne-restframe-tilpasning anvendes.

Signerede amplituder fra faste Gaussprofiler med FWHM λ/115000 og tre gange denne bredde gemmes for hver epoke. Alle ERR-arrays mangler brugbare fejl. Derfor rapporteres ingen formelle amplitudeusikkerheder eller SNR-tal. Førstedifferens-MAD er kun en støjproxy; amplitude-kvartiler og spænd er beskrivende variation, ikke konfidensintervaller. Alle 324 profiler er komplette, og ingen nye profiler udløser det fastlagte lav-kontinuum-flag.

[Inputkontrollen](INPUT_CHECKS.json) bekræfter filhash, metadata, bølgelængdeenhed og barycentrisk SPECSYS for alle 63 eksponeringer. [Den numeriske kontrol](NUMERICAL_AUDIT.json) efterregner 18 deterministisk valgte profiler i en frisk proces med skalarinterpolation og separat algebra. Alle kontroller bestod. Det er samme agents beregningskontrol, ikke uafhængig menneskelig validering. Alle 15 grupper er visuelt gennemgået på fire oversigtsfigurer; N06 desuden i detalje.

En separat arbejdskopi kan genskabes med `measure_epochs.py`, `plot_epochs.py`, `plot_overview.py`, `audit_epochs.py`, `report_results.py` og `write_report.py`, med projektets Python-afhængigheder. `report_results.py` skriver også den eksplicitte hændelse-epoke-eksport til den foregående opfølgningsmappe. De frosne planer og oprindelige dispositioner ændres ikke.

## Samlet dækning af 95 hændelser

[Den samlede hændelsesoversigt](COMBINED_95_EVENT_FOLLOWUP.csv) omfatter alle 64 + 31 hændelser: 91 er knyttet til gentagne barycentriske spektralstrukturer, tre til gentagne observer-frame-mønstre og én til en svag linje med topocentrisk præference. Dette er separate beskrivende fund; alle 95 oprindelsesstatusser forbliver uafklarede i denne opfølgning.

Unionen omfatter 117 unikke, allerede eksisterende eksponeringer af 11 stjerner. Der er 43 separat fastlagte og målte grupper, 469 gruppe-epoke-par, 938 frame-profiler og 2.076 hændelse-epoke-frame-rækker. Grupperne overlapper: en ren metadata-sammenlægning giver 37 bølgelængdegrupper. De 37 er ikke genmålt, og 469 gruppe-epoke-par er ikke 469 uafhængige observationer. Denne kontrol tilføjer ingen ny teleskopeksponering og ingen ny hovedprøve til forsøgets søgte datamængde.
