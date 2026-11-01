# Spektral kontekst for 64 oprindelige + 31 nye uafklarede V2-hits

Denne efteranalyse forklarer, hvad de lokale toppe ligger i, uden at ændre detektoren eller oprindelsesklassifikationerne. Alle 95 hændelser på 11 mål er med i `CANDIDATE_CONTEXT_95.csv`; de oprindelige 64 er bevaret separat i `CONTEXT_64.csv`, udvidelsen i `CONTEXT_31.csv`. Ingen enkelt atomar eller molekylær overgang er identificeret sikkert.

**Hovedresultatet er gentagelig stjernespektral struktur:** 89/95 hændelser ligger i de valgte brede CN-/CH-indeksområder efter korrektion med eksponeringens målte stjerne-RV. Ni grupper på tværs af stjerner indeholder 81 hændelser. De tilsvarende gruppemidtpunkter ligger inden for 0,00825 Å i den omtrentlige stjerneramme. Det er ikke kun en sammenligning af topcentrene: profilerne omkring dem ligner også hinanden, når hele bølgelængdeaksen korrigeres med den uafhængigt målte CCF-RV, uden at optimere et ekstra offset. Det støtter almindelig stjernespektral struktur som arbejdshypotese. Det fastslår ikke, at enhver top er én CN-/CH-linje, eller at en lokal top nødvendigvis er fysisk emission.

| Delmængde | Hits | CN-område | CH-område | Andre områder |
|---|---:|---:|---:|---:|
| Oprindelige | 64 | 44 | 16 | 4 |
| Nye efter kortlægningskontrol | 31 | 24 | 5 | 2 |
| Samlet | 95 | 68 | 21 | 6 |

De brede områder er 3861–3884 Å og 4285–4315 Å, anvendt som kontekst efter Dias et al. (2018), afsnit 3.2, og Lardo et al. (2012), afsnit 3. Indeksgrænserne er ikke en liste over molekylære overgange; deres air/vacuum-konvention er ikke tilstrækkeligt eksplicit til præcise linjematch. Her bruges de kun som brede områdemærker. Se kilde-URL'er i `SOURCES.json`.

## Hvad de faktiske sammenligninger viser

`GROUPS_95.json` og `CROSS_TARGET_PROFILE_PAIRS.csv` indeholder alle grupper og alle 32 profilpar. Ni grupper ligger i de brede CN-/CH-områder. Den tiende, X03 omkring 3851,423 Å, er en to-stjerne-nærhed mellem 0001/0139; den tælles særskilt og er ikke evidens for en fælles stjerneoprindelse, fordi 0001 har en observerrammekomponent, mens de senere epoker for 0139 understøtter barycentrisk persistens. En fælles stjernebaggrund kan ligne hinanden, selv om den centrale top har forskellig kontekst.

- X11 ved 3869,4846 Å: fem stjerner, 19 hændelser, spænd 0,00737 Å mellem gruppemidtpunkter.
- X17 ved 4312,4085 Å: fire stjerner, ti hændelser, spænd 0,00715 Å.
- HD106515A og HD114783 deler fire adskilte strukturer. Efter hver eksponerings CCF-RV-korrektion er den største restforskel mellem gruppemidtpunkterne ækvivalent med 0,0752 km/s. Det er en beskrivende konsistenskontrol, ikke en ny præcisions-RV-måling. Syv målpar har mindst to fælles strukturer; alle er opført i `MULTIFEATURE_TARGET_PAIRS.csv`.

En trepunktsmedian-top ligger under den lokale 95-percentil i afstande 1–5 Å i 69/95 tilfælde og under 95-percentilen i afstande 3–10 Å i 78/95 tilfælde. Alle disse ligger i CN-/CH-områderne. Figurerne viser ofte toppe mellem dybe absorptionsstrukturer. Percentilerne er **ikke et kalibreret fysisk kontinuum**: line blanketing, støj, blaze-/farvevariation og lokale båndkanter påvirker dem. En top over en percentil er derfor ikke automatisk en emissionslinje, og en top under den udelukker ikke en tilføjet emission oven på absorption. Ingen af forholdstallene bruges som klassifikationsgrænse.

## De seks hændelser uden for de valgte indeksområder

| ID | Mål | Topocentrisk air, Å | Kontekst og begrænsning |
|---|---|---:|---|
| 0001 | HD103991 | 3852,190680 | Observerramme-/instrumenthypotese; selvstændig råbilledkontrol nødvendig. |
| 0103 | HD114386 | 3822,679329 | Gentaget observerramme-kam undersøges mod kalibreringslys. |
| 0104 | HD114386 | 3822,831815 | Samme eksponering som 0103; afstand 0,152487 Å. |
| 0125 | HD114783 | 3852,337547 | Vigtigt modeksempel: epoch31-kontrollen giver r=0,967 barycentrisk mod −0,046 topocentrisk. Nærheden til 0139 i observerrammen identificerer ikke en fælles kontaminant. |
| 0139 | HD115031 | 3852,342759 | Parmedianerne 0,883/0,864 er domineret af tidsklynger. De to senere epoker favoriserer barycentrisk persistens (r>0,88 mod negativ topocentrisk r). Begrænset tidsdækning; ingen kemisk identifikation. |
| 0205 | HD120411 | 6363,774156 | Nær atmosfærisk O I 6363,776 Å; undersøges særskilt i doublet-opfølgningen. Ingen klassifikation her. |

