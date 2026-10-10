# SETI: fast frekvens og otte nye driftsøgningsfelter

**10. oktober 2026.** To afgrænsede analyser er gennemført én gang efter offentlig fastlåsning. Den tidligere stærke linje ved **1426,282128 MHz** er tydelig i alle seks scanninger, også de tre OFF-scanninger. Otte nye delbånd tilføjer **32.768 undersøgte referencekanaler pr. ON-scanning**. Den samlede sparsomme driftsøgning dækker nu **163.840 kanaler pr. ON, svarende til 15,625 %** af det gemte frekvensudsnit. De ni nye udvalgte profiler forbliver uafklarede.

Alle scanninger stammer fra samme besøg den 17. marts 2016. Betegnelserne `epoch1/2/3` er scanningsnavne. Der er ingen nye observationer eller nye teleskopdownloads i denne aktivitet. Arbejdet er eksplorativt; A/B forbliver FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og tidligere holdouts er fortsat lukkede.

## Den fælles stationære linje

Den faste native kanal `158766416` blev valgt fra den allerede offentliggjorte ON2-profil med nul drift og bredde én kanal. De samme 21 fysiske kanaler, alle seks scanninger og alle 16 tidsrækker blev udtrukket fra ni gemte driftudklip. Alle ni kopier af både rå og normaliserede celler var byte-identiske. Sammenligningen bruger én fælles baggrund: rækkens median af 14 faste kanaler med absolut kanalafstand større end tre inden for ±10 kanaler.

| Scanning | Fast centrum, bredde 1 | Fast centrum, bredde 3 | Positive rækker, begge bredder |
| --- | ---: | ---: | ---: |
| ON1 | 1,329333 | 0,832037 | 16/16 |
| OFF1 | 1,553348 | 0,836950 | 16/16 |
| ON2 | 1,561473 | 0,891072 | 16/16 |
| OFF2 | 1,367921 | 0,862467 | 16/16 |
| ON3 | 0,990075 | 0,867187 | 16/16 |
| OFF3 | 1,136054 | 0,859101 | 16/16 |

Tallene er middelværdier af normaliseret centereffekt minus den faste baggrund. De er ikke kalibreret SNR eller flux. For de syv tidligere udvalgte profiler med drift forskellig fra nul er den faste reference større end driftsporets centrum i alle **21 OFF-sammenligninger**, med middelforskelle fra **0,511981 til 0,874247**. Det understøtter, at små værdier på disse ekstrapolerede driftspor kan skyldes, at sporene forlader en stationær linje, som stadig findes i OFF-data. Det fastslår ikke linjens fysiske oprindelse.

De ni profiler er nært beslægtede varianter omkring samme område. De 54 sammenligninger er afhængige beskrivelser, ikke 54 uafhængige forsøg. De oprindelige profiler med baggrund i ±64 kanaler bevares separat; deres middelværdier må ikke direkte sammenblandes med den nye 14-kanals baggrund. Bredde 5 og 9 er supplerende, afhængige beskrivelser; bredde 9 overlapper baggrundskanalerne ved ±4.

Se [den detaljerede ankerrapport](RADIO_DRIFT_ANCHOR_REPORT_2026-10-10.md) og [alle tal](results/radio_drift_anchor_20261010/measurement/DRIFT_ANCHOR_RESULT.json).

## Ny søgedækning

Otte metadata-valgte felter på hver 4.096 referencekanaler ligger mellem de tidligere 32 felter. De nye referencekanaler er indbyrdes disjunkte og overlapper ingen tidligere referencekanaler. Læse- og sporhaloer kan overlappe. Tilføjelsen svarer til **92.913,776 Hz kanalbredde pr. ON-scanning**, fordelt over otte adskilte felter; den er ikke ét sammenhængende bånd.

Den uændrede detektor søgte 763 lineære drifthastigheder fra −4 til +4 Hz/s ved bredde 1 og 3, altså 1.526 hypoteser pr. referencekanal. Alle **24 scanningsfelter** blev færdige. Hvert felt gemmer alle 4.096 maksimale scores, vindende drift og bredde samt gyldige hypoteseantal. Top-20-listen for hver af tre ON-scanninger bruger den tidligere afstandsundertrykkelse på tre kanaler. De tre højeste pr. ON blev derefter projiceret ved uændret frekvens, drift og bredde i alle seks scanninger: **ni profiler, 54 scanningsprofiler og 864 tidsrækker**.

De ni udvalgte ON-profiler har middelresidualer **0,089249–0,169044**, positive første og sidste halvdele og **13–16 positive rækker**. Det eksakte spor i den efterfølgende OFF-scanning med samme `epoch`-etiket har middelresidualer **−0,028865–0,046200**. De øvrige scanninger, inklusive forudgående OFF-kontroller, er også bevaret i de seks-scanningsprofiler. De robuste udvælgelsesscores ligger mellem **5,544223 og 5,982187**. Scores og positive rækker er efter udvælgelse og har ingen kalibreret sandsynlighedsfortolkning.

