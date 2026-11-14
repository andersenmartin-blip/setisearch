# SETI D065–D066: uafhængige instrumenter og fem FEROS-datasæt

**13. november 2026.** Grundlag: projektversion57, SHA256 `33c32423c9049a3a4e6bd4f6cff44ba46d45b6cd965b45835fd9d1865649f1bd`. Alle klokkeslæt i forespørgsler og kvitteringer er UTC. Arbejdet omfatter identitet, arkivmetadata, headers og proveniens. Der er ikke hentet nye FITS-datakroppe eller læst nye pixels/spektrale fluxværdier.

## Resultatet

Der er fundet **fem FEROS-råfilposter og fem tilhørende reducerede spektrumprodukter fra november2019**. Alle fem par har samme katalogalias for HD43629, matchende header-målkoordinater og en entydig provenienskæde. Det giver et konkret grundlag for næste arbejde med et andet instrument.

Det indledende positionsproblem er bevaret og undersøgt: arkivets og headernes RA/DEC-felter ligger69–79buesekunder fra stjernens katalogposition, mens de særskilte **ESO TEL TARG ALPHA/DELTA**-felter ligger **0.354929buesekund** fra den. De to feltsæt ændres ikke. Metadata understøtter det navngivne mål; årsagen til de afvigende RA/DEC-værdier og den faktiske fiber-/komponentbelysning er ikke fysisk bevist.

De fire afgrænsede primære søgninger efter ESPRESSO/UVES gav nul poster. Der er en dokumenteret dækningsbegrænsning i den bredere instrumentsøgning: én positionsforespørgsel efter reducerede produkter for alle instrumenter kunne ikke gennemføres. **Ingen global påstand om manglende observationer fremsættes.**

Ingen ny signalanalyse er udført. Alle tre tidligere udsving forbliver fysisk uafklarede; **0 kvalificerede lasersignaler**.

## D065: identitet og fast arkivmetode

Den officielle SIMBAD-tjeneste i Harvard returnerer ét objekt ved den eksakte HD-betegnelse: oid879752, main-ID `HD  43629`, ICRS/J2000 **RA94.16446925625°, DEC−13.98743690902°**, koordinatreference `2020yCat.1350....0G`. Elleve aliaser omfatter TIC34077285, TOI-880, GaiaDR3 2993658970584498048 og2MASS J06163947-1359147. Gamle teleskoppegninger bruges ikke som kanoniske koordinater. Spejlingens præcise snapshotdato er ikke verificeret.

Hovedtjenesten gavHTTP404. Harvard-opslaget lykkedes. Første identitetsscript standsede, fordi SIMBAD returnerede display-padding med to mellemrum iHD-navnet. Den første kvittering og kode bevares. En særskilt registreret formatrettelse kollapser kun whitespace, kræver stadig ét objekt og bevarer alle originale strenge; objekt eller koordinater skiftes ikke.

Aktuel officiel ESO-dokumentation og117 kolonnespecifikationer blev læst før observationsforespørgslerne. Metoden blev låst før de nye arkivresultater: råtabellen `dbo.raw` og produkttabellen `ivoa.ObsCore`, delsESPRESSO/UVES, dels alle instrumenter som kontekst; for hver en120buesekunders kegle om den kanoniske position og en separat eksakt aliassøgning. Det giver otte logiske forespørgsler. Alle rå kategorier og produkttyper beholdes. Der filtreres ikke efter dato, eksponering, SNR, bølgelængde eller signalform.

Hver forespørgsel har loft5001rækker og kontrolleret VOTable QUERY_STATUS. Nulrækker er adskilt fraHTTP-/parsefejl og overflow. En normaliseret aliasoverensstemmelse plus højst30buesekunders positionsafstand er den på forhånd fastlagte identitetsklasse. Øvrige navne-/positionskonflikter beholdes uændret som uafklarede.

To rå positionsforespørgsler fik en SQL-geography-fejl om ugyldige latitudeværdier. De blev afviklet med arkivets dokumenterede `s_region`-punktfelt efter en særskilt låst implementeringspræcisering. Kegle, mål, aliasser, instrumenter, kolonner og rækkegrænser var uændrede. Den brede reducerede positionsforespørgsel gav først503 og derefter timeout ved én identisk gentagelse. Alle fejl og begge forsøg bevares. Der blev udført **11 direkte observationsmetadataforespørgsler**; fire af fire primære og tre af fire brede logiske ruter er gennemført.

