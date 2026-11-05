# Samlet leverancekontrol og næste HARPS-udvalg

**5. november 2026: De publicerede tabeller stemmer indbyrdes. Den oprindelige optiske prøve indeholder 300 unikke hovedeksponeringer af 20 stjernenavne og 70,875 timers summeret eksponeringstid. De krævede leverancedele findes med udtrykkelige begrænsninger i følsomhed og ophavsbestemmelse. Rubin er fortsat et begrænset forstudie.**

Dette er en samlerapport under den godkendte ugeplan, ikke en ny signalanalyse eller et kalibreret nulresultat. Kontrollen læser kun allerede publicerede tabeller og kvitteringer. Den åbner ingen spektre eller råbilleder, ændrer ingen klassifikationer og genkører ingen afsluttet diagnose. Den optiske kalenderuge slutter fortsat 7. november; Rubin-rammen er 2.–8. november efter den tidligere fremskyndelse.

## Hvad er faktisk søgt?

| Afgrænset hovedprøve | Unikke eksponeringer | Stjernenavne | Eksponeringstid, sekunder | V1 søgte punkter | V2 søgte punkter |
|---|---:|---:|---:|---:|---:|
| Oprindelig prøve | 100 | 20 | 82.699,582 | 30.650.658 | Ikke kørt |
| Første V2-prøve | 100 | 19 af de samme | 85.599,583 | 30.650.652 | 30.619.618 |
| Anden udvidelse | 100 | 16 af de samme | 86.849,578 | 30.650.654 | 30.618.855 |
| Samlet | **300** | **20 forskellige** | **255.148,743** | **91.951.964 på 300 eksponeringer** | **61.238.473 på 200 eksponeringer** |

Observationernes ADP-ID, råforløber, mål, starttid, gemte inputhash og konkrete søgte punkter fremgår af [alle 300 eksponeringsrækker](results/EXPOSURE_LEDGER.csv). Ingen ADP-ID'er, råforløbere eller mål/start-par er dubleret mellem hovedprøverne. De ni særskilte udviklings-/kontrolspektre tælles ikke med i de 300.

Begge detektorer har det fastlagte område 3800–6900 Å i barycentriske luftbølgelængder. Per eksponering er ikke-finite/udfyldte punkter, huller og metodens rande udeladt. Regnskabet bevarer de faktisk søgte punktantal og summerer deres 0,01 Å brede gridceller særskilt for hver metode. Det er **ikke** én unik bølgelængdestrækning eller uafhængige opløsningselementer. Tiden er summeret over stjerner og år, ikke sammenhængende overvågning. ADU-flux, manglende brugbar ERR-vektor og historiske identitetsforbehold bevares.

## Alle træf og deres nuværende status

| V2-disposition, fortsat foreløbig | Poster |
|---|---:|
| A: sandsynligt detektorartefakt | 403 |
| O: foreneligt med atmosfærisk O I | 46 |
| U: uafklaret spektralstruktur | 185 |
| M: utilstrækkelig oprindelig råbilledkobling | 35 |
| Manglende første rågennemgang | 0 |
| Samlet V2 | **669** |

[Alle 669 rækker](results/V2_CURRENT_DISPOSITIONS_669.csv) bevarer oprindeligt produktionsudfald, nuværende kode, observation, inputhash og evidenstabel med post-ID. De er kontrolleret mod begge uændrede produktionskataloger. A/O er foreløbige forklaringsspor; ingen af disse tabeller beviser endeligt fysisk ophav.

[Alle 22 V1-træf](results/V1_DISPOSITIONS_22.csv) er ligeledes bevaret. De første ti har syv foreløbige artefakt- og tre O I-vurderinger. De to senere sæt på seks har hver et samme-eksponering V2-match inden for den eksisterende 0,02 Å-regel. Deres V2-reference er med i tabellen. V1- og V2-tallene må derfor ikke lægges sammen som uafhængige hændelser.

De [90 poster i den sidst afsluttede kø](../work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md) er de 90 U-poster i anden udvidelse, ikke alle 185 U-poster. Alle 90 har dokumenteret afsluttet afgrænset diagnose eller præcis tidligere behandling. De tidligere 95 U-poster har deres særskilte gemte epokekontekst. De 35 M-poster har alle fået den faste mappingdiagnose over 21 eksponeringer, men deres oprindelige M-koder er bevaret. Afsluttet arbejde betyder ikke, at signalernes fysiske årsag er afgjort.

## Kontrolgenfinding og den konkrete mangel

| Indsat top / oprindelig lokal populationsspredning | V1, oprindelige kontroller | V1, friske parrede kontroller | V2, samme friske kontroller |
|---|---:|---:|---:|
| 4 × | 0/12 | 0/48 | 5/48 |
| 8 × | 0/12 | 0/48 | 36/48 |
| 16 × | 5/12 | 22/48 | 48/48 |
| 32 × | 6/12 | 27/48 | 48/48 |

[Kontrolregnskabet](results/CONTROL_RECOVERY.csv) indeholder også hver bølgelængdeposition. De oprindelige 48 forsøg genbrugte 12 baggrundsudsnit fra én stjerne. De friske 192 V1/V2-forsøg genbrugte 16 udsnit og 48 geometrier, også fra én stjerne. Ingen kontrolposition havde et matchende uændret træf. Hele uændrede baggrundsspektre indeholder dog andre træf med uafklaret ophav; kontrollerne må ikke omsættes til en global falsk-alarm-rate.

