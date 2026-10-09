# SETI — nyt frekvensbånd, 9. oktober 2026

Et tidligere uåbnet bånd omkring **1424,532–1427,505 MHz** er hentet og analyseret i alle seks scanninger af HIP98505/HD189733 fra **17. marts 2016**. Det er nye frekvensværdier fra den samme historiske observation, ikke et nyt teleskopbesøg.

Det centrale nye kontrolresultat er, at det stærkt rangerede område ved **1426,282 MHz** også findes med næsten samme faste profilmiddel i OFF: ON2s drift-rang 1 giver **1,578749 mod OFF1s 1,558537**, og ON3s drift-rang 1 giver **0,897975 mod OFF3s 0,877271**, i de samme additive profilenheder. De ni driftprofiler er korrelerede varianter af dette ene frekvensområde. De mindre stationære udsving forbliver uafklarede.

Den stationære søgning er afsluttet for **1.048.010 bærefrekvenser pr. scanning** i bredde 1 og 3; både ON og de reciprokke OFF-kontroller er bevaret. Den separate driftssøgning er afsluttet for **131.072 bærefrekvenser pr. ON** i 32 faste, adskilte delbånd, med 763 driftværdier fra −4 til +4 Hz/s og bredde 1/3. Driftfamilien dækker **12,5 %** af den hentede native kanalblok.

Alle **18** profiler i udvalget af **rang 1–3 fra hvert ON og hver af de to familier** er undersøgt ved den oprindeligt valgte frekvens, drift og bredde. Udvælgelsesreglen var frosset før signalværdierne blev åbnet; frekvenserne og driftværdierne blev valgt af selve søgningen. 6 af profilerne har positivt center-minus-flanke i alle 16 ON-rækker. De største drift-rangeringer samler sig i samme smalle frekvensområde med tydelige OFF-træk. Tallene beskriver udvalgte profiler og er ikke uafhængige forsøg eller sandsynligheder.

**Alle viste spor forbliver uafklarede eksplorative rangeringer. A/B er fortsat FAIL_CLOSED, og en kvalificeret sky-pilot er fortsat blokeret.** Der er ingen kalibreret sky-SNR, falskalarmrate, flux, følsomhedsgrænse, celestial klassifikation eller generel nuldetektion.

## Stationært overskud og reciprokke kontroller

Hver scanning normaliseres med sin egen median over hele den frosne kanalblok i hver tidsrække. Det stationære spektrum er middelpower delt med sin 501-kanalers løbende median minus 1. Rangeringen er scanningens bredde-middel minus den største værdi i de tilstødende kontrolscanninger inden for ±32 kanaler. Tabellen viser kun rang 1; alle top20-lister og samtlige signerede bredde1/bredde3-kort er bevaret.

| Oprindelse | MHz | Bredde, kanaler | Stationær signeret kontrast |
| --- | --- | --- | --- |
| ON1 | 1425,004496 | 1 | 0,259807 |
| OFF1 | 1424,787563 | 1 | 0,062209 |
| ON2 | 1424,970073 | 1 | 0,064893 |
| OFF2 | 1425,004513 | 1 | 0,103059 |
| ON3 | 1425,836881 | 1 | 0,080217 |
| OFF3 | 1425,004516 | 1 | 0,154050 |

ON1s første rang ved **1425,004495974 MHz** har et stationært fraktionelt overskud på 1,930771. OFF1 har 1,068801 ved samme kanal og 1,670964 i det frosne ±32-kanalers vindue. Den signerede forskel er derfor 0,259807. OFF2 og OFF3s første rang ligger ved 1425,004512987 og 1425,004515823 MHz. Der er således stærke nærliggende træk i kontrolscanningerne; en positiv kontrast her er ikke evidens for et isoleret ON-træk.

ON og OFF bruger samme stationære regneregel, men er ikke certificeret udskiftelige. ON1 og OFF3 har én tilstødende kontrol; de andre har to. Tidspunkter, delte kontroller, frekvenser, interferens og individuel normalisering kan påvirke rangeringerne. De reciprokke OFF-rangeringer er kontrolmateriale, ikke en kalibreret nulfordeling.

## Driftfamilien