Unionen indeholder **114 forskellige fil-/produktposter**. De angiver tilgængelige offentlige metadata inden for forespørgslerne. Antal produkter er ikke antal uafhængige hændelser; rå og reduceret fil kan beskrive samme eksponering. En frigivelsesdato i metadata er ikke en afprøvet garanti for senere filadgang.

| Instrument | Råfilposter | Reducerede produktposter | Alias+position≤30″ | Øvrige bevarede poster |
| --- | ---: | ---: | ---: | ---: |
| ESPRESSO | 0 | 0 | 0 | 0 |
| FEROS | 5 | 5 | 0 | 10 |
| GRAVITY | 6 | 0 | 6 | 0 |
| HARPS | 46 | 46 | 92 | 0 |
| PIONIER | 6 | 0 | 6 | 0 |
| UVES | 0 | 0 | 0 | 0 |

HARPS er tidligere undersøgt instrumentkontekst og bliver ikke genåbnet som råkø eller talt som uafhængig bekræftelse. GRAVITY/PIONIER-posterne er kalibrerings-/interferometrikontekst, inklusive sky/dark; de er bevaret uden at blive promoveret til relevante optiske laserobservationer. FEROS' ti poster står fortsat med deres oprindelige positionskonflikt iD065. D066 tilføjer en separat headerbaseret vurdering.

## D066: fem faste FEROS-par

Alle fem råfilposter og alle fem spektrumprodukter fraD065 beholdes. De matches entydigt på metadata-starttid inden for2sekunder. Der vælges ikke den stærkeste, pæneste eller mest interessante eksponering. En særskilt metode og auditkode blev låst før de nye header-/relationssvar.

Der indhentes produktheader, DataLink-relationstabel og råheader for hvert par: **15 direkte svar**, alleHTTP200. Ingen link til en FITS-datakrop følges. For alle fem stemmer instrumentFEROS og målalias TIC34077285 i begge headers; både DataLinks entydige progenitor og produktetsPROV1 peger på den udvalgte råfil. Rå- og produkttider stemmer med katalogposterne inden for den faste2sekundersgrænse.

| Dato2019 | Rå-ID | Produkt-ID | RA/DEC-afstand, ″ | Header-målafstand, ″ |
| --- | --- | --- | ---: | ---: |
| 2019-11-04 | `FEROS.2019-11-04T07:39:37.310` | `ADP.2020-10-15T09:53:47.193` | 78.666 | 0.354929 |
| 2019-11-07 | `FEROS.2019-11-07T07:46:17.029` | `ADP.2020-10-15T09:53:47.341` | 75.644 | 0.354929 |
| 2019-11-08 | `FEROS.2019-11-08T06:31:09.737` | `ADP.2020-10-15T09:53:47.385` | 69.444 | 0.354929 |
| 2019-11-10 | `FEROS.2019-11-10T05:01:01.524` | `ADP.2020-10-15T09:53:47.463` | 69.052 | 0.354929 |
| 2019-11-14 | `FEROS.2019-11-14T06:29:26.536` | `ADP.2020-10-15T09:53:47.647` | 77.283 | 0.354929 |

Alle fem rå- og produktheaders angiver targetALPHA61639.47 ogDELTA−135914.42, med epoch/equinox2000 og juliansk epochsystem. Den fælles ESO TEL.TARG-kodningHHMMSS.TTT/DDMMSS.TTT er kontrolleret i officielESO-dokumentation; det giver RA94.16445833333°, DEC−13.98733888889°. Kodningskontrollen er ikke overførsel af en instrumentprofil eller kalibrering mellemVIRCAM, FEROS ogHARPS.

De reducerede poster angiver eksponering500.043s, kalibreringsniveau2 og nomineltR48000. Bølgelængdegrænserne iObsCore er i vakuummeter. De sammenlignes endnu ikke med de gamle barycentriske luftbølgelængder. Ingen HARPS-trace, COMB-respons, støjkovarians, radialhastighedskorrektion eller lasersvarfunktion overføres tilFEROS.

