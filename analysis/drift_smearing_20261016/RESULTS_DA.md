# SETI: frekvensudstrygning inden for hver integration

De ni tidligere udvalgte ON-spor har høje scorer i deres udvalgte enkeltkanaler, men der er ikke en tilsvarende forhøjelse i den omkringliggende frekvensstøtte, som den her fastlagte model for et vedvarende driftende signal fordeler størstedelen af signalets effekt over. Det er en beskrivende morfologikontrol af allerede eksponerede data. Den er ikke en formel forkastelse af signalerne eller en ny SETI-detektion.

For de ni spor spænder den oprindelige fire-række-score fra **6,638 til 7,450**. Når de udvalgte centrale bins maskeres, spænder den vægtede score i den forventede udstrygning fra **−1,203 til 1,536**. De centrale bins har gennemsnitlige standardiserede residualer på **3,319–3,725**; den kernelvægtede middelværdi i de øvrige bins er **−0,120–0,392**. Disse størrelser beskriver residualer og vægtninger; de er ikke kalibreret SNR eller sandsynligheder.

| Oprindeligt ON-spor | Udstrygning, native kanaler | Oprindelig central score | Score uden central bin | Otte forskudte kontroller: min.–maks. |
|---|---:|---:|---:|---:|
| Scan 1 / spor 1 | 25.471 | 6.813 | -1.203 | -1.029 til 1.161 |
| Scan 1 / spor 2 | 12.901 | 6.744 | 0.659 | -1.728 til 1.298 |
| Scan 1 / spor 3 | 3.308 | 6.638 | 0.928 | -2.364 til 0.744 |
| Scan 2 / spor 1 | 18.525 | 6.997 | 0.607 | -1.725 til 1.451 |
| Scan 2 / spor 2 | 24.148 | 6.962 | -0.044 | -1.722 til 2.603 |
| Scan 2 / spor 3 | 6.285 | 6.916 | 0.553 | -1.544 til 1.159 |
| Scan 3 / spor 1 | 12.901 | 7.450 | 0.141 | -0.758 til 0.669 |
| Scan 3 / spor 2 | 10.916 | 7.031 | -0.088 | -0.868 til 0.947 |
| Scan 3 / spor 3 | 4.300 | 6.750 | 1.536 | -0.912 til 3.026 |

Kontrollerne bruger de samme fastlagte spor ved ±256, ±512, ±768 og ±1.024 kanaler. Syv af ni ON-værdier uden central bin ligger inden for deres otte kontrollers observerede interval; én ligger over og én under. Intervallerne er hverken usikkerhedsintervaller eller en nulfordeling. Alle kontroller og udfald er bevaret, og der er ikke beregnet p-værdier.

Modellen er en en-kanal bred uniform intrinsisk linje foldet med den uniforme frekvensbevægelse under hver **18,253611008 sekunders integration**. Udstrygningen er |drift| × integrationstid / kanalbredde; for de ni oprindelige drifthastigheder er den **3,308–25,471 kanaler**. Den centrale bin fjernes efter beregningen af den fulde model, uden at genfordele den fjernede masse til nabobins. Modellen placerer **69,77–96,07 %** af sin masse uden for den centrale bin. De oprindelige drifthastigheder, frekvensreferencer, vinduer og normaliseringer er fastholdt.

Et signal, der kun er aktivt i en del af integrationen, kan være smallere. Reel instrumentel kanalrespons, subkanalplacering og tidslig variation kan også afvige fra den idealiserede model. Resultatet fastslår derfor ikke signalernes oprindelse og udelukker ikke korte bursts. Det giver ikke et kvalificeret OFF-veto, falskalarmrate eller fysisk følsomhed.

Kontrollen omfatter alle **54 spor/scanningskontekster**, **486 frekvensforskudte kontekster**, **7.776 rækkespektre** og **505.440 gemte spektralceller** fra HIP98505/HD189733-besøget **28. april 2017**. Hvert spektrum indeholder 65 kanaler omkring det oprindelige afrundede spor; alle 16 rækker er bevaret. Primærstatistikken bruger altid de samme oprindelige fire rækker. De tre ON- og tre OFF-scanninger tilhører samme historiske besøg. Ingen nye observationer eller frekvensområder er tilføjet.

Alle 54 oprindelige fire-række-scorer genfindes med **0,0 maksimal afvigelse i binary64** fra de gemte metadata. Den nye statistik er summen af modelmasse × standardiseret residual divideret med kvadratroden af summen af de kvadrerede modelmasser; det giver samme algebraiske L2-normalisering for mål og kontroller. Der er ikke tilpasset amplitude, drift, fase, bredde, normalisering eller tærskel til udfaldene.

`SCOPE.json`, `primary.py`, `plot.py` og den præcise kildemetadata blev offentliggjort og læst tilbage byte for byte før det første egentlige numeriske kald, ved commit `3f41b4a4931aba44c1637136d006da2cd8cb4e5b`. En første launcher nåede ikke at starte Python-programmet, fordi dens hardkodede fortolkersti ikke fandtes. Denne fejl er bevaret i `*.launch_failure_01`; den åbnede ingen spektraldata og brugte **0,019271 CPU-sekund**. Den efterfølgende korrekte launcher brugte den eksisterende Python-fortolker og gennemførte den første egentlige primærkørsel én gang.

Den gennemførte primærproces brugte **10.557173 hele-børneproces-CPU-sekunder**, **10.593699 sekunders forløbet tid** og **85,536,768 bytes maksimal RSS**. Programmet målte selv 10,388446 CPU-sekunder; det er ikke det samme som hele procesmålingen. Udgift **0 DKK**; nul nye teleskopforespørgsler og teleskopbytes.

`results/spectra/P00.npz` til `P53.npz` indeholder de gemte rå 65-kanalspektre, lokale median501-baselines, standardiserede residualer, kontinuerte og afrundede koordinater, kernelmasser, masker og rækkebidrag. Sammen med scope og metadata er de tilstrækkelige til selvstændigt at genberegne de faste scorer fra de bevarede kapsler. En fuld ny kontrol af de lokale median501-baselines mod råkilden kræver det SHA-256-fastlåste `SETI_NATIVE_SPOR_2026-10-14.zip`, hvis placering og pins står i scopet. De oprindelige 54 råcrops og normaliseringsfiler findes i det kildearkiv.

Primærresultatet bevares som `COMPLETE_PRIMARY_PENDING_INDEPENDENT_QA`. Den efterfølgende uafhængige QA har **PASS** i `qa/QA_RECEIPT.json`: alle 108 kildepins og 505.440 spektralceller er kontrolleret i 3.087.090 numeriske sammenligninger. Rå værdier, median501-baselines, standardiserede residualer og sporcentre matcher præcist; største kontrollerede afvigelse er 4,44 × 10⁻¹⁵ i kernelmasser og 6,15 × 10⁻¹⁴ i scorer. QA bruger en separat trapez-CDF og importerer ikke primærprogrammets numeriske funktioner. Den centrale maske fjerner det direkte udvalgte scorebidrag, men gør ikke nabobins uafhængige af den oprindelige udvælgelse eller den fælles normalisering. De frosne primærresultater er uændrede. Gamle pensionerede og fejllukkede identiteter genbruges ikke. Oprindelig A/B-status og lukkede 2016-/2019-ruter er uændrede. Formelt kontrolpunkt: 20. oktober 2026.
