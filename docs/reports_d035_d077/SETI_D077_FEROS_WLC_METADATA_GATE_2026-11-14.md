# SETI D077: metadata- og proveniensgate for FEROS' 30 bølgelængdekalibreringer

**14. november 2026. Aktuelt fortsættelsespunkt: D077.** Stjerne: HD 43629 (`TIC34077285`), de fem faste FEROS-epoker fra 4., 7., 8., 10. og 14. november 2019 (`F1`–`F5`) og de tre kendte kandidatpositioner (`D002-0061`, `D002-0063`, `D002-0071`). Grundlag: verificeret D076-checkpoint (version 2 af aktiv pointer, 105.681 tabelceller). **0 FITS-billedkroppe hentet, 0 kalibreringspixelarrays læst, 0 nye science- eller fiber-2-fluxarrays læst.**

## Hovedresultat

Samtlige **30 deklarerede WLC-råreferencer** (`ESO PRO REC1 WLC RAW1..6 NAME`, 6 pr. epoke på tværs af `F1`–`F5`) er lokaliseret og verificeret i ESO's offentlige arkiv (`dbo.raw`, `archive.eso.org/hdr` og `DataLink`) under en prospektivt låst protokol (`73/73` HTTP 200-svar, `790.968` bytes ren tekst/XML/HTML-metadata, `0` fejl eller afskæringer). Alle **30/30 arkividentiteter** stemmer eksakt overens mellem pipeline-opskriftens filnavn, `dp_id`, `dbo.raw`, headerens `ARCFILE`/`ORIGFILE` og DataLink `#this`, og alle 30 råfiler er offentligt frigivet uden proprietær spærring (`release_date = exp_start` i november 2019; ~5,6 MB pr. råfil).

Samtidig dokumenterer gaten tre afgørende fysiske og arkivmæssige vilkår, som styrer enhver videre bølgelængde- eller referencerammekontrol:

1. **Identisk CCD-udlæsning, men dagslys-kalibrering 9,18–11,93 timer før stjernen og ændret filter/fiber-optik:** Alle **49 faste detektor-, udlæsnings- og vindueskort** (`CCD-60` / `EEV CCD-44`, `2148 × 4096` inkl. prescan/overscan, `1 × 1` binning, `R 225Kps Low Gain`, `Fast`, hoved-CCD `TLM1 = 138,0 K`) er eksakt identiske mellem de 30 WLC-råbilleder og de 5 natlige science-råbilleder (`CONAD = GAIN = RON = 0,0` er pladsholdere i begge). Hver WLC-sekvens består af tre skabelontrin inden for samme dagslys-observationsblok (`910-StanCal-norm`): `2 × 30,04 s` (de 2 første af en `20 × 30 s`-serie), `2 × 150,04 s` og `2 × 300,04 s` med `ThAr+Ne`-lampen (`LAMP3`) belyst gennem **begge fibre uden dæmpning** (`CALMIRR1 = SHUT1 = BOTHFIBS`, `FILT1 POS = 0,0`), optaget **9,18 til 11,93 timer før** den tilhørende `500,04 s` science-optagelse, hvor `LAMP3` kun sendes i **fiber 2 med neutraldæmpning `ND = 1,301`** (`CALMIRR1 = SHUT1 = SKYFIB`).
2. **Ingen offentlige afledte `MASTER_WAVE`-tabeller eller linjelister i ESO's arkiv:** Positiv kontrol i `ivoa.ObsCore` genfinder alle `5/5` science ADP-produkter, men returnerer **0 rækker** for de fem deklarerede master-bølgelængdeløsninger (`ThArNe0121`, `ThArNe0326`, `ThArNe0396`, `ThArNe0539`, `ThArNe0857`) og **0 rækker** for WLC-råfilerne. DataLink for både science- og WLC-råfiler udstiller ingen `#calibration`-links, og de lokale D067 science-TAR-pakker indeholder hverken `ThArNe*`-polynomier eller atomare linjelister. Desuden bekræfter ESO's officielle FEROS Phase 3-dokumentation (`releaseDescriptions/94`, 15.02.2023), at den simultane fiber-2-lampe i `OBJECT,WAVE`-optagelser **ikke anvendes** af den automatiske `fern/1.0`-reduktion, og at de blå kalibreringsordener kan have lavt S/N og falde tilbage til en gæt-session.
3. **Manglende `TIMESYS`, manglende QC-enheder og uændrede kandidattal:** `TIMESYS` mangler i samtlige `35/35` rå FITS-headere (`MISSING_NOT_ASSUMED_PROVEN`), `BUNIT` mangler på råbillederne, lampeslots `LAMP1`, `LAMP2` og `LAMP4` mangler i alle headere og fastholdes som `MISSING_UNKNOWN` (`0` imputerede `OFF`-tilstande), og enhederne på `ESO PRO REC1 WLC QC`-skalarerne er fortsat ikke uafhængigt fastlagt. **Ingen kandidatstatistikker eller kildearrays er ændret. 0 kvalificerede lasersignaler; alle tre kandidatpositioners fysiske oprindelse er fortsat uafklaret.**

