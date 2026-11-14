# D037: kontinuert egen-A-COMB-respons efterprøvet

11. november 2026. **En fleksibel, kontinuert profil ved 655 nm består de på forhånd fastlagte krav i alle fire kontrolgrupper. Modellen er tilpasset 16 linjeforekomster; alle 107 øvrige forekomster holdes udenfor selve profiltilpasningen. En simpel Gauss-profil består ikke median-kravet.** Dette efterprøver den lokale COMB-kalibreringsklasse i det fastlagte raw-r3-udtræk; overførsel til stjerne-/laserlys er ikke valideret.

| Kontrolgruppe | Forekomster | Spline median R | Spline 95-percentil R | Spline største R | Gauss median R |
|---|---:|---:|---:|---:|---:|
| Samme optagelse, udeladte linjer | 16 | 0.00013048 | 0.00029874 | 0.00032185 | 0.00424530 |
| Gentagelse før originalen | 29 | 0.00013295 | 0.00037741 | 0.00045690 | 0.00428934 |
| Primær efter originalen | 30 | 0.00013209 | 0.00035603 | 0.00039571 | 0.00428069 |
| Gentagelse efter originalen | 32 | 0.00016778 | 0.00032020 | 0.00042015 | 0.00432584 |

Den samlede median for de 107 kontrolforekomster er 0.00013481 for splinen og 0.00428226 for Gauss-profilen. Splinens samlede interval er 0.00005021–0.00045690. Ingen amplitude eller position rammer en fitgrænse. Alle tre startværdier konvergerer for hver model; splinens tre træningsmål er ens inden for 3,1 × 10⁻¹⁵. Modeller og start vælges udelukkende på træningsdata. Kontrolforekomsterne deler ofte frekvenskam-modes og instrument; de er ikke 107 uafhængige observationer af en falsk-alarm-rate.

## Metode og adgang til data

Nearest-before-primæren er `HARPS.2021-03-04T19:56:54.800`. Dens 32 bevarede A-toppe sorteres efter native indeks: lige, nulbaserede rangnumre giver 16 træningslinjer, og de øvrige 16 holdes ude. De 29 forekomster fra gentagelsen før originalen samt 30 og 32 fra de to senere optagelser holdes også ude. Alle 123 forekomster fra D036 er bevaret. De oprindelige COMB-pixels og deres bredder var allerede synlige i D036; dette kaldes derfor ikke en blind undersøgelse.

Hver linje bruger sine 15 oprindelige raw-r3-prøver omkring den fastlagte top. En affin baggrund bestemmes fra afstand 5–7 pixels; det signerede residual divideres med summen af dets positive del. Negative prøver bevares. Kontroltilpasninger må justere styrke og position for hver linje, men ikke den fælles profil. Der efterprøves således profilform, ikke uafhængig forudsigelse af absolut lysstyrke eller bølgelængde.

Den primære model er en kubisk B-spline med knuder hver 0,5 pixel, støtte −6 til +6, ikke-negative koefficienter, areal 1 og første moment 0. De første og sidste to koefficienter er nul. En fast regularisering 0,0001 gange summen af kvadrerede anden-koefficientdifferenser indgår i træningsmålet. Det er en effektiv, samplet raw-r3-respons: **detektorpixelintegration er allerede indeholdt og må ikke påføres igen.** Profilen er ikke en dekonvolveret optisk PSF eller en 2D-model.

Gauss-baselinen har fælles sigma med fast interval 0,6–2,5 pixels. Begge modeller har træningsstarter ved 1,0, 1,4 og 1,8 pixels. Amplituder ligger i 0–2, og positioner i −1 til +1 pixel. Kontrolpositioner prøves i alle 401 faste gitterpunkter med analytisk profilleret amplitude og derefter lokal skalarforfinelse. Der er ingen ny topudvælgelse.