Den laveste friske V2-kontrolposition var **4231,19 Å**. Samtidig ligger **188 af 669 V2-træfrækker i 3800–4000 Å**. De tidligere kontroller måler derfor ikke genfinding i dette blå område. Der findes heller ikke en særskilt følsomhedsmåling for anden udvidelses stjerner. Den stærke genfinding ved 16/32 × på HD100508 er ikke dokumentation for samme følsomhed på alle stjerner og bølgelængder.

Kontrollerne gælder additive Gaussian-profiler i reducerede 1D-data. De måler hverken rådatareduktionens tab, transmittereffekt, pulstiming eller populationers forekomst. Det er grunden til den næste konkrete kontrolplan; ingen tidligere tærskel ændres.

## Ugeplanens leverancer

| Krav | Dokumenteret leverance | Begrænsning |
|---|---|---|
| Mindst 10 stjerner / 50 brugbare hovedeksponeringer | 20 målnavne, 300 headergodkendte individuelle eksponeringer | Katalog- og headeridentiteter; tidligere fysisk identitetsforbehold bevares |
| Alle træf med disposition | 669 V2- og 22 V1-rækker med oprindelige kilder | 185 U, 35 M og foreløbige A/O bevares |
| Målt genfinding og kontroludfald | 48 oprindelige og 192 friske parrede forsøg, alle styrker/positioner bevaret | Kun én kontrolstjerne; blå dækning mangler |
| Data, figurer, kode, konfiguration og hashes | Tidligere komplette kataloger, atlasser, rå-/epokefigurer og arkivkvitteringer bevares; samlet tabelindgang her | De store FITS-filer er ikke alle genhashet i denne kontrol |
| Reproduceret eksempel | Gemte beståede kvitteringer for oprindelige prøve, første V2-prøve og anden udvidelse | Her kontrolleres eksisterende kvitteringer; ingen ny spektral genkørsel og ingen ny uafhængig forskervurdering |
| Samlet status | Leverancedele til optisk minimumsprøve foreligger med målte begrænsninger | Intet kvalificeret fravær af lasere; 5. november er endnu ikke planens dag 7 |

Rubin har 190 udvalgte hovedobjekter, men kun to numerisk vurderbare i det primære source-spor, svarende til syv oktoberpunkter. Det særskilte forced-spor har fire vurderbare objekter og 16 punkter med overlap mellem sporene. Ingen objekter er fuldt kvalitetsgodkendte. Minimum 50 er ikke nået. De 36 kontrolforløb gav 18 samplede genfund og 18 usamplede forløb. De tal bevares som forstudie, ikke som et nulresultat, og datagrenen genåbnes ikke af denne kontrol.

## Næste udvalg er fastlagt fra metadata

[Den nye liste på 54 eksponeringer](results/FRESH_METADATA_COHORT54.csv) rummer **50 hovedeksponeringer af 10 andre stjerner** og **fire kontrolspektre fra to yderligere stjerner**. Hovedprøven svarer til 38.369,802 sekunders metadataeksponering, endnu ikke ny søgt tid. Ingen af de 12 målnavne indgår i de oprindelige 20 hovedstjerner eller de to reserverede udviklingsstjerner.

| Rolle | Stjerner |
|---|---|
| Kontrol, to eksponeringer af hver | HD142022, HD142415 |
| Hovedprøve, fem eksponeringer af hver | HD28185, HD30177, HD4208, HD43629, HD48265, HD52758, HD55, HD6718, HD72687, HD73267 |

Udvalget er deterministisk fra den tidligere publicerede, afgrænsede alfabetiske metadatafil. Alle oprindelige 309 input-ID'er og de tidligere mål/start-par er udelukket; råforløbere og aktuelle produktmetadata skal stadig verificeres. De oprindelige målnavne udelukkes helt, inklusive de stjerner, som senere fik ekstra historiske referenceepoker. Rækkefølge, nætter og metadata-SNR afgør udvalget. Der udskiftes ingen fejlede observationer efter at signalværdier er set. Den afgrænsede katalogfil er ikke repræsentativ for hele HARPS-arkivet, og fravær fra den kendte referenceliste beviser ingen videnskabelig nyhed.

De planlagte **288 parrede kontrolforsøg** bruger seks nye bølgelængder, heraf 3807,13 og 3861,29 Å i det blå område, tre pixelplaceringer og de samme fire styrker. Der er 24 unikke baggrundsudsnit og 72 geometrier; det er ikke 288 uafhængige observationer. Den eksisterende V2-detektor forbliver uændret, og der tilpasses ikke efter kontrol- eller hovedresultater. Denne opfølgning er motiveret af tidligere kendte begrænsninger og kaldes ikke en blind, uafhængig kontrol af hele den gamle søgning.

**Der er endnu ikke hentet nye science-filer, læst nye signalværdier eller udført nogen ny kontrol- eller hovedsøgning.** [Den særskilte ruteplan](results/FRESH_ROUTE_PLAN.json) kræver aktuelle metadata-/provenienschecks og derefter en komplet offentlig, verificeret metodefrysning før nye signalværdier. Budgettet er 0 DKK; ingen betalt tjeneste, ny konto eller forskerkontakt indgår. Ingen baggrundssøgning er sat i gang.

## Reproducer denne tabelkontrol

Kør fra repositoryroden i en kopi med de 39 kildefiler fra [SCOPE.json](SCOPE.json):

```bash
python3 work_seti_20261105_d001_delivery/audit_delivery.py --out /tmp/seti-d001-fresh-reproduction
```

Destinationsmappen skal være ny. Programmet kontrollerer kilde- og kodehashes og nægter at overskrive tidligere output. [Det maskinlæsbare resultat](results/DELIVERY_AUDIT.json), [outputhashes](results/OUTPUT_HASHES.json) og [fortsættelsespunktet](NEXT_ACTION.json) bevarer præcis scope og begrænsninger.