Identitetskontrollen understøtter metadataenes navngivne mål. Den fastslår ikke den faktiske fotonbelysning i fiberen, en bestemt komponent i et muligt system, en fysisk årsag til RA/DEC-forskellen eller kvaliteten af spektrenes indhold. Observationerne er fra2019 og kan ikke direkte bekræfte en samtidig hændelse i2021.

## Kontroller og bevaring

Fire anvendelige audits består og er genkørt uden at ændre deres kanoniske kvitteringer. D065's første audit efterregner3114 XML-celler, identitet,114produktposter og routemedlemskab. Den efterfølgende afgrænsede audit efterregner1890 yderligere celler og bevarer timeout som fejl. Den oprindelige completion-auditor forudsatte tre vellykkede svar; den bevares ueksekveret, mens den særskilt låste afgrænsede auditor kontrollerer den faktiske delvise dækning. Produktionsresultater ændres ikke for at få en audit til at bestå.

D066 efterregner4230 headerværdier med en separat strengparser, alle15 svarhashes og fem koordinatpar. En ekstra efterfølgende proveniensaudit genberegner45 gatebetingelser, DataLink-/PROV1-identitet samt epoch/equinox og koordinatkodning. Største forskel mellem to vinkelberegninger er under1.3e−11buesekund. Dette er intern efterregning af samme assistent, ikke ekstern fagfællebedømmelse.

Dokumentationsadgang er registreret særskilt: første manualhentning ramte en8MB-grænse og bevares markeret som afkortet. Hele manualen på10,658,129bytes blev derefter hentet med en eksplicit større dokumentgrænse. To supplerende webvisninger af headers kunne ikke håndtere den bare query-URL og gav intet brugbart headerindhold. Alle videnskabelige headerdata kommer fra de15 gemte direkte svar.

Alle **88.593 tidligere tabelceller** bevares eksakt i samme37+141rækker. Hver fase tilføjer otte kolonner; nu **91.441celler**. De oprindelige0061-rho-fejl, blåCOMB-mangel, sekundære6.marts-status, støj-/responsbegrænsninger og alle gamle signalvurderinger er uændrede. De tre tidligere aktive rodpegere ligger eksakt iD065/FROZEN_PARENT. Alle tidligere videnskabelige hovedarkivmedlemmer bevares byte for byte.

Resultatpakken indeholder begge faser, rå metadata- og fejlresponses, headers, relationer, alle parseroutputs, fulde state-tabeller, metoder, kode, audits, primærdokumentation og rapport. `verify.py` efterregner de fire audits uden netværk og bevarer kanoniske kvitteringer. Relevante direkte input uden for hovedarkivet medtages uændret.

## Fortsættelse

D067 foreslås som en særskilt låst erhvervelse og validering af **alle fem faste FEROS-rå-/produktpar**. Filidentiteter, bytegrænser, adgang, headers, HDU-struktur og checksums skal fastlægges før hentning. Spektralanalysen skal derefter have sin egen metode med instrumentets egne koordinat-, bølgelængde-, støj- og kalibreringsforudsætninger. Ingen datakroppe er hentet fra denne plan, ogD067 er endnu ikke låst eller udført.

De samme gamle optiske eksponeringers valgfrie modelvarianter forbliver sat på pause. Den gamle141kø er lukket,90-/Rubinspor stoppet, offentlig upload udskudt. Ingen udgifter, eksterne personkontakter eller baggrundsberegninger. Alle tre oprindelser er fortsat uafklarede;0 kvalificerede lasersignaler og ingen kalibreretFAP.

## Primærkilder

- [ESO: programmatisk arkivadgang](https://www.eso.org/cms/eso-data/programmatic-access.html) og [TAP-eksempler](https://archive.eso.org/tap_obs/examples); aktuelle skemaer og præcise forespørgsler er gemt i pakken.
- [Officiel SIMBAD Harvard-spejling](https://simbad.cfa.harvard.edu/simbad/sim-tap/); eksakt HD-identitetsforespørgsel, svar og koordinatmetadata er gemt.
- [ESO-manual med TEL.TARG-koordinatkodning](https://eso.org/sci/facilities/paranal/instruments/vircam/doc/VIS-MAN-ESO-06000-0002_v105_2.pdf). Anvendt til fælles keywordformat; ingen FEROS-responskalibrering udledes.
- De15 præcise ESO-header-/DataLink-URL'er og svarhashes findes iD066/responses og GATE_RESULTS5.json.
