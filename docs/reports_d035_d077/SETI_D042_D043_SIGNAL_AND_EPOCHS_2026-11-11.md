# SETI D042 — signalets lokale overskud i to koordinatrammer

11. november 2026. Udgangspunkt: D041, gemt projektversion 47.

**Kontroloptagelsen har et væsentligt mindre lokalt overskud ved den fastlagte, barycentrisk korrigerede position.** Det gælder alle seks kontinuumvalg og de deklarerede afrundingsvalg. I den primære måling ligger det største positive kontrol/original-forhold på 10.03 %. Dette er et maksimum blandt de beskrevne målevalg; det har ingen kalibreret dækningssandsynlighed og er ikke en statistisk øvre grænse for en laser.

Resultatet kvantificerer forskellen mellem to allerede kendte observationer af HD 43629. D016 og D021 havde tidligere undersøgt de fem registrerede epoker, herunder E04 og CCF-baserede koordinater. D042 er en ny, fastlagt sammenligning af det robuste radius3-overskud med alle seks baggrunde og tydelig afrundingskontrol. Det er ingen ny observation eller blind opdagelse. Årsagen til trækket fra 5. marts er fortsat uafklaret; 0 kvalificerede lasere.

## Koordinater og fastlagt metode

Den arvede, kendte position er 6550,095 Å i barycentriske luftbølgelængder. Den blev ikke genestimeret fra de aktuelle profiler. Egne native A-polynomier og egne BERV-headerværdier bestemmer observatørbølgelængde og native position. De egne Phase3-produkter bekræfter BARYCENT, Angstrom, luftbølgelængder og HARPS_3.8. Den tidligere D022-konvertering reproduceres.

Der anvendes den dokumenterede strækning

`lambda_bary = lambda_observer × (1 + BERV/c)`, med `c = 299792.458 km/s`.

Ingen luft/vakuum-konvertering eller frit tilpasset forskydning tilføjes. Den primære ramme er solsystemets barycentrum. En særskilt følsomhedskontrol med tidligere CCF-hastigheder er beskrevet nedenfor; den primære analyse er ikke en ny reduktion til stjernens fysiske hvileramme.

| Optagelse | Egen BERV, km/s | Forventet observer-air-position, Å | Fraktionel native position | Nærmeste sample |
|---|---:|---:|---:|---:|
| 2021-03-05 | -22.255773812 | 6550.581297276 | 421.393486027 | 421 |
| 2021-03-09 | -22.917285048 | 6550.595752658 | 422.120268643 | 422 |

Den beregnede forskel er 0.726782616 pixel. Den primære sammenligning bruger derfor originalens sample 421 og kontrollens sample 422. Som separat detektorkontrol beholdes sample 421 i begge optagelser, hvilket svarer til samme rå række 3674, men eget rumligt A-spor. Barycentrisk bruges både NEAREST, FLOOR og CEIL. FLOOR er her numerisk identisk med NEAREST og beholdes som en eksplicit dublet.

De to røde kontekster og D041-figurerne var allerede set, inden D042-metoden blev fastlagt. METHOD_LOCK.json blev derefter skrevet før første D042-amplitudesammenligning. Der er ikke flyttet, interpoleret eller geninddelt rå fluxprøver. Hele beregningen bruger eksisterende samples 293–549; intet nyt råvindue er åbnet.

## Det målte overskud

Den primære størrelse er den fortegnede sum af tre samples, `anker−1, anker, anker+1`, efter fradrag af det lokalt tilpassede kontinuum. Der gemmes også summer over 5 og 15 samples samt et diagnostisk maksimum i et fast ±2-vindue. Maksimum bruges aldrig til at flytte positionen eller vælge baggrund.

Alle seks arvede kontinuumvalg bruges: affine og kvadratiske sidebånd 5–7, 8–12 og 12–20 pixels. Hver optagelse normaliseres kun med sin tidligere fastlagte median uden for de centrale 41 samples. Kontrollens median er 97,434 % af originalens. Der tilpasses ingen lokal fluxskala efter sammenligningen.

Tabellen viser intervallet over de seks baggrundsvalg. Forholdet bruger de to optagelsers egne faste normaliseringer.

| Koordinatramme / afrunding | Originalens 3-sample-sum, ADU | Kontrollens 3-sample-sum, ADU | Fortegnet kontrol/original-forhold |
|---|---:|---:|---:|
| DETECTOR_NATIVE / FIXED_K421 | 782.25 til 1178.09 | -102.05 til 351.74 | -8.96 % til +46.15 % |
| BARYCENTRIC_AIR / NEAREST | 782.25 til 1178.09 | -250.39 til 76.48 | -27.89 % til +10.03 % |
| BARYCENTRIC_AIR / FLOOR | 782.25 til 1178.09 | -250.39 til 76.48 | -27.89 % til +10.03 % |
| BARYCENTRIC_AIR / CEIL | 807.94 til 1176.54 | -623.85 til -49.73 | -79.25 % til -5.45 % |

