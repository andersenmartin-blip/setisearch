# Lokal driftopfølgning - 14. oktober 2026

Ingen kvalificeret SETI-detektion er etableret. De ni tidligere udvalgte
ON-spor er undersøgt i alle seks scanninger fra HIP98505/HD189733-besøget
28. april 2017. Den finere søgning ændrer ikke deres oprindelige topscorer.

| Profilgruppe | Antal | Fin all7-score, min-max | Median | Lokalt rang 1 |
|---|---:|---:|---:|---:|
| Oprindeligt udvælgelses-ON | 9 | 6,638491-7,450295 | 6,916444 | 9 |
| Andre ON | 18 | 2,444902-4,543590 | 3,133826 | 3 |
| OFF | 27 | 2,010474-3,605558 | 2,907583 | 4 |

Score er summen af fire standardiserede residualer divideret med 2, ikke
kalibreret SNR. Egen udvælgelses-ON har selektionsfordel. Kontekstmaksima
bekræfter ikke gentagelse; manglende sammenlignelig styrke udelukker ikke
intermittens. Der indføres ingen detektionstærskel eller kvalificeret OFF-veto.

## Frosset familie

Hver af de 54 profiler bruger 81 drifter over d0 +/-4/158 Hz/s og fem faser
fra -0,5 til +0,5 native kanaler. Sporankeret er det oprindelige første valgte
integrationsmidtpunkt. Bredde 1, den originale normaliseringskerne på 4.096
kanaler og median501 bevares. De faktiske pauser mellem scans indgår.

Primærscore maksimerer 405 tupler på de oprindelige fire rækker. Sekundær
all7-score maksimerer over syv fire-rækkers vinduer. Otte korrelerede kontroller
ved +/-256, 512, 768 og 1.024 kanaler bruger samme familie og normalisering.
Alle 1.377.810 scoreforekomster og 3.149.280 rækketermer er gemt. De 153.090
target-scorer er en delmængde; primærscore tælles ikke igen. Flere tupler kan
give identiske afrundede kanalbaner. Første tuple vælges ved scorelighed;
vinderens drift/fase er ikke et fysisk parameterestimat.

Tidsafstanden fra ankeret når 1.997,804 sekunder. Et halvt oprindeligt
drifttrin kan her flytte forventet frekvens 18,102 native kanaler. Det fine
grid giver en geometrisk nærmeste-grid-afstand på højst 0,35128 kanal fra
drift og fase samlet. Det garanterer ikke identiske native bins efter
kanalafrunding og etablerer ingen fysisk følsomhed.

Ingen testet vindue rammer de tre præcise faste DC-centerbins. Deres
hypotesemasker og fulde koordinater er gemt. Nabokanallækage og anden
interferens er fortsat mulige. Kontrolranks er beskrivende og er ikke p-værdier.

## Betingede indsprøjtninger

3.024 tilfælde består af 54 profiler, syv aktivitetsvinduer, fire off-grid
drift/fasepar og to amplituder. Der tilføjes 2 eller 8 standardiserede
enheder til én native bin pr. aktiv række ved kontrolforskydning +512.
Rådata og normalisering ændres ikke; instrumentets linjeform modelleres ikke.

| Amplitude | Tilfælde | Fin vinder rammer 4/4 | Grov vinder rammer 4/4 |
|---|---:|---:|---:|
| 2 | 1512 | 1067 | 39 |
| 8 | 1512 | 1493 | 40 |

Signal alene: fin familie kan repræsentere 4/4 i 1.493 af 1.512 geometrier;
grov d0/fase0 ved det rigtige vindue kan i 40 af 1.512. Gennemsnitlig
indfangning af aktive rækker er 99,6528% versus 7,8208%. Amplituderne
bruger samme geometrier og eksponerede baggrunde. Det er betingede,
korrelerede softwarekontroller, ikke fysisk følsomhed eller en universel
recovery-sandsynlighed.

19 geometrier mangler fuld indfangning også ved amplitude 8: 17 rammer
3/4, og to rammer 2/4. Mere styrke retter ikke dette geometriske tab i
samme familie. Næste kontrol undersøger de præcise afrundingsgrænser,
før observationsfamilien eventuelt udvides.

## Efterregning og reproduktion

Uafhængig QA genberegnede alle 54 normaliseringskerner med direkte
501-medianer, alle rækketermer og scorer, 486 offset-vindersammendrag/ranks
og alle 3.024 indsprøjtninger. JSON/CSV stemmer. Største afvigelse er
5,329070518200751e-15. Alle 54 oprindelige fixed4-scorer reproduceres med
absolut afvigelse 0. QA brugte 29,45492 CPU-sekunder og 68.505.600 bytes
maksimal RAM. Numerisk PASS er efterregning, ikke metodekvalifikation.

Producenten gemte alle familier og sammendrag, men fejlede ved JSON-gemning
af en NumPy-bool. Original kode, fejl og delvis JSON er bevaret. En eneste
bool-cast rettede formatet. Finaliseringen genskabte indsprøjtningsfiler fra
autentificerede gemte familiearrays uden rådataanalyse. Første forsøgs
målte tid er utilgængelig; hele cap på 600 CPU-/900 vægsekunder opføres
konservativt. Genskabelse og QA har separate målte kvitteringer.

Resultatpakken SETI_DRIFT_OPFOELGNING_2026-10-14.zip indeholder alle råcrops,
normaliseringer, familiearrays, tabeller, kode og kontrolkvitteringer.
`python3 replay.py /absolute/new-replay-directory` kan reproducere korrigeret
produktion og uafhængig QA fra pakken. Wrapperen er syntakskontrolleret;
leverancens separate fulde producer- og QA-kørsler er udført. Dette commit
publicerer tekstoutputs, kode og checksumspor. Binære råcrops og familiearrays
følger den leverede resultatpakke.

0 DKK, nul nye teleskopforespørgsler. Original A/B er FAIL_CLOSED;
beskyttede 2016-kontroller og lukket 2019-adgang er uændrede. Checkpoint:
20. oktober 2026.