Små værdier ved det præcist forudsagte OFF-spor fastslår ikke, at et nærliggende OFF-signal mangler. Der er ikke anvendt et kvalificeret OFF-veto eller beregnet falskalarmrate. Ingen af de ni profiler udnævnes til et himmelsignal. De tidligere stationære profiler og de oprindelige 32 søgefelter ændres ikke.

Se [den detaljerede rapport om de nye felter](RADIO_GAP_DRIFT_REPORT_2026-10-10.md), [top-20-listerne](results/radio_gap_drift_20261010/measurement/DRIFT_TOP20.json) og [de ni komplette profilbeskrivelser](results/radio_gap_drift_20261010/measurement/FIXED_TOP3_PROFILES.json).

[Figuren med alle seks scanningsmidler](results/radio_signal_followup_20261010/figures/GAP_FIXED_PROFILE_MEANS.png) viser kontrolkonteksten for alle ni profiler. [Tidsrækkerne i origin-ON og den efterfølgende OFF](results/radio_signal_followup_20261010/figures/GAP_ORIGIN_PAIRED_OFF_ROWS.png) viser alle 16 rækker for hvert af de to udvalgte scanningsforløb; forudgående OFF-kontroller for ON2 og ON3 er fortsat med i den første figur og de komplette profilfiler.

## Fastlåsning, kontrol og ressourcer

Kode og scopes blev offentliggjort i commit `ada64c4d46ead59b92f8e65ae2ce6aa4d13d0759` og læst tilbage med eksakt indholdskontrol før nogen af de to numeriske kørsler. Begge havde uafhængig statisk gennemgang. Råindgange og tidligere kode er hashbundet. Resultater, kontrolkvitteringer, figurer og reproduktionsvejledning gemmes sammen med de ni gamle inputudklip i `SETI_SIGNAL_FOLLOWUP_2026-10-10.zip`. De seks større kompakte HDF5-inputfiler ligger i det tidligere gemte `SETI_FRESH_BAND151_RAW_2026-10-09.zip`, SHA256 `6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d`.

Den uafhængige resultatkontrol består for begge analyser. Ankerkontrollen verificerede 18 byte-identiske fysiske kopisammenligninger, 186 sekstenrækkes-sammenfatninger og 1.116 skalarmål. Kontrollen af de nye felter verificerede alle 98.304 gemte ON-kanalmaksima, alle 60 top-20-rangeringer samt ni råudklip og 54 profilsammenfatninger. Den kontrollerede 111.456 råceller og alle 864 profilrækker med faste koordinater, tider, normalisering og baggrund. Ingen af kontrollerne genkørte detektoren eller læste HDF5-kildedata. Se [ankerkontrollen](results/radio_drift_anchor_20261010/measurement/QA_RECEIPT.json) og [kontrollen af de nye felter](results/radio_gap_drift_20261010/measurement/QA_RECEIPT.json).

| Numerisk kørsel | CPU-sekunder | Vægtid, sekunder | Maksimal RSS, bytes | CPU-grænse |
| --- | ---: | ---: | ---: | ---: |
| Fast anker | 1,61992847 | 1,62417332 | 129.560.576 | 40 |
| Otte nye felter og ni profiler | 73,86158298 | 73,89685867 | 491.298.816 | 90 |

Der er reserveret **180 + 160 CPU-sekunder** til hele de to aktiviteter inklusive klargøring, kontrol, pakning og offentliggørelse. Tidligere reservationer beholdes uden tilbageførsel. Den godkendte samlede grænse er stadig **43.200 CPU-sekunder, 4 GiB RAM, 8 GiB arbejdsplads og 0 DKK**. Der resterer **62,705144981 CPU-sekunder**, heraf 60 som intern reserve til afsluttende kontrol. Målt CPU for enkelte processer er ikke en måling af hele aktiviteten.

Gendannelsen af tre tidligere gemte arkiver overførte 592.152.992 arkivbytes. Den eksakte tidligere HDF5-codec blev gendannet med 51.507.696 wheelbytes og 47.145 metadata-bytes. Det konservative samlede kilde-, gendannelses- og afhængighedsregnskab er **1.638.958.570 bytes**, under den godkendte grænse på 4,25 GiB. Teleskopets hidtidige kilde- og metadataregnskab for denne cadence er fortsat **611.429.683 bytes**; denne aktivitet tilføjede **0 teleskoprequests og 0 teleskopbytes**.

Der er ikke beregnet kalibreret SNR, falskalarmrate, flux, EIRP, følsomhed eller generaliseret nulresultat. Dataværdierne var allerede åbnet i tidligere stationært arbejde; fastlåsningen var forud for de nye driftresultater og er ikke blind validering. Der er fortsat ingen verificeret, optaget anden besøgsobservation i dette frekvensbånd.

Se [reproduktionsvejledningen](RADIO_SIGNAL_FOLLOWUP_REPRODUCIBILITY_2026-10-10.md) og [de to reservationer](results/radio_gap_drift_20261010/RESOURCE_LEDGER.json).
