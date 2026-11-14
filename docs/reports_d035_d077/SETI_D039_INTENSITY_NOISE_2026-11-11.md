# D039: lysstyrke, baggrund og støj i 0061-sammenligningen

11. november 2026. **16.000 fastlagte simuleringer viser, at lav lysstyrke ændrer den forventede profilscore markant. Resultatet er samtidig følsomt for baggrundens form. Med de tre affine baggrunde når 0/1000 simuleringer originalens R i hver gruppe; med de tre kvadratiske baggrunde er tallene 113/1000, 59/1000 og 26/1000. En efterfølgende positionsudvidelse ændrer ingen af disse seks tællinger.** Det er modelbetingede udfald, ikke en kalibreret falsk-alarm-sandsynlighed. 0061s årsag er fortsat uafklaret, den gamle kvalitetsfejl består, og kvalificerede laserfund er nul.

## De seks kildetilpassede støjkontroller

Hver gruppe har 1000 simuleringer. Alle grupper bruger den låste egen-A-COMB-profil fra D037. Intensitet, position og kontinuum er den pågældende baggrunds allerede kendte D038-fitværdier; de er indsat i modellen og er ikke uafhængigt målt på nye stjerneobservationer.

| Baggrund | Simuleret median R | Simuleret 95-percentil R | Originalens R | Antal R ≥ original, ±1 pixel | Samme antal, ±2 pixels |
|---|---:|---:|---:|---:|---:|
| 5_7_affine | 0.095491 | 0.189536 | 0.429001 | 0/1000 | 0/1000 |
| 5_7_quadratic | 0.147772 | 0.837281 | 0.555232 | 113/1000 | 113/1000 |
| 8_12_affine | 0.079577 | 0.151852 | 0.348779 | 0/1000 | 0/1000 |
| 8_12_quadratic | 0.090735 | 0.329552 | 0.319788 | 59/1000 | 59/1000 |
| 12_20_affine | 0.065051 | 0.123432 | 0.358742 | 0/1000 | 0/1000 |
| 12_20_quadratic | 0.126532 | 0.373000 | 0.478927 | 26/1000 | 26/1000 |

For den primære 5–7-pixels affine baggrund er den simulerede median R = 0.095491, 95-percentilen 0.189536 og maksimum 0.341001; originalens uændrede R er 0.429001. D037s stærke kalibreringslinjer havde til sammenligning en kontrolmedian på 0,00013481. Støjsimuleringen gør dermed forskellen til stærkt kalibreringslys væsentligt mindre, uden at den primære affine støjmodel gengiver originalens store residualscore i disse 1000 træk.

De kvadratiske baggrunde giver langt bredere scorefordelinger. Særligt baggrund bestemt fra kun afstand 5–7 pixels kan få stor usikkerhed i det estimerede niveau ved linjens centrum. Det er vores fortolkning af denne models følsomhed, ikke en måling af den sande stjernebaggrund. Ingen baggrund vælges eller udelades på grund af tællingerne. R er fortsat et uvejet residualforhold, og **0/1000 betyder hverken en præcis nul-sandsynlighed, en fysisk afvisning eller en søgningsomfattende signifikans**. Simuleringerne er ikke uafhængige astronomiske nulobservationer, og der er endnu ingen valideret stjerne-/laser-belysningsoverførsel.

## Den rigtige CCD og de rigtige enheder

Den oprindelige råfil er `HARPS.2021-03-05T00:22:15.030.fits`; dens gemte komprimerede bytes genfinder SHA256 `4ba21e12ffc0405481e1c3799a4ebad760bab0284e6db3ecdc49ab85a04e7584`. Samtlige gemte source-kolonner ligger på CCD2, FITS-HDU2. Headerens egne værdier er CONAD = **1,36 e⁻/ADU**, GAIN = 0,74 ADU/e⁻ og RON = **7,07 e⁻**, svarende til 5,19853 ADU. Den oprindelige native DRS-header angiver også 1,36 e⁻/ADU. De to gainretninger er afrundede; produktet er 1,0064. Den eksplicitte CONAD-enhed styrer beregningen.

BZERO = 32768 er en del af FITS' talrepræsentation og er ikke det elektroniske bias eller et fotoelektrontal. Før nye overscan-pixels blev læst, blev alle 265 eksisterende source-rækker samt råkolonner 0:50 og 2098:2148 fastlagt. Efter udlæsning reproducerer de 17.225 tidligere gemte source-pixelpladser nøjagtigt råfilen. De nye to faste strips indeholder 26.500 pixelpladser.

Det primære bias er hver rækkes middelværdi af alle 50 postscan-pixels. Medianen af disse rækkemidler er 183.16 ADU. Prescan giver 184.80 ADU; medianforskellen post minus pre er −1,60 ADU. Alle kolonner bevares, inklusive den tydelige faste struktur i postscan. Efter fjernelse af række- og kolonnemiddelværdier er residualspredningen 3.31463 ADU = 4.50789 e⁻ i postscan og 4.58972 e⁻ i prescan. Dette er en diagnose fra én optagelse, ikke en fuld, empirisk CCD-kovarianskalibrering. Headerens højere RON bruges primært; den målte værdi og dobbelt header-RON beholdes som fastlagte følsomheder.