## Metode og prospektiv låsning

Før nogen arkivforespørgsel mod de 30 kalibreringseksponeringer blev sendt, blev kode, nøjagtig forespørgselsliste, bytegrænser, retry-politik og fortolkningsregler låst i `METHOD_LOCK.json` (`35.481` B, SHA-256 `2b9c8d8c54b283cb1e1e225cc3dd4ec47b6651c5b76853d0949393f903f319ea`, `45` låste inputfiler, `archive_responses_present_at_lock = false`). De 30 WLC-navne var på forhånd kendt fra `D073/EPOCH_CONTEXT5.json` og `D076/PROPOSED_WLC_INPUTS30.json`; gaten er derfor en prospektiv metadata- og proveniensgate uden filtrering eller cherry-picking efter kvalitet, ikke en blind detektionstest.

De **73 låste metadataforespørgsler** bestod af:
- 3 TAP/ADQL VOTable-forespørgsler mod `https://archive.eso.org/tap_obs/sync`: alle 30 WLC `dp_id` i `dbo.raw`, de 5 faste science-rå `dp_id` i `dbo.raw` til skema-identisk sammenligning, samt kontrol af 5 science ADP-ID'er + 30 WLC-ID'er + 5 `ThArNe*`-navne i `ivoa.ObsCore`.
- 30 primære FITS-headere via `https://archive.eso.org/hdr?<wlc_dp_id>` og 30 DataLink-VOTables via `https://archive.eso.org/datalink/links?ID=ivo://eso.org/ID?<wlc_dp_id>` (med bogstavelige koloner i `<dp_id>`).
- 5 tilsvarende rå FITS-headere og 5 DataLink-VOTables for de faste science-ankre (`FEROS.2019-11-04..14`), hvilket gør sammenligningen af samtlige rå `ESO DET *`- og `ESO INS *`-kort 100 % selvbærende uden download af den 382 MB store D067-råpakke.

Første arkivkald startede efter `LOCK_RECEIPT.json` (`lock_precedes_first_request = true`). Alle 35 rå primærheadere (`8.225` tildelte FITS-kort; `221` pr. WLC-fil og `319` pr. science-fil; `0` linjer over 80 tegn) og alle 38 VOTables (`2.480` tabelceller) blev parset uden fejl. For de 5 science-råheadere stemte samtlige `24/24` tidligere gemte D072-skalarer eksakt overens (`5/5`).

## De fem kalibreringskæder (`F1`–`F5`)