R er summen af kvadrerede, uvejede residualer divideret med summen af kvadrerede målværdier. Det er hverken en fotonandel, en sandsynlighed eller en kalibreret chi-i-anden-statistik. Hver kontrolgruppe skal særskilt have median R ≤ 0,001, 95-percentil ≤ 0,005 og maksimum ≤ 0,01, med alle resultater endelige og uden nuisance-randtilfælde. Derudover kræves alle fire kvartpixel-fasebins repræsenteret i træningen samt ét væsentligt profilmaksimum højst 0,5 pixel fra nulcentroiden. Splinens fasebinantal er 6, 2, 3 og 5; det numeriske profilmaksimum ligger ved −0,265 pixel. Den effektive halvhøjdebredde er cirka 3.28166 pixels. Kravene er interne, fastlagte kontrolkrav for denne kalibreringsklasse, ikke en fysisk klassifikationstærskel.

`METHOD_LOCK.json` og `FROZEN_LINES123.json` låser hele opdelingen, data og modelregler før D037-fit. En før-fit implementeringsrettelse konverterer et NumPy-boolsk flag til et almindeligt JSON-flag og føjer hashkontrol til; den oprindelige kode og den uændrede videnskabelige metode er bevaret i `prefit_implementation/` og `IMPLEMENTATION_LOCK.json`. Ingen fitresultater var set før rettelsen.

## Efterkontrol og bevaring

En separat Cox–de Boor-implementering uden SciPy-interpolation, analytiske B-spline-integraler, skalarbaggrunde og en gyldensnitsøgning reproducerer alle 246 linjetilpasninger, alle 98.646 fasegitterværdier og alle seks træningsstarter. Største forskel i R er 6.07e-18; positionsforskellen er højst 8.72e-09 pixel. Alle normaliserings-, centroid-, gruppe- og fasekrav er genkontrolleret. Dette er kontrol i samme assistentforløb, ikke ekstern fagfællebedømmelse.

Alle 48,721 tidligere 37/141-felter bevares nøjagtigt; otte D037-felter tilføjes. Begge endelige figurer er direkte gennemset. Ingen nye teleskopprodukter eller råpixels er hentet. Kvalificerede laserfund er nul, og den gamle kvalitetsfejl for 0061 består.

`SPLINE_MODEL.json`, `GAUSSIAN_MODEL.json`, `FROZEN_LINES123.json`, `ALL_OUTCOMES246.csv`, de to `*_PHASE_GRIDS.npz` og `NUMERICAL_AUDIT.json` indeholder model, alle udfald og efterkontrol. Kør `python3 work_harps_20261111_d037_comb_response/audit_response.py` fra en udpakning med de bevarede inputstier. NumPy kræves til efterkontrollen; produktionsfit kræver også SciPy. `RESPONSE_VALIDATION.png` viser samtlige udfald og det svageste kontrolfit; `ALL_HELDOUT_PROFILES.png` viser alle 107 kontrolprofiler.

Den efterfølgende, særskilt fastlagte D038-sammenligning er gennemført i samme forløb. Den ændrer ikke den låste D037-model eller dens kontrolgrupper.

---

# D038: 0061 sammenlignet med den låste COMB-respons

11. november 2026. **0061s oprindelige raw-r3-struktur gengives fortsat dårligt af den lokale, efterprøvede COMB-profil under alle seks tidligere fastlagte baggrunde: R = 0.31979–0.55523. Et udvidet positionsinterval ændrer ingen score meningsfuldt.** Dette er en betinget profilsammenligning. Fysisk årsag er fortsat uafklaret, den gamle kvalitetsfejl består, og kvalificerede laserfund er nul.

| Baggrund | Primær spline R | Position, pixels | Normaliseret amplitude |
|---|---:|---:|---:|
| 5_7_affine | 0.42900075 | +0.631817 | 1.074042 |
| 5_7_quadratic | 0.55523221 | +0.642296 | 1.045878 |
| 8_12_affine | 0.34877949 | +0.557578 | 0.861007 |
| 8_12_quadratic | 0.31978763 | +0.555497 | 0.816132 |
| 12_20_affine | 0.35874247 | +0.505175 | 0.759091 |
| 12_20_quadratic | 0.47892657 | +0.511100 | 0.870515 |

Den primære 5–7-pixels affine baggrund giver R = 0.42900075. Til sammenligning ligger de 107 D037-kontrolforekomster ved R = 0.00005021–0.00045690. **De to grupper har forskellig lysstyrke, støj og fiberbelysning. Scoreforskellen kan ikke omregnes til en falsk-alarm-sandsynlighed, sigma-værdi eller sandsynlighed for en laser.** Den store, smalle centrale prøve og residualerne ses direkte i `SOURCE_COMPARISON6.png`.

