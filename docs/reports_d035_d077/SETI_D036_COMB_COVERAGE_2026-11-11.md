# D036: direkte kontrol af lokal COMB-dækning

11. november 2026. **De otte på forhånd udvalgte råoptagelser er nu hentet og målt. Ved 655,057 nm findes brugbare COMB-linjer i begge fibre i alle fire optagelser. Ved 482,701 nm finder den fastlagte test ingen accepterede linjer i nogen af de fire optagelser. De blå vinduer kan derfor ikke levere den planlagte lokale responskontrol for 0063. Kvalificerede laserfund er fortsat nul.**

Dette er en ny måling af kalibreringspixels, ikke en ny undersøgelse af de tre oprindelige strukturers pixels. Ingen fysisk årsag er fastslået.

## Resultater

| Struktur | Fiber | Tilstrækkelig lokal dækning | Detekterede linjeforekomster | Brugbare linjeforekomster |
|---|---|---:|---:|---:|
| D002-0061 | A | 4/4 | 123 | 123 |
| D002-0061 | B | 4/4 | 134 | 130 |
| D002-0063 | A | 0/4 | 0 | 0 |
| D002-0063 | B | 0/4 | 0 | 0 |

Forekomsterne omfatter gentagne målinger af mange af de samme frekvenskam-linjer. A og B deler optagelser og kalibreringssystematik; tabellens antal er ikke uafhængige statistiske nulprøver eller forskellige atomare overgange. Fire B-forekomster ved 655 nm udelades fra brugbarhedsgruppen på grund af den fastlagte kantregel. Alle 257 detektioner og alle 16 fiberpladser er bevaret; ingen lokal pixel når 55.000 ADU, 60.000 ADU eller 65.535 ADU.

0061s A-fiber har 29–32 brugbare forekomster pr. optagelse. Maksimale lokale pixelværdier er 19.221–19.675 ADU i A og 17.519–18.338 ADU i B. De kontrollerede profiler topper 0–0,25 pixel fra deres egne oprindelige spor; de positive profilcentroider ligger 0,024–0,031 pixel fra sporene. De diagnostiske A-bredder er 3.23921–3.52072 pixels. Bredden er ikke et udvælgelseskriterium og er ikke fit til originalstrukturen.

I 0063s blå vinduer ligger maksimale lokale pixelværdier ved 286–296 ADU i A og 277–284 ADU i B. Prominensgrænserne er 156,7–176,0 ADU i A og 138,2–171,9 ADU i B. Ingen top passerer dem. Manglen på accepterede linjer betyder også, at den selvstændige sporkontrol i disse optagelser er **ubekræftet**. Resultatet er utilstrækkelig lokal kalibrering under den bevarede metode; det beviser hverken absolut fravær af blåt COMB-lys, en bestemt fysisk årsag eller fravær i hele ESO-arkivet. De brede, små residualbølger er bevaret uden at blive omdøbt til smalle kalibreringslinjer. Ingen grænse er sænket bagefter.

## Alle otte optagelser

| Struktur | ARCFILE uden .fits | Rolle | Timer fra science-midtpunkt | Brugbare A | Brugbare B |
|---|---|---|---:|---:|---:|
| 0061 | `HARPS.2021-03-04T19:55:44.426` | BEFORE/REPEAT | -4.68628 | 29 | 32 |
| 0061 | `HARPS.2021-03-04T19:56:54.800` | BEFORE/PRIMARY | -4.66673 | 32 | 35 |
| 0061 | `HARPS.2021-03-05T19:15:10.667` | AFTER/PRIMARY | +18.63768 | 30 | 31 |
| 0061 | `HARPS.2021-03-05T19:16:21.181` | AFTER/REPEAT | +18.65726 | 32 | 32 |
| 0063 | `HARPS.2021-03-08T20:40:46.265` | BEFORE/REPEAT | -4.85551 | 0 | 0 |
| 0063 | `HARPS.2021-03-08T20:41:56.700` | BEFORE/PRIMARY | -4.83594 | 0 | 0 |
| 0063 | `HARPS.2021-03-09T21:24:00.521` | AFTER/PRIMARY | +19.86512 | 0 | 0 |
| 0063 | `HARPS.2021-03-09T21:25:10.986` | AFTER/REPEAT | +19.88469 | 0 | 0 |

Gentagelserne er cirka 70 sekunder fra deres primære optagelse. Science-observationerne, tidsvinduerne og alle udvælgelsesidentiteter følger uændret fra D035. Ingen optagelse er tilføjet for 0071, og dets oprindelige 48-timersvindue er ikke udvidet.

## Fastlagt måling

`METHOD_LOCK.json` blev gemt før nye DataLink-forespørgsler, råkroppe og COMB-pixels. For hvert eget fiberspor bruges 513 native indeks omkring den oprindelige A-bølgelængde. B-ordenen bestemmes selvstændigt ud fra B's egne bølgelængdekoefficienter: orden 66 ved 0061 og 34 ved 0063; A bruger orden 67 og 34. Der foretages ingen B-til-A-overførsel. De to råchips beskæres hver ved kolonner 50:2098 og samles; rå række er 4095 minus native indeks. Alle koefficienter og koordinater kommer fra den pågældende oprindelige observations egne A/B-oplysninger.