| Kæde | Science rå-ID (`OBJECT,WAVE`) | Deklareret `MASTER_WAVE` | Verificerede WLC råfiler | Forspring før science | Eksponeringsstige (`RAW1..6`) | Bevaret QC Fib1 `NLINSEL/ALL` (`RMS`*) | Bevaret QC Fib2 `NLINSEL/ALL` (`RMS`*) |
| --- | --- | --- | :---: | ---: | --- | ---: | ---: |
| F1 | `FEROS.2019-11-04T07:39:37.310` | `ThArNe0121` | 6 / 6 | 11,23–11,89 t | 2×30,04 + 2×150,04 + 2×300,04 s | 790/796 (0,0048) | 819/827 (0,0068) |
| F2 | `FEROS.2019-11-07T07:46:17.029` | `ThArNe0326` | 6 / 6 | 11,27–11,93 t | 2×30,04 + 2×150,04 + 2×300,04 s | 789/797 (0,0065) | 829/832 (0,0058) |
| F3 | `FEROS.2019-11-08T06:31:09.737` | `ThArNe0396` | 6 / 6 | 10,17–10,83 t | 2×30,04 + 2×150,04 + 2×300,04 s | 796/801 (0,0046) | 827/831 (0,0056) |
| F4 | `FEROS.2019-11-10T05:01:01.524` | `ThArNe0539` | 6 / 6 | 9,18–9,85 t | 2×30,04 + 2×150,04 + 2×300,04 s | 788/793 (0,0050) | 829/832 (0,0058) |
| F5 | `FEROS.2019-11-14T06:29:26.536` | `ThArNe0857` | 6 / 6 | 10,81–11,48 t | 2×30,04 + 2×150,04 + 2×300,04 s | 802/806 (0,0049) | 831/835 (0,0058) |

*\*Bemærk: Enheder på `WLC QC LINE RESID*` er ikke angivet i FITS-kommentarer eller i ESO's Phase 3-dokumentation (`unit_not_independently_established = true`) og må ikke tolkes som fysisk hastighedspræcision, stjerne-RV eller støjkovarians.*

I hver af de fem kæder afvikles de 6 deklarerede WLC-råfiler i nøjagtig samme mønster under standardblokken `OBS NAME = 910-StanCal-norm` (`PROG ID = 60.A-9700(A)`):
1. **`RAW1`–`RAW2` (`~30,04 s`):** Eksponering nr. 1 og 2 af en skabelon med `TPL NEXP = 20` (`FEROS ThAr+Ne wavelength calibration (20 x 30 s`), adskilt af ~83 s. Derefter følger et interval på `1.554–1.560 s` (~26 min), svarende til de øvrige ~18 korte eksponeringer i `20 × 30 s`-serien, som ikke indgår i `WLC RAW1..6`.
2. **`RAW3`–`RAW4` (`~150,04 s`):** Eksponering nr. 1 og 2 af en ny skabelon (`TPL NEXP = 2`, ~201 s start-til-start).
3. **`RAW5`–`RAW6` (`~300,04 s`):** Eksponering nr. 1 og 2 af en tredje skabelon (`TPL NEXP = 2`, ~352 s start-til-start), der giver tilstrækkeligt signal i svagere thoriumlinjer uden at mætte de kraftige linjer fra de korte eksponeringer.

Denne tretrinsstruktur forklarer samtidig de to formelle forskelle mellem `ESO PRO REC1 WLC`-opskriften på science-produkterne og de enkelte WLC-råheadere: `PRO REC1 WLC TPL NAME` lagrer skabelon-ID'et `FEROS_ech_cal_ThAr_Ne` (eksakt match med `ESO TPL ID` på `30/30`), ikke den beskrivende `ESO TPL NAME`-tekst, og `PRO REC1 WLC TPL START` lagrer kun ét skabelon-starttidspunkt pr. kæde — nemlig starttidspunktet for første skabelon (`RAW1`–`RAW2`, eksakt på `10/30`), mens `RAW3`–`RAW6` bærer deres egne efterfølgende `TPL START` (`20/30`), alle inden for eksakt samme `OBS START` (`30/30`).

## Sammenligning af instrument, detektor, tidsskala og belysning