På den primære barycentriske position er originalens overskud 782.25–1178.09 ADU og kontrollens −250,39 til +76,48 ADU. Original minus kontrol er positivt i samtlige deklarerede sammenligninger. Resultatet afhænger altså ikke af at udpege én foretrukken baggrund eller den afrunding, der giver mindst kontrolsignal.

Negative værdier angiver et underskud i forhold til det tilpassede kontinuum. En sum over tre native samples er et lokalt mål for overskuddet, ikke en kalibreret linjeluminositet, ækvivalentbredde eller et integral over nøjagtigt samme fysiske bølgelængdeinterval. Afrundingsvalgene belyser denne følsomhed og er ikke et kalibreret interval for bølgelængdefejlen. Den oprindelige position anvendes ved den gemte præcision 6550,095 Å.

Der er 48 enkelt-slots og 24 par-slots. De svarer til 30 forskellige native-anker/kontinuumtilpasninger og 18 forskellige par af ankre/kontinuumvalg. Seks par er rene FLOOR/NEAREST-dubletter. De mange slots er ikke uafhængige bekræftelser eller en population til beregning af falske alarmer.

## Ekstra kontrol med historiske CCF-hastigheder

Ved gennemgang af projektets tidligere analyser blev de gemte CCF-hastigheder fra D016 og E04-proveniensen inddraget. Denne **supplerende** kontrol blev fastlagt efter de primære D042-resultater og efter, at CCF-værdierne var set. Den ændrer ikke den primære metode eller noget primært resultat.

De registrerede CCF-RVC-værdier er 33.862656421089 og 33.864923767328 km/s. Deres nominelle forskel er 2.267346 m/s. Til sammenligning anvendes kontrolpositionen

`6550.095 × (1 + RVC_control/c) / (1 + RVC_original/c)`

som barycentrisk mål og derfra egen BERV-konvertering. Det flytter kontrollens fraktionelle native koordinat med 0.002433506 pixel til 422.122702149. NEAREST, FLOOR og CEIL forbliver henholdsvis 422, 422 og 423. Dermed er alle deklarerede, diskrete amplitude-summer uændrede ved denne nominelle følsomhedskontrol.

Originalens CCF-medlem og header er verificeret direkte mod de allerede gemte ancillary-bytes og historisk SHA. Kontrollens CCF-body er ikke gendannet eller hentet i denne fase; dens værdi har alene den arvede metadata/proveniens. Kontrollen er derfor ingen ny, uafhængig kalibrering af stjernens intrinsiske hastighed eller af en bestemt linjes bevægelse. RV_SENSITIVITY_SCOPE.json og RV_SENSITIVITY_RESULT.json bevarer denne begrænsning.

## Beregningskontrol og fortolkning

En separat implementering løser bølgelængdekoordinaterne med 60-cifret Decimal-aritmetik og genberegner alle 48 kontinuumtilpasninger med QR. Alle 144 sumoperatorer kontrolleres direkte som lineære funktionaler af de uændrede native samples; de annullerer de tilpassede kontinuumpolynomier. De 24 par, alle afrundinger, dubletter, forhold og fortegn er kontrolleret. Den største forskel i en fortegnet ADU-sum er cirka 2,1×10⁻¹¹ ADU. Kontrollen består. Dette er separate algoritmer i samme arbejdssession, ikke ekstern fagfællebedømmelse.

Den fastlagte sammenligning viser mindre lokalt overskud i kontroloptagelsen inden for de deklarerede koordinater og støtter. Der beregnes ingen gaussiske signifikansniveauer, p-værdier, kalibreret FAP eller kilde-duty-cycle. Én kontrolobservation afgør hverken en fysisk variabilitetsmekanisme eller en bestemt fejl-/partikelårsag. D040/D041s store referenceudsving og den uvaliderede fulde kovarians består som begrænsninger.

De tidligere tabellers 55.841 felter er uændrede; D042 tilføjer kun egne kolonner. D039s 16 grene og 22.000 tilpasninger, D040s 10.000 træk og D041s 2.000 træk bevares. D002-0061s oprindelige kvalitetsfejl, rho 0,780656 < 0,8, er ikke erstattet af den nye amplitudeanalyse. D002-0063s blå status ændres ikke.

Der findes fire fulde figurer i resultatarkivet: FRAME_MAPPING_AND_PRIMARY_CONTRAST.png, BARYCENTRIC_SIGNED_PROFILES6.png, ALL24_SIGNED_CONTRAST_RATIOS.png og FULL_CONTEXT_IN_BOTH_FRAMES.png. Samme arkiv indeholder alle 48 profiler, alle 24 par, de lineære vægte, kode, metodeversioner og input til reproduktion.