De 32 delbånd indeholder tilsammen 0,371655 MHz kanalbredde pr. ON. Mellemrummene er ikke driftssøgt. Den uændrede detector bruger normalisering på hvert fast 4096-kanalers core, en 501-kanalers løbende median og en empirisk MAD-skala. Den robuste box-track-score er en anden størrelse end den stationære fraktionelle kontrast og må ikke sammenlignes numerisk med den.

| Oprindelse | MHz ved første rækkemidtpunkt | Drift, Hz/s | Bredde, kanaler | Robust box-track-score |
| --- | --- | --- | --- | --- |
| ON1 | 1426,282128 | −0,010499 | 3 | 54,103 |
| ON2 | 1426,282128 | 0,000000 | 1 | 58,200 |
| ON3 | 1426,282126 | 0,000000 | 3 | 58,059 |

Alle **ni** viste driftprofiler ligger i samme smalle frekvensregion omkring **1426,282 MHz**, ved source-kanaler 158766412–158766421 og referencefrekvenser 1426,282114269–1426,282139789 MHz. De er korrelerede nabovarianter af ét frekvensområde, ikke ni uafhængige fund. Den frosne visningsregel undertrykker kun referencer inden for tre kanaler og kan derfor vise varianter fire kanaler fra en stærk feature.

Alle bærefrekvensers maksimum, vindende bredde/drift og komplette hypotesetælling er gemt særskilt for hvert scan/core-trin. Der er ikke anvendt OFF-veto. Rangeringen bruger hvert ONs eget første integrationsmidtpunkt som reference; kontrolprofilerne følger den samme faste topocentriske forudsigelse ved deres faktiske observationstider.

## Alle 18 faste profiler

Tabellens additive profilmål er bredde-middel af raw power delt med den gemte full-chunk-rækkemedian, minus rækkens flankmedian ved faste offsets med |offset| > 3 inden for ±64 kanaler. Frekvens, drift, bredde, tidsvindue og kanalskift er ikke justeret efter udvælgelsen. Alle 16 rækker og alle seks scanninger er gemt som raw float32-patches og normaliserede profiler.

| Fast valgt profil | MHz | Drift | Bredde | ON-middel | Største tilstødende OFF-middel | ON minus OFF | Positive ON-rækker |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Stationær ON1 rang 1 | 1425,004496 | 0,0000 | 1 | 1,858853 | 1,025203 | 0,833650 | 16/16 |
| Stationær ON1 rang 2 | 1425,001161 | 0,0000 | 1 | 0,672272 | 0,374302 | 0,297971 | 16/16 |
| Stationær ON1 rang 3 | 1426,035352 | 0,0000 | 1 | 0,122145 | 0,034048 | 0,088097 | 15/16 |
| Stationær ON2 rang 1 | 1424,970073 | 0,0000 | 1 | 0,134119 | 0,015388 | 0,118731 | 13/16 |
| Stationær ON2 rang 2 | 1425,519435 | 0,0000 | 1 | 0,106362 | 0,015756 | 0,090605 | 15/16 |
| Stationær ON2 rang 3 | 1426,118194 | 0,0000 | 1 | 0,120947 | 0,031122 | 0,089825 | 15/16 |
| Stationær ON3 rang 1 | 1425,836881 | 0,0000 | 1 | 0,134680 | 0,005729 | 0,128951 | 14/16 |
| Stationær ON3 rang 2 | 1424,648895 | 0,0000 | 1 | 0,130013 | −0,005781 | 0,135794 | 13/16 |
| Stationær ON3 rang 3 | 1426,282126 | 0,0000 | 1 | 1,420761 | 1,316814 | 0,103947 | 16/16 |
| Drift ON1 rang 1 | 1426,282128 | −0,0105 | 3 | 0,836998 | 0,330711 | 0,506287 | 16/16 |
| Drift ON1 rang 2 | 1426,282117 | 0,0525 | 3 | 0,454940 | 0,059754 | 0,395186 | 14/16 |
| Drift ON1 rang 3 | 1426,282140 | −0,0840 | 3 | 0,435169 | 0,001241 | 0,433928 | 15/16 |
| Drift ON2 rang 1 | 1426,282128 | 0,0000 | 1 | 1,578749 | 1,558537 | 0,020212 | 16/16 |
| Drift ON2 rang 2 | 1426,282140 | −0,0630 | 3 | 0,477128 | 0,025033 | 0,452096 | 13/16 |
| Drift ON2 rang 3 | 1426,282117 | 0,0525 | 3 | 0,443144 | 0,020451 | 0,422693 | 13/16 |
| Drift ON3 rang 1 | 1426,282126 | 0,0000 | 3 | 0,897975 | 0,877271 | 0,020705 | 16/16 |
| Drift ON3 rang 2 | 1426,282137 | −0,0525 | 3 | 0,545852 | 0,010291 | 0,535562 | 13/16 |
| Drift ON3 rang 3 | 1426,282114 | 0,0630 | 3 | 0,400880 | 0,002640 | 0,398240 | 14/16 |

