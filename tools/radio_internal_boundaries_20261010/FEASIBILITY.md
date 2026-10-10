# Gennemførlighed: seks interne grænsefelter

Status: **metodeforslag og metadata-kontrol; ingen numerisk implementering eller kørsel**. De gemte kildemetadata og algoritmekilder gør søgningen gennemførlig uden nye teleskoprequests. En separat offentlig kode- og scopefrysning skal ske før en eventuel beregning. De oprindelige søgninger, deres 254 referencefelter pr. bånd og deres afslutningsstatus ændres ikke.

## Fast frekvensgeometri

Hvert nabopar samles i stigende absolut kanalorden, med venstre bånds kanalstart og 2.097.152 kanaler. Frekvensaksen falder fortsat, fordi `df = -2.835503418452676 Hz`. Kun de to sammenføjede referencefelter q255 og q256 søges; de svarer til venstre native q255 og højre native q0. Hvert felt indeholder 4.096 referencekanaler.

| Par | Venstre native q255, absolut halvåbent kanalinterval | Højre native q0, absolut halvåbent kanalinterval |
|---|---:|---:|
| 153 + 154 | [161476608, 161480704) | [161480704, 161484800) |
| 154 + 155 | [162525184, 162529280) | [162529280, 162533376) |
| 157 + 158 | [165670912, 165675008) | [165675008, 165679104) |

De seks scanetiketter, roller, kildeidentiteter og komplette aktuelle headers er identiske inden for hvert par. Tidsstempler, sampling, kanalafstand, kanalnulpunkt, datatype og HDF5-layout stemmer dermed overens. De to native kanalintervaller støder præcist op til hinanden. Metadata-kvitteringen pinner begge manifester, begge acquisition-kvitteringer, begge acquisition-QA-kvitteringer samt de af disse deklarerede kompaktfil- og rækkehashes. Denne gennemførlighedskontrol læser ingen spektrale arrays og gentager ikke deres tidligere byte- eller rækkeaudit.

Feltet q255 har relativt interval [1044480, 1048576), og q256 har [1048576, 1052672). Den uændrede halo på 4.000 kanaler giver samlet læsekontekst [1040480, 1056672), altså 16.192 kanaler omkring samlingen. Den konservative seks-scan profilafstand inklusive ±64 kanaler er 2.772 kanaler ud fra de faktiske header-tider. Både detektorkontekst og faste profiler ligger inden for det gemte par; ingen kontekst fra 156, 159 eller andre naboer behøves.

## Anbefalet ny familie og normalisering

De to native kompaktfiler skal valideres og indlæses separat med den uændrede loader og deres egne native kanalstarter og længden 1.048.576. Først derefter samles de rå `float32`-værdier fra venstre mod højre. Loaderen skal ikke præsenteres for en opdigtet kompaktfil med dobbelt længde.

Detektoren modtager den rå sammenhængende kontekst. Dens eksisterende normalisering over det enkelte statiske 4.096-kanalers felt, 501-kanalers filtrering, robuste score, 763 driftværdier fra −4 til +4 Hz/s og bredderne 1 og 3 ændres ikke. Der må ikke indføres forudgående skalering af detektorinputtet med en native eller sammenføjet median. Absolut kildekanalafrunding med `np.rint`, skalær frekvenskonvertering og den eksisterende behandling af ligestillede scores bevares.

De efterfølgende faste profiler bruger en **ny** fælles nævner: medianen af alle 2.097.152 rå kanaler i hver scanrække, beregnet som `np.median(float32_row)` og derefter promoveret til `float64`, med NumPy 2.3.5. Alle seks gange 16 medianer skal være endelige og positive, gemmes og hashes. Den eksakte sammenføjede median kan ikke udledes af de to gamle native medianer. Der foretages ingen tilpasning eller udligning på de to sider af grænsen.

Dette ændrer profilnormaliseringen i forhold til de tidligere native familier. Den nye baggrund og de nye middelresidualer skal mærkes som en særskilt familie; de må ikke udlægges som en kalibreret forbedring eller sammenlignes som identiske mål med tidligere profiler. Detektorens aritmetik forbliver uændret, men rangeringen omfatter en anden fast familie af referencekanaler.

For hvert par og hver ON-origin samles resultaterne fra præcis de to nye felter. Den eksisterende sortering og afstandsregel anvendes på absolutte referencekanaler, også hen over samlingen. Der gemmes en top20-liste pr. ON-origin. Udvælgelsesreglen for rang 1–3 fryses før den nye kørsel; selve frekvenserne vælges af dens data. Ingen rangering blandes med gamle felter eller mellem naboparrene, og ingen OFF-veto indføres.

De ni profiler pr. par fastholder valgt frekvens, drift og bredde uden refit, frekvensskift eller breddeoptimering. De omfatter alle seks scans og alle 16 rækker, ±64 kanaler og den uændrede medianflanke `abs(offset) > 3` (122 kanaler). Hver ON's første integrationsmidtpunkt er dens egen reference, og profilbanerne bruger de faktiske seks header-tider. Profilfunktionen skal have parrets venstre kanalstart, den sammenføjede længde og en isoleret normaliseringssti som eksplicit kontekst. Hvis det gamle NPZ-feltnavn `saved_full_chunk_row_medians` bevares, skal metadata entydigt definere det som medianen af hele det sammenføjede par.