[ESOs detektorside](https://www.eso.org/sci/facilities/lasilla/instruments/harps/inst/detector.html) støtter den generelle enheds- og readout-kontekst. [DRS-manualen, issue 1.0 fra 2003](https://www.eso.org/sci/facilities/lasilla/instruments/harps/doc/DRS.pdf) beskriver rækkevis biasbestemmelse fra 50 kolonner. De historiske dokumenter bruges ikke som erstatning for den konkrete 2021-header eller som bevis for en bestemt 2021-pipelineimplementering.

## Den fastlagte simulationsmodel

Hver simulering bruger de samme 41 native rækker k401–441, seks r3-aperturpixels og 12 oprindeligt fastlagte baggrundsreferencepixels pr. række. Fotoelektroner trækkes fra en Poisson-fordeling efter biasfjernelse og CONAD-konvertering; uafhængig normalfordelt læsestøj tilføjes. Summen af aperturens fotoner simuleres samlet, hvilket bevarer Poisson-summens middel og varians. Det fastslår ingen 2D-lysfordeling. Referencepixels simuleres enkeltvis, og den gentagne medianbaggrund genberegnes i hver række og hvert træk.

Den gemte affine rumlige baggrund løftes kun så meget, at den antagne fotonbaggrund er ikke-negativ i alle brugte pixels. Løftet og alle middelmodeller er bevaret i `MEAN_MODELS16.npz`; det er en fysisk afgrænsning af en model, ikke en ny måling af sand diffus baggrund. Det valgte polynomielle stjernekontinuum og den faste kalibreringsprofil tilføjes i det eksisterende raw-r3-rum. Der påføres ingen yderligere pixelintegration. Den primære models linjestyrkeparameter er 1281,68759 ADU. Den faktiske tilføjede samplesum er denne parameter gange summen af den samplede profil; en kontinuert arealnormalisering må ikke forveksles med en nøjagtig diskret tællingssum ved enhver fase.

Den spektrale baggrund bestemmes igen fra hver simulerings egne sideprøver. Alle signerede 15 linjeprøver bevares og normaliseres som i D038. Profilens form ændres ikke; kun amplitude i 0–2 og position i det fastlagte interval tilpasses. Det giver den viste modelgenererede residualkorrelation. Korrelationen er ikke en empirisk måling af støjen i uafhængige stjerneobservationer.

De 16 grupper blev fastlagt før tilfældige støjudfald: seks kildebaggrunde; nul, halv og dobbelt signalstyrke; fire kvartpixel-positioner; målt overscan-RON; dobbelt header-RON; prescan-bias. Hver har 1000 træk med PCG64DXSM og fast SeedSequence `[20261111,39,gruppeindeks]`; batchstørrelse og trækorden er bevaret. Nul-signal-gruppen er en diagnose af svage/nul-amplitude-tilpasninger, ikke en observeret ikke-laser-population.

Den låste profil blev oprindeligt bestemt efter en kontinuumkorrektion. Derfor registreres også den lille, deterministiske effekt af at estimere baggrunden igen på de injicerede middelmodeller: den primære støjfrie R er 0.00013034, og den snævre kvadratiske baggrund giver 0.00081651. Disse støjfrie diagnostikker blev beregnet under opbygning af middelmodellerne og var kendt ved den endelige støjlås; det fremgår særskilt af `PREFLIGHT_TIMING_NOTE.json`. Ingen gruppe, frø eller regel blev ændret efter dem, og ingen tilfældige støjudfald var set ved låsen.

Modellen udelader ADC-kvantisering, ukendt mørkestrøms-/fastmønstersystematik, fysisk pixel-/rækkekovarians og afvigelser fra de antagne glatte stjernekontinua. Parametrene er betinget på den allerede udvalgte struktur. Simulationshyppighederne kan derfor ikke bruges som en kalibreret p-værdi eller lasersandsynlighed.

## Alle følsomheder og bevarede randtilfælde

Tabellen viser det oprindelige ±1-pixelinterval; alle træk er bevaret.

| Gruppe | Median R | 95-percentil R | Antal R ≥ den relevante original | Positionsrand | Amplituderand |
|---|---:|---:|---:|---:|---:|
| SOURCE_5_7_affine | 0.095491 | 0.189536 | 0/1000 | 40 | 0 |
| SOURCE_5_7_quadratic | 0.147772 | 0.837281 | 113/1000 | 110 | 13 |
| SOURCE_8_12_affine | 0.079577 | 0.151852 | 0/1000 | 1 | 0 |
| SOURCE_8_12_quadratic | 0.090735 | 0.329552 | 59/1000 | 1 | 0 |
| SOURCE_12_20_affine | 0.065051 | 0.123432 | 0/1000 | 0 | 0 |
| SOURCE_12_20_quadratic | 0.126532 | 0.373000 | 26/1000 | 4 | 0 |
| ZERO_SIGNAL | 0.984887 | 1.000000 | 988/1000 | 786 | 397 |
| HALF_SIGNAL | 0.291012 | 0.634887 | 207/1000 | 199 | 0 |
| DOUBLE_SIGNAL | 0.026449 | 0.052748 | 0/1000 | 1 | 0 |
| PHASE_QUARTER_0 | 0.096353 | 0.200881 | 1/1000 | 1 | 0 |
| PHASE_QUARTER_1 | 0.096168 | 0.198795 | 0/1000 | 0 | 0 |
| PHASE_QUARTER_2 | 0.098520 | 0.188255 | 0/1000 | 0 | 0 |
| PHASE_QUARTER_3 | 0.099960 | 0.197614 | 0/1000 | 1 | 0 |
| EMPIRICAL_OVERSCAN_RON | 0.095136 | 0.192653 | 0/1000 | 26 | 0 |
| DOUBLE_HEADER_RON | 0.119968 | 0.249708 | 2/1000 | 56 | 0 |
| PRESCAN_BIAS_SENSITIVITY | 0.095221 | 0.192369 | 0/1000 | 40 | 0 |

Ved halv signalstyrke når 207/1000 træk den primære originals score; ved dobbelt styrke gør 0/1000. Det understreger afhængigheden af den indsatte intensitet. Nul-signal-resultaterne må ikke læses som en søgningsomfattende falsk-alarmtest. I de oprindelige 17.000 fitpladser indgår 410 flade nul-amplitude-udfald; de udelades ikke.

## Afgrænset positionsopfølgning og efterkontrol

Den primære gruppe havde 40 positionsrandtilfælde. Efter at dette var kendt, blev en særskilt opfølgning låst for hele den oprindelige seks-baggrundsgruppe, ikke et resultatudvalgt deludsnit. Samme 6000 træk afprøves ved ±2 pixels; 1000 var allerede afprøvet i første protokol, så der beregnes 5000 ekstra fit og ingen nye tilfældige træk. Alle oprindelige resultater og deres hashes er bevaret. De seks tællinger i første tabel er helt uændrede. I den snævre kvadratiske gruppe består 13 positionsrandmærker, alle med nul amplitude og flad positionsscore; de er ikke velbestemte, positive linjecentre. Øvrige udvidede kildegrupper har ingen positionsrandtilfælde.

En separat FITS-byteparser reproducerer overscan-data og kontrollerer alle tre HDU'ers DATASUM. Det fulde tilfældige input genopbygges nøjagtigt fra de fastlagte frø. En separat kompileret Siegel-estimator genfinder alle **656.000** rumlige baggrundsfit. Andre polynomieløsninger, Cox–de Boor-profiler og direkte residualsummer kontrollerer alle **22.000** fitpladser og **11.222.000** fasegitterværdier. Desuden bruges 198 særskilte gyldensnitsøgninger på faste prøveindeks. Alle kontroller består; største R-forskel er 3,33 × 10⁻¹⁶. Det er efterkontrol i samme assistentforløb, ikke ekstern fagfællebedømmelse eller empirisk validering af den fysiske støjmodel.

Alle 51,569 tidligere felter i 37/141-tabellerne er bevaret nøjagtigt; otte D039-felter er tilføjet. Fem endelige figurer er direkte gennemset. Den gamle 0061-korrelation 0,780656 er fortsat under den oprindelige 0,8-regel; ingen modeltest ophæver den.

## Reproduktion og næste trin

`DETECTOR_GATE_LOCK.json`, `NOISE_METHOD_LOCK.json` og `PHASE_FOLLOWUP_LOCK.json` afgrænser de tre trin og deres timing. `BRANCH_SUMMARY16.csv`, `PHASE_FOLLOWUP_RESULTS.json`, de to tal-audits og alle tilfældige input/kurver/fitgitre dokumenterer resultaterne. Den særskilte resultatpakke `SETI_D039_INTENSITY_NOISE_RESULTS_2026-11-11.zip` indeholder også de nødvendige oprindelige input på deres relative stier og hele `d039_simulation_payload/`. Udpak den til én rod. Kør `python3 work_harps_20261111_d039_intensity_noise/audit_noise.py`, derefter `audit_phase_followup.py`; NumPy og SciPy kræves. De store simulationsarrays er en særskilt afhængighed til hovedfortsættelsen, så de gamle teleskopdata kan bevares uden overskridelse af filgrænsen.

**Næste foreslåede D040-trin er at afprøve støj- og baggrundsantagelserne på rigtige, matchede stjerneobservationer fra den allerede registrerede D024/D025-kontrolpulje.** Identiteter, egne headers, intensitetsregler og råvinduer skal fastlægges før nye kontrolpixels. Metoden er endnu ikke fastlagt eller udført; ingen baggrundsberegning kører.

Ingen nye teleskopprodukter er hentet; budget 0 kr., ingen eksterne kontakter. 0063 har fortsat ingen brugbar COMB-dækning i de faste blå vinduer; ingen rød-til-blå overførsel eller 0071-vinduesudvidelse er udført. Den oprindelige råkø er lukket med 139 fulde og to delvise tilfælde. Old90 og Rubin er stoppet, offentlig upload er udskudt efter gældende projektstatus, og alle tre fysiske årsager er fortsat uafklarede.