| Egenskab | 30 dagslys-WLC råfiler (`RAW1..6`) | 5 natlige science råfiler (`F1`–`F5`) | Konsekvens for proveniens |
| --- | --- | --- | --- |
| `DPR CATG / TYPE / TECH` | `CALIB / WAVE / ECHELLE` (`30/30`) | `SCIENCE / OBJECT,WAVE / ECHELLE` (`5/5`) | Samme echelle-modus (`ESO INS MODE = FEROS`). |
| Faste CCD- og udlæsningskort | `49/49` kort identiske (`CCD-60`, `2148×4096`, `1×1`, `Fast`, `R 225Kps Low Gain`, `TLM1 = 138,0 K`) | Samme `49/49` kort | Ingen forskel i detektorgeometri, binning eller udlæsningsclock. |
| Afvigende `ESO DET`-kort (`9` kort) | `UIT1 = 30/150/300 s`, `DIT1`, `DKTM`; `TLM2..4` afviger `0,1–0,2 K` | `UIT1 = 500 s`, `DIT1`, `DKTM`; `TLM2..4` inden for `0,1–0,2 K` | Kun planlagt eksponeringstid og lille passiv sensordrift. |
| Rå støjparametre / `BUNIT` | `CONAD = GAIN = RON = 0,0`; `BUNIT` mangler | `CONAD = GAIN = RON = 0,0`; `BUNIT` mangler | Ingen kalibreret foton-/udlæsningskovarians i råheaderne (`SDP ERR = NaN`). |
| Kalibreringsspejle og lukker | `CALMIRR1 = BOTHFIBS`, `SHUT1 = BOTHFIBS`, `CALMIRR2 = LAMP3` | `CALMIRR1 = SKYFIB`, `SHUT1 = SKYFIB`, `CALMIRR2 = LAMP3` | Dagslys-WLC belyser nominelt begge fibre; natlig `OBJECT,WAVE` kun fiber 2. |
| Neutraldæmpning (`FILT1 POS`) | `0,0` (encoder `1932`, udæmpet) | `1,301` (encoder `7701`, faktor ~20 dæmpning) | Tilpasset hhv. korte/mellemlange kalibreringer og `500 s` simultan eksponering. |
| Foldespejl `ESO INS MIRR3 NAME` | `WFI` (`30/30`, intern kalibrering) | `FEROS` på `F2`; `ERROR` på `F1, F3, F4, F5` | Dokumenteret telemetri-statusflag på M3-sensoren; påvirkede ikke stjernefluxen, men bevares eksplicit. |
| Lampeetiketter (`LAMP1..4`) | `LAMP3 = ThAr+Ne` (`ST = T`); `LAMP1, 2, 4` mangler (`MISSING_UNKNOWN`) | `LAMP3 = ThAr+Ne` (`ST = T`); `LAMP1, 2, 4` mangler (`MISSING_UNKNOWN`) | Manglende lampeslots antages aldrig `OFF`; header er nominel kommando, ikke fotonbevis. |
| `TIMESYS` og betinget UTC-tjek | `TIMESYS` mangler (`0/30`); maks. \|`DATE-OBS` − `MJD-OBS`\| = `1,14 ms` under betinget UTC | `TIMESYS` mangler (`0/5`); `dp_id` − `DATE-OBS` ≤ `1,00 ms` | Tidsskala antages ikke bevist fra header alene (`MISSING_NOT_ASSUMED_PROVEN`). |

## Betydning for de tre faste kandidatområder

Alle tre kandidatområder ligger i **barycentriske luftbølgelængder (`Å`)**, hvor én observatør-barycentrisk korrektion (`ESO DRS BARYCORR` i intervallet `16,3340` til `19,0142 km/s`) allerede er påført af `fern/1.0`. Der må aldrig påføres en ekstra barycentrisk korrektion, og ESO's egen dokumentation påpeger begrænset præcision i `ESO DRS BARYCORR` (~1 års periodicitet; Müller et al. 2013) samt op til ~2 bueminutters `RA/DEC`-afvigelse (allerede dokumenteret mod `ESO TEL TARG ALPHA/DELTA` i D066/D072).