Baggrunden er et gentaget medianfit af en affin rumlig funktion i de faste 10–14- og 26–30-pixelbånd, med afstand over otte pixels til alle A/B-spor. R3-udtrækket summerer signerede, baggrundskorrigerede pixels højst tre pixels fra eget spor. Detektion sker efter en 31-samples medianbaggrund ved prominens mindst max(20 ADU, 10 × en fast robust differensskala). **Differensskalaen indeholder linjestruktur og er ikke en kalibreret støjmodel eller et antal sigma.** Ingen spektral flux glattes eller resamples ud over den udtrykkelige medianbaggrund til detektion.

Brugbarhed kræver afstand fra vindueskant, mindst otte pixels til en anden detekteret top, lokal råværdi under 60.000 ADU og bestået egen sporkontrol. 60.000 er en konservativ videreført grænse for headroom, ikke en målt ikke-linearitetstærskel. Der kræves mindst tre brugbare linjer pr. fiber/optagelse. Der er ingen breddegrænse, kilde-score eller originalstruktur i udvælgelsen. Reglerne var interne og prospektive for disse COMB-pixels; tidligere source- og lampedata var allerede kendt, så undersøgelsen kaldes ikke blind eller offentligt forhåndsregistreret.

## Adgang, implementering og efterkontrol

Otte DataLink-forespørgsler og otte råfilforespørgsler lykkedes uden netværksgenforsøg. De otte råkroppe indeholder tilsammen 140,413,850 bytes og matcher alle DataLinks præcise længder. ARCFILE, de fulde forventede instrumentoplysninger og alle 6.108 tildelte headerfelter er kontrolleret. Kun numerisk DATASUM får fjernet repræsentationsmellemrum ved sammenligningen; de øvrige felter kræver præcis lighed.

Før pixeladgang stoppede den første headerkontrol på DATASUM-teksterne `         0` og `0`. Et for tidligt analysekald stoppede derefter på den manglende headergodkendelsesfil uden at læse pixels. Den oprindelige kode, fejloplysninger og det fejlslagne adgangsmærke er bevaret. `IMPLEMENTATION_AMENDMENT.json` fastlægger normalisering af netop DATASUM samt korrekt rækkefølge for adgangsmærket før ny pixeladgang. Ingen vinduer, geometrikrav, udvælgelses- eller kvalitetsregler er ændret.

En separat byteparser uden Astropy genlæser FITS-blokke, big-endian-pixels og alle 24 HDU'ers DATASUM. En anden polynomieberegning, skalar-medianer, manuel top-/prominenssøgning, lineær interpolation og skalarbredder kontrollerer 533.520 gemte rå samplepladser, 8.208 baggrundsrækker og alle 257 detektioner. Samplepladser kan overlappe mellem fibre og tæller ikke som lige så mange unikke fysiske pixels. Største kurveafvigelse er 1.46e-11 ADU, bølgelængdeafvigelsen 9.09e-13 Å og breddeafvigelsen 8.88e-16 pixel. Alle kontroller består. Det er efterkontrol i samme assistentforløb, ikke ekstern fagfællebedømmelse.

Alle 47,297 tidligere felter i 37- og 141-rækkers tabeller er bevaret nøjagtigt; otte D036-felter er tilføjet. Begge oversigtsfigurer er direkte gennemset. Der er ikke beregnet en ny fit-score for nogen originalstruktur. 0061s oprindelige kvalitetsfejl består, og sammenhængen mellem 0063s centrale og off-trace-struktur er fortsat uafklaret. Ingen stjerne-/laserrespons eller falsk-alarm-sandsynlighed er kalibreret.

## Filer, reproduktion og næste trin

`COVERAGE_RESULTS16.csv`/`.json` indeholder alle målepladser; `ALL_DETECTED_FEATURES.csv` indeholder alle toppe, kantudelukkelser og diagnostiske bredder. `contexts/` rummer signerede råudtræk, baggrunde, kurver og rumlige profiler. `RAW_HEADER_VERIFICATION.json`, adgangskvitteringer og `NUMERICAL_AUDIT.json` dokumenterer kildeidentiteter og efterkontrol. `D002-0061_COVERAGE.png` og `D002-0063_COVERAGE.png` viser alle optagelser.

Råinput gemmes særskilt som `SETI_HARPS_D036_COMB_INPUTS_2026-11-11.zip`. Resultatpakken indeholder de nødvendige originale A/B-headers, forventede COMB-headers og D035-overdragelsestabeller på deres oprindelige relative stier. Udpak resultat- og inputpakken til samme rod og kør `python3 work_harps_20261111_d036_comb_coverage/audit_coverage.py` for byte- og talefterkontrollen. NumPy kræves; produktionskoden bruger desuden SciPy og Astropy, og figurerne Matplotlib. De komplette gamle D031-råinput er fortsat en separat afhængighed for D031, ikke for D036.

**Næste afgrænsede trin er D037: fastlæg og valider en kontinuert egen-A-COMB-respons ved 655 nm med adskilte linjer og optagelser til tilpasning og efterprøvning, før den bruges i en ny kildesammenligning.** D036s 123 brugbare A-forekomster er en mulig kalibreringsbank, ikke allerede en valideret respons. 0063 kan ikke få en blå respons fra disse vinduer, og den røde respons må ikke bare ekstrapoleres dertil. D037 er endnu ikke fastlagt eller udført; ingen baggrundsberegning kører.

Budget 0 kr.; ingen eksterne kontakter eller nye science-observationer. Den oprindelige råkø er lukket med 139 fulde og to delvise tilfælde. Old90 og Rubin er stoppet, og offentlig upload er udskudt efter gældende projektstatus.