## Omfang og endelige ressourcegrænser

| Gemte eller beregnede poster | Pr. par | Alle tre par |
|---|---:|---:|
| Nye referencefelter | 2 | 6 |
| ON-feltkort | 6 | 18 |
| Tilhørende felt-normaliserings-JSON | 6 | 18 |
| Referencekanal × ON-poster | 24.576 | 73.728 |
| Drift × bredde-hypotesekombinationer | 37.502.976 | 112.508.928 |
| Top20-poster | 60 | 180 |
| Faste rang 1–3-profiler | 9 | 27 |
| Scanprofil-sammendrag | 54 | 162 |
| Tidsrække-forekomster i profilerne | 864 | 2.592 |
| Rå profilcelle-forekomster | 111.456 | 334.368 |

Hypotesetallet er `6 × 3 × 4096 × 763 × 2`. Poster og hypoteser er korrelerede beregninger, ikke uafhængige signaler eller forsøg. Der indgår 12 kompaktfiler og 192 deklarerede rækkehashes pr. par. Over alle tre par er det 36 fil- og 576 rækkeforekomster, men kun 30 forskellige kompaktfiler og 480 forskellige rækker, fordi bånd 154 bruges i to par. En senere audit skal udtrykkeligt vælge og rapportere sin politik for denne genbrug.

Forslaget holder den angivne ramme på **600 CPU-s: 3 × 120 s numerisk arbejde + 120 s QA + 60 s forberedelse + 60 s pakning**. Der er nul nye HTTP-requests og nul DKK. 120 CPU-s pr. par virker plausibelt med seks felter, men er ikke målt og er ingen gennemførelsesgaranti. En senere kørsel skal afsluttes ærligt ved sin frosne CPU-, wall- eller RAM-grænse og bevare delvise checkpoints og oprindelige fejlstatusser.

Parrene bør behandles sekventielt, med højst 4 GiB pr. job, højst 4 GiB samlet aktiv RAM og højst 8 GiB aktiv arbejdsplads. De seks sammenføjede `float32`-arrays bruger 768 MiB. En simpel sammenføjning med begge originale arrays i hukommelsen topper på 1.536 MiB før disse frigives, plus median- og detektortemporærer. En forudallokeret sammenføjet buffer med en native side ad gangen kan reducere denne top. Undgå komplette sammenføjede `float64`-kopier og unødvendige kopier af inputarkiver. Der er ingen grund til at gemme nye komplette sammenføjede HDF5-filer.

En fremtidig scope skal pinne algoritmekilder, miljøversioner, begge kildemanifester, acquisition- og QA-kvitteringer, alle 12 fil- og 192 rækkeidentiteter pr. par, præcise referencefelter, normaliseringsdefinition, grænser og en isoleret once-only-kvitteringssti. `(pair_id, track_id)` skal identificere profiler entydigt. Hvert færdigt ON-felt skal gemmes og hashes før næste felt; gennemførelse betyder seks komplette kort og ni komplette profiler for det enkelte par. Der udføres ingen genberegning af tidligere referencefelter.

## Videnskabelige begrænsninger

Dette er en ny, efterfølgende udforskende søgefamilie i samme historiske besøg. Kilderne er allerede hentet, og nabokanalerne har indgået i tidligere hele-bånd-medianer, konteksthalos eller baner. Nye referencehypoteser er derfor ikke nye blinde observationer eller uafhængig validering. De tre par deler kontroller, og to par deler hele bånd 154.

ON-udvalgte høje scores og positive profiler giver ingen nulfordeling, FAP, SNR, flux, følsomhed, støjcertificering eller kildeklassifikation. ON og OFF er ikke udskiftelige nulprøver. En lille OFF-residual langs en valgt bevægelig bane udelukker ikke en nærliggende stationær struktur. Rå grænse- og bandpass-struktur skal bevares, beskrives og kontrolleres; den må ikke fjernes gennem efterfølgende normaliseringsvalg eller refit.

Kun nye referencefelter tilføjes. Separate dækningsunioner på 255/256 felter for 153, 155, 157 og 158 og 256/256 for 154 kræver verificeret gemt dækning af alle 254 oprindelige referencefelter i hvert bånd samt fuld gennemførelse af den nye grænsefamilie. Unionerne gælder netop dette faste grid og disse to bredder. De oprindelige fem 254/256-scopes og alle deres afslutningsstatusser bevares, herunder oprindelige ressourcefejl. Det giver ingen generel kompletheds- eller følsomhedspåstand. Grænser mod beskyttet 156 og 159 samt alle ungemte naboer forbliver lukkede. Hele de oprindelige teleskopfiler har fortsat ikke fået deres fulde MD5 verificeret.

Anbefaling: gå videre til en særskilt prospektiv kode- og scopeforberedelse, hvis root autoriserer det. Der er ingen metadata- eller geometriblokering; de væsentlige risici er normaliseringens nye betydning, genbrug af eksponerede data og ressourcetoppe. Ingen numerisk kode eller kørsel indgår i denne anbefaling.
