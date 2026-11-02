Næste konkrete HARPS-spor er en **afgrænset metadataundersøgelse af en længere BERV-baseline**, først for HD122640 og derefter HD135204. Første post er **V2E2-0229**. Denne mappe læser kun allerede gemte metadata: ingen nye spektralværdier, downloads, arkivforespørgsler eller klassifikationer.

De tidligere 200 eksponeringer udvider tids- og hastighedsdækningen, men løser ikke den registrerede korte baseline. Alle eksisterende observationer af disse to stjerner ligger mellem 19. februar og 1. marts 2023. Datoerne er observationsdatoer, ikke datoerne i ADP-id'erne.

| Mål | Nuværende extension02-epoker | Nuværende BERV-spænd | Ekstra epoker i tidligere 200 | Samlet antal | Samlet BERV-interval, km/s | Samlet spænd / c/R |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| HD122640 | 3 | 0,892510 km/s | 11 | 14 | 25,199822–27,437732 | 0,858459 |
| HD135204 | 5 | 0,725569 km/s | 10 | 15 | 26,776141–28,490262 | 0,657535 |

De samlede spænd er **2,237910 og 1,714121 km/s**, begge under den nominelle opløsning `c/R = 2,606891 km/s` ved `R=115000`. Én opløsningsenhed er her et beskrivende sammenligningsmål; subopløsningsforskydninger kan i princippet måles, og tabellen er ingen effektberegning, signifikansgrænse eller sikker ophavsbestemmelse. Stjernens radialhastighed, bølgelængdekalibrering og spektral kompleksitet skal fortsat medregnes.

| Mål | Eksakte U-poster i den bevarede FRAME_BASELINE_CONTEXT-kø |
| --- | --- |
| HD122640 | V2E2-0229, V2E2-0231, V2E2-0234, V2E2-0235, V2E2-0236, V2E2-0237 |
| HD135204 | V2E2-0303, V2E2-0305, V2E2-0308, V2E2-0309 |

Kørækkefølgen er den oprindelige katalogrækkefølge og er ikke en sandsynlighedsrangering. **V2E2-0231 er ikke V2-0231**, som tilhører den afsluttede mapping-diagnose. [FRAME_BASELINE_QUEUE.csv](FRAME_BASELINE_QUEUE.csv) bevarer hver posts discovery-id, center, kildehash og oprindelige opfølgningsgrund.

Det gemte `expansion/EXTRA_ELIGIBLE_METADATA.csv` indeholder 9 og 10 yderligere produkter for de to mål; alle er allerede blandt de 300. Der er ingen ubrugt række i dette afgrænsede lokale katalog. Det siger ikke, at hele ESO-arkivet er udtømt.

Næste handling er derfor først at verificere den officielle metadatakontrakt og fryse præcise målidentiteter, ADQL/parametre og svarhåndtering. Den foreslåede grænse er højst **to målforespørgsler, ét forsøg hver, 30 sekunder hver, 1.000 rækker og 4 MiB pr. svar, ingen redirects og ingen science-payloads**. Inventér offentlige HARPS-enkelteksponeringer uden for den eksisterende observationsperiode og udeluk kendte DP-/rå-id'er. Hvis der ikke kommer egnede nye epoker, en grænse rammes eller adgang fejler, gem udfaldet og stop dette spor. Dato alene garanterer ikke ændret BERV; en dokumenteret BERV-/headerkilde skal verificeres under en særskilt afgrænset plan før valg af nye spektre. Dette er en kommende plan, ikke udførte forespørgsler.

[HANDOFF.json](HANDOFF.json) indeholder de præcise fortsættelsesgrænser. [EXISTING_TARGET_EXPOSURES.csv](EXISTING_TARGET_EXPOSURES.csv) lister alle 29 kendte måleprodukter med observeret tidspunkt, BERV, kanonisk sti, størrelse og arkiveret SHA-256. De tre autoritative inputmanifester er:

- `work_harps_20261101/acquisition/DOWNLOAD_MANIFEST.json` — første 100 hovedeksponeringer, rollen `main_unopened`.
- `work_harps_20261101/v2/acquisition/DOWNLOAD_MANIFEST.json` — næste 100, rollen `v2_main_unopened`.
- `work_harps_20261101/v2/extension02/acquisition/DOWNLOAD_MANIFEST.json` — sidste 100, rollen `extension02_unopened`.

Handoff registrerer også de tidligere gemte inputarkivers identiteter og extension02's præcise medlem-/arkivmanifester. Binærfiler behøves ikke til denne metadatakontrol; deres hashes er hentet fra de oprindelige manifester og er ikke genberegnet fra payloads her. Ved en senere gendannelse bruges staging og medlemshashes, og gamle absolutte scratch-stier må ikke genbruges.

Mapping-kontrollen er afsluttet for **alle 35 M-poster i 21 eksponeringer**. Normaliseringsopfølgningen af V2E2-0092/0104 er afsluttet: den lave flux ligger i en senere referenceepoke, ingen discovery er lav, og positiv skalering alene kan ikke øge Pearson-korrelation. De oprindelige 2.185 epokepar/4.370 profiler skal heller ikke genkøres for denne fortsættelse. Rubin er stoppet efter 190 udvalgte objekter med kun 2 numerisk vurderbare i hovedstrømmen og separat 4 i forced-strømmen; minimum 50 er ikke nået. Den ene septemberforespørgsel gav `[]`, og den ene alternative broker kræver dokumenteret konto/token. Ingen af disse afsluttede forløb genstartes af denne handoff.

Alle **185 U og 35 M** bevares; samlet stadig 403 A / 46 O / 185 U / 35 M / 0 N. [SOURCE_HASHES.json](SOURCE_HASHES.json) binder 19 filer inklusive reproduktionsscriptet. [PRESERVATION_CHECK.json](PRESERVATION_CHECK.json) kontrollerer uændrede kilder og labels. [independent_check.json](independent_check.json) reproducerer uafhængigt alle målantal, BERV-ekstremer, de ti U-identiteter og den udtømte lokale ekstraliste. Reproduktion: `python3 build_handoff.py` i denne mappe; scriptet læser kun gemte JSON-/CSV-/Markdown-metadata.
