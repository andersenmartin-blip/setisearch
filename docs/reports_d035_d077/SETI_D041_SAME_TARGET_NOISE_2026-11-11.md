# SETI D041 — kontrol af samme stjerne ved matchende flux

11. november 2026. Udgangspunkt: D040, gemt projektversion 46.

**Vi har nu en reel kontrol af samme stjerne ved næsten samme lysstyrke.** Optagelsen af HD 43629 fra 9. marts 2021 opfylder de fastlagte krav til instrumentfelter, egen sporingsgeometri og intensitet. Fluxen er 97.43 % af originalens. Den typiske støjspredning er omtrent som forventet, men kraftige referenceudsving og lokal korrelation gør fortsat den fulde model med uafhængig støj utilstrækkeligt valideret. Der er ingen ny fysisk klassifikation eller kvalificeret laser.

## Hvad der blev målt

D041 bruger kun den allerede gemte råfil HARPS.2021-03-09T01:17:26.087 med egne native A/B-spor- og bølgelængdeheaders. Det er samme stjerne, samme eksponeringstid på 1.799,9965 sekunder og samme relevante STAR,SKY-konfiguration som originalen HARPS.2021-03-05T00:22:15.030. Den anden optagelse rummer også den tidligere blå D002-0063-kontekst; her undersøges alene et kendt rødt støjvindue ved 655 nm. Den blå kandidats status ændres ikke.

Der er ikke hentet nye teleskopprodukter. Pool, geometri, fluxregel, støjgrene, seeds, sidebånd og beskrivende halediagnostik blev fastlagt i SCIENCE_METHOD_LOCK.json før de nye røde pixels blev målt. De tidligere native-headeroplysninger og D040-resultater var allerede kendte.

| Størrelse | Original, 5. marts | Kontrol, 9. marts |
|---|---:|---:|
| Median signed raw-r3 uden for centrale 41 samples, ADU | 3666.930 | 3572.845 |
| Flux i forhold til original | 100,00 % | 97.43 % |
| Målt postscan-støj, elektroner | 4.5150 | 4.5127 |
| Egen header-RON, elektroner | 7,07 | 7,07 |
| Median rumlig profiltop, pixels fra eget spor | 0,0 | 0.0 |
| Sammenlignelig intensitet efter fast regel | Reference | Bestået |

Kravet var en positiv median uden for centrale 41 samples og et forhold på 0,5–2,0 til originalen. Kravet blev ikke ændret. Der er **én matchende kontrol af samme stjerne fra en anden nat**. D040 har fortsat nul matchende kontroller af andre stjerner; de fire svage observationer bevares i deres egne grupper. Den nye kontrol er ikke en uafhængigt certificeret laserfri nulobservation.

## Egen geometri og genbrug af originalen

Det faste observer-air-vindue er 6550,573287171706 Å på egen A-ordre 67. Nærmeste native sample er 421, og alle 257 samples fra 293 til 549 beholdes. Der anvendes egne A72/B71-spor; native indeks k svarer til rå række 4095−k, og sporet evalueres ved samme argument. Referencerne ligger ved absolut sporafstand 10–14 eller 26–30 pixels og mere end 8 pixels fra alle egne A/B-spor. Alle rækker har 12 faste referencepixels og 6 pixels i radius3-aperturen. Der foretages ingen flytning af sporet.

Baggrunden er den samme repeated-median-estimator som i D040. Alle skiftevis sorterede referencepixels indgår også i to halvdele, hvis integrerede baggrundsforskel annullerer den fælles stjerneapertur. Egne 50 pre- og 50 postscan-kolonner beholdes; ingen kolonne eller ekstrem referencepixel fjernes.

Der er målt 16.705 nye røde råpixels og 25.700 overscan-pixels i kontrolkonteksten. Rå-HDU2 blev afkodet i fuld størrelse; kun de beskrevne spektroskopiske vinduer beholdes til analysen. Kontrolobservationens native fluxarrays er ikke læst eller brugt. Dens native headers bruges til koordinater og geometri. Originalens 257 rækker er genindekseret fra de allerede gemte D029- og D039-arrays; dens median og alle seks kontinuumcentralværdier reproducerer D040.

## Typisk støj ved den relevante intensitet

Der er gennemført to fastlagte grene med 1.000 simuleringer hver: egen header-RON og egen målte postscan-RON. Modellen, baggrundsgenestimeringen og kontraststatistikken er fra D040; D041 bruger særskilte PCG64DXSM-seeds [20261111,41,0,gren]. Alle 2.000 træk, input og resultater beholdes.

Fotonmiddelværdierne er plug-in-estimater fra den valgte optagelse. Modellen tilføjer uafhængig Poisson-støj i elektroner og analog Gauss-læsestøj. Egen bias holdes betinget fast. Referencebaggrunden løftes kun nok til ikke-negativ fotonforventning: i denne kontrol rammer det 58 rækker, højst 4,4675 ADU. Ingen aperture-fotonmiddelværdi kræver gulv. Hver simulering genestimerer både den fulde rumlige baggrund og begge referencehalvdele.

| Optagelse | Støjgren | Median simuleret raw-r3-støj, ADU | Målt robust anden-differens-spredning / MC | Robust reference-nabodifferens / modelskala |
|---|---|---:|---:|---:|
| 2021-03-05 original | HEADER_RON | 54.90 | 0.972 | 0.655 |
| 2021-03-05 original | OWN_OVERSCAN_RON | 53.41 | 0.991 | 0.987 |
| 2021-03-09 same-target control | HEADER_RON | 54.13 | 1.015 | 0.683 |
| 2021-03-09 same-target control | OWN_OVERSCAN_RON | 52.73 | 1.046 | 1.026 |