OFF-kolonnen følger præcis den valgte frekvens/drift ved hvert OFFs tidspunkt. Den søger ikke et nyt OFF-maksimum og erstatter ikke den stationære rangregels ±32-kanalers kontrol-envelope. Additive profilmål er heller ikke de robuste driftsscorer. Lignende profiler kan skyldes flere forhold; en forskel mellem ON og OFF alene afgør ikke oprindelsen.

En valgt driftvariant kan mellem scanningerne flytte sin præcise forudsigelse væk fra en lokal feature. En lille OFF-værdi på denne faste bane er derfor ikke dokumentation for fravær af en nærliggende OFF-feature. Det stationære top20-materiale viser eksempelvis ved 1426,282125611 MHz et ON3-overskud på 1,379804, en tilstødende OFF2-vinduesværdi på 1,311687 og OFF3s præcise kanalværdi på 1,274975. Dette er gemt kontrolevidens i samme region, uden at indføre et efterfølgende OFF-veto.

Ved ON2s drift-rang 1 er det faste additive middel 1,578749, mens OFF1 er 1,558537 og OFF2 1,360915. ON3s drift-rang 1 har middel 0,897975 mod OFF3s 0,877271. Kontrolprofilerne er altså næsten lige så store ved den samme næsten stationære feature. Alle 18 valgte ON-midler overstiger deres største tilstødende faste OFF-middel, altså 0/18 med OFF-middel mindst lige så stort som ON. Sammenligningen er påvirket af, at alle profiler blev udvalgt ud fra ON-scorer; den kan derfor ikke bruges som en fordelingsfri falskalarmtest eller som uafhængig bekræftelse. Middelprofilerne over ±64 kanaler viser også de nærliggende OFF-toppe, som driftvarianternes præcise center kan bevæge sig væk fra. Ingen bane er refittet eller flyttet for denne vurdering.

## Figurer og gemt evidens

- `epoch1_on_stationary_rank_01`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch1_on_stationary_rank_01_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch1_on_stationary_rank_01_mean.png)
- `epoch1_on_stationary_rank_02`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch1_on_stationary_rank_02_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch1_on_stationary_rank_02_mean.png)
- `epoch1_on_stationary_rank_03`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch1_on_stationary_rank_03_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch1_on_stationary_rank_03_mean.png)
- `epoch2_on_stationary_rank_01`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch2_on_stationary_rank_01_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch2_on_stationary_rank_01_mean.png)
- `epoch2_on_stationary_rank_02`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch2_on_stationary_rank_02_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch2_on_stationary_rank_02_mean.png)
- `epoch2_on_stationary_rank_03`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch2_on_stationary_rank_03_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch2_on_stationary_rank_03_mean.png)
- `epoch3_on_stationary_rank_01`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch3_on_stationary_rank_01_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch3_on_stationary_rank_01_mean.png)
- `epoch3_on_stationary_rank_02`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch3_on_stationary_rank_02_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch3_on_stationary_rank_02_mean.png)
- `epoch3_on_stationary_rank_03`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch3_on_stationary_rank_03_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch3_on_stationary_rank_03_mean.png)
- `epoch1_on_drift_rank_01`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch1_on_drift_rank_01_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch1_on_drift_rank_01_mean.png)
- `epoch1_on_drift_rank_02`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch1_on_drift_rank_02_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch1_on_drift_rank_02_mean.png)
- `epoch1_on_drift_rank_03`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch1_on_drift_rank_03_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch1_on_drift_rank_03_mean.png)
- `epoch2_on_drift_rank_01`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch2_on_drift_rank_01_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch2_on_drift_rank_01_mean.png)
- `epoch2_on_drift_rank_02`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch2_on_drift_rank_02_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch2_on_drift_rank_02_mean.png)
- `epoch2_on_drift_rank_03`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch2_on_drift_rank_03_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch2_on_drift_rank_03_mean.png)
- `epoch3_on_drift_rank_01`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch3_on_drift_rank_01_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch3_on_drift_rank_01_mean.png)
- `epoch3_on_drift_rank_02`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch3_on_drift_rank_02_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch3_on_drift_rank_02_mean.png)
- `epoch3_on_drift_rank_03`: [Tidsprofil](results/radio_fresh_band_20261009/presentation/epoch3_on_drift_rank_03_time.png) · [Middelspektrum](results/radio_fresh_band_20261009/presentation/epoch3_on_drift_rank_03_mean.png)