- **`D002-0061` (`6550,095 Å`, HDU 0, 29 og 30; to overlappende røde ordener):** D075–D076 viste her den største protokolafhængighed (op til `1,45 km/s` mellem enkeltorden og samlet spektrum, `1,35 km/s` mellem rødt og blåt sidebånd og `0,95 km/s` frem/tilbage-afvigelse). D077 fastslår, at en uafhængig kontrol af ordens-bølgelængdeskalaen i HDU 29 og 30 ikke kan hentes fra offentlige `ThArNe*`-tabeller, men kræver en særskilt låst numerisk gate på enten eksisterende spektre med et låst linjekatalog, de allerede arkiverede simultane `OBJECT,WAVE` fiber-2-produkter i D067, eller selve WLC-råbillederne. Alle historiske flag bevares (`D018_original_D016_rho = 0.7806562435869904 < 0.8`, sample-midtpunktsafrunding og 6. marts 2021 sekundær HARPS-gruppe).
- **`D002-0063` (`4826,6475 Å`, HDU 0 og 17; én enkelt orden):** Enkeltordenen og det samlede SDP-spektrum duplikerer de samme rebinnede data (`0,0` SSE-forskel i D075–D076). ESO's Phase 3-beskrivelse fremhæver netop, at de blå kalibreringsordener i FEROS kan lide af lavt lampe-S/N og falde tilbage til en gæt-session, når for få linjer findes; hvor tæt HDU 17 faktisk er forankret i isolerede `ThAr+Ne`-linjer kan først afgøres under en separat låst pixel-/linjeliste-gate. Den uvaliderede blå HARPS LFC/COMB-status fra D036 bevares uændret.
- **`D002-0071` (`5730,715 Å`, HDU 0, 24 og 25; to overlappende ordener):** Kalibreret alene via den foregående eftermiddags `ThArNe*`-løsning i automatisk `fern/1.0`, mens de simultane `OBJECT,WAVE` fiber-2-data forbliver ubrugte i standardreduktionen. De historiske D033/D055–D056 rumlige og linjemæssige forbehold bevares uændret.

## Uafhængig efterregning, sub-ULP-revisionskvittering og tilstandsbevaring

Den uafhængige stdlib-only kontrol parser samtlige **38 VOTables (`2.480` celler)** med `xml.dom.minidom`, samtlige **35 rå FITS-headere (`8.225` tildelte kort)** med en selvstændig regex/slice-parser og efterregner alle **115 tidsdifferencer** i 50-cifret `Decimal`-aritmetik samt alle 45 låste input-hashes og alle 73 rå arkivsvar-hashes.

Under første kørsel af den låste `audit.py` passerede alle 45 input-hashes, alle 73 svar-hashes, alle 2.480 VOTable-celler og alle 8.225 FITS-kort, hvorefter linje 292 udløste en teknisk tærskel-assertion (`1e-7 s`) på differencen mellem IEEE-754 `binary64` MJD-subtraktion og `Decimal(str(mjd))`. Ved `MJD ≈ 58791` (`∈ [2^15, 2^16)`) er **1 IEEE-754 `binary64` ULP eksakt `2^-37 døgn = 6,286427 × 10^-7 s`** (`6,286427 × 10^-4 ms`) — næsten 1.000 gange finere end FITS-headerens egen opløsning på `10^-8 døgn = 8,64 × 10^-4 s`. Den observerede afrundingsforskel var højst `5,8166 × 10^-7 s` (`< 1,0 ULP`), og eksakt `binary64` Sterbenz-subtraktion via `Decimal.from_float` har afvigelse **`0,0 s`**. I overensstemmelse med projektets transparensregler er den oprindelige `audit.py` bevaret 100 % byte-uændret sammen med `INITIAL_AUDIT_FAILURE_RECEIPT.json` og `AUDIT_IMPLEMENTATION_AMENDMENT.json`, og `audit_ulp_exact.py` bekræfter `NUMERICAL_AUDIT.json = PASS` (`verify.py --recompute` består for både D075, D076 og D077).

Alle **105.681 tidligere tabelceller** fra D076 (og alle **102.833 celler** fra D074) er bevaret eksakt i samme `37 + 141` rækker; tilføjelsen af 8 `D077_*`-kolonner bringer totalen på **107.105 celler**. Næste fase (**D078**) er kun beskrevet som afgrænsede muligheder i `NEXT_ACTION.json` og er hverken låst eller påbegyndt.

**0 kvalificerede lasersignaler; alle tre kandidatpositioners fysiske oprindelse er uafklaret.** Ingen downloadede FITS-kroppe, ingen læste kalibrerings- eller nye science-pixelarrays, ingen ændrede kildearrays, ingen udgifter, ingen eksterne kontakter og ingen kørende baggrundsjobs. Den gamle 141-råkø forbliver lukket, 90-/Rubin-sporene er stoppet, og den tidligere afviste offentlige 663-fil-upload er ikke forsøgt gentaget.