Stjerneaperturens robuste anden-differens-spredning er 1.015 gange den simulerede værdi med header-RON og 1.046 med egen postscan-RON. De typiske størrelser er altså omtrent som forventet ved næsten samme stjerneflux. Spektrallinjer og krumning kan dog bidrage; dette er ikke en isoleret elektronisk støjkalibrering. Originalens værdier i tabellen er uændrede D040-resultater, ikke nye simuleringer.

Referencepixel-differenser med egen postscan-RON har robust spredning tæt på en modelenhed. Header-RON overestimerer deres centrale spredning. Dette understøtter beskrivelsen af typisk støj i netop disse kontekster. Det validerer ikke modellens sjældne store udsving, den fulde fysiske kovarians eller en survey-falsk-alarm-rate.

## Store baggrundsudsving og korrelation

Alle referencepixels indgår i de samme fysiske kolonner ved lag 1–5; der sammenlignes ikke blot samme position i en skiftende reference-liste. Kontroloptagelsens ordinære lag1-korrelation er 0.474036. De største beskrevne udsving ligger ved native indekser omkring 382–387 og fysiske kolonner 3606–3609, uden for centrale 41 samples. Deres fysiske årsag er uafklaret.

| Støjgren | Reference-MAD | Reference-RMS | Maks. absolut nabodifferens | Antal over 5 | Antal over 10 |
|---|---:|---:|---:|---:|---:|
| HEADER_RON | 0.683 | 2.789 | 64.40 | 15 | 15 |
| OWN_OVERSCAN_RON | 1.026 | 3.572 | 87.39 | 16 | 15 |

Tallene er betinget variansnormaliserede beskrivelser, ikke kalibrerede gaussiske signifikansniveauer eller laser-sandsynligheder. Alle 3.060 reference-nabopar og de fastlagte beskrivelser over henholdsvis 3, 5 og 10 modellenheder er beholdt. Halediagnostikken og top10-reglen blev denne gang fastlagt før de nye røde pixels. Der er ingen efterfølgende klipning, maskeskift eller erstatningsobservation.

Korrelationerne i den filtrerede stjerneapertur er sammenlignet med præcis samme anden-differens-filter i Monte Carlo-modellen. Overlappende filtre skaber selv korrelation, også hvis inputrækkerne er uafhængige. Den observerede referencekorrelation og store udsving må ikke uden videre omdøbes til detektorens rene elektroniske kovarians.

Alle seks kontinuumvalg er beholdt: affine og kvadratiske sidebånd 5–7, 8–12 og 12–20 pixels. Kontrolobservationens centrale kontinuumspredning er 154.045 ADU mod originalens 132.805 ADU. Betingede noise-only-fordelinger er gemt, men der udpeges ikke bagefter et foretrukket kontinuum eller en fysisk fortolkning.

## Kontrol af beregninger og bevaring

Den separate implementering læser FITS-blokke uden Astropy og verificerer tre DATASUM-felter, beregner geometri med Horner-evaluering og kontrollerer alle 771 reelle samt 1.542.000 simulerede fulde/halve baggrundstilpasninger med SciPys kompilerede Siegel-estimator. Alle 12.000 simulerede kontinuumcentralværdier er genberegnet med QR. De 10 reference-lagbeskrivelser og 10.000 filtrerede MC-korrelationsværdier er kontrolleret separat. Kontrollen består. Det er separate algoritmer i samme arbejdssession, ikke ekstern fagfællebedømmelse.

De to eksisterende tabellers 54.417 tidligere felter er uændrede; D041 tilføjer alene egne kolonner. D039s 16 grene og 22.000 formtilpasninger, D040s 10.000 støjtræk og alle tidligere rådata, fejl og referenceudsving er bevaret.

Fire figurer findes i resultatarkivet: MATCHED_CONTROL_AND_NOISE.png, SAME_TARGET_SPECTRAL_CONTEXT.png, SAME_TARGET_COVARIANCE.png og SAME_TARGET_REFERENCE_EXCURSIONS.png. Resultatarkivet indeholder også alle målte kontekster, alle nye stokastiske input og kode. Projektpakkens COMPANION_REFERENCE.json angiver den præcise resultatfil og hash.

## Hvad det næste skridt kan afklare

D041 har undersøgt støj i et fast observer-air-vindue. Den har **ikke** gennemført en kilde-gentagelses- eller fraværstest. Det ville kræve eksplicit behandling af de egne bølgelængdeløsninger og BERV. Den foreslåede D042 vil derfor først fastlægge en målrettet sammenligning af den allerede kendte 0061-feature i både detektor- og stjerne/barycentrisk ramme med alle seks kontinuumvalg. Der skal ikke tilpasses en vilkårlig forskydning for at få spektrene til at ligne hinanden.

De røde kontekster og figurer er nu allerede set. En sådan D042-sammenligning bliver ikke en blind ny opdagelsestest. Metode og resultater for D042 er endnu ikke fastlagt eller udført; kun den afgrænsede fortsættelse er beskrevet i NEXT_ACTION.json.

Status: 0 kvalificerede lasere, alle tre oprindelige fysiske årsager uafklarede, ingen kalibreret FAP. Den tidligere 0061-kvalitetsfejl, rho 0,780656 < 0,8, består; den blå 0063-status ændres ikke. Den gamle 141-råkø er lukket, old90/Rubin fortsat stoppet, offentlig upload udskudt. Ingen baggrundsanalyse kører efter afslutningen; ingen udgifter eller eksterne henvendelser.