De oprindeligt gemte figurer under `profiles/` er bevaret uændret. Rapportens figurer under `presentation/` er særskilt hashregistrerede præsentationskopier, som alene ændrer layout og etiketter og bruger de allerede gemte profil-arrays. Signalanalysen er ikke genkørt.

Alle 18 profiler og 108 scan-profiler findes desuden i de ledsagende CSV-tabeller. Filhashes, eksakte kanalintervaller og fasernes fuldstændighed fremgår af de gemte receipts.

## Evidenshul og næste videnskabelige arbejde

Der mangler fortsat et uafhængigt besøg med samme frekvensdækning eller en separat kvalificeret model, som bevarer korrelationerne og omfatter hele udvælgelsesfamilien. En rang blandt millioner af beslægtede hypoteser samt 16 positive rækker kan ikke i sig selv give en falskalarmrate. OFF er heller ikke certificeret ren støj.

Det primære næste evidenstrin er at finde et uafhængigt besøg med frekvensoverlap. Et endnu uåbnet bånd eller en separat kvalificeret korrelationsbevarende kontrolmodel er videnskabelige muligheder, som kræver en ny konkret ressourcefordeling. De er ikke finansierede næste analysejobs inden for den aktuelle frie ramme. Den tidligere kvalifikationsfejl og holdouts skal forblive lukkede, og en kontrolmodel må ikke tilpasses for at gøre de viste spor mere positive.

Denne arbejdsomgang har en konservativ reservation på 750 CPU-sekunder. Den resterende ramme er 652,705 CPU-sekunder, hvoraf 650 er beskyttet til afslutningen 20. oktober og 2,705 er udisponeret. Den samlede godkendte ramme er ikke udvidet; der er ikke disponeret til endnu et nyt bånd.

## Prospective freeze og komplette artefakter

Metadata-båndvalget blev offentliggjort i [d2ea2eceda0f969ab82e7563286930c21b36e054](https://github.com/andersenmartin-blip/setisearch/commit/d2ea2eceda0f969ab82e7563286930c21b36e054). Acquisition- og analysescope samt kode og ressourcefordeling blev frosset i [44872590df8136135a99e52612b456c187c67190](https://github.com/andersenmartin-blip/setisearch/commit/44872590df8136135a99e52612b456c187c67190), før de nye spektrale værdier blev hentet.

De komplette artefakter samles i `SETI_FRESH_BAND151_RAW_2026-10-09.zip` og `SETI_FRESH_BAND151_RESULTS_2026-10-09.zip`. RAW indeholder kompakte raw-H5-filer, scopes og receipts. RESULTS indeholder alle stationære kort og spektre, drift-arrays, 18 raw-patches, de 36 oprindelige figurer og 36 præsentationskopier samt CSV-tabeller, rapport, kode og QA. Archivehashes og faktisk tilgængelighed dokumenteres særskilt efter afsluttet lagring.

## Udførelse

Acquisition blev afsluttet med 305.137.622 modtagne spektrale application-body-byte fordelt på 96 præcise ranges. Fil- og rækkehashes er kontrolleret. Kildebyte er ikke en måling af samlet wire-trafik.

- Hentning: 3,436 CPU-s; 564,972 vægsekunder; fuldstændig.
- Stationær analyse: 7,753 CPU-s; 7,650 vægsekunder; fuldstændig.
- Driftanalyse: 250,095 CPU-s; 250,145 vægsekunder; fuldstændig.
- Faste profiler: 21,603 CPU-s; 21,520 vægsekunder; fuldstændig.