Cretignier et al. (2021), afsnit 2.6 og figur 6, dokumenterer HARPS-ghosts fra referencefiber B med Fabry–Pérot-kamstruktur omkring 3822 og 3851 Å i terrestrisk/BERV-ramme. Det begrunder en konkret instrumenthypotese for de afvigende blå strukturer; de omtrentlige litteraturområder er ikke præcise linjepositioner. Den selvstændige råbilled-/fiberanalyse leverer den afgørende lokale kontrol. Denne rapport bruger ingen endelig instrumentel oprindelsesklassifikation.

## Begrænset atomar kontrol

`ATOMIC_CONTEXT_95.csv` sammenholder alle 95 positioner med en udtrykkeligt afgrænset liste over H I-, He I- og Ca-linjer fra NISTs air-tabeller. Den er ikke et komplet linjeatlas og bruges ikke som et veto. H I 3889,049 og 4340,462 Å samt Ca II 3933,6614/3968,4673 Å må ikke forveksles med de undersøgte lokale toppe. Der findes en reel positionsnærhed mellem He I 3867,48 Å og strukturen omkring 3867,51 Å. Den er kun et flag: uden sammenhængende ledsagelinjer, en fysisk stjernemodel og eksplicit behandling af blends kan den ikke bære en heliumidentifikation. NISTs laboratorieintensiteter er ikke forudsagte emissionsforhold i disse stjerner.

## Rammer, fejl og reproduktion

ADP-headerne kontrolleres for `SPECSYS=BARYCENT`, Å-enheder og `TUCD1=em.wl;obs.atmos`. Alle viste bølgelængder forbliver **air**; der foretages ingen implicit vacuum-konvertering. Den omtrentlige stjerneramme er λ_bary/(1+RVC/c), og observerrammen λ_bary/(1+BERV/c), c=299792,458 km/s. Dette er tilstrækkeligt til kontekst, men ikke en fuld relativistisk eller absolut laboratoriekalibrering. CCF-maskens nulpunkt, linjeblends og atmosfæriske stjerneskift begrænser absolutte identifikationer.

`RV_HEADERS_92.csv/json` indeholder direkte læste CCF-headerdata med TAR-hash og medlemnavn: 84 eksponeringer har én maske, seks har både G2 og K5, og to mangler CCF. Alle 95 valgte hændelser har målte værdier. For to masker bruges det aritmetiske middel alene som en beskrivende koordinat, mens begge værdier og deres fulde spænd bevares. Største maskespænd er 0,015014 km/s. `ccf_noise_km_s` er headerens photon-noise-estimat; ved to masker gemmes maksimum, ikke en fejl på middelværdien. Planlægnings-RV bruges aldrig som erstatning.

Alle 95 lokale ERR-arrayudsnit mangler gyldige positive usikkerheder. Derfor estimeres ingen formel fluxsignifikans. Første forsøg, der fejlede på dette, er bevaret i `attempts/`, og en eksplicit ændring til uvejede deskriptive fluxmål står i `PLAN_AMENDMENT01.json`. Håndtering af to CCF-masker er dokumenteret i `PLAN_AMENDMENT02.json`; de oprindelige planer og mislykkede forsøg er bevaret. Den senere tværstjerne-profiltest og atomare kontrol har egne planer og er tydeligt post hoc.

Fra projektroden køres med Python, NumPy, SciPy, Astropy og Matplotlib:

```bash
PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/line_identification/analyse_context.py
PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/line_identification/analyse_new31.py
PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/line_identification/combine_context.py
PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/line_identification/check_atomic_context.py
PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/line_identification/verify_context.py
```

`VERIFICATION_95.csv` kontrollerer hver hændelses kildehash, RV-koordinat, coremedian, topmål og begge 95-percentiler direkte mod den fulde FITS-fil. Alle kontroller bestod. Alle 28 oprindelige og 15 ekstra grupperepræsentanter samt de ti overlays er visuelt gennemset; se `VISUAL_REVIEW.json`. Ingen original disposition er ændret af denne analyse.

`LINE_CONTEXT_EVIDENCE.zip` indeholder alle 95 profil-NPZ'er samt rapporter, tabeller, planer, kode og logs. De 21 PNG-figurer leveres separat. `EVIDENCE_ARCHIVE.json` angiver SHA-256, CRC32 og størrelse for hvert arkivmedlem og bekræfter byte-for-byte-kontrol mod kildefilerne. `MANIFEST.json` omfatter også figurerne; arkivet og dets egen audit er undtaget fra den selvrefererende del. Arkivet genskabes med `python v2/line_identification/package_evidence.py`.