## Afgrænset test

D038-metoden blev låst efter D037-efterkontrollen og før den nye kildetilpasning. Alle seks affine/kvadratiske baggrunde med bånd 5–7, 8–12 og 12–20 pixels følger uændret fra D029. Hver OLS-baggrund beregnes på samtlige fastlagte sideprøver; de genberegnede koefficienter reproducerer D029. Sammenligningen bruger kun de samme 15 native raw-r3-prøver omkring k421 i orden 67. Ingen r5/r6/r7- eller native-DRS-profil får overført r3-modellen.

Den signerede kildelinje normaliseres med samme positive-sum-konvention som D037. Den frosne profils form ændres ikke; kun amplitude og position tilpasses. Amplituden er 0–2. Hver model afprøves både i det primære −1 til +1-pixelinterval og i en særskilt fastlagt −2 til +2-pixelfølsomhed. Det giver 2 modeller × 6 baggrunde × 2 intervaller = 24 bevarede udfald og 14.424 fasegitterværdier. Ingen amplitude eller position rammer en grænse. Største forbedring i spline-R ved intervaludvidelsen er 1.11e-16, svarende til afrunding.

Gauss-baselinen er bevaret som sammenligningsmodel og giver primært R = 0.30332–0.54757. Den består ikke D037s krav for kalibreringslinjerne og vælges ikke i stedet for splinen ud fra originalens lidt mindre score. Ingen baggrund, model eller fasegrænse udvælges for at ændre originalens status.

Resultatet er, at denne faste COMB-respons ikke reproducerer den observerede kildes profil godt under de seks konkrete behandlinger. Der er fortsat forskel mellem stærkt kalibreringslys og en svag struktur oven på et stjernespektrum. Der mangler en kalibreret støjkovarians og efterprøvning ved matchet lysstyrke samt valideret stjerne-/laser-belysningsoverførsel. Modellen er 1D; den påviser ikke en bestemt kosmisk partikel, detektorfejl eller en fælles årsag med en off-trace-struktur. D016-korrelationen 0,780656 ligger fortsat under den oprindelige grænse 0,8.

## Efterkontrol og næste trin

En separat normal-ligningsløsning for baggrundene samt Cox–de Boor-profiler og gyldensnitsøgning kontrollerer alle 24 udfald og alle 14.424 fasegitterværdier. Største forskel i R er 3.33e-16; største positionsforskel er 2.19e-08 pixel. Alle kontroller består i samme assistentforløb; det er ikke ekstern fagfællebedømmelse. Begge endelige figurer er direkte gennemset.

Alle 50,145 tidligere felter fra D037 bevares nøjagtigt; otte D038-felter tilføjes. Alle tidligere D036-felter er dermed også bevaret. Ingen nye teleskopprodukter er hentet; budget 0 kr., ingen eksterne kontakter.

`SOURCE_PROFILES6.json`, `SOURCE_OUTCOMES24.csv`/`.json`, alle fasegitre og `NUMERICAL_AUDIT.json` dokumenterer data og beregning. Kør `python3 work_harps_20261111_d038_comb_source_compare/audit_source.py` efter D037-efterkontrollen, med de oprindelige relative inputstier bevaret.

**Næste foreslåede trin D039 er at efterprøve lysstyrke, baggrund og støj i denne sammenligning før stærkere fysisk fortolkning.** Gevinster, bias, læsestøj og enheder skal kontrolleres før en simulationsmodel; kontroller, intensiteter, faste frø og fejlhåndtering skal fastlægges før nye udfald. En modelafhængig simulation er ikke en uafhængig astronomisk nulobservation. Metoden er endnu ikke fastlagt eller udført, og ingen baggrundsberegning kører.

0063 har fortsat ingen brugbar COMB-kalibrering i de fastlagte blå vinduer. Ingen rød-til-blå overførsel eller udvidelse af 0071-vinduet er udført. Den oprindelige råkø er lukket med 139 fulde og to delvise tilfælde. Old90 og Rubin er stoppet, og offentlig upload er udskudt efter gældende projektstatus. Alle tre fysiske oprindelser er fortsat uafklarede; kvalificerede laserfund er nul.