## Fortsættelse

Næste foreslåede skridt, D043, er en afgrænset metadataundersøgelse efter yderligere, uafhængige optagelser af den samme kendte stjerne tæt på 5. marts 2021. De fem allerede undersøgte epoker skal identificeres som eksisterende data. Forslaget er ét mål, ±30 dage, højst 25 katalogrækker og højst to metadataforespørgsler; ingen nye spektre eller råbodies i metadatafasen. Query, rækkefølge, grænser og beholdningsregler skal fastlægges før forespørgslen. Dette var det foreslåede næste skridt ved D042-afslutningen. D043 blev derefter gennemført i samme arbejdspas: 14 katalogrækker, fem klare ekstra metadatakandidater og syv uafklarede navne. Se den separate D043-rapport i dette resultatarkiv.

Den gamle 141-råkø er lukket; old90/Rubin er fortsat stoppet. Offentlig upload er udskudt. Ingen baggrundsanalyse kører efter afslutningen, og der er ingen udgifter eller eksterne henvendelser. Samlet status: 0 kvalificerede lasere og alle tre oprindelige fysiske årsager uafklarede.

## Kilder til bølgelængdekonventionen

- [Bertaux m.fl., TAPAS, A&A 564 A46 (2014), ligning 1](https://www.aanda.org/articles/aa/pdf/2014/04/aa22383-13.pdf): fortegn og barycentrisk bølgelængdestrækning.
- [Dumusque, A&A 620 A47 (2018), afsnit 3.2](https://www.aanda.org/articles/aa/pdf/2018/12/aa33795-18.pdf): HARPS-ordrer i observatørrammen, egen BERV og særskilt stellar-RV-korrektion.
- [ESO HARPS-produktbeskrivelse, 15. maj 2024](https://support.eso.org/en-US/kb/articles/harps-how-to-get-the-pipeline-generated-files-ccf-s1d-e2ds-bis-int-guide) og [legacy DRS-manual, issue 1.0, 2003](https://www.eso.org/sci/facilities/lasilla/instruments/harps/doc/DRS.pdf).

De to artiklers relevante, indekserede primærkildeuddrag er hentet; direkte PDF-hentning gav 403, og fulde PDF-tekster blev ikke anvendt. Egne 2021-headers og den gemte D022-konvention kontrolleres separat. Nyere HARPS-pipelinekonventioner bruges ikke som erstatning for disse HARPS_3.8-produkter. Se PRIMARY_SOURCES.json.


---

# SETI D043 — afgrænset katalogtjek efter flere kontroloptagelser

11. november 2026. Dette metadataarbejde fortsætter direkte fra den lokale, afsluttede D042-analyse; begge faser gemmes samlet fra projektversion 47.

**Kataloget returnerede 14 rækker i det fastlagte område og tidsrum.** To er de kendte E03/E04-optagelser. Fem yderligere rækker opfylder de fastlagte metadataregler med navnet HD 43629; ingen af disse fem findes i den oprindelige 54-eksponeringsgruppe eller 141-kandidattabel. Syv rækker har navnet TOI-880 og beholdes som uafklarede navne-/identitetstilfælde. Der er ikke hentet eller analyseret nye spektre, og katalogposter alene er ikke verificerede fysiske råidentiteter.

## Fastlagt forespørgsel

Plan og kode blev låst før to read-only-forespørgsler til ESOs ivoa.ObsCore: én optælling og én kronologisk liste med højst 25 rækker. Begge lykkedes; optællingen gav 14, og alle 14 rækker blev modtaget. Der var ingen genforsøg, sideinddeling eller udvidelse efter resultatet.

Filtrene var HARPS, overlap med ±30 dage omkring 2021-03-05T00:22:15.030 UTC, og en cirkel på 10 buesekunder omkring RA 94,165202°, Dec −13,98512°. Katalogtider, koordinater, eksponering, bølgelængdedækning, enkeltobservation og kanonisk målnavn blev kontrolleret. Udvælgelse er efter tid, ikke efter SNR eller et set signal. Se METADATA_PLAN.json og METADATA_LOCK.json.

| Observationsstart, UTC | Katalognavn | Klassifikation | I tidligere 54-gruppe |
|---|---|---|---|
| 2021-03-02T00:43:28.824+00:00 | HD  43629 | ADDITIONAL_METADATA_CANDIDATE | Nej |
| 2021-03-04T01:59:35.557+00:00 | HD  43629 | ADDITIONAL_METADATA_CANDIDATE | Nej |
| 2021-03-05T00:22:15.030+00:00 | HD  43629 | KNOWN_EXISTING_EPOCH | Ja |
| 2021-03-06T01:16:40.899+00:00 | HD  43629 | ADDITIONAL_METADATA_CANDIDATE | Nej |
| 2021-03-07T00:54:07.878+00:00 | HD  43629 | ADDITIONAL_METADATA_CANDIDATE | Nej |
| 2021-03-08T01:19:40.978+00:00 | HD  43629 | ADDITIONAL_METADATA_CANDIDATE | Nej |
| 2021-03-09T01:17:26.087+00:00 | HD  43629 | KNOWN_EXISTING_EPOCH | Ja |
| 2021-03-13T01:13:08.584+00:00 | TOI-880 | AMBIGUOUS_OR_INELIGIBLE_RETAINED | Nej |
| 2021-03-14T01:02:06.383+00:00 | TOI-880 | AMBIGUOUS_OR_INELIGIBLE_RETAINED | Nej |
| 2021-03-15T01:11:45.359+00:00 | TOI-880 | AMBIGUOUS_OR_INELIGIBLE_RETAINED | Nej |
| 2021-03-17T01:07:49.403+00:00 | TOI-880 | AMBIGUOUS_OR_INELIGIBLE_RETAINED | Nej |
| 2021-03-18T00:56:39.228+00:00 | TOI-880 | AMBIGUOUS_OR_INELIGIBLE_RETAINED | Nej |
| 2021-03-21T01:04:03.597+00:00 | TOI-880 | AMBIGUOUS_OR_INELIGIBLE_RETAINED | Nej |
| 2021-03-23T00:34:55.248+00:00 | TOI-880 | AMBIGUOUS_OR_INELIGIBLE_RETAINED | Nej |

De syv TOI-880-rækker afvises ikke som fysisk andre stjerner; identiteten er blot ikke verificeret under denne fases faste navnekrav. Alle rækker bevares. Der er ikke foretaget et efterfølgende aliasopslag eller ændret på reglen.

## Konkrete næste kontroller

Den nærmeste, klare metadatakandidat på hver side af signaloptagelsen blev valgt efter den på forhånd fastlagte tidsregel:

- BEFORE: `ADP.2021-03-05T01:11:43.795`, observeret 2021-03-04T01:59:35.557+00:00.
- AFTER: `ADP.2021-03-07T01:02:15.648`, observeret 2021-03-06T01:16:40.899+00:00.

Disse er optagelser fra 4. og 6. marts 2021. Datoen i et ADP-produkt-ID er produktets arkividentifikator og skal ikke forveksles med observationsdatoen. Kandidaternes egne raw-progenitorer, instrumentindstillinger, geometri, faktisk flux og spektrale overskud er endnu ikke verificeret.

## Dækning og begrænsninger

Tidsreferencen i det låste script er kandidatens midttid relativt til originalens starttid. En supplerende kontrol med også originalens midttid giver præcis de samme to valg; ingen forespørgsel, klassifikation eller udvælgelse er ændret. Se TIME_REFERENCE_AUDIT.json.

Forespørgslen er fuldstændig inden for de fastlagte filtre: 14 optalte og 14 modtagne rækker. Den er ikke en fuldstændig navne-/aliasoversigt for HD 43629. To tidligere kendte optagelser i tidsrummet, E01/E02, har gemte koordinater lidt uden for 10-buesekunderskeglen, og E05 ligger uden for tidsrummet. Dette bevares eksplicit i PRIOR_MEMBERSHIP_AND_COVERAGE_AUDIT.json; keglen blev ikke udvidet efterfølgende.

Medlemskab er kontrolleret særskilt mod den tidligere 54-eksponeringsgruppe og 141-kandidattabel. De fem klare ekstra rækker er nye i forhold til disse to afgrænsede datasæt. Det er ingen påstand om en ny teleskopobservation i dag, en ny opdagelse eller garanteret uafhængighed af instrumentelle systematikker.

En separat kontrol genlæste de originale CSV-svar, verificerede hashes, alle 14 koordinater/klassifikationer, den kronologiske rækkefølge og begge valg af nærmeste tidsnabo. Kontrollen består. D042s resultater er uændrede, og de tidligere tabellers 57.265 felter er bevaret med nye D043-kolonner tilføjet.

Næste foreslåede D044 er en separat fastlagt header- og proveniensport for de to udvalgte produkt-ID'er. Der skal verificeres identitet, mode og præcise relationer før nye fluxdata. D044 er endnu ikke fastlagt eller udført. Ingen udgifter, eksterne henvendelser eller baggrundsarbejde. Den gamle 141-råkø, old90 og Rubin genstartes ikke. Offentlig upload er udskudt. Status er fortsat 0 kvalificerede lasere og alle tre oprindelige fysiske årsager uafklarede.
